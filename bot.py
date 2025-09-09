import os
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler
)
from database import Database

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота и ID создателя - ОБНОВЛЕННЫЙ ТОКЕН!
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8487564738:AAEwVt2D_qzko-0XhbxAtuvp1yLX8aygNRI')
CREATOR_ID = 8097784914
PAYMENT_BOT_URL = os.environ.get('PAYMENT_BOT_URL', 'http://t.me/send?start=IVwpcz1iEoxg')

# Состояния для ConversationHandler
REGISTER_USERNAME, REGISTER_PASSWORD, REGISTER_NICKNAME, REGISTER_WALLET = range(4)
ROOM_SELECTION, ROOM_CHAT, CREATE_ROOM_NAME, CREATE_ROOM_TYPE, CREATE_ROOM_PERSISTENCE, CREATE_ROOM_PASSWORD = range(4, 10)
TRANSFER_USER, TRANSFER_AMOUNT = range(10, 12)
ADMIN_ACTION, BAN_USER, MUTE_USER, MUTE_DURATION, MAKE_ADMIN = range(12, 17)
PAYMENT_CONFIRMATION = 17

# Инициализация базы данных
db = Database()

# Клавиатуры
def main_keyboard():
    return ReplyKeyboardMarkup([
        ['👤 Профиль', '💬 Анонимный чат'],
        ['💰 Передать USD', '➕ Создать комнату'],
        ['💳 Пополнить баланс']
    ], resize_keyboard=True)

def admin_keyboard():
    return ReplyKeyboardMarkup([
        ['👤 Профиль', '💬 Анонимный чат'],
        ['💰 Передать USD', '➕ Создать комнату'],
        ['💳 Пополнить баланс', '⚙️ Админ панель']
    ], resize_keyboard=True)

def rooms_keyboard():
    rooms = db.get_rooms()
    keyboard = []
    for room in rooms:
        keyboard.append([f"🚪 {room[1]}"])
    keyboard.append(['🔙 Назад'])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def admin_panel_keyboard():
    return ReplyKeyboardMarkup([
        ['🔨 Бан', '🔇 Мут'],
        ['👥 Все пользователи', '👑 Назначить админа'],
        ['🔙 Назад']
    ], resize_keyboard=True)

def payment_amount_keyboard():
    return ReplyKeyboardMarkup([
        ['5 USD', '10 USD', '20 USD'],
        ['50 USD', '100 USD', '🔙 Назад']
    ], resize_keyboard=True)

# Функция для создания платежа
async def create_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, amount, payment_type, details):
    # Генерируем уникальный ID платежа
    payment_id = db.add_pending_payment(user_id, amount, payment_type, details)
    
    if payment_id:
        # Создаем ссылку для оплаты
        payment_url = f"{PAYMENT_BOT_URL}_{payment_id}_{amount}"
        
        payment_text = (
            f"💳 Оплата {amount} USD\n\n"
            f"📋 Тип: {payment_type}\n"
            f"🔗 Для оплаты перейдите по ссылке:\n{payment_url}\n\n"
            f"После оплаты средства будут зачислены на ваш баланс автоматически."
        )
        
        await update.message.reply_text(payment_text)
        return True
    return False

# Обработка платежей
async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        payment_data = context.args[0].split('_')
        if len(payment_data) >= 3:
            payment_id = int(payment_data[1])
            amount = float(payment_data[2])
            
            payment = db.get_pending_payment(payment_id)
            if payment and not payment[6]:  # is_completed = 0
                # Зачисляем средства
                db.update_balance(payment[1], amount)
                db.complete_payment(payment_id)
                
                user = db.get_user(payment[1])
                if user:
                    await update.message.reply_text(
                        f"✅ Оплата {amount} USD успешно зачислена на ваш баланс!\n"
                        f"💰 Текущий баланс: {user[6] + amount} USD",
                        reply_markup=main_keyboard() if not user[7] else admin_keyboard()
                    )
                else:
                    await update.message.reply_text(
                        f"✅ Оплата {amount} USD успешно зачислена!",
                        reply_markup=main_keyboard()
                    )
            else:
                await update.message.reply_text("Платеж уже обработан или не найден.")
        else:
            await update.message.reply_text("Неверный формат платежа.")
    except Exception as e:
        await update.message.reply_text("Ошибка обработки платежа.")
        logger.error(f"Payment error: {e}")

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем, не является ли это оплатой
    if context.args and context.args[0].startswith('IVwpcz1iEoxg_'):
        await handle_payment(update, context)
        return ConversationHandler.END
    
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if user:
        # Пользователь уже зарегистрирован
        if user_id == CREATOR_ID or user[7]:  # is_admin
            await update.message.reply_text(
                f"Добро пожаловать назад, {user[3]}! 👑",
                reply_markup=admin_keyboard()
            )
        else:
            await update.message.reply_text(
                f"Добро пожаловать назад, {user[3]}!",
                reply_markup=main_keyboard()
            )
        return ConversationHandler.END
    else:
        # Новый пользователь
        await update.message.reply_text(
            "Добро пожаловать в PPZ! Для использования бота необходимо зарегистрироваться.\n"
            "Введите ваш username:"
        )
        return REGISTER_USERNAME

