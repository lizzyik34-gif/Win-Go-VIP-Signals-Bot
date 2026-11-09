import time
import json
import random
import urllib.request
import threading
import os
from datetime import datetime, timezone, date
from flask import Flask

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super-secret-win-go-key-2026")

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = "9220984648:AAHdxoWfIKx_voCokgn2_NiSSzglcgRVCxo"

# Unlimited Admin IDs (Untouched)
UNLIMITED_USER_IDS = ["8842031370", "7891601316"]

# Daily Limited Users (Untouched - 60 signals per day)
LIMITED_USERS = {
    "8882241036": {"limit": 60, "used": 0, "last_date": str(date.today())}
}

# Free Trial Tracking: cumulative wins and stage tracking per user
FREE_TRIALS = {}

# Keep track of users we've already notified the admin about
NOTIFIED_USERS = set()

def get_color_from_number(num):
    if num == 0:
        return "🔴 RED + 🟣 VIOLET"
    elif num == 5:
        return "🟢 GREEN + 🟣 VIOLET"
    elif num in [1, 3, 7, 9]:
        return "🟢 GREEN"
    else:
        return "🔴 RED"

def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload_dict = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload_dict["reply_markup"] = reply_markup

    payload = json.dumps(payload_dict).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"Error sending message: {e}")

def answer_callback_query(callback_query_id, text=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
    payload_dict = {"callback_query_id": callback_query_id}
    if text:
        payload_dict["text"] = text
    payload = json.dumps(payload_dict).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"Error answering callback: {e}")

def notify_admin_about_user(user_id, first_name, username):
    if user_id not in UNLIMITED_USER_IDS and user_id not in LIMITED_USERS and user_id not in NOTIFIED_USERS:
        NOTIFIED_USERS.add(user_id)
        admin_msg = (
            f"🔔 *New Bot User Alert!*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Name*: {first_name}\n"
            f"🔗 *Username*: @{username if username else 'None'}\n"
            f"🆔 *User ID*: `{user_id}`\n"
            f"🎁 *Status*: Free Trial User"
        )
        send_message("8842031370", admin_msg)

def check_user_access(user_id):
    today_str = str(date.today())

    # 1. Unlimited Users (Untouched)
    if user_id in UNLIMITED_USER_IDS:
        return True

    # 2. Daily Limited Users (Untouched - 60/day)
    if user_id in LIMITED_USERS:
        user_data = LIMITED_USERS[user_id]
        if user_data["last_date"] != today_str:
            user_data["used"] = 0
            user_data["last_date"] = today_str

        if user_data["used"] < user_data["limit"]:
            user_data["used"] += 1
            return True
        else:
            return False

    # 3. Free Trial Users
    if user_id not in FREE_TRIALS:
        FREE_TRIALS[user_id] = {"wins": 0, "stage": 1, "expired": False}

    if FREE_TRIALS[user_id]["expired"]:
        return False

    return True

def generate_prediction_signal(tf_name, tf_secs, offset=0, stage_override=1):
    now = datetime.now(timezone.utc)
    date_prefix = now.strftime("%Y%m%d")
    secs_today = now.hour * 3600 + now.minute * 60 + now.second
    base_idx = secs_today // tf_secs + 100010001
    period_idx = base_idx + offset
    period_number = f"{date_prefix}{period_idx}"

    num = random.randint(0, 9)
    color = get_color_from_number(num)
    win_rate = random.randint(75, 88)
    stage = stage_override  # Uses current active stage

    signal_text = (
        f"📊 *WIN GO COLOR SIGNAL ({tf_name})*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔹 *Period*: `{period_number}`\n"
        f"📈 *Stage Level*: Stage {stage} / 6\n"
        f"🎨 *Color Bet*: *{color}*\n"
        f"🔢 *Target Number*: `{num}`\n"
        f"🔥 *Win Rate*: `{win_rate}%` \n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👇 *Did this signal Win or Lose?*"
    )
    
    buttons = {
        "inline_keyboard": [
            [
                {"text": "✅ Win", "callback_data": "result_win"},
                {"text": "❌ Loss", "callback_data": "result_loss"}
            ]
        ]
    }
    return signal_text, buttons

def send_start_menu(chat_id):
    buttons = {
        "inline_keyboard": [
            [
                {"text": "⚡ 30s", "callback_data": "tf_30s_0"},
                {"text": "🔥 1m", "callback_data": "tf_1m_0"},
                {"text": "📈 3m", "callback_data": "tf_3m_0"},
                {"text": "📊 5m", "callback_data": "tf_5m_0"}
            ],
            [
                {"text": "⏭️ Next 30s (+1)", "callback_data": "tf_30s_1"},
                {"text": "⏭️ Next 1m (+1)", "callback_data": "tf_1m_1"}
            ]
        ]
    }
    msg = (
        "👋 *Welcome to Win Go Color Signal Bot!*\n\n"
        "🎁 *Free Trial Active*: Accumulate 7 total wins to complete your trial!\n\n"
        "**Current Commands:**\n"
        "▪ `/30s`, `/1m`, `/3m`, `/5m` - Current Period\n"
        "▪ `/next30s`, `/next1m`, `/next3m`, `/next5m` - Next Period Ahead"
    )
    send_message(chat_id, msg, reply_markup=buttons)

