"""
STAN ARI Book Bot — final buttons version

ENV variables:
BOT_TOKEN=your_new_token
CHANNEL_USERNAME=@Stan_Ari
SITE_URL=https://stanari.art
GUMROAD_URL=https://staskit.gumroad.com/l/lpkwbc
DONATE_URL=https://send.monobank.ua/jar/AUje48FJ8f
ADMIN_ID=your_telegram_id
FIREBASE_SERVICE_ACCOUNT_JSON={...firebase service account json...}
"""

import os
import json
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

import firebase_admin
from firebase_admin import credentials, firestore


TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@Stan_Ari").strip()
SITE_URL = os.getenv("SITE_URL", "https://stanari.art").strip().rstrip("/")
GUMROAD_URL = os.getenv("GUMROAD_URL", "https://staskit.gumroad.com/l/lpkwbc").strip()
DONATE_URL = os.getenv("DONATE_URL", "https://send.monobank.ua/jar/AUje48FJ8f").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or "0")
CHANNEL_URL = "https://t.me/" + CHANNEL_USERNAME.lstrip("@")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is missing.")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")


def init_firebase():
    if firebase_admin._apps:
        return firestore.client()

    service_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    if service_json:
        cred = credentials.Certificate(json.loads(service_json))
    elif os.path.exists("serviceAccountKey.json"):
        cred = credentials.Certificate("serviceAccountKey.json")
    else:
        raise RuntimeError("Firebase credentials missing.")

    firebase_admin.initialize_app(cred)
    return firestore.client()


db = init_firebase()


def detect_source(message_text):
    parts = (message_text or "").split()
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


