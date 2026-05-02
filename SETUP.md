# AI Exotic Car Agent - Setup Guide

Automated system to monitor Porsche listings across multiple platforms and alert when you find deals matching your criteria.

## 📋 Prerequisites

- Python 3.10+
- PostgreSQL 12+
- Docker & Docker Compose (optional, for containerized deployment)

## 🚀 Quick Start

### 1. Clone & Navigate
```bash
cd /path/to/A.I.-Exotic-Car-Agent
```

### 2. Install Dependencies
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your settings
```

### 4. Set Up Database

#### Option A: Using PostgreSQL locally
```bash
# Create database
createdb -U postgres exotic_car_db

# Import schema
psql -U postgres -d exotic_car_db -f data/schema.sql
```

#### Option B: Using Docker
```bash
cd docker
docker-compose up -d postgres
# Wait for postgres to be ready, then:
docker exec porsche_db psql -U postgres -d exotic_car_db -f /docker-entrypoint-initdb.d/schema.sql
```

### 5. Initialize Application
```bash
python -m src.config  # Test configuration loading
```

### 6. Run Scrapers
```bash
# Run all scrapers
python -m src.main scrape --all

# Run specific platform
python -m src.main scrape --platform CLASSIC.COM

# View recent alerts
python -m src.main alerts --since 24h
```

## 📁 Project Structure

```
A.I.-Exotic-Car-Agent/
├── src/
│   ├── main.py                 # Main entry point
│   ├── config.py               # Configuration manager
│   ├── scrapers/               # Platform-specific scrapers
│   │   ├── base_scraper.py
│   │   ├── classic_scraper.py
│   │   ├── pcarmarket_scraper.py
│   │   └── ...
│   ├── filters/                # Matching & filtering logic
│   │   ├── matcher.py
│   │   └── requirements.py
│   ├── storage/                # Database layer
│   │   ├── models.py
│   │   └── database.py
│   ├── alerts/                 # Alert delivery
│   │   └── webhook.py
│   └── utils/                  # Utilities
│       ├── csv_parser.py
│       └── logger.py
├── data/
│   ├── hit_list.csv            # Your target vehicles
│   ├── requirements.md         # Your requirements
│   └── schema.sql              # Database schema
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── tests/                      # Test suite
├── logs/                       # Application logs
├── requirements.txt            # Python dependencies
└── .env.example               # Environment template
```

## ⚙️ Configuration

### .env File
```ini
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=exotic_car_db
DB_USER=postgres
DB_PASSWORD=your_password

# Webhook Alerting
WEBHOOK_URL=https://your-webhook-endpoint.com/notify
WEBHOOK_SECRET=your_secret_key

# Application
LOG_LEVEL=INFO
UPDATE_FREQUENCY_HOURS=12
SCRAPER_TIMEOUT=30
```

### hit_list.csv
Edit `/data/hit_list.csv` with your target vehicles. Format:
```csv
Model,Generation,Years,Target Buy Price,The Steal Indicator
Porsche GT3,991.1,2014-2016,"<$145,000","Documented G6 engine swap + PCCBs"
...
```

### requirements.md
Edit `/data/requirements.md` with your buying criteria:
```
Clean Title
One to Six Owners
No accidents
Must have service records
Only alert me if the price is $5k to $20k below market
...
```

## 🐳 Docker Deployment

### Local Testing
```bash
cd docker
docker-compose up -d

# Check logs
docker-compose logs -f app

# Stop
docker-compose down
```

### Production Deployment

1. Update `.env` with production settings
2. Deploy with Docker Compose or Kubernetes
3. Set up CI/CD pipeline for automatic updates

Example with systemd:
```bash
# Create service file
sudo nano /etc/systemd/system/porsche-scraper.service

[Unit]
Description=Porsche Listing Monitor
After=network.target postgresql.service

[Service]
Type=simple
User=porsche
WorkingDirectory=/home/porsche/A.I.-Exotic-Car-Agent
Environment="PATH=/home/porsche/A.I.-Exotic-Car-Agent/venv/bin"
ExecStart=/home/porsche/A.I.-Exotic-Car-Agent/venv/bin/python -m src.main scrape --all
Restart=always
RestartSec=300

[Install]
WantedBy=multi-user.target

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable porsche-scraper
sudo systemctl start porsche-scraper
```

## 🔔 Webhook Alerting

Configure webhook endpoint to receive alerts:

```json
{
  "type": "porsche_listing_alert",
  "data": {
    "listing_id": 123,
    "platform": "CLASSIC.COM",
    "title": "2015 Porsche 911 GT3",
    "price": 142000,
    "market_price": 148000,
    "savings": 6000,
    "url": "https://...",
    "steal_indicators": ["Documented G6 engine swap", "PCCBs"],
    "confidence_score": 0.95,
    "message": "🚗 PORSCHE ALERT: 2015 Porsche 911 GT3 at $142,000"
  }
}
```

### Popular Webhook Integrations

- **IFTTT**: Create webhook applet to send notifications
- **Slack**: Post alerts to Slack channel
- **Discord**: Send Discord webhook messages
- **Email**: Transform via Zapier to email
- **SMS**: Use Twilio webhook integration

## 📊 Database Management

### View Recent Alerts
```bash
psql -U postgres -d exotic_car_db -c "SELECT * FROM alerts ORDER BY sent_at DESC LIMIT 10;"
```

### Clear Old Data
```bash
psql -U postgres -d exotic_car_db -c "DELETE FROM listings WHERE status='sold' AND last_seen_at < NOW() - INTERVAL '30 days';"
```

### Backup
```bash
pg_dump -U postgres exotic_car_db > backup.sql
```

## 🧪 Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=src tests/

# Run specific test
pytest tests/test_matcher.py -v
```

## 🐛 Troubleshooting

### Database Connection Error
```
Error: could not connect to server
```
- Ensure PostgreSQL is running
- Check DB_HOST, DB_PORT, DB_USER, DB_PASSWORD in .env

### Module Not Found
```
ModuleNotFoundError: No module named 'src'
```
- Run from project root: `cd /path/to/A.I.-Exotic-Car-Agent`
- Or add to PYTHONPATH: `export PYTHONPATH="${PYTHONPATH}:/path/to/A.I.-Exotic-Car-Agent"`

### No Alerts Being Sent
- Check webhook URL is correct
- Verify webhook endpoint is accessible
- Check logs: `tail -f logs/webhook_alerter.log`

### Scraper Failures
```bash
# Check scraper logs
tail -f logs/scraper_classic.log

# Run single scraper with debug
python -m src.main scrape --platform CLASSIC.COM --debug
```

## 📝 Logs

Logs are stored in `/logs/` directory:
- `scraper_*.log` - Platform-specific scrape logs
- `webhook_alerter.log` - Alert delivery logs
- `database.log` - Database operations

## 🔄 Maintenance

### Weekly
- Review alerts and feedback on accuracy
- Check scraper success rates
- Monitor database size

### Monthly
- Update market baseline prices
- Review and adjust steal thresholds
- Backup database

### Quarterly
- Update Python dependencies
- Test all scrapers against live sites
- Review and optimize matching rules

## 📞 Support

For issues or questions:
1. Check logs in `/logs/` directory
2. Review configuration in `.env`
3. Test individual scrapers
4. Check platform websites are accessible

## 📄 License

MIT License - See LICENSE file for details
