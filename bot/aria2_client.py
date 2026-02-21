import asyncio
import logging
from typing import Any, Callable, Coroutine

from aioaria2 import Aria2WebsocketClient

from config import settings

logger = logging.getLogger(__name__)

EventCallback = Callable[[dict], Coroutine[Any, Any, None]]


class Aria2Client:
    def __init__(self) -> None:
        self._client: Aria2WebsocketClient | None = None
        self._on_complete: EventCallback | None = None
        self._on_error: EventCallback | None = None

    async def connect(self, max_retries: int = 30, delay: float = 2.0) -> None:
        for attempt in range(1, max_retries + 1):
            try:
                url = settings.aria2_rpc_url
                secret = settings.aria2_rpc_secret
                self._client = await Aria2WebsocketClient.new(
                    url, token=secret
                )
                logger.info("Connected to aria2 RPC")

                if self._on_complete:
                    self._client.onDownloadComplete(self._on_complete)
                if self._on_error:
                    self._client.onDownloadError(self._on_error)

                return
            except Exception as e:
                logger.warning(
                    "aria2 connect attempt %d/%d failed: %s",
                    attempt,
                    max_retries,
                    e,
                )
                if attempt < max_retries:
                    await asyncio.sleep(delay)
        raise ConnectionError("Failed to connect to aria2 RPC after retries")

    async def disconnect(self) -> None:
        if self._client:
            # aioaria2 closes the WS on context exit; we just drop the ref
            self._client = None

    def on_complete(self, callback: EventCallback) -> None:
        self._on_complete = callback
        if self._client:
            self._client.onDownloadComplete(callback)

    def on_error(self, callback: EventCallback) -> None:
        self._on_error = callback
        if self._client:
            self._client.onDownloadError(callback)

    async def add_uri(self, uris: list[str], options: dict | None = None) -> str:
        return await self._client.addUri(uris, options=options or {})

    async def tell_status(self, gid: str) -> dict:
        return await self._client.tellStatus(gid)

    async def tell_active(self) -> list[dict]:
        return await self._client.tellActive()

    async def tell_waiting(self, offset: int = 0, num: int = 100) -> list[dict]:
        return await self._client.tellWaiting(offset, num)

    async def tell_stopped(self, offset: int = 0, num: int = 100) -> list[dict]:
        return await self._client.tellStopped(offset, num)

    async def pause(self, gid: str) -> str:
        return await self._client.pause(gid)

    async def unpause(self, gid: str) -> str:
        return await self._client.unpause(gid)

    async def remove(self, gid: str) -> str:
        return await self._client.remove(gid)

    async def force_remove(self, gid: str) -> str:
        return await self._client.forceRemove(gid)

    async def pause_all(self) -> str:
        return await self._client.pauseAll()

    async def unpause_all(self) -> str:
        return await self._client.unpauseAll()

    async def add_torrent(self, torrent_base64: str, options: dict | None = None) -> str:
        params: list = [torrent_base64, []]
        if options:
            params.append(options)
        return await self._client.jsonrpc("addTorrent", params)

    async def change_option(self, gid: str, options: dict) -> str:
        return await self._client.changeOption(gid, options)

    async def get_files(self, gid: str) -> list[dict]:
        return await self._client.getFiles(gid)

    async def get_global_stat(self) -> dict:
        return await self._client.getGlobalStat()
