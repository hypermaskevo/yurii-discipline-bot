 # yurii_discipline_bot_v3.6.py
import json
import os
import datetime
import asyncio
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes,
    filters, CallbackQueryHandler
)
from dotenv import load_dotenv

# Load .env
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
USER_ID = int(os.getenv("USER_ID"))

# Load plan
with open("yurii_discipline_plan_30days_v36.json", "r", encoding="utf-8") as f:
    full_plan = json.load(f)

# State
user_state = {
    "day": 1,
    "hellmode": False,
    "confirmed": False,
    "strike": 0,
    "streak": 0,
    "task_timer": {},
    "weekly_goal": ""
}

JOURNAL_FILE = "journal.json"
if os.path.exists(JOURNAL_FILE):
    with open(JOURNAL_FILE, "r", encoding="utf-8") as f:
        journal_data = json.load(f)
else:
    journal_data = {}

# Quotes
MOTIVATION_QUOTES = [
    "🔥 Якщо не ти — то хто?",
    "💀 Дисципліна або смерть твоїм мріям.",
    "🧠 Перемагає не сильний, а впертий.",
    "🎯 Слабкість не дасть тобі мільйон.",
    "🔪 Дій щодня — або знову будеш без грошей."
]

ACHIEVEMENTS = []

# Save journal
def save_journal():
    with open(JOURNAL_FILE, "w", encoding="utf-8") as f:
        json.dump(journal_data, f, indent=2, ensure_ascii=False)

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != USER_ID:
        return
    keyboard = [[InlineKeyboardButton("📅 План", callback_data="show_plan")]]
    await update.message.reply_text("🔥 Yurii Discipline Bot V3.6 запущено. Натисни або /help", reply_markup=InlineKeyboardMarkup(keyboard))

# HELP
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "👋 *Вітаю в Yuri Discipline Bot V3.6*\n\n"
        "🔥 *Головні команди:*\n"
        "/start – Почати / перезапустити день\n"
        "/status – Статус дня: Strikes, Hellmode, Звіт\n"
        "/done – Надіслати звіт за день\n"
        "/plan 1 – Показати план на день (1-30)\n\n"
        "🎯 *Цілі:*\n"
        "/goal – Встановити ціль на тиждень\n"
        "/hellmode – Активувати Hellmode: збільшена складність\n\n"
        "📒 *Журнал:*\n"
        "/journal – Переглянути свої дні\n\n"
        "🧱 *Системні команди:*\n"
        "/begin – Записати початок завдання (/begin gym)\n"
        "/end – Завершити завдання і подивитися час (/end gym)\n"
        "/reset – Скинути все до Дня 1 (опціонально)\n\n"
        "❗ *Важливо:*\n"
        "– Якщо не надішлеш /done до вечора — буде STRIKE ❌\n"
        "– Якщо 3 STRIKE підряд — блокування на 1 день\n"
        "– Бот нагадує ціль щодня об 12:00\n"
        "– Hellmode автоматично додає складність після 5 днів\n"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

# HELL
async def hellmode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_state["hellmode"] = True
    await update.message.reply_text("💥 Hellmode активовано. Завтра буде жорстко!")

# STATUS
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.date.today().isoformat()
    result = journal_data.get(today, "❓ Не надіслано звіт")
    await update.message.reply_text(
        f"📅 День: {user_state['day']}, Strike: {user_state['strike']}/3\n"
        f"🔥 Hellmode: {'ON' if user_state['hellmode'] else 'OFF'}\n"
        f"✅ Стрік: {user_state['streak']}\n📘 Звіт: {result}"
    )

# JOURNAL
async def journal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    output = "\n".join(f"{date}: {entry}" for date, entry in sorted(journal_data.items())) or "Немає записів."
    await update.message.reply_text(f"📊 Журнал:\n{output}")

# GOAL
async def goal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_state['weekly_goal'] = "Подати 50 заявок"
    await update.message.reply_text("🎯 Ціль на тиждень встановлено: Подати 50 заявок")

