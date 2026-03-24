# ============================================================
# handlers/admin.py — Полная админ-панель с FSM
# ============================================================

from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Filter

from config import ADMIN_ID
from database.db import (
    get_all_working_days, add_working_day, close_day, open_day,
    delete_working_day, get_slots_for_date, add_slot, delete_slot,
    get_bookings_for_date, get_all_active_bookings, cancel_booking,
    get_booking_by_id,
)
from keyboards.admin_kb import (
    admin_main_kb, admin_days_kb, admin_day_manage_kb, admin_slots_kb,
    admin_slot_manage_kb, admin_bookings_kb, admin_booking_manage_kb,
)
from keyboards.main_kb import back_to_main_kb
from utils.scheduler import cancel_reminder

router = Router()


# ─────────────────────────────────────────────────────────────
# Фильтр администратора
# ─────────────────────────────────────────────────────────────

class IsAdmin(Filter):
    async def __call__(self, event) -> bool:
        if isinstance(event, Message):
            return event.from_user.id == ADMIN_ID  # type: ignore
        elif isinstance(event, CallbackQuery):
            return event.from_user.id == ADMIN_ID
        return False


# ─────────────────────────────────────────────────────────────
# FSM States для admin
# ─────────────────────────────────────────────────────────────

class AdminStates(StatesGroup):
    add_day_input    = State()
    add_slot_input   = State()


# ─────────────────────────────────────────────────────────────
# /admin — Открыть панель
# ─────────────────────────────────────────────────────────────

@router.message(Command("admin"), IsAdmin())
async def admin_panel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🔧 <b>Панель адміністратора</b>\n\nОберіть розділ:",
        parse_mode="HTML",
        reply_markup=admin_main_kb(),
    )


@router.callback_query(F.data == "adm:main", IsAdmin())
async def admin_main_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(  # type: ignore
        "🔧 <b>Панель адміністратора</b>\n\nОберіть розділ:",
        parse_mode="HTML",
        reply_markup=admin_main_kb(),
    )


# ─────────────────────────────────────────────────────────────
# Управление рабочими днями
# ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:days", IsAdmin())
async def admin_days(callback: CallbackQuery):
    days = await get_all_working_days()
    if not days:
        await callback.message.edit_text(  # type: ignore
            "📅 <b>Робочі дні</b>\n\nНемає налаштованих днів.\n\nНатисніть «➕ Додати день».",
            parse_mode="HTML",
            reply_markup=admin_days_kb([]),
        )
        return
    await callback.message.edit_text(  # type: ignore
        "📅 <b>Робочі дні</b>\n\n"
        "🟢 — відкритий  |  🔴 — закритий\n\n"
        "Натисніть на день для керування:",
        parse_mode="HTML",
        reply_markup=admin_days_kb(days),
    )


@router.callback_query(F.data == "adm:add_day", IsAdmin())
async def admin_add_day_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(  # type: ignore
        "📅 <b>Додавання робочого дня</b>\n\n"
        "Введіть дату у форматі <code>YYYY-MM-DD</code>\n"
        "Наприклад: <code>2026-04-01</code>",
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.add_day_input)


@router.message(AdminStates.add_day_input, IsAdmin())
async def admin_add_day_input(message: Message, state: FSMContext):
    date_str = message.text.strip()  # type: ignore
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await message.answer("❌ Невірний формат. Введіть дату як YYYY-MM-DD.")
        return

    added = await add_working_day(date_str)
    await state.clear()
    if added:
        await message.answer(
            f"✅ <b>День {date_str} додано</b> з тимчасовими слотами за замовчуванням.",
            parse_mode="HTML",
            reply_markup=back_to_main_kb(),
        )
    else:
        await message.answer(
            f"⚠️ День {date_str} вже існує.",
            reply_markup=back_to_main_kb(),
        )


@router.callback_query(F.data.startswith("adm:day_info:"), IsAdmin())
async def admin_day_info(callback: CallbackQuery):
    date_str = callback.data.split("adm:day_info:")[1]  # type: ignore
    days = await get_all_working_days()
    day = next((d for d in days if d["date"] == date_str), None)
    if not day:
        await callback.answer("День не знайдено.", show_alert=True)
        return

    status = "🔴 Закритий" if day["is_closed"] else "🟢 Відкритий"
    slots = await get_slots_for_date(date_str)
    free = sum(1 for s in slots if s["is_available"])
    total = len(slots)

    await callback.message.edit_text(  # type: ignore
        f"📅 <b>День: {date_str}</b>\n"
        f"Статус: {status}\n"
        f"Слоти: {free}/{total} вільно",
        parse_mode="HTML",
        reply_markup=admin_day_manage_kb(date_str, bool(day["is_closed"])),
    )


