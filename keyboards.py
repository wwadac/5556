from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

def main_menu_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📋 Задание"), KeyboardButton(text="👤 Профиль"))
    builder.row(KeyboardButton(text="💸 Вывод"), KeyboardButton(text="🆘 Тех. поддержка"))
    return builder.as_markup(resize_keyboard=True)

def cancel_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True)

def admin_submission_kb(sub_id: int, user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Одобрить (+300к)", callback_data=f"app_t:{sub_id}:{user_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"rej_t:{sub_id}:{user_id}")
    )
    return builder.as_markup()

def admin_withdraw_kb(req_id: int, user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Выплачено", callback_data=f"app_w:{req_id}:{user_id}"),
        InlineKeyboardButton(text="❌ Отклонить (Вернуть баланс)", callback_data=f"rej_w:{req_id}:{user_id}")
    )
    return builder.as_markup()