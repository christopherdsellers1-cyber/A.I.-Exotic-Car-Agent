import json
import requests
from bs4 import BeautifulSoup

def evaluate_deal(listing_title, listing_price, listing_desc, expert_db):
    """The Ruthless Filter: Validates price equity and mechanical shortcuts."""
    
    # 1. Match the model in your 103-car Brain
    for model_name, data in expert_db.items():
        if model_name.lower() in listing_title.lower():
            market_price = data['strike_price']
            
            if market_price == 0: continue # Skip if no strike price is set

            # 2. Equity Calculation ($5k to $20k below market)
            equity = market_price - listing_price
            if not (5000 <= equity <= 20000):
                continue

            # 3. Clean Title & History Verification
            red_flags = ['salvage', 'rebuilt', 'accident', 'damage', 'lemon']
            if any(flag in listing_desc.lower() for flag in red_flags):
                print(f"🚩 Rejected {listing_title}: History red flags found.")
                continue

            # 4. Mandatory "Green Flags" (Clean Title & Records)
            must_haves = ['service records', 'maintenance', 'clean title']
            if not any(flag in listing_desc.lower() for flag in must_haves):
                continue

            # 5. Expert Shortcut Match (Manual, PTS, Weissach, etc.)
            shortcuts = [s.strip().lower() for s in data['shortcuts'].split('.') if s.strip()]
            found_shortcuts = [s for s in shortcuts if s in listing_desc.lower() or s in listing_title.lower()]
            
            if found_shortcuts:
                return {
                    "status": "HIT",
                    "model": model_name,
                    "equity": equity,
                    "features": found_shortcuts
                }
    return None

def main():
    print("🚀 Foundation Four Agent: Executing Targeted Hunt...")
    with open('models_db.json', 'r') as f:
        expert_db = json.load(f)
    
    print(f"✅ Loaded {len(expert_db)} models with strict filters.")
    # Tomorrow we connect the Scraper output directly to this evaluator.
