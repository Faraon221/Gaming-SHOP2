import asyncio
import logging
import sqlite3
import random
import time
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
import aiohttp
from typing import Optional

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = '8541451907:AAGMF-LzAc_X0AHn-zBeW2-wJFAavGTaPew'
ADMIN_ID = 8326910687
CRYPTO_BOT_TOKEN = '512737:AAJnzkIcW2NjFpLFI4Fmg2yy44qip2XqLH6'
SUPPORT_USERNAME = '@BlackoutBazaar_support'
SUPPORT_ID = '8194391196'

# Увеличиваем timeout и другие параметры
bot = Bot(token=BOT_TOKEN, timeout=90)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ==================== ФУНКЦИИ ДЛЯ БАЗЫ ДАННЫХ ====================
def recreate_tables():
    """Пересоздание таблиц с правильной структурой"""
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    
    try:
        # Удаляем старые таблицы
        cursor.execute("DROP TABLE IF EXISTS orders")
        cursor.execute("DROP TABLE IF EXISTS products")
        cursor.execute("DROP TABLE IF EXISTS cart")
        cursor.execute("DROP TABLE IF EXISTS users")
        cursor.execute("DROP TABLE IF EXISTS logs")
        cursor.execute("DROP TABLE IF EXISTS auth_users")
        cursor.execute("DROP TABLE IF EXISTS bot_messages")
        
        print("🗑️ Старые таблицы удалены")
        
        # Создаем таблицы заново
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auth_users (
                user_id INTEGER PRIMARY KEY,
                login TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                join_date TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES auth_users(user_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price INTEGER NOT NULL,
                description TEXT,
                weight TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cart (
                user_id INTEGER,
                product_id INTEGER,
                quantity INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_id INTEGER,
                quantity INTEGER,
                total_price INTEGER,
                district TEXT,
                city TEXT,
                status TEXT DEFAULT 'pending',
                cryptobot_invoice_id TEXT,
                cryptobot_asset TEXT,
                cryptobot_amount REAL,
                cryptobot_pay_url TEXT,
                six_digit_code TEXT,
                payment_confirmed BOOLEAN DEFAULT 0,
                coordinates_sent BOOLEAN DEFAULT 0,
                created_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                details TEXT,
                timestamp TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_messages (
                user_id INTEGER,
                message_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, message_id)
            )
        ''')
        
        # Вставляем зашифрованные товары
        products = [
            ('@мф3т@м1н', '🎯 Стимуляторы', 2500, 'Высокое качество, чистота 90%. Россия.', '1,00г'),
            ('m3ф3dр0н (крNст@лы)', '🎯 Стимуляторы', 2000, 'Кристаллы m3ф3dр0н, голландский синтез.', '0,5г'),
            ('m3ф3dр0н (Мyк@)', '🎯 Стимуляторы', 1900, 'Мука m3ф3dр0н, китайский синтез.', '0,5г'),
            ('к0к@1н (К0лyмбNя)', '🎯 Стимуляторы', 9250, 'к0к@1н HQ, К0лyмбNя, чистота 92%.', '1,00г'),
            ('г@шNш', '🌿 Каннабиноиды', 2000, 'г@шNш, 2г. Индийский, мягкий.', '0,5г'),
            ('шNшкN', '🌿 Каннабиноиды', 2100, 'шNшкN, Амнезия Хейз.', '1,00г'),
            ('3кст@зN', '🌈 Психоделики', 3600, '3кст@зN таблетки, 250мг MDMA.', '4,00г'),
            ('LSД', '🌈 Психоделики', 3000, 'LSД-25, 200мкг. Марки с рисунком.', '2,00г'),
            ('грNбы (ПсNл0цNбNновые)', '🌈 Психоделики', 6000, 'грNбы псNл0цNбNн, сушеные.', '10,00г'),
            ('@lph@-PvP whNt3', '🧪 Синтетика', 3600, '@lph@-PvP белый кристаллический.', '1,00г'),
            ('м3т@д0н', '💊 Опиоиды', 3800, 'м3т@д0н, 40мг, таблетки.', '0,25г')
        ]
        
        cursor.executemany(
            "INSERT INTO products (name, category, price, description, weight) VALUES (?,?,?,?,?)",
            products
        )
        
        # Создаем тестового пользователя (логин: admin, пароль: admin123)
        cursor.execute(
            "INSERT OR IGNORE INTO auth_users (user_id, login, password, created_at) VALUES (?,?,?,?)",
            (ADMIN_ID, 'admin', 'admin123', datetime.now().isoformat())
        )
        
        conn.commit()
        print("✅ Таблицы пересозданы с системой аутентификации")
        
    except Exception as e:
        print(f"❌ Ошибка пересоздания таблиц: {e}")
        conn.rollback()
    finally:
        conn.close()

# Пересоздаем таблицы с нуля
recreate_tables()

# ==================== CRYPTOBOT API ====================
class CryptoBotAPI:
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = "https://pay.crypt.bot/api"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def create_session(self):
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def create_invoice(self, asset: str, amount: float, description: str = ""):
        """Создать инвойс для оплаты"""
        await self.create_session()
        
        headers = {
            "Crypto-Pay-API-Token": self.api_token
        }
        
        data = {
            "asset": asset,
            "amount": str(amount),
            "description": description,
            "paid_btn_name": "viewItem",
            "paid_btn_url": "https://t.me/your_bot"
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/createInvoice",
                headers=headers,
                json=data
            ) as response:
                result = await response.json()
                if result.get("ok"):
                    invoice = result["result"]
                    return invoice["pay_url"], invoice["invoice_id"]
                else:
                    logging.error(f"CryptoBot Error: {result}")
                    return None, None
        except Exception as e:
            logging.error(f"CryptoBot API Error: {e}")
            return None, None
    
    async def check_invoice_status(self, invoice_id: str):
        """Проверить статус инвойса"""
        await self.create_session()
        
        headers = {
            "Crypto-Pay-API-Token": self.api_token
        }
        
        try:
            async with self.session.get(
                f"{self.base_url}/getInvoices?invoice_ids={invoice_id}",
                headers=headers
            ) as response:
                result = await response.json()
                if result.get("ok"):
                    invoices = result["result"]["items"]
                    if invoices:
                        return invoices[0]["status"]
        except Exception as e:
            logging.error(f"CryptoBot Check Error: {e}")
        return None
    
    async def close(self):
        if self.session:
            await self.session.close()

crypto_bot = CryptoBotAPI(CRYPTO_BOT_TOKEN)

# ==================== ФЕДЕРАЛЬНЫЕ ОКРУГА И ГОРОДА ====================
DISTRICTS = {
    "1": {"name": "Центральный федеральный округ", "cities": [
        "Москва", "Воронеж", "Ярославль", "Рязань", "Липецк", "Курск", "Тула", "Брянск"]},
    "2": {"name": "Северо-Западный федеральный округ", "cities": [
        "Санкт-Петербург", "Архангельск", "Мурманск", "Череповец", "Вологда", "Петрозаводск"]},
    "3": {"name": "Южный федеральный округ", "cities": [
        "Ростов-на-Дону", "Волгоград", "Краснодар", "Астрахань", "Сочи", "Севастополь"]},
    "4": {"name": "Приволжский федеральный округ", "cities": [
        "Нижний Новгород", "Казань", "Самара", "Уфа", "Пермь", "Саратов"]},
    "5": {"name": "Уральский федеральный округ", "cities": [
        "Екатеринбург", "Челябинск", "Тюмень", "Курган", "Сургут", "Нижневартовск"]},
    "6": {"name": "Сибирский федеральный округ", "cities": [
        "Новосибирск", "Омск", "Красноярск", "Барнаул", "Иркутск", "Кемерово"]},
    "7": {"name": "Дальневосточный федеральный округ", "cities": [
        "Владивосток", "Хабаровск", "Якутск", "Благовещенск", "Комсомольск-на-Амуре"]}
}

# ==================== ЛОГИРОВАНИЕ ====================
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger()

logger = setup_logging()

def log_action(user_id: int, action: str, details: str = ""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"User {user_id}: {action} - {details}")
    
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO logs (user_id, action, details, timestamp) VALUES (?,?,?,?)",
        (user_id, action, details, timestamp)
    )
    conn.commit()
    conn.close()

# ==================== FSM СОСТОЯНИЯ ====================
class AuthState(StatesGroup):
    waiting_for_action = State()
    waiting_for_login = State()
    waiting_for_password = State()
    waiting_for_registration_login = State()
    waiting_for_registration_password = State()

class OrderState(StatesGroup):
    choosing_district = State()
    choosing_city = State()
    choosing_category = State()
    choosing_product = State()
    choosing_quantity = State()
    choosing_crypto = State()
    confirming_order = State()
    waiting_payment = State()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def get_db_connection():
    return sqlite3.connect('shop.db')

async def register_user(user_id: int, username: str, first_name: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username, first_name, join_date) VALUES (?,?,?,?)",
        (user_id, username, first_name, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    log_action(user_id, "register", f"username: {username}")

async def get_user_cart(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.id, p.name, p.price, c.quantity 
        FROM cart c 
        JOIN products p ON c.product_id = p.id 
        WHERE c.user_id = ?
    ''', (user_id,))
    items = cursor.fetchall()
    conn.close()
    return items

async def check_cryptobot_payment(order_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT cryptobot_invoice_id FROM orders WHERE order_id = ?",
        (order_id,)
    )
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        return False
    
    invoice_id = result[0]
    
    if not invoice_id:
        conn.close()
        return False
    
    status = await crypto_bot.check_invoice_status(invoice_id)
    
    if status == "paid":
        cursor.execute(
            "UPDATE orders SET status = 'paid', payment_confirmed = 1 WHERE order_id = ?",
            (order_id,)
        )
        conn.commit()
        conn.close()
        return True
    
    conn.close()
    return False

async def delete_all_user_messages(user_id: int, chat_id: int):
    """Удаление всех сообщений бота для пользователя"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT message_id FROM bot_messages WHERE user_id = ? ORDER BY timestamp DESC",
        (user_id,)
    )
    messages = cursor.fetchall()
    
    # Удаляем все сообщения
    for msg in messages:
        try:
            await bot.delete_message(chat_id, msg[0])
        except:
            pass
    
    # Очищаем таблицу сообщений для пользователя
    cursor.execute("DELETE FROM bot_messages WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

async def save_bot_message(user_id: int, message_id: int):
    """Сохранить ID сообщения бота для последующего удаления"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO bot_messages (user_id, message_id) VALUES (?, ?)",
        (user_id, message_id)
    )
    conn.commit()
    conn.close()

