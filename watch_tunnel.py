import time
import re
from notify_telegram import send_message

LOG_FILE = "tunnel.log"
URL_REGEX = re.compile(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com")

print("Waiting for Cloudflare tunnel URL...")

while True:
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                match = URL_REGEX.search(line)
                if match:
                    url = match.group(0)
                    send_message(
                        f"🚀 Mission RBI Dashboard Started🌍\n URL:{url}"
                    )
                    print("URL sent to Telegram:", url)
                    exit(0)   # ✅ EXIT AFTER FIRST SEND
    except FileNotFoundError:
        pass

    time.sleep(2)
