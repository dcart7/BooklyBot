
# Портфолио

from aiogram import Router, F # type: ignore
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message # type: ignore
from aiogram.fsm.context import FSMContext # type: ignore
from aiogram.fsm.state import State, StatesGroup # type: ignore

from database.db import get_setting, set_setting # type: ignore
from keyboards.main_kb import back_to_main_kb # type: ignore

router = Router()


class PortfolioStates(StatesGroup):
    waiting_for_link = State()


@router.callback_query(F.data == "portfolio")
async def show_portfolio(callback: CallbackQuery):
    link = await get_setting("portfolio_link") or "https://t.me/"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖼 Дивитися портфоліо", url=link)],
        [InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu")],
    ])
    await callback.message.edit_text(  # type: ignore
        "🖼 <b>Портфоліо майстра</b>\n\nНатисніть кнопку нижче, щоб переглянути роботи:",
        parse_mode="HTML",
        reply_markup=kb,
    )



# Редактирование ссылки (администратор)

@router.callback_query(F.data == "adm:portfolio")
async def admin_edit_portfolio(callback: CallbackQuery, state: FSMContext):
    current = await get_setting("portfolio_link") or ""
    await callback.message.edit_text(  # type: ignore
        f"🔗 <b>Зміна посилання портфоліо</b>\n\n"
        f"Поточне посилання: {current}\n\n"
        "Надішліть нове посилання:",
        parse_mode="HTML",
    )
    await state.set_state(PortfolioStates.waiting_for_link)


@router.message(PortfolioStates.waiting_for_link)
async def save_portfolio_link(message: Message, state: FSMContext):
    link = message.text.strip()  # type: ignore
    if not link.startswith("http"):
        await message.answer("❌ Некоректне посилання. Введіть URL, що починається з http.")
        return
    await set_setting("portfolio_link", link)
    await state.clear()
    await message.answer(
        "✅ <b>Посилання на портфоліо оновлено!</b>",
        parse_mode="HTML",
        reply_markup=back_to_main_kb(),
    )
