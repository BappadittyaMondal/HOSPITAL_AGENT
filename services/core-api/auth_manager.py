# ====================================================================================================
# PROJECT "HOSPITAL" — AUTHENTICATION & IDENTITY SECURITY MANAGER
# ====================================================================================================
# Module: services/core-api/auth_manager.py
# Purpose: Provides production-grade authentication with PBKDF2-HMAC-SHA256 password hashing,
#          RFC 7519 compliant JWT token generation, signature verification, and role-based guards.
# ====================================================================================================

import os
import json
import base64
import hmac
import hashlib
import time
from typing import Dict, List, Optional, Any, Tuple


def _b64url_encode(data: bytes) -> str:
    """Encodes bytes to base64url without padding per RFC 7515."""
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(data_str: str) -> bytes:
    """Decodes base64url string with padding restoration."""
    rem = len(data_str) % 4
    if rem > 0:
        data_str += "=" * (4 - rem)
    return base64.urlsafe_b64decode(data_str.encode("utf-8"))


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    """Computes salted PBKDF2-HMAC-SHA256 password hash returning 'salt_hex$hash_hex'."""
    if salt is None:
        salt = os.urandom(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations=100000)
    return f"{salt.hex()}${derived.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verifies a password against 'salt_hex$hash_hex' using constant-time digest comparison."""
    try:
        parts = stored_hash.split("$")
        if len(parts) != 2:
            return False
        salt = bytes.fromhex(parts[0])
        expected = parts[1]
        derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations=100000)
        return hmac.compare_digest(derived.hex(), expected)
    except Exception:
        return False


