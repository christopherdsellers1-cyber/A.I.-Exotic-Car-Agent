import json

def load_brain():
    with open('models_db.json', 'r') as f:
        return json.load(f)

def evaluate_listing(listing):
    brain = load_brain()
    model_key = f"{listing['make']} {listing['model']}"
    
    if model_key in brain:
        rules = brain[model_key]
        # logic: Is price below our Strike Price?
        if listing['price'] <= rules['strike_price']:
            # logic: Does the description have our 'Must-Have' shortcuts?
            # (e.g., 'Manual', 'PTS', 'Carbon Buckets')
            return True
    return False
