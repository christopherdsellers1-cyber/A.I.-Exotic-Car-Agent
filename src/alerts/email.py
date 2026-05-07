"""
Email alerts via SendGrid API.
"""

import os
from typing import Optional
from src.utils.logger import get_logger

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False


class EmailAlerter:
    """Send alerts via SendGrid email service."""

    def __init__(self):
        self.logger = get_logger("email_alerter")
        self.api_key = os.getenv('SENDGRID_API_KEY', '')
        self.from_email = os.getenv('ALERT_FROM_EMAIL', '')
        self.to_email = os.getenv('ALERT_TO_EMAIL', '')

        if not SENDGRID_AVAILABLE:
            self.logger.warning("SendGrid not installed. Install with: pip install sendgrid")
            return

        if not self.api_key or not self.from_email or not self.to_email:
            self.logger.warning("SendGrid not configured (missing API key or email addresses)")
            return

        self.sg = SendGridAPIClient(self.api_key)
        self.logger.info("SendGrid email alerter initialized")

    def send_alert(self, subject: str, html_body: str) -> bool:
        """
        Send email alert via SendGrid.

        Args:
            subject: Email subject
            html_body: HTML formatted email body

        Returns:
            True if successful, False otherwise
        """
        if not SENDGRID_AVAILABLE or not self.api_key:
            self.logger.warning("SendGrid not available or not configured")
            return False

        try:
            message = Mail(
                from_email=Email(self.from_email),
                to_emails=To(self.to_email),
                subject=subject,
                html_content=Content("text/html", html_body)
            )

            response = self.sg.send(message)

            if response.status_code in [200, 201, 202]:
                self.logger.info(f"Email alert sent successfully")
                return True
            else:
                self.logger.error(f"SendGrid returned {response.status_code}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")
            return False

    def format_alert_email(
        self,
        model: str,
        year: int,
        price: float,
        market_price: float,
        url: str,
        steal_indicators: list,
        confidence_score: float
    ) -> tuple[str, str]:
        """
        Format alert as email subject and HTML body.

        Returns:
            (subject, html_body)
        """
        savings = market_price - price if market_price else None
        savings_text = f"Save ${savings:,.0f}!" if savings else "Price TBD"

        subject = f"🏎️ PORSCHE ALERT: {year} {model} at ${price:,.0f}"

        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #d32f2f;">🏎️ Porsche Listing Match Found!</h2>

                <h3>{year} {model}</h3>

                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px;">
                    <p><strong>Price:</strong> ${price:,.0f}</p>
                    <p><strong>Market Value:</strong> ${market_price:,.0f}</p>
                    <p><strong>Savings:</strong> <span style="color: #4caf50; font-weight: bold;">{savings_text}</span></p>
                    <p><strong>Confidence:</strong> {confidence_score*100:.1f}%</p>
                </div>

                <h4>✓ Steal Indicators Met:</h4>
                <ul>
                    {''.join(f'<li>{indicator}</li>' for indicator in steal_indicators)}
                </ul>

                <p>
                    <a href="{url}" style="display: inline-block; background-color: #d32f2f; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                        View Listing
                    </a>
                </p>

                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="font-size: 12px; color: #999;">
                    This is an automated alert from your AI Exotic Car Agent.
                </p>
            </body>
        </html>
        """

        return subject, html_body
