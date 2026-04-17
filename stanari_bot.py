"""
STAN ARI Book Bot — @stanari_book_bot
Автоматична видача книги після підписки на канал/групу

Встановлення:
  pip install pyTelegramBotAPI

Запуск:
  python stanari_bot.py

Для постійної роботи (безкоштовно):
  https://railway.app або https://render.com
"""

import telebot
import json
import os
from datetime import datetime

# ══════════════════════════════════════
# НАЛАШТУВАННЯ — змінюй тільки тут
# ══════════════════════════════════════

TOKEN = "8653793852:AAGN_tdPSU-JTg6AV6rCrkfUeLm9vEcHS5s"

# ID або @username твоєї групи/каналу де лежить книга
# Після того як зробиш групу публічною — встав сюди @username
GROUP_USERNAME = "@stanari_book_ua"

# Посилання на повідомлення з книгою в групі
# Формат: https://t.me/stanari_book_ua/2
BOOK_LINK_UA = "https://t.me/stanari_book_ua/2"
BOOK_LINK_PL = None  # Польська ще не готова

# Промокоди
PROMO_CODES = {
    "TIKTOK":   "TikTok",
    "YOUTUBE":  "YouTube",
    "STAN":     "Universal",
    "STANARI":  "Universal",
    "FREE":     "Universal",
}

# Файл для статистики
STATS_FILE = "stats.json"

# ══════════════════════════════════════

bot = telebot.TeleBot(TOKEN)

# Завантаження статистики
def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            return json.load(f)
    return {"users": {}, "total": 0, "sources": {}}

def save_stats(stats):
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

def log_user(user_id, source, username=""):
    stats = load_stats()
    uid = str(user_id)
    if uid not in stats["users"]:
        stats["users"][uid] = {
            "username": username,
            "source": source,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "got_book": False
        }
        stats["total"] += 1
        stats["sources"][source] = stats["sources"].get(source, 0) + 1
    save_stats(stats)

def mark_got_book(user_id):
    stats = load_stats()
    uid = str(user_id)
    if uid in stats["users"]:
        stats["users"][uid]["got_book"] = True
    save_stats(stats)

# ══════════════════════════════════════
# ГОЛОВНЕ МЕНЮ
# ══════════════════════════════════════

def send_main_menu(chat_id, name=""):
    greeting = f"Привіт, {name}! 👋\n\n" if name else "Привіт! 👋\n\n"
    text = (
        greeting +
        "✨ *STAN ARI — Creator of Inner Worlds*\n\n"
        "Я допоможу тобі отримати книгу *The Life Operator* безкоштовно.\n\n"
        "Обери що тебе цікавить:"
    )
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(
        telebot.types.InlineKeyboardButton("🎁 Отримати книгу", callback_data="get_book")
    )
    keyboard.row(
        telebot.types.InlineKeyboardButton("🔑 Ввести промокод", callback_data="enter_promo")
    )
    keyboard.row(
        telebot.types.InlineKeyboardButton("📖 Про книгу", callback_data="about_book"),
        telebot.types.InlineKeyboardButton("🌐 Сайт", url="https://stanari.tiiny.site")
    )
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=keyboard)


@bot.message_handler(commands=["start"])
def start(message):
    user = message.from_user
    name = user.first_name or ""

    # Перевіряємо параметр (звідки прийшов)
    args = message.text.split()
    source = "direct"
    if len(args) > 1:
        param = args[1].lower()
        if "tiktok" in param:
            source = "TikTok"
        elif "youtube" in param or "yt" in param:
            source = "YouTube"
        elif "site" in param:
            source = "Website"

    log_user(user.id, source, user.username or "")
    send_main_menu(message.chat.id, name)


