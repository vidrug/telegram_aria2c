import logging

from aiogram import Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from aiogram.enums import ParseMode

from aria2_client import Aria2Client
from callback_types import DownloadAction, ListAction, TorrentAction
from services.progress_updater import ProgressUpdater
from utils.formatting import (
    format_download_list,
    format_file_list,
    format_progress,
)

logger = logging.getLogger(__name__)
router = Router()

# chat_id -> gid awaiting file selection input
pending_file_selections: dict[int, str] = {}


@router.callback_query(DownloadAction.filter())
async def on_download_action(
    callback: CallbackQuery,
    callback_data: DownloadAction,
    aria2: Aria2Client,
) -> None:
    gid = callback_data.gid
    action = callback_data.action

    try:
        if action == "pause":
            await aria2.pause(gid)
            await callback.answer(f"Paused {gid}")
        elif action == "resume":
            await aria2.unpause(gid)
            await callback.answer(f"Resumed {gid}")
        elif action == "cancel":
            await aria2.force_remove(gid)
            await callback.answer(f"Cancelled {gid}")

            if callback.message:
                await callback.message.edit_text(
                    f"\u274C Cancelled <code>{gid}</code>",
                    parse_mode=ParseMode.HTML,
                )
            return
    except Exception as e:
        await callback.answer(f"Error: {e}", show_alert=True)
        return

    # Update the message with current status
    try:
        status = await aria2.tell_status(gid)
        state = status.get("status", "")
        text = format_progress(status)

        buttons = []
        if state == "active":
            buttons.append(
                InlineKeyboardButton(
                    text="\u23F8 Pause",
                    callback_data=DownloadAction(action="pause", gid=gid).pack(),
                )
            )
        elif state == "paused":
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
        kb = InlineKeyboardMarkup(inline_keyboard=[buttons])

        if callback.message:
            await callback.message.edit_text(
                text, parse_mode=ParseMode.HTML, reply_markup=kb
            )
    except Exception:
        pass


@router.callback_query(ListAction.filter())
async def on_list_action(
    callback: CallbackQuery,
    callback_data: ListAction,
    aria2: Aria2Client,
) -> None:
    if callback_data.action != "refresh":
        await callback.answer()
        return

    active = await aria2.tell_active()
    waiting = await aria2.tell_waiting()
    all_downloads = active + waiting

    text = format_download_list(all_downloads)

    rows: list[list[InlineKeyboardButton]] = []
    for d in all_downloads:
        gid = d.get("gid", "")
        state = d.get("status", "")
        btns: list[InlineKeyboardButton] = []
        if state == "active":
            btns.append(
                InlineKeyboardButton(
                    text="\u23F8 Pause",
                    callback_data=DownloadAction(action="pause", gid=gid).pack(),
                )
            )
        elif state in ("paused", "waiting"):
            btns.append(
                InlineKeyboardButton(
                    text="\u25B6 Resume",
                    callback_data=DownloadAction(action="resume", gid=gid).pack(),
                )
            )
        btns.append(
            InlineKeyboardButton(
                text="\u274C Cancel",
                callback_data=DownloadAction(action="cancel", gid=gid).pack(),
            )
        )
        rows.append(btns)

    rows.append(
        [
            InlineKeyboardButton(
                text="\U0001F504 Refresh",
                callback_data=ListAction(action="refresh").pack(),
            )
        ]
    )
    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    if callback.message:
        await callback.message.edit_text(
            text, parse_mode=ParseMode.HTML, reply_markup=kb
        )
    await callback.answer()


@router.callback_query(TorrentAction.filter())
async def on_torrent_action(
    callback: CallbackQuery,
    callback_data: TorrentAction,
    aria2: Aria2Client,
    progress_updater: ProgressUpdater,
) -> None:
    gid = callback_data.gid
    action = callback_data.action

    if action == "download_all":
        try:
            await aria2.unpause(gid)
        except Exception as e:
            await callback.answer(f"Error: {e}", show_alert=True)
            return

        try:
            status = await aria2.tell_status(gid)
            text = format_progress(status)
        except Exception:
            text = f"\U0001F4E5 Download started\nGID: <code>{gid}</code>"

        if callback.message:
            await callback.message.edit_text(text, parse_mode=ParseMode.HTML)
            progress_updater.track(
                gid, callback.message.chat.id, callback.message.message_id
            )

        await callback.answer("Download started")

    elif action == "select_files":
        try:
            files = await aria2.get_files(gid)
        except Exception as e:
            await callback.answer(f"Error: {e}", show_alert=True)
            return

        text = format_file_list(files)
        chat_id = callback.message.chat.id if callback.message else None

        if chat_id is not None:
            pending_file_selections[chat_id] = gid

        if callback.message:
            await callback.message.edit_text(
                f"\U0001F4CB <b>Select files to download</b>\n\n"
                f"{text}\n\n"
                f"Enter file numbers: <code>1,3,5</code> or <code>1-7</code> or <code>1-3,5,7</code>",
                parse_mode=ParseMode.HTML,
            )
        await callback.answer()

    else:
        await callback.answer()
