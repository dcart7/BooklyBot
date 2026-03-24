# ============================================================
# bot.py — Точка входа бота
# ============================================================

import asyncio
import logging
import sys
from pathlib import Path

# Добавляем корень проекта в sys.path для корректного импорта
sys.path.insert(0, str(Path(__file__).parent))

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database.db import init_db
from utils.scheduler import get_scheduler, restore_jobs_from_db

# Импортируем все роутеры
from handlers import start, booking, cancel, prices, portfolio, admin

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bookly.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    """Выполняется при старте бота."""
    logger.info("Initializing database...")
    await init_db()

    logger.info("Restoring reminder jobs from DB...")
    await restore_jobs_from_db(bot)

    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started.")

    logger.info("Bot started successfully! ✅")


async def on_shutdown(bot: Bot) -> None:
    """Выполняется при остановке бота."""
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
    logger.info("Bot stopped.")


async def main() -> None:
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("❌ Вкажіть BOT_TOKEN у файлі .env або config.py!")
        sys.exit(1)

    bot = Bot(token=BOT_TOKEN, default=None)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрируем обработчики startup/shutdown
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Подключаем роутеры
    # Порядок важен: admin перед booking, чтобы adm:prices/adm:portfolio
    # обрабатывались именно в admin (они там определены как callbacks)
    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(prices.router)
    dp.include_router(portfolio.router)
    dp.include_router(booking.router)
    dp.include_router(cancel.router)

    # Запускаем polling
    logger.info("Starting polling...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user.")
