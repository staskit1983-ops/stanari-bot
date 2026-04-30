"""
STAN ARI Book Bot — READY DROP-IN VERSION
Просто замінити файли в GitHub і запустити.

Що вміє:
- перевіряє підписку на Telegram канал
- видає унікальний промокод із локального списку
- кнопки: сайт, купити книгу, донат, канал
"""

import telebot
import json
import os
from datetime import datetime

TOKEN = "8653793852:AAGN_tdPSU-JTg6AV6rCrkfUeLm9vEcHS5s"

CHANNEL_USERNAME = "@Stan_Ari"
CHANNEL_URL = "https://t.me/Stan_Ari"

SITE_URL = "https://stanari.art"
READER_URL = "https://stanari.art/reader.html"
BUY_URL = "https://staskit.gumroad.com/l/lpkwbc"
DONATE_URL = "https://send.monobank.ua/jar/AUje48FJ8f"

STATS_FILE = "bot_stats.json"

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")


def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    return {
        "users": {},
        "issued": {
            "tiktok": 0,
            "youtube": 0,
            "telegram": 0
        }
    }


def save_stats(stats):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def detect_source(text):
    parts = (text or "").split()
    if len(parts) < 2:
        return "telegram"

    p = parts[1].lower()

    if "tik" in p or "tt" in p:
        return "tiktok"
    if "you" in p or "yt" in p:
        return "youtube"
    if "tg" in p or "tele" in p:
        return "telegram"

    return "telegram"


def make_code(source, number):
    if source == "tiktok":
        return f"tt{number:04d}"
    if source == "youtube":
        return f"yt{number:04d}"
    return f"tg{number:04d}"


def is_subscribed(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False


def get_or_issue_code(user, source):
    stats = load_stats()
    uid = str(user.id)

    if uid in stats["users"] and stats["users"][uid].get("code"):
        return stats["users"][uid]["code"]

    stats["issued"][source] = stats["issued"].get(source, 0) + 1
    number = stats["issued"][source]
    code = make_code(source, number)

    stats["users"][uid] = {
        "telegram_id": user.id,
        "username": user.username or "",
        "first_name": user.first_name or "",
        "source": source,
        "code": code,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    save_stats(stats)
    return code


def main_keyboard():
    kb = telebot.types.InlineKeyboardMarkup()
    kb.row(telebot.types.InlineKeyboardButton("🎁 Отримати код доступу", callback_data="get_code"))
    kb.row(telebot.types.InlineKeyboardButton("📖 Купити книгу", url=BUY_URL))
    kb.row(telebot.types.InlineKeyboardButton("💛 Донат Monobank", url=DONATE_URL))
    kb.row(
        telebot.types.InlineKeyboardButton("🌐 Сайт автора", url=SITE_URL),
        telebot.types.InlineKeyboardButton("📢 Telegram канал", url=CHANNEL_URL)
    )
    return kb


def subscribe_keyboard():
    kb = telebot.types.InlineKeyboardMarkup()
    kb.row(telebot.types.InlineKeyboardButton("📢 Підписатися на канал", url=CHANNEL_URL))
    kb.row(telebot.types.InlineKeyboardButton("✅ Перевірити підписку", callback_data="check_sub"))
    return kb


def code_keyboard():
    kb = telebot.types.InlineKeyboardMarkup()
    kb.row(telebot.types.InlineKeyboardButton("🌐 Ввести код на сайті", url=SITE_URL))
    kb.row(telebot.types.InlineKeyboardButton("📖 Читати книгу", url=READER_URL))
    kb.row(telebot.types.InlineKeyboardButton("📖 Купити книгу", url=BUY_URL))
    kb.row(telebot.types.InlineKeyboardButton("💛 Донат Monobank", url=DONATE_URL))
    kb.row(telebot.types.InlineKeyboardButton("📢 Telegram канал", url=CHANNEL_URL))
    return kb


def send_welcome(chat_id, name=""):
    hello = f"Привіт, {name}! 👋\n\n" if name else "Привіт! 👋\n\n"

    bot.send_message(
        chat_id,
        hello +
        "<b>STAN ARI — The Life Operator</b>\n\n"
        "Тут ти можеш отримати персональний код доступу до онлайн-читання книги.\n\n"
        "Також можеш купити повну книгу або підтримати фонд Aria.",
        reply_markup=main_keyboard()
    )


def send_not_subscribed(chat_id):
    bot.send_message(
        chat_id,
        "❌ <b>Схоже, ти ще не підписався</b>\n\n"
        "Підпишись на Telegram канал і натисни «Перевірити підписку».",
        reply_markup=subscribe_keyboard()
    )


def send_code(chat_id, user, source):
    code = get_or_issue_code(user, source)

    bot.send_message(
        chat_id,
        "✅ <b>Твій код доступу готовий</b>\n\n"
        f"🔑 Код: <code>{code}</code>\n\n"
        "Що робити далі:\n"
        "1. Перейди на сайт\n"
        "2. Натисни «Читати книгу»\n"
        "3. Увійди через Google\n"
        "4. Введи код\n\n"
        "🐾 33% прибутку йде у фонд Aria та майбутній притулок для тварин.",
        reply_markup=code_keyboard()
    )


user_sources = {}


@bot.message_handler(commands=["start"])
def start(message):
    source = detect_source(message.text)
    user_sources[message.from_user.id] = source
    send_welcome(message.chat.id, message.from_user.first_name or "")


@bot.callback_query_handler(func=lambda call: call.data == "get_code")
def get_code(call):
    uid = call.from_user.id
    source = user_sources.get(uid, "telegram")

    if not is_subscribed(uid):
        bot.answer_callback_query(call.id, "Спочатку підпишись на канал", show_alert=True)
        send_not_subscribed(call.message.chat.id)
        return

    bot.answer_callback_query(call.id)
    send_code(call.message.chat.id, call.from_user, source)


@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub(call):
    uid = call.from_user.id
    source = user_sources.get(uid, "telegram")

    if not is_subscribed(uid):
        bot.answer_callback_query(call.id, "Підписку ще не знайдено", show_alert=True)
        return

    bot.answer_callback_query(call.id, "Підписка підтверджена ✅")
    send_code(call.message.chat.id, call.from_user, source)


@bot.message_handler(commands=["mycode"])
def mycode(message):
    stats = load_stats()
    uid = str(message.from_user.id)

    if uid in stats["users"] and stats["users"][uid].get("code"):
        code = stats["users"][uid]["code"]
        bot.send_message(
            message.chat.id,
            f"🔑 Твій код: <code>{code}</code>",
            reply_markup=code_keyboard()
        )
    else:
        bot.send_message(message.chat.id, "У тебе ще немає коду. Натисни /start")


@bot.message_handler(commands=["stats"])
def stats(message):
    stats = load_stats()
    total_users = len(stats.get("users", {}))
    issued = stats.get("issued", {})

    bot.send_message(
        message.chat.id,
        "📊 <b>Статистика</b>\n\n"
        f"👥 Користувачів: <b>{total_users}</b>\n"
        f"TikTok: {issued.get('tiktok', 0)}\n"
        f"YouTube: {issued.get('youtube', 0)}\n"
        f"Telegram: {issued.get('telegram', 0)}"
    )


@bot.message_handler(func=lambda m: True)
def fallback(message):
    send_welcome(message.chat.id, message.from_user.first_name or "")


if __name__ == "__main__":
    print("🤖 STAN ARI Book Bot started")
    bot.infinity_polling(skip_pending=True)
