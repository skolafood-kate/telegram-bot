"""
Telegram-бот: тест из 7 вопросов по пищевому поведению.
Собирает имя и телефон пользователя, отправляет заявку администратору.
"""

import os
import html
import logging
from pathlib import Path
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_CHAT_ID = os.environ["ADMIN_CHAT_ID"]

(
    STATE_Q1, STATE_Q2, STATE_Q3, STATE_Q4,
    STATE_Q5, STATE_Q6, STATE_Q7,
    STATE_WAIT_NAME, STATE_WAIT_PHONE,
) = range(9)

QUESTIONS = [
    "Вопрос 1: Ты часто решаешь «начать новую жизнь с понедельника», но через несколько дней срываешься и возвращаешься к прежнему питанию?",
    "Вопрос 2: Тебе знакомо чувство вины за съеденную еду, даже если ты не объелась?",
    "Вопрос 3: Ты можешь есть не потому, что голодна, а потому что устала, скучаешь или испытываешь стресс?",
    "Вопрос 4: Ты пробовала несколько диет, но вес всегда возвращается, даже если сначала удавалось похудеть?",
    "Вопрос 5: Если у тебя был срыв, тебе кажется, что уже нет смысла продолжать, и ты начинаешь есть всё подряд?",
    "Вопрос 6: Ты мечтаешь просто нормально есть, не думая о калориях, но боишься, что без контроля быстро наберёшь вес?",
    "Вопрос 7: Ты замечала, что тебе сложно остановиться, если перед тобой что-то вкусное, даже если уже сыта?",
]

ANSWER_OPTIONS = [
    ("a) согласна", "a"),
    ("b) скорее согласна", "b"),
    ("c) затрудняюсь ответить", "c"),
    ("d) скорее не согласна", "d"),
    ("e) не согласна", "e"),
]

ANSWER_LABELS = {
    "a": "согласна", "b": "скорее согласна",
    "c": "затрудняюсь ответить", "d": "скорее не согласна", "e": "не согласна",
}

WELCOME_IMAGE = Path(__file__).parent / "welcome.png"
WELCOME_FILE_ID = "AgACAgIAAxkDAAMmadP0pGc2nIit7aK8eyfGpLF9mzIAAuEVaxtwAqFKD_vhCwm_0zoBAAMCAAN5AAM7BA"


def build_answer_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton(l, callback_data=v)] for l, v in ANSWER_OPTIONS])


async def send_question(update, context, question_index):
    text = QUESTIONS[question_index]
    keyboard = build_answer_keyboard()
    if update.callback_query:
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    else:
        await update.message.reply_text(text=text, reply_markup=keyboard)
    return question_index


async def start(update, context):
    context.user_data.clear()
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Начать тест", callback_data="start_test")]])
    caption = (
        "Привет! Меня зовут Екатерина Меньшикова - специалист по психологии питания и пищевого поведения.\n\n"
        "Пройди короткий тест из 7 вопросов и узнай, почему у тебя никак не получается похудеть, "
        "а также получи еще дополнительный бонус (см. кнопку \"начать тест\" внизу)\n\n"
        "Если у тебя не получается открыть тест, пиши мне кодовое слово ТЕСТ в личку  http://t.me/EkaterinaMenshikova и я тебе его пришлю"
    )
    photo = open(WELCOME_IMAGE, "rb") if WELCOME_IMAGE.exists() else WELCOME_FILE_ID
    if WELCOME_IMAGE.exists():
        with open(WELCOME_IMAGE, "rb") as f:
            await update.message.reply_photo(photo=f, caption=caption, reply_markup=keyboard)
    else:
        await update.message.reply_photo(photo=WELCOME_FILE_ID, caption=caption, reply_markup=keyboard)
    return STATE_Q1


async def begin_test(update, context):
    await update.callback_query.answer()
    context.user_data["answers"] = {}
    return await send_question(update, context, 0)


