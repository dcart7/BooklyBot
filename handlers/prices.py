# ============================================================
# handlers/prices.py — Прайс-лист
# ============================================================

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db import get_setting, set_setting
from keyboards.main_kb import back_to_main_kb

router = Router()


class PriceStates(StatesGroup):
    waiting_for_price_text = State()


# ─────────────────────────────────────────────────────────────
# Просмотр прайса (пользователь)
# ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "prices")
async def show_prices(callback: CallbackQuery):
    price_html = await get_setting("price_list_html")
    await callback.message.edit_text(  # type: ignore
        price_html or "Прайс ще не налаштований.",
        parse_mode="HTML",
        reply_markup=back_to_main_kb(),
    )


# ─────────────────────────────────────────────────────────────
# Редактирование прайса (администратор)  /setprices
# ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:prices")
async def admin_edit_prices(callback: CallbackQuery, state: FSMContext):
    current = await get_setting("price_list_html") or ""
    await callback.message.edit_text(  # type: ignore
        "💰 <b>Редагування прайсу</b>\n\n"
        "Надішліть новий текст прайсу у форматі HTML.\n\n"
        f"<b>Поточний текст:</b>\n{current}",
        parse_mode="HTML",
    )
    await state.set_state(PriceStates.waiting_for_price_text)


@router.message(PriceStates.waiting_for_price_text)
async def save_price_list(message: Message, state: FSMContext):
    await set_setting("price_list_html", message.html_text)
    await state.clear()
    await message.answer(
        "✅ <b>Прайс оновлено!</b>",
        parse_mode="HTML",
        reply_markup=back_to_main_kb(),
    )
