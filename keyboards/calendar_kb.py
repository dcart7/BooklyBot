# ============================================================
# keyboards/calendar_kb.py — Inline-календарь
# ============================================================

import calendar
from datetime import datetime, date, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

MONTHS_RU = [
    "", "Січ", "Лют", "Бер", "Квіт", "Трав", "Черв",
    "Лип", "Серп", "Вер", "Жовт", "Лист", "Груд",
]
WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]


def build_calendar(year: int, month: int, available_dates: list[str]) -> InlineKeyboardMarkup:
    """
    Строит inline-календарь.
    available_dates — список строк 'YYYY-MM-DD' со свободными слотами.
    """
    buttons: list[list[InlineKeyboardButton]] = []

    # Заголовок: кнопки навигации и название месяца
    year_short = str(year)[-2:]
    header = [
        InlineKeyboardButton(text="◀️", callback_data=f"cal:prev:{year}:{month}"),
        InlineKeyboardButton(text=f"{MONTHS_RU[month]} {year_short}", callback_data="cal:ignore"),
        InlineKeyboardButton(text="▶️", callback_data=f"cal:next:{year}:{month}"),
    ]
    buttons.append(header)

    # Дни недели
    buttons.append([
        InlineKeyboardButton(text=d, callback_data="cal:ignore") for d in WEEKDAYS_RU
    ])

    # Сетка дней
    month_calendar = calendar.monthcalendar(year, month)
    today = date.today()

    for week in month_calendar:
        row = []
        for day_num in week:
            if day_num == 0:
                row.append(InlineKeyboardButton(text="·", callback_data="cal:ignore"))
            else:
                d = date(year, month, day_num)
                date_str = d.strftime("%Y-%m-%d")
                if d < today:
                    # Прошедшие дни — недоступны
                    row.append(InlineKeyboardButton(text=f"·{day_num}", callback_data="cal:ignore"))
                elif date_str in available_dates:
                    # Доступна запись
                    row.append(InlineKeyboardButton(
                        text=f"✅ {day_num}",
                        callback_data=f"cal:day:{date_str}",
                    ))
                else:
                    # Нет свободных слотов
                    row.append(InlineKeyboardButton(text=f"❌ {day_num}", callback_data="cal:ignore"))
        buttons.append(row)

    # Кнопка «Назад»
    buttons.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_services")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_prev_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def get_next_month(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1
    return year, month + 1