async def handle_answer(update, context):
    query = update.callback_query
    await query.answer()
    current_q_index = context.user_data.get("current_q", 0)
    context.user_data["answers"][f"Вопрос {current_q_index + 1}"] = ANSWER_LABELS.get(query.data, query.data)
    next_q_index = current_q_index + 1
    if next_q_index < len(QUESTIONS):
        context.user_data["current_q"] = next_q_index
        return await send_question(update, context, next_q_index)
    else:
        return await finish_test(update, context)


async def handle_answer_q(update, context, q_index):
    context.user_data["current_q"] = q_index
    return await handle_answer(update, context)


async def answer_q1(u, c): return await handle_answer_q(u, c, 0)
async def answer_q2(u, c): return await handle_answer_q(u, c, 1)
async def answer_q3(u, c): return await handle_answer_q(u, c, 2)
async def answer_q4(u, c): return await handle_answer_q(u, c, 3)
async def answer_q5(u, c): return await handle_answer_q(u, c, 4)
async def answer_q6(u, c): return await handle_answer_q(u, c, 5)
async def answer_q7(u, c): return await handle_answer_q(u, c, 6)


async def finish_test(update, context):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Получить результат теста", callback_data="get_result")]])
    await update.callback_query.edit_message_text(
        "Спасибо за ответы! На основе теста мы подготовили для вас персональные рекомендации и ещё один подарок.",
        reply_markup=keyboard,
    )
    return STATE_WAIT_NAME


async def ask_name(update, context):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("Как тебя зовут? Напиши своё имя:")
    return STATE_WAIT_NAME


async def receive_name(update, context):
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("Отлично! Теперь напиши свой номер телефона:")
    return STATE_WAIT_PHONE


async def receive_phone(update, context):
    context.user_data["phone"] = update.message.text.strip()
    await update.message.reply_text("Отлично! Мы свяжемся с вами в ближайшее время.")
    name = html.escape(context.user_data.get("name", "—"))
    phone = html.escape(context.user_data.get("phone", "—"))
    answers = context.user_data.get("answers", {})
    user = update.effective_user
    tg_line = f"🆔 Telegram: @{html.escape(user.username)}" if user.username else f"🆔 Telegram ID: {user.id}"
    lines = ["📋 <b>Новая заявка из теста</b>", "", f"👤 <b>Имя:</b> {name}", f"📞 <b>Телефон:</b> {phone}", tg_line, "", "<b>Ответы на вопросы:</b>"]
    for q, a in answers.items():
        lines.append(f"  {html.escape(q)}: {html.escape(a)}")
    try:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="\n".join(lines), parse_mode="HTML")
    except Exception as e:
        logger.error("Не удалось отправить заявку администратору: %s", e)
    return ConversationHandler.END


async def cancel(update, context):
    await update.message.reply_text("Тест отменён. Напиши /start, чтобы начать заново.")
    return ConversationHandler.END


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        per_message=False,
        states={
            STATE_Q1: [CallbackQueryHandler(begin_test, pattern="^start_test$"), CallbackQueryHandler(answer_q1, pattern="^(a|b|c|d|e)$")],
            STATE_Q2: [CallbackQueryHandler(answer_q2, pattern="^(a|b|c|d|e)$")],
            STATE_Q3: [CallbackQueryHandler(answer_q3, pattern="^(a|b|c|d|e)$")],
            STATE_Q4: [CallbackQueryHandler(answer_q4, pattern="^(a|b|c|d|e)$")],
            STATE_Q5: [CallbackQueryHandler(answer_q5, pattern="^(a|b|c|d|e)$")],
            STATE_Q6: [CallbackQueryHandler(answer_q6, pattern="^(a|b|c|d|e)$")],
            STATE_Q7: [CallbackQueryHandler(answer_q7, pattern="^(a|b|c|d|e)$")],
            STATE_WAIT_NAME: [CallbackQueryHandler(ask_name, pattern="^get_result$"), MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
            STATE_WAIT_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phone)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
    app.add_handler(conv_handler)
    logger.info("Бот запущен. Ожидание сообщений...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
