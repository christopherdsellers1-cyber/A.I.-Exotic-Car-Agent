import os
import requests

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def hunt():
    print("🚀 Agent is active. Starting scan...")
    
    # This is the test message to verify the connection
    message = "🎯 **System Online:** Porsche Hunter is scanning the market from Akron."
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    
    try:
        response = requests.post(url, json=payload)
        # This will tell us EXACTLY what Telegram says
        if response.status_code == 200:
            print("✅ SUCCESS: Telegram message sent.")
        else:
            print(f"❌ TELEGRAM ERROR: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ CONNECTION ERROR: {e}")

if __name__ == "__main__":
    hunt()
