"""
tests/test_dashboard_domain_flow.py
End-to-End Test Suite for Dashboard Domain Single Source of Truth System.

Covers the 5 core test cases required:
- Test Case 1: Selecting "AI / Machine Learning" on Dashboard propagates to Resume Analyzer,
  Aptitude questions (AI_Engineer.xlsx), and Coding Round.
- Test Case 2: Changing domain on Dashboard to "Backend Development" immediately switches all subsequent modules.
- Test Case 3: Historical reports preserve original domain snapshots even after Dashboard domain change.
- Test Case 4: No domain selected -> User is prompted on Dashboard, blocked from starting assessments or uploading resume.
- Test Case 5: Domain persists across login/logout sessions via database persistence.
- Test Case 6: Robust canonical normalization and file mapping for all 10 supported engineering domains.
"""

import os
import sys
import unittest
import json
from datetime import datetime, timezone

# Ensure project root is in python search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import (
    app, db, User, UserProfile, ResumeAnalysis, MCQSession, CodingAssessment,
    SUPPORTED_DOMAINS, DOMAIN_METADATA, normalize_canonical_domain,
    get_user_selected_domain, set_user_selected_domain, map_domain_to_aptitude_file,
    build_resume_webhook_payload
)
import question_bank


class TestDashboardDomainFlow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        cls.client = app.test_client()

        with app.app_context():
            db.create_all()
            # Ensure a clean dedicated test user
            user = User.query.filter_by(username="domain_tester").first()
            if not user:
                user = User(
                    username="domain_tester",
                    email="domain_tester@example.com",
                    password_hash="$2b$12$SaNvHt44MeTZFMApICHUke/Pde5NEpw0YZm4S2oy8r.WtnTQRwzVW",
                    selected_domain="AI / Machine Learning"
                )
                db.session.add(user)
                db.session.commit()
                profile = UserProfile(user_id=user.id, preferred_domain="AI / Machine Learning")
                db.session.add(profile)
                db.session.commit()
            cls.test_user_id = user.id

    def login_test_user(self):
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.test_user_id)
            sess['user_id'] = self.test_user_id
            sess['role'] = 'user'
            sess['selected_domain'] = 'AI / Machine Learning'

    def test_case_1_aiml_domain_propagation(self):
        """
        Test Case 1: Selecting "AI / Machine Learning" on Dashboard ->
        Resume Analyzer receives AI/ML context -> Aptitude loads AI/ML questions ->
        Coding setup inherits AI/ML.
        """
        with app.app_context():
            user = User.query.get(self.test_user_id)
            with app.test_request_context():
                set_user_selected_domain("AI / Machine Learning", user=user)
                active_domain = get_user_selected_domain(user=user)
                self.assertEqual(active_domain, "AI / Machine Learning")

                # 1. Resume Analyzer payload contains selected domain
                from flask_login import login_user
                login_user(user)
                payload = build_resume_webhook_payload(
                    resume_text="Experienced in PyTorch and Machine Learning models.",
                    job_description="Looking for an AI / Machine Learning Engineer.",
                    interview_type="technical"
                )
                self.assertEqual(payload['selected_domain'], "AI / Machine Learning")
                self.assertEqual(payload['domain'], "AI / Machine Learning")

                # 2. Aptitude mapping uses AI_Engineer.xlsx
                aptitude_file = map_domain_to_aptitude_file(active_domain)
                self.assertEqual(aptitude_file, "AI_Engineer")
                excel_path = os.path.join(app.root_path, 'questions', f"{aptitude_file}.xlsx")
                self.assertTrue(os.path.exists(excel_path), f"File {excel_path} should exist")

        # 3. Coding setup and assessment endpoints inherit AI / Machine Learning
        self.login_test_user()
        res_setup = self.client.get('/coding/setup')
        self.assertEqual(res_setup.status_code, 200)
        self.assertIn(b"AI / Machine Learning", res_setup.data)

        res_assess = self.client.get('/coding/assessment')
        self.assertEqual(res_assess.status_code, 200)
        self.assertIn(b"AI / Machine Learning", res_assess.data)

    def test_case_2_switch_to_backend_development(self):
        """
        Test Case 2: Changing domain on Dashboard to "Backend Development" ->
        all subsequent modules switch to Backend Development immediately.
        """
        self.login_test_user()
        # Post domain change to API
        res = self.client.post('/api/user/domain', json={'domain': 'Backend Development', 'confirm_switch': True})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['domain'], "Backend Development")

        with app.app_context():
            user = User.query.get(self.test_user_id)
            self.assertEqual(user.selected_domain, "Backend Development")
            self.assertEqual(user.profile.preferred_domain, "Backend Development")

            # Verify Aptitude mapping immediately switches to Backend_Developer
            aptitude_file = map_domain_to_aptitude_file(user.selected_domain)
            self.assertEqual(aptitude_file, "Backend_Developer")
            excel_path = os.path.join(app.root_path, 'questions', f"{aptitude_file}.xlsx")
            self.assertTrue(os.path.exists(excel_path))

        # Coding setup and assessment now reflect Backend Development
        res_setup = self.client.get('/coding/setup')
        self.assertEqual(res_setup.status_code, 200)
        self.assertIn(b"Backend Development", res_setup.data)

        res_assess = self.client.get('/coding/assessment')
        self.assertEqual(res_assess.status_code, 200)
        self.assertIn(b"Backend Development", res_assess.data)

    def test_case_3_historical_reports_preserve_snapshots(self):
        """
        Test Case 3: Historical reports preserve original domain snapshots even after Dashboard domain change.
        """
        with app.app_context():
            user = User.query.get(self.test_user_id)
            # Create past MCQ session taken under 'Frontend Development'
            past_mcq = MCQSession(
                user_id=user.id,
                domain="Frontend Development",
                difficulty="Medium",
                score=85,
                total_questions=20,
                correct_answers=17,
                wrong_answers=3,
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                time_taken_seconds=600
            )
            # Create past CodingAssessment taken under 'Frontend Development'
            past_coding = CodingAssessment(
                user_id=user.id,
                role="Frontend Developer",
                domain="Frontend Development",
                difficulty="Medium",
                language="Python",
                total_questions=3,
                questions_solved=3,
                questions_attempted=3,
                overall_score=92.0,
                time_used_seconds=900,
                duration_minutes=45,
                total_test_cases=15,
                passed_test_cases=15,
                failed_test_cases=0,
                questions_data="[]",
                results_data="{}",
                submitted_at=datetime.now(timezone.utc)
            )
            db.session.add(past_mcq)
            db.session.add(past_coding)
            db.session.commit()
            past_coding_id = past_coding.id

            # Now switch active user domain to 'Cybersecurity'
            with app.test_request_context():
                set_user_selected_domain("Cybersecurity", user=user)

        self.login_test_user()
        # Verify the historical coding report still reports Frontend Development
        res_report = self.client.get(f'/coding/report/{past_coding_id}')
        self.assertEqual(res_report.status_code, 200)
        self.assertIn(b"Frontend Development", res_report.data)

        with app.app_context():
            rec = CodingAssessment.query.get(past_coding_id)
            self.assertEqual(rec.domain, "Frontend Development")

    def test_case_4_no_domain_selected_gate(self):
        """
        Test Case 4: No domain selected -> User is prompted to select one on Dashboard,
        cannot start assessment or analyze resume.
        """
        with app.app_context():
            # Create a user with NO domain selected
            no_domain_user = User.query.filter_by(username="no_domain_user").first()
            if not no_domain_user:
                no_domain_user = User(
                    username="no_domain_user",
                    email="no_domain_user@example.com",
                    password_hash="$2b$12$SaNvHt44MeTZFMApICHUke/Pde5NEpw0YZm4S2oy8r.WtnTQRwzVW",
                    selected_domain=None
                )
                db.session.add(no_domain_user)
                db.session.commit()
            else:
                no_domain_user.selected_domain = None
                if no_domain_user.profile:
                    no_domain_user.profile.preferred_domain = None
                db.session.commit()
            no_domain_id = no_domain_user.id

        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(no_domain_id)
            sess['user_id'] = no_domain_id
            sess['role'] = 'user'
            sess.pop('selected_domain', None)
            sess.pop('coding_domain', None)
            sess.pop('target_domain', None)

        # 1. Resume upload rejected with 400
        res_upload = self.client.post('/resume/upload', data={
            'job_description': 'Software Engineer Job',
            'interview_type': 'technical'
        })
        self.assertEqual(res_upload.status_code, 400)
        self.assertIn("Please select your target domain from the Dashboard before analyzing your resume.", res_upload.get_json()['message'])

        # 2. Aptitude assessment renders no_domain state
        res_apt = self.client.get('/interview-assessment')
        self.assertEqual(res_apt.status_code, 200)
        self.assertIn(b"Target Domain Selection Required", res_apt.data)

        # 3. Aptitude setup redirects to dashboard
        res_apt_setup = self.client.get('/interview/setup')
        self.assertEqual(res_apt_setup.status_code, 302)
        self.assertIn('/dashboard', res_apt_setup.headers['Location'])

        # 4. Coding setup GET shows no_domain warning
        res_coding_setup = self.client.get('/coding/setup')
        self.assertEqual(res_coding_setup.status_code, 200)
        self.assertIn(b"Target Domain Selection Required", res_coding_setup.data)

        # 5. Coding setup POST redirects to dashboard
        res_coding_post = self.client.post('/coding/setup', data={'language': 'Python'})
        self.assertEqual(res_coding_post.status_code, 302)
        self.assertIn('/dashboard', res_coding_post.headers['Location'])

        # 6. Coding assessment GET redirects to dashboard
        res_coding_assess = self.client.get('/coding/assessment')
        self.assertEqual(res_coding_assess.status_code, 302)
        self.assertIn('/dashboard', res_coding_assess.headers['Location'])

    def test_case_5_persistence_across_login_sessions(self):
        """
        Test Case 5: Domain persists across login/logout sessions.
        """
        with app.app_context():
            user = User.query.get(self.test_user_id)
            with app.test_request_context():
                set_user_selected_domain("DevOps", user=user)

        # Log out
        self.client.get('/logout')

        # Log back in and verify domain is immediately restored from DB
        self.login_test_user()
        with self.client.session_transaction() as sess:
            sess.pop('selected_domain', None)

        with app.app_context():
            user = User.query.get(self.test_user_id)
            self.assertEqual(user.selected_domain, "DevOps")
            self.assertEqual(get_user_selected_domain(user=user), "DevOps")

        res_dash = self.client.get('/dashboard')
        self.assertEqual(res_dash.status_code, 200)
        self.assertIn(b"DevOps", res_dash.data)

    def test_case_6_all_10_canonical_domains(self):
        """
        Test Case 6: Verify all 10 canonical domains are supported, normalized, and have question files.
        """
        for domain in SUPPORTED_DOMAINS:
            # Canonical normalization check
            norm = normalize_canonical_domain(domain)
            self.assertEqual(norm, domain)

            # Metadata check
            self.assertIn(domain, DOMAIN_METADATA)
            self.assertIn("icon", DOMAIN_METADATA[domain])
            self.assertIn("badge", DOMAIN_METADATA[domain])

            # Aptitude mapping check
            file_key = map_domain_to_aptitude_file(domain)
            file_path = os.path.join(app.root_path, 'questions', f"{file_key}.xlsx")
            self.assertTrue(os.path.exists(file_path), f"Question file missing for {domain}: {file_path}")

            # Coding question bank coverage check
            questions = question_bank.get_questions_for_assessment(domain=domain, count=3)
            self.assertGreaterEqual(len(questions), 3, f"Not enough questions in question bank for {domain}")


if __name__ == '__main__':
    unittest.main()