async def delete_previous_messages(chat_id: int, message_ids: list):
    """Удаление нескольких предыдущих сообщений"""
    for msg_id in message_ids:
        try:
            await bot.delete_message(chat_id, msg_id)
        except:
            pass

def generate_six_digit_code():
    """Генерация 6-значного кода"""
    return str(random.randint(100000, 999999))

# ==================== КЛАВИАТУРЫ ====================
def auth_kb():
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🔄 Войти")],
        [KeyboardButton(text="📝 Зарегистрироваться")]
    ], resize_keyboard=True)
    return kb

def main_kb():
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🎯 Каталог"), KeyboardButton(text="🛒 Корзина")],
        [KeyboardButton(text="📦 Мои заказы"), KeyboardButton(text="👨‍💼 Поддержка")],
        [KeyboardButton(text="⚠️ Инструкция"), KeyboardButton(text="💎 Купить TON")],
        [KeyboardButton(text="🤝 Партнёрка"), KeyboardButton(text="🚪 Выйти")]
    ], resize_keyboard=True)
    return kb

def districts_kb():
    builder = InlineKeyboardBuilder()
    for key, data in DISTRICTS.items():
        builder.add(InlineKeyboardButton(
            text=data["name"], 
            callback_data=f"district_{key}"
        ))
    builder.adjust(1)
    return builder.as_markup()

