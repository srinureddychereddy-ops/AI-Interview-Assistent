import unittest
import json
from datetime import datetime, timezone, timedelta
from app import app, db, User, UserProfile, ResumeAnalysis, MCQSession, CodingAssessment, CertificateRecord, InterviewJourney, normalize_canonical_domain

class ProductionReadyDataTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_landing_page_leaderboard_rendering(self):
        """Test landing page retrieves and displays top performers without errors."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        self.assertIn('Leaderboard', html)
        self.assertIn('Top Performers', html)

    def test_admin_console_routes(self):
        """Test admin console sections load with real data aggregates."""
        # Find an admin user or create a temporary one for testing
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            admin = User(username='test_admin', email='test_admin@test.com', password_hash='hash', role='admin')
            db.session.add(admin)
            db.session.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = admin.id
            sess['user_email'] = admin.email
            sess['user_name'] = admin.username
            sess['role'] = 'admin'
            sess['_user_id'] = str(admin.id)

        # 1. Admin Dashboard
        resp = self.client.get('/admin/dashboard')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('Total Users', html)
        self.assertIn('Resume Analyses', html)
        self.assertIn('Coding Attempts', html)
        self.assertIn('Certificates Issued', html)

        # 2. Admin Users Table
        resp = self.client.get('/admin/users')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('Selected Domain', html)
        self.assertIn('Journey Status', html)
        self.assertIn('Latest Score', html)

        # 3. Admin Resume Analyses
        resp = self.client.get('/admin/resumes')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('ATS Score', html)

        # 4. Admin Aptitude Assessments
        resp = self.client.get('/admin/aptitude-assessments')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('Aptitude Assessments', html)

        # 5. Admin Coding Round
        resp = self.client.get('/admin/coding-assessments')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('Coding Round Assessments', html)

        # 6. Admin Certificates
        resp = self.client.get('/admin/certificates')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('Issued Certificates', html)

    def test_resume_status_polling_endpoint(self):
        """Test the async resume status polling endpoint returns 404 for nonexistent task and valid JSON schema when authenticated."""
        user = User.query.filter_by(role='user').first()
        if user:
            with self.client.session_transaction() as sess:
                sess['user_id'] = user.id
                sess['user_email'] = user.email
                sess['user_name'] = user.username
                sess['role'] = user.role
                sess['_user_id'] = str(user.id)

            resp = self.client.get('/api/resume/status/nonexistent-task-id')
            self.assertEqual(resp.status_code, 404)
            data = resp.get_json()
            self.assertFalse(data['success'])

    def test_history_page_authenticated(self):
        """Test user history page renders with Coding Round tab."""
        user = User.query.filter_by(role='user').first()
        if user:
            with self.client.session_transaction() as sess:
                sess['user_id'] = user.id
                sess['user_email'] = user.email
                sess['user_name'] = user.username
                sess['role'] = user.role
                sess['_user_id'] = str(user.id)

            resp = self.client.get('/history')
            self.assertEqual(resp.status_code, 200)
            html = resp.data.decode('utf-8')
            self.assertIn('Coding Rounds', html)
            self.assertIn('Aptitude Assessments', html)
            self.assertIn('Resume Analyses', html)

    def test_profile_page_authenticated(self):
        """Test user profile page renders real stats and joined date."""
        user = User.query.filter_by(role='user').first()
        if user:
            with self.client.session_transaction() as sess:
                sess['user_id'] = user.id
                sess['user_email'] = user.email
                sess['user_name'] = user.username
                sess['role'] = user.role
                sess['_user_id'] = str(user.id)

            resp = self.client.get('/profile')
            self.assertEqual(resp.status_code, 200)
            html = resp.data.decode('utf-8')
            self.assertIn('Account Created', html)
            self.assertNotIn('Not Available', html if user.created_at else '')

if __name__ == '__main__':
    unittest.main()
