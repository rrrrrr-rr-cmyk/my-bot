import asyncio
import io

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.exceptions import TelegramRetryAfter

TOKEN = "7966858937:AAGwXAM-P5dwRvRCTAByvD2j4Wt6SI-lvZw"
ADMIN_ID = 1085706185

bot = Bot(token=TOKEN)
dp = Dispatcher()

users = set()
online_users = set()
user_modes = {}

# ===== SAFE SEND =====
async def safe_send(func, *args, **kwargs):
    while True:
        try:
            return await func(*args, **kwargs)
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)

# ===== КНОПКИ =====
def menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Код → ID", callback_data="c2i")],
        [InlineKeyboardButton(text="🆔 ID → Код", callback_data="i2c")],
        [InlineKeyboardButton(text="📈 Генерация кодов", callback_data="gen")]
    ])

# ===== КОНВЕРТЕР =====
class LongToCodeConverter:
    CHARS = "QWERTYUPASDFGHJKLZCVBNM23456789"
    TAG = "X"

    def _to_long(self, hi, lo):
        return (hi << 32) | (lo & 0xFFFFFFFF)

    def _convert(self, val):
        res = []
        base = len(self.CHARS)
        while val > 0:
            res.insert(0, self.CHARS[val % base])
            val //= base
        return ''.join(res)

    def to_code(self, id_val):
        hi = id_val >> 32
        lo = id_val & 0xFFFFFFFF

        if hi >= 256:
            return None

        l = self._to_long(lo >> 24, hi | (lo << 8))
        return self.TAG + self._convert(l)

    def to_id(self, code):
        code = code.strip().upper()

        if not code.startswith("X"):
            return -1

        code = code[1:]

        base = len(self.CHARS)
        unk6 = 0
        unk7 = 0

        for c in code:
            idx = self.CHARS.find(c)
            if idx == -1:
                return -1

            unk12 = unk6 * base + idx
            unk7 = ((unk7 << 32) | unk6) * base + idx >> 32
            unk6 = unk12

        v13 = ((unk7 << 32) | unk12) >> 8
        lo = v13 & 0x7FFFFFFF
        hi = unk6 & 0xFF

        return self._to_long(hi, lo)

converter = LongToCodeConverter()

# ===== START =====
@dp.message(Command("start"))
async def start(msg: types.Message):
    user_modes[msg.from_user.id] = None
    users.add(msg.from_user.id)
    online_users.add(msg.from_user.id)

    await safe_send(msg.answer,
        "👋 Привет!\n\n"
        "Я бот, который поможет тебе работать с кодами команд в Brawl Stars 🎮\n\n"
        "С моей помощью ты можешь:\n"
        "🔑 преобразовать код команды в ID\n"
        "🆔 преобразовать ID обратно в код\n"
        "📈 генерировать следующие коды на основе твоего\n\n"
        "Если что-то не понятно, напиши /help 📘\n"
        "Я делаю всё быстро и точно. Выбери действие ниже 👇"
    )

    await safe_send(msg.answer, "👇 Выбери действие:", reply_markup=menu())

# ===== КНОПКИ =====
@dp.callback_query()
async def cb(call: types.CallbackQuery):
    uid = call.from_user.id

    if call.data == "c2i":
        user_modes[uid] = "c2i"
        await safe_send(call.message.answer, "Введи код")

    elif call.data == "i2c":
        user_modes[uid] = "i2c"
        await safe_send(call.message.answer, "Введи ID")

    elif call.data == "gen":
        user_modes[uid] = "gen"
        await safe_send(call.message.answer, "Введи код и количество\nПример:\nXA 1000")

    await call.answer()

# ===== ГЕНЕРАЦИЯ =====
@dp.message()
async def handle(msg: types.Message):
    text = msg.text.strip()
    parts = text.split()
    mode = user_modes.get(msg.from_user.id)

    if mode not in ["gen", "c2i", "i2c"]:
        await safe_send(msg.answer, "❌ Сначала нажми кнопку 👇", reply_markup=menu())
        return

    if mode == "gen":
        if len(parts) != 2 or not parts[1].isdigit():
            await safe_send(msg.answer, "❌ Пример: XA 1000", reply_markup=menu())
            return

        code = parts[0].upper()
        count = int(parts[1])

        start_id = converter.to_id(code)
        if start_id == -1:
            await safe_send(msg.answer, "❌ Неверный код", reply_markup=menu())
            return

        batch_size = 200  # 🔥 делим на части

        for start in range(0, count + 1, batch_size):
            result = ""

            for i in range(start, min(start + batch_size, count + 1)):
                cur_id = start_id + i
                new_code = converter.to_code(cur_id)

                if not new_code:
                    continue

                link = f"https://link.brawlstars.com/?tag={new_code}"
                result += f"{i+1}. {new_code}\n🔗 {link}\n\n"

            file = io.BytesIO(result.encode())
            file.name = f"codes_{start}_{start+batch_size}.txt"

            await safe_send(msg.answer_document, file)
            await asyncio.sleep(1)  # 🔥 анти-флуд

        user_modes[msg.from_user.id] = None
        await safe_send(msg.answer, "👇 Выбери действие:", reply_markup=menu())
