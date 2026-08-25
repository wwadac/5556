"""Главный файл бота"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import config
from database import db
from middlewares import SubscriptionMiddleware, ChannelMiddleware
from handlers import (
    start_router, admin_router, messages_router,
    deleted_router, edits_router, callbacks_router
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    await db.init()
    logger.info("✅ База данных инициализирована")

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    dp.message.middleware(ChannelMiddleware())
    dp.message.middleware(SubscriptionMiddleware())

    # Порядок ВАЖЕН: более специфичные роутеры первыми
    dp.include_router(start_router)      # /start
    dp.include_router(admin_router)      # фото (скриншоты оплаты) — ДО messages
    dp.include_router(callbacks_router)  # callback-кнопки
    dp.include_router(deleted_router)    # удаление чата
    dp.include_router(edits_router)      # редактирование
    dp.include_router(messages_router)   # ВСЕ сообщения — ПОСЛЕДНИМ

    logger.info("🚀 Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
