import asyncio
import json
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
import os

# ==================== НАСТРОЙКА ====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота (получи у @BotFather)
BOT_TOKEN = "8556723456:AAFeT0XjYIF9yEYNJnyKH6VWniFLllb6nq4"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ID владельца бота (ваш ID)
OWNER_ID = 8593061718  # Замените на ваш ID Telegram

# ==================== ХРАНЕНИЕ ДАННЫХ ====================
class DataStorage:
    def __init__(self):
        self.data_file = 'bot_data.json'
        self.load_data()
    
    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        else:
            # Изначальные настройки с примером замены
            self.data = {
                'replacements': {
                    'привет': {
                        'new_text': 'Приветик! 😊',
                        'sticker_id': None,  # ID стикера для отправки
                        'enabled': True,
                        'delete_original': True,  # Удалять оригинальное сообщение
                        'send_as_new': True  # Отправлять как новое сообщение (иначе редактировать)
                    },
                    'тупой': {
                        'new_text': 'умный',
                        'sticker_id': None,
                        'enabled': True,
                        'delete_original': True,
                        'send_as_new': True
                    }
                },
                'auto_replace_enabled': True,
                'owner_id': OWNER_ID
            }
            self.save_data()
    
    def save_data(self):
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

storage = DataStorage()

# ==================== СОСТОЯНИЯ FSM ====================
class Form(StatesGroup):
    waiting_replace_trigger = State()
    waiting_replace_text = State()
    waiting_replace_sticker = State()
    waiting_replace_settings = State()

# ==================== ИНЛАЙН-КЛАВИАТУРЫ ====================
def get_main_menu() -> InlineKeyboardMarkup:
    """Главное меню с инлайн-кнопками"""
    builder = InlineKeyboardBuilder()
    
    status_icon = "✅" if storage.data['auto_replace_enabled'] else "❌"
    
    builder.row(
        InlineKeyboardButton(text=f"🔄 Автозамена: {status_icon}", 
                           callback_data="toggle_auto_replace")
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Настройка замен", callback_data="menu_replacements"),
        InlineKeyboardButton(text="⚙️ Настройки сообщений", callback_data="menu_settings")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
        InlineKeyboardButton(text="🆘 Помощь", callback_data="help")
    )
    
    return builder.as_markup()

def get_replacements_menu() -> InlineKeyboardMarkup:
    """Меню управления заменами"""
    builder = InlineKeyboardBuilder()
    
    replacements = storage.data['replacements']
    
    if not replacements:
        builder.row(
            InlineKeyboardButton(text="➕ Добавить первую замену", callback_data="add_replacement")
        )
    else:
        for trigger, data in replacements.items():
            status = "✅" if data['enabled'] else "❌"
            sticker_icon = "🖼️" if data['sticker_id'] else ""
            builder.row(
                InlineKeyboardButton(
                    text=f"{status} '{trigger}' → '{data['new_text'][:15]}...'{sticker_icon}",
                    callback_data=f"edit_replacement:{trigger}"
                )
            )
    
    builder.row(
        InlineKeyboardButton(text="➕ Добавить замену", callback_data="add_replacement"),
        InlineKeyboardButton(text="« Назад", callback_data="main_menu")
    )
    
    return builder.as_markup()

def get_edit_replacement_menu(trigger: str) -> InlineKeyboardMarkup:
    """Меню редактирования конкретной замены"""
    builder = InlineKeyboardBuilder()
    
    replace_data = storage.data['replacements'][trigger]
    
    builder.row(
        InlineKeyboardButton(text="📝 Изменить текст", 
                           callback_data=f"change_replace_text:{trigger}"),
        InlineKeyboardButton(text="🖼 Изменить стикер", 
                           callback_data=f"change_replace_sticker:{trigger}")
    )
    builder.row(
        InlineKeyboardButton(text="⚙️ Настройки отправки", 
                           callback_data=f"replace_settings:{trigger}")
    )
    builder.row(
        InlineKeyboardButton(
            text=f"{'❌ Выключить' if replace_data['enabled'] else '✅ Включить'}",
            callback_data=f"toggle_replacement:{trigger}"
        ),
        InlineKeyboardButton(text="🗑 Удалить", 
                           callback_data=f"delete_replacement:{trigger}")
    )
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="menu_replacements")
    )
    
    return builder.as_markup()

