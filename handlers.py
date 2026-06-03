import random
import io
import logging
from PIL import Image, ImageDraw
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

import database as db
from config import ADMIN_ID, ADMIN_CHAT_ID, TASK_REWARD, MIN_WITHDRAW, TASK_LINK, SERVER_NAME
from keyboards import main_menu_kb, cancel_kb, admin_submission_kb, admin_withdraw_kb
from states import RegistrationFSM, TaskFSM, WithdrawFSM, SupportFSM, AdminFSM

main_router = Router()
admin_router = Router()
logger = logging.getLogger(__name__)

def get_notify_target():
    return ADMIN_CHAT_ID if ADMIN_CHAT_ID else ADMIN_ID

# Функция автоматической генерации графической капчи
def generate_captcha_img():
    code = str(random.randint(1000, 9999))
    img = Image.new('RGB', (130, 50), color=(30, 30, 40))
    d = ImageDraw.Draw(img)
    # Рисуем текст по центру (без внешних .ttf шрифтов, чтобы работало везде)
    d.text((35, 18), code, fill=(255, 215, 0))
    # Добавляем случайные линии для защиты от простых ботов
    for _ in range(4):
        d.line([(random.randint(0, 130), random.randint(0, 50)), (random.randint(0, 130), random.randint(0, 50))], fill=(100, 100, 100))
    
    bio = io.BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    return bio.getvalue(), code

# ------------------------------------------------------------
# СТАРТ И РЕГИСТРАЦИЯ С КАПЧЕЙ
# ------------------------------------------------------------
@main_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = await db.get_user(message.from_user.id)
    
    if user and user["minecraft_nick"]:
        await message.answer(f"👋 С возвращением на <b>{SERVER_NAME}</b>!", reply_markup=main_menu_kb(), parse_mode="HTML")
        return

    img_bytes, code = generate_captcha_img()
    await state.update_data(captcha_code=code)
    
    photo = BufferedInputFile(img_bytes, filename="captcha.png")
    await message.answer_photo(
        photo, 
        caption="🤖 <b>Решите капчу, чтобы подтвердить, что вы не робот:</b>\nВведите 4 цифры с картинки ниже👇", 
        parse_mode="HTML"
    )
    await state.set_state(RegistrationFSM.waiting_captcha)

@main_router.message(RegistrationFSM.waiting_captcha)
async def process_captcha(message: Message, state: FSMContext):
    data = await state.get_data()
    correct_code = data.get("captcha_code")
    
    if message.text and message.text.strip() == correct_code:
        await message.answer("✅ Капча решена успешно!\n\n⛏ Теперь введите ваш <b>игровой никнейм</b> на сервере Майнкрафт:", parse_mode="HTML")
        await state.set_state(RegistrationFSM.entering_minecraft_nick)
    else:
        img_bytes, code = generate_captcha_img()
        await state.update_data(captcha_code=code)
        photo = BufferedInputFile(img_bytes, filename="captcha.png")
        await message.answer_photo(photo, caption="❌ Неверно. Попробуйте еще раз. Введите цифры с картинки:", parse_mode="HTML")

@main_router.message(RegistrationFSM.entering_minecraft_nick)
async def process_nick(message: Message, state: FSMContext):
    nick = message.text.strip()
    if len(nick) < 3 or len(nick) > 16:
        await message.answer("❌ Ник должен быть от 3 до 16 символов. Попробуйте снова:")
        return
        
    await db.create_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    await db.update_user(message.from_user.id, minecraft_nick=nick)
    
    await message.answer(
        f"🎉 Регистрация завершена!\nВаш ник: <b>{nick}</b>\nУдачного заработка монет!", 
        reply_markup=main_menu_kb(), 
        parse_mode="HTML"
    )
    await state.clear()

# ------------------------------------------------------------
# ПРОФИЛЬ ИГРОКА (КРАСИВОЕ ОФОРМЛЕНИЕ)
# ------------------------------------------------------------
@main_router.message(F.text == "👤 Профиль")
async def cmd_profile(message: Message, state: FSMContext):
    await state.clear()
    user = await db.get_user(message.from_user.id)
    if not user: return

    user_id = message.from_user.id
    username_str = f"@{message.from_user.username}" if message.from_user.username else "<i>не установлен</i>"
    minecraft_nick = user['minecraft_nick']
    balance = user['balance']

    text = f"""
👤 <b>ЛИЧНЫЙ ПРОФИЛЬ | 💎 {SERVER_NAME}</b>

<blockquote>📊 <b>Статистика твоего аккаунта:</b>
├ 🆔 Твой Telegram ID: <code>{user_id}</code>
├ 👤 Юзернейм в ТГ: {username_str}
├ ⛏ Ник в Minecraft: <code>{minecraft_nick}</code>
└ 💰 Текущий баланс: <code>{balance:,} 🪙</code></blockquote>

📈 Выполняй бесконечные квесты во вкладке <b>«📋 Задание»</b>, зарабатывай монеты и выводи их прямо на сервере!
"""
    await message.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")

