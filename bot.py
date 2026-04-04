import json
import os
import asyncio
import signal

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram.filters import Command
from aiohttp import web

USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(list(users), f)

TOKEN = "7966858937:AAEJot3qSamrS36WDIhdm4C7Xp57JyJDne0"
ADMIN_ID = 1085706185

bot = Bot(token=TOKEN)
dp = Dispatcher()

users = load_users()
online_users = set()

# ===== УДАЛЕНИЕ WEBHOOK =====
async def delete_webhook_on_start():
    await bot.delete_webhook(drop_pending_updates=True)

# ===== УБИЙСТВО СТАРОГО ПРОЦЕССА =====
PID_FILE = "bot.pid"

def kill_old_process():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                old_pid = int(f.read())

            print(f"Пытаюсь убить старый процесс: {old_pid}")
            os.kill(old_pid, signal.SIGTERM)
        except Exception as e:
            print(f"Не удалось убить старый процесс: {e}")

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

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

# ===== КНОПКИ =====
def menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Код → ID", callback_data="c2i")],
        [InlineKeyboardButton(text="🆔 ID → Код", callback_data="i2c")],
        [InlineKeyboardButton(text="📈 Генерация кодов", callback_data="gen")]
    ])

# ===== TELEGRAM MENU =====
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Как пользоваться"),
        BotCommand(command="stats", description="Статистика (админ)"),
    ]
    await bot.set_my_commands(commands)

# ===== START =====
@dp.message(Command("start"))
async def start(msg: types.Message):
    user_id = msg.from_user.id
    users.add(user_id)
    save_users(users)
    online_users.add(user_id)

    await msg.answer(
        "👋 Привет!\n\n"
        "Я бот, который поможет тебе работать с кодами команд в Brawl Stars 🎮\n\n"
        "С моей помощью ты можешь:\n"
        "🔑 преобразовать код команды в ID\n"
        "🆔 преобразовать ID обратно в код\n"
        "📈 генерировать следующие коды на основе твоего\n\n"
        "Если что-то не понятно, напиши /help 📘\n"
        "Я делаю всё быстро и точно. Выбери действие ниже 👇"
    )

    await msg.answer("👇 Выбери действие:", reply_markup=menu())

# ===== HELP =====
@dp.message(Command("help"))
async def help_cmd(msg: types.Message):
    await msg.answer(
        "📘 Как пользоваться:\n\n"
        "🔑 Код → ID\n"
        "XZZJHPS → ID\n\n"
        "🆔 ID → Код\n"
        "123456789 → Код\n\n"
        "📈 Генерация кодов\n"
        "XZZJHPS 3\n\n",
        reply_markup=menu()
    )

# ===== СТАТИСТИКА =====
@dp.message(Command("stats"))
async def stats(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return

    await msg.answer(
        f"👥 Всего пользователей: {len(users)}\n"
        f"🟢 Онлайн: {len(online_users)}"
    )

# ===== КНОПКИ =====
@dp.callback_query()
async def cb(call: types.CallbackQuery):
    if call.data == "c2i":
        await call.message.answer("Введи код (пример: XABC123)")
    elif call.data == "i2c":
        await call.message.answer("Введи ID")
    elif call.data == "gen":
        await call.message.answer("Введите код и количество следующих кодов\nПример:\nXABC123 100")
    await call.answer()

# ===== ЛОГИКА =====
@dp.message()
async def handle(msg: types.Message):
    text = msg.text.strip()
    parts = text.split()

    try:
        if len(parts) == 2:
            code = parts[0].upper()
            count = int(parts[1])

            start_id = converter.to_id(code)

            if start_id == -1:
                await msg.answer("❌ Неверный код", reply_markup=menu())
                return

            result = ""
            for i in range(count):
                cur_id = start_id + i
                new_code = converter.to_code(cur_id)
                if new_code:
                    link = f"https://link.brawlstars.com/?tag={new_code}"
                    result += f"{i+1}. {new_code}\nID: {cur_id}\n🔗 {link}\n\n"

            filename = f"brawl_codes_{count}.txt"
            file = types.BufferedInputFile(result.encode(), filename=filename)
            await msg.answer_document(file)

            await msg.answer("👇 Выбери действие:", reply_markup=menu())
            return

        elif text.upper().startswith("X"):
            id_val = converter.to_id(text)
            if id_val == -1:
                await msg.answer("❌ Неверный код", reply_markup=menu())
            else:
                await msg.answer(f"ID: {id_val}", reply_markup=menu())

        elif text.isdigit():
            code = converter.to_code(int(text))
            if code:
                await msg.answer(f"Код: {code}", reply_markup=menu())
            else:
                await msg.answer("❌ Ошибка", reply_markup=menu())

        else:
            await msg.answer("❌ Неверный формат", reply_markup=menu())

    except:
        await msg.answer("❌ Ошибка ввода", reply_markup=menu())

# ===== WEB SERVER =====
async def web_server():
    app = web.Application()
    app.router.add_get('/', lambda request: web.Response(text="Bot is alive!"))

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# ===== MAIN =====
async def main():
    kill_old_process()  # 👈 ДОБАВЛЕНО
    await delete_webhook_on_start()
    await set_commands(bot)
    await web_server()
    print("Бот запущен 🚀")
    print("Polling started")
    await dp.start_polling(bot)

# ===== START =====
if __name__ == "__main__":
    asyncio.run(main())
