import base64
import logging
import re

from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from aiogram.enums import ParseMode

from aria2_client import Aria2Client
from callback_types import TorrentAction
from services.progress_updater import ProgressUpdater
from utils.formatting import format_progress, format_torrent_info, format_file_list

logger = logging.getLogger(__name__)
router = Router()

URL_RE = re.compile(
    r"https?://[^\s<>\"']+|magnet:\?[^\s<>\"']+", re.IGNORECASE
)

FILE_SELECT_RE = re.compile(r"^[\d,\s\-]+$")


def _parse_file_indices(text: str) -> set[int]:
    """Parse file selection like '1,3,5' or '1-7' or '1-3,5,7-9'."""
    result: set[int] = set()
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            bounds = part.split("-", 1)
            try:
                start, end = int(bounds[0].strip()), int(bounds[1].strip())
                result.update(range(start, end + 1))
            except ValueError:
                continue
        else:
            try:
                result.add(int(part))
            except ValueError:
                continue
    return result


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


@router.message(Command("files"))
async def cmd_files(
    message: Message, command: CommandObject, aria2: Aria2Client
) -> None:
    gid = (command.args or "").strip()
    if not gid:
        await message.answer("Usage: /files &lt;gid&gt;", parse_mode=ParseMode.HTML)
        return
    try:
        files = await aria2.get_files(gid)
        text = format_file_list(files)
        if not text:
            text = "No files found."
        await message.answer(
            f"\U0001F4C2 <b>Files for</b> <code>{gid}</code>:\n\n{text}",
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        await message.answer(f"Error: {e}")


@router.message(F.document)
async def handle_torrent_file(
    message: Message,
    bot: Bot,
    aria2: Aria2Client,
) -> None:
    doc = message.document
    if not doc or not (doc.file_name or "").lower().endswith(".torrent"):
        return

    try:
        file = await bot.download(doc)
        torrent_bytes = file.read()
        torrent_b64 = base64.b64encode(torrent_bytes).decode()
    except Exception as e:
        await message.answer(f"\u274C Failed to download torrent file: {e}")
        return

    try:
        gid = await aria2.add_torrent(torrent_b64, options={"pause": "true"})
    except Exception as e:
        await message.answer(f"\u274C Failed to add torrent: {e}")
        return

    try:
        status = await aria2.tell_status(gid)
        files = await aria2.get_files(gid)
        text = format_torrent_info(status, files)
    except Exception:
        text = f"\U0001F9F2 Torrent added (paused)\nGID: <code>{gid}</code>"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="\u25B6 Download All",
                    callback_data=TorrentAction(
                        action="download_all", gid=gid
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="\U0001F4CB Select Files",
                    callback_data=TorrentAction(
                        action="select_files", gid=gid
                    ).pack(),
                ),
            ]
        ]
    )

    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)


@router.message(F.text)
async def handle_url(
    message: Message,
    aria2: Aria2Client,
    progress_updater: ProgressUpdater,
) -> None:
    text = message.text or ""

    # Check for pending file selection
    from handlers.callbacks import pending_file_selections

    chat_id = message.chat.id
    if chat_id in pending_file_selections and FILE_SELECT_RE.match(text.strip()):
        gid = pending_file_selections.pop(chat_id)
        indices = _parse_file_indices(text.strip())
        if not indices:
            await message.answer("Invalid input. Enter file numbers, e.g.: <code>1,3,5</code> or <code>1-7</code>",
                                 parse_mode=ParseMode.HTML)
            pending_file_selections[chat_id] = gid
            return

        select_file_str = ",".join(str(i) for i in sorted(indices))
        try:
            await aria2.change_option(gid, {"select-file": select_file_str})
            await aria2.unpause(gid)
        except Exception as e:
            await message.answer(f"\u274C Error: {e}")
            return

        try:
            status = await aria2.tell_status(gid)
            reply_text = format_progress(status)
        except Exception:
            reply_text = f"\U0001F4E5 Download started\nGID: <code>{gid}</code>"

        sent = await message.answer(reply_text, parse_mode=ParseMode.HTML)
        progress_updater.track(gid, sent.chat.id, sent.message_id)
        return

    # Normal URL handling
    urls = URL_RE.findall(text)
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
            reply_text = format_progress(status)
        except Exception:
            reply_text = f"\U0001F4E5 Download added\nGID: <code>{gid}</code>"

        sent = await message.answer(reply_text, parse_mode=ParseMode.HTML)
        progress_updater.track(gid, sent.chat.id, sent.message_id)