@router.callback_query(F.data.startswith("adm:close_day:"), IsAdmin())
async def admin_close_day(callback: CallbackQuery):
    date_str = callback.data.split("adm:close_day:")[1]  # type: ignore
    await close_day(date_str)
    await callback.answer(f"✅ День {date_str} закрито.", show_alert=True)
    # Обновляем инфо
    await admin_day_info(callback)


@router.callback_query(F.data.startswith("adm:open_day:"), IsAdmin())
async def admin_open_day(callback: CallbackQuery):
    date_str = callback.data.split("adm:open_day:")[1]  # type: ignore
    await open_day(date_str)
    await callback.answer(f"✅ День {date_str} відкрито.", show_alert=True)
    await admin_day_info(callback)


@router.callback_query(F.data.startswith("adm:delete_day:"), IsAdmin())
async def admin_delete_day(callback: CallbackQuery):
    date_str = callback.data.split("adm:delete_day:")[1]  # type: ignore
    await delete_working_day(date_str)
    await callback.answer(f"🗑 День {date_str} видалено.", show_alert=True)
    # Показываем обновлённый список
    days = await get_all_working_days()
    try:
        await callback.message.edit_text(  # type: ignore
            "📅 <b>Робочі дні</b>",
            parse_mode="HTML",
            reply_markup=admin_days_kb(days),
        )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# Управление слотами
# ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:slots", IsAdmin())
async def admin_slots_select_day(callback: CallbackQuery):
    days = await get_all_working_days()
    if not days:
        await callback.answer("Немає робочих днів.", show_alert=True)
        return
    await callback.message.edit_text(  # type: ignore
        "⏰ <b>Оберіть день для керування слотами:</b>",
        parse_mode="HTML",
        reply_markup=admin_days_kb(days),
    )


@router.callback_query(F.data.startswith("adm:manage_slots:"), IsAdmin())
async def admin_manage_slots(callback: CallbackQuery):
    date_str = callback.data.split("adm:manage_slots:")[1]  # type: ignore
    slots = await get_slots_for_date(date_str)
    await callback.message.edit_text(  # type: ignore
        f"⏰ <b>Слоти на {date_str}</b>\n\n"
        "🟢 — вільний  |  🔴 — зайнятий",
        parse_mode="HTML",
        reply_markup=admin_slots_kb(slots, date_str),
    )


@router.callback_query(F.data.startswith("adm:slot_info:"), IsAdmin())
async def admin_slot_info(callback: CallbackQuery):
    parts = callback.data.split("adm:slot_info:")[1].rsplit(":", 1)  # type: ignore
    date_str, time_str = parts[0], parts[1]
    await callback.message.edit_text(  # type: ignore
        f"⏰ <b>Слот {time_str} на {date_str}</b>",
        parse_mode="HTML",
        reply_markup=admin_slot_manage_kb(date_str, time_str),
    )


