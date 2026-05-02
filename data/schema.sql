-- Core listing storage
CREATE TABLE IF NOT EXISTS listings (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    platform_id VARCHAR(255) UNIQUE NOT NULL,
    url TEXT NOT NULL,
    title VARCHAR(255),
    model VARCHAR(100),
    generation VARCHAR(50),
    year INTEGER,
    price DECIMAL(10,2),
    price_currency VARCHAR(3) DEFAULT 'USD',
    mileage INTEGER,
    mileage_unit VARCHAR(5),
    condition VARCHAR(50),
    transmission VARCHAR(20),
    title_status VARCHAR(50),
    owner_count INTEGER,
    features_json JSONB,
    has_service_records BOOLEAN,
    has_accidents BOOLEAN,
    seller_name VARCHAR(255),
    seller_location VARCHAR(255),
    image_urls JSONB,
    raw_html TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active',
    INDEX listing_platform (platform, platform_id),
    INDEX listing_created (created_at),
    INDEX listing_model_year (model, year),
    INDEX listing_price (price)
);

-- Track price/mileage changes over time
CREATE TABLE IF NOT EXISTS listing_history (
    id SERIAL PRIMARY KEY,
    listing_id INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    price DECIMAL(10,2),
    mileage INTEGER,
    condition VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX listing_history_idx (listing_id, timestamp)
);

-- Track what we've alerted on
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    listing_id INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    alert_type VARCHAR(50) DEFAULT 'new_match',
    reason TEXT,
    steal_indicators JSONB,
    confidence_score DECIMAL(3,2),
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    delivered_at TIMESTAMP,
    user_acknowledged BOOLEAN DEFAULT FALSE,
    INDEX alert_listing (listing_id, sent_at)
);

-- Prevent duplicate processing
CREATE TABLE IF NOT EXISTS dedup_log (
    id SERIAL PRIMARY KEY,
    listing_hash VARCHAR(64) UNIQUE NOT NULL,
    platform VARCHAR(50),
    listing_id INTEGER REFERENCES listings(id) ON DELETE SET NULL,
    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX dedup_created (created_at)
);

-- Market reference data
CREATE TABLE IF NOT EXISTS market_baseline (
    id SERIAL PRIMARY KEY,
    model VARCHAR(100),
    generation VARCHAR(50),
    year_start INTEGER,
    year_end INTEGER,
    market_price DECIMAL(10,2),
    updated_at TIMESTAMP,
    source VARCHAR(255),
    INDEX market_model_year (model, year_start)
);

-- Scraper run logs for monitoring
CREATE TABLE IF NOT EXISTS scraper_logs (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(50),
    status VARCHAR(20),
    listings_found INTEGER,
    listings_processed INTEGER,
    errors INTEGER,
    runtime_seconds INTEGER,
    run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    INDEX scraper_logs_platform (platform, run_at)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_listings_status ON listings(status);
CREATE INDEX IF NOT EXISTS idx_listings_model ON listings(model);
CREATE INDEX IF NOT EXISTS idx_listings_year ON listings(year);
CREATE INDEX IF NOT EXISTS idx_alerts_sent ON alerts(sent_at DESC);
