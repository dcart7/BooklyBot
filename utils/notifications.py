# ============================================================
# utils/notifications.py — Уведомления admin / канал расписания
# ============================================================

import logging
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from config import ADMIN_ID, SCHEDULE_CHANNEL_ID

logger = logging.getLogger(__name__)


def _format_booking(booking) -> str:
    """Формирует HTML-текст сообщения о записи."""
    hours = booking["duration_min"] // 60
    mins = booking["duration_min"] % 60
    if hours and mins:
        dur_str = f"{hours}год {mins}хв"
    elif hours:
        dur_str = f"{hours}год"
    else:
        dur_str = f"{mins}хв"

    return (
        f"💅 <b>Новий запис!</b>\n\n"
        f"📅 <b>Дата:</b> {booking['date']}\n"
        f"⏰ <b>Час:</b> {booking['time_str']}\n"
        f"⏱ <b>Тривалість:</b> {dur_str}\n"
        f"💅 <b>Послуга:</b> {booking['service_name']}\n"
        f"👤 <b>Клієнт:</b> {booking['user_name']}\n"
        f"📱 <b>Телефон:</b> {booking['phone']}\n"
        f"🆔 <b>User ID:</b> <code>{booking['user_id']}</code>"
    )


async def notify_admin(bot: Bot, booking) -> None:
    """Отправляет уведомление администратору о новой записи."""
    try:
        await bot.send_message(
            ADMIN_ID,
            _format_booking(booking),
            parse_mode="HTML",
        )
    except TelegramBadRequest as e:
        logger.error(f"Failed to notify admin: {e}")


async def post_to_channel(bot: Bot, booking) -> None:
    """Публикует информацию о записи в канал расписания."""
    try:
        await bot.send_message(
            SCHEDULE_CHANNEL_ID,
            _format_booking(booking),
            parse_mode="HTML",
        )
    except TelegramBadRequest as e:
        logger.error(f"Failed to post to channel: {e}")
    except Exception as e:
        logger.warning(f"Channel post skipped: {e}")