@router.callback_query(F.data.startswith("adm:add_slot:"), IsAdmin())
async def admin_add_slot_prompt(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.split("adm:add_slot:")[1]  # type: ignore
    await state.update_data(add_slot_date=date_str)
    await callback.message.edit_text(  # type: ignore
        f"➕ <b>Додати слот на {date_str}</b>\n\n"
        "Введіть час у форматі <code>HH:MM</code>\n"
        "Наприклад: <code>14:30</code>",
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.add_slot_input)


@router.message(AdminStates.add_slot_input, IsAdmin())
async def admin_add_slot_input(message: Message, state: FSMContext):
    time_str = message.text.strip()  # type: ignore
    try:
        datetime.strptime(time_str, "%H:%M")
    except ValueError:
        await message.answer("❌ Невірний формат. Введіть час як HH:MM.")
        return

    data = await state.get_data()
    date_str = data.get("add_slot_date", "")
    await state.clear()
    added = await add_slot(date_str, time_str)
    if added:
        await message.answer(
            f"✅ Слот <b>{time_str}</b> на {date_str} додано.",
            parse_mode="HTML",
        )
    else:
        await message.answer("❌ Не вдалося додати слот (день не знайдено або слот вже існує).")


@router.callback_query(F.data.startswith("adm:del_slot:"), IsAdmin())
async def admin_del_slot(callback: CallbackQuery):
    # adm:del_slot:YYYY-MM-DD:HH:MM
    raw = callback.data[len("adm:del_slot:"):]  # type: ignore
    # Разделяем: первые 10 символов — дата
    date_str = raw[:10]
    time_str = raw[11:]
    await delete_slot(date_str, time_str)
    await callback.answer(f"🗑 Слот {time_str} видалено.", show_alert=True)
    slots = await get_slots_for_date(date_str)
    try:
        await callback.message.edit_text(  # type: ignore
            f"⏰ <b>Слоти на {date_str}</b>",
            parse_mode="HTML",
            reply_markup=admin_slots_kb(slots, date_str),
        )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# Просмотр и отмена записей
# ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:bookings", IsAdmin())
async def admin_bookings(callback: CallbackQuery):
    bookings = await get_all_active_bookings()
    if not bookings:
        await callback.message.edit_text(  # type: ignore
            "📭 <b>Активних записів немає.</b>",
            parse_mode="HTML",
            reply_markup=back_to_main_kb(),
        )
        return
    await callback.message.edit_text(  # type: ignore
        f"📋 <b>Активні записи ({len(bookings)}):</b>",
        parse_mode="HTML",
        reply_markup=admin_bookings_kb(bookings),
    )


@router.callback_query(F.data.startswith("adm:day_bookings:"), IsAdmin())
async def admin_day_bookings(callback: CallbackQuery):
    date_str = callback.data.split("adm:day_bookings:")[1]  # type: ignore
    bookings = await get_bookings_for_date(date_str)
    if not bookings:
        await callback.answer(f"На {date_str} немає активних записів.", show_alert=True)
        return
    await callback.message.edit_text(  # type: ignore
        f"📋 <b>Записи на {date_str}:</b>",
        parse_mode="HTML",
        reply_markup=admin_bookings_kb(bookings),
    )


@router.callback_query(F.data.startswith("adm:booking:"), IsAdmin())
async def admin_booking_detail(callback: CallbackQuery):
    booking_id = int(callback.data.split("adm:booking:")[1])  # type: ignore
    b = await get_booking_by_id(booking_id)
    if not b:
        await callback.answer("Запис не знайдено.", show_alert=True)
        return

    hours = b["duration_min"] // 60
    mins = b["duration_min"] % 60
    if hours and mins:
        dur_str = f"{hours}год {mins}хв"
    elif hours:
        dur_str = f"{hours}год"
    else:
        dur_str = f"{mins}хв"

    text = (
        f"📋 <b>Запис #{b['id']}</b>\n\n"
        f"💅 <b>Послуга:</b> {b['service_name']}\n"
        f"⏱ <b>Тривалість:</b> {dur_str}\n"
        f"📅 <b>Дата:</b> {b['date']}\n"
        f"⏰ <b>Час:</b> {b['time_str']}\n"
        f"👤 <b>Клієнт:</b> {b['user_name']}\n"
        f"📱 <b>Телефон:</b> {b['phone']}\n"
        f"🆔 <b>User ID:</b> <code>{b['user_id']}</code>"
    )
    await callback.message.edit_text(  # type: ignore
        text,
        parse_mode="HTML",
        reply_markup=admin_booking_manage_kb(booking_id),
    )


@router.callback_query(F.data.startswith("adm:cancel_booking:"), IsAdmin())
async def admin_cancel_booking_cb(callback: CallbackQuery, bot: Bot):
    booking_id = int(callback.data.split("adm:cancel_booking:")[1])  # type: ignore
    b = await get_booking_by_id(booking_id)
    cancelled = await cancel_booking(booking_id)
    if not cancelled:
        await callback.answer("Запис не знайдено або вже скасована.", show_alert=True)
        return

    # Удаляем задачу напоминания
    if cancelled["reminder_job_id"]:
        cancel_reminder(cancelled["reminder_job_id"])

    # Уведомляем пользователя об отмене
    try:
        await bot.send_message(
            cancelled["user_id"],
            f"⚠️ <b>Ваш запис було скасовано адміністратором.</b>\n\n"
            f"📅 Дата: {cancelled['date']}\n"
            f"⏰ Час: {cancelled['time_str']}\n\n"
            "Для нового запису скористайтеся ботом.",
            parse_mode="HTML",
        )
    except Exception:
        pass

    await callback.answer("✅ Запис скасовано, клієнта сповіщено.", show_alert=True)
    # Обновляем список
    bookings = await get_all_active_bookings()
    try:
        await callback.message.edit_text(  # type: ignore
            f"📋 <b>Активні записи ({len(bookings)}):</b>",
            parse_mode="HTML",
            reply_markup=admin_bookings_kb(bookings) if bookings else back_to_main_kb(),
        )
    except Exception:
        pass
