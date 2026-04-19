import asyncio
import io

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

TOKEN = "YOUR_NEW_TOKEN"
ADMIN_ID = 1085706185

bot = Bot(token=TOKEN)
dp = Dispatcher()

users = set()
online_users = set()
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

    await msg.answer(
        "👋 Привет!\n\n"
        "Выбери действие 👇"
    )
    await msg.answer("👇 Меню:", reply_markup=menu())

# ===== HELP =====
@dp.message(Command("help"))
async def help_cmd(msg: types.Message):
    await msg.answer(
        "📘 Примеры:\n\n"
        "Код → ID:\nXABC123\n\n"
        "ID → Код:\n123456\n\n"
        "Генерация:\nXABC123 10",
        reply_markup=menu()
    )

# ===== STATS =====
@dp.message(Command("stats"))
async def stats(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return

    await msg.answer(
        f"👥 Пользователи: {len(users)}\n"
        f"🟢 Онлайн: {len(online_users)}"
    )

# ===== КНОПКИ =====
@dp.callback_query()
async def cb(call: types.CallbackQuery):
    uid = call.from_user.id

    if call.data == "c2i":
        user_modes[uid] = "c2i"
        await call.message.answer("Введи код")

    elif call.data == "i2c":
        user_modes[uid] = "i2c"
        await call.message.answer("Введи ID")

    elif call.data == "gen":
        user_modes[uid] = "gen"
        await call.message.answer("Введи код и количество\nПример:\nXA 10")

    await call.answer()

# ===== ЛОГИКА =====
@dp.message()
async def handle(msg: types.Message):
    text = msg.text.strip()
    parts = text.split()
    mode = user_modes.get(msg.from_user.id)

    if mode not in ["gen", "c2i", "i2c"]:
        await msg.answer("❌ Сначала нажми кнопку", reply_markup=menu())
        return

    try:
        # ===== ГЕНЕРАЦИЯ =====
        if mode == "gen":
            if len(parts) != 2:
                await msg.answer("❌ Пример: XA 10", reply_markup=menu())
                return

            code = parts[0].upper()

            if not parts[1].isdigit():
                await msg.answer("❌ Количество должно быть числом", reply_markup=menu())
                return

            count = int(parts[1])

            start_id = converter.to_id(code)
            if start_id == -1:
                await msg.answer("❌ Неверный код", reply_markup=menu())
                return

            result = ""
            for i in range(count + 1):
                cur_id = start_id + i
                new_code = converter.to_code(cur_id)

                if not new_code:
                    continue

                link = f"https://link.brawlstars.com/?tag={new_code}"
                result += f"{i+1}. {new_code}\nID: {cur_id}\n🔗 {link}\n\n"

            file = io.BytesIO(result.encode())
            file.name = f"codes_{count}.txt"

            await msg.answer_document(file)

            user_modes[msg.from_user.id] = None
            await msg.answer("👇 Меню:", reply_markup=menu())
            return

        # ===== КОД → ID =====
        elif mode == "c2i":
            id_val = converter.to_id(text)

            if id_val == -1:
                await msg.answer("❌ Неверный код", reply_markup=menu())
            else:
                await msg.answer(f"ID: {id_val}", reply_markup=menu())

            user_modes[msg.from_user.id] = None
            return

        # ===== ID → КОД =====
        elif mode == "i2c":
            if not text.isdigit():
                await msg.answer("❌ Введи число", reply_markup=menu())
                return

            code = converter.to_code(int(text))
            await msg.answer(f"Код: {code}", reply_markup=menu())

            user_modes[msg.from_user.id] = None
            return

    except Exception as e:
        print("ERROR:", e)
        await msg.answer("❌ Ошибка", reply_markup=menu())

# ===== ЗАПУСК =====
async def main():
    print("Бот запущен 🚀")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
