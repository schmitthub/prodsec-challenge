import os

if os.getenv("PYTEST_CURRENT_TEST") is None and os.getenv("APP_ENV") != "test":
    raise RuntimeError("test fixtures must not be imported outside tests")


FIXTURE_JWT_SECRET = "unit-test-only-jwt-secret-not-used-in-runtime"
