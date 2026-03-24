# ============================================================
# handlers/start.py — /start, главное меню, проверка подписки
# ============================================================

from aiogram import Router, F, Bot  # type: ignore
from aiogram.filters import CommandStart, Command  # type: ignore
from aiogram.types import Message, CallbackQuery  # type: ignore
from aiogram.exceptions import TelegramBadRequest  # type: ignore

from config import ADMIN_ID, CHANNEL_ID, CHANNEL_LINK  # type: ignore
from keyboards.main_kb import main_menu_kb, subscription_kb, back_to_main_kb  # type: ignore

router = Router()

# ─────────────────────────────────────────────────────────────
# Проверка подписки
# ─────────────────────────────────────────────────────────────

async def is_subscribed(bot: Bot, user_id: int) -> bool:
    """Проверяет, что пользователь подписан на канал."""
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status not in ("left", "kicked", "banned")
    except TelegramBadRequest:
        # Если бот не является участником канала — пропускаем проверку
        return True


async def require_subscription(message_or_callback, bot: Bot) -> bool:
    """
    Проверяет подписку. Если не подписан — отправляет сообщение.
    Возвращает True если доступ разрешён.
    """
    if isinstance(message_or_callback, Message):
        user_id = message_or_callback.from_user.id  # type: ignore
        send = message_or_callback.answer
    else:
        user_id = message_or_callback.from_user.id
        send = message_or_callback.message.answer

    if not await is_subscribed(bot, user_id):
        await send(
            "📢 <b>Для запису необхідно підписатися на канал.</b>\n\n"
            "Після підписки натисніть «✅ Перевірити підписку».",
            parse_mode="HTML",
            reply_markup=subscription_kb(CHANNEL_LINK),
        )
        return False
    return True


# ─────────────────────────────────────────────────────────────
# /start
# ─────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    user = message.from_user
    text = (
        f"👋 Привіт, <b>{user.first_name}</b>!\n\n"  # type: ignore
        "Ласкаво просимо в бот для запису до майстра манікюру. 💅\n\n"
        "Оберіть дію:"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=main_menu_kb())


# ─────────────────────────────────────────────────────────────
# Проверка подписки (callback)
# ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "check_subscription")
async def check_subscription_cb(callback: CallbackQuery, bot: Bot):
    if await is_subscribed(bot, callback.from_user.id):
        is_admin = callback.from_user.id == ADMIN_ID
        await callback.message.edit_text(  # type: ignore
            "✅ <b>Підписку підтверджено!</b>\n\nОберіть дію:",
            parse_mode="HTML",
            reply_markup=main_menu_kb(is_admin)  # type: ignore
        )
        await callback.answer()
    else:
        await callback.answer(
            "❌ Підписка не знайдена. Будь ласка, підпишіться на канал.",
            show_alert=True,
        )


# ─────────────────────────────────────────────────────────────
# Главное меню (callback)
# ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "main_menu")
async def main_menu_cb(callback: CallbackQuery):
    await callback.message.edit_text(  # type: ignore
        "🏠 <b>Головне меню</b>\n\nОберіть дію:",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )
