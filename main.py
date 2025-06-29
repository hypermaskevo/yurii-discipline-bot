# yurii_discipline_bot_v3.6.py
# ➕ /help, /done, /reset, /plan

import json, os, datetime, asyncio, random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
USER_ID = int(os.getenv("USER_ID"))

with open("yurii_discipline_plan_30days.json", "r", encoding="utf-8") as f:
    full_plan = json.load(f)

user_state = {"day": 1, "hellmode": False, "confirmed": False}
JOURNAL_FILE = "journal.json"
if os.path.exists(JOURNAL_FILE):
    with open(JOURNAL_FILE, "r", encoding="utf-8") as f:
        journal_data = json.load(f)
else:
    journal_data = {}

MOTIVATION_QUOTES = [
    "🔥 Якщо не ти — то хто?",
    "💀 Дисципліна або смерть твоїм мріям.",
    "🧠 Перемагає не сильний, а впертий.",
    "🎯 Слабкість не дасть тобі мільйон.",
    "🔪 Дій щодня — або знову будеш без грошей."
]

def save_journal():
    with open(JOURNAL_FILE, "w", encoding="utf-8") as f:
        json.dump(journal_data, f, indent=2, ensure_ascii=False)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != USER_ID:
        return
    keyboard = [[InlineKeyboardButton("📅 Показати план", callback_data="show_plan")]]
    await update.message.reply_text("👋 Готовий до прориву? Натисни кнопку або /hellmode.", reply_markup=InlineKeyboardMarkup(keyboard))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != USER_ID:
        return
    await update.message.reply_text(
        "/start — активувати бота\n"
        "/done — підтвердити виконання\n"
        "/status — переглянути статус\n"
        "/reset — почати знову з дня 1\n"
        "/plan номер — переглянути завдання на вказаний день\n"
        "/help — ця довідка"
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "show_plan":
        day = user_state["day"]
        tasks = full_plan.get(str(day), ["Немає плану"])
        mode = "HELLMODE" if user_state["hellmode"] else "Нормальний режим"
        await query.edit_message_text(f"📅 День {day} ({mode}):\n" + "\n".join(f"🔹 {t}" for t in tasks))
    elif query.data.startswith("journal_"):
        result = query.data.split("_")[1]
        today = datetime.date.today().isoformat()
        journal_data[today] = result
        save_journal()
        await query.edit_message_text(f"📘 Звіт за {today}: {result}\n{random.choice(MOTIVATION_QUOTES)}")

async def send_daily_task(context: ContextTypes.DEFAULT_TYPE):
    day = user_state["day"]
    tasks = full_plan.get(str(day), [])
    if user_state["hellmode"]:
        tasks += ["⚠️ Подвійне відео TikTok", "⚠️ 2x фокус-сесії"]
    msg = f"🌅 День {day}. Завдання:\n" + "\n".join(f"✅ {t}" for t in tasks)
    msg += f"\n\n{random.choice(MOTIVATION_QUOTES)}"
    await context.bot.send_message(chat_id=USER_ID, text=msg)
    user_state["confirmed"] = False

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    if not user_state["confirmed"]:
        await context.bot.send_message(chat_id=USER_ID, text="🔔 Ти ще не почав день. Не злий себе.")

async def send_afternoon_check(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=USER_ID, text="⏳ Як просувається день?")

async def ask_for_journal(context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("✅ Виконав", callback_data="journal_done")],
        [InlineKeyboardButton("❌ Не виконав", callback_data="journal_fail")]
    ]
    await context.bot.send_message(chat_id=USER_ID, text="📘 Що з сьогоднішнім днем?", reply_markup=InlineKeyboardMarkup(keyboard))

async def journal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != USER_ID:
        return
    output = "\n".join(f"{date}: {entry}" for date, entry in sorted(journal_data.items())) or "Немає записів."
    await update.message.reply_text(f"📊 Журнал виконання:\n{output}")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != USER_ID:
        return
    day = user_state["day"]
    hell = "ON" if user_state["hellmode"] else "OFF"
    today = datetime.date.today().isoformat()
    result = journal_data.get(today, "❓ Ще не відповідав")
    await update.message.reply_text(f"📅 День: {day}\n🔥 Hellmode: {hell}\n📘 Звіт: {result}")

async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != USER_ID:
        return
    user_state["confirmed"] = True
    user_state["day"] += 1
    await update.message.reply_text("✅ День підтверджено! Рухаємось далі.")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != USER_ID:
        return
    user_state["day"] = 1
    user_state["hellmode"] = False
    await update.message.reply_text("🔁 Скинуто до Дня 1.")

async def plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != USER_ID:
        return
    if len(context.args) != 1 or not context.args[0].isdigit():
        await update.message.reply_text("Введи номер дня: /plan 1")
        return
    day = int(context.args[0])
    tasks = full_plan.get(str(day), ["Немає завдань"])
    await update.message.reply_text(f"📅 План на день {day}:\n" + "\n".join(f"🔹 {t}" for t in tasks))

async def hellmode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_state["hellmode"] = True
    await update.message.reply_text("💥 Hellmode активовано. Завтра — жорсткий день!")

async def weekly_summary(context: ContextTypes.DEFAULT_TYPE):
    past_7 = list(sorted(journal_data.items()))[-7:]
    total = len([1 for d in past_7 if "done" in d[1]])
    await context.bot.send_message(chat_id=USER_ID, text=f"📊 Звіт за тиждень:\n✅ {total}/7 виконано\n❌ {7 - total} прогулів")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("journal", journal_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("done", done_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("plan", plan_command))
    app.add_handler(CommandHandler("hellmode", hellmode_command))
    app.add_handler(CallbackQueryHandler(button))

    job_queue = app.job_queue
    berlin_tz = datetime.timezone(datetime.timedelta(hours=2))
    job_queue.run_daily(send_daily_task, time=datetime.time(hour=8, tzinfo=berlin_tz))
    job_queue.run_daily(send_reminder, time=datetime.time(hour=12, tzinfo=berlin_tz))
    job_queue.run_daily(send_afternoon_check, time=datetime.time(hour=17, tzinfo=berlin_tz))
    job_queue.run_daily(ask_for_journal, time=datetime.time(hour=20, tzinfo=berlin_tz))
    job_queue.run_daily(weekly_summary, time=datetime.time(hour=20, tzinfo=berlin_tz), days=(6,))

    print("✅ Yurii Discipline Bot V3.6 запущено")
    app.run_polling()
