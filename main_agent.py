import json
import requests
from bs4 import BeautifulSoup
import time

def load_brain():
    try:
        with open('models_db.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Brain Error: {e}")
        return {}

def scan_rennlist(expert_db):
    print("👀 Scanning Rennlist Marketplace...")
    # Target: Porsche 911 (991) and GT3 sections
    url = "https://rennlist.com/forums/market/vehicles"
    headers = {'User-Agent': 'Foundation-Four-Agent-1.0'}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        listings = soup.find_all('div', class_='thread-info') # Rennlist specific class

        for item in listings:
            title = item.find('a').text.strip()
            price_str = item.find('span', class_='price').text.strip() if item.find('span', class_='price') else "0"
            
            # Clean price: remove $, commas
            price = int(''.join(filter(str.isdigit, price_str))) if price_str != "0" else 0

            # Match against your 103 models
            for model, data in expert_db.items():
                if model.split(' ')[0] in title and data['strike_price'] > 0:
                    # Check for your "Shortcuts"
                    matches = [s for s in data['shortcuts'].split('.') if s.strip().lower() in title.lower()]
                    
                    if price <= data['strike_price'] and price != 0:
                        print(f"🎯 HIT: {title} | Price: ${price} | Target: ${data['strike_price']}")
                        print(f"✨ Match on Shortcuts: {matches}")
                        # Next step: Send Telegram notification
    except Exception as e:
        print(f"⚠️ Scraper encountered a minor hurdle: {e}")

def main():
    print("🚀 Foundation Four Agent: Initializing Search...")
    expert_db = load_brain()
    if expert_db:
        print(f"✅ Success: Loaded {len(expert_db)} models.")
        scan_rennlist(expert_db)
        print("🎯 Scan Complete. Resting for next cycle...")

if __name__ == "__main__":
    main()
