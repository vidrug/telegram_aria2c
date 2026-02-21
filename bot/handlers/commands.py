import logging
import os

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode

from aria2_client import Aria2Client
from callback_types import DownloadAction, ListAction, UsbAction
from config import settings
from utils.formatting import format_download_list, format_global_stats

logger = logging.getLogger(__name__)
router = Router()

# /copyusb state per chat
usb_file_mappings: dict[int, dict[int, str]] = {}
usb_selected_file: dict[int, str] = {}
usb_dest_mappings: dict[int, dict[int, str]] = {}

HELP_TEXT = (
    "<b>Available commands:</b>\n\n"
    "/start — Welcome message\n"
    "/help — Show this help\n"
    "/downloads — List active downloads\n"
    "/stats — aria2c statistics\n"
    "/files &lt;gid&gt; — List torrent files\n"
    "/pause &lt;gid&gt; — Pause download\n"
    "/resume &lt;gid&gt; — Resume download\n"
    "/cancel &lt;gid&gt; — Cancel download\n"
    "/pauseall — Pause all\n"
    "/resumeall — Resume all\n"
    "/cancelall — Cancel all\n"
    "/copyusb — Copy files to USB\n\n"
    "Send a URL or <b>.torrent</b> file to start a download."
)


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "\U0001F44B <b>aria2c Download Bot</b>\n\n"
        "Send me a URL and I'll download it.\n"
        "Use /help for the full command list.",
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, parse_mode=ParseMode.HTML)


@router.message(Command("downloads"))
async def cmd_downloads(message: Message, aria2: Aria2Client) -> None:
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
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)


@router.message(Command("stats"))
async def cmd_stats(message: Message, aria2: Aria2Client) -> None:
    stat = await aria2.get_global_stat()
    await message.answer(
        format_global_stats(stat), parse_mode=ParseMode.HTML
    )


@router.message(Command("copyusb"))
async def cmd_copyusb(message: Message) -> None:
    download_dir = settings.download_dir
    try:
        entries = os.listdir(download_dir)
    except FileNotFoundError:
        await message.answer("Download directory not found.")
        return

    entries = [e for e in entries if not e.startswith(".")]
    if not entries:
        await message.answer("\U0001F4ED No files in downloads directory.")
        return

    entries.sort()
    chat_id = message.chat.id
    mapping: dict[int, str] = {}
    rows: list[list[InlineKeyboardButton]] = []

    for idx, name in enumerate(entries):
        mapping[idx] = name
        path = os.path.join(download_dir, name)
        label = f"\U0001F4C1 {name}" if os.path.isdir(path) else f"\U0001F4C4 {name}"
        rows.append([
            InlineKeyboardButton(
                text=label,
                callback_data=UsbAction(action="file", idx=idx).pack(),
            )
        ])

    usb_file_mappings[chat_id] = mapping
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await message.answer(
        "\U0001F4CB <b>Select file to copy to USB:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
