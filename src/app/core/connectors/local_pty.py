import os
import platform
import select


def _resolve_windows_shell() -> str:
    pwsh_path = os.environ.get("OPS_AGENT_PWSH_PATH")
    if pwsh_path:
        return pwsh_path

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    candidate_paths = [
        os.path.join(local_app_data, "Microsoft", "WindowsApps", "pwsh.exe") if local_app_data else "",
        r"C:\Program Files\PowerShell\7\pwsh.exe",
        r"C:\Program Files (x86)\PowerShell\7\pwsh.exe",
        r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
    ]

    for candidate in candidate_paths:
        if candidate and os.path.exists(candidate):
            return candidate

    return os.environ.get("COMSPEC") or "cmd.exe"


class LocalPtyConnector:
    def __init__(self, *, cols: int = 80, rows: int = 24):
        self.cols = cols
        self.rows = rows
        self._process = None
        self._pid = None
        self._fd = None

    def run_command(self, command: str) -> str:
        raise NotImplementedError("local terminal command execution requires an interactive session")

    def open_interactive(self) -> str:
        if platform.system() == "Windows":
            return self._open_windows()
        return self._open_posix()

    def read(self) -> str:
        if platform.system() == "Windows":
            return self._read_windows()
        return self._read_posix()

    def write(self, data: str) -> None:
        if platform.system() == "Windows":
            if self._process is None:
                return
            self._process.write(data)
            return
        if self._fd is not None:
            os.write(self._fd, data.encode(errors="ignore"))

    def resize(self, cols: int, rows: int) -> None:
        self.cols = cols
        self.rows = rows
        if platform.system() == "Windows":
            self._resize_windows(cols, rows)
            return
        self._resize_posix(cols, rows)

    def close(self) -> None:
        if platform.system() == "Windows":
            if self._process is not None:
                self._process.terminate()
                self._process = None
            return
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
        if self._pid is not None:
            try:
                os.kill(self._pid, 15)
                os.waitpid(self._pid, 0)
            except ChildProcessError:
                pass
            except ProcessLookupError:
                pass
            self._pid = None

    def _open_windows(self) -> str:
        try:
            winpty = __import__("winpty", fromlist=["PtyProcess"])
        except ImportError as exc:
            raise RuntimeError("pywinpty is required for local terminal sessions on Windows") from exc
        PtyProcess = winpty.PtyProcess
        shell = _resolve_windows_shell()
        self._process = PtyProcess.spawn(shell, dimensions=(self.rows, self.cols))
        return "local terminal connected"

    def _read_windows(self) -> str:
        if self._process is None:
            return ""
        try:
            return self._process.read(4096)
        except EOFError:
            return ""

    def _resize_windows(self, cols: int, rows: int) -> None:
        if self._process is None:
            return
        for method_name in ("setwinsize", "set_size", "resize"):
            method = getattr(self._process, method_name, None)
            if method is None:
                continue
            try:
                method(rows, cols)
            except TypeError:
                method(cols, rows)
            return

    def _open_posix(self) -> str:
        import pty

        shell = os.environ.get("SHELL") or "/bin/sh"
        env = os.environ.copy()
        # Disable some shell extensions that might cause issues in PTY
        env["ZSH_AUTOSUGGEST_MANUAL_REBIND"] = "1"
        env["TERM"] = "xterm-256color"

        self._pid, self._fd = pty.fork()
        if self._pid == 0:
            os.execvpe(shell, [shell], env)
        self._resize_posix(self.cols, self.rows)
        return "local terminal connected"

    def _read_posix(self) -> str:
        if self._fd is None:
            return ""
        readable, _, _ = select.select([self._fd], [], [], 0.05)
        if not readable:
            return ""
        try:
            return os.read(self._fd, 4096).decode(errors="ignore")
        except OSError:
            return ""

    def _resize_posix(self, cols: int, rows: int) -> None:
        if self._fd is None:
            return
        import fcntl
        import struct
        import termios

        size = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(self._fd, termios.TIOCSWINSZ, size)
