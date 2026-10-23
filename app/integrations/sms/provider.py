from app.core.config import settings
from app.core.logging import logger

class SMSProvider:
    def __init__(self):
        self.provider = settings.SMS_PROVIDER

    def send_sms(self, phone_number: str, message: str) -> bool:
        logger.info(f"Dispatching SMS to {phone_number} | Message: {message[:30]}...")
        return True

sms_provider = SMSProvider()
