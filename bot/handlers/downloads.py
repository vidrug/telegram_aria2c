import logging
import re

from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from aiogram.enums import ParseMode

from aria2_client import Aria2Client
from services.progress_updater import ProgressUpdater
from utils.formatting import format_progress

logger = logging.getLogger(__name__)
router = Router()

URL_RE = re.compile(
    r"https?://[^\s<>\"']+|magnet:\?[^\s<>\"']+", re.IGNORECASE
)


@router.message(Command("cancel"))
async def cmd_cancel(
    message: Message, command: CommandObject, aria2: Aria2Client
) -> None:
    gid = (command.args or "").strip()
    if not gid:
        await message.answer("Usage: /cancel &lt;gid&gt;", parse_mode=ParseMode.HTML)
        return
    try:
        await aria2.force_remove(gid)
        await message.answer(f"\u274C Cancelled <code>{gid}</code>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await message.answer(f"Error: {e}")


@router.message(Command("pause"))
async def cmd_pause(
    message: Message, command: CommandObject, aria2: Aria2Client
) -> None:
    gid = (command.args or "").strip()
    if not gid:
        await message.answer("Usage: /pause &lt;gid&gt;", parse_mode=ParseMode.HTML)
        return
    try:
        await aria2.pause(gid)
        await message.answer(f"\u23F8 Paused <code>{gid}</code>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await message.answer(f"Error: {e}")


@router.message(Command("resume"))
async def cmd_resume(
    message: Message, command: CommandObject, aria2: Aria2Client
) -> None:
    gid = (command.args or "").strip()
    if not gid:
        await message.answer("Usage: /resume &lt;gid&gt;", parse_mode=ParseMode.HTML)
        return
    try:
        await aria2.unpause(gid)
        await message.answer(f"\u25B6 Resumed <code>{gid}</code>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await message.answer(f"Error: {e}")


@router.message(Command("pauseall"))
async def cmd_pause_all(message: Message, aria2: Aria2Client) -> None:
    await aria2.pause_all()
    await message.answer("\u23F8 All downloads paused.")


@router.message(Command("resumeall"))
async def cmd_resume_all(message: Message, aria2: Aria2Client) -> None:
    await aria2.unpause_all()
    await message.answer("\u25B6 All downloads resumed.")


@router.message(Command("cancelall"))
async def cmd_cancel_all(message: Message, aria2: Aria2Client) -> None:
    active = await aria2.tell_active()
    waiting = await aria2.tell_waiting()
    for d in active + waiting:
        gid = d.get("gid")
        if gid:
            try:
                await aria2.force_remove(gid)
            except Exception:
                pass
    await message.answer("\u274C All downloads cancelled.")


@router.message(F.text)
async def handle_url(
    message: Message,
    aria2: Aria2Client,
    progress_updater: ProgressUpdater,
) -> None:
    urls = URL_RE.findall(message.text or "")
    if not urls:
        return

    for url in urls:
        try:
            gid = await aria2.add_uri([url])
        except Exception as e:
            await message.answer(f"\u274C Failed to add download: {e}")
            continue

        try:
            status = await aria2.tell_status(gid)
            text = format_progress(status)
        except Exception:
            text = f"\U0001F4E5 Download added\nGID: <code>{gid}</code>"

        sent = await message.answer(text, parse_mode=ParseMode.HTML)
        progress_updater.track(gid, sent.chat.id, sent.message_id)
