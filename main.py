import json
import os
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, ContextTypes,
    CommandHandler, MessageHandler, filters, JobQueue, CallbackQueryHandler
)
from dotenv import load_dotenv

# --- Конфігурація ---
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
USER_ID = int(os.getenv("USER_ID"))

# --- Завантаження плану ---
with open("yurii_discipline_plan_30days.json", "r", encoding="utf-8") as f:
    full_plan = json.load(f)

# --- Стан користувача ---
user_state = {
    "day": 1,
    "confirmed": False
}

# --- Статистика ---
LOG_FILE = "yurii_progress_log.json"

if os.path.exists(LOG_FILE):
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        progress_log = json.load(f)
else:
    progress_log = []

# --- Часова зона для Німеччини ---
TZ = datetime.timezone(datetime.timedelta(hours=2))

# --- Відправлення щоденного завдання ---
async def send_daily_task(context: ContextTypes.DEFAULT_TYPE):
    day = user_state["day"]
    if str(day) not in full_plan:
        await context.bot.send_message(chat_id=USER_ID, text="✅ План завершено!")
        return

    task = full_plan[str(day)]
    message = f"\U0001F680 День {day}:\n\n"
    for block, item in task.items():
        message += f"\u2728 *{block}*: {item}\n"
    message += "\nНатисни кнопку, коли виконаєш завдання."

    keyboard = [[InlineKeyboardButton("✅ Виконано", callback_data="confirm_done")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(chat_id=USER_ID, text=message, parse_mode="Markdown", reply_markup=reply_markup)
    user_state["confirmed"] = False

# --- Підтвердження виконання (кнопка або команда) ---
async def confirm_done_action(context):
    user_state["confirmed"] = True
    user_state["day"] += 1

    log_entry = {
        "date": datetime.datetime.now(tz=TZ).strftime("%Y-%m-%d %H:%M"),
        "day": user_state["day"] - 1,
        "status": "✅ Виконано"
    }
    progress_log.append(log_entry)

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(progress_log, f, indent=2, ensure_ascii=False)

# --- Команда /done ---
async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if user_state["confirmed"]:
        await update.message.reply_text("Вже підтверджено ✅")
    else:
        await confirm_done_action(context)
        await update.message.reply_text("Добре, рухаємось далі! \U0001F4AA")

# --- Обробка кнопки ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "confirm_done":
        if user_state["confirmed"]:
            await query.edit_message_text("Вже підтверджено ✅")
        else:
            await confirm_done_action(context)
            await query.edit_message_text("Добре, рухаємось далі! \U0001F4AA")

# --- Штрафи, якщо не підтверджено ---
async def penalty_reminder(context: ContextTypes.DEFAULT_TYPE):
    if not user_state["confirmed"]:
        await context.bot.send_message(
            chat_id=USER_ID,
            text="\u274C Завдання не виконано. Уяви: день без інтернету, грошей чи їжі. Не допускай цього завтра."
        )
        log_entry = {
            "date": datetime.datetime.now(tz=TZ).strftime("%Y-%m-%d %H:%M"),
            "day": user_state["day"],
            "status": "❌ Пропущено"
        }
        progress_log.append(log_entry)
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(progress_log, f, indent=2, ensure_ascii=False)

# --- Щотижневий звіт ---
async def weekly_report(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now(tz=TZ)
    week_ago = now - datetime.timedelta(days=7)
    recent = [entry for entry in progress_log if datetime.datetime.strptime(entry["date"], "%Y-%m-%d %H:%M") >= week_ago]
    if not recent:
        msg = "За останній тиждень не було активності."
    else:
        msg = "📊 Звіт за останні 7 днів:\n"
        for e in recent:
            msg += f"{e['date']}: День {e['day']} — {e['status']}\n"
    await context.bot.send_message(chat_id=USER_ID, text=msg)

# --- Команда /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот активний. Завтра о 08:00 отримаєш завдання.")

# --- Команда /status ---
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    day = user_state["day"]
    confirmed = user_state["confirmed"]
    msg = f"\U0001F4CA Сьогодні день: {day}\n"
    msg += "\u2705 Виконано" if confirmed else "\u274C Не підтверджено"
    await update.message.reply_text(msg)

# --- Команда /reset ---
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_state["day"] = 1
    user_state["confirmed"] = False
    await update.message.reply_text("⏮ Починаємо знову з Дня 1")

# --- Команда /help ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "\U0001F4D6 *Yurii Discipline Bot – Допомога*\n\n"
        "/start – активувати бота\n"
        "/done – підтвердити виконання\n"
        "/status – переглянути поточний день та статус\n"
        "/reset – почати знову з дня 1\n"
        "/plan [номер] – переглянути завдання на вказаний день (або сьогодні)\n"
        "/help – ця довідка\n\n"
        "Щоранку о 08:00 ти отримуєш завдання. Якщо не підтвердиш – ввечері буде нагадування-шарлатан!"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# --- Команда /plan ---
async def plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if args and args[0].isdigit():
        day = int(args[0])
    else:
        day = user_state["day"]

    if str(day) not in full_plan:
        await update.message.reply_text("План на цей день не знайдено.")
        return

    task = full_plan[str(day)]
    message = f"\U0001F4DD План на день {day}:\n\n"
    for block, item in task.items():
        message += f"\u2728 *{block}*: {item}\n"
    await update.message.reply_text(message, parse_mode="Markdown")

# --- Запуск ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("plan", plan))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.job_queue.run_daily(send_daily_task, time=datetime.time(hour=8, tzinfo=TZ))
    app.job_queue.run_daily(penalty_reminder, time=datetime.time(hour=20, tzinfo=TZ))
    app.job_queue.run_daily(weekly_report, time=datetime.time(hour=21, minute=0, tzinfo=TZ), days=(6,))  # Sunday

    print("\u2705 Yurii Discipline Bot V3.3 запущено")
    app.run_polling()
