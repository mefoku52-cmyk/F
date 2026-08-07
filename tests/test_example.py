import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_example():
    assert True


def test_password_service():
    try:
        from cli.shared.application.passwords import PasswordService

        password = "secure_password123"
        hashed = PasswordService.hash_password(password)
        assert PasswordService.verify_password(password, hashed)
        assert not PasswordService.verify_password("wrong", hashed)
    except ImportError:
        pytest.skip("PasswordService not available")