@bot.message_handler(commands=["stats"])
def stats_command(message):
    # Тільки для тебе — вставши свій Telegram ID
    ADMIN_ID = None  # ЗАМІНИ на свій числовий ID
    if ADMIN_ID and message.from_user.id != ADMIN_ID:
        return

    stats = load_stats()
    sources = stats.get("sources", {})
    src_text = "\n".join([f"  {k}: {v}" for k, v in sources.items()]) or "  —"

    text = (
        f"📊 *Статистика бота*\n\n"
        f"👥 Всього користувачів: *{stats['total']}*\n\n"
        f"📣 За джерелами:\n{src_text}\n\n"
        f"📚 Отримали книгу: *{sum(1 for u in stats['users'].values() if u.get('got_book'))}*"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")


# ══════════════════════════════════════
# ПРОМОКОД через повідомлення
# ══════════════════════════════════════

user_states = {}  # зберігаємо стан (чекаємо промокод)

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid = message.from_user.id
    text = message.text.strip().upper()

    if user_states.get(uid) == "waiting_promo":
        if text in PROMO_CODES:
            user_states.pop(uid, None)
            source = PROMO_CODES[text]
            log_user(uid, source, message.from_user.username or "")
            send_book(message.chat.id, uid)
        else:
            bot.send_message(
                message.chat.id,
                "❌ Невірний код. Спробуй ще раз або напиши /start",
            )
    else:
        send_main_menu(message.chat.id, message.from_user.first_name or "")


# ══════════════════════════════════════
# CALLBACK КНОПКИ
# ══════════════════════════════════════

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    uid = call.from_user.id
    cid = call.message.chat.id

    if call.data == "get_book":
        # Пропонуємо підписатись і отримати книгу
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.row(
            telebot.types.InlineKeyboardButton(
                "✅ Я підписався — дай книгу!",
                callback_data="check_sub"
            )
        )
        keyboard.row(
            telebot.types.InlineKeyboardButton("🔑 Маю промокод", callback_data="enter_promo")
        )
        bot.edit_message_text(
            "📚 *Отримай Том 1 безкоштовно*\n\n"
            "1️⃣ Підпишись на наш Telegram канал\n"
            "2️⃣ Натисни кнопку нижче і отримай книгу миттєво\n\n"
            f"👉 {GROUP_USERNAME}",
            cid, call.message.message_id,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    elif call.data == "check_sub":
        # Перевіряємо підписку
        try:
            member = bot.get_chat_member(GROUP_USERNAME, uid)
            if member.status in ["member", "administrator", "creator"]:
                send_book(cid, uid)
            else:
                raise Exception("not member")
        except:
            keyboard = telebot.types.InlineKeyboardMarkup()
            keyboard.row(
                telebot.types.InlineKeyboardButton(
                    "📢 Підписатись на канал",
                    url=f"https://t.me/{GROUP_USERNAME.lstrip('@')}"
                )
            )
            keyboard.row(
                telebot.types.InlineKeyboardButton(
                    "✅ Перевірити ще раз",
                    callback_data="check_sub"
                )
            )
            bot.answer_callback_query(call.id, "❌ Підписка не знайдена", show_alert=True)
            bot.edit_message_text(
                "❌ *Схоже ти ще не підписався*\n\n"
                "Підпишись на канал і натисни «Перевірити ще раз»",
                cid, call.message.message_id,
                parse_mode="Markdown",
                reply_markup=keyboard
            )

    elif call.data == "enter_promo":
        user_states[uid] = "waiting_promo"
        bot.edit_message_text(
            "🔑 *Введи промокод*\n\n"
            "Коди можна знайти в:\n"
            "• Описі відео на TikTok\n"
            "• Описі відео на YouTube\n"
            "• Telegram каналі\n\n"
            "Просто напиши код у чат 👇",
            cid, call.message.message_id,
            parse_mode="Markdown"
        )

    elif call.data == "about_book":
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.row(
            telebot.types.InlineKeyboardButton("🎁 Отримати безкоштовно", callback_data="get_book")
        )
        keyboard.row(
            telebot.types.InlineKeyboardButton("🌐 Сайт автора", url="https://stanari.tiiny.site")
        )
        bot.edit_message_text(
            "📖 *The Life Operator — Том 1*\n"
            "_Rewrite Your Inner Code_\n\n"
            "Книга про те, що людина бачить результат — але не бачить, що його створює.\n\n"
            "• Внутрішній код і переконання\n"
            "• Пам'ять поколінь і рід\n"
            "• Свідомість і трансформація\n\n"
            "✍️ Автор: *STAN ARI*\n"
            "🌍 Мови: Українська • Polski\n"
            "📦 Формат: PDF\n\n"
            "33% прибутку → Фонд Aria 🐾",
            cid, call.message.message_id,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    bot.answer_callback_query(call.id)


# ══════════════════════════════════════
# ВИДАЧА КНИГИ
# ══════════════════════════════════════

def send_book(chat_id, user_id):
    mark_got_book(user_id)

    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(
        telebot.types.InlineKeyboardButton("📖 UA — Читати", url=BOOK_LINK_UA)
    )
    if BOOK_LINK_PL:
        keyboard.row(
            telebot.types.InlineKeyboardButton("📖 PL — Czytaj", url=BOOK_LINK_PL)
        )
    keyboard.row(
        telebot.types.InlineKeyboardButton("🌐 Сайт автора", url="https://stanari.tiiny.site"),
        telebot.types.InlineKeyboardButton("📢 Канал", url="https://t.me/STAN_ARI")
    )

    bot.send_message(
        chat_id,
        "✅ *Книга твоя!*\n\n"
        "📚 *The Life Operator — Том 1*\n\n"
        "Обери мову і починай читати прямо зараз 👇\n\n"
        "🐾 Пам'ятай: 33% прибутку йде на фонд Aria і притулок для тварин.\n"
        "Дякуємо що ти частина цього!",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


# ══════════════════════════════════════
# ЗАПУСК
# ══════════════════════════════════════

if __name__ == "__main__":
    print("🤖 STAN ARI Bot запущено...")
    print(f"📱 t.me/stanari_book_bot")
    bot.infinity_polling(skip_pending=True)
