"""Tests for Fernet encryption utility."""

import os
from unittest.mock import patch

import pytest
from cryptography.fernet import InvalidToken


class TestEncryption:
    """Test encrypt_value and decrypt_value round-trip."""

    def setup_method(self):
        os.environ.setdefault("ENCRYPTION_MASTER_KEY", "")
        from utils.encryption import encrypt_value, decrypt_value
        self.encrypt = encrypt_value
        self.decrypt = decrypt_value

    def test_round_trip(self):
        plaintext = "secret-Ix0bVV0oVB19U8v6GRJtlrx6k"
        encrypted = self.encrypt(plaintext)
        assert encrypted != plaintext
        assert self.decrypt(encrypted) == plaintext

    def test_different_inputs_different_outputs(self):
        a = self.encrypt("key-one")
        b = self.encrypt("key-two")
        assert a != b

    def test_empty_string(self):
        encrypted = self.encrypt("")
        assert self.decrypt(encrypted) == ""

    def test_unicode(self):
        plaintext = "unicode-key-éèê"
        assert self.decrypt(self.encrypt(plaintext)) == plaintext

    def test_invalid_ciphertext_raises(self):
        with pytest.raises((InvalidToken, Exception)):
            self.decrypt("not-valid-base64-ciphertext")

    def test_long_value(self):
        plaintext = "x" * 10000
        assert self.decrypt(self.encrypt(plaintext)) == plaintext
