import unittest
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message="Using `httpx` with `starlette.testclient`.*")
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.health import router as health_router


class ApiTests(unittest.TestCase):
    def test_health_endpoint_is_liveness_only(self):
        app = FastAPI()
        app.include_router(health_router, prefix="/api/v1")

        response = TestClient(app).get("/api/v1/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertNotIn("services", response.json())


if __name__ == "__main__":
    unittest.main()
