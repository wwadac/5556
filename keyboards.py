from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Первый ответ", callback_data="first_text")],
        [InlineKeyboardButton(text="🎭 Стикер", callback_data="sticker")],
        [InlineKeyboardButton(text="💬 Ответ после сообщения", callback_data="followup")],
        [InlineKeyboardButton(text="⏱ Задержка", callback_data="delay")],
        [InlineKeyboardButton(text="👁 Визуальные эффекты", callback_data="visual")],
        [InlineKeyboardButton(text="🔴 Вкл / Выкл", callback_data="toggle")]
    ])