def cities_in_district_kb(district_key: str):
    builder = InlineKeyboardBuilder()
    cities = DISTRICTS[district_key]["cities"]
    
    for city in cities:
        builder.add(InlineKeyboardButton(text=city, callback_data=f"city_{city}"))
    
    builder.adjust(2)
    return builder.as_markup()

def categories_kb():
    categories = ["🎯 Стимуляторы", "🌿 Каннабиноиды", "🌈 Психоделики", "🧪 Синтетика", "💊 Опиоиды"]
    
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.add(InlineKeyboardButton(text=cat, callback_data=f"cat_{cat}"))
    builder.adjust(2)
    return builder.as_markup()

def crypto_kb():
    builder = InlineKeyboardBuilder()
    cryptos = [
        ("💎 TON", "TON"),
        ("💵 USDT", "USDT"),
        ("₿ BTC", "BTC"),
        ("Ξ ETH", "ETH")
    ]
    
    for name, code in cryptos:
        builder.add(InlineKeyboardButton(text=name, callback_data=f"crypto_{code}"))
    builder.adjust(2)
    return builder.as_markup()

# ==================== ОСНОВНЫЕ ОБРАБОТЧИКИ ====================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id FROM auth_users WHERE user_id = ? AND is_active = 1",
        (user_id,)
    )
    auth_user = cursor.fetchone()
    conn.close()
    
    if auth_user:
        # Пользователь уже авторизован
        await state.update_data(authorized=True, prev_messages=[])
        msg = await message.answer(
            "✅ Вы уже авторизованы! Добро пожаловать в Blackout Bazaar.",
            reply_markup=main_kb()
        )
        await save_bot_message(user_id, msg.message_id)
    else:
        # Пользователь не авторизован
        await state.set_state(AuthState.waiting_for_action)
        msg = await message.answer(
            "🔐 Добро пожаловать в Blackout Bazaar.\n\n"
            "Для доступа к функциям бота необходимо авторизоваться.",
            reply_markup=auth_kb()
        )
        await save_bot_message(user_id, msg.message_id)
    
    log_action(user_id, "start_command")

@dp.message(F.text == "🔄 Войти")
async def login_start(message: types.Message, state: FSMContext):
    await state.set_state(AuthState.waiting_for_login)
    msg = await message.answer("Введите ваш логин:")
    await save_bot_message(message.from_user.id, msg.message_id)
    log_action(message.from_user.id, "login_started")

@dp.message(F.text == "📝 Зарегистрироваться")
async def register_start(message: types.Message, state: FSMContext):
    await state.set_state(AuthState.waiting_for_registration_login)
    msg = await message.answer("Придумайте и введите логин для регистрации:")
    await save_bot_message(message.from_user.id, msg.message_id)
    log_action(message.from_user.id, "registration_started")

@dp.message(AuthState.waiting_for_login)
async def process_login(message: types.Message, state: FSMContext):
    await state.update_data(login=message.text)
    await state.set_state(AuthState.waiting_for_password)
    msg = await message.answer("Введите пароль:")
    await save_bot_message(message.from_user.id, msg.message_id)
    log_action(message.from_user.id, "login_entered", f"login: {message.text}")

@dp.message(AuthState.waiting_for_password)
async def process_password(message: types.Message, state: FSMContext):
    data = await state.get_data()
    login = data.get('login', '')
    password = message.text
    user_id = message.from_user.id
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id FROM auth_users WHERE login = ? AND password = ?",
        (login, password)
    )
    user = cursor.fetchone()
    
    if user:
        # Авторизация успешна
        cursor.execute(
            "UPDATE auth_users SET is_active = 1, last_login = ? WHERE user_id = ?",
            (datetime.now().isoformat(), user[0])
        )
        conn.commit()
        
        await register_user(user_id, message.from_user.username, message.from_user.first_name)
        await state.clear()
        await state.update_data(authorized=True, prev_messages=[])
        
        msg = await message.answer(
            "✅ Авторизация успешна! Добро пожаловать в Blackout Bazaar.",
            reply_markup=main_kb()
        )
        await save_bot_message(user_id, msg.message_id)
        log_action(user_id, "login_successful", f"login: {login}")
    else:
        # Авторизация не удалась
        await state.set_state(AuthState.waiting_for_action)
        msg = await message.answer(
            "❌ Неверный логин или пароль. Попробуйте снова.",
            reply_markup=auth_kb()
        )
        await save_bot_message(user_id, msg.message_id)
        log_action(user_id, "login_failed", f"login: {login}")
    
    conn.close()

@dp.message(AuthState.waiting_for_registration_login)
async def process_registration_login(message: types.Message, state: FSMContext):
    login = message.text.strip()
    
    if len(login) < 3:
        msg = await message.answer("❌ Логин должен содержать минимум 3 символа. Попробуйте снова:")
        await save_bot_message(message.from_user.id, msg.message_id)
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id FROM auth_users WHERE login = ?",
        (login,)
    )
    existing_user = cursor.fetchone()
    conn.close()
    
    if existing_user:
        msg = await message.answer("❌ Этот логин уже занят. Выберите другой:")
        await save_bot_message(message.from_user.id, msg.message_id)
    else:
        await state.update_data(reg_login=login)
        await state.set_state(AuthState.waiting_for_registration_password)
        msg = await message.answer("Отлично! Теперь придумайте пароль (минимум 6 символов):")
        await save_bot_message(message.from_user.id, msg.message_id)
        log_action(message.from_user.id, "registration_login_entered", f"login: {login}")

