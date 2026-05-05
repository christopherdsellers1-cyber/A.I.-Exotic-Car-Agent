import json
import os
import requests

def send_telegram_alert(message):
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        print("❌ Error: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing from GitHub Secrets.")
        return
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✅ Telegram alert sent successfully!")
        else:
            print(f"❌ Telegram Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"⚠️ Failed to connect to Telegram: {e}")

def main():
    print("🚀 Foundation Four Agent: Executing Targeted Hunt...")
    # Your existing loading logic here
    
    # TEST TRIGGER: Un-comment the line below to force a test message to your phone
    # send_telegram_alert("🚀 *Foundation Four Online* \nSystem is scanning for $5k-$20k equity gaps.")
