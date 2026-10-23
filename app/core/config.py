import os
from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, field_validator


class Settings(BaseSettings):
    PROJECT_NAME: str = "ShopSphere Pro"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "mysql+pymysql://root:aman2004@localhost:3306/shopsphere_pro_db"
    TEST_DATABASE_URL: str = "mysql+pymysql://root:aman2004@localhost:3306/shopsphere_pro_test_db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # Security
    SECRET_KEY: str = "shopsphere_pro_super_secret_jwt_key_for_production_and_testing_change_me_in_prod"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Stripe Payment Gateway
    STRIPE_SECRET_KEY: str = "sk_test_shopsphere_mock_sandbox_key"
    STRIPE_WEBHOOK_SECRET: str = "whsec_shopsphere_mock_sandbox_secret"
    STRIPE_PUBLISHABLE_KEY: str = "pk_test_shopsphere_mock_key"

    # SMTP / Email
    SMTP_HOST: str = "smtp.mailtrap.io"
    SMTP_PORT: int = 587
    SMTP_USER: str = "test_smtp_user"
    SMTP_PASSWORD: str = "test_smtp_password"
    SMTP_FROM_EMAIL: str = "noreply@shopspherepro.com"
    SMTP_FROM_NAME: str = "ShopSphere Pro"
    SMTP_ENABLED: bool = False

    # SMS
    SMS_PROVIDER: str = "sandbox"
    SMS_API_KEY: str = "sandbox_sms_api_key"
    SMS_SENDER_ID: str = "ShopSphere"

    # Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    # Super Admin Seed
    SUPER_ADMIN_EMAIL: str = "superadmin@shopsphere.com"
    SUPER_ADMIN_PASSWORD: str = "SuperAdmin123!"
    SUPER_ADMIN_FULL_NAME: str = "Super Administrator"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
