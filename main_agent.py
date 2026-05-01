import json

def get_expert_criteria(make_model):
    with open('models_db.json', 'r') as f:
        db = json.load(f)
    # This finds the "Shortcut" from your HTML file
    return db.get(make_model, "No specific shortcuts found.")

def scan_and_filter(listing):
    criteria = get_expert_criteria(f"{listing['make']} {listing['model']}")
    print(f"Checking against Expert Brain: {criteria}")
    
    # RUTHLESS FILTER: Only alert if it hits your specific "Brain" criteria
    # Example: If the Brain says 'PCCB' and the car doesn't have it, we skip.