# Обработчики регистрации
async def register_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['username'] = update.message.text
    await update.message.reply_text("Отлично! Теперь введите ваш пароль:")
    return REGISTER_PASSWORD

async def register_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['password'] = update.message.text
    await update.message.reply_text("Теперь придумайте уникальный псевдоним:")
    return REGISTER_NICKNAME

async def register_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nickname = update.message.text
    if db.get_user_by_nickname(nickname):
        await update.message.reply_text("Этот псевдоним уже занят. Пожалуйста, выберите другой:")
        return REGISTER_NICKNAME
    
    context.user_data['nickname'] = nickname
    await update.message.reply_text("Теперь введите адрес вашего крипто-кошелька:")
    return REGISTER_WALLET

async def register_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallet = update.message.text
    user_id = update.effective_user.id
    username = context.user_data['username']
    password = context.user_data['password']
    nickname = context.user_data['nickname']
    
    if db.add_user(user_id, username, password, nickname, wallet):
        await update.message.reply_text(
            "Регистрация завершена! Теперь вы можете пользоваться ботом.",
            reply_markup=main_keyboard()
        )
    else:
        await update.message.reply_text(
            "Произошла ошибка при регистрации. Попробуйте снова с помощью /start"
        )
    
    return ConversationHandler.END

# Обработка текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    text = update.message.text
    
    if not user:
        await update.message.reply_text("Пожалуйста, зарегистрируйтесь с помощью /start")
        return
    
    if db.is_muted(user_id):
        await update.message.reply_text("Вы заблокированы от отправки сообщений.")
        return
    
    if text == '👤 Профиль':
        await show_profile(update, user)
    elif text == '💬 Анонимный чат':
        await update.message.reply_text("Выберите комнату:", reply_markup=rooms_keyboard())
    elif text == '💰 Передать USD':
        await update.message.reply_text("Введите псевдоним пользователя, которому хотите передать USD:")
        return TRANSFER_USER
    elif text == '➕ Создать комнату':
        await update.message.reply_text("Введите название для новой комнаты:")
        return CREATE_ROOM_NAME
    elif text == '💳 Пополнить баланс':
        await update.message.reply_text(
            "Выберите сумму для пополнения:",
            reply_markup=payment_amount_keyboard()
        )
        return PAYMENT_CONFIRMATION
    elif text == '⚙️ Админ панель' and (user_id == CREATOR_ID or user[7]):
        await update.message.reply_text("Админ панель:", reply_markup=admin_panel_keyboard())
        return ADMIN_ACTION
    elif text.startswith('🚪 '):
        room_name = text[2:]
        await join_room(update, context, room_name)
    elif text == '🔙 Назад':
        if user_id == CREATOR_ID or user[7]:
            await update.message.reply_text("Главное меню:", reply_markup=admin_keyboard())
        else:
            await update.message.reply_text("Главное меню:", reply_markup=main_keyboard())
        return ConversationHandler.END

# Показать профиль
async def show_profile(update: Update, user):
    profile_text = (
        f"👤 Ваш профиль:\n\n"
        f"🆔 ID: {user[1]}\n"
        f"👤 Псевдоним: {user[3]}\n"
        f"🔑 Пароль: {user[2]}\n"
        f"💰 Баланс: {user[6]} USD\n"
        f"📊 Крипто-кошелек: {user[4]}"
    )
    await update.message.reply_text(profile_text)