def is_subscribed(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False


def get_bot_user(user_id):
    snap = db.collection("botUsers").document(str(user_id)).get()
    return snap.to_dict() if snap.exists else None


def save_bot_user(user, source, promo_code=None):
    data = {
        "telegramUserId": user.id,
        "username": user.username or "",
        "firstName": user.first_name or "",
        "lastName": user.last_name or "",
        "source": source,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    }
    if promo_code:
        data["promoCode"] = promo_code
        data["codeIssuedAt"] = firestore.SERVER_TIMESTAMP

    db.collection("botUsers").document(str(user.id)).set(data, merge=True)


def find_free_code(source):
    query = (
        db.collection("promoCodes")
        .where("used", "==", False)
        .where("accessType", "==", "free_book")
        .where("source", "==", source)
        .limit(30)
    )

    for doc in query.stream():
        data = doc.to_dict() or {}
        if data.get("reserved") is True:
            continue
        return doc.id
    return None


def issue_code_for_user(user, source):
    existing = get_bot_user(user.id)
    if existing and existing.get("promoCode"):
        return existing["promoCode"], False

    code_id = find_free_code(source)
    if not code_id and source != "telegram":
        code_id = find_free_code("telegram")
        source = "telegram"

    if not code_id:
        return None, False

    code_ref = db.collection("promoCodes").document(code_id)
    user_ref = db.collection("botUsers").document(str(user.id))

    @firestore.transactional
    def reserve(transaction):
        snap = code_ref.get(transaction=transaction)
        if not snap.exists:
            return None

        data = snap.to_dict() or {}
        if data.get("used") is True or data.get("reserved") is True:
            return None

        transaction.update(code_ref, {
            "reserved": True,
            "reservedByTelegramId": user.id,
            "reservedByUsername": user.username or "",
            "reservedAt": firestore.SERVER_TIMESTAMP,
        })

        transaction.set(user_ref, {
            "telegramUserId": user.id,
            "username": user.username or "",
            "firstName": user.first_name or "",
            "lastName": user.last_name or "",
            "source": source,
            "promoCode": code_id,
            "codeIssuedAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        }, merge=True)

        return code_id

    transaction = db.transaction()
    reserved_code = reserve(transaction)
    return reserved_code, True


def subscribe_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📢 Підписатися на канал", url=CHANNEL_URL))
    kb.add(InlineKeyboardButton("✅ Перевірити підписку", callback_data="check_sub"))
    return kb


def main_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🎁 Отримати код доступу", callback_data="get_code"))
    kb.add(InlineKeyboardButton("📖 Купити книгу", url=GUMROAD_URL))
    kb.add(InlineKeyboardButton("💛 Донат Monobank", url=DONATE_URL))
    kb.add(InlineKeyboardButton("🌐 Сайт автора", url=SITE_URL))
    kb.add(InlineKeyboardButton("📢 Telegram канал", url=CHANNEL_URL))
    return kb


def code_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🌐 Ввести код на сайті", url=SITE_URL))
    kb.add(InlineKeyboardButton("📖 Читати книгу", url=SITE_URL + "/reader.html"))
    kb.add(InlineKeyboardButton("📖 Купити книгу", url=GUMROAD_URL))
    kb.add(InlineKeyboardButton("💛 Донат Monobank", url=DONATE_URL))
    kb.add(InlineKeyboardButton("📢 Telegram канал", url=CHANNEL_URL))
    return kb


def send_welcome(chat_id, first_name=""):
    name = ", " + first_name if first_name else ""
    bot.send_message(
        chat_id,
        "Привіт" + name + "! 👋\n\n"
        "<b>STAN ARI — The Life Operator</b>\n\n"
        "Тут ти можеш отримати персональний код доступу до онлайн-читання книги.\n\n"
        "Також можеш купити повну книгу або підтримати фонд Aria.",
        reply_markup=main_keyboard(),
    )


def send_not_subscribed(chat_id):
    bot.send_message(
        chat_id,
        "❌ <b>Схоже, ти ще не підписався</b>\n\n"
        "Підпишись на Telegram канал і натисни «Перевірити підписку».",
        reply_markup=subscribe_keyboard(),
    )


def send_code(chat_id, user, source):
    code, is_new = issue_code_for_user(user, source)

    if not code:
        bot.send_message(
            chat_id,
            "⚠️ Зараз немає вільних кодів для видачі. "
            "Спробуй пізніше або напиши автору.",
            reply_markup=main_keyboard(),
        )
        return

    save_bot_user(user, source, code)

    bot.send_message(
        chat_id,
        "✅ <b>Твій код доступу готовий</b>\n\n"
        "🔑 Код: <code>" + code + "</code>\n\n"
        "Що робити далі:\n"
        "1. Перейди на сайт\n"
        "2. Натисни «Читати книгу»\n"
        "3. Увійди через Google\n"
        "4. Введи код\n\n"
        "🐾 33% прибутку йде у фонд Aria та майбутній притулок для тварин.",
        reply_markup=code_keyboard(),
    )


user_sources = {}


@bot.message_handler(commands=["start"])
def start(message):
    source = detect_source(message.text)
    user_sources[message.from_user.id] = source
    save_bot_user(message.from_user, source)
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
def my_code(message):
    existing = get_bot_user(message.from_user.id)
    if existing and existing.get("promoCode"):
        bot.send_message(
            message.chat.id,
            "🔑 Твій код: <code>" + existing["promoCode"] + "</code>",
            reply_markup=code_keyboard(),
        )
    else:
        bot.send_message(message.chat.id, "У тебе ще немає коду. Натисни /start")


@bot.message_handler(commands=["stats"])
def stats(message):
    if not ADMIN_ID or message.from_user.id != ADMIN_ID:
        return

    users = list(db.collection("botUsers").stream())
    total = len(users)
    with_code = 0
    sources = {}

    for snap in users:
        data = snap.to_dict() or {}
        src = data.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1
        if data.get("promoCode"):
            with_code += 1

    source_text = "\n".join([str(k) + ": " + str(v) for k, v in sources.items()]) or "—"

    bot.send_message(
        message.chat.id,
        "📊 <b>Статистика</b>\n\n"
        "👥 Користувачів: <b>" + str(total) + "</b>\n"
        "🔑 Отримали код: <b>" + str(with_code) + "</b>\n\n"
        "Джерела:\n" + source_text
    )


@bot.message_handler(func=lambda m: True)
def fallback(message):
    send_welcome(message.chat.id, message.from_user.first_name or "")


if __name__ == "__main__":
    print("🤖 STAN ARI Bot started")
    bot.infinity_polling(skip_pending=True)
