"""
OTP Provider — pluggable interface for sending OTPs.

To integrate a real SMS provider (MSG91, Fast2SMS, Twilio, etc.):
  1. Create a new class that extends BaseOTPProvider
  2. Implement the send_otp() method
  3. Change get_otp_provider() to return your new class

No other file needs to change.
"""

from abc import ABC, abstractmethod


# ─── Interface ────────────────────────────────────────────────────────────────

class BaseOTPProvider(ABC):
    @abstractmethod
    def send_otp(self, mobile: str, otp: str) -> bool:
        """
        Send OTP to the given mobile number.
        Returns True if sent successfully, False otherwise.
        """
        ...


# ─── Mock Provider (current) ─────────────────────────────────────────────────

class MockOTPProvider(BaseOTPProvider):
    """
    Development/testing provider.
    OTP is always 1234 — just logs to console, no real SMS sent.
    """
    FIXED_OTP = "1234"

    def send_otp(self, mobile: str, otp: str) -> bool:
        print(f"[MockOTPProvider] OTP for {mobile} → {otp}  (fixed: {self.FIXED_OTP})")
        return True


# ─── Future: Real SMS Provider Example ───────────────────────────────────────
# Uncomment and fill in when your client provides the SMS service credentials.
#
# class MSG91OTPProvider(BaseOTPProvider):
#     def __init__(self, api_key: str, template_id: str):
#         self.api_key = api_key
#         self.template_id = template_id
#
#     def send_otp(self, mobile: str, otp: str) -> bool:
#         import requests
#         response = requests.post(
#             "https://api.msg91.com/api/v5/otp",
#             json={"mobile": mobile, "otp": otp, "template_id": self.template_id},
#             headers={"authkey": self.api_key},
#         )
#         return response.status_code == 200


# ─── Factory — change provider here only ─────────────────────────────────────

def get_otp_provider() -> BaseOTPProvider:
    """
    Returns the active OTP provider.
    Switch to a real provider here when ready — nothing else changes.
    """
    return MockOTPProvider()
