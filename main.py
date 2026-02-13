import asyncio
import logging
from datetime import datetime, timezone, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN
from calendar_service import get_auth_url, get_credentials_from_code, get_upcoming_events, get_past_events
from database import init_db, set_token, get_user_data, get_all_users, set_reminder

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

MONTHS = ["", "января", "февраля", "марта", "апреля", "мая", "июня",
          "июля", "августа", "сентября", "октября", "ноября", "декабря"]


# ---фон.задача проверка уведомлений---
async def check_calendar_notifications():
    users = await get_all_users()
    for user_id, token_json, remind_mins in users:
        if not token_json: continue
        try:
            events = await get_upcoming_events(token_json)
            for event in events:
                start_str = event['start'].get('dateTime', event['start'].get('date'))
                start_time = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                diff = start_time - now

                if timedelta(minutes=remind_mins - 2) <= diff <= timedelta(minutes=remind_mins + 2):
                    date_text = f"{start_time.day} {MONTHS[start_time.month]} {start_time.year}, {start_time.strftime('%H:%M')}"

                    link = event.get('hangoutLink') or event.get('htmlLink') or "Ссылка отсутствует"

                    msg = (
                        "⏰ **Напоминание!**\n\n"
                        f"**Встреча:**\n\"{event.get('summary', 'Без названия')}\"\n\n"
                        f"**Время:** {date_text}\n\n"
                        f"**Ссылка:** [перейти к событию]({link})"
                    )
                    await bot.send_message(user_id, msg, parse_mode="Markdown", disable_web_page_preview=True)
        except Exception as e:
            logging.error(f"Ошибка планировщика для {user_id}: {e}")


# ---команды---

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    kb = [
        [types.KeyboardButton(text="/events"), types.KeyboardButton(text="/history")],
        [types.KeyboardButton(text="/set_reminder 15"), types.KeyboardButton(text="/help")],
        [types.KeyboardButton(text="/auth")]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n"
        "Я PlanMan — твой ассистент Google Календаря.\n\n"
        "Нажми **/help**, чтобы увидеть список команд.",
        reply_markup=keyboard, parse_mode="Markdown"
    )


@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "📖 **Справка по командам:**\n\n"
        "🔐 /auth — Подключить Google Календарь\n"
        "📅 /events — Ближайшие 10 встреч\n"
        "📂 /history — Последние 10 прошедших встреч\n"
        "⚙️ `/set_reminder 30` — Настройка времени уведомления\n",
        parse_mode="Markdown"
    )


@dp.message(Command("auth"))
async def auth_command(message: types.Message):
    url = get_auth_url(message.from_user.id)
    await message.answer(f"🔗 [Авторизоваться в Google]({url})\n\nПришли код подтверждения в ответ на это сообщение.",
                         parse_mode="Markdown")


@dp.message(Command("set_reminder"))
async def set_reminder_cmd(message: types.Message):
    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit():
        return await message.answer("⚠️ Формат: `/set_reminder 30`", parse_mode="Markdown")
    mins = int(args[1])
    await set_reminder(message.from_user.id, mins)
    await message.answer(f"✅ Настройки сохранены. Напомню за {mins} мин.")


@dp.message(Command("events"))
async def events_command(message: types.Message):
    data = await get_user_data(message.from_user.id)
    if not data or not data[1]: return await message.answer("Сначала /auth")
    events = await get_upcoming_events(data[1])
    if not events: return await message.answer("Будущих встреч нет.")

    text = "📅 Предстоящие встречи:\n\n"
    for ev in events:
        start_str = ev['start'].get('dateTime', ev['start'].get('date'))
        dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
        text += f"🔹 {ev.get('summary')} — {dt.strftime('%d.%m %H:%M')}\n"
    await message.answer(text, parse_mode="Markdown")


@dp.message(Command("history"))
async def history_command(message: types.Message):
    data = await get_user_data(message.from_user.id)
    if not data or not data[1]: return await message.answer("Сначала /auth")
    events = await get_past_events(data[1])
    if not events: return await message.answer("История пуста.")

    text = "📂 Последние 10 встреч:\n\n"
    for i, ev in enumerate(events, 1):
        start_str = ev['start'].get('dateTime', ev['start'].get('date'))
        dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
        text += f"{i}. [{dt.strftime('%d.%m.%Y %H:%M')}] {ev.get('summary')}\n"
    await message.answer(text, parse_mode="Markdown")


@dp.message()
async def handle_msg(message: types.Message):
    if len(message.text) > 20 and not message.text.startswith('/'):
        try:
            token = await get_credentials_from_code(message.text)
            await set_token(message.from_user.id, token)
            await message.answer("✅ Авторизация успешна!")
        except:
            await message.answer("❌ Неверный код.")
    elif message.text.startswith('/set_reminder'):
        await set_reminder_cmd(message)


async def main():
    await init_db()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_calendar_notifications, "interval", minutes=5)
    scheduler.start()
    print("Бот PlanMan запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())