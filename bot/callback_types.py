from aiogram.filters.callback_data import CallbackData


class DownloadAction(CallbackData, prefix="dl"):
    action: str  # pause, resume, cancel
    gid: str


class ListAction(CallbackData, prefix="list"):
    action: str  # refresh


class TorrentAction(CallbackData, prefix="tor"):
    action: str  # download_all, select_files
    gid: str


class UsbAction(CallbackData, prefix="usb"):
    action: str  # copy
    idx: int