# Анонимный чат
async def join_room(update: Update, context: ContextTypes.DEFAULT_TYPE, room_name):
    user_id = update.effective_user.id
    rooms = db.get_rooms()
    
    for room in rooms:
        if room[1] == room_name:
            if room[4]:  # is_private
                await update.message.reply_text("Эта комната приватная. Введите пароль:")
                context.user_data['room_id'] = room[0]
                return CREATE_ROOM_PASSWORD
            else:
                context.user_data['room_id'] = room[0]
                await update.message.reply_text(
                    f"Вы вошли в комнату '{room_name}'. Напишите сообщение для отправки в чат.",
                    reply_markup=ReplyKeyboardMarkup([['🔙 Выйти из комнаты']], resize_keyboard=True)
                )
                return ROOM_CHAT
    
    await update.message.reply_text("Комната не найдена.")
    return ConversationHandler.END

# Обработка сообщений в комнате
async def handle_room_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    room_id = context.user_data.get('room_id')
    
    if not room_id:
        await update.message.reply_text("Сначала выберите комнату.")
        return ConversationHandler.END
    
    if update.message.text == '🔙 Выйти из комнаты':
        if user_id == CREATOR_ID or user[7]:
            await update.message.reply_text("Вы вышли из комнаты.", reply_markup=admin_keyboard())
        else:
            await update.message.reply_text("Вы вышли из комната.", reply_markup=main_keyboard())
        return ConversationHandler.END
    
    # Сохраняем сообщение в базе
    db.add_message(room_id, user_id, update.message.text)
    
    # Отправляем сообщение всем в комнате
    room = db.get_room(room_id)
    await update.message.reply_text(f"[{user[3]}]: {update.message.text}")

# Создание комнаты
async def create_room_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    room_name = update.message.text
    context.user_data['room_name'] = room_name
    await update.message.reply_text(
        "Выберите тип комнаты:",
        reply_markup=ReplyKeyboardMarkup([['🔓 Публичная', '🔒 Приватная']], resize_keyboard=True)
    )
    return CREATE_ROOM_TYPE

async def create_room_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    room_type = update.message.text
    is_private = 1 if room_type == '🔒 Приватная' else 0
    context.user_data['is_private'] = is_private
    
    await update.message.reply_text(
        "Сообщения должны пропадать после прочтения?",
        reply_markup=ReplyKeyboardMarkup([['✅ Да', '❌ Нет']], resize_keyboard=True)
    )
    return CREATE_ROOM_PERSISTENCE

