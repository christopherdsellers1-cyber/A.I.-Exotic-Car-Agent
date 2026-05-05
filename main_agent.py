import json
import requests
from bs4 import BeautifulSoup

def evaluate_deal(listing, expert_db):
    name = listing['title']
    price = listing['price']
    desc = listing['description'].lower()

    if name in expert_db:
        target = expert_db[name]
        market_price = target['strike_price']
        
        # 1. Price Arbitrage Check ($5k to $20k below market)
        savings = market_price - price
        if not (5000 <= savings <= 20000):
            return False

        # 2. Clean Title & History Filter
        red_flags = ['salvage', 'rebuilt', 'accident', 'damage', 'lemon']
        if any(flag in desc for flag in red_flags):
            return False

        # 3. Required "Green Flags"
        must_haves = ['service records', 'maintenance', 'clean title']
        if not any(flag in desc for flag in must_haves):
            return False

        return True
    return False
