# app/config.py
from pydantic_settings import BaseSettings
from typing import Optional, Set
from pydantic import Field

class Settings(BaseSettings):
    SECRET_KEY: str = Field("change-me-in-production")
    ALGORITHM: str = Field("HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7)

    DATABASE_URL: str
    SQLALCHEMY_DATABASE_URL: Optional[str] = None

    # IP Whitelist: comma-separated IPs. If empty or missing → allow any IP.
    OFFICE_IP_WHITELIST: Optional[str] = None

    model_config = {
        "env_file": ".env",
        "extra": "allow",
    }

    @property
    def effective_database_url(self) -> str:
        return self.SQLALCHEMY_DATABASE_URL or self.DATABASE_URL or "sqlite+aiosqlite:///./test.db"

    @property
    def allowed_ips(self) -> Optional[Set[str]]:
        """
        Returns:
          - None → no restriction (allow any IP)
          - Set[str] → only these IPs allowed
        """
        if not self.OFFICE_IP_WHITELIST:
            return None
        return {ip.strip() for ip in self.OFFICE_IP_WHITELIST.split(",") if ip.strip()}

settings = Settings()