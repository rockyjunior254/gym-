import sys
import unittest
from app import create_app

class AdminCrudTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        with self.client.session_transaction() as sess:
            sess['user'] = {
                'id': 'b16ba989-8b00-40e3-ad82-9b6e397342a3',
                'email': 'achiengpatricia32@gmail.com',
                'full_name': 'Admin Patricia',
                'role': 'admin'
            }

    def test_all_18_routes_render(self):
        routes = [
            '/admin/dashboard',
            '/admin/members',
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
            '/admin/audit-logs',
            '/admin/users',
            '/admin/settings'
        ]
        for route in routes:
            with self.subTest(route=route):
                resp = self.client.get(route)
                self.assertEqual(resp.status_code, 200, f"Route {route} failed with {resp.status_code}")
                # Verify Strakly branding is present
                self.assertIn(b'Strakly', resp.data)
                # Ensure no old Levy Kirinya branding
                self.assertNotIn(b'Levy Kirinya', resp.data)

    def test_ui_controls_presence(self):
        # 1. Members
        resp = self.client.get('/admin/members')
        self.assertIn(b'openEditMemberModal', resp.data)
        self.assertIn(b'editMemberModal', resp.data)
        self.assertIn(b'/admin/members/delete/', resp.data)
        
        # 2. Plans
        resp = self.client.get('/admin/plans')
        self.assertIn(b'openEditPlanModal', resp.data)
        self.assertIn(b'editPlanModal', resp.data)

        # 3. Subscriptions
        resp = self.client.get('/admin/subscriptions')
        self.assertIn(b'openRenewSubModal', resp.data)
        self.assertIn(b'renewSubModal', resp.data)

        # 4. Services
        resp = self.client.get('/admin/services')
        self.assertIn(b'openEditServiceModal', resp.data)
        self.assertIn(b'editServiceModal', resp.data)

        # 5. Exercises
        resp = self.client.get('/admin/exercises')
        self.assertIn(b'openEditExerciseModal', resp.data)
        self.assertIn(b'editExerciseModal', resp.data)

        # 6. Classes
        resp = self.client.get('/admin/classes')
        self.assertIn(b'openEditClassModal', resp.data)
        self.assertIn(b'editClassModal', resp.data)

        # 7. Attendance
        resp = self.client.get('/admin/attendance')
        self.assertIn(b'Actions', resp.data)

        # 8. Announcements
        resp = self.client.get('/admin/announcements')
        self.assertIn(b'openEditAnnModal', resp.data)
        self.assertIn(b'editAnnouncementModal', resp.data)

        # 9. Users
        resp = self.client.get('/admin/users')
        self.assertIn(b'openEditUserModal', resp.data)
        self.assertIn(b'editUserModal', resp.data)

if __name__ == '__main__':
    unittest.main()
