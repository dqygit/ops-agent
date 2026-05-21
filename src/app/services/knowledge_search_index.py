from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterable
from contextlib import closing
from pathlib import Path

from app.services.knowledge_models import (
    KnowledgeEntry,
    KnowledgeReindexResult,
    KnowledgeSearchFilters,
    KnowledgeSearchHit,
)

_MATCH_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_一-鿿]+")
_MAX_LIMIT = 100
_DEFAULT_LIMIT = 20


class KnowledgeSearchIndex:
    def __init__(self, index_path: Path) -> None:
        self._index_path = index_path
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def index_entry(self, entry: KnowledgeEntry) -> None:
        with closing(self._connect()) as connection:
            with connection:
                self._delete_entry_rows(connection, entry.id)
                self._insert_entry_rows(connection, entry)

    def delete_entry(self, entry_id: str) -> None:
        with closing(self._connect()) as connection:
            with connection:
                self._delete_entry_rows(connection, entry_id)

    def rebuild(self, entries: Iterable[KnowledgeEntry]) -> KnowledgeReindexResult:
        indexed = 0
        failed = 0
        with closing(self._connect()) as connection:
            with connection:
                connection.execute("DELETE FROM knowledge_fts")
                connection.execute("DELETE FROM knowledge_index_meta")
                connection.execute("DELETE FROM knowledge_index_assets")
                connection.execute("DELETE FROM knowledge_index_tags")
                for entry in entries:
                    savepoint = f"entry_{indexed + failed}"
                    connection.execute(f"SAVEPOINT {savepoint}")
                    try:
                        self._delete_entry_rows(connection, entry.id)
                        self._insert_entry_rows(connection, entry)
                    except Exception:
                        connection.execute(f"ROLLBACK TO {savepoint}")
                        connection.execute(f"RELEASE {savepoint}")
                        failed += 1
                    else:
                        connection.execute(f"RELEASE {savepoint}")
                        indexed += 1
        return KnowledgeReindexResult(indexed=indexed, failed=failed)

    def search(self, filters: KnowledgeSearchFilters) -> list[KnowledgeSearchHit]:
        limit = _clamp_limit(filters.limit)
        offset = max(0, filters.offset)
        match_query = _build_match_query(filters.query)

        with closing(self._connect()) as connection:
            connection.row_factory = sqlite3.Row
            if match_query:
                rows = self._search_with_query(connection, filters, match_query, limit, offset)
            else:
                rows = self._search_without_query(connection, filters, limit, offset)

        return [
            KnowledgeSearchHit(entryId=str(row["entry_id"]), score=float(row["score"]))
            for row in rows
        ]

    def count(self, filters: KnowledgeSearchFilters) -> int:
        match_query = _build_match_query(filters.query)
        with closing(self._connect()) as connection:
            if match_query:
                return self._count_with_query(connection, filters, match_query)
            return self._count_without_query(connection, filters)

    def _initialize_schema(self) -> None:
        try:
            with closing(self._connect()) as connection:
                with connection:
                    connection.execute(
                        """
                        CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
                            entry_id UNINDEXED,
                            title,
                            summary,
                            problem,
                            diagnosis,
                            resolution,
                            commands_text,
                            assets_text,
                            tags_text,
                            source_text
                        )
                        """
                    )
                    connection.execute(
                        """
                        CREATE TABLE IF NOT EXISTS knowledge_index_meta (
                            entry_id TEXT PRIMARY KEY,
                            updated_at TEXT NOT NULL,
                            source_conversation_id TEXT,
                            source_conversation_title TEXT NOT NULL DEFAULT ''
                        )
                        """
                    )
                    connection.execute(
                        """
                        CREATE TABLE IF NOT EXISTS knowledge_index_assets (
                            entry_id TEXT NOT NULL,
                            asset_id INTEGER,
                            asset_label TEXT NOT NULL DEFAULT ''
                        )
                        """
                    )
                    connection.execute(
                        """
                        CREATE TABLE IF NOT EXISTS knowledge_index_tags (
                            entry_id TEXT NOT NULL,
                            tag TEXT NOT NULL
                        )
                        """
                    )
                    connection.execute(
                        "CREATE INDEX IF NOT EXISTS idx_knowledge_index_meta_updated_at "
                        "ON knowledge_index_meta(updated_at)"
                    )
                    connection.execute(
                        "CREATE INDEX IF NOT EXISTS idx_knowledge_index_meta_source_conversation_id "
                        "ON knowledge_index_meta(source_conversation_id)"
                    )
                    connection.execute(
                        "CREATE INDEX IF NOT EXISTS idx_knowledge_index_assets_asset_id "
                        "ON knowledge_index_assets(asset_id)"
                    )
                    connection.execute(
                        "CREATE INDEX IF NOT EXISTS idx_knowledge_index_tags_tag "
                        "ON knowledge_index_tags(tag)"
                    )
        except sqlite3.OperationalError as exc:
            if "fts5" in str(exc).lower() or "no such module" in str(exc).lower():
                raise RuntimeError("SQLite FTS5 is required for knowledge search.") from exc
            raise

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._index_path)

    def _search_with_query(
        self,
        connection: sqlite3.Connection,
        filters: KnowledgeSearchFilters,
        match_query: str,
        limit: int,
        offset: int,
    ) -> list[sqlite3.Row]:
        where_clauses = ["knowledge_fts MATCH ?"]
        params: list[object] = [match_query]
        self._append_filters(where_clauses, params, filters, "meta")

        sql = f"""
            SELECT
                knowledge_fts.entry_id AS entry_id,
                (
                    (-bm25(knowledge_fts) * 1000.0)
                    + {self._boost_expression(filters, 'meta')}
                ) AS score
            FROM knowledge_fts
            JOIN knowledge_index_meta AS meta ON meta.entry_id = knowledge_fts.entry_id
            WHERE {' AND '.join(where_clauses)}
            ORDER BY score DESC, meta.updated_at DESC, knowledge_fts.entry_id ASC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        return list(connection.execute(sql, params))

    def _search_without_query(
        self,
        connection: sqlite3.Connection,
        filters: KnowledgeSearchFilters,
        limit: int,
        offset: int,
    ) -> list[sqlite3.Row]:
        where_clauses = ["1 = 1"]
        params: list[object] = []
        self._append_filters(where_clauses, params, filters, "meta")

        sql = f"""
            SELECT
                meta.entry_id AS entry_id,
                {self._boost_expression(filters, 'meta')} AS score
            FROM knowledge_index_meta AS meta
            WHERE {' AND '.join(where_clauses)}
            ORDER BY score DESC, meta.updated_at DESC, meta.entry_id ASC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        return list(connection.execute(sql, params))

    def _count_with_query(
        self,
        connection: sqlite3.Connection,
        filters: KnowledgeSearchFilters,
        match_query: str,
    ) -> int:
        where_clauses = ["knowledge_fts MATCH ?"]
        params: list[object] = [match_query]
        self._append_filters(where_clauses, params, filters, "meta")
        row = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM knowledge_fts
            JOIN knowledge_index_meta AS meta ON meta.entry_id = knowledge_fts.entry_id
            WHERE {' AND '.join(where_clauses)}
            """,
            params,
        ).fetchone()
        return int(row[0]) if row else 0

    def _count_without_query(
        self,
        connection: sqlite3.Connection,
        filters: KnowledgeSearchFilters,
    ) -> int:
        where_clauses = ["1 = 1"]
        params: list[object] = []
        self._append_filters(where_clauses, params, filters, "meta")
        row = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM knowledge_index_meta AS meta
            WHERE {' AND '.join(where_clauses)}
            """,
            params,
        ).fetchone()
        return int(row[0]) if row else 0

    def _append_filters(
        self,
        where_clauses: list[str],
        params: list[object],
        filters: KnowledgeSearchFilters,
        meta_alias: str,
    ) -> None:
        if filters.asset_id is not None:
            where_clauses.append(
                "EXISTS ("
                "SELECT 1 FROM knowledge_index_assets AS filter_assets "
                f"WHERE filter_assets.entry_id = {meta_alias}.entry_id "
                "AND filter_assets.asset_id = ?"
                ")"
            )
            params.append(filters.asset_id)
        if filters.tag:
            where_clauses.append(
                "EXISTS ("
                "SELECT 1 FROM knowledge_index_tags AS filter_tags "
                f"WHERE filter_tags.entry_id = {meta_alias}.entry_id "
                "AND filter_tags.tag = ?"
                ")"
            )
            params.append(filters.tag)
        if filters.source_conversation_id is not None:
            where_clauses.append(f"{meta_alias}.source_conversation_id = ?")
            params.append(filters.source_conversation_id)

    def _boost_expression(self, filters: KnowledgeSearchFilters, meta_alias: str) -> str:
        asset_boost = "0.0"
        tag_boost = "0.0"
        source_boost = "0.0"
        if filters.asset_id is not None:
            asset_boost = (
                "CASE WHEN EXISTS ("
                "SELECT 1 FROM knowledge_index_assets AS boost_assets "
                f"WHERE boost_assets.entry_id = {meta_alias}.entry_id "
                f"AND boost_assets.asset_id = {int(filters.asset_id)}"
                ") THEN 3.0 ELSE 0.0 END"
            )
        if filters.tag:
            escaped_tag = filters.tag.replace("'", "''")
            tag_boost = (
                "CASE WHEN EXISTS ("
                "SELECT 1 FROM knowledge_index_tags AS boost_tags "
                f"WHERE boost_tags.entry_id = {meta_alias}.entry_id "
                f"AND boost_tags.tag = '{escaped_tag}'"
                ") THEN 2.0 ELSE 0.0 END"
            )
        if filters.source_conversation_id is not None:
            escaped_source = filters.source_conversation_id.replace("'", "''")
            source_boost = (
                "CASE WHEN "
                f"{meta_alias}.source_conversation_id = '{escaped_source}' "
                "THEN 1.5 ELSE 0.0 END"
            )
        recency_boost = (
            "(1.0 / (1.0 + "
            "(max(0.0, julianday('now') - julianday("
            f"{meta_alias}.updated_at)) / 30.0)))"
        )
        return f"({asset_boost} + {tag_boost} + {source_boost} + {recency_boost})"

    def _delete_entry_rows(self, connection: sqlite3.Connection, entry_id: str) -> None:
        connection.execute("DELETE FROM knowledge_fts WHERE entry_id = ?", (entry_id,))
        connection.execute("DELETE FROM knowledge_index_meta WHERE entry_id = ?", (entry_id,))
        connection.execute("DELETE FROM knowledge_index_assets WHERE entry_id = ?", (entry_id,))
        connection.execute("DELETE FROM knowledge_index_tags WHERE entry_id = ?", (entry_id,))

    def _insert_entry_rows(self, connection: sqlite3.Connection, entry: KnowledgeEntry) -> None:
        connection.execute(
            """
            INSERT INTO knowledge_fts (
                entry_id,
                title,
                summary,
                problem,
                diagnosis,
                resolution,
                commands_text,
                assets_text,
                tags_text,
                source_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.id,
                entry.title,
                entry.summary,
                entry.problem,
                entry.diagnosis,
                entry.resolution,
                _commands_text(entry),
                _assets_text(entry),
                " ".join(entry.tags),
                _source_text(entry),
            ),
        )
        connection.execute(
            """
            INSERT INTO knowledge_index_meta (
                entry_id,
                updated_at,
                source_conversation_id,
                source_conversation_title
            ) VALUES (?, ?, ?, ?)
            """,
            (
                entry.id,
                entry.updated_at,
                entry.source_conversation.id,
                entry.source_conversation.title,
            ),
        )
        connection.executemany(
            """
            INSERT INTO knowledge_index_assets (entry_id, asset_id, asset_label)
            VALUES (?, ?, ?)
            """,
            [
                (entry.id, asset.asset_id, asset.label)
                for asset in entry.assets
            ],
        )
        connection.executemany(
            """
            INSERT INTO knowledge_index_tags (entry_id, tag)
            VALUES (?, ?)
            """,
            [(entry.id, tag) for tag in entry.tags],
        )


def _build_match_query(query: str) -> str:
    tokens = _MATCH_TOKEN_PATTERN.findall(query)
    if not tokens:
        return ""
    return " OR ".join(f'"{token}"' for token in dict.fromkeys(tokens))


def _clamp_limit(limit: int) -> int:
    if limit <= 0:
        return _DEFAULT_LIMIT
    return min(limit, _MAX_LIMIT)


def _commands_text(entry: KnowledgeEntry) -> str:
    parts: list[str] = []
    for command in entry.commands:
        parts.extend([command.command, command.purpose, command.outcome])
    return " ".join(part for part in parts if part)


def _assets_text(entry: KnowledgeEntry) -> str:
    parts: list[str] = []
    for asset in entry.assets:
        if asset.asset_id is not None:
            parts.append(str(asset.asset_id))
        if asset.label:
            parts.append(asset.label)
    return " ".join(parts)


def _source_text(entry: KnowledgeEntry) -> str:
    parts = [
        entry.source_conversation.id or "",
        entry.source_conversation.title,
        entry.source_conversation.updated_at or "",
    ]
    for source in entry.sources:
        parts.extend(
            [
                source.conversation_id or "",
                source.event_id or "",
                str(source.event_index) if source.event_index is not None else "",
                source.event_type,
                source.quote,
                source.relevance,
            ]
        )
    return " ".join(part for part in parts if part)