# BUTTON
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "show_plan":
        tasks = full_plan.get(str(user_state["day"]), [])
        msg = f"📅 День {user_state['day']}:\n" + "\n".join(f"🔹 {task}" for task in tasks)
        await query.edit_message_text(msg)
    elif query.data == "journal_done":
        today = datetime.date.today().isoformat()
        journal_data[today] = "done"
        user_state['streak'] += 1
        user_state['strike'] = 0
        save_journal()
        if user_state['streak'] == 7:
            await query.edit_message_text("🏅 Досягнення: 7 днів поспіль!")
        else:
            await query.edit_message_text(f"✅ Звіт прийнято. Стрік: {user_state['streak']}")
    elif query.data == "journal_fail":
        today = datetime.date.today().isoformat()
        journal_data[today] = "fail"
        user_state['strike'] += 1
        user_state['streak'] = 0
        save_journal()
        msg = f"❌ Програв день. STRIKE {user_state['strike']}/3\n"
        if user_state['strike'] >= 3:
            msg += "🔴 Три провали поспіль. Ти втрачаєш $100."
        await query.edit_message_text(msg)

# TASK
async def send_daily_task(context: ContextTypes.DEFAULT_TYPE):
    hour = datetime.datetime.now().hour
    if hour > 10 and not user_state['confirmed']:
        await context.bot.send_message(USER_ID, "🔒 День заблоковано. Тільки завтра.")
        return
    user_state['confirmed'] = False
    tasks = full_plan.get(str(user_state['day']), [])
    if user_state['hellmode'] or user_state['day'] > 5:
        tasks += ["🔥 +1 TikTok", "⚙️ 2x IT-сесії"]
    msg = f"🌅 День {user_state['day']}:\n" + "\n".join(f"✅ {t}" for t in tasks)
    await context.bot.send_message(USER_ID, msg)

# REMINDER
async def reminder(context: ContextTypes.DEFAULT_TYPE):
    if not user_state['confirmed']:
        await context.bot.send_message(USER_ID, "🧠 Твоє майбутнє чекає. А ти чекаєш що?")

# AFTERNOON
async def afternoon_check(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(USER_ID, "⏳ Що ти вже зробив? Прогрес є?")

# JOURNAL ASK
async def ask_journal(context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("✅ Виконав", callback_data="journal_done")],
        [InlineKeyboardButton("❌ Не виконав", callback_data="journal_fail")]
    ]
    await context.bot.send_message(USER_ID, "📘 Звіт за день?", reply_markup=InlineKeyboardMarkup(keyboard))

# /done — підтвердження
async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_state['confirmed'] = True
    await update.message.reply_text("🟢 Почав день! Не зупиняйся.")

# /begin — почати завдання
async def begin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    task = " ".join(context.args) or "No description"
    start_time = datetime.datetime.now().isoformat()
    user_state['task_timer'][task] = start_time
    await update.message.reply_text(f"▶️ Почав: {task}")

# /end — завершити завдання
async def end_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    task = " ".join(context.args) or "No description"
    start_time = user_state['task_timer'].get(task)
    if not start_time:
        await update.message.reply_text("❌ Не знайдено старт для цього завдання.")
        return
    duration = datetime.datetime.now() - datetime.datetime.fromisoformat(start_time)
    await update.message.reply_text(f"✅ Завершено: {task} — {duration}")
    del user_state['task_timer'][task]

# SUMMARY
async def weekly_summary(context: ContextTypes.DEFAULT_TYPE):
    last_7 = list(journal_data.values())[-7:]
    done_days = last_7.count("done")
    await context.bot.send_message(USER_ID, f"📈 Тиждень: {done_days}/7 виконано")

# BOT RUN
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("journal", journal_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("hellmode", hellmode_command))
    app.add_handler(CommandHandler("goal", goal_command))
    app.add_handler(CommandHandler("done", done_command))
    app.add_handler(CommandHandler("begin", begin_command))
    app.add_handler(CommandHandler("end", end_command))
    app.add_handler(CallbackQueryHandler(button))

    tz = datetime.timezone(datetime.timedelta(hours=2))
    job_queue = app.job_queue
    job_queue.run_daily(send_daily_task, time=datetime.time(hour=8, tzinfo=tz))
    job_queue.run_daily(reminder, time=datetime.time(hour=12, tzinfo=tz))
    job_queue.run_daily(afternoon_check, time=datetime.time(hour=17, tzinfo=tz))
    job_queue.run_daily(ask_journal, time=datetime.time(hour=20, tzinfo=tz))
    job_queue.run_daily(weekly_summary, time=datetime.time(hour=21, tzinfo=tz), days=(6,))

    print("✅ Yurii Discipline Bot V3.6 Active")
    app.run_polling() 
