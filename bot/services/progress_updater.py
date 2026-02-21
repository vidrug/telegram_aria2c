import asyncio
import logging

from aiogram import Bot
from aiogram.enums import ParseMode

from aria2_client import Aria2Client
from callback_types import DownloadAction
from utils.formatting import format_progress

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)


def _progress_keyboard(gid: str, status: str) -> InlineKeyboardMarkup:
    buttons = []
    if status == "active":
        buttons.append(
            InlineKeyboardButton(
                text="\u23F8 Pause",
                callback_data=DownloadAction(action="pause", gid=gid).pack(),
            )
        )
    elif status == "paused":
        buttons.append(
            InlineKeyboardButton(
                text="\u25B6 Resume",
                callback_data=DownloadAction(action="resume", gid=gid).pack(),
            )
        )
    buttons.append(
        InlineKeyboardButton(
            text="\u274C Cancel",
            callback_data=DownloadAction(action="cancel", gid=gid).pack(),
        )
    )
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


class ProgressUpdater:
    def __init__(self, bot: Bot, aria2: Aria2Client, interval: int = 5) -> None:
        self._bot = bot
        self._aria2 = aria2
        self._interval = interval
        # gid -> (chat_id, message_id)
        self._tracked: dict[str, tuple[int, int]] = {}
        self._task: asyncio.Task | None = None

    def track(self, gid: str, chat_id: int, message_id: int) -> None:
        self._tracked[gid] = (chat_id, message_id)

    def untrack(self, gid: str) -> tuple[int, int] | None:
        return self._tracked.pop(gid, None)

    def get(self, gid: str) -> tuple[int, int] | None:
        return self._tracked.get(gid)

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(self._interval)
            try:
                await self._update_all()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Progress update error")

    async def _update_all(self) -> None:
        if not self._tracked:
            return

        for gid, (chat_id, msg_id) in list(self._tracked.items()):
            try:
                status = await self._aria2.tell_status(gid)
            except Exception:
                logger.warning("Failed to get status for %s", gid)
                continue

            state = status.get("status")
            if state in ("complete", "error", "removed"):
                continue

            text = format_progress(status)
            kb = _progress_keyboard(gid, state)
            try:
                await self._bot.edit_message_text(
                    text=text,
                    chat_id=chat_id,
                    message_id=msg_id,
                    parse_mode=ParseMode.HTML,
                    reply_markup=kb,
                )
            except Exception:
                pass  # message not modified or deleted
