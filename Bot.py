import os
import json
import time
import random
import sqlite3
import urllib.request
import urllib.parse
from datetime import date

TOKEN = os.environ.get("BOT_TOKEN", "").strip()

if not TOKEN:
    print("XATO: BOT_TOKEN maxfiy sozlamasini kiriting!")
    raise SystemExit

API = f"https://api.telegram.org/bot{TOKEN}/"
DB = sqlite3.connect("asliddin_coin.db")
DB.row_factory = sqlite3.Row

DB.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT,
    coins INTEGER DEFAULT 0,
    vip INTEGER DEFAULT 0,
    tap_day TEXT DEFAULT '',
    taps INTEGER DEFAULT 0,
    bonus_day TEXT DEFAULT ''
)
""")

DB.commit()


def request(method, data=None):
    body = urllib.parse.urlencode(
        data or {}
    ).encode()

    req = urllib.request.Request(
        API + method,
        data=body
    )

    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode())


def send(chat_id, text, keyboard=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        data["reply_markup"] = json.dumps({
            "inline_keyboard": keyboard
        })

    request("sendMessage", data)


def user(uid, name="O'yinchi"):
    DB.execute(
        "INSERT OR IGNORE INTO users(id, name) VALUES(?, ?)",
        (uid, name)
    )
    DB.execute(
        "UPDATE users SET name=? WHERE id=?",
        (name, uid)
    )
    DB.commit()

    return DB.execute(
        "SELECT * FROM users WHERE id=?",
        (uid,)
    ).fetchone()


def main_menu():
    return [
        [{"text": "🪙 COIN yig'ish", "callback_data": "tap"}],
        [{"text": "💣 Mina o'yini", "callback_data": "mines"}],
        [{"text": "🎁 Kunlik bonus", "callback_data": "bonus"}],
        [{"text": "👑 VIP do'koni", "callback_data": "vip"}],
        [{"text": "🏆 TOP 100", "callback_data": "top"}],
        [{"text": "👤 Profil", "callback_data": "profile"}]
    ]


def show_menu(chat_id, uid, name):
    u = user(uid, name)

    send(
        chat_id,
        "👑 ASLIDDIN COIN\n\n"
        f"🪙 Balansing: {u['coins']} COIN\n"
        f"👑 VIP: {'Faol' if u['vip'] else 'Oddiy'}\n\n"
        "Kerakli bo'limni tanla:",
        main_menu()
    )


def callback_answer(cid, text):
    request("answerCallbackQuery", {
        "callback_query_id": cid,
        "text": text
    })


def start_mines(chat_id, uid):
    u = user(uid)

    if u["coins"] < 50:
        send(
            chat_id,
            "❌ Mina o'yinini boshlash uchun "
            "50 COIN kerak!"
        )
        return

    DB.execute(
        "UPDATE users SET coins=coins-50 WHERE id=?",
        (uid,)
    )
    DB.commit()

    mines = random.sample(range(25), 3)

    game = {
        "mines": mines,
        "opened": [],
        "stake": 50
    }

    path = f"game_{uid}.json"

    with open(path, "w") as f:
        json.dump(game, f)

    show_board(chat_id, uid, game)


def show_board(chat_id, uid, game, result=""):
    keyboard = []

    for row in range(5):
        buttons = []

        for col in range(5):
            i = row * 5 + col

            if i in game["opened"]:
                label = "💎"
                data = "ignore"
            else:
                label = "⬜"
                data = f"cell_{i}"

            buttons.append({
                "text": label,
                "callback_data": data
            })

        keyboard.append(buttons)

    keyboard.append([
        {
            "text": "💰 YUTUQNI OLISH",
            "callback_data": "cashout"
        }
    ])

    safe = len(game["opened"])

    # Mukofot: har xavfsiz katak uchun 15 COIN
    prize = 50 + safe * 15

    send(
        chat_id,
        "💣 MINA O'YINI\n\n"
        "Tikilgan: 50 COIN\n"
        f"Xavfsiz kataklar: {safe}\n"
        f"Joriy mukofot: {prize} COIN\n\n"
        "💥 Minaga tushsang, raund yutug'i yo'qoladi.\n"
        "💰 Xohlagan vaqtingda yutug'ingni ol!",
        keyboard
    )


def handle_callback(c):
    cid = c["id"]
    data = c.get("data", "")
    msg = c.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    person = c.get("from", {})
    uid = person.get("id")
    name = person.get("first_name", "O'yinchi")

    if not uid or not chat_id:
        return

    user(uid, name)

    callback_answer(cid, "ASLIDDIN COIN")

    if data == "ignore":
        return

    if data == "tap":
        today = str(date.today())
        u = user(uid, name)

        if u["tap_day"] != today:
            DB.execute(
                "UPDATE users SET tap_day=?, taps=0 WHERE id=?",
                (today, uid)
            )
            DB.commit()
            u = user(uid, name)

        limit = 2000 if u["vip"] else 200
        reward = 20 if u["vip"] else 1

        if u["taps"] >= limit:
            send(
                chat_id,
                "⏳ Bugungi COIN yig'ish limiting tugadi!"
            )
            return

        amount = min(reward, limit - u["taps"])

        DB.execute("""
            UPDATE users
            SET coins=coins+?, taps=taps+?
            WHERE id=?
        """, (amount, amount, uid))
        DB.commit()

        u = user(uid, name)

        send(
            chat_id,
            f"🪙 +{amount} COIN!\n"
            f"Balans: {u['coins']} COIN\n"
            f"Bugungi limit: {u['taps']}/{limit}",
            main_menu()
        )

    elif data == "bonus":
        today = str(date.today())
        u = user(uid, name)

        if u["bonus_day"] == today:
            send(chat_id, "🎁 Bugungi bonusni olding!")
            return

        reward = 25

        DB.execute("""
            UPDATE users
            SET coins=coins+?, bonus_day=?
            WHERE id=?
        """, (reward, today, uid))
        DB.commit()

        send(
            chat_id,
            f"🎁 Tabriklayman! +{reward} COIN olding!",
            main_menu()
        )

    elif data == "mines":
        if os.path.exists(f"game_{uid}.json"):
            send(
                chat_id,
                "💣 Avval joriy raundni tugat yoki yutug'ingni ol."
            )
        else:
            start_mines(chat_id, uid)

    elif data.startswith("cell_"):
        path = f"game_{uid}.json"

        if not os.path.exists(path):
            send(chat_id, "Avval yangi mina o'yinini boshlagin.")
            return

        with open(path) as f:
            game = json.load(f)

        i = int(data.split("_")[1])

        if i in game["opened"]:
            return

        if i in game["mines"]:
            os.remove(path)

            send(
                chat_id,
                "💥 MINAGA TUSHDING!\n\n"
                "Bu raunddagi 50 COIN yo'qoldi.\n"
                "Yana urinib ko'r!",
                main_menu()
            )
            return

        game["opened"].append(i)

        with open(path, "w") as f:
            json.dump(game, f)

        show_board(chat_id, uid, game)

    elif data == "cashout":
        path = f"game_{uid}.json"

        if not os.path.exists(path):
            send(chat_id, "Hozir faol o'yin yo'q.")
            return

        with open(path) as f:
            game = json.load(f)

        safe = len(game["opened"])

        if safe == 0:
            send(
                chat_id,
                "Avval kamida bitta xavfsiz katakni och!"
            )
            return

        # 50 COIN tikilgan, xavfsiz kataklar uchun
        # 15 COIN dan mukofot qo'shiladi.
        prize = 50 + safe * 15

        DB.execute(
            "UPDATE users SET coins=coins+? WHERE id=?",
            (prize, uid)
        )
        DB.commit()

        os.remove(path)

        send(
            chat_id,
            f"🎉 Raund tugadi!\n"
            f"💰 +{prize} COIN olding!\n"
            "Yana o'ynash uchun Mina o'yinini tanla.",
            main_menu()
        )

    elif data == "profile":
        u = user(uid, name)

        send(
            chat_id,
            "👤 PROFIL\n\n"
            f"Ism: {u['name']}\n"
            f"ID: {uid}\n"
            f"🪙 COIN: {u['coins']}\n"
            f"👑 VIP: {'Faol' if u['vip'] else 'Faol emas'}",
            main_menu()
        )

    elif data == "vip":
        send(
            chat_id,
            "👑 VIP DO'KONI\n\n"
            "VIP uchun hozircha xarid mavjud emas.\n"
            "Keyingi bosqichda VIP xarid tizimini qo'shamiz.",
            main_menu()
        )

    elif data == "top":
        rows = DB.execute("""
            SELECT name, coins FROM users
            ORDER BY coins DESC LIMIT 100
        """).fetchall()

        text = "🏆 ASLIDDIN COIN — TOP 100\n\n"

        for i, row in enumerate(rows, 1):
            text += (
                f"{i}. {row['name']} — "
                f"{row['coins']} COIN\n"
            )

        send(chat_id, text, main_menu())


print("ASLIDDIN COIN ishga tushmoqda...")

offset = 0

while True:
    try:
        result = request("getUpdates", {
            "offset": offset,
            "timeout": 30
        })

        for update in result.get("result", []):
            offset = update["update_id"] + 1

            if "message" in update:
                m = update["message"]
                chat_id = m["chat"]["id"]
                person = m.get("from", {})
                uid = person.get("id")
                name = person.get("first_name", "O'yinchi")
                text = m.get("text", "")

                if uid and text == "/start":
                    show_menu(chat_id, uid, name)

            elif "callback_query" in update:
                try:
                    handle_callback(update["callback_query"])
                except Exception as e:
                    print("Tugma xatosi:", e)

    except Exception as e:
        print("Aloqa xatosi:", e)
        time.sleep(5)