@dp.message(AuthState.waiting_for_registration_password)
async def process_registration_password(message: types.Message, state: FSMContext):
    password = message.text.strip()
    user_id = message.from_user.id
    data = await state.get_data()
    login = data.get('reg_login', '')
    
    if len(password) < 6:
        msg = await message.answer("❌ Пароль должен содержать минимум 6 символов. Попробуйте снова:")
        await save_bot_message(user_id, msg.message_id)
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO auth_users (user_id, login, password, created_at, is_active) VALUES (?,?,?,?,?)",
            (user_id, login, password, datetime.now().isoformat(), 1)
        )
        conn.commit()
        
        await register_user(user_id, message.from_user.username, message.from_user.first_name)
        await state.clear()
        await state.update_data(authorized=True, prev_messages=[])
        
        msg = await message.answer(
            "✅ Регистрация успешна! Добро пожаловать в Blackout Bazaar.",
            reply_markup=main_kb()
        )
        await save_bot_message(user_id, msg.message_id)
        log_action(user_id, "registration_successful", f"login: {login}")
        
    except Exception as e:
        msg = await message.answer(f"❌ Ошибка регистрации: {str(e)}. Попробуйте снова.", reply_markup=auth_kb())
        await save_bot_message(user_id, msg.message_id)
        await state.set_state(AuthState.waiting_for_action)
        log_action(user_id, "registration_failed", f"error: {str(e)}")
    
    conn.close()

# ==================== ПРОВЕРКА АВТОРИЗАЦИИ ====================
async def check_auth(message: types.Message, state: FSMContext) -> bool:
    data = await state.get_data()
    if not data.get('authorized'):
        msg = await message.answer("❌ Доступ запрещен. Пожалуйста, авторизуйтесь через /start")
        await save_bot_message(message.from_user.id, msg.message_id)
        return False
    return True

@dp.message(F.text == "🚪 Выйти")
async def logout(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # Сообщения для выхода
    exit_messages = [
        "✅ Безопасный выход выполнен. Сеанс закрыт.",
        "Следы уничтожены. До новых встреч.",
        "Сеанс завершён. Бот обезличен."
    ]
    
    # Отправляем первое сообщение
    msg1 = await message.answer("🔄 Зачищаю переписку...")
    
    # Удаляем все сообщения
    await delete_all_user_messages(user_id, chat_id)
    
    # Ждем немного для реалистичности
    await asyncio.sleep(1)
    
    # Отправляем второе сообщение
    msg2 = await message.answer(random.choice(exit_messages))
    
    # Ждем и удаляем первое сообщение
    await asyncio.sleep(1)
    try:
        await bot.delete_message(chat_id, msg1.message_id)
    except:
        pass
    
    # Обновляем статус пользователя
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE auth_users SET is_active = 0 WHERE user_id = ?",
        (user_id,)
    )
    conn.commit()
    conn.close()
    
    # Очищаем состояние
    await state.clear()
    
    # Возвращаем к аутентификации
    await asyncio.sleep(2)
    await state.set_state(AuthState.waiting_for_action)
    msg3 = await message.answer(
        "🔐 Для доступа к функциям бота необходимо авторизоваться.",
        reply_markup=auth_kb()
    )
    await save_bot_message(user_id, msg3.message_id)
    
    log_action(user_id, "logout_successful")