# ------------------------------------------------------------
# БЕСКОНЕЧНОЕ ЗАДАНИЕ (ГОЛОСОВАНИЕ)
# ------------------------------------------------------------
@main_router.message(F.text == "📋 Задание")
async def show_task(message: Message, state: FSMContext):
    await state.clear()
    user = await db.get_user(message.from_user.id)
    if not user: return

    text = f"""
<b>📋 ЗАДАНИЕ: Проголосовать за канал</b>

<blockquote>📢 <b>Условия квеста:</b>
Отдать 4 голоса в наш канал {TASK_LINK}
В ответ пришлите скриншот, подтверждающий, что вы кинули 4 голоса!</blockquote>

🪙 <b>Награда:</b> <code>{TASK_REWARD:,} 🪙</code>
♾ <b>Доступность:</b> Бесконечное (Можно выполнять много раз!)

👇 Нажмите кнопку ниже, чтобы отправить скриншот отчета.
"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔗 Перейти к каналу", url=TASK_LINK))
    builder.row(InlineKeyboardButton(text="📸 Отправить скриншот", callback_data="send_report"))
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@main_router.callback_query(F.data == "send_report")
async def send_report_start(call: CallbackQuery, state: FSMContext):
    await call.message.answer("📸 <b>Отправьте скриншот-подтверждение</b> выполнения задания:", reply_markup=cancel_kb(), parse_mode="HTML")
    await state.set_state(TaskFSM.waiting_screenshot)
    await call.answer()

@main_router.message(TaskFSM.waiting_screenshot, F.photo)
async def receive_screenshot(message: Message, state: FSMContext, bot: Bot):
    photo_id = message.photo[-1].file_id
    user = await db.get_user(message.from_user.id)
    
    sub_id = await db.add_submission(message.from_user.id, photo_id)
    await message.answer("✅ <b>Скриншот отправлен на проверку!</b>\nПосле одобрения админом вы получите монеты.", reply_markup=main_menu_kb(), parse_mode="HTML")
    await state.clear()
    
    target = get_notify_target()
    username_str = f"@{message.from_user.username}" if message.from_user.username else "Нет"
    caption = (
        f"<b>📸 НОВЫЙ ОТЧЕТ ЗАДАНИЯ #{sub_id}</b>\n\n"
        f"👤 Игрок: {message.from_user.full_name} ({username_str})\n"
        f"⛏ Ник в Майнкрафт: <code>{user['minecraft_nick']}</code>\n"
        f"🆔 Telegram ID: <code>{message.from_user.id}</code>"
    )
    await bot.send_photo(chat_id=target, photo=photo_id, caption=caption, reply_markup=admin_submission_kb(sub_id, message.from_user.id), parse_mode="HTML")

# ------------------------------------------------------------
# ВЫВОД СРЕДСТВ (КРАСИВОЕ ОФОРМЛЕНИЕ)
# ------------------------------------------------------------
@main_router.message(F.text == "💸 Вывод")
async def show_withdraw(message: Message, state: FSMContext = None):
    if state: await state.clear()
    user = await db.get_user(message.from_user.id)
    if not user: return
    
    balance = user["balance"]
    status_emoji = "✅" if balance >= MIN_WITHDRAW else "❌"
    status_text = "Доступно к выводу!" if balance >= MIN_WITHDRAW else f"Недостаточно монет (минимум {MIN_WITHDRAW:,})"

    text = f"""
💳 <b>ВЫВОД СРЕДСТВ | 💎 {SERVER_NAME}</b>

<blockquote>🌟 <b>Условия вывода:</b>
└ 🔸 Минимальная сумма: <code>{MIN_WITHDRAW:,} 🪙</code></blockquote>

📋 <b>Инструкция (как получить монеты):</b>
<blockquote>1️⃣ Проверь правильность своего никнейма.
2️⃣ Выставь <b>1 блок земли</b> за цену вывода $.
3️⃣ Нажми кнопку <i>«💸 Подать заявку»</i>.
4️⃣ Ожидай выкупа лота администратором.

⚠️ <b>Важно:</b> Не отменяй лот до завершения сделки!</blockquote>

📊 <b>Состояние твоего счёта:</b>
├ 💰 Баланс: <code>{balance:,} 🪙</code>
└ {status_emoji} Статус: <b>{status_text}</b>

