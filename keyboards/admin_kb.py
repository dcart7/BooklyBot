# ============================================================
# keyboards/admin_kb.py — Клавиатуры админ-панели
# ============================================================

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def admin_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Робочі дні", callback_data="adm:days")],
        [InlineKeyboardButton(text="⏰ Слоти", callback_data="adm:slots")],
        [InlineKeyboardButton(text="📋 Записи клієнтів", callback_data="adm:bookings")],
        [InlineKeyboardButton(text="💰 Редагувати прайс", callback_data="adm:prices")],
        [InlineKeyboardButton(text="🔗 Змінити портфоліо", callback_data="adm:portfolio")],
    ])


def admin_days_kb(working_days: list) -> InlineKeyboardMarkup:
    """Список рабочих дней с кнопками управления."""
    rows = []
    for day in working_days:
        status = "🔴" if day["is_closed"] else "🟢"
        rows.append([
            InlineKeyboardButton(
                text=f"{status} {day['date']}",
                callback_data=f"adm:day_info:{day['date']}",
            )
        ])
    rows.append([InlineKeyboardButton(text="➕ Додати день", callback_data="adm:add_day")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="adm:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_day_manage_kb(date_str: str, is_closed: bool) -> InlineKeyboardMarkup:
    toggle_text = "🟢 Відкрити день" if is_closed else "🔴 Закрити день"
    toggle_cb = f"adm:open_day:{date_str}" if is_closed else f"adm:close_day:{date_str}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏰ Керування слотами", callback_data=f"adm:manage_slots:{date_str}")],
        [InlineKeyboardButton(text=toggle_text, callback_data=toggle_cb)],
        [InlineKeyboardButton(text="🗑 Видалити день", callback_data=f"adm:delete_day:{date_str}")],
        [InlineKeyboardButton(text="📋 Записи на цей день", callback_data=f"adm:day_bookings:{date_str}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="adm:days")],
    ])


def admin_slots_kb(slots: list, date_str: str) -> InlineKeyboardMarkup:
    """Список слотов дня с кнопками удаления."""
    rows = []
    for slot in slots:
        status = "🟢" if slot["is_available"] else "🔴"
        rows.append([
            InlineKeyboardButton(
                text=f"{status} {slot['time_str']}",
                callback_data=f"adm:slot_info:{date_str}:{slot['time_str']}",
            )
        ])
    rows.append([InlineKeyboardButton(text="➕ Додати слот", callback_data=f"adm:add_slot:{date_str}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"adm:day_info:{date_str}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_slot_manage_kb(date_str: str, time_str: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Видалити слот", callback_data=f"adm:del_slot:{date_str}:{time_str}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"adm:manage_slots:{date_str}")],
    ])


def admin_bookings_kb(bookings: list) -> InlineKeyboardMarkup:
    """Список активных бронирований."""
    rows = []
    for b in bookings:
        rows.append([
            InlineKeyboardButton(
                text=f"📅 {b['date']} {b['time_str']} — {b['user_name']}",
                callback_data=f"adm:booking:{b['id']}",
            )
        ])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="adm:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_booking_manage_kb(booking_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Скасувати запис", callback_data=f"adm:cancel_booking:{booking_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="adm:bookings")],
    ])


def admin_date_select_kb(working_days: list, prefix: str = "adm:view_date") -> InlineKeyboardMarkup:
    rows = []
    for day in working_days:
        rows.append([
            InlineKeyboardButton(text=day["date"], callback_data=f"{prefix}:{day['date']}")
        ])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="adm:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
