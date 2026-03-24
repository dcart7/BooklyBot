# ============================================================
# handlers/cancel.py — Отмена записи пользователем
# ============================================================

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

from database.db import get_user_active_booking, cancel_booking
from keyboards.booking_kb import my_booking_kb, confirm_cancel_kb
from keyboards.main_kb import main_menu_kb, back_to_main_kb
from utils.scheduler import cancel_reminder

router = Router()


@router.callback_query(F.data == "my_bookings")
async def my_bookings(callback: CallbackQuery, bot: Bot):
    booking = await get_user_active_booking(callback.from_user.id)
    if not booking:
        await callback.message.edit_text(  # type: ignore
            "📭 <b>У вас немає активних записів.</b>",
            parse_mode="HTML",
            reply_markup=back_to_main_kb(),
        )
        return

    text = (
        "📋 <b>Ваш запис:</b>\n\n"
        f"💅 <b>Послуга:</b> {booking['service_name']}\n"
        f"📅 <b>Дата:</b> {booking['date']}\n"
        f"⏰ <b>Час:</b> {booking['time_str']}\n"
        f"👤 <b>Ім'я:</b> {booking['user_name']}\n"
        f"📱 <b>Телефон:</b> {booking['phone']}\n"
    )
    await callback.message.edit_text(  # type: ignore
        text,
        parse_mode="HTML",
        reply_markup=my_booking_kb(booking["id"]),
    )


@router.callback_query(F.data.startswith("cancel_my:"))
async def ask_cancel_my(callback: CallbackQuery):
    booking_id = int(callback.data.split(":")[1])  # type: ignore
    await callback.message.edit_text(  # type: ignore
        "⚠️ <b>Ви впевнені, що хочете скасувати запис?</b>",
        parse_mode="HTML",
        reply_markup=confirm_cancel_kb(booking_id),
    )


@router.callback_query(F.data.startswith("do_cancel:"))
async def do_cancel(callback: CallbackQuery, bot: Bot):
    booking_id = int(callback.data.split(":")[1])  # type: ignore
    cancelled = await cancel_booking(booking_id)

    if not cancelled:
        await callback.answer("Запис не знайдено або вже скасовано.", show_alert=True)
        return

    # Удаляем задачу напоминания
    if cancelled["reminder_job_id"]:
        cancel_reminder(cancelled["reminder_job_id"])

    await callback.message.edit_text(  # type: ignore
        "✅ <b>Запис успішно скасовано.</b>\n\nЧекаємо на вас знову! 💖",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )
