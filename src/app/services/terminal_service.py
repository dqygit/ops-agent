from functools import partial
from typing import Any, Awaitable, Callable, TypeVar, cast

import anyio
from starlette.websockets import WebSocketDisconnect

from app.core.connectors.context_bridge import build_terminal_context
from app.core.connectors.session_manager import TerminalSessionManager


T = TypeVar("T")
RunSyncCallable = Callable[..., Awaitable[T]]
run_sync = cast(RunSyncCallable[Any], getattr(anyio.to_thread, "run_sync"))


class TerminalService:
    def __init__(self, connector_factory, persistence):
        self._connector_factory = connector_factory
        self._persistence = persistence
        self._sessions = {}

    def open_session(self, asset):
        asset_id = getattr(asset, "id", None)
        if asset_id is None and isinstance(asset, dict):
            asset_id = asset.get("id")
        terminal_session_id = self._persistence.create_session(asset_id or 0)
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
            self._persistence.update_session(
                terminal_session_id,
                status="failed",
                last_error=str(exc),
            )
            self._persistence.record_event(terminal_session_id, "error", str(exc))
            return {"terminal_session_id": None, "channel": None, "error": str(exc)}
        self._sessions[terminal_session_id] = session_manager
        self._persistence.record_event(terminal_session_id, "connected", "")
        return {"terminal_session_id": terminal_session_id, "channel": "terminal connected", "error": ""}

    async def stream_session(self, terminal_session_id: int, websocket) -> None:
        session_manager = self.get_session(terminal_session_id)
        if session_manager is None:
            await websocket.close(code=1008)
            return
        await websocket.accept()
        closed = anyio.Event()
        send_lock = anyio.Lock()
        try:
            async with anyio.create_task_group() as task_group:
                task_group.start_soon(self._receive_websocket_input, terminal_session_id, session_manager, websocket, closed, send_lock)
                task_group.start_soon(self._send_terminal_output, terminal_session_id, session_manager, websocket, closed, send_lock)
        except WebSocketDisconnect:
            pass
        except Exception as exc:
            await run_sync(partial(self._persistence.update_session, terminal_session_id, status="failed", last_error=str(exc)))
            await run_sync(self._persistence.record_event, terminal_session_id, "error", str(exc))
            try:
                await websocket.send_json({"type": "error", "message": str(exc)})
            except Exception:
                pass
        finally:
            await run_sync(self.close_session, terminal_session_id)

    async def _receive_websocket_input(self, terminal_session_id: int, session_manager, websocket, closed, send_lock) -> None:
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
                await run_sync(self._persistence.record_event, terminal_session_id, message_type or "message", message)
        except WebSocketDisconnect:
            return
        finally:
            closed.set()

    async def _send_terminal_output(self, terminal_session_id: int, session_manager, websocket, closed, send_lock) -> None:
        while True:
            output = await run_sync(session_manager.read)
            if output:
                await run_sync(self._persistence.record_event, terminal_session_id, "terminal_output", output)
                try:
                    async with send_lock:
                        await websocket.send_json({"type": "output", "data": output})
                except WebSocketDisconnect:
                    closed.set()
                    return
            if closed.is_set():
                final_output = await run_sync(session_manager.read)
                if final_output:
                    await run_sync(self._persistence.record_event, terminal_session_id, "terminal_output", final_output)
                    async with send_lock:
                        await websocket.send_json({"type": "output", "data": final_output})
                return
            await anyio.sleep(0.02)

    def close_session(self, terminal_session_id: int) -> bool:
        session_manager = self._sessions.pop(terminal_session_id, None)
        if session_manager is None:
            return False
        session_manager.close()
        self._persistence.update_session(terminal_session_id, status="disconnected", ended=True)
        self._persistence.record_event(terminal_session_id, "disconnected", "")
        return True

    def get_session(self, terminal_session_id: int):
        return self._sessions.get(terminal_session_id)

    def send_input(self, terminal_session_id: int, data: str) -> None:
        session_manager = self.get_session(terminal_session_id)
        if session_manager is None:
            raise ValueError("terminal session not found")
        session_manager.write(data)
        self._persistence.record_event(terminal_session_id, "input", data)

    def read_recent_output(self, terminal_session_id: int) -> str:
        session_manager = self.get_session(terminal_session_id)
        if session_manager is None:
            return ""
        output = session_manager.read()
        if output:
            self._persistence.record_event(terminal_session_id, "terminal_output", output)
        return output

    def attach_context(self, terminal_session_id: int, selection_label: str, selected_text: str):
        attachment = build_terminal_context(terminal_session_id, selection_label, selected_text)
        self._persistence.record_event(
            terminal_session_id,
            "context_attached",
            {"selection_label": selection_label, "selected_text": selected_text},
        )
        return attachment
