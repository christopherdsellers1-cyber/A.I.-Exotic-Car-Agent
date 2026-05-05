import json
import os
import requests

def send_telegram_alert(message):
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        print("❌ Error: Missing credentials in GitHub Secrets.")
        return
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✅ Telegram alert sent successfully!")
        else:
            # This will tell us EXACTLY why it failed (e.g., 401 Unauthorized or 400 Bad Request)
            print(f"❌ Telegram Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"⚠️ Connection Error: {e}")

def main():
    print("🚀 Foundation Four Agent: Starting Diagnostic Hunt...")
    
    # MANDATORY TEST MESSAGE
    send_telegram_alert("🚨 *SYSTEM DIAGNOSTIC*: If you see this, Foundation Four is live.")
    
    with open('models_db.json', 'r') as f:
        expert_db = json.load(f)
    print(f"✅ Loaded {len(expert_db)} models.")

if __name__ == "__main__":
    main()
