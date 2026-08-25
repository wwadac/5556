"""Клавиатуры бота"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import config


def get_main_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📨 Мои переписки", callback_data="my_dialogs"),
        InlineKeyboardButton(text="📊 Мой профиль", callback_data="my_profile")
    )
    builder.row(
        InlineKeyboardButton(text="💳 Подписка", callback_data="subscription"),
        InlineKeyboardButton(text="❓ Помощь", callback_data="help")
    )
    if is_admin:
        builder.row(InlineKeyboardButton(text="🔐 Админ-панель", callback_data="admin_panel"))
    return builder.as_markup()


def get_admin_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")
    )
    builder.row(
        InlineKeyboardButton(text="✅ Проверить платёж", callback_data="admin_verify")
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_main"))
    return builder.as_markup()


def get_dialogs_keyboard(dialogs: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for d in dialogs:
        name = d.get("peer_name") or d.get("peer_username") or f"ID: {d['peer_id']}"
        count = d.get("message_count", 0)
        builder.row(InlineKeyboardButton(
            text=f"💬 {name} ({count})",
            callback_data=f"dialog:{d['chat_id']}"
        ))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_main"))
    return builder.as_markup()


def get_dialog_actions_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📥 Скачать чат", callback_data=f"download:{chat_id}")
    )
    builder.row(InlineKeyboardButton(text="◀️ К перепискам", callback_data="my_dialogs"))
    return builder.as_markup()


def get_payment_keyboard(code: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📤 Отправить скриншот", callback_data=f"screenshot:{code}"))
    builder.row(InlineKeyboardButton(text="🔄 Новый код", callback_data="new_code"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_main"))
    return builder.as_markup()


def get_channel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📢 Подписаться", url=config.REQUIRED_CHANNEL_LINK))
    builder.row(InlineKeyboardButton(text="✅ Я подписался", callback_data="check_channel"))
    return builder.as_markup()


def get_verify_keyboard(payment_id: int, user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"verify_pay:{payment_id}:{user_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_pay:{payment_id}:{user_id}")
    )
    return builder.as_markup()


def get_back_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_main"))
    return builder.as_markup()
