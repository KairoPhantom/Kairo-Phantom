import asyncio
import json
import logging
import sys
import traceback
from typing import Callable, Coroutine, Any

log = logging.getLogger("kairo-sidecar.ipc")

class NamedPipeProtocol(asyncio.Protocol):
    def __init__(self, handler: Callable[[dict], Coroutine[Any, Any, dict]]):
        self.handler = handler
        self.transport = None
        self.buffer = b""

    def connection_made(self, transport):
        self.transport = transport
        log.info("Client connected to named pipe")

    def data_received(self, data):
        self.buffer += data
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            asyncio.create_task(self._process_line(line))

    async def _process_line(self, line: bytes):
        if not line.strip():
            return
        try:
            req = json.loads(line.decode("utf-8").strip())
            resp = await self.handler(req)
            resp_bytes = (json.dumps(resp) + "\n").encode("utf-8")
            if self.transport:
                self.transport.write(resp_bytes)
        except Exception as e:
            log.error(f"Error handling line: {e}\n{traceback.format_exc()}")
            try:
                err_resp = {"ok": False, "error": str(e), "traceback": traceback.format_exc()}
                if self.transport:
                    self.transport.write((json.dumps(err_resp) + "\n").encode("utf-8"))
            except Exception:
                pass

    def connection_lost(self, exc):
        log.info(f"Client disconnected from named pipe: {exc}")
        self.transport = None


async def start_named_pipe_server(pipe_name: str, handler: Callable[[dict], Coroutine[Any, Any, dict]]):
    """Starts the Windows Named Pipe server using asyncio ProactorEventLoop."""
    loop = asyncio.get_running_loop()
    if not sys.platform.startswith("win"):
        # Fallback to local TCP on non-Windows platforms for development/tests compatibility
        raise OSError("Named Pipe IPC is only supported on Windows")

    log.info(f"Binding to Named Pipe: {pipe_name}")
    
    # ProactorEventLoop has start_serving_pipe
    try:
        server = await loop.start_serving_pipe(
            lambda: NamedPipeProtocol(handler),
            pipe_name
        )
        return server
    except AttributeError:
        log.error("Active event loop does not support Named Pipes (must use ProactorEventLoop on Windows)")
        raise RuntimeError("ProactorEventLoop required for Windows Named Pipes")