@dp.message(Command("check_payment"))
async def cmd_check_payment(message: types.Message, state: FSMContext):
    if not await check_auth(message, state):
        return
    
    user_id = message.from_user.id
    data = await state.get_data()
    prev_messages = data.get('prev_messages', [])
    
    # Удаляем предыдущие сообщения
    await delete_previous_messages(message.chat.id, prev_messages)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT order_id, product_id, quantity, total_price, status, cryptobot_invoice_id
        FROM orders 
        WHERE user_id = ? AND status = 'pending'
        ORDER BY created_at DESC 
        LIMIT 1
    ''', (user_id,))
    order = cursor.fetchone()
    conn.close()
    
    if not order:
        msg = await message.answer("У вас нет активных заказов")
        await state.update_data(prev_messages=[msg.message_id])
        await save_bot_message(user_id, msg.message_id)
        return
    
    order_id, product_id, quantity, total_price, status, invoice_id = order
    
    if status == 'paid':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT coordinates_sent FROM orders WHERE order_id = ?", (order_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            msg = await message.answer("✅ Ваш заказ уже оплачен. Координаты уже отправлены.")
            await state.update_data(prev_messages=[msg.message_id])
            await save_bot_message(user_id, msg.message_id)
        else:
            msg = await message.answer(
                "✅ Оплата подтверждена!\n\n"
                f"Заказ #{order_id}\n"
                f"Свяжитесь с поддержкой для получения координат:\n"
                f"{SUPPORT_USERNAME}\n\n"
                "Сообщите номер заказа для получения координат."
            )
            await state.update_data(prev_messages=[msg.message_id])
            await save_bot_message(user_id, msg.message_id)
        return
    
    is_paid = await check_cryptobot_payment(order_id)
    
    if is_paid:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM products WHERE id = ?", (product_id,))
        product_name = cursor.fetchone()[0]
        conn.close()
        
        msg = await message.answer(
            "✅ Оплата подтверждена!\n\n"
            f"Заказ #{order_id}: {product_name} ×{quantity}\n"
            f"Сумма: {total_price} руб.\n\n"
            f"📍 Свяжитесь с поддержкой для получения координат:\n"
            f"{SUPPORT_USERNAME}\n\n"
            "Сообщите номер заказа для получения координат."
        )
        await state.update_data(prev_messages=[msg.message_id])
        await save_bot_message(user_id, msg.message_id)
        log_action(user_id, "payment_confirmed", f"order: {order_id}")
    else:
        msg = await message.answer(
            "⏳ Оплата еще не поступила.\n"
            "Пожалуйста, подождите 2-10 минут и проверьте снова командой /check_payment"
        )
        await state.update_data(prev_messages=[msg.message_id])
        await save_bot_message(user_id, msg.message_id)

# ==================== ОБРАБОТЧИКИ КНОПОК ГЛАВНОГО МЕНЮ ====================
@dp.message(F.text == "🎯 Каталог")
async def catalog_start(message: types.Message, state: FSMContext):
    if not await check_auth(message, state):
        return
    
    data = await state.get_data()
    prev_messages = data.get('prev_messages', [])
    
    # Удаляем предыдущие сообщения
    await delete_previous_messages(message.chat.id, prev_messages)
    
    await state.set_state(OrderState.choosing_district)
    msg = await message.answer("Сначала выберите федеральный округ:", reply_markup=districts_kb())
    await state.update_data(prev_messages=[msg.message_id])
    await save_bot_message(message.from_user.id, msg.message_id)
    log_action(message.from_user.id, "start_catalog")

@dp.message(F.text == "🛒 Корзина")
async def show_cart(message: types.Message, state: FSMContext):
    if not await check_auth(message, state):
        return
    
    data = await state.get_data()
    prev_messages = data.get('prev_messages', [])
    
    # Удаляем предыдущие сообщения
    await delete_previous_messages(message.chat.id, prev_messages)
    
    user_id = message.from_user.id
    items = await get_user_cart(user_id)
    
    if not items:
        msg = await message.answer("🛒 Корзина пуста")
        await state.update_data(prev_messages=[msg.message_id])
        await save_bot_message(user_id, msg.message_id)
        return
    
    text = "🛒 Ваша корзина:\n\n"
    total = 0
    
    for prod_id, name, price, quantity in items:
        item_total = price * quantity
        total += item_total
        text += f"{name}\n{price} руб. × {quantity} = {item_total} руб.\n\n"
    
    text += f"💰 Итого: {total} руб."
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оформить заказ", callback_data="checkout_cart")],
        [InlineKeyboardButton(text="🗑️ Очистить корзину", callback_data="clear_cart")]
    ])
    
    msg = await message.answer(text, reply_markup=kb)
    await state.update_data(prev_messages=[msg.message_id])
    await save_bot_message(user_id, msg.message_id)
    log_action(user_id, "view_cart", f"items: {len(items)}")

@dp.message(F.text == "📦 Мои заказы")
async def show_orders(message: types.Message, state: FSMContext):
    if not await check_auth(message, state):
        return
    
    data = await state.get_data()
    prev_messages = data.get('prev_messages', [])
    
    # Удаляем предыдущие сообщения
    await delete_previous_messages(message.chat.id, prev_messages)
    
    user_id = message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT o.order_id, p.name, o.quantity, o.total_price, o.status, o.district, o.city, o.created_at
        FROM orders o
        JOIN products p ON o.product_id = p.id
        WHERE o.user_id = ?
        ORDER BY o.created_at DESC
        LIMIT 10
    ''', (user_id,))
    
    orders = cursor.fetchall()
    conn.close()
    
    if not orders:
        msg = await message.answer("📦 У вас нет заказов")
        await state.update_data(prev_messages=[msg.message_id])
        await save_bot_message(user_id, msg.message_id)
        return
    
    text = "📦 Ваши последние заказы:\n\n"
    for order_id, name, qty, total, status, district, city, created in orders:
        date = created.split()[0] if isinstance(created, str) else created
        status_icon = "✅" if status == 'paid' else "⏳" if status == 'pending' else "❌"
        text += f"#{order_id} {name} ×{qty}\n"
        text += f"Сумма: {total} руб. | Статус: {status_icon} {status}\n"
        text += f"Место: {city} ({district})\n"
        text += f"Дата: {date}\n\n"
    
    msg = await message.answer(text)
    await state.update_data(prev_messages=[msg.message_id])
    await save_bot_message(user_id, msg.message_id)
    log_action(user_id, "view_orders")

@dp.message(F.text == "👨‍💼 Поддержка")
async def support(message: types.Message, state: FSMContext):
    if not await check_auth(message, state):
        return
    
    data = await state.get_data()
    prev_messages = data.get('prev_messages', [])
    
    # Удаляем предыдущие сообщения
    await delete_previous_messages(message.chat.id, prev_messages)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Связь с оператором", url=f"https://t.me/{SUPPORT_USERNAME[1:]}")]
    ])
    
    msg = await message.answer(
        f"👨‍💼 Поддержка:\n\n"
        f"📞 Связь с оператором: {SUPPORT_USERNAME}\n"
        f"🆔 ID: {SUPPORT_ID}",
        reply_markup=kb
    )
    await state.update_data(prev_messages=[msg.message_id])
    await save_bot_message(message.from_user.id, msg.message_id)
    log_action(message.from_user.id, "support_requested")

@dp.message(F.text == "⚠️ Инструкция")
async def instructions(message: types.Message, state: FSMContext):
    if not await check_auth(message, state):
        return
    
    data = await state.get_data()
    prev_messages = data.get('prev_messages', [])
    
    # Удаляем предыдущие сообщения
    await delete_previous_messages(message.chat.id, prev_messages)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Перейти в канал с инструкциями", url="https://t.me/BlackoutBazaarInstructions")]
    ])
    
    msg = await message.answer(
        "📚 Инструкция по использованию бота находится в нашем канале:",
        reply_markup=kb
    )
    await state.update_data(prev_messages=[msg.message_id])
    await save_bot_message(message.from_user.id, msg.message_id)
    log_action(message.from_user.id, "instructions_viewed")

@dp.message(F.text == "💎 Купить TON")
async def buy_ton(message: types.Message, state: FSMContext):
    if not await check_auth(message, state):
        return
    
    data = await state.get_data()
    prev_messages = data.get('prev_messages', [])
    
    # Удаляем предыдущие сообщения
    await delete_previous_messages(message.chat.id, prev_messages)
    
    msg = await message.answer(
        "💎 Для покупки TON:\n\n"
        "1. Открой @CryptoBot в Telegram\n"
        "2. Нажми «Купить криптовалюту»\n"
        "3. Выбери TON\n"
        "4. Укажи сумму\n"
        "5. Оплати"
    )
    await state.update_data(prev_messages=[msg.message_id])
    await save_bot_message(message.from_user.id, msg.message_id)
    log_action(message.from_user.id, "buy_ton_requested")

