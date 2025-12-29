import requests

BOT_TOKEN = "8585336393:AAEl1KIA0U2rjn_zYvUke_rGpSfdQMe8IXo"
CHAT_ID = 1462710191

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text
    })

if __name__ == "__main__":
    send_message("Test message from Mission RBI")
