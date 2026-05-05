import json
import os

def load_brain():
    """Loads the 100+ models from your Expert Database."""
    try:
        with open('models_db.json', 'r') as f:
            db = json.load(f)
            print(f"✅ Success: Loaded {len(db)} models from Foundation Four Brain.")
            return db
    except FileNotFoundError:
        print("❌ Error: models_db.json not found in repository.")
        return {}
    except json.JSONDecodeError:
        print("❌ Error: models_db.json has a formatting error.")
        return {}

def hunt():
    print("🚀 Foundation Four Agent: Initializing Search...")
    expert_db = load_brain()
    
    if not expert_db:
        return

    # Diagnostic check for your top tier models
    core_4 = ["Porsche 911 GT3 (991)", "Porsche Cayenne (3rd Gen)", "BMW X5 M (G05)", "Mercedes-AMG GT Series"]
    
    print("\n🔍 Monitoring Strike Zones for:")
    for car in core_4:
        if car in expert_db:
            # Matches shortcuts from your exotic_car_agent_ultimate.html
            print(f"  - {car}: Looking for {expert_db[car]['shortcuts']}")

    print("\n🎯 System Online. Scanning Marketplaces...")

if __name__ == "__main__":
    hunt()