@dp.message(F.text == "🤝 Партнёрка")
async def partner(message: types.Message, state: FSMContext):
    if not await check_auth(message, state):
        return
    
    data = await state.get_data()
    prev_messages = data.get('prev_messages', [])
    
    # Удаляем предыдущие сообщения
    await delete_previous_messages(message.chat.id, prev_messages)
    
    msg = await message.answer(
        "🤝 Партнёрская программа:\n\n"
        "Приводите клиентов - получайте 15%\n\n"
        f"Ваша ссылка:\n"
        f"https://t.me/your_bot?start=ref_{message.from_user.id}\n\n"
        "Статистика: /stats"
    )
    await state.update_data(prev_messages=[msg.message_id])
    await save_bot_message(message.from_user.id, msg.message_id)
    log_action(message.from_user.id, "partner_viewed")

# ==================== ОБРАБОТЧИКИ ДЛЯ КОЛБЭКОВ ====================
@dp.callback_query(F.data == "checkout_cart")
async def checkout_cart(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    prev_messages = data.get('prev_messages', [])
    
    # Удаляем предыдущие сообщения
    await delete_previous_messages(callback.message.chat.id, prev_messages)
    
    user_id = callback.from_user.id
    
    items = await get_user_cart(user_id)
    if not items:
        msg = await callback.message.answer("Корзина пуста. Добавьте товары из каталога.")
        await state.update_data(prev_messages=[msg.message_id])
        await save_bot_message(user_id, msg.message_id)
        return
    
    await state.set_state(OrderState.choosing_district)
    msg = await callback.message.answer("Для оформления заказа сначала выберите федеральный округ:", reply_markup=districts_kb())
    await state.update_data(prev_messages=[msg.message_id])
    await save_bot_message(user_id, msg.message_id)
    log_action(user_id, "cart_checkout_started")

@dp.callback_query(F.data == "clear_cart")
async def clear_cart(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    prev_messages = data.get('prev_messages', [])
    
    # Удаляем предыдущие сообщения
    await delete_previous_messages(callback.message.chat.id, prev_messages)
    
    user_id = callback.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM cart WHERE user_id = ?", (user_id,))
    count = cursor.fetchone()[0]
    
    cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    msg = await callback.message.answer(f"✅ Корзина очищена. Удалено товаров: {count}")
    await state.update_data(prev_messages=[msg.message_id])
    await save_bot_message(user_id, msg.message_id)
    log_action(user_id, "cart_cleared", f"items: {count}")

# ==================== КАТАЛОГ И ЗАКАЗЫ ====================
@dp.callback_query(F.data.startswith("district_"))
async def process_district(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    prev_messages = data.get('prev_messages', [])
    
    # Удаляем предыдущие сообщения
    await delete_previous_messages(callback.message.chat.id, prev_messages)
    
    district_key = callback.data.split("_", 1)[1]
    district_name = DISTRICTS[district_key]["name"]
    
    await state.update_data(district_key=district_key, district_name=district_name)
    await state.set_state(OrderState.choosing_city)
    
    msg = await callback.message.answer(
        f"📍 Округ: {district_name}\n\n"
        f"Выберите город:",
        reply_markup=cities_in_district_kb(district_key)
    )
    await state.update_data(prev_messages=[msg.message_id])
    await save_bot_message(callback.from_user.id, msg.message_id)
    log_action(callback.from_user.id, "district_selected", district_name)

@dp.callback_query(F.data.startswith("city_"))
async def process_city(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    prev_messages = data.get('prev_messages', [])
    
    # Удаляем предыдущие сообщения
    await delete_previous_messages(callback.message.chat.id, prev_messages)
    
    city = callback.data.split("_", 1)[1]
    data = await state.get_data()
    district_name = data.get('district_name', '')
    
    await state.update_data(city=city)
    await state.set_state(OrderState.choosing_category)
    
    msg = await callback.message.answer(
        f"📍 Округ: {district_name}\n"
        f"🏙️ Город: {city}\n\n"
        f"Выберите категорию:",
        reply_markup=categories_kb()
    )
    await state.update_data(prev_messages=[msg.message_id])
    await save_bot_message(callback.from_user.id, msg.message_id)
    log_action(callback.from_user.id, "city_selected", f"{district_name} - {city}")

@dp.callback_query(F.data.startswith("cat_"))
async def process_category(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    prev_messages = data.get('prev_messages', [])
    
    # Удаляем предыдущие сообщения
    await delete_previous_messages(callback.message.chat.id, prev_messages)
    
    category = callback.data.split("_", 1)[1]
    data = await state.get_data()
    city = data.get('city', 'Москва')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, price, description, weight FROM products WHERE category = ?",
        (category,)
    )
    products = cursor.fetchall()
    conn.close()
    
    if not products:
        msg = await callback.message.answer(f"В городе {city} нет товаров в категории {category}")
        await state.update_data(prev_messages=[msg.message_id])
        await save_bot_message(callback.from_user.id, msg.message_id)
        return
    
    builder = InlineKeyboardBuilder()
    for prod_id, name, price, desc, weight in products:
        builder.add(InlineKeyboardButton(
            text=f"{name} - {price} руб.",
            callback_data=f"prod_{prod_id}"
        ))
    builder.adjust(1)
    
    await state.set_state(OrderState.choosing_product)
    await state.update_data(category=category)
    
    # Показываем товары
    text = f"🎯 {category}\n"
    text += f"🏙️ Город: {city}\n\n"
    
    msg = await callback.message.answer(
        text,
        reply_markup=builder.as_markup()
    )
    await state.update_data(prev_messages=[msg.message_id])
    await save_bot_message(callback.from_user.id, msg.message_id)
    log_action(callback.from_user.id, "category_selected", category)

@dp.callback_query(F.data.startswith("prod_"))
async def process_product(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    prev_messages = data.get('prev_messages', [])
    
    # Удаляем предыдущие сообщения
    await delete_previous_messages(callback.message.chat.id, prev_messages)
    
    product_id = int(callback.data.split("_", 1)[1])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, price, description, weight FROM products WHERE id = ?", (product_id,))
    product = cursor.fetchone()
    conn.close()
    
    if product:
        name, price, desc, weight = product
        await state.update_data(product_id=product_id, product_name=name, price=price, weight=weight)
        await state.set_state(OrderState.choosing_quantity)
        
        msg = await callback.message.answer(
            f"🎯 Товар: {name}\n"
            f"💰 Цена: {price} руб.\n\n"
            f"Введите количество:"
        )
        await state.update_data(prev_messages=[msg.message_id])
        await save_bot_message(callback.from_user.id, msg.message_id)
        log_action(callback.from_user.id, "product_selected", name)

@dp.message(OrderState.choosing_quantity)
async def process_quantity(message: types.Message, state: FSMContext):
    data = await state.get_data()
    prev_messages = data.get('prev_messages', [])
    
    # Удаляем предыдущие сообщения
    await delete_previous_messages(message.chat.id, prev_messages)
    
    try:
        quantity = int(message.text)
        if quantity <= 0 or quantity > 100:
            msg = await message.answer("Введите число от 1 до 100:")
            await state.update_data(prev_messages=[msg.message_id])
            await save_bot_message(message.from_user.id, msg.message_id)
            return
    except:
        msg = await message.answer("Введите число:")
        await state.update_data(prev_messages=[msg.message_id])
        await save_bot_message(message.from_user.id, msg.message_id)
        return
    
    data = await state.get_data()
    total = data['price'] * quantity
    
    await state.update_data(quantity=quantity, total=total)
    await state.set_state(OrderState.choosing_crypto)
    
    msg = await message.answer(
        f"📋 Заказ:\n\n"
        f"Товар: {data['product_name']}\n"
        f"Город: {data['city']}\n"
        f"Количество: {quantity}\n"
        f"Цена: {data['price']} руб.\n"
        f"Итого: {total} руб.\n\n"
        f"Выберите валюту:",
        reply_markup=crypto_kb()
    )
    await state.update_data(prev_messages=[msg.message_id])
    await save_bot_message(message.from_user.id, msg.message_id)
    log_action(message.from_user.id, "quantity_entered", f"{data['product_name']} x{quantity}")

@dp.callback_query(F.data.startswith("crypto_"))
async def process_crypto(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    prev_messages = data.get('prev_messages', [])
    
    # Удаляем предыдущие сообщения
    await delete_previous_messages(callback.message.chat.id, prev_messages)
    
    crypto = callback.data.split("_", 1)[1]
    
    crypto_prices = {
        "TON": 150,
        "USDT": 81,
        "BTC": 7311495,
        "ETH": 251049
    }
    
    order_data = await state.get_data()
    total_rub = order_data['total']
    
    if crypto not in crypto_prices:
        msg = await callback.message.answer("Неверная валюта. Выберите снова.", reply_markup=crypto_kb())
        await state.update_data(prev_messages=[msg.message_id])
        await save_bot_message(callback.from_user.id, msg.message_id)
        return
    
    crypto_amount = total_rub / crypto_prices[crypto]
    
    await state.update_data(crypto=crypto, crypto_amount=crypto_amount)
    await state.set_state(OrderState.confirming_order)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_order")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_order")]
    ])
    
    crypto_name = "💎 TON" if crypto == "TON" else "💵 USDT" if crypto == "USDT" else f"₿ {crypto}" if crypto == "BTC" else f"Ξ {crypto}"
    
    msg = await callback.message.answer(
        f"📋 Заказ:\n\n"
        f"Товар: {order_data['product_name']}\n"
        f"Город: {order_data['city']}\n"
        f"Количество: {order_data['quantity']}\n"
        f"Сумма: {total_rub} руб.\n"
        f"Валюта: {crypto_name}\n"
        f"К оплате: ~{crypto_amount:.6f}\n\n"
        f"Подтвердить?",
        reply_markup=kb
    )
    await state.update_data(prev_messages=[msg.message_id])
    await save_bot_message(callback.from_user.id, msg.message_id)
    log_action(callback.from_user.id, "crypto_selected", f"{crypto}")

@dp.callback_query(F.data == "confirm_order")
async def confirm_order(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    prev_messages = data.get('prev_messages', [])
    
    # Удаляем предыдущие сообщения
    await delete_previous_messages(callback.message.chat.id, prev_messages)
    
    data = await state.get_data()
    user_id = callback.from_user.id
    
    # Генерируем 6-значный код
    six_digit_code = generate_six_digit_code()
    
    pay_url, invoice_id = await crypto_bot.create_invoice(
        asset=data['crypto'],
        amount=data['crypto_amount'],
        description=f"Заказ товара: {data['product_name']}"
    )
    
    if not pay_url or not invoice_id:
        msg = await callback.message.answer(
            "❌ Ошибка оплаты. Попробуйте позже."
        )
        await state.update_data(prev_messages=[msg.message_id])
        await save_bot_message(user_id, msg.message_id)
        log_action(user_id, "cryptobot_api_error", "Failed to create invoice")
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO orders (user_id, product_id, quantity, total_price, district, city, 
                          cryptobot_invoice_id, cryptobot_asset, cryptobot_amount, cryptobot_pay_url, 
                          six_digit_code, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        user_id, data['product_id'], data['quantity'], data['total'],
        data.get('district_name', ''), data['city'],
        invoice_id, data['crypto'], data['crypto_amount'], pay_url,
        six_digit_code, datetime.now().isoformat()
    ))
    
    order_id = cursor.lastrowid
    
    cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
    
    conn.commit()
    conn.close()
    
    await state.set_state(OrderState.waiting_payment)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💳 Оплатить {data['crypto_amount']:.6f} {data['crypto']}", url=pay_url)],
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"check_{invoice_id}")]
    ])
    
    crypto_name = "💎 TON" if data['crypto'] == "TON" else "💵 USDT" if data['crypto'] == "USDT" else f"₿ {data['crypto']}" if data['crypto'] == "BTC" else f"Ξ {data['crypto']}"
    
    # Разделяем сообщение на 2 части
    msg1 = await callback.message.answer(
        f"✅ Заказ #{order_id} оформлен!\n\n"
        f"Товар: {data['product_name']} ×{data['quantity']}\n"
        f"Город: {data['city']}\n"
        f"Сумма: {data['crypto_amount']:.6f} {crypto_name}\n\n"
        f"⚠️ Ваш код: `{six_digit_code}`\n"
        f"Укажите его при оплате!"
    )
    
    msg2 = await callback.message.answer(
        f"1. Нажмите '💳 Оплатить'\n"
        f"2. Оплатите точную сумму\n"
        f"3. В комментарии укажите код: `{six_digit_code}`\n"
        f"4. Нажмите '✅ Я оплатил'\n\n"
        f"После оплаты:\n"
        f"{SUPPORT_USERNAME}\n\n"
        f"⚠️ Счет действует 1 час.",
        reply_markup=keyboard
    )
    
    await state.update_data(prev_messages=[msg1.message_id, msg2.message_id])
    await save_bot_message(user_id, msg1.message_id)
    await save_bot_message(user_id, msg2.message_id)
    log_action(user_id, "order_created", 
              f"order: {order_id}, city: {data['city']}, crypto: {data['crypto']}, code: {six_digit_code}")

