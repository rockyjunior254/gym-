"""
Comprehensive Test Suite for Cloudflare Turnstile Bot Protection in Strakly Gym System.

Covers:
- Test A: Successful verification (token accepted, auth proceeds)
- Test B: Missing token (blocked with friendly warning)
- Test C: Invalid token (blocked)
- Test D: Cloudflare API failure / Timeout (blocked, fail closed)
- Test E: Token exceeding 2048 chars (blocked)
- Test F: Invalid login credentials with valid token (Turnstile passes, auth fails)
- Test G: Successful login with valid token (Turnstile passes, session established, redirect works)
- Test H: Login page rendering (Turnstile JS present, site key dynamically injected, secret key absent)
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import requests
from app import create_app
from app.services.turnstile import verify_turnstile_token, TurnstileVerificationResult

class TestCloudflareTurnstileIntegration(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        self.expected_site_key = os.getenv('TURNSTILE_SITE_KEY', '').strip()

    # -------------------------------------------------------------------------
    # UNIT TESTS: Server-Side Turnstile Verification Service
    # -------------------------------------------------------------------------
    def test_verify_turnstile_missing_token(self):
        """Missing or empty token must be rejected immediately without calling Cloudflare."""
        with patch('requests.post') as mock_post:
            result = verify_turnstile_token("")
            self.assertFalse(result)
            self.assertIn("complete the human verification", result.error_message)
            mock_post.assert_not_called()

            result_none = verify_turnstile_token(None)
            self.assertFalse(result_none)
            mock_post.assert_not_called()

    def test_verify_turnstile_oversized_token(self):
        """Token exceeding 2048 characters must be rejected immediately."""
        oversized = "a" * 2049
        with patch('requests.post') as mock_post:
            result = verify_turnstile_token(oversized)
            self.assertFalse(result)
            self.assertIn("Human verification failed", result.error_message)
            mock_post.assert_not_called()

    @patch('requests.post')
    def test_verify_turnstile_success(self, mock_post):
        """Valid token with Cloudflare success: true must succeed."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'success': True,
            'challenge_ts': '2026-11-28T13:00:00Z',
            'hostname': 'localhost'
        }
        mock_post.return_value = mock_resp

        result = verify_turnstile_token("dummy-valid-token", remote_ip="127.0.0.1")
        self.assertTrue(result)
        self.assertTrue(bool(result))
        mock_post.assert_called_once()
        # Verify secret and response submitted
        call_kwargs = mock_post.call_args[1]
        self.assertEqual(call_kwargs['data']['response'], "dummy-valid-token")
        self.assertTrue('secret' in call_kwargs['data'])

    @patch('requests.post')
    def test_verify_turnstile_failure_invalid(self, mock_post):
        """Cloudflare response with success: false must fail."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'success': False,
            'error-codes': ['invalid-input-response']
        }
        mock_post.return_value = mock_resp

        result = verify_turnstile_token("invalid-token")
        self.assertFalse(result)
        self.assertIn("Human verification failed", result.error_message)

    @patch('requests.post')
    def test_verify_turnstile_failure_expired(self, mock_post):
        """Cloudflare response with timeout-or-duplicate must inform user."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'success': False,
            'error-codes': ['timeout-or-duplicate']
        }
        mock_post.return_value = mock_resp

        result = verify_turnstile_token("expired-token")
        self.assertFalse(result)
        self.assertIn("expired or was already used", result.error_message)

    @patch('requests.post')
    def test_verify_turnstile_api_timeout(self, mock_post):
        """Requests timeout must fail closed and report availability error."""
        mock_post.side_effect = requests.Timeout("Connection timed out")

        result = verify_turnstile_token("any-token")
        self.assertFalse(result)
        self.assertIn("timed out", result.error_message.lower())

    @patch('requests.post')
    def test_verify_turnstile_network_error(self, mock_post):
        """Network exception must fail closed and report temporary unavailability."""
        mock_post.side_effect = requests.ConnectionError("DNS failure")

        result = verify_turnstile_token("any-token")
        self.assertFalse(result)
        self.assertIn("temporarily unavailable", result.error_message)

    # -------------------------------------------------------------------------
    # INTEGRATION TESTS: Login Route & Template Behavior
    # -------------------------------------------------------------------------
    def test_login_page_renders_turnstile_elements(self):
        """GET /login must include official script, widget container, site key, and never secret key."""
        res = self.client.get('/login')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Check script URL
        self.assertIn('https://challenges.cloudflare.com/turnstile/v0/api.js', html)
        # Check widget class and attributes
        self.assertIn('class="cf-turnstile"', html)
        self.assertIn(f'data-sitekey="{self.expected_site_key}"', html)
        self.assertIn('data-action="login"', html)
        # Confirm secret key is NEVER leaked in page source
        secret_key = os.getenv('TURNSTILE_SECRET_KEY', '')
        if secret_key:
            self.assertNotIn(secret_key, html)

    def test_login_post_missing_turnstile_token(self):
        """POST /login without cf-turnstile-response must be rejected with 400."""
        res = self.client.post('/login', data={
            'email': 'athlete@strakly.com',
            'password': 'Password123!',
            'role_hint': 'member'
        })
        self.assertEqual(res.status_code, 400)
        html = res.data.decode('utf-8')
        self.assertIn('complete the human verification', html)
        # Ensure session was not created
        with self.client.session_transaction() as sess:
            self.assertNotIn('user', sess)

    @patch('app.routes.public.verify_turnstile_token')
    def test_login_post_failed_turnstile(self, mock_verify):
        """POST /login with failed verification must stop before authentication."""
        mock_verify.return_value = TurnstileVerificationResult(
            success=False,
            error_message="Human verification failed. Please try again."
        )

        res = self.client.post('/login', data={
            'email': 'athlete@strakly.com',
            'password': 'Password123!',
            'cf-turnstile-response': 'bogus-token',
            'role_hint': 'member'
        })
        self.assertEqual(res.status_code, 400)
        html = res.data.decode('utf-8')
        self.assertIn('Human verification failed', html)
        with self.client.session_transaction() as sess:
            self.assertNotIn('user', sess)

    @patch('app.routes.public.db_service')
    @patch('app.routes.public.verify_turnstile_token')
    def test_login_post_turnstile_pass_successful_auth(self, mock_verify, mock_db):
        """POST /login with successful verification and valid credentials logs in successfully."""
        mock_verify.return_value = TurnstileVerificationResult(success=True)
        mock_db.is_configured = True
        
        # Mock Supabase Auth sign_in_with_password
        mock_auth_res = MagicMock()
        mock_auth_res.user.id = '00000000-0000-0000-0000-000000000003'
        mock_db.client.auth.sign_in_with_password.return_value = mock_auth_res
        
        # Mock profiles table query
        mock_tbl = MagicMock()
        mock_tbl.select.return_value.eq.return_value.execute.return_value.data = [{
            'id': '00000000-0000-0000-0000-000000000003',
            'email': 'athlete@strakly.com',
            'full_name': 'Elena Rostova',
            'role': 'member',
            'avatar_url': None
        }]
        mock_db.get_table.return_value = mock_tbl

        res = self.client.post('/login', data={
            'email': 'athlete@strakly.com',
            'password': 'ValidPassword123!',
            'cf-turnstile-response': 'valid-test-token'
        }, follow_redirects=False)

        # Successfully redirects to member dashboard
        self.assertEqual(res.status_code, 302)
        self.assertIn('/member/dashboard', res.headers.get('Location', ''))

        with self.client.session_transaction() as sess:
            self.assertIn('user', sess)
            self.assertEqual(sess['user']['role'], 'member')

    @patch('app.routes.public.db_service')
    @patch('app.routes.public.verify_turnstile_token')
    def test_login_post_turnstile_pass_invalid_credentials(self, mock_verify, mock_db):
        """POST /login with successful Turnstile verification but invalid credentials fails auth gracefully."""
        mock_verify.return_value = TurnstileVerificationResult(success=True)
        mock_db.is_configured = True
        
        # Simulate Supabase auth invalid login error
        mock_db.client.auth.sign_in_with_password.side_effect = Exception("Invalid login credentials")

        res = self.client.post('/login', data={
            'email': 'wrong@strakly.com',
            'password': 'WrongPassword!',
            'cf-turnstile-response': 'valid-test-token'
        }, follow_redirects=False)

        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Authentication failed', html)
        with self.client.session_transaction() as sess:
            self.assertNotIn('user', sess)

    @patch('app.routes.public.db_service')
    @patch('app.routes.public.verify_turnstile_token')
    def test_login_post_turnstile_pass_admin_redirect(self, mock_verify, mock_db):
        """POST /login with admin credentials redirects to admin dashboard."""
        mock_verify.return_value = TurnstileVerificationResult(success=True)
        mock_db.is_configured = True
        
        mock_auth_res = MagicMock()
        mock_auth_res.user.id = '00000000-0000-0000-0000-000000000001'
        mock_db.client.auth.sign_in_with_password.return_value = mock_auth_res
        
        mock_tbl = MagicMock()
        mock_tbl.select.return_value.eq.return_value.execute.return_value.data = [{
            'id': '00000000-0000-0000-0000-000000000001',
            'email': 'admin@strakly.com',
            'full_name': 'Head Administrator',
            'role': 'admin',
            'avatar_url': None
        }]
        mock_db.get_table.return_value = mock_tbl

        res = self.client.post('/login', data={
            'email': 'admin@strakly.com',
            'password': 'AdminPassword123!',
            'cf-turnstile-response': 'valid-test-token'
        }, follow_redirects=False)

        self.assertEqual(res.status_code, 302)
        self.assertIn('/admin/dashboard', res.headers.get('Location', ''))

        with self.client.session_transaction() as sess:
            self.assertIn('user', sess)
            self.assertEqual(sess['user']['role'], 'admin')

if __name__ == '__main__':
    unittest.main()
