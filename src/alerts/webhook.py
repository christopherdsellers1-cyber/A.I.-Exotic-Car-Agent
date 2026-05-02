import requests
import json
from typing import Dict, Any, Optional
from src.utils.logger import get_logger
from src.config import get_config


class WebhookAlerter:
    """Send alerts via webhook to external services."""

    def __init__(self, webhook_url: Optional[str] = None):
        self.logger = get_logger("webhook_alerter")
        config = get_config()
        self.webhook_url = webhook_url or config.webhook_url
        self.webhook_secret = config.webhook_secret

    def send_alert(self, alert_data: Dict[str, Any]) -> bool:
        """
        Send alert via webhook.

        Args:
            alert_data: Dictionary with alert information

        Returns:
            True if successful, False otherwise
        """
        if not self.webhook_url:
            self.logger.warning("Webhook URL not configured")
            return False

        try:
            payload = {
                'type': 'porsche_listing_alert',
                'data': alert_data,
            }

            headers = {
                'Content-Type': 'application/json',
                'X-Porsche-Alert': 'true',
            }

            if self.webhook_secret:
                headers['Authorization'] = f"Bearer {self.webhook_secret}"

            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=headers,
                timeout=10
            )

            if response.status_code in [200, 201, 202]:
                self.logger.info(f"Webhook alert sent successfully")
                return True
            else:
                self.logger.error(f"Webhook returned {response.status_code}: {response.text}")
                return False

        except requests.RequestException as e:
            self.logger.error(f"Failed to send webhook alert: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending webhook alert: {e}")
            return False

    def send_batch_alerts(self, alerts: list[Dict[str, Any]]) -> int:
        """
        Send multiple alerts.

        Args:
            alerts: List of alert dictionaries

        Returns:
            Number of successfully sent alerts
        """
        sent_count = 0
        for alert in alerts:
            if self.send_alert(alert):
                sent_count += 1
        return sent_count

    def format_alert_for_webhook(
        self,
        listing_id: int,
        platform: str,
        model: str,
        year: int,
        price: float,
        market_price: float,
        url: str,
        steal_indicators: list[str],
        confidence_score: float
    ) -> Dict[str, Any]:
        """
        Format listing data as alert for webhook.

        Returns:
            Formatted alert dictionary
        """
        savings = market_price - price if market_price else None

        return {
            'listing_id': listing_id,
            'platform': platform,
            'title': f"{year} {model}",
            'price': float(price),
            'market_price': float(market_price) if market_price else None,
            'savings': float(savings) if savings else None,
            'url': url,
            'steal_indicators': steal_indicators,
            'confidence_score': float(confidence_score),
            'message': (
                f"🚗 PORSCHE ALERT: {year} {model} at ${price:,.0f} "
                f"({f'Save ${savings:,.0f}!' if savings else 'Price TBD'})"
            ),
        }
