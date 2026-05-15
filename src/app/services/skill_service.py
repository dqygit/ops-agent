from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from app.shared.config import APP_DIR

SKILL_BODY_LIMIT_BYTES = 64 * 1024
_FRONTMATTER_RE = re.compile(r"\A---\s*\n(?P<meta>.*?)\n---\s*\n?(?P<body>.*)\Z", re.DOTALL)
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


@dataclass(frozen=True)
class SkillPackage:
    name: str
    description: str
    path: str
    valid: bool
    error: str | None
    updated_at: datetime
    body_size: int


@dataclass(frozen=True)
class LoadedSkill:
    name: str
    description: str
    body: str
    path: str


@dataclass(frozen=True)
class _DiscoveredSkill:
    package: SkillPackage
    body: str | None
    skill_file: Path | None


class SkillService:
    def __init__(self, *, skills_dir: Path | None = None) -> None:
        self._skills_dir = skills_dir or (APP_DIR / "skills")

    def list_skills(self) -> list[SkillPackage]:
        return [item.package for item in self._discover_skills()]

    def load_skill(self, name: str) -> LoadedSkill:
        for item in self._discover_skills():
            if item.package.valid and item.package.name == name and item.body is not None:
                return LoadedSkill(
                    name=item.package.name,
                    description=item.package.description,
                    body=item.body,
                    path=item.package.path,
                )
        raise ValueError(f"Skill not found or invalid: {name}")

    def _discover_skills(self) -> list[_DiscoveredSkill]:
        if not self._skills_dir.exists() or not self._skills_dir.is_dir():
            return []

        skills_root = self._resolve_path(self._skills_dir)
        if skills_root is None or not skills_root.is_dir():
            return []

        discovered: list[_DiscoveredSkill] = []
        seen_valid_names: set[str] = set()

        for package_dir in sorted(self._skills_dir.iterdir(), key=lambda path: path.name):
            if not package_dir.is_dir():
                continue

            item = self._discover_skill(package_dir, skills_root)
            if item.package.valid:
                if item.package.name in seen_valid_names:
                    item = _DiscoveredSkill(
                        package=replace(item.package, valid=False, error="Duplicate skill name"),
                        body=None,
                        skill_file=item.skill_file,
                    )
                else:
                    seen_valid_names.add(item.package.name)
            discovered.append(item)

        return discovered

    def _discover_skill(self, package_dir: Path, skills_root: Path) -> _DiscoveredSkill:
        entry_updated_at = self._entry_timestamp(package_dir)
        path = self._display_path(package_dir)

        resolved_package_dir = self._resolve_path(package_dir)
        if resolved_package_dir is None:
            return self._invalid_skill(
                name=package_dir.name,
                description="",
                path=path,
                updated_at=entry_updated_at,
                error="Failed to resolve skill package",
                body_size=0,
            )
        if not self._is_within(skills_root, resolved_package_dir):
            return self._invalid_skill(
                name=package_dir.name,
                description="",
                path=path,
                updated_at=entry_updated_at,
                error="Skill package escapes skills directory",
                body_size=0,
            )

        skill_file = resolved_package_dir / "SKILL.md"
        try:
            skill_file.lstat()
        except OSError:
            return self._invalid_skill(
                name=package_dir.name,
                description="",
                path=path,
                updated_at=entry_updated_at,
                error="Missing SKILL.md",
                body_size=0,
            )

        resolved_skill_file = self._resolve_path(skill_file)
        if resolved_skill_file is None:
            return self._invalid_skill(
                name=package_dir.name,
                description="",
                path=path,
                updated_at=entry_updated_at,
                error="Failed to resolve SKILL.md",
                body_size=0,
            )
        if not self._is_within(resolved_package_dir, resolved_skill_file):
            return self._invalid_skill(
                name=package_dir.name,
                description="",
                path=path,
                updated_at=entry_updated_at,
                error="SKILL.md escapes skill package",
                body_size=0,
            )
        if not resolved_skill_file.is_file():
            return self._invalid_skill(
                name=package_dir.name,
                description="",
                path=path,
                updated_at=entry_updated_at,
                error="Missing SKILL.md",
                body_size=0,
            )

        updated_at = self._timestamp(resolved_skill_file)

        try:
            content = resolved_skill_file.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            return self._invalid_skill(
                name=package_dir.name,
                description="",
                path=path,
                updated_at=updated_at,
                error=f"Failed to read SKILL.md: {exc}",
                body_size=0,
            )

        match = _FRONTMATTER_RE.match(content)
        if match is None:
            return self._invalid_skill(
                name=package_dir.name,
                description="",
                path=path,
                updated_at=updated_at,
                error="Missing frontmatter",
                body_size=0,
            )

        metadata = self._parse_metadata(match.group("meta"))
        body = match.group("body")
        body_size = len(body.encode("utf-8"))

        raw_name = (metadata.get("name") or "").strip()
        description = (metadata.get("description") or "").strip()
        display_name = raw_name or package_dir.name

        if not raw_name:
            return self._invalid_skill(
                name=display_name,
                description=description,
                path=path,
                updated_at=updated_at,
                error="Missing name",
                body_size=body_size,
            )
        if not description:
            return self._invalid_skill(
                name=display_name,
                description="",
                path=path,
                updated_at=updated_at,
                error="Missing description",
                body_size=body_size,
            )
        if _NAME_RE.match(raw_name) is None:
            return self._invalid_skill(
                name=display_name,
                description=description,
                path=path,
                updated_at=updated_at,
                error="Invalid name",
                body_size=body_size,
            )
        if body_size > SKILL_BODY_LIMIT_BYTES:
            return self._invalid_skill(
                name=raw_name,
                description=description,
                path=path,
                updated_at=updated_at,
                error=f"Skill body exceeds {SKILL_BODY_LIMIT_BYTES} bytes",
                body_size=body_size,
            )

        return _DiscoveredSkill(
            package=SkillPackage(
                name=raw_name,
                description=description,
                path=path,
                valid=True,
                error=None,
                updated_at=updated_at,
                body_size=body_size,
            ),
            body=body,
            skill_file=resolved_skill_file,
        )

    def _invalid_skill(
        self,
        *,
        name: str,
        description: str,
        path: str,
        updated_at: datetime,
        error: str,
        body_size: int,
    ) -> _DiscoveredSkill:
        return _DiscoveredSkill(
            package=SkillPackage(
                name=name,
                description=description,
                path=path,
                valid=False,
                error=error,
                updated_at=updated_at,
                body_size=body_size,
            ),
            body=None,
            skill_file=None,
        )

    def _parse_metadata(self, raw_metadata: str) -> dict[str, str]:
        metadata: dict[str, str] = {}
        for line in raw_metadata.splitlines():
            stripped = line.strip()
            if not stripped or ":" not in stripped:
                continue
            key, value = stripped.split(":", 1)
            key = key.strip()
            if key not in {"name", "description"}:
                continue
            metadata[key] = value.strip()
        return metadata

    def _resolve_path(self, path: Path) -> Path | None:
        try:
            return path.resolve(strict=True)
        except OSError:
            return None

    def _is_within(self, root: Path, path: Path) -> bool:
        try:
            path.relative_to(root)
        except ValueError:
            return False
        return True

    def _display_path(self, package_dir: Path) -> str:
        for base_dir in (APP_DIR.parent, self._skills_dir.parent):
            try:
                return package_dir.relative_to(base_dir).as_posix()
            except ValueError:
                continue

        return (Path(self._skills_dir.name) / package_dir.name).as_posix()

    def _entry_timestamp(self, path: Path) -> datetime:
        try:
            return datetime.fromtimestamp(path.lstat().st_mtime, UTC)
        except OSError:
            return datetime.now(UTC)

    def _timestamp(self, path: Path) -> datetime:
        return datetime.fromtimestamp(path.stat().st_mtime, UTC)
