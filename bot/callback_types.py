from aiogram.filters.callback_data import CallbackData


class DownloadAction(CallbackData, prefix="dl"):
    action: str  # pause, resume, cancel
    gid: str


class ListAction(CallbackData, prefix="list"):
    action: str  # refresh
