"""
kairo-sidecar/sidecar/cua/vlm_download_manager.py

Async GGUF model download manager for Kairo Phantom VLM.

Key behaviors (from briefing Doc 01 §1):
  - No bundled model — download on first CUA activation
  - Background async download, comparable to a game patch (~4.2 GB)
  - While downloading: CUA works in keyboard-only mode via WellKnownShortcut templates
  - Tray progress indicator via named pipe notification to Rust daemon
  - Shared model cache at ~/.kairo-phantom/models/
  - Resume-capable download (range requests)

Hardware-adaptive:
  - ≥6 GB VRAM → 7B Q4_K_M (4.2 GB)
  - <6 GB VRAM → 3B Q4_K_M (2.0 GB)
  - CPU-only still runs (3–5 sec/screenshot)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import subprocess
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

import httpx

from .vlm_config import VlmConfig, VlmModelSpec, get_vlm_config, write_modelfile

logger = logging.getLogger(__name__)


# ─── Download State ───────────────────────────────────────────────────────────

class DownloadState(str, Enum):
    NOT_STARTED = "not_started"
    DOWNLOADING = "downloading"
    COMPLETE = "complete"
    FAILED = "failed"
    VERIFYING = "verifying"


@dataclass
class DownloadProgress:
    state: DownloadState
    bytes_downloaded: int = 0
    total_bytes: int = 0
    speed_mbps: float = 0.0
    eta_seconds: float = 0.0
    error: Optional[str] = None

    @property
    def percent(self) -> float:
        if self.total_bytes <= 0:
            return 0.0
        return min(100.0, (self.bytes_downloaded / self.total_bytes) * 100)

    @property
    def is_complete(self) -> bool:
        return self.state == DownloadState.COMPLETE

    @property
    def is_active(self) -> bool:
        return self.state in (DownloadState.DOWNLOADING, DownloadState.VERIFYING)


import queue

# ─── Tray Notifier ────────────────────────────────────────────────────────────

class TrayProgressNotifier:
    """
    Notifies the Rust daemon of download progress via the named pipe.
    The daemon renders a tray progress indicator.
    """
    PIPE_NAME = r"\\.\pipe\kairo"

    def __init__(self) -> None:
        self._queue = queue.Queue(maxsize=10)
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()

    def notify(self, progress: DownloadProgress) -> None:
        """Send download progress to Rust tray via named pipe (best-effort)."""
        try:
            payload = json.dumps({
                "type": "vlm_download_progress",
                "state": progress.state.value,
                "percent": round(progress.percent, 1),
                "speed_mbps": round(progress.speed_mbps, 1),
                "eta_seconds": int(progress.eta_seconds),
                "error": progress.error,
            })
            try:
                self._queue.put_nowait(payload)
            except queue.Full:
                try:
                    self._queue.get_nowait()
                    self._queue.put_nowait(payload)
                except queue.Empty:
                    pass
        except Exception as e:
            logger.debug(f"Tray notify failed (non-fatal): {e}")

    def _worker(self) -> None:
        while True:
            try:
                payload = self._queue.get()
                self._write_to_pipe(payload)
                self._queue.task_done()
            except Exception:
                time.sleep(0.1)

    def _write_to_pipe(self, payload: str) -> None:
        try:
            import win32file  # type: ignore
            handle = win32file.CreateFile(
                self.PIPE_NAME,
                win32file.GENERIC_WRITE,
                0, None,
                win32file.OPEN_EXISTING,
                0, None,
            )
            win32file.WriteFile(handle, (payload + "\n").encode())
            win32file.CloseHandle(handle)
        except Exception:
            pass  # Tray notification is best-effort


# ─── Download Manager ─────────────────────────────────────────────────────────

class VlmDownloadManager:
    """
    Manages async download of the GGUF model file.

    Usage:
        manager = VlmDownloadManager(config)
        await manager.ensure_model_available(on_progress=callback)

    The download is resume-capable — if partially downloaded, it resumes
    from where it stopped using HTTP range requests.
    """

    # Hugging Face CDN base URL
    HF_BASE = "https://huggingface.co/{repo}/resolve/main/{filename}"

    def __init__(
        self,
        config: VlmConfig,
        notifier: Optional[TrayProgressNotifier] = None,
    ) -> None:
        self.config = config
        self.notifier = notifier or TrayProgressNotifier()
        self._progress = DownloadProgress(state=DownloadState.NOT_STARTED)
        self._lock = asyncio.Lock()

    @property
    def progress(self) -> DownloadProgress:
        return self._progress

    @property
    def is_model_ready(self) -> bool:
        """Check if the model file is downloaded and ready for Ollama."""
        return self.config.is_downloaded

    async def ensure_model_available(
        self,
        on_progress: Optional[Callable[[DownloadProgress], None]] = None,
    ) -> bool:
        """
        Ensure the model is available. Downloads if missing.
        
        Args:
            on_progress: Optional callback for progress updates
        
        Returns:
            True if model is ready, False if download failed
        """
        async with self._lock:
            if self.is_model_ready:
                self._progress = DownloadProgress(state=DownloadState.COMPLETE)
                logger.info(f"VLM model already available: {self.config.model_path}")
                return True

            logger.info(
                f"VLM model not found — starting download: "
                f"{self.config.selected_model.description} "
                f"({self.config.selected_model.size_gb:.1f} GB)"
            )
            success = await self._download_model(on_progress)

            if success:
                await self._register_with_ollama()

            return success

    async def _download_model(
        self,
        on_progress: Optional[Callable[[DownloadProgress], None]] = None,
    ) -> bool:
        """Download the GGUF file with progress tracking and resume support."""
        model = self.config.selected_model
        dest_path = self.config.model_path
        tmp_path = dest_path.with_suffix(".gguf.tmp")

        url = self.HF_BASE.format(repo=model.hf_repo, filename=model.hf_filename)

        # Resume from partial download
        resume_pos = tmp_path.stat().st_size if tmp_path.exists() else 0
        headers = {}
        if resume_pos > 0:
            headers["Range"] = f"bytes={resume_pos}-"
            logger.info(f"Resuming download from byte {resume_pos:,}")

        self._progress = DownloadProgress(
            state=DownloadState.DOWNLOADING,
            bytes_downloaded=resume_pos,
        )

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=300.0)) as client:
                async with client.stream("GET", url, headers=headers, follow_redirects=True) as resp:
                    resp.raise_for_status()

                    # Determine total size
                    if "content-range" in resp.headers:
                        # Range response: Content-Range: bytes 1000-9999/10000
                        total = int(resp.headers["content-range"].split("/")[-1])
                    elif "content-length" in resp.headers:
                        total = resume_pos + int(resp.headers["content-length"])
                    else:
                        total = int(model.size_gb * 1024 * 1024 * 1024)

                    self._progress.total_bytes = total

                    start_time = time.monotonic()
                    last_notify = start_time

                    mode = "ab" if resume_pos > 0 else "wb"
                    with open(tmp_path, mode) as f:
                        async for chunk in resp.aiter_bytes(chunk_size=1 << 20):  # 1 MB chunks
                            f.write(chunk)
                            self._progress.bytes_downloaded += len(chunk)

                            # Update speed + ETA
                            elapsed = time.monotonic() - start_time
                            if elapsed > 0:
                                downloaded_this_session = self._progress.bytes_downloaded - resume_pos
                                speed_bps = downloaded_this_session / elapsed
                                self._progress.speed_mbps = speed_bps / (1024 * 1024)
                                remaining = total - self._progress.bytes_downloaded
                                self._progress.eta_seconds = (
                                    remaining / speed_bps if speed_bps > 0 else 0
                                )

                            # Throttle notifications to 1/sec
                            now = time.monotonic()
                            if now - last_notify >= 1.0:
                                last_notify = now
                                self.notifier.notify(self._progress)
                                if on_progress:
                                    on_progress(self._progress)

            # Rename tmp → final
            tmp_path.rename(dest_path)
            logger.info(f"Download complete: {dest_path}")
            return True

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.request.url}"
            logger.error(f"VLM download failed: {error_msg}")
            self._progress = DownloadProgress(
                state=DownloadState.FAILED,
                error=error_msg,
            )
            self.notifier.notify(self._progress)
            return False

        except Exception as e:
            error_msg = str(e)
            logger.error(f"VLM download error: {error_msg}", exc_info=True)
            self._progress = DownloadProgress(
                state=DownloadState.FAILED,
                error=error_msg,
            )
            self.notifier.notify(self._progress)
            return False

    async def _register_with_ollama(self) -> bool:
        """
        Register the downloaded model with Ollama via `ollama create kairo-vlm`.
        This writes the Modelfile and runs the creation command.
        """
        try:
            modelfile_path = write_modelfile(self.config)
            logger.info(f"Registering model with Ollama: {self.config.selected_model.ollama_name}")

            proc = await asyncio.create_subprocess_exec(
                "ollama", "create", self.config.selected_model.ollama_name,
                "-f", str(modelfile_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120.0)

            if proc.returncode == 0:
                logger.info(f"Ollama model registered: {self.config.selected_model.ollama_name}")
                self._progress = DownloadProgress(state=DownloadState.COMPLETE)
                self.notifier.notify(self._progress)
                return True
            else:
                error = stderr.decode().strip()
                logger.error(f"Ollama create failed: {error}")
                self._progress = DownloadProgress(
                    state=DownloadState.FAILED,
                    error=f"ollama create failed: {error}",
                )
                self.notifier.notify(self._progress)
                return False

        except asyncio.TimeoutError:
            logger.error("Ollama model registration timed out")
            return False
        except FileNotFoundError:
            logger.error("Ollama not found — ensure Ollama is installed")
            return False
        except Exception as e:
            logger.error(f"Model registration error: {e}", exc_info=True)
            return False


# ─── Background Download ──────────────────────────────────────────────────────

class BackgroundVlmDownloader:
    """
    Initiates model download in a background thread, allowing CUA to run in
    keyboard-only mode while the model downloads.

    Usage:
        downloader = BackgroundVlmDownloader()
        downloader.start()            # non-blocking
        if downloader.is_ready:       # check later
            ...
    """

    def __init__(self) -> None:
        self.config = get_vlm_config()
        self.manager = VlmDownloadManager(self.config)
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    @property
    def is_ready(self) -> bool:
        return self.manager.is_model_ready

    @property
    def is_downloading(self) -> bool:
        return self.manager.progress.is_active

    @property
    def download_progress(self) -> DownloadProgress:
        return self.manager.progress

    def start(self, on_progress: Optional[Callable[[DownloadProgress], None]] = None) -> None:
        """Start background download (no-op if already downloading or complete)."""
        if self.is_ready or self.is_downloading:
            return
        self._thread = threading.Thread(
            target=self._run_async_download,
            args=(on_progress,),
            name="kairo-vlm-download",
            daemon=True,
        )
        self._thread.start()
        logger.info("VLM background download started")

    def _run_async_download(self, on_progress: Optional[Callable] = None) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(
                self.manager.ensure_model_available(on_progress=on_progress)
            )
        finally:
            self._loop.close()


# ─── Singleton ────────────────────────────────────────────────────────────────

_downloader: Optional[BackgroundVlmDownloader] = None


def get_background_downloader() -> BackgroundVlmDownloader:
    """Get (or create) the singleton background downloader."""
    global _downloader
    if _downloader is None:
        _downloader = BackgroundVlmDownloader()
    return _downloader
