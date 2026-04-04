import json
import os
import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram.filters import Command

TOKEN = "7966858937:AAEJot3qSamrS36WDIhdm4C7Xp57JyJDne0"
ADMIN_ID = 1085706185

bot = Bot(token=TOKEN)
dp = Dispatcher()

user_modes = {}

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
            idx = val % base
            res.insert(0, self.CHARS[idx])
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

    await msg.answer("👋 Привет! Выбери действие 👇")
    await msg.answer("👇 Выбери действие:", reply_markup=menu())

# ===== КНОПКИ =====
@dp.callback_query()
async def cb(call: types.CallbackQuery):
    user_id = call.from_user.id

    if call.data == "c2i":
        user_modes[user_id] = "c2i"
        await call.message.answer("Введи код (пример: XABC123)")

    elif call.data == "i2c":
        user_modes[user_id] = "i2c"
        await call.message.answer("Введи ID")

    elif call.data == "gen":
        user_modes[user_id] = "gen"
        await call.message.answer("Введите код и количество\nПример:\nXABC123 10")

    await call.answer()

# ===== ЛОГИКА =====
@dp.message()
async def handle(msg: types.Message):
    text = msg.text.strip()
    parts = text.split()
    mode = user_modes.get(msg.from_user.id)

    # ===== ДОБАВЛЕНО: ЖЁСТКАЯ ПРОВЕРКА =====
    if mode is None:
        await msg.answer("🆔 Сначала выбери действие 👇", reply_markup=menu())
        return

    try:
        # ===== ГЕНЕРАЦИЯ =====
        if mode == "gen" and len(parts) == 2:
            code = parts[0].upper()
            count = int(parts[1])

            start_id = abs(hash(code)) % (10**9)

            wait_msg = await msg.answer("⏳ Генерирую...")
            await asyncio.sleep(2)

            result = ""
            for i in range(count):
                cur_id = start_id + i
                new_code = converter.to_code(cur_id)

                if not new_code:
                    new_code = f"INVALID_{cur_id}"

                link = f"https://link.brawlstars.com/?tag={new_code}"
                result += f"{i+1}. {new_code}\nID: {cur_id}\n🔗 {link}\n\n"

            filename = f"codes_{count}.txt"

            with open(filename, "w", encoding="utf-8") as f:
                f.write(result)

            with open(filename, "rb") as f:
                await msg.answer_document(f)

            user_modes[msg.from_user.id] = None  # ← ДОБАВЛЕНО

            await wait_msg.delete()
            await msg.answer("👇 Выбери действие:", reply_markup=menu())
            return

        # ===== КОД → ID =====
        elif mode == "c2i":
            id_val = converter.to_id(text)

            if id_val == -1:
                await msg.answer("❌ Неверный код", reply_markup=menu())
            else:
                await msg.answer(f"ID: {id_val}", reply_markup=menu())

            user_modes[msg.from_user.id] = None  # ← ДОБАВЛЕНО
            return

        # ===== ID → КОД =====
        elif mode == "i2c":
            if text.isdigit():
                code = converter.to_code(int(text))

                if code:
                    await msg.answer(f"Код: {code}", reply_markup=menu())
                else:
                    await msg.answer("❌ Ошибка", reply_markup=menu())
            else:
                await msg.answer("❌ Введи ID", reply_markup=menu())

            user_modes[msg.from_user.id] = None  # ← ДОБАВЛЕНО
            return

    except Exception as e:
        print(e)
        await msg.answer("❌ Ошибка", reply_markup=menu())

# ===== ЗАПУСК =====
async def main():
    print("Бот запущен 🚀")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
