"""Settings management for Gmail Manager."""

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


@dataclass
class Settings:
    """Application settings loaded from .env file."""

    gmail_email: str
    gmail_app_password: str
    download_dir: Path
    imap_server: str = "imap.gmail.com"
    imap_port: int = 993

    def validate(self) -> tuple[bool, list[str]]:
        """Validate settings and return (is_valid, errors)."""
        errors = []

        if not self.gmail_email:
            errors.append("GMAIL_EMAIL is not set")
        elif "@" not in self.gmail_email:
            errors.append("GMAIL_EMAIL must be a valid email address")

        if not self.gmail_app_password:
            errors.append("GMAIL_APP_PASSWORD is not set")

        if not self.download_dir:
            errors.append("DOWNLOAD_DIR is not set")

        return len(errors) == 0, errors


def load_settings(env_path: Path | None = None) -> Settings:
    """Load settings from .env file.

    Args:
        env_path: Optional path to .env file. Defaults to project root.

    Returns:
        Settings object with loaded configuration.

    Raises:
        ValueError: If required settings are missing or invalid.
    """
    if env_path is None:
        # Look for .env in the project root (parent of src)
        env_path = Path(__file__).parent.parent.parent / ".env"

    load_dotenv(env_path)

    gmail_email = os.getenv("GMAIL_EMAIL", "").strip()
    gmail_app_password = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    download_dir_str = os.getenv("DOWNLOAD_DIR", "downloads").strip()

    # Resolve download directory relative to project root
    project_root = Path(__file__).parent.parent.parent
    download_dir = project_root / download_dir_str

    settings = Settings(
        gmail_email=gmail_email,
        gmail_app_password=gmail_app_password,
        download_dir=download_dir,
    )

    is_valid, errors = settings.validate()
    if not is_valid:
        raise ValueError("Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))

    return settings