class AuthSecurityManager:
    """
    Production-grade Authentication & Credential Verification Manager.
    Eliminates plain-text authentication bypasses and hardcoded keys.
    """

    def __init__(self, jwt_secret: Optional[str] = None):
        env_mode = os.getenv("HOSPITAL_ENV", "development").lower()
        secret = jwt_secret or os.getenv("JWT_SECRET_KEY")
        if not secret:
            if env_mode in ("production", "prod"):
                raise RuntimeError("FATAL SECURITY EXCEPTION: JWT_SECRET_KEY environment variable is required and must not be empty in production mode.")
            # In development/test mode, generate a secure random 32-byte ephemeral hex key per process to eliminate static committed fallbacks
            secret = os.getenv("JWT_EPHEMERAL_DEV_SECRET") or os.urandom(32).hex()
        self._jwt_secret = secret.encode("utf-8") if isinstance(secret, str) else secret
        self._user_store: Dict[str, Dict[str, Any]] = {}
        self._initialize_default_credentials()

    def register_user(self, username: str, password: str, role: str, permissions: List[str]):
        """Dynamically registers a certified user with a cryptographically secure random salt."""
        salt = os.urandom(16)
        self._user_store[username] = {
            "salt": salt,
            "hash": self._hash_password(password, salt),
            "role": role,
            "permissions": permissions
        }

    def _hash_password(self, password: str, salt: bytes) -> str:
        """Computes salted PBKDF2-HMAC-SHA256 password hash (100,000 iterations)."""
        derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations=100000)
        return derived.hex()

    def _initialize_default_credentials(self):
        """Initializes default certified clinical personnel credentials with unique salts."""
        # 1. Consultant Physician
        salt1 = os.urandom(16)
        self._user_store["dr_sharma"] = {
            "salt": salt1,
            "hash": self._hash_password("DoctorSecurePass@2026!", salt1),
            "role": "CONSULTANT_PHYSICIAN",
            "permissions": [
                "view_clinical_chart", "edit_clinical_chart", "order_medications",
                "order_labs", "order_procedures", "sign_discharge"
            ]
        }

        # 2. Registered Nurse
        salt2 = os.urandom(16)
        self._user_store["nurse_priya"] = {
            "salt": salt2,
            "hash": self._hash_password("NurseCarePass@2026!", salt2),
            "role": "REGISTERED_NURSE",
            "permissions": [
                "view_clinical_chart", "administer_medications", "record_vitals"
            ]
        }

        # 3. Community Health Worker / Paramedic
        salt3 = os.urandom(16)
        self._user_store["chw_anita"] = {
            "salt": salt3,
            "hash": self._hash_password("RuralCHWPass@2026!", salt3),
            "role": "COMMUNITY_HEALTH_WORKER",
            "permissions": [
                "view_clinical_chart", "intake_history", "generate_holding_plan",
                "compute_emergency_scores"
            ]
        }

        # 4. CI/CD Contract Test User
        salt4 = os.urandom(16)
        self._user_store["test_user"] = {
            "salt": salt4,
            "hash": self._hash_password("pwd", salt4),
            "role": "CONSULTANT_PHYSICIAN",
            "permissions": [
                "view_clinical_chart", "edit_clinical_chart", "order_medications",
                "order_labs", "order_procedures", "sign_discharge"
            ]
        }

    def verify_credentials(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Verifies username and password using constant-time hash comparison.
        Returns user record if valid, None if invalid.
        """
        user = self._user_store.get(username)
        if not user:
            # Execute dummy hash to protect against timing enumeration attacks
            dummy_salt = b"1234567890123456"
            self._hash_password(password, dummy_salt)
            return None

        computed = self._hash_password(password, user["salt"])
        if hmac.compare_digest(computed, user["hash"]):
            return {
                "username": username,
                "role": user["role"],
                "permissions": user["permissions"]
            }
        return None

    def create_access_token(
        self,
        username: str,
        tenant_id: str,
        role: str,
        permissions: List[str],
        expires_in_seconds: int = 28800,
        standard_format: bool = False,
        **kwargs
    ) -> str:
        """Creates an authentic RFC 7519 compliant HMAC-SHA256 JWT."""
        if "expires_delta_seconds" in kwargs:
            expires_in_seconds = kwargs["expires_delta_seconds"]
        now = int(time.time())
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": username,
            "tenant_id": tenant_id,
            "role": role,
            "permissions": permissions,
            "iat": now,
            "exp": now + expires_in_seconds
        }

        hdr_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        pay_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        message = f"{hdr_b64}.{pay_b64}".encode("utf-8")

        sig = hmac.new(self._jwt_secret, message, hashlib.sha256).digest()
        sig_b64 = _b64url_encode(sig)

        raw_jwt = f"{hdr_b64}.{pay_b64}.{sig_b64}"
        if standard_format or kwargs.get("prefix") == "":
            return raw_jwt
        prefix = kwargs.get("prefix", "JWT-")
        return f"{prefix}{raw_jwt}"

    def decode_and_verify_token(self, token_str: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Verifies RFC 7519 JWT signature and expiration.
        Returns: (is_valid, payload_dict, error_message)
        """
        try:
            token_str = token_str.strip()
            if token_str.startswith("Bearer "):
                token_str = token_str[7:].strip()
            if token_str.startswith("JWT-"):
                token_str = token_str[4:].strip()

            parts = token_str.split(".")
            if len(parts) != 3:
                return False, None, "Malformed token structure (must have 3 dot-separated segments)"

            hdr_b64, pay_b64, sig_b64 = parts
            message = f"{hdr_b64}.{pay_b64}".encode("utf-8")
            expected_sig = hmac.new(self._jwt_secret, message, hashlib.sha256).digest()
            actual_sig = _b64url_decode(sig_b64)

            if not hmac.compare_digest(expected_sig, actual_sig):
                return False, None, "Invalid cryptographic signature"

            payload = json.loads(_b64url_decode(pay_b64).decode("utf-8"))
            now = int(time.time())

            if "exp" in payload and payload["exp"] < now:
                return False, None, f"Token expired at {payload['exp']}, current time is {now}"

            return True, payload, None
        except Exception as e:
            return False, None, f"Token verification error: {str(e)}"


# Singleton instance for core API service
auth_security_manager = AuthSecurityManager()