👤 <b>Твой текущий ник:</b> <code>{user['minecraft_nick']}</code>
"""

    builder = InlineKeyboardBuilder()
    if balance >= MIN_WITHDRAW:
        builder.row(InlineKeyboardButton(text="💸 Подать заявку", callback_data="apply_withdraw"))
    else:
        builder.row(InlineKeyboardButton(text="🔒 Недостаточно средств", callback_data="low_balance_alert"))
    builder.row(InlineKeyboardButton(text="📝 Изменить ник", callback_data="change_nick_withdraw"))
    
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@main_router.callback_query(F.data == "low_balance_alert")
async def low_balance_cb(call: CallbackQuery):
    await call.answer("❌ На вашем балансе меньше 200,000 монет!", show_alert=True)

@main_router.callback_query(F.data == "change_nick_withdraw")
async def change_nick_start(call: CallbackQuery, state: FSMContext):
    await call.message.answer("📝 <b>Введите ваш новый никнейм на сервере:</b>", reply_markup=cancel_kb(), parse_mode="HTML")
    await state.set_state(WithdrawFSM.changing_nick)
    await call.answer()

@main_router.message(WithdrawFSM.changing_nick)
async def change_nick_proc(message: Message, state: FSMContext):
    nick = message.text.strip()
    if len(nick) < 3 or len(nick) > 16:
        await message.answer("❌ Неверный ник. Введите от 3 до 16 символов:")
        return
    await db.update_user(message.from_user.id, minecraft_nick=nick)
    await message.answer(f"✅ Игровой ник успешно изменен на <b>{nick}</b>!", parse_mode="HTML")
    await state.clear()
    await show_withdraw(message)

@main_router.callback_query(F.data == "apply_withdraw")
async def apply_withdraw_execute(call: CallbackQuery, bot: Bot):
    user = await db.get_user(call.from_user.id)
    if not user or user["balance"] < MIN_WITHDRAW:
        await call.answer("❌ Ошибка баланса", show_alert=True)
        return
        
    amount = user["balance"]
    req_id = await db.add_withdraw_request(call.from_user.id, amount, user["minecraft_nick"])
    await db.subtract_balance(call.from_user.id, amount)
    
    await call.message.answer("✅ <b>Заявка успешно отправлена!</b>\nАдминистратор проверит лот аукциона и выкупит его.", reply_markup=main_menu_kb(), parse_mode="HTML")
    
    target = get_notify_target()
    username_str = f"@{call.from_user.username}" if call.from_user.username else "Нет"
    admin_msg = (
        f"💸 <b>ЗАЯВКА НА ВЫВОД #{req_id}</b>\n\n"
        f"👤 Игрок: {call.from_user.full_name} ({username_str})\n"
        f"⛏ Ник в Minecraft: <code>{user['minecraft_nick']}</code>\n"
        f"💰 Сумма выкупа: <code>{amount:,} $</code>\n"
        f"⚠️ Инструкция: Зайдите на сервер и выкупите 1 блок земли у этого игрока."
    )
    await bot.send_message(chat_id=target, text=admin_msg, reply_markup=admin_withdraw_kb(req_id, call.from_user.id), parse_mode="HTML")
    await call.answer()

# ------------------------------------------------------------
# ТЕХНИЧЕСКАЯ ПОДДЕРЖКА
# ------------------------------------------------------------
@main_router.message(F.text == "🆘 Тех. поддержка")
async def support_welcome(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("💬 <b>Добро пожаловать в техподдержку!</b>\nНапишите ваш вопрос или проблему в следующем сообщении:", reply_markup=cancel_kb(), parse_mode="HTML")
    await state.set_state(SupportFSM.chatting)

@main_router.message(SupportFSM.chatting)
async def support_msg_handle(message: Message, state: FSMContext, bot: Bot):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Вы вышли в главное меню.", reply_markup=main_menu_kb())
        return

    user = await db.get_user(message.from_user.id)
    target = get_notify_target()
    username_str = f"@{message.from_user.username}" if message.from_user.username else "Нет"
    
    await message.answer("✅ <b>Ваше сообщение отправлено администрации!</b>\nОжидайте ответа прямо здесь.", parse_mode="HTML", reply_markup=main_menu_kb())
    await state.clear()
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💬 Ответить игроку", callback_data=f"rep_sup:{message.from_user.id}"))
    
    await bot.send_message(
        chat_id=target,
        text=f"🆘 <b>ТИКЕТ ПОДДЕРЖКИ</b>\n\n👤 От: {message.from_user.full_name} ({username_str})\n⛏ Игровой ник: <code>{user['minecraft_nick']}</code>\n🆔 ID: <code>{message.from_user.id}</code>\n\n📝 <b>Текст обращения:</b>\n{message.text}",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

# ------------------------------------------------------------
# ОБРАБОТЧИКИ КНОПОК МОДЕРАЦИИ (АДМИН-ПАНЕЛЬ)
# ------------------------------------------------------------
@admin_router.callback_query(F.data.startswith("app_t:"))
async def approve_task_callback(call: CallbackQuery, bot: Bot):
    _, sub_id, user_id = call.data.split(":")
    sub = await db.get_submission(int(sub_id))
    if not sub or sub["status"] != "pending":
        await call.answer("❌ Заявка уже обработана!", show_alert=True)
        return
    await db.update_submission(int(sub_id), "approved")
    await db.add_balance(int(user_id), TASK_REWARD)
    await call.message.edit_caption(caption=call.message.caption + f"\n\n✅ <b>ОДОБРЕНО! Начислено {TASK_REWARD:,} монет.</b>", parse_mode="HTML")
    try:
        await bot.send_message(int(user_id), f"🎉 <b>Ваш отчет одобрен!</b>\nНа ваш баланс зачислено: <code>{TASK_REWARD:,} 🪙</code>", parse_mode="HTML")
    except: pass
    await call.answer()

@admin_router.callback_query(F.data.startswith("rej_t:"))
async def reject_task_callback(call: CallbackQuery, bot: Bot):
    _, sub_id, user_id = call.data.split(":")
    sub = await db.get_submission(int(sub_id))
    if not sub or sub["status"] != "pending":
        await call.answer("❌ Заявка уже обработана!", show_alert=True)
        return
    await db.update_submission(int(sub_id), "rejected")
    await call.message.edit_caption(caption=call.message.caption + "\n\n❌ <b>ОТКЛОНЕНО АДМИНИСТРАТОРОМ!</b>", parse_mode="HTML")
    try:
        await bot.send_message(int(user_id), "❌ <b>Ваш отчет по заданию был отклонен.</b>\nПроверьте выполнение условий и отправьте скриншот заново.")
    except: pass
    await call.answer()

@admin_router.callback_query(F.data.startswith("app_w:"))
async def approve_withdraw_callback(call: CallbackQuery, bot: Bot):
    _, req_id, user_id = call.data.split(":")
    req = await db.get_withdraw_request(int(req_id))
    if not req or req["status"] != "pending":
        await call.answer("❌ Заявка уже обработана!", show_alert=True)
        return
    await db.update_withdraw_request(int(req_id), "approved")
    await call.message.edit_text(text=call.message.text + "\n\n✅ <b>ВЫПЛАЧЕНО (ЛОТ ВЫКУПЛЕН)</b>", parse_mode="HTML")
    try:
        await bot.send_message(int(user_id), f"✅ <b>Ваш вывод средств одобрен!</b>\nАдминистратор выкупил ваш лот земли на аукционе.")
    except: pass
    await call.answer()

@admin_router.callback_query(F.data.startswith("rej_w:"))
async def reject_withdraw_callback(call: CallbackQuery, bot: Bot):
    _, req_id, user_id = call.data.split(":")
    req = await db.get_withdraw_request(int(req_id))
    if not req or req["status"] != "pending":
        await call.answer("❌ Заявка уже обработана!", show_alert=True)
        return
    await db.update_withdraw_request(int(req_id), "rejected")
    await db.add_balance(int(user_id), req["amount"]) 
    await call.message.edit_text(text=call.message.text + "\n\n❌ <b>ОТКЛОНЕНО. Монеты возвращены на баланс игрока.</b>", parse_mode="HTML")
    try:
        await bot.send_message(int(user_id), f"❌ <b>Ваша заявка на вывод была отклонена.</b>\nМонеты возвращены на ваш баланс. Проверьте ваш лот на аукционе сервера.")
    except: pass
    await call.answer()

@admin_router.callback_query(F.data.startswith("rep_sup:"))
async def admin_reply_support_start(call: CallbackQuery, state: FSMContext):
    user_id = call.data.split(":")[1]
    await call.message.answer(f"✏️ <b>Введите ответ для пользователя</b> <code>{user_id}</code>:", parse_mode="HTML")
    await state.update_data(reply_user_id=int(user_id))
    await state.set_state(AdminFSM.replying_support)
    await call.answer()

@admin_router.message(AdminFSM.replying_support)
async def admin_reply_support_send(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user_id = data.get("reply_user_id")
    await state.clear()
    
    try:
        await bot.send_message(chat_id=user_id, text=f"📩 <b>Ответ от тех. поддержки сервера:</b>\n\n{message.text}", parse_mode="HTML")
        await message.answer("✅ Ответ успешно доставлен игроку!")
    except:
        await message.answer("❌ Не удалось отправить сообщение. Возможно, игрок заблокировал бота.")

# Глобальная команда отмены стейтов для Reply-кнопок
@main_router.message(F.text == "❌ Отмена")
async def global_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=main_menu_kb())

# Заглушка на неизвестный текст
@main_router.message()
async def fallback_handler(message: Message):
    await message.answer("🤷‍♂️ Воспользуйтесь кнопками меню для управления ботом.", reply_markup=main_menu_kb())