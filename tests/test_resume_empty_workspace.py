import os
import sys
import unittest
import json
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db, User, ResumeAnalysis, bcrypt, get_interview_journey_status, get_user_dashboard_stats

class ResumeEmptyWorkspaceTestCase(unittest.TestCase):
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
                email=f"{username}@resumetest.com",
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

    def test_fresh_visit_starts_empty_analyzer(self):
        """Part 13 A & I: Fresh visit to /resume displays EMPTY analyzer workspace, not latest analysis."""
        user_id = self.create_isolated_user("resume_fresh_user")
        self.login_user(user_id)

        # Give user an existing completed analysis record in DB
        now = datetime.now(timezone.utc)
        with app.app_context():
            existing_rec = ResumeAnalysis(
                user_id=user_id,
                job_role="Full Stack Development",
                ats_score=78.5,
                analysis_json=json.dumps({
                    "ats_score": 78.5,
                    "job_match_score": 82.0,
                    "resume_summary": "Experienced full stack software engineer",
                    "strengths": ["Strong Python background"],
                    "areas_for_improvement": ["Add more cloud credentials"]
                }),
                status="completed",
                created_at=now
            )
            db.session.add(existing_rec)
            db.session.commit()
            record_id = existing_rec.id

        # 1. First visit to /resume
        resp = self.client.get('/resume')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')

        # Form must be present and ready
        self.assertIn('id="resumeAnalyzerFormV2"', html)
        self.assertIn('Upload Resume', html)
        self.assertIn('Job Description', html)
        self.assertIn('Analyze Resume &amp; Generate Interview', html)

        # MUST NOT automatically hydrate the previous 78.5% analysis
        self.assertIn('window.__INITIAL_ANALYSIS__ = null;', html)
        self.assertIn('window.__INITIAL_RECORD_ID__ = null;', html)

        # 2. Refresh /resume (Part 13 I)
        refresh_resp = self.client.get('/resume')
        self.assertEqual(refresh_resp.status_code, 200)
        refresh_html = refresh_resp.data.decode('utf-8')
        self.assertIn('window.__INITIAL_ANALYSIS__ = null;', refresh_html)

        # 3. Explicit view via ?analysis_id=<record_id> (Part 13 G / Part 5)
        explicit_resp = self.client.get(f'/resume?analysis_id={record_id}')
        self.assertEqual(explicit_resp.status_code, 200)
        explicit_html = explicit_resp.data.decode('utf-8')
        self.assertIn('"ats_score": 78.5', explicit_html)
        self.assertIn(f'window.__INITIAL_RECORD_ID__ = {record_id};', explicit_html)

        # 4. Confirm database record was NOT deleted
        with app.app_context():
            saved = ResumeAnalysis.query.get(record_id)
            self.assertIsNotNone(saved)
            self.assertEqual(saved.ats_score, 78.5)

    def test_dashboard_and_history_still_use_saved_analysis(self):
        """Part 13 G & H: Dashboard and History continue to derive real analytics from saved records."""
        user_id = self.create_isolated_user("resume_history_user")
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
            db.session.commit()
            rec_id = rec.id

            user = User.query.get(user_id)
            dash = get_user_dashboard_stats(user)
            self.assertEqual(dash['resume_status'], 'Completed')
            self.assertEqual(dash['ats_score'], 85.0)

        # History page shows record
        resp = self.client.get('/history')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('85%', html)
        self.assertIn(f'/resume-analysis/{rec_id}', html)

if __name__ == '__main__':
    unittest.main()

