# ============================================================
# utils/scheduler.py — APScheduler напоминания
# ============================================================

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore

from database.db import get_pending_reminder_bookings, set_reminder_job_id

logger = logging.getLogger(__name__)

# Глобальный экземпляр планировщика
_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        jobstores = {"default": MemoryJobStore()}
        _scheduler = AsyncIOScheduler(jobstores=jobstores, timezone="Europe/Kyiv")
    return _scheduler


# ─────────────────────────────────────────────────────────────
# Функция напоминания (вызывается по расписанию)
# ─────────────────────────────────────────────────────────────

async def send_reminder(bot, user_id: int, service_name: str, time_str: str):
    """Отправляет напоминание пользователю за 24ч до записи."""
    try:
        await bot.send_message(
            user_id,
            f"🔔 <b>Нагадування про запис!</b>\n\n"
            f"Нагадуємо, що ви записані на <b>{service_name}</b> завтра о <b>{time_str}</b>.\n\n"
            "Чекаємо на вас!",
            parse_mode="HTML",
        )
        logger.info(f"Reminder sent to user {user_id}")
    except Exception as e:
        logger.warning(f"Failed to send reminder to {user_id}: {e}")


# ─────────────────────────────────────────────────────────────
# Создание задачи напоминания при бронировании
# ─────────────────────────────────────────────────────────────

async def schedule_reminder(bot, booking_id: int, date_str: str, time_str: str):
    """
    Планирует отправку напоминания за 24ч до визита.
    Если до визита меньше 24ч — напоминание не создаётся.
    """
    from database.db import get_booking_by_id

    scheduler = get_scheduler()
    booking_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    remind_at = booking_dt - timedelta(hours=24)

    if remind_at <= datetime.now():
        logger.info(f"Booking {booking_id}: reminder skipped (less than 24h away)")
        return

    booking = await get_booking_by_id(booking_id)
    if not booking:
        return

    job_id = f"reminder_{booking_id}"
    scheduler.add_job(
        send_reminder,
        trigger="date",
        run_date=remind_at,
        args=[bot, booking["user_id"], booking["service_name"], time_str],
        id=job_id,
        replace_existing=True,
    )
    await set_reminder_job_id(booking_id, job_id)
    logger.info(f"Reminder scheduled for booking {booking_id} at {remind_at}")


# ─────────────────────────────────────────────────────────────
# Отмена задачи напоминания
# ─────────────────────────────────────────────────────────────

def cancel_reminder(job_id: str):
    """Удаляет задачу напоминания из планировщика."""
    if not job_id:
        return
    scheduler = get_scheduler()
    try:
        scheduler.remove_job(job_id)
        logger.info(f"Reminder job {job_id} cancelled")
    except Exception:
        logger.debug(f"Job {job_id} not found in scheduler (already fired or removed)")


# ─────────────────────────────────────────────────────────────
# Восстановление задач при перезапуске бота
# ─────────────────────────────────────────────────────────────

async def restore_jobs_from_db(bot):
    """
    При старте бота восстанавливает все будущие напоминания из БД.
    Вызывается в on_startup.
    """
    bookings = await get_pending_reminder_bookings()
    restored = 0
    for b in bookings:
        booking_dt = datetime.strptime(f"{b['date']} {b['time_str']}", "%Y-%m-%d %H:%M")
        remind_at = booking_dt - timedelta(hours=24)

        if remind_at <= datetime.now():
            continue  # Время уже прошло

        job_id = b["reminder_job_id"] or f"reminder_{b['id']}"
        scheduler = get_scheduler()
        scheduler.add_job(
            send_reminder,
            trigger="date",
            run_date=remind_at,
            args=[bot, b["user_id"], b["service_name"], b["time_str"]],
            id=job_id,
            replace_existing=True,
        )
        restored += 1

    logger.info(f"Restored {restored} reminder job(s) from DB")