@dp.callback_query(F.data == "cancel_order")
async def cancel_order(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    prev_messages = data.get('prev_messages', [])
    
    # Удаляем предыдущие сообщения
    await delete_previous_messages(callback.message.chat.id, prev_messages)
    
    await state.clear()
    msg = await callback.message.answer("❌ Заказ отменен.")
    await state.update_data(prev_messages=[msg.message_id])
    await save_bot_message(callback.from_user.id, msg.message_id)
    log_action(callback.from_user.id, "order_cancelled")

@dp.callback_query(F.data.startswith("check_"))
async def check_payment_callback(callback: types.CallbackQuery, state: FSMContext):
    invoice_id = callback.data.replace("check_", "")
    
    status = await crypto_bot.check_invoice_status(invoice_id)
    
    if status == "paid":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT order_id, user_id, six_digit_code FROM orders WHERE cryptobot_invoice_id = ?",
            (invoice_id,)
        )
        result = cursor.fetchone()
        
        if result:
            order_id, user_id, six_digit_code = result
            cursor.execute(
                "UPDATE orders SET status = 'paid', payment_confirmed = 1 WHERE order_id = ?",
                (order_id,)
            )
            conn.commit()
            conn.close()
            
            data = await state.get_data()
            prev_messages = data.get('prev_messages', [])
            
            # Удаляем предыдущие сообщения
            await delete_previous_messages(callback.message.chat.id, prev_messages)
            
            msg = await callback.message.answer(
                "✅ Оплачено!\n\n"
                f"Заказ #{order_id}\n"
                f"Код: `{six_digit_code}`\n\n"
                f"Свяжитесь с поддержкой:\n"
                f"{SUPPORT_USERNAME}"
            )
            await state.update_data(prev_messages=[msg.message_id])
            await save_bot_message(user_id, msg.message_id)
            await callback.answer("Оплата подтверждена!")
            log_action(user_id, "payment_confirmed_callback", f"order: {order_id}, code: {six_digit_code}")
        else:
            await callback.answer("Заказ не найден")
    elif status == "active":
        await callback.answer("Платёж ещё не поступил. Подождите 1-2 минуты.")
    else:
        await callback.answer("Платёж не найден или просрочен")

