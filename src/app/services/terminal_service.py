from collections import deque
from functools import partial
from typing import Any, Awaitable, Callable, TypeVar, cast

import anyio
from starlette.websockets import WebSocketDisconnect

from app.core.connectors.context_bridge import build_terminal_context
from app.core.connectors.session_manager import TerminalSessionManager


T = TypeVar("T")
RunSyncCallable = Callable[..., Awaitable[T]]
run_sync = cast(RunSyncCallable[Any], getattr(anyio.to_thread, "run_sync"))


import uuid

class TerminalService:
    def __init__(self, connector_factory, persistence=None):
        self._connector_factory = connector_factory
        self._sessions = {}
        self._output_buffers: dict[str, deque[tuple[int, str]]] = {}
        self._output_sequences: dict[str, int] = {}

    def open_session(self, asset):
        terminal_id = str(uuid.uuid4())
        connector = None
        session_manager = None
        try:
            connector = self._connector_factory(asset)
            session_manager = TerminalSessionManager(connector)
            session_manager.open()
        except Exception as exc:
            if session_manager is not None and session_manager.is_open:
                session_manager.close()
            elif connector is not None:
                connector.close()
            return {"terminal_id": None, "channel": None, "error": str(exc)}
        self._sessions[terminal_id] = session_manager
        self._output_buffers[terminal_id] = deque(maxlen=2000)
        self._output_sequences[terminal_id] = 0
        return {"terminal_id": terminal_id, "channel": "terminal connected", "error": ""}

    async def stream_session(self, terminal_id: str, websocket) -> None:
        session_manager = self.get_session(terminal_id)
        if session_manager is None:
            await websocket.close(code=1008)
            return
        await websocket.accept()
        closed = anyio.Event()
        send_lock = anyio.Lock()
        try:
            async with anyio.create_task_group() as task_group:
                task_group.start_soon(self._receive_websocket_input, terminal_id, session_manager, websocket, closed, send_lock)
                task_group.start_soon(self._send_terminal_output, terminal_id, session_manager, websocket, closed, send_lock)
        except WebSocketDisconnect:
            pass
        except Exception as exc:
            try:
                await websocket.send_json({"type": "error", "message": str(exc)})
            except Exception:
                pass
        finally:
            await run_sync(self.close_session, terminal_id)

    async def _receive_websocket_input(self, terminal_id: str, session_manager, websocket, closed, send_lock) -> None:
        try:
            while True:
                message = await websocket.receive_json()
                message_type = message.get("type")
                if message_type == "input":
                    await run_sync(session_manager.write, message.get("data", ""))
                elif message_type == "resize":
                    try:
                        cols = int(message.get("cols", 80))
                        rows = int(message.get("rows", 24))
                    except (TypeError, ValueError):
                        async with send_lock:
                            await websocket.send_json({"type": "error", "message": "invalid terminal size"})
                        continue
                    await run_sync(session_manager.resize, cols, rows)
                elif message_type == "close":
                    async with send_lock:
                        await websocket.send_json({"type": "closed"})
                    return
        except WebSocketDisconnect:
            return
        finally:
            closed.set()

    async def _send_terminal_output(self, terminal_id: str, session_manager, websocket, closed, send_lock) -> None:
        while True:
            output = await run_sync(session_manager.read)
            if output:
                await run_sync(self._append_output, terminal_id, output)
                try:
                    async with send_lock:
                        await websocket.send_json({"type": "output", "data": output})
                except WebSocketDisconnect:
                    closed.set()
                    return
            if closed.is_set():
                final_output = await run_sync(session_manager.read)
                if final_output:
                    await run_sync(self._append_output, terminal_id, final_output)
                    async with send_lock:
                        await websocket.send_json({"type": "output", "data": final_output})
                return
            await anyio.sleep(0.02)

    def close_session(self, terminal_id: str) -> bool:
        session_manager = self._sessions.pop(terminal_id, None)
        if session_manager is None:
            return False
        self._output_buffers.pop(terminal_id, None)
        self._output_sequences.pop(terminal_id, None)
        session_manager.close()
        return True

    def get_session(self, terminal_id: str):
        return self._sessions.get(terminal_id)

    def send_input(self, terminal_id: str, data: str) -> None:
        session_manager = self.get_session(terminal_id)
        if session_manager is None:
            raise ValueError("terminal session not found")
        session_manager.write(data)

    def read_recent_output(self, terminal_id: str) -> str:
        session_manager = self.get_session(terminal_id)
        if session_manager is None:
            return ""
        output = session_manager.read()
        if output:
            self._append_output(terminal_id, output)
        return output

    def get_output_cursor(self, terminal_id: str) -> int:
        return self._output_sequences.get(terminal_id, 0)

    def read_output_since(self, terminal_id: str, cursor: int) -> tuple[int, str]:
        if terminal_id not in self._sessions:
            return cursor, ""
        chunks = self._output_buffers.get(terminal_id)
        if not chunks:
            return self._output_sequences.get(terminal_id, cursor), ""
        latest_cursor = cursor
        output_parts: list[str] = []
        for sequence, chunk in chunks:
            if sequence > cursor:
                output_parts.append(chunk)
                latest_cursor = sequence
        return latest_cursor, "".join(output_parts)

    def _append_output(self, terminal_id: str, output: str) -> None:
        if not output:
            return
        sequence = self._output_sequences.get(terminal_id, 0) + 1
        self._output_sequences[terminal_id] = sequence
        self._output_buffers.setdefault(terminal_id, deque(maxlen=2000)).append((sequence, output))

    def attach_context(self, terminal_id: str, selection_label: str, selected_text: str):
        attachment = build_terminal_context(terminal_id, selection_label, selected_text)
        return attachment
