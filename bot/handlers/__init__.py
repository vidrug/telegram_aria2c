from aiogram import Router

from handlers import callbacks, commands, downloads


def setup_routers() -> Router:
    root = Router()
    root.include_router(commands.router)
    root.include_router(callbacks.router)
    # downloads last — has catch-all F.text handler
    root.include_router(downloads.router)
    return root
