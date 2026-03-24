# ============================================================
# handlers/booking.py — Полный FSM-флоу записи
# ============================================================

from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_ID
from database.db import (
    get_all_services, get_service, get_available_dates,
    get_available_slots_for_date, get_user_active_booking,
    create_booking, get_booking_by_id,
)
from keyboards.booking_kb import services_kb, slots_kb, confirm_booking_kb
from keyboards.calendar_kb import build_calendar, get_prev_month, get_next_month
from keyboards.main_kb import main_menu_kb
from handlers.start import require_subscription
from utils.notifications import notify_admin, post_to_channel
from utils.scheduler import schedule_reminder

router = Router()


# ─────────────────────────────────────────────────────────────
# FSM States
# ─────────────────────────────────────────────────────────────

class BookingStates(StatesGroup):
    choose_service = State()
    choose_date    = State()
    choose_slot    = State()
    enter_name     = State()
    enter_phone    = State()
    confirm        = State()


# ─────────────────────────────────────────────────────────────
# Начало записи
# ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "book_start")
async def book_start(callback: CallbackQuery, state: FSMContext, bot: Bot):
    # Проверяем подписку
    if not await require_subscription(callback, bot):
        return

    # Проверяем, нет ли уже активной записи
    existing = await get_user_active_booking(callback.from_user.id)
    if existing:
        await callback.message.edit_text(  # type: ignore
            f"⚠️ <b>У вас вже є активний запис:</b>\n\n"
            f"📅 <b>Дата:</b> {existing['date']}\n"
            f"⏰ <b>Час:</b> {existing['time_str']}\n"
            f"💅 <b>Послуга:</b> {existing['service_name']}\n\n"
            "Скасуйте поточний запис, щоб створити новий.",
            parse_mode="HTML",
            reply_markup=main_menu_kb(),
        )
        return

    services = await get_all_services()
    await callback.message.edit_text(  # type: ignore
        "💅 <b>Оберіть послугу:</b>",
        parse_mode="HTML",
        reply_markup=services_kb(services),
    )
    await state.set_state(BookingStates.choose_service)


# ─────────────────────────────────────────────────────────────
# Выбор услуги
# ─────────────────────────────────────────────────────────────

@router.callback_query(BookingStates.choose_service, F.data.startswith("svc:"))
async def choose_service(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split(":")[1])  # type: ignore
    service = await get_service(service_id)
    if not service:
        await callback.answer("Послугу не знайдено.", show_alert=True)
        return

    await state.update_data(service_id=service_id, duration_min=service["duration_min"])

    now = datetime.now()
    available_dates = await get_available_dates()
    await callback.message.edit_text(  # type: ignore
        f"✅ Обрано послугу: <b>{service['name']}</b>\n\n"
        "📅 <b>Оберіть дату:</b>",
        parse_mode="HTML",
        reply_markup=build_calendar(now.year, now.month, available_dates),
    )
    await state.update_data(cal_year=now.year, cal_month=now.month)
    await state.set_state(BookingStates.choose_date)


# ─────────────────────────────────────────────────────────────
# Навигация по календарю
# ─────────────────────────────────────────────────────────────

