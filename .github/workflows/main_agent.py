import sqlite3
import requests
# The AI will add the scraping logic here for Classic.com and others.

def hunt_for_porsches():
    # 1. Check the 'hit_list.csv' for targets
    # 2. Scrape the live market
    # 3. If Model in Hit List and Price < Target:
    #    4. Check SQLite Database: Have I seen this VIN before?
    #    5. If New: Send Telegram Alert + Save to Database
    print("Agent is hunting...")

if __name__ == "__main__":
    hunt_for_porsches()
