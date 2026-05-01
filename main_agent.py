def analyze_listing(listing, db):
    model_name = listing['full_name']
    if model_name in db:
        target = db[model_name]
        
        # LOGIC 1: Price Check
        price_gap = target['strike_price'] - listing['price']
        
        # LOGIC 2: Keyword Shortcut Check (from your HTML)
        has_keywords = any(word.lower() in listing['description'].lower() 
                          for word in target['shortcuts'].split())

        if price_gap > 0 and has_keywords:
            return f"🔥 DEAL ALERT: {model_name} is ${price_gap} BELOW strike price!"
    return None
