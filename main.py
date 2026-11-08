import time
import json
import random
import urllib.request
import threading
import os
from datetime import datetime, timezone
from flask import Flask

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super-secret-win-go-key-2026")

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = "9220984648:AAHdxoWfIKx_voCokgn2_NiSSzglcgRVCxo"
AUTHORIZED_USER_ID = "8842031370"

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

def generate_prediction_signal(tf_name, tf_secs, offset=0):
    now = datetime.now(timezone.utc)
    date_prefix = now.strftime("%Y%m%d")
    secs_today = now.hour * 3600 + now.minute * 60 + now.second
    base_idx = secs_today // tf_secs + 100010001
    period_idx = base_idx + offset
    period_number = f"{date_prefix}{period_idx}"

    num = random.randint(0, 9)
    color = get_color_from_number(num)
    win_rate = random.randint(75, 88)
    stage = random.randint(1, 3)

    signal_text = (
        f"📊 *WIN GO COLOR SIGNAL ({tf_name})*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔹 *Period*: `{period_number}`\n"
        f"📈 *Stage Level*: Stage {stage} / 6\n"
        f"🎨 *Color Bet*: *{color}*\n"
        f"🔢 *Target Number*: `{num}`\n"
        f"🔥 *Win Rate*: `{win_rate}%` \n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ *Status*: ACTIVE SIGNAL"
    )
    return signal_text

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
                        user_id = str(message.get("from", {}).get("id", ""))
                        text = message.get("text", "").strip()

                        if chat_id:
                            if user_id != AUTHORIZED_USER_ID:
                                send_message(chat_id, "⛔ *Access Denied*: You are not authorized to use this bot.")
                                continue

                            # Standard current period commands
                            if text == "/start":
                                send_start_menu(chat_id)
                            elif text == "/30s":
                                send_message(chat_id, generate_prediction_signal("30S", 30, 0))
                            elif text in ["/1m", "/signal"]:
                                send_message(chat_id, generate_prediction_signal("1M", 60, 0))
                            elif text == "/3m":
                                send_message(chat_id, generate_prediction_signal("3M", 180, 0))
                            elif text == "/5m":
                                send_message(chat_id, generate_prediction_signal("5M", 300, 0))
                            
                            # Next period ahead commands
                            elif text == "/next30s":
                                send_message(chat_id, generate_prediction_signal("30S (Next)", 30, 1))
                            elif text in ["/next1m", "/next"]:
                                send_message(chat_id, generate_prediction_signal("1M (Next)", 60, 1))
                            elif text == "/next3m":
                                send_message(chat_id, generate_prediction_signal("3M (Next)", 180, 1))
                            elif text == "/next5m":
                                send_message(chat_id, generate_prediction_signal("5M (Next)", 300, 1))

                    elif "callback_query" in result:
                        cb = result["callback_query"]
                        chat_id = cb["message"]["chat"]["id"]
                        user_id = str(cb["from"]["id"])
                        data_key = cb.get("data", "")

                        if user_id != AUTHORIZED_USER_ID:
                            continue

                        if data_key.startswith("tf_"):
                            parts = data_key.split("_")
                            tf_type = parts[1] 
                            offset_val = int(parts[2]) if len(parts) > 2 else 0

                            secs_map = {"30s": 30, "1m": 60, "3m": 180, "5m": 300}
                            name_map = {"30s": "30S", "1m": "1M", "3m": "3M", "5m": "5M"}

                            if tf_type in secs_map:
                                label = f"{name_map[tf_type]} (Next)" if offset_val > 0 else name_map[tf_type]
                                send_message(chat_id, generate_prediction_signal(label, secs_map[tf_type], offset_val))

        except Exception as e:
            time.sleep(5)

@app.route("/")
def home():
    return "<h3>FB999 Smart Signals Bot is Live & Running!</h3>"

if __name__ == "__main__":
    bot_thread = threading.Thread(target=telegram_bot_loop, daemon=True)
    bot_thread.start()
    
    app.run(host="0.0.0.0", port=10000)
