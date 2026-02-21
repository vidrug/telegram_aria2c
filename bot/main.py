import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import settings
from aria2_client import Aria2Client
from handlers import setup_routers
from middlewares.auth import AuthMiddleware
from services.download_manager import DownloadManager
from services.progress_updater import ProgressUpdater

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    aria2 = Aria2Client()
    await aria2.connect()

    progress = ProgressUpdater(
        bot, aria2, interval=settings.progress_update_interval
    )
    _manager = DownloadManager(bot, aria2, progress)

    dp = Dispatcher()
    dp.update.middleware(AuthMiddleware())
    dp.include_router(setup_routers())

    # Make dependencies available via DI
    dp["aria2"] = aria2
    dp["progress_updater"] = progress

    progress.start()

    try:
        logger.info("Bot started")
        await dp.start_polling(bot)
    finally:
        await progress.stop()
        await aria2.disconnect()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
