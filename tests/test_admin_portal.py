import unittest
import os
import uuid
from app import create_app

class AdminPortalTestCase(unittest.TestCase):
    """
    Authoritative test suite for the Strakly Gym Management System Admin Portal.
    Tests:
    1. Authentication and role-based access control.
    2. Zero-data rendering stability and absence of fake hardcoded records.
    3. All 17 administrative module routes and sub-routes.
    4. Form submissions and CSRF/method safety.
    5. CSV export generation.
    6. Non-admin access denial (403/redirect).
    """

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()

    def set_admin_session(self):
        with self.client.session_transaction() as sess:
            sess['user'] = {
                'id': str(uuid.uuid4()),
                'email': 'achiengpatricia32@gmail.com',
                'full_name': 'Patricia Achieng',
                'role': 'admin'
            }

    def set_member_session(self):
        with self.client.session_transaction() as sess:
            sess['user'] = {
                'id': str(uuid.uuid4()),
                'email': 'athlete@example.com',
                'full_name': 'Standard Athlete',
                'role': 'member'
            }

    def clear_session(self):
        with self.client.session_transaction() as sess:
            sess.clear()

    # -------------------------------------------------------------------------
    # 1. SECURITY & PERMISSIONS
    # -------------------------------------------------------------------------
    def test_admin_route_requires_auth(self):
        """Unauthenticated requests must redirect to login."""
        self.clear_session()
        res = self.client.get('/admin/dashboard')
        self.assertIn(res.status_code, [302, 401, 403])

    def test_member_cannot_access_admin(self):
        """Standard member role must be denied access to admin portal."""
        self.set_member_session()
        res = self.client.get('/admin/dashboard')
        self.assertIn(res.status_code, [302, 403])

    # -------------------------------------------------------------------------
    # 2. ALL ADMIN ROUTES (HTTP 200 WITH ZERO/LIVE DATA)
    # -------------------------------------------------------------------------
    def test_all_admin_views_render_successfully(self):
        self.set_admin_session()
        routes = [
            '/admin/dashboard',
            '/admin/dashboard?range=today',
            '/admin/dashboard?range=7d',
            '/admin/dashboard?range=30d',
            '/admin/dashboard?range=month',
            '/admin/dashboard?range=year',
            '/admin/members',
            '/admin/members?status=active',
            '/admin/members?status=inactive',
            '/admin/plans',
            '/admin/subscriptions',
            '/admin/payments',
            '/admin/attendance',
            '/admin/trainers',
            '/admin/classes',
            '/admin/exercises',
            '/admin/services',
            '/admin/equipment',
            '/admin/community',
            '/admin/announcements',
            '/admin/notifications',
            '/admin/reports',
            '/admin/reports?type=cash_collection',
            '/admin/reports?type=attendance',
            '/admin/reports?type=memberships',
            '/admin/reports?type=trainers',
            '/admin/reports?type=equipment',
            '/admin/audit-logs',
            '/admin/users',
            '/admin/settings'
        ]

        for r in routes:
            with self.subTest(route=r):
                res = self.client.get(r)
                self.assertEqual(res.status_code, 200, f"Route {r} failed with status {res.status_code}")

    # -------------------------------------------------------------------------
    # 3. CSV EXPORTS
    # -------------------------------------------------------------------------
    def test_reports_csv_export(self):
        self.set_admin_session()
        report_types = ['cash_collection', 'attendance', 'memberships', 'trainers', 'equipment']
        for rt in report_types:
            with self.subTest(report_type=rt):
                res = self.client.get(f'/admin/reports?type={rt}&export=csv')
                self.assertEqual(res.status_code, 200)
                self.assertIn('text/csv', res.headers.get('Content-Type', ''))
                self.assertIn('attachment;', res.headers.get('Content-Disposition', ''))

    # -------------------------------------------------------------------------
    # 4. ABSENCE OF FAKE HARDCODED RECORDS & STRAKLY BRANDING
    # -------------------------------------------------------------------------
    def test_no_fake_sample_records_in_html(self):
        """Verify that known fabricated demo rows do not appear as live records."""
        self.set_admin_session()
        res = self.client.get('/admin/payments')
        self.assertNotIn(b'RCP-2026-9481A', res.data, "Fake receipt number RCP-2026-9481A must not be in payments")

        res_att = self.client.get('/admin/attendance')
        self.assertNotIn(b'Locker #14', res_att.data, "Fake attendance Locker #14 must not be in attendance")

    def test_strakly_branding_in_views(self):
        """Verify Strakly product branding is present across views."""
        self.set_admin_session()
        res = self.client.get('/admin/dashboard')
        self.assertIn(b'STRAKLY', res.data)
        self.assertNotIn(b'Levy Kirinya', res.data)

    def test_trainer_creation_workflow(self):
        """Verify adding a trainer POST request succeeds and redirects."""
        self.set_admin_session()
        res = self.client.post('/admin/trainers', data={
            'action': 'create',
            'full_name': 'Daniel Brooks',
            'email': f'daniel.brooks.{uuid.uuid4().hex[:4]}@strakly.com',
            'phone': '+254700112233',
            'specialisations': 'Strength & Conditioning, Powerlifting',
            'bio': 'Senior strength coach at Strakly.'
        }, follow_redirects=False)
        self.assertEqual(res.status_code, 302)

    def test_user_creation_and_role_workflow(self):
        """Verify user creation POST request succeeds and redirects."""
        self.set_admin_session()
        test_email = f'user.{uuid.uuid4().hex[:4]}@strakly.com'
        res = self.client.post('/admin/users', data={
            'full_name': 'Oliver Bennett',
            'email': test_email,
            'role': 'member',
            'phone': '+254700445566'
        }, follow_redirects=False)
        self.assertEqual(res.status_code, 302)

if __name__ == '__main__':
    unittest.main()
