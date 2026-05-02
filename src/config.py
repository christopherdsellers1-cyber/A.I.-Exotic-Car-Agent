import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any
from src.utils.csv_parser import load_config
from src.utils.logger import get_logger

# Load environment variables
load_dotenv()

logger = get_logger("config")


class Config:
    """Central configuration object."""

    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.data_dir = self.base_dir / "data"
        self.logs_dir = self.base_dir / "logs"

        # Create directories if they don't exist
        self.logs_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)

        # Database
        self.db_host = os.getenv('DB_HOST', 'localhost')
        self.db_port = os.getenv('DB_PORT', '5432')
        self.db_name = os.getenv('DB_NAME', 'exotic_car_db')
        self.db_user = os.getenv('DB_USER', 'postgres')
        self.db_password = os.getenv('DB_PASSWORD', 'postgres')
        self.database_url = f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

        # Email alerting (optional)
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.alert_to_email = os.getenv('ALERT_TO_EMAIL', '')

        # Webhook alerting
        self.webhook_url = os.getenv('WEBHOOK_URL', '')
        self.webhook_secret = os.getenv('WEBHOOK_SECRET', '')

        # Scraper settings
        self.user_agent = os.getenv('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        self.scraper_timeout = int(os.getenv('SCRAPER_TIMEOUT', '30'))
        self.max_retries = int(os.getenv('MAX_RETRIES', '3'))

        # Scheduler settings
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.update_frequency_hours = int(os.getenv('UPDATE_FREQUENCY_HOURS', '12'))

        # Load hit list and requirements
        self.app_config = self._load_app_config()

    def _load_app_config(self) -> Dict[str, Any]:
        """Load application configuration from CSV/MD files."""
        try:
            # Check both data/ and root directory for files
            hit_list_path = self.data_dir / 'hit_list.csv'
            if not hit_list_path.exists():
                hit_list_path = self.base_dir / 'hit_list.csv'

            requirements_path = self.data_dir / 'requirements.md'
            if not requirements_path.exists():
                requirements_path = self.base_dir / 'requirements.md'

            if not hit_list_path.exists():
                logger.warning(f"Hit list file not found: {hit_list_path}")
                return {}

            if not requirements_path.exists():
                logger.warning(f"Requirements file not found: {requirements_path}")
                return {}

            config = load_config(str(hit_list_path), str(requirements_path))
            logger.info(f"Loaded {len(config.get('hit_list', []))} hit list entries")
            logger.info(f"Loaded {len(config.get('requirements', []))} requirements")
            return config

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return {}

    @property
    def hit_list(self):
        """Get hit list entries."""
        return self.app_config.get('hit_list', [])

    @property
    def hit_list_dict(self):
        """Get hit list as dictionary."""
        return self.app_config.get('hit_list_dict', {})

    @property
    def requirements(self):
        """Get requirements list."""
        return self.app_config.get('requirements', [])

    @property
    def requirements_categorized(self):
        """Get categorized requirements."""
        return self.app_config.get('requirements_categorized', {})

    def is_email_configured(self) -> bool:
        """Check if email alerting is properly configured."""
        return bool(self.smtp_user and self.smtp_password and self.alert_to_email)

    def is_webhook_configured(self) -> bool:
        """Check if webhook alerting is properly configured."""
        return bool(self.webhook_url)

    def __repr__(self):
        return (
            f"<Config("
            f"db={self.db_name}, "
            f"hit_list_entries={len(self.hit_list)}, "
            f"requirements={len(self.requirements)}"
            f")>"
        )


# Global config instance
_config = None


def get_config() -> Config:
    """Get global config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def init_config() -> Config:
    """Initialize and return config."""
    return get_config()