async def create_room_persistence(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_ephemeral = 1 if update.message.text == '✅ Да' else 0
    context.user_data['is_ephemeral'] = is_ephemeral
    
    if context.user_data['is_private']:
        await update.message.reply_text("Введите пароль для комнаты:")
        return CREATE_ROOM_PASSWORD
    else:
        return await finish_room_creation(update, context)

async def create_room_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['password'] = update.message.text
    return await finish_room_creation(update, context)

async def finish_room_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    room_name = context.user_data['room_name']
    is_private = context.user_data['is_private']
    is_ephemeral = context.user_data['is_ephemeral']
    password = context.user_data.get('password', '')
    
    # Проверяем баланс пользователя
    user = db.get_user(user_id)
    if user[6] < 2.0:
        # Предлагаем оплатить
        payment_success = await create_payment(
            update, context, user_id, 2.0, 
            "Создание комнаты", f"Комната: {room_name}"
        )
        
        if payment_success:
            await update.message.reply_text(
                "После оплаты 2 USD комната будет создана автоматически.",
                reply_markup=main_keyboard()
            )
        else:
            await update.message.reply_text(
                "Ошибка при создании платежа. Попробуйте позже.",
                reply_markup=main_keyboard()
            )
        return ConversationHandler.END
    
    # Если достаточно средств, создаем комнату
    db.update_balance(user_id, -2.0)
    
    if db.create_room(room_name, user_id, is_ephemeral, is_private, password):
        await update.message.reply_text(f"Комната '{room_name}' успешно создана! Списано 2 USD.", reply_markup=main_keyboard())
    else:
        await update.message.reply_text("Ошибка при создании комнаты. Возможно, такое имя уже существует.")
    
    return ConversationHandler.END

# Передача USD
async def transfer_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nickname = update.message.text
    recipient = db.get_user_by_nickname(nickname)
    
    if not recipient:
        await update.message.reply_text("Пользователь с таким псевдонимом не найден. Попробуйте еще раз:")
        return TRANSFER_USER
    
    context.user_data['recipient_id'] = recipient[1]
    await update.message.reply_text(f"Найдено: {recipient[3]}. Введите сумму для передачи:")
    return TRANSFER_AMOUNT

async def transfer_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        user_id = update.effective_user.id
        recipient_id = context.user_data['recipient_id']
        
        if amount <= 0:
            await update.message.reply_text("Сумма должна быть положительной. Попробуйте еще раз:")
            return TRANSFER_AMOUNT
        
        if db.transfer_balance(user_id, recipient_id, amount):
            await update.message.reply_text(f"Передача {amount} USD успешно выполнена!", reply_markup=main_keyboard())
        else:
            await update.message.reply_text("Недостаточно средств для передачи.", reply_markup=main_keyboard())
        
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректную сумму:")
        return TRANSFER_AMOUNT

# Пополнение баланса
async def handle_payment_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.message.text == '🔙 Назад':
            user_id = update.effective_user.id
            user = db.get_user(user_id)
            if user_id == CREATOR_ID or user[7]:
                await update.message.reply_text("Главное меню:", reply_markup=admin_keyboard())
            else:
                await update.message.reply_text("Главное меню:", reply_markup=main_keyboard())
            return ConversationHandler.END
        
        amount = float(update.message.text.split()[0])
        user_id = update.effective_user.id
        
        payment_success = await create_payment(
            update, context, user_id, amount, 
            "Пополнение баланса", f"Пополнение на {amount} USD"
        )
        
        if payment_success:
            await update.message.reply_text(
                f"После оплаты {amount} USD будут зачислены на ваш баланс.",
                reply_markup=main_keyboard()
            )
        
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Пожалуйста, выберите сумму из предложенных:")
        return PAYMENT_CONFIRMATION

# Админ панель
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == '🔨 Бан':
        await update.message.reply_text("Введите ID пользователя для бана:")
        return BAN_USER
    elif text == '🔇 Мут':
        await update.message.reply_text("Введите ID пользователя для мута:")
        return MUTE_USER
    elif text == '👥 Все пользователи':
        users = db.get_all_users()
        users_text = "Все пользователи:\n\n"
        for user in users:
            users_text += f"ID: {user[1]}, Nick: {user[3]}, Balance: {user[6]}, Admin: {user[7]}, Banned: {user[8]}\n"
        
        # Разбиваем сообщение если слишком длинное
        if len(users_text) > 4096:
            for x in range(0, len(users_text), 4096):
                await update.message.reply_text(users_text[x:x+4096])
        else:
            await update.message.reply_text(users_text)
        
        return ADMIN_ACTION
    elif text == '👑 Назначить админа':
        await update.message.reply_text("Введите ID пользователя для назначения админом:")
        return MAKE_ADMIN
    elif text == '🔙 Назад':
        await update.message.reply_text("Главное меню:", reply_markup=admin_keyboard())
        return ConversationHandler.END

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id_to_ban = int(update.message.text)
        db.ban_user(user_id_to_ban)
        await update.message.reply_text(f"Пользователь {user_id_to_ban} забанен.", reply_markup=admin_panel_keyboard())
        return ADMIN_ACTION
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректный ID пользователя:")
        return BAN_USER

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id_to_mute = int(update.message.text)
        context.user_data['mute_user_id'] = user_id_to_mute
        await update.message.reply_text("Введите длительность мута в минутах:")
        return MUTE_DURATION
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректный ID пользователя:")
        return MUTE_USER

async def mute_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        duration = int(update.message.text)
        user_id_to_mute = context.user_data['mute_user_id']
        db.mute_user(user_id_to_mute, duration)
        await update.message.reply_text(f"Пользователь {user_id_to_mute} замучен на {duration} минут.", reply_markup=admin_panel
