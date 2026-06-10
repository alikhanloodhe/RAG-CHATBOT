import logging

from app.core.config import settings


def configure_logging() -> None:
    """Configures the global logging setup for the application using standard format schemas."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logging.getLogger("app").info("Logging configured", extra={"app_env": settings.APP_ENV})
