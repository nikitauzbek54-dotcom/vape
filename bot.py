import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from database import Database
from handlers import user, admin

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 0))
MANAGER_ID = int(os.getenv("MANAGER_ID", 0))
DATABASE_URL = os.getenv("DATABASE_URL")

db = Database(DATABASE_URL)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

admin_ids = [OWNER_ID]
if MANAGER_ID:
    admin_ids.append(MANAGER_ID)


async def main():
    await db.connect()
    # Регистрируем админов в БД
    await db.add_admin(OWNER_ID, "owner")
    if MANAGER_ID:
        await db.add_admin(MANAGER_ID, "manager")
    # Дефолтные настройки
    if not await db.get_setting("pickup_address"):
        await db.set_setting("pickup_address", "Уточните у менеджера")
    if not await db.get_setting("about_text"):
        await db.set_setting("about_text", "Ondetlin shop — вейп-шоп в Новосибирске.")

    # Middleware: прокидываем db, bot, admin_ids
    dp["db"] = db
    dp["bot"] = bot
    dp["admin_ids"] = admin_ids

    dp.include_router(admin.router)
    dp.include_router(user.router)

    print("✅ Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())