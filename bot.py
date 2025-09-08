import os
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters, 
    CallbackContext, ConversationHandler
)
from database import Database

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота и ID создателя
BOT_TOKEN = os.environ.get('BOT_TOKEN', '7914229102:AAGVfk6qafoooQM28fS-SY0mWlXlSRwL_Do')
CREATOR_ID = 8097784914

# Состояния для ConversationHandler
REGISTER_USERNAME, REGISTER_PASSWORD, REGISTER_NICKNAME, REGISTER_WALLET = range(4)
ROOM_SELECTION, ROOM_CHAT, CREATE_ROOM_NAME, CREATE_ROOM_TYPE, CREATE_ROOM_PERSISTENCE, CREATE_ROOM_PASSWORD = range(4, 10)
TRANSFER_USER, TRANSFER_AMOUNT = range(10, 12)
ADMIN_ACTION, BAN_USER, MUTE_USER, MUTE_DURATION, MAKE_ADMIN = range(12, 17)

# Инициализация базы данных
db = Database()

# Клавиатуры
def main_keyboard():
    return ReplyKeyboardMarkup([
        ['👤 Профиль', '💬 Анонимный чат'],
        ['💰 Передать USD', '➕ Создать комнату']
    ], resize_keyboard=True)

def admin_keyboard():
    return ReplyKeyboardMarkup([
        ['👤 Профиль', '💬 Анонимный чат'],
        ['💰 Передать USD', '➕ Создать комнату'],
        ['⚙️ Админ панель']
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

# Команда /start
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if user:
        # Пользователь уже зарегистрирован
        if user_id == CREATOR_ID or user[7]:  # is_admin
            update.message.reply_text(
                f"Добро пожаловать назад, {user[3]}! 👑",
                reply_markup=admin_keyboard()
            )
        else:
            update.message.reply_text(
                f"Добро пожаловать назад, {user[3]}!",
                reply_markup=main_keyboard()
            )
        return ConversationHandler.END
    else:
        # Новый пользователь
        update.message.reply_text(
            "Добро пожаловать в PPZ! Для использования бота необходимо зарегистрироваться.\n"
            "Введите ваш username:"
        )
        return REGISTER_USERNAME

# Обработчики регистрации
def register_username(update: Update, context: CallbackContext):
    context.user_data['username'] = update.message.text
    update.message.reply_text("Отлично! Теперь введите ваш пароль:")
    return REGISTER_PASSWORD

def register_password(update: Update, context: CallbackContext):
    context.user_data['password'] = update.message.text
    update.message.reply_text("Теперь придумайте уникальный псевдоним:")
    return REGISTER_NICKNAME

def register_nickname(update: Update, context: CallbackContext):
    nickname = update.message.text
    if db.get_user_by_nickname(nickname):
        update.message.reply_text("Этот псевдоним уже занят. Пожалуйста, выберите другой:")
        return REGISTER_NICKNAME
    
    context.user_data['nickname'] = nickname
    update.message.reply_text("Теперь введите адрес вашего крипто-кошелька:")
    return REGISTER_WALLET

def register_wallet(update: Update, context: CallbackContext):
    wallet = update.message.text
    user_id = update.effective_user.id
    username = context.user_data['username']
    password = context.user_data['password']
    nickname = context.user_data['nickname']
    
    if db.add_user(user_id, username, password, nickname, wallet):
        update.message.reply_text(
            "Регистрация завершена! Теперь вы можете пользоваться ботом.",
            reply_markup=main_keyboard()
        )
    else:
        update.message.reply_text(
            "Произошла ошибка при регистрации. Попробуйте снова с помощью /start"
        )
    
    return ConversationHandler.END

# Обработка текстовых сообщений
def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    text = update.message.text
    
    if not user:
        update.message.reply_text("Пожалуйста, зарегистрируйтесь с помощью /start")
        return
    
    if db.is_muted(user_id):
        update.message.reply_text("Вы заблокированы от отправки сообщений.")
        return
    
    if text == '👤 Профиль':
        show_profile(update, user)
    elif text == '💬 Анонимный чат':
        update.message.reply_text("Выберите комнату:", reply_markup=rooms_keyboard())
    elif text == '💰 Передать USD':
        update.message.reply_text("Введите псевдоним пользователя, которому хотите передать USD:")
        return TRANSFER_USER
    elif text == '➕ Создать комнату':
        update.message.reply_text("Введите название для новой комнаты:")
        return CREATE_ROOM_NAME
    elif text == '⚙️ Админ панель' and (user_id == CREATOR_ID or user[7]):
        update.message.reply_text("Админ панель:", reply_markup=admin_panel_keyboard())
        return ADMIN_ACTION
    elif text.startswith('🚪 '):
        room_name = text[2:]
        join_room(update, context, room_name)
    elif text == '🔙 Назад':
        if user_id == CREATOR_ID or user[7]:
            update.message.reply_text("Главное меню:", reply_markup=admin_keyboard())
        else:
            update.message.reply_text("Главное меню:", reply_markup=main_keyboard())
        return ConversationHandler.END

# Показать профиль
def show_profile(update: Update, user):
    profile_text = (
        f"👤 Ваш профиль:\n\n"
        f"🆔 ID: {user[1]}\n"
        f"👤 Псевдоним: {user[3]}\n"
        f"🔑 Пароль: {user[2]}\n"
        f"💰 Баланс: {user[6]} USD\n"
        f"📊 Крипто-кошелек: {user[4]}"
    )
    update.message.reply_text(profile_text)

# Анонимный чат
def join_room(update: Update, context: CallbackContext, room_name):
    user_id = update.effective_user.id
    rooms = db.get_rooms()
    
    for room in rooms:
        if room[1] == room_name:
            if room[4]:  # is_private
                update.message.reply_text("Эта комната приватная. Введите пароль:")
                context.user_data['room_id'] = room[0]
                return CREATE_ROOM_PASSWORD
            else:
                context.user_data['room_id'] = room[0]
                update.message.reply_text(
                    f"Вы вошли в комнату '{room_name}'. Напишите сообщение для отправки в чат.",
                    reply_markup=ReplyKeyboardMarkup([['🔙 Выйти из комнаты']], resize_keyboard=True)
                )
                return ROOM_CHAT
    
    update.message.reply_text("Комната не найдена.")
    return ConversationHandler.END

# Обработка сообщений в комнате
def handle_room_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    room_id = context.user_data.get('room_id')
    
    if not room_id:
        update.message.reply_text("Сначала выберите комнату.")
        return ConversationHandler.END
    
    if update.message.text == '🔙 Выйти из комнаты':
        if user_id == CREATOR_ID or user[7]:
            update.message.reply_text("Вы вышли из комнаты.", reply_markup=admin_keyboard())
        else:
            update.message.reply_text("Вы вышли из комнаты.", reply_markup=main_keyboard())
        return ConversationHandler.END
    
    # Сохраняем сообщение в базе
    db.add_message(room_id, user_id, update.message.text)
    
    # Отправляем сообщение всем в комнате (в реальности нужен механизм подписок)
    room = db.get_room(room_id)
    update.message.reply_text(f"[{user[3]}]: {update.message.text}")

# Создание комнаты
def create_room_name(update: Update, context: CallbackContext):
    room_name = update.message.text
    context.user_data['room_name'] = room_name
    update.message.reply_text(
        "Выберите тип комнаты:",
        reply_markup=ReplyKeyboardMarkup([['🔓 Публичная', '🔒 Приватная']], resize_keyboard=True)
    )
    return CREATE_ROOM_TYPE

def create_room_type(update: Update, context: CallbackContext):
    room_type = update.message.text
    is_private = 1 if room_type == '🔒 Приватная' else 0
    context.user_data['is_private'] = is_private
    
    update.message.reply_text(
        "Сообщения должны пропадать после прочтения?",
        reply_markup=ReplyKeyboardMarkup([['✅ Да', '❌ Нет']], resize_keyboard=True)
    )
    return CREATE_ROOM_PERSISTENCE

def create_room_persistence(update: Update, context: CallbackContext):
    is_ephemeral = 1 if update.message.text == '✅ Да' else 0
    context.user_data['is_ephemeral'] = is_ephemeral
    
    if context.user_data['is_private']:
        update.message.reply_text("Введите пароль для комнаты:")
        return CREATE_ROOM_PASSWORD
    else:
        return finish_room_creation(update, context)

def create_room_password(update: Update, context: CallbackContext):
    context.user_data['password'] = update.message.text
    return finish_room_creation(update, context)

def finish_room_creation(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    room_name = context.user_data['room_name']
    is_private = context.user_data['is_private']
    is_ephemeral = context.user_data['is_ephemeral']
    password = context.user_data.get('password', '')
    
    # Проверяем баланс пользователя
    user = db.get_user(user_id)
    if user[6] < 2.0:
        update.message.reply_text("Недостаточно средств для создания комнаты. Нужно 2 USD.")
        return ConversationHandler.END
    
    # Списываем средства
    db.update_balance(user_id, -2.0)
    
    # Создаем комнату
    if db.create_room(room_name, user_id, is_ephemeral, is_private, password):
        update.message.reply_text(f"Комната '{room_name}' успешно создана!", reply_markup=main_keyboard())
    else:
        update.message.reply_text("Ошибка при создании комнаты. Возможно, такое имя уже существует.")
    
    return ConversationHandler.END

# Передача USD
def transfer_user(update: Update, context: CallbackContext):
    nickname = update.message.text
    recipient = db.get_user_by_nickname(nickname)
    
    if not recipient:
        update.message.reply_text("Пользователь с таким псевдонимом не найден. Попробуйте еще раз:")
        return TRANSFER_USER
    
    context.user_data['recipient_id'] = recipient[1]
    update.message.reply_text(f"Найдено: {recipient[3]}. Введите сумму для передачи:")
    return TRANSFER_AMOUNT

def transfer_amount(update: Update, context: CallbackContext):
    try:
        amount = float(update.message.text)
        user_id = update.effective_user.id
        recipient_id = context.user_data['recipient_id']
        
        if amount <= 0:
            update.message.reply_text("Сумма должна быть положительной. Попробуйте еще раз:")
            return TRANSFER_AMOUNT
        
        if db.transfer_balance(user_id, recipient_id, amount):
            update.message.reply_text(f"Передача {amount} USD успешно выполнена!", reply_markup=main_keyboard())
        else:
            update.message.reply_text("Недостаточно средств для передачи.", reply_markup=main_keyboard())
        
        return ConversationHandler.END
    except ValueError:
        update.message.reply_text("Пожалуйста, введите корректную сумму:")
        return TRANSFER_AMOUNT

# Админ панель
def admin_action(update: Update, context: CallbackContext):
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == '🔨 Бан':
        update.message.reply_text("Введите ID пользователя для бана:")
        return BAN_USER
    elif text == '🔇 Мут':
        update.message.reply_text("Введите ID пользователя для мута:")
        return MUTE_USER
    elif text == '👥 Все пользователи':
        users = db.get_all_users()
        users_text = "Все пользователи:\n\n"
        for user in users:
            users_text += f"ID: {user[1]}, Nick: {user[3]}, Balance: {user[6]}, Admin: {user[7]}, Banned: {user[8]}\n"
        
        # Разбиваем сообщение если слишком длинное
        if len(users_text) > 4096:
            for x in range(0, len(users_text), 4096):
                update.message.reply_text(users_text[x:x+4096])
        else:
            update.message.reply_text(users_text)
        
        return ADMIN_ACTION
    elif text == '👑 Назначить админа':
        update.message.reply_text("Введите ID пользователя для назначения админом:")
        return MAKE_ADMIN
    elif text == '🔙 Назад':
        update.message.reply_text("Главное меню:", reply_markup=admin_keyboard())
        return ConversationHandler.END

def ban_user(update: Update, context: CallbackContext):
    try:
        user_id_to_ban = int(update.message.text)
        db.ban_user(user_id_to_ban)
        update.message.reply_text(f"Пользователь {user_id_to_ban} забанен.", reply_markup=admin_panel_keyboard())
        return ADMIN_ACTION
    except ValueError:
        update.message.reply_text("Пожалуйста, введите корректный ID пользователя:")
        return BAN_USER

def mute_user(update: Update, context: CallbackContext):
    try:
        user_id_to_mute = int(update.message.text)
        context.user_data['mute_user_id'] = user_id_to_mute
        update.message.reply_text("Введите длительность мута в минутах:")
        return MUTE_DURATION
    except ValueError:
        update.message.reply_text("Пожалуйста, введите корректный ID пользователя:")
        return MUTE_USER

def mute_duration(update: Update, context: CallbackContext):
    try:
        duration = int(update.message.text)
        user_id_to_mute = context.user_data['mute_user_id']
        db.mute_user(user_id_to_mute, duration)
        update.message.reply_text(f"Пользователь {user_id_to_mute} замучен на {duration} минут.", reply_markup=admin_panel_keyboard())
        return ADMIN_ACTION
    except ValueError:
        update.message.reply_text("Пожалуйста, введите корректное количество минут:")
        return MUTE_DURATION

def make_admin(update: Update, context: CallbackContext):
    try:
        user_id_to_admin = int(update.message.text)
        db.make_admin(user_id_to_admin)
        update.message.reply_text(f"Пользователь {user_id_to_admin} назначен администратором.", reply_markup=admin_panel_keyboard())
        return ADMIN_ACTION
    except ValueError:
        update.message.reply_text("Пожалуйста, введите корректный ID пользователя:")
        return MAKE_ADMIN

# Обработка ошибок
def error(update: Update, context: CallbackContext):
    logger.warning('Update "%s" caused error "%s"', update, context.error)

# Основная функция
def main():
    # Создаем Updater и передаем ему токен бота
    updater = Updater(BOT_TOKEN, use_context=True)
    
    # Получаем диспетчер для регистрации обработчиков
    dp = updater.dispatcher
    
    # Обработчик команды /start с регистрацией
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            REGISTER_USERNAME: [MessageHandler(Filters.text & ~Filters.command, register_username)],
            REGISTER_PASSWORD: [MessageHandler(Filters.text & ~Filters.command, register_password)],
            REGISTER_NICKNAME: [MessageHandler(Filters.text & ~Filters.command, register_nickname)],
            REGISTER_WALLET: [MessageHandler(Filters.text & ~Filters.command, register_wallet)],
            TRANSFER_USER: [MessageHandler(Filters.text & ~Filters.command, transfer_user)],
            TRANSFER_AMOUNT: [MessageHandler(Filters.text & ~Filters.command, transfer_amount)],
            CREATE_ROOM_NAME: [MessageHandler(Filters.text & ~Filters.command, create_room_name)],
            CREATE_ROOM_TYPE: [MessageHandler(Filters.text & ~Filters.command, create_room_type)],
            CREATE_ROOM_PERSISTENCE: [MessageHandler(Filters.text & ~Filters.command, create_room_persistence)],
            CREATE_ROOM_PASSWORD: [MessageHandler(Filters.text & ~Filters.command, create_room_password)],
            ROOM_CHAT: [MessageHandler(Filters.text & ~Filters.command, handle_room_message)],
            ADMIN_ACTION: [MessageHandler(Filters.text & ~Filters.command, admin_action)],
            BAN_USER: [MessageHandler(Filters.text & ~Filters.command, ban_user)],
            MUTE_USER: [MessageHandler(Filters.text & ~Filters.command, mute_user)],
            MUTE_DURATION: [MessageHandler(Filters.text & ~Filters.command, mute_duration)],
            MAKE_ADMIN: [MessageHandler(Filters.text & ~Filters.command, make_admin)],
        },
        fallbacks=[CommandHandler('start', start)],
    )
    
    dp.add_handler(conv_handler)
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dp.add_error_handler(error)
    
    # Запускаем бота
    port = int(os.environ.get('PORT', 5000))
    updater.start_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=BOT_TOKEN,
        webhook_url=f"https://ppz-bot.onrender.com/{BOT_TOKEN}"
    )
    updater.idle()

if __name__ == '__main__':
    main()
