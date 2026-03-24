# ============================================================
# keyboards/booking_kb.py — Клавиатуры процесса записи
# ============================================================

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def services_kb(services: list) -> InlineKeyboardMarkup:
    """Список услуг для выбора."""
    rows = []
    for svc in services:
        hours = svc["duration_min"] // 60
        mins = svc["duration_min"] % 60
        if hours and mins:
            dur_str = f"{hours}год {mins}хв"
        elif hours:
            dur_str = f"{hours}год"
        else:
            dur_str = f"{mins}хв"
        rows.append([
            InlineKeyboardButton(
                text=f"{svc['name']}  ({dur_str})",
                callback_data=f"svc:{svc['id']}",
            )
        ])
    rows.append([InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def slots_kb(slots: list, date_str: str) -> InlineKeyboardMarkup:
    """Сетка свободных временных слотов."""
    rows = []
    row = []
    for i, slot in enumerate(slots):
        row.append(InlineKeyboardButton(
            text=f"⏰ {slot['time_str']}",
            callback_data=f"slot:{slot['id']}:{slot['time_str']}",
        ))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append([InlineKeyboardButton(text="⬅️ Обрати іншу дату", callback_data="back_to_calendar")])
    rows.append([InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_booking_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Підтвердити", callback_data="confirm_booking"),
            InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_booking_flow"),
        ],
    ])


def my_booking_kb(booking_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Скасувати запис", callback_data=f"cancel_my:{booking_id}")],
        [InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu")],
    ])


def confirm_cancel_kb(booking_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Так, скасувати", callback_data=f"do_cancel:{booking_id}"),
            InlineKeyboardButton(text="🔙 Ні, назад", callback_data="main_menu"),
        ]
    ])
