import unittest

from app.core.config import Settings


class ConfigTests(unittest.TestCase):
    def test_development_cors_origins_are_parsed(self):
        settings = Settings(APP_ENV="development", CORS_ORIGINS="http://localhost:5173,http://127.0.0.1:5173")

        self.assertEqual(
            settings.allowed_cors_origins,
            ["http://localhost:5173", "http://127.0.0.1:5173"],
        )

    def test_production_rejects_wildcard_cors(self):
        settings = Settings(APP_ENV="production", CORS_ORIGINS="*")

        with self.assertRaises(ValueError):
            settings.allowed_cors_origins

    def test_database_uri_is_built_from_local_postgres_settings(self):
        settings = Settings(
            POSTGRES_SERVER="localhost",
            POSTGRES_PORT=5432,
            POSTGRES_USER="postgres",
            POSTGRES_PASSWORD="postgres",
            POSTGRES_DB="rag_db",
        )

        self.assertEqual(
            settings.SQLALCHEMY_DATABASE_URI,
            "postgresql+asyncpg://postgres:postgres@localhost:5432/rag_db",
        )


if __name__ == "__main__":
    unittest.main()
