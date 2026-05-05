import json
import os

def load_expert_data():
    try:
        with open('models_db.json', 'r') as f:
            data = json.load(f)
            print(f"✅ Success: Loaded {len(data)} models from Expert Brain.")
            return data
    except Exception as e:
        print(f"❌ Error loading models_db.json: {e}")
        return {}

def hunt():
    print("🚀 Foundation Four Agent is initializing...")
    expert_models = load_expert_data()
    
    if not expert_models:
        print("⚠️ No models found. Check if models_db.json exists in your repo.")
        return

    # This is where we will add the multi-site scrapers tomorrow
    print("📡 Ready to scan: Bring a Trailer, Rennlist, and Forums.")
    print("🎯 System Online. Standing by for deals.")

if __name__ == "__main__":
    hunt()