@router.callback_query(BookingStates.choose_date, F.data.startswith("cal:"))
async def calendar_navigate(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")  # type: ignore
    action = parts[1]

    if action == "ignore":
        await callback.answer()
        return

    data = await state.get_data()
    available_dates = await get_available_dates()

    if action == "prev":
        year, month = get_prev_month(int(parts[2]), int(parts[3]))
    elif action == "next":
        year, month = get_next_month(int(parts[2]), int(parts[3]))
    elif action == "day":
        date_str = parts[2]
        await state.update_data(chosen_date=date_str)

        duration_min = data.get("duration_min", 60)
        slots = await get_available_slots_for_date(date_str, duration_min)

        if not slots:
            await callback.answer("На цю дату немає вільних слотів.", show_alert=True)
            return

        await callback.message.edit_text(  # type: ignore
            f"📅 <b>Дата:</b> {date_str}\n\n⏰ <b>Оберіть час:</b>",
            parse_mode="HTML",
            reply_markup=slots_kb(slots, date_str),
        )
        await state.set_state(BookingStates.choose_slot)
        return
    else:
        await callback.answer()
        return

    await state.update_data(cal_year=year, cal_month=month)
    await callback.message.edit_reply_markup(  # type: ignore
        reply_markup=build_calendar(year, month, available_dates)
    )


# ─────────────────────────────────────────────────────────────
# Назад к списку услуг
# ─────────────────────────────────────────────────────────────

@router.callback_query(BookingStates.choose_date, F.data == "back_to_services")
async def back_to_services(callback: CallbackQuery, state: FSMContext):
    services = await get_all_services()
    await callback.message.edit_text(  # type: ignore
        "💅 <b>Оберіть послугу:</b>",
        parse_mode="HTML",
        reply_markup=services_kb(services),
    )
    await state.set_state(BookingStates.choose_service)


# ─────────────────────────────────────────────────────────────
# Назад к календарю
# ─────────────────────────────────────────────────────────────

@router.callback_query(BookingStates.choose_slot, F.data == "back_to_calendar")
async def back_to_calendar(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    year = data.get("cal_year", datetime.now().year)
    month = data.get("cal_month", datetime.now().month)
    available_dates = await get_available_dates()

    await callback.message.edit_text(  # type: ignore
        "📅 <b>Оберіть дату:</b>",
        parse_mode="HTML",
        reply_markup=build_calendar(year, month, available_dates),
    )
    await state.set_state(BookingStates.choose_date)


# ─────────────────────────────────────────────────────────────
# Выбор слота
# ─────────────────────────────────────────────────────────────

@router.callback_query(BookingStates.choose_slot, F.data.startswith("slot:"))
async def choose_slot(callback: CallbackQuery, state: FSMContext):
    _, slot_id_str, time_str = callback.data.split(":")  # type: ignore
    await state.update_data(chosen_slot_id=int(slot_id_str), chosen_time=time_str)

    await callback.message.edit_text(  # type: ignore
        "👤 <b>Введіть ваше ім'я:</b>",
        parse_mode="HTML",
    )
    await state.set_state(BookingStates.enter_name)


# ─────────────────────────────────────────────────────────────
# Ввод имени
# ─────────────────────────────────────────────────────────────

@router.message(BookingStates.enter_name)
async def enter_name(message: Message, state: FSMContext):
    name = message.text.strip()  # type: ignore
    if len(name) < 2:
        await message.answer("❌ Введіть коректне ім'я (мінімум 2 символи).")
        return
    await state.update_data(user_name=name)
    await message.answer(
        "📱 <b>Введіть ваш номер телефону:</b>\n\n"
        "Приклад: <code>+380991234567</code>",
        parse_mode="HTML",
    )
    await state.set_state(BookingStates.enter_phone)


# ─────────────────────────────────────────────────────────────
# Ввод телефона
# ─────────────────────────────────────────────────────────────

@router.message(BookingStates.enter_phone)
async def enter_phone(message: Message, state: FSMContext):
    phone = message.text.strip()  # type: ignore
    # Базовая проверка
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) < 10:
        await message.answer("❌ Введіть коректний номер телефону (мінімум 10 цифр).")
        return

    await state.update_data(phone=phone)
    data = await state.get_data()
    service = await get_service(data["service_id"])

    hours = data["duration_min"] // 60
    mins = data["duration_min"] % 60
    if hours and mins:
        dur_str = f"{hours}год {mins}хв"
    elif hours:
        dur_str = f"{hours}год"
    else:
        dur_str = f"{mins}хв"

    text = (
        "📋 <b>Перевірте дані запису:</b>\n\n"
        f"💅 <b>Послуга:</b> {service['name']}\n"  # type: ignore
        f"⏱ <b>Тривалість:</b> {dur_str}\n"
        f"📅 <b>Дата:</b> {data['chosen_date']}\n"
        f"⏰ <b>Час:</b> {data['chosen_time']}\n"
        f"👤 <b>Ім'я:</b> {data['user_name']}\n"
        f"📱 <b>Телефон:</b> {phone}\n\n"
        "Все вірно?"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=confirm_booking_kb())
    await state.set_state(BookingStates.confirm)


# ─────────────────────────────────────────────────────────────
# Подтверждение записи
# ─────────────────────────────────────────────────────────────

@router.callback_query(BookingStates.confirm, F.data == "confirm_booking")
async def confirm_booking(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()

    # Финальная проверка — нет ли уже активной записи
    existing = await get_user_active_booking(callback.from_user.id)
    if existing:
        await callback.message.edit_text(  # type: ignore
            "⚠️ У вас вже є активний запис. Поверніться в головне меню.",
            reply_markup=main_menu_kb(),
        )
        await state.clear()
        return

    booking_id = await create_booking(
        user_id=callback.from_user.id,
        user_name=data["user_name"],
        phone=data["phone"],
        service_id=data["service_id"],
        date_str=data["chosen_date"],
        time_str=data["chosen_time"],
        duration_min=data["duration_min"],
    )

    booking = await get_booking_by_id(booking_id)
    service = await get_service(data["service_id"])

    # Планируем напоминание
    await schedule_reminder(bot, booking_id, data["chosen_date"], data["chosen_time"])

    # Уведомляем администратора
    await notify_admin(bot, booking)

    # Публикуем в канал расписания
    await post_to_channel(bot, booking)

    await state.clear()

    await callback.message.edit_text(  # type: ignore
        "🎉 <b>Запис успішно створено!</b>\n\n"
        f"💅 <b>Послуга:</b> {service['name']}\n"  # type: ignore
        f"📅 <b>Дата:</b> {data['chosen_date']}\n"
        f"⏰ <b>Час:</b> {data['chosen_time']}\n\n"
        "Чекаємо на вас! 💖\n"
        "За 24 години до візиту ви отримаєте нагадування.",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )


# ─────────────────────────────────────────────────────────────
# Отмена флоу бронирования
# ─────────────────────────────────────────────────────────────

@router.callback_query(BookingStates.confirm, F.data == "cancel_booking_flow")
async def cancel_booking_flow(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(  # type: ignore
        "↩️ Запис скасовано. Повернутися в меню:",
        reply_markup=main_menu_kb(),
    )