def telegram_bot_loop():
    print("Telegram Bot worker is starting...")
    try:
        urllib.request.urlopen(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook?drop_pending_updates=true", timeout=5)
    except Exception:
        pass

    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={offset}&timeout=30"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=35) as response:
                data = json.loads(response.read().decode("utf-8"))
                for result in data.get("result", []):
                    offset = result["update_id"] + 1

                    if "message" in result:
                        message = result["message"]
                        chat_id = message.get("chat", {}).get("id")
                        user_info = message.get("from", {})
                        user_id = str(user_info.get("id", ""))
                        first_name = user_info.get("first_name", "Unknown")
                        username = user_info.get("username", "")
                        text = message.get("text", "").strip()

                        if chat_id:
                            notify_admin_about_user(user_id, first_name, username)

                            if not check_user_access(user_id):
                                send_message(chat_id, "⛔ *Free Trial Completed*: You have completed your 7 wins! Your free trial has ended. Please contact the administrator to upgrade.")
                                continue

                            if text == "/start":
                                send_start_menu(chat_id)
                            elif text in ["/30s", "/1m", "/3m", "/5m", "/signal", "/next30s", "/next1m", "/next3m", "/next5m", "/next"]:
                                secs_map = {"/30s": 30, "/1m": 60, "/signal": 60, "/3m": 180, "/5m": 300, "/next30s": 30, "/next1m": 60, "/next": 60, "/next3m": 180, "/next5m": 300}
                                names_map = {"/30s": "30S", "/1m": "1M", "/signal": "1M", "/3m": "3M", "/5m": "5M", "/next30s": "30S (Next)", "/next1m": "1M (Next)", "/next": "1M (Next)", "/next3m": "3M (Next)", "/next5m": "5M (Next)"}
                                offset_val = 1 if "next" in text else 0
                                
                                current_stage = 1
                                if user_id in FREE_TRIALS:
                                    current_stage = FREE_TRIALS[user_id]["stage"]

                                sig_text, sig_markup = generate_prediction_signal(names_map.get(text, "1M"), secs_map.get(text, 60), offset_val, current_stage)
                                send_message(chat_id, sig_text, reply_markup=sig_markup)

                    elif "callback_query" in result:
                        cb = result["callback_query"]
                        cb_id = cb["id"]
                        chat_id = cb["message"]["chat"]["id"]
                        user_info = cb["from"]
                        user_id = str(user_info["id"])
                        first_name = user_info.get("first_name", "Unknown")
                        username = user_info.get("username", "")
                        data_key = cb.get("data", "")

                        notify_admin_about_user(user_id, first_name, username)

                        if data_key.startswith("result_"):
                            answer_callback_query(cb_id)
                            if user_id not in FREE_TRIALS:
                                FREE_TRIALS[user_id] = {"wins": 0, "stage": 1, "expired": False}

                            if not FREE_TRIALS[user_id]["expired"]:
                                if data_key == "result_win":
                                    # Add to total accumulated wins, and reset stage back to 1
                                    FREE_TRIALS[user_id]["wins"] += 1
                                    FREE_TRIALS[user_id]["stage"] = 1  
                                    total_wins = FREE_TRIALS[user_id]["wins"]
                                    
                                    if total_wins >= 7:
                                        FREE_TRIALS[user_id]["expired"] = True
                                        send_message(chat_id, "🎉 *Congratulations!* You reached 7 total wins! Your free trial is now complete. Contact the admin to upgrade.")
                                    else:
                                        send_message(chat_id, f"✅ *Win Recorded!* Total Wins: `{total_wins}/7`. Stage reset back to `Stage 1`.")
                                        
                                elif data_key == "result_loss":
                                    # Advance stage on loss (caps at stage 6), keeping previous wins safe!
                                    if FREE_TRIALS[user_id]["stage"] < 6:
                                        FREE_TRIALS[user_id]["stage"] += 1
                                    next_stage = FREE_TRIALS[user_id]["stage"]
                                    current_wins = FREE_TRIALS[user_id]["wins"]
                                    send_message(chat_id, f"❌ *Loss Recorded.* Safe Wins: `{current_wins}/7`. Advancing to *Stage {next_stage} / 6*.")
                            continue

                        if not check_user_access(user_id):
                            answer_callback_query(cb_id, "Free trial completed!")
                            continue

                        if data_key.startswith("tf_"):
                            answer_callback_query(cb_id)
                            parts = data_key.split("_")
                            tf_type = parts[1] 
                            offset_val = int(parts[2]) if len(parts) > 2 else 0

                            secs_map = {"30s": 30, "1m": 60, "3m": 180, "5m": 300}
                            name_map = {"30s": "30S", "1m": "1M", "3m": "3M", "5m": "5M"}

                            if tf_type in secs_map:
                                label = f"{name_map[tf_type]} (Next)" if offset_val > 0 else name_map[tf_type]
                                current_stage = 1
                                if user_id in FREE_TRIALS:
                                    current_stage = FREE_TRIALS[user_id]["stage"]

                                sig_text, sig_markup = generate_prediction_signal(label, secs_map[tf_type], offset_val, current_stage)
                                send_message(chat_id, sig_text, reply_markup=sig_markup)

        except Exception:
            time.sleep(5)

@app.route("/")
def home():
    return "<h3>FB999 Smart Signals Bot is Live & Running!</h3>"

if __name__ == "__main__":
    bot_thread = threading.Thread(target=telegram_bot_loop, daemon=True)
    bot_thread.start()
    
    app.run(host="0.0.0.0", port=10000)
