"""
Cloudflare Turnstile Server-Side Verification Service
Official Documentation: https://developers.cloudflare.com/turnstile/get-started/server-side-validation/

Endpoint: https://challenges.cloudflare.com/turnstile/v0/siteverify
Validates:
1. cf-turnstile-response presence and maximum length (<= 2048 chars).
2. Secret key retrieval from environment variables.
3. Strict POST submission to Cloudflare Siteverify.
4. Fails closed on any network error, timeout, malformed payload, or verification failure.
5. Never logs full secret keys or full response tokens.
"""

import os
import logging
import requests

logger = logging.getLogger(__name__)

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
MAX_TOKEN_LENGTH = 2048
REQUEST_TIMEOUT_SECONDS = 10

class TurnstileVerificationResult:
    def __init__(self, success: bool, error_message: str = None, error_codes: list = None):
        self.success = success
        self.error_message = error_message
        self.error_codes = error_codes or []

    def __bool__(self):
        return self.success


def verify_turnstile_token(token: str, remote_ip: str = None) -> TurnstileVerificationResult:
    """
    Validates a Cloudflare Turnstile token server-side.
    Fails closed on missing token, network errors, timeouts, or failure responses.
    """
    secret_key = os.getenv('TURNSTILE_SECRET_KEY', '').strip()

    if not secret_key:
        logger.error("TURNSTILE_SECRET_KEY is not configured in environment variables.")
        return TurnstileVerificationResult(
            success=False,
            error_message="Security verification is temporarily unavailable. Please try again."
        )

    # 1. Validate token presence
    if not token or not str(token).strip():
        logger.warning("Turnstile verification failed: missing response token.")
        return TurnstileVerificationResult(
            success=False,
            error_message="Please complete the human verification before signing in."
        )

    token = str(token).strip()

    # 2. Validate token length constraint
    if len(token) > MAX_TOKEN_LENGTH:
        logger.warning(f"Turnstile verification failed: token exceeded max length ({len(token)} > {MAX_TOKEN_LENGTH}).")
        return TurnstileVerificationResult(
            success=False,
            error_message="Human verification failed. Please try again."
        )

    # 3. Submit payload to Cloudflare Siteverify
    payload = {
        'secret': secret_key,
        'response': token
    }
    if remote_ip:
        payload['remoteip'] = remote_ip

    token_preview = f"{token[:8]}...{token[-4:]}" if len(token) > 12 else "***"

    try:
        response = requests.post(
            SITEVERIFY_URL,
            data=payload,
            timeout=REQUEST_TIMEOUT_SECONDS
        )

        if response.status_code != 200:
            logger.error(f"Cloudflare Siteverify returned non-200 HTTP status: {response.status_code}")
            return TurnstileVerificationResult(
                success=False,
                error_message="Security verification is temporarily unavailable. Please try again."
            )

        data = response.json()
        is_success = bool(data.get('success', False))
        error_codes = data.get('error-codes', [])

        if is_success:
            logger.info(f"Turnstile verification succeeded for token [{token_preview}].")
            return TurnstileVerificationResult(success=True)
        else:
            logger.warning(f"Turnstile verification failed for token [{token_preview}]. Codes: {error_codes}")
            # Determine appropriate user-facing message based on error-codes if known
            if 'timeout-or-duplicate' in error_codes:
                user_msg = "Your verification has expired or was already used. Please verify again."
            else:
                user_msg = "Human verification failed. Please try again."

            return TurnstileVerificationResult(
                success=False,
                error_message=user_msg,
                error_codes=error_codes
            )

    except requests.Timeout:
        logger.error("Cloudflare Siteverify timed out after %s seconds.", REQUEST_TIMEOUT_SECONDS)
        return TurnstileVerificationResult(
            success=False,
            error_message="Security verification timed out. Please try again."
        )
    except requests.RequestException as exc:
        logger.error(f"Network error during Cloudflare Siteverify: {type(exc).__name__}")
        return TurnstileVerificationResult(
            success=False,
            error_message="Security verification is temporarily unavailable. Please try again."
        )
    except ValueError as exc:
        logger.error(f"Failed to parse Cloudflare Siteverify JSON response: {exc}")
        return TurnstileVerificationResult(
            success=False,
            error_message="Security verification is temporarily unavailable. Please try again."
        )
