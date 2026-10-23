from typing import Optional
from app.core.config import settings
from app.core.logging import logger

class EmailProvider:
    def __init__(self):
        self.enabled = settings.SMTP_ENABLED

    def send_email(self, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> bool:
        logger.info(f"Dispatching email to {to_email} | Subject: {subject}")
        # In real production with SMTP_ENABLED, connect to smtplib
        return True

email_provider = EmailProvider()
