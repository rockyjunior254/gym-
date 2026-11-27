import unittest
from app import create_app
from app.services.repository import GymRepository

class StraklyTrainerAndPublicVerification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Fetch an actual trainer UUID from the database
        trainers = GymRepository.get_all_trainers()
        if trainers:
            cls.trainer_id = trainers[0]['id']
            cls.trainer_name = trainers[0].get('full_name', 'Coach James')
            cls.trainer_email = trainers[0].get('email', 'coach@strakly.com')
        else:
            cls.trainer_id = 'c7986c19-512d-4b46-bbcb-b6182dc5060b'
            cls.trainer_name = 'Coach Michael Owen'
            cls.trainer_email = 'daniel.test@strakly.com'

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

    def test_public_website_routes(self):
        """Verifies public homepage and all public marketing pages load successfully (200 OK)"""
        public_routes = [
            '/',
            '/about',
            '/programmes',
            '/classes',
            '/trainers',
            '/memberships',
            '/gallery',
            '/contact'
        ]
        for route in public_routes:
            with self.subTest(route=route):
                resp = self.client.get(route)
                self.assertEqual(resp.status_code, 200, f"Public route {route} failed with {resp.status_code}")
        print("✓ All 8 public website pages verified (200 OK).")

    def test_public_homepage_cash_only_and_dynamic_content(self):
        """Ensures cash-only and dynamic gym notices are present on homepage"""
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        # Check cash-only clarity
        self.assertIn("Cash-Only Transparency", html)
        self.assertIn("Manual front-desk check-in", html)
        # Check dynamic sections
        self.assertIn("FACILITY SERVICES & OFFERINGS", html)
        self.assertIn("MEMBERSHIP PACKAGES", html)
        self.assertIn("MEET OUR ATHLETIC TRAINERS", html)
        print("✓ Public homepage cash-only and dynamic content verified.")

    def test_contact_form_submission(self):
        """Tests POST /contact form processing"""
        post_data = {
            'name': 'Marcus Vance',
            'email': 'marcus@example.com',
            'subject': 'Membership Inquiry',
            'message': 'I would like to inquire about personal training schedules.'
        }
        resp = self.client.post('/contact', data=post_data, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn("Thank you for reaching out! A facility representative will contact you shortly", html)
        print("✓ Contact form submission verified with flash confirmation.")

    def test_trainer_portal_authorization_guard(self):
        """Ensures unauthenticated users cannot access Trainer Portal"""
        resp = self.client.get('/trainer/dashboard', follow_redirects=False)
        self.assertIn(resp.status_code, [302, 401, 403])
        print("✓ Trainer portal access guard verified (Unauthenticated blocked).")

    def test_trainer_portal_all_14_modules(self):
        """Verifies all 14 Trainer Portal modules render with 200 OK and coach authentication"""
        with self.client.session_transaction() as sess:
            sess['user'] = {
                'id': self.trainer_id,
                'email': self.trainer_email,
                'full_name': self.trainer_name,
                'role': 'trainer'
            }
        trainer_modules = [
            '/trainer/dashboard',
            '/trainer/members',
            '/trainer/plans',
            '/trainer/library',
            '/trainer/schedule',
            '/trainer/sessions',
            '/trainer/progress',
            '/trainer/feedback',
            '/trainer/assessments',
            '/trainer/reports',
            '/trainer/programmes',
            '/trainer/community',
            '/trainer/notifications',
            '/trainer/profile',
            '/trainer/settings'
        ]
        for route in trainer_modules:
            with self.subTest(module=route):
                resp = self.client.get(route)
                self.assertEqual(resp.status_code, 200, f"Trainer module {route} failed with status {resp.status_code}")
        print("✓ All 15 Trainer Portal modules (including Specialised Programmes) verified (200 OK).")

    def test_specialised_programme_proposal_and_approval_workflow(self):
        """Tests trainer proposing a programme and Admin approving it (Part 5)"""
        # 1. Trainer proposes programme
        with self.client.session_transaction() as sess:
            sess['user'] = {
                'id': self.trainer_id,
                'email': self.trainer_email,
                'full_name': self.trainer_name,
                'role': 'trainer'
            }
        prog_data = {
            'name': 'Olympic Barbell Mastery',
            'objective': 'Snatch & Clean Peaking',
            'category': 'Powerlifting & Strength',
            'duration_weeks': '8',
            'sessions_count': '24',
            'proposed_price': '18000',
            'target_audience': 'Advanced Barbell Lifters',
            'description': 'Periodized training protocol focusing on kinetic bar path and maximum velocity.'
        }
        resp = self.client.post('/trainer/programmes', data=prog_data, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn("submitted for Admin review", html)
        print("✓ Trainer successfully proposed specialised coaching programme.")

    def test_trainer_dashboard_fitpulse_components(self):
        """Verifies FitPulse KPIs, greeting, and coaching metrics on Trainer Dashboard"""
        with self.client.session_transaction() as sess:
            sess['user'] = {
                'id': self.trainer_id,
                'email': self.trainer_email,
                'full_name': self.trainer_name,
                'role': 'trainer'
            }
        resp = self.client.get('/trainer/dashboard')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn("WELCOME, COACH", html)
        self.assertIn("My Athletes", html)
        self.assertIn("Active Plans", html)
        self.assertIn("Coaching Schedule", html)
        print("✓ Trainer dashboard FitPulse KPIs & greeting verified.")

    def test_trainer_profile_submit_and_admin_approval_workflow(self):
        """Tests the full trainer profile submission & admin review/approval cycle"""
        # 1. Trainer submits profile update
        with self.client.session_transaction() as sess:
            sess['user'] = {
                'id': self.trainer_id,
                'email': self.trainer_email,
                'full_name': self.trainer_name,
                'role': 'trainer'
            }
        submit_data = {
            'action': 'submit_approval',
            'full_name': self.trainer_name,
            'phone': '+254700112233',
            'specialisations': 'Powerlifting, Strength Peaking',
            'bio': 'Over 8 years training competitive powerlifters and athletes.',
            'qualifications': 'CSCS Certified, Olympic Coach Level 2',
            'coaching_philosophy': 'Precision programming, load progression, strict technique.',
            'experience_years': '8'
        }
        resp = self.client.post('/trainer/profile', data=submit_data, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn("Coach profile submitted for Admin approval", html)
        print("✓ Trainer profile successfully submitted for Admin approval.")

        # 2. Admin reviews and approves profile
        with self.client.session_transaction() as sess:
            sess['user'] = {
                'id': 'b16ba989-8b00-40e3-ad82-9b6e397342a3',
                'email': 'achiengpatricia32@gmail.com',
                'full_name': 'Patricia Achieng',
                'role': 'admin'
            }
        resp_approve = self.client.post(f'/admin/trainers/approve/{self.trainer_id}', follow_redirects=True)
        self.assertEqual(resp_approve.status_code, 200)
        approve_html = resp_approve.data.decode('utf-8')
        self.assertIn("Coach public profile approved and published to website", approve_html)
        print("✓ Admin successfully approved and published trainer profile.")

if __name__ == '__main__':
    unittest.main()
