import os
import sys
import unittest
import json
import uuid
from datetime import datetime, timezone, timedelta

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import (
    app, db, User, ResumeAnalysis, MCQSession, CodingAssessment,
    InterviewJourney, CertificateRecord, bcrypt, get_user_dashboard_stats
)

class DashboardProductionRealTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        cls.client = app.test_client()

        with app.app_context():
            db.create_all()

    def create_isolated_user(self, prefix, domain="Full Stack Development"):
        with app.app_context():
            unique_suffix = uuid.uuid4().hex[:8]
            username = f"{prefix}_{unique_suffix}"
            u = User(
                username=username,
                email=f"{username}@dashboardtest.com",
                password_hash=bcrypt.generate_password_hash("Pass123!").decode('utf-8'),
                selected_domain=domain
            )
            db.session.add(u)
            db.session.commit()
            return u.id

    def login_user(self, user_id):
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(user_id)
            sess['user_id'] = user_id
            sess['_fresh'] = True

    def test_case_a_new_user_no_results(self):
        """Case A: New user with no assessment data shows pure empty state."""
        user_id = self.create_isolated_user("dash_case_a_user")
        self.login_user(user_id)

        with app.app_context():
            user = User.query.get(user_id)
            stats = get_user_dashboard_stats(user)

            self.assertIsNone(stats['average_score'])
            self.assertEqual(stats['sessions_completed'], 0)
            self.assertIsNone(stats['peak_score'])
            self.assertEqual(stats['resume_status'], 'Pending')
            self.assertIsNone(stats['ats_score'])
            self.assertIsNone(stats['domain_score'])
            self.assertEqual(stats['today_completed'], 0)
            self.assertEqual(stats['today_goal'], 3)
            self.assertEqual(stats['chart_labels'], [])
            self.assertEqual(stats['chart_data'], [])

        # Check HTML rendering
        resp = self.client.get('/dashboard')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')

        self.assertIn('No assessment data yet', html)
        self.assertIn('Upload your resume to begin', html)
        self.assertIn('0</strong><small>of 3</small>', html)
        self.assertNotIn('100%', html)

        # Check /api/dashboard endpoint
        api_resp = self.client.get('/api/dashboard')
        self.assertEqual(api_resp.status_code, 200)
        data = api_resp.get_json()
        self.assertIsNone(data['average_score'])
        self.assertEqual(data['sessions_completed'], 0)
        self.assertEqual(data['resume']['status'], 'Pending')

    def test_case_b_user_with_resume_only(self):
        """Case B: User with resume analyzed (85%) shows resume completed."""
        user_id = self.create_isolated_user("dash_case_b_user")
        self.login_user(user_id)

        with app.app_context():
            rec = ResumeAnalysis(
                user_id=user_id,
                job_role="Full Stack Development",
                ats_score=85.0,
                analysis_json=json.dumps({"ats_score": 85.0, "summary": "Strong dev"}),
                status="completed",
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(rec)
            db.session.commit()

            user = User.query.get(user_id)
            stats = get_user_dashboard_stats(user)

            self.assertEqual(stats['sessions_completed'], 0)
            self.assertIsNone(stats['average_score'])
            self.assertEqual(stats['resume_status'], 'Completed')
            self.assertEqual(stats['ats_score'], 85.0)
            self.assertEqual(stats['domain_score'], 85.0)
            self.assertEqual(stats['today_completed'], 1)

        resp = self.client.get('/dashboard')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('85%', html)
        self.assertIn('Completed', html)

    def test_case_c_user_with_resume_and_aptitude(self):
        """Case C: User with resume (85%) + aptitude (82%) unlocks Coding."""
        user_id = self.create_isolated_user("dash_case_c_user")
        self.login_user(user_id)

        with app.app_context():
            # 1. Resume 85%
            rec = ResumeAnalysis(
                user_id=user_id,
                job_role="Full Stack Development",
                ats_score=85.0,
                analysis_json=json.dumps({"ats_score": 85.0}),
                status="completed",
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(rec)
            # 2. Aptitude MCQ 82%
            mcq = MCQSession(
                user_id=user_id,
                domain="Full Stack Development",
                score=82,
                total_questions=20,
                correct_answers=16,
                wrong_answers=4,
                difficulty="medium",
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                time_taken_seconds=900
            )
            db.session.add(mcq)
            db.session.commit()

            user = User.query.get(user_id)
            stats = get_user_dashboard_stats(user)

            self.assertEqual(stats['sessions_completed'], 1)
            self.assertEqual(stats['average_score'], 82.0)
            self.assertEqual(stats['peak_score'], 82.0)
            self.assertEqual(stats['resume_status'], 'Completed')
            self.assertEqual(stats['ats_score'], 85.0)
            self.assertEqual(stats['domain_score'], round((82 + 85) / 2, 1))
            self.assertEqual(stats['today_completed'], 2)  # resume + aptitude

            # Stepper check: Stage 1 Completed, Stage 2 Completed, Stage 3 Unlocked
            journey = stats['journey']
            self.assertTrue(journey['resume']['completed'])
            self.assertTrue(journey['aptitude']['completed'])
            self.assertTrue(journey['coding']['unlocked'])
            self.assertFalse(journey['certificate']['unlocked'])

        resp = self.client.get('/dashboard')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('82%', html)
        self.assertIn('85%', html)

    def test_case_d_user_with_resume_aptitude_coding(self):
        """Case D: User with resume (85%) + aptitude (82%) + coding (76%)."""
        user_id = self.create_isolated_user("dash_case_d_user")
        self.login_user(user_id)

        now = datetime.now(timezone.utc)
        with app.app_context():
            rec = ResumeAnalysis(
                user_id=user_id,
                job_role="Full Stack Development",
                ats_score=85.0,
                analysis_json=json.dumps({"ats_score": 85.0}),
                status="completed",
                created_at=now
            )
            db.session.add(rec)

            mcq = MCQSession(
                user_id=user_id,
                domain="Full Stack Development",
                score=82,
                total_questions=20,
                correct_answers=16,
                wrong_answers=4,
                difficulty="medium",
                start_time=now,
                end_time=now,
                time_taken_seconds=900
            )
            db.session.add(mcq)

            coding = CodingAssessment(
                user_id=user_id,
                role="Full Stack Engineer",
                domain="Full Stack Development",
                difficulty="Medium",
                total_questions=5,
                questions_solved=4,
                overall_score=76.0,
                submitted_at=now
            )
            db.session.add(coding)
            db.session.commit()

            user = User.query.get(user_id)
            stats = get_user_dashboard_stats(user)

            self.assertEqual(stats['sessions_completed'], 2)
            self.assertEqual(stats['average_score'], round((82 + 76) / 2, 1))  # 79.0
            self.assertEqual(stats['peak_score'], 82.0)
            self.assertEqual(stats['domain_score'], round((82 + 76 + 85) / 3, 1))  # 81.0

            journey = stats['journey']
            self.assertTrue(journey['resume']['completed'])
            self.assertTrue(journey['aptitude']['completed'])
            self.assertTrue(journey['coding']['completed'])
            self.assertTrue(journey['certificate']['unlocked'])

        resp = self.client.get('/dashboard')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('79%', html)
        self.assertIn('82%', html)

    def test_case_e_user_with_certificate(self):
        """Case E: User with completed certificate shows unlocked credential."""
        user_id = self.create_isolated_user("dash_case_e_user")
        self.login_user(user_id)

        now = datetime.now(timezone.utc)
        with app.app_context():
            rec = ResumeAnalysis(
                user_id=user_id,
                job_role="Full Stack Development",
                ats_score=90.0,
                analysis_json=json.dumps({"ats_score": 90.0}),
                status="completed",
                created_at=now
            )
            db.session.add(rec)
            mcq = MCQSession(
                user_id=user_id,
                domain="Full Stack Development",
                score=88,
                total_questions=20,
                correct_answers=18,
                wrong_answers=2,
                difficulty="medium",
                start_time=now,
                end_time=now,
                time_taken_seconds=900
            )
            db.session.add(mcq)
            coding = CodingAssessment(
                user_id=user_id,
                domain="Full Stack Development",
                total_questions=5,
                questions_solved=5,
                overall_score=92.0,
                submitted_at=now
            )
            db.session.add(coding)
            cert_id = f"IA-{uuid.uuid4().hex[:10].upper()}"
            cert = CertificateRecord(
                certificate_id=cert_id,
                user_id=user_id,
                candidate_name="Case E Candidate",
                domain="Full Stack Development",
                ats_score=90.0,
                aptitude_score=88,
                coding_score=92.0,
                issue_date=now
            )
            db.session.add(cert)
            db.session.commit()

        resp = self.client.get('/dashboard')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')

        self.assertIn('View Certificate', html)
        self.assertIn(cert_id, html)

        # Refresh dashboard and verify consistent data
        refresh_resp = self.client.get('/dashboard')
        self.assertEqual(refresh_resp.status_code, 200)
        self.assertEqual(resp.data, refresh_resp.data)

if __name__ == '__main__':
    unittest.main()