# ==================== АВТОМАТИЧЕСКАЯ ПРОВЕРКА ПЛАТЕЖЕЙ ====================
async def check_payments_periodically():
    while True:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT order_id, user_id, cryptobot_invoice_id, six_digit_code FROM orders WHERE status = 'pending' AND cryptobot_invoice_id IS NOT NULL AND created_at > ?",
                ((datetime.now() - timedelta(hours=2)).isoformat(),)
            )
            pending_orders = cursor.fetchall()
            conn.close()
            
            for order_id, user_id, invoice_id, six_digit_code in pending_orders:
                if not invoice_id:
                    continue
                    
                status = await crypto_bot.check_invoice_status(invoice_id)
                
                if status == "paid":
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE orders SET status = 'paid', payment_confirmed = 1 WHERE order_id = ?",
                        (order_id,)
                    )
                    conn.commit()
                    conn.close()
                    
                    try:
                        await bot.send_message(
                            user_id,
                            f"✅ Оплата #{order_id} подтверждена!\n\n"
                            f"Код: `{six_digit_code}`\n\n"
                            f"Свяжитесь с поддержкой:\n"
                            f"{SUPPORT_USERNAME}"
                        )
                    except:
                        pass
                    
                    log_action(user_id, "auto_payment_confirmed", f"order: {order_id}, code: {six_digit_code}")
        
        except Exception as e:
            logging.error(f"Payment check error: {e}")
        
        await asyncio.sleep(60)

# ==================== ЗАПУСК ====================
async def main():
    logger.info("Bot starting...")
    
    asyncio.create_task(check_payments_periodically())
    
    try:
        await dp.start_polling(bot)
    finally:
        await crypto_bot.close()

if __name__ == '__main__':
    asyncio.run(main())
