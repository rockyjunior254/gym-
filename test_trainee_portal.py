#!/usr/bin/env python3
import unittest
from app import create_app

class TraineePortalTestSuite(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        # Simulate authenticated member session with real profile ID
        with self.client.session_transaction() as sess:
            sess['user'] = {
                'id': 'a232d420-da81-447c-b2e2-6eb1ad21c1ab',
                'email': 'rockyjunior254@gmail.com',
                'full_name': 'Rocky Junior',
                'role': 'member',
                'phone': '+254700000000'
            }

    def test_01_trainee_routes_render_200(self):
        routes = [
            '/member/dashboard',
            '/member/profile',
            '/member/membership',
            '/member/workouts',
            '/member/exercises',
            '/member/calendar',
            '/member/trainer',
            '/member/classes',
            '/member/progress',
            '/member/challenges',
            '/member/gear',
            '/member/store',
            '/member/services',
            '/member/payments',
            '/member/attendance',
            '/member/notifications',
            '/member/support',
            '/member/settings'
        ]

        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(
                    response.status_code, 200,
                    f"Route {route} failed to return HTTP 200 (Got {response.status_code})"
                )
                self.assertIn(b'STRAKLY', response.data)
                self.assertIn(b'ATHLETE', response.data)
                print(f"  [PASS] {route} -> 200 OK")

    def test_02_member_profile_update(self):
        res = self.client.post('/member/profile', data={
            'full_name': 'Patricia Achieng Updated',
            'phone': '+254700000000',
            'emergency_contact_name': 'Marcus Vance',
            'emergency_contact_phone': '+254711000000',
            'fitness_goals': 'Strength, Hypertrophy, Mobility'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'updated successfully', res.data)
        print("  [PASS] Profile update form works cleanly")

    def test_03_member_workout_log(self):
        res = self.client.post('/member/workouts', data={
            'title': 'Heavy Deadlift & Grip Workout',
            'duration_minutes': '75',
            'notes': '5x5 at 140kg, RPE 8'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'logged successfully', res.data)
        print("  [PASS] Workout logging form works cleanly")

    def test_04_member_support_ticket(self):
        res = self.client.post('/member/support', data={
            'category': 'membership',
            'subject': 'Inquiry regarding locker rental',
            'message': 'Do we have permanent lockers available on the first floor?',
            'priority': 'normal'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'logged', res.data)
        print("  [PASS] Support ticket creation works cleanly")

    def test_05_member_settings_update(self):
        res = self.client.post('/member/settings', data={
            'notify_email': 'on',
            'notify_class_reminders': 'on',
            'share_progress_with_coach': 'on'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Account preferences updated', res.data)
        print("  [PASS] Member settings update works cleanly")

if __name__ == '__main__':
    print("\n=======================================================")
    print("RUNNING STRAKLY TRAINEE PORTAL END-TO-END TEST SUITE")
    print("=======================================================")
    unittest.main()
