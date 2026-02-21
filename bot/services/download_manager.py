import logging

from aiogram import Bot
from aiogram.enums import ParseMode

from aria2_client import Aria2Client
from services.progress_updater import ProgressUpdater
from utils.formatting import format_completed, format_error

logger = logging.getLogger(__name__)


class DownloadManager:
    def __init__(
        self, bot: Bot, aria2: Aria2Client, progress: ProgressUpdater
    ) -> None:
        self._bot = bot
        self._aria2 = aria2
        self._progress = progress

        self._aria2.on_complete(self._handle_complete)
        self._aria2.on_error(self._handle_error)

    async def _handle_complete(self, trigger: dict) -> None:
        gid = trigger.get("gid") or (
            trigger.get("params", [{}])[0].get("gid")
            if trigger.get("params")
            else None
        )
        if not gid:
            return

        loc = self._progress.untrack(gid)
        if not loc:
            return

        chat_id, msg_id = loc
        try:
            status = await self._aria2.tell_status(gid)
            text = format_completed(status)
        except Exception:
            text = f"\u2705 Download complete (GID: <code>{gid}</code>)"

        try:
            await self._bot.edit_message_text(
                text=text,
                chat_id=chat_id,
                message_id=msg_id,
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            logger.exception("Failed to edit complete message for %s", gid)

    async def _handle_error(self, trigger: dict) -> None:
        gid = trigger.get("gid") or (
            trigger.get("params", [{}])[0].get("gid")
            if trigger.get("params")
            else None
        )
        if not gid:
            return

        loc = self._progress.untrack(gid)
        if not loc:
            return

        chat_id, msg_id = loc
        try:
            status = await self._aria2.tell_status(gid)
            text = format_error(status)
        except Exception:
            text = f"\u274C Download failed (GID: <code>{gid}</code>)"

        try:
            await self._bot.edit_message_text(
                text=text,
                chat_id=chat_id,
                message_id=msg_id,
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            logger.exception("Failed to edit error message for %s", gid)
