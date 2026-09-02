import unittest

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def login(email: str, password: str) -> str:
    response = client.post("/api/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class RecordsApiTests(unittest.TestCase):
    def test_health_check(self):
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_member_can_list_their_records(self):
        token = login("alice@example.test", "alice-password")

        response = client.get("/api/records", headers=auth_headers(token))

        self.assertEqual(response.status_code, 200)
        records = response.json()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["id"], "rec_alice_001")

    def test_member_can_read_their_record_notes(self):
        token = login("alice@example.test", "alice-password")

        response = client.get(
            "/api/records/rec_alice_001/notes", headers=auth_headers(token)
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["record_id"], "rec_alice_001")

    # Access-control regression test. Production coverage should use generated users,
    # records, and roles; this fixture-based test demonstrates the control's intent.
    def test_member_cannot_access_others_records(self):
        token = login("alice@example.test", "alice-password")

        response = client.get("/api/records/rec_bob_001", headers=auth_headers(token))

        self.assertIn(response.status_code, [403, 404])


if __name__ == "__main__":
    unittest.main()
