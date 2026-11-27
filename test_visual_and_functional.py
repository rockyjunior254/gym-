import unittest
from app import create_app

class StraklyFullSystemVerification(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

    def test_admin_dashboard_exact_greeting(self):
        with self.client.session_transaction() as sess:
            sess['user'] = {
                'id': 'b16ba989-8b00-40e3-ad82-9b6e397342a3',
                'email': 'achiengpatricia32@gmail.com',
                'full_name': 'Patricia Achieng',
                'role': 'admin'
            }
        resp = self.client.get('/admin/dashboard')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        
        # Verify professional enterprise dashboard header (no hardcoded codes/unwanted greetings)
        self.assertIn("Business Overview", html)
        self.assertNotIn("CCS/00104/022", html)
        self.assertNotIn("WELCOME, PATRICIA ACHIENG", html)
        print("✓ Admin dashboard enterprise header verified (unwanted strings successfully removed).")

    def test_trainee_portal_stability(self):
        with self.client.session_transaction() as sess:
            sess['user'] = {
                'id': 'b16ba989-8b00-40e3-ad82-9b6e397342a3',
                'email': 'member@strakly.com',
                'full_name': 'Test Trainee',
                'role': 'member'
            }
        trainee_routes = [
            '/member/dashboard',
            '/community/',
            '/member/notifications',
            '/member/settings',
            '/member/workouts',
            '/member/classes',
            '/member/trainer',
            '/member/membership'
        ]
        for route in trainee_routes:
            with self.subTest(route=route):
                resp = self.client.get(route)
                self.assertEqual(resp.status_code, 200, f"Trainee route {route} failed with {resp.status_code}")
                print(f"✓ Trainee route {route} returned 200 OK.")

if __name__ == '__main__':
    unittest.main()
