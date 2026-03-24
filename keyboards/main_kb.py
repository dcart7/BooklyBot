# ============================================================
# keyboards/main_kb.py — Главное меню
# ============================================================

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_kb(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Головне меню користувача."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Записатися", callback_data="book_start")],
        [InlineKeyboardButton(text="📋 Мої записи", callback_data="my_bookings")],
        [
            InlineKeyboardButton(text="💰 Прайс", callback_data="prices"),
            InlineKeyboardButton(text="🖼 Портфоліо", callback_data="portfolio"),
        ],
    ])


def subscription_kb(channel_link: str) -> InlineKeyboardMarkup:
    """Клавіатура перевірки підписки на канал."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Підписатися", url=channel_link)],
        [InlineKeyboardButton(text="✅ Перевірити підписку", callback_data="check_subscription")],
    ])


def back_to_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu")]
    ])