def get_replace_settings_menu(trigger: str) -> InlineKeyboardMarkup:
    """Меню настроек отправки для замены"""
    builder = InlineKeyboardBuilder()
    
    replace_data = storage.data['replacements'][trigger]
    
    delete_icon = "✅" if replace_data['delete_original'] else "❌"
    send_new_icon = "✅" if replace_data['send_as_new'] else "❌"
    
    builder.row(
        InlineKeyboardButton(
            text=f"{delete_icon} Удалять оригинал",
            callback_data=f"toggle_delete:{trigger}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"{send_new_icon} Отправлять как новое",
            callback_data=f"toggle_send_new:{trigger}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data=f"edit_replacement:{trigger}")
    )
    
    return builder.as_markup()

# ==================== ОБРАБОТЧИКИ КОМАНД ====================
@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    await message.answer(
        "🤖 **Бот для автозамены текста активирован!**\n\n"
        "✨ **Как работает:**\n"
        "• Вы пишете в чат сообщение\n"
        "• Бот находит триггерные слова (например, 'привет')\n"
        "• Бот заменяет их на настроенный текст\n"
        "• И отправляет стикер (если настроено)\n\n"
        "⚙️ **Пример:**\n"
        "Вы пишете: 'Привет всем!'\n"
        "Бот меняет на: 'Приветик всем! 😊'\n"
        "И отправляет веселый стикер\n\n"
        "Используйте меню для настройки:",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

@dp.message(Command("settings"))
async def cmd_settings(message: Message):
    """Обработчик команды /settings"""
    await message.answer(
        "⚙️ **Панель управления автозаменой**\nВыберите раздел:",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

@dp.message(Command("myid"))
async def cmd_myid(message: Message):
    """Команда для получения своего ID"""
    await message.answer(f"Ваш ID: `{message.from_user.id}`\n\n"
                        f"Добавьте его в код в переменную OWNER_ID",
                        parse_mode="Markdown")

@dp.message(Command("test"))
async def cmd_test(message: Message):
    """Тестовая команда"""
    test_text = "привет"
    if test_text in storage.data['replacements']:
        data = storage.data['replacements'][test_text]
        if data['enabled']:
            await message.answer(
                f"✅ Тест замены:\n"
                f"**Исходное:** '{test_text}'\n"
                f"**Замена:** '{data['new_text']}'\n"
                f"**Удалять оригинал:** {'Да' if data['delete_original'] else 'Нет'}\n"
                f"**Стикер:** {'Есть' if data['sticker_id'] else 'Нет'}"
            )
        else:
            await message.answer(f"❌ Замена '{test_text}' выключена")
    else:
        await message.answer(f"❌ Замена для '{test_text}' не настроена")

# ==================== ОБРАБОТЧИКИ CALLBACK-ЗАПРОСОВ ====================
@dp.callback_query(F.data == "main_menu")
async def main_menu_handler(callback: CallbackQuery):
    """Главное меню"""
    await callback.message.edit_text(
        "🤖 **Главное меню автозамены**\nВыберите раздел:",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "toggle_auto_replace")
async def toggle_auto_replace_handler(callback: CallbackQuery):
    """Включение/выключение автозамены"""
    storage.data['auto_replace_enabled'] = not storage.data['auto_replace_enabled']
    storage.save_data()
    
    status = "включена" if storage.data['auto_replace_enabled'] else "выключена"
    await callback.message.edit_text(
        f"✅ **Автозамена {status}**\n\n"
        f"Теперь бот будет {'автоматически заменять ваши сообщения' if storage.data['auto_replace_enabled'] else 'игнорировать ваши сообщения'}.",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "menu_replacements")
async def menu_replacements_handler(callback: CallbackQuery):
    """Меню замен"""
    count = len(storage.data['replacements'])
    
    await callback.message.edit_text(
        f"✏️ **Управление заменами текста**\n\n"
        f"Настроено замен: {count}\n"
        "Список ваших замен:\n"
        "✅ - включена, ❌ - выключена, 🖼️ - есть стикер",
        reply_markup=get_replacements_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("edit_replacement:"))
async def edit_replacement_handler(callback: CallbackQuery):
    """Редактирование конкретной замены"""
    trigger = callback.data.split(":")[1]
    replace_data = storage.data['replacements'].get(trigger)
    
    if not replace_data:
        await callback.answer("Замена не найдена!", show_alert=True)
        return
    
    sticker_info = f"\n• 🖼 Стикер: {'есть' if replace_data['sticker_id'] else 'не настроен'}"
    settings_info = f"\n• ⚙️ Удалять оригинал: {'Да' if replace_data['delete_original'] else 'Нет'}"
    
    await callback.message.edit_text(
        f"✏️ **Редактирование замены**\n\n"
        f"• Замена: `{trigger}` → `{replace_data['new_text']}`\n"
        f"• Статус: {'✅ Включена' if replace_data['enabled'] else '❌ Выключена'}"
        f"{sticker_info}{settings_info}\n\n"
        f"Выберите действие:",
        reply_markup=get_edit_replacement_menu(trigger),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "add_replacement")
async def add_replacement_handler(callback: CallbackQuery, state: FSMContext):
    """Добавление новой замены"""
    await callback.message.edit_text(
        "📝 **Добавление новой замены**\n\n"
        "Введите слово или фразу, которую нужно заменять\n"
        "Пример: `привет`, `тупой`, `пока`\n\n"
        "_Бот будет искать это слово в ваших сообщениях_",
        reply_markup=InlineKeyboardBuilder().add(
            InlineKeyboardButton(text="« Назад", callback_data="menu_replacements")
        ).as_markup(),
        parse_mode="Markdown"
    )
    await state.set_state(Form.waiting_replace_trigger)
    await callback.answer()

@dp.callback_query(F.data.startswith("change_replace_text:"))
async def change_replace_text_handler(callback: CallbackQuery, state: FSMContext):
    """Изменение текста замены"""
    trigger = callback.data.split(":")[1]
    await state.update_data(editing_trigger=trigger)
    
    await callback.message.edit_text(
        f"📝 **Изменение текста замены**\n\n"
        f"Текущая замена:\n`{trigger}` → `{storage.data['replacements'][trigger]['new_text']}`\n\n"
        f"Введите новый текст для замены:",
        reply_markup=InlineKeyboardBuilder().add(
            InlineKeyboardButton(text="« Назад", callback_data=f"edit_replacement:{trigger}")
        ).as_markup(),
        parse_mode="Markdown"
    )
    await state.set_state(Form.waiting_replace_text)
    await callback.answer()

@dp.callback_query(F.data.startswith("change_replace_sticker:"))
async def change_replace_sticker_handler(callback: CallbackQuery, state: FSMContext):
    """Изменение стикера для замены"""
    trigger = callback.data.split(":")[1]
    await state.update_data(editing_trigger=trigger)
    
    current_sticker = storage.data['replacements'][trigger]['sticker_id']
    sticker_info = "\n_Пришлите 'удалить' чтобы убрать стикер_" if current_sticker else ""
    
    await callback.message.edit_text(
        f"🖼 **Настройка стикера для замены '{trigger}'**\n\n"
        f"{'Стикер уже настроен' if current_sticker else 'Стикер не настроен'}"
        f"{sticker_info}\n\n"
        f"Отправьте стикер (не файл, а именно стикер):",
        reply_markup=InlineKeyboardBuilder().add(
            InlineKeyboardButton(text="« Назад", callback_data=f"edit_replacement:{trigger}")
        ).as_markup(),
        parse_mode="Markdown"
    )
    await state.set_state(Form.waiting_replace_sticker)
    await callback.answer()

@dp.callback_query(F.data.startswith("replace_settings:"))
async def replace_settings_handler(callback: CallbackQuery):
    """Настройки отправки для замены"""
    trigger = callback.data.split(":")[1]
    
    await callback.message.edit_text(
        f"⚙️ **Настройки отправки для '{trigger}'**\n\n"
        "Выберите настройки:",
        reply_markup=get_replace_settings_menu(trigger),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("toggle_delete:"))
async def toggle_delete_handler(callback: CallbackQuery):
    """Переключение удаления оригинала"""
    trigger = callback.data.split(":")[1]
    storage.data['replacements'][trigger]['delete_original'] = not storage.data['replacements'][trigger]['delete_original']
    storage.save_data()
    
    status = "включено" if storage.data['replacements'][trigger]['delete_original'] else "выключено"
    await callback.answer(f"✅ Удаление оригинала {status}", show_alert=True)
    await replace_settings_handler(callback)

@dp.callback_query(F.data.startswith("toggle_send_new:"))
async def toggle_send_new_handler(callback: CallbackQuery):
    """Переключение отправки как нового"""
    trigger = callback.data.split(":")[1]
    storage.data['replacements'][trigger]['send_as_new'] = not storage.data['replacements'][trigger]['send_as_new']
    storage.save_data()
    
    status = "новым сообщением" if storage.data['replacements'][trigger]['send_as_new'] else "редактированием"
    await callback.answer(f"✅ Отправка {status}", show_alert=True)
    await replace_settings_handler(callback)

@dp.callback_query(F.data.startswith("toggle_replacement:"))
async def toggle_replacement_handler(callback: CallbackQuery):
    """Включение/выключение замены"""
    trigger = callback.data.split(":")[1]
    replace_data = storage.data['replacements'].get(trigger)
    
    if replace_data:
        replace_data['enabled'] = not replace_data['enabled']
        storage.save_data()
        
        status = "включена" if replace_data['enabled'] else "выключена"
        await callback.answer(f"✅ Замена '{trigger}' {status}", show_alert=True)
        await edit_replacement_handler(callback)
    else:
        await callback.answer("❌ Замена не найдена", show_alert=True)

@dp.callback_query(F.data.startswith("delete_replacement:"))
async def delete_replacement_handler(callback: CallbackQuery):
    """Удаление замены"""
    trigger = callback.data.split(":")[1]
    
    if trigger in storage.data['replacements']:
        del storage.data['replacements'][trigger]
        storage.save_data()
        
        await callback.answer(f"✅ Замена '{trigger}' удалена", show_alert=True)
        await menu_replacements_handler(callback)
    else:
        await callback.answer("❌ Замена не найдена", show_alert=True)

# ==================== ОБРАБОТЧИКИ СОСТОЯНИЙ FSM ====================
@dp.message(Form.waiting_replace_trigger)
async def process_replace_trigger(message: Message, state: FSMContext):
    """Обработка нового триггера замены"""
    trigger = message.text.strip()
    
    if not trigger:
        await message.answer("❌ Триггер не может быть пустым!")
        return
    
    if trigger in storage.data['replacements']:
        await message.answer(
            f"⚠️ Замена для '{trigger}' уже существует!",
            reply_markup=get_replacements_menu()
        )
        await state.clear()
        return
    
    # Создаем новую замену
    storage.data['replacements'][trigger] = {
        'new_text': f"Замена для '{trigger}'",
        'sticker_id': None,
        'enabled': True,
        'delete_original': True,
        'send_as_new': True
    }
    storage.save_data()
    
    await state.clear()
    await message.answer(
        f"✅ Замена для '{trigger}' добавлена!\n"
        f"Теперь настройте текст замены и стикер.",
        reply_markup=get_replacements_menu()
    )

@dp.message(Form.waiting_replace_text)
async def process_replace_text(message: Message, state: FSMContext):
    """Обработка текста замены"""
    data = await state.get_data()
    trigger = data['editing_trigger']
    
    storage.data['replacements'][trigger]['new_text'] = message.text
    storage.save_data()
    
    await state.clear()
    await message.answer(
        f"✅ Текст замены для '{trigger}' обновлен!\n"
        f"Теперь: `{trigger}` → `{message.text}`",
        reply_markup=get_replacements_menu()
    )

@dp.message(Form.waiting_replace_sticker)
async def process_replace_sticker(message: Message, state: FSMContext):
    """Обработка стикера для замены"""
    if message.text and message.text.lower() == 'удалить':
        # Удаляем стикер
        data = await state.get_data()
        trigger = data['editing_trigger']
        storage.data['replacements'][trigger]['sticker_id'] = None
        storage.save_data()
        
        await state.clear()
        await message.answer(
            f"✅ Стикер для замены '{trigger}' удален!",
            reply_markup=get_replacements_menu()
        )
        return
    
    if not message.sticker:
        await message.answer("❌ Пожалуйста, отправьте стикер (не файл)!")
        return
    
    data = await state.get_data()
    trigger = data['editing_trigger']
    storage.data['replacements'][trigger]['sticker_id'] = message.sticker.file_id
    storage.save_data()
    
    await state.clear()
    await message.answer(
        f"✅ Стикер для замены '{trigger}' сохранен!",
        reply_markup=get_replacements_menu()
    )

# ==================== ОСНОВНОЙ ОБРАБОТЧИК АВТОЗАМЕНЫ ====================
@dp.message()
async def auto_replace_handler(message: Message):
    """Основной обработчик автозамены сообщений владельца"""
    
    # Проверяем, включена ли автозамена
    if not storage.data['auto_replace_enabled']:
        return
    
    # Проверяем, что сообщение от владельца
    if message.from_user.id != storage.data.get('owner_id', OWNER_ID):
        return
    
    # Игнорируем команды и служебные сообщения
    if message.text and message.text.startswith('/'):
        return
    
    # Игнорируем сообщения от самого бота
    if message.from_user.id == bot.id:
        return
    
    # Проверяем текст сообщения
    if not message.text:
        return
    
    user_text = message.text
    chat_id = message.chat.id
    message_id = message.message_id
    
    # Проверяем все замены
    for trigger, data in storage.data['replacements'].items():
        if data['enabled'] and trigger.lower() in user_text.lower():
            # Получаем новый текст (заменяем все вхождения)
            new_text = user_text
            # Простая замена без учета регистра
            import re
            new_text = re.sub(re.escape(trigger), data['new_text'], new_text, flags=re.IGNORECASE)
            
            # Если текст не изменился, пропускаем
            if new_text == user_text:
                continue
            
            try:
                # Если нужно удалить оригинал
                if data['delete_original']:
                    try:
                        await message.delete()
                    except Exception as e:
                        logger.error(f"Не удалось удалить сообщение: {e}")
                        # Если не удалось удалить, редактируем его
                        await bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=message_id,
                            text=new_text
                        )
                        message_id = None  # Сообщение уже отредактировано
                else:
                    # Отправляем как новое сообщение
                    await bot.send_message(
                        chat_id=chat_id,
                        text=new_text
                    )
                
                # Отправляем стикер, если он есть
                if data['sticker_id']:
                    await asyncio.sleep(0.3)  # Небольшая пауза
                    await bot.send_sticker(
                        chat_id=chat_id,
                        sticker=data['sticker_id']
                    )
                    
            except Exception as e:
                logger.error(f"Ошибка при обработке замены: {e}")
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ Ошибка замены: {e}"
                )
            
            break  # Обрабатываем только первую найденную замену

# ==================== ЗАПУСК БОТА ====================
async def main():
    print("🤖 Бот для автозамены запускается...")
    print(f"• Владелец: {storage.data.get('owner_id', 'Не установлен')}")
    print(f"• Замен настроено: {len(storage.data['replacements'])}")
    print(f"• Автозамена: {'ВКЛ' if storage.data['auto_replace_enabled'] else 'ВЫКЛ'}")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
