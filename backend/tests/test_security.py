from datetime import timedelta
import unittest

from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


class SecurityTests(unittest.TestCase):
    def test_password_hash_verification(self):
        password_hash = hash_password("correct-password")

        self.assertTrue(verify_password("correct-password", password_hash))
        self.assertFalse(verify_password("wrong-password", password_hash))
        self.assertNotIn("correct-password", password_hash)

    def test_access_token_round_trip_and_tamper_rejection(self):
        token = create_access_token(subject=123, expires_delta=timedelta(minutes=5))
        payload = decode_access_token(token)

        self.assertIsNotNone(payload)
        self.assertEqual(payload["sub"], "123")
        self.assertIsNone(decode_access_token(f"{token}tampered"))


if __name__ == "__main__":
    unittest.main()
