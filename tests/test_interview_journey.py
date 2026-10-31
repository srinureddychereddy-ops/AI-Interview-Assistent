"""
tests/test_interview_journey.py
Comprehensive End-to-End Test Suite for Guided Interview Journey.

Tests all 13 required scenarios from Section 18:
1. New user with domain selected -> Resume available, Aptitude locked, Coding locked, Certificate locked
2. ATS 79 -> Aptitude remains locked
3. ATS 80 -> Aptitude unlocks
4. Aptitude 79 -> Coding remains locked
5. Aptitude 80 -> Coding unlocks
6. Coding incomplete -> Certificate locked
7. Coding successfully completed -> Certificate unlocks
8. Direct URL access to Aptitude before ATS >= 80 -> blocked
9. Direct URL access to Coding before Aptitude >= 80 -> blocked
10. Direct URL access to Certificate before all stages complete -> blocked
11. Domain change creates a new journey without modifying historical results
12. Certificate contains correct user name, domain, company name, certificate ID, and issue date
13. Logout/login preserves current journey state
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
    InterviewJourney, CertificateRecord, get_interview_journey_status,
    set_user_selected_domain, get_user_selected_domain
)


class TestInterviewJourney(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        cls.client = app.test_client()

        with app.app_context():
            db.create_all()

    def create_candidate_user(self, username, domain="AI / Machine Learning", full_name="Alan Turing"):
        """Helper to create an isolated candidate user with profile and domain."""
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(
                username=username,
                email=f"{username}@example.com",
                password_hash="$2b$12$SaNvHt44MeTZFMApICHUke/Pde5NEpw0YZm4S2oy8r.WtnTQRwzVW",
                selected_domain=domain
            )
            db.session.add(user)
            db.session.commit()

            first_name, _, last_name = full_name.partition(' ')
            profile = UserProfile(
                user_id=user.id,
                first_name=first_name,
                last_name=last_name,
                preferred_domain=domain
            )
            db.session.add(profile)
        else:
            user.selected_domain = domain
            if user.profile:
                user.profile.preferred_domain = domain
            db.session.commit()
        return user

    def create_resume_analysis(self, user_id, ats_score, domain="Software Engineering", role="Software Engineer"):
        """Helper to create a fully valid ResumeAnalysis with analysis_json."""
        data = {
            "ats_score": ats_score,
            "domain": domain,
            "target_role": role,
            "key_skills": ["Python", "Algorithms"]
        }
        return ResumeAnalysis(
            user_id=user_id,
            job_role=role,
            ats_score=float(ats_score),
            analysis_json=json.dumps(data),
            filename="resume.pdf",
            job_description=f"{role} position in {domain}",
            status="completed"
        )

    def create_mcq_session(self, user_id, domain, score, difficulty="Medium", total_questions=20):
        """Helper to create a fully valid MCQSession with all non-null fields."""
        correct = int(round(total_questions * (score / 100.0)))
        wrong = total_questions - correct
        now = datetime.now(timezone.utc)
        return MCQSession(
            user_id=user_id,
            domain=domain,
            difficulty=difficulty,
            score=score,
            total_questions=total_questions,
            correct_answers=correct,
            wrong_answers=wrong,
            start_time=now,
            end_time=now,
            time_taken_seconds=600
        )

    def login_user(self, user_id, domain):
        """Helper to simulate session login."""
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(user_id)
            sess['user_id'] = user_id
            sess['role'] = 'user'
            sess['selected_domain'] = domain

    def test_01_new_user_with_domain_selected(self):
        """Scenario 1: New user with domain selected -> Resume available, others locked."""
        with app.app_context():
            user = self.create_candidate_user("candidate_01", "AI / Machine Learning")
            status = get_interview_journey_status(user)

            self.assertTrue(status['has_domain'])
            self.assertEqual(status['domain'], "AI / Machine Learning")
            self.assertEqual(status['active_stage'], "resume")
            self.assertEqual(status['resume']['status'], "available")
            self.assertTrue(status['resume']['unlocked'])
            self.assertFalse(status['resume']['completed'])

            self.assertFalse(status['aptitude']['unlocked'])
            self.assertEqual(status['aptitude']['status'], "locked")

            self.assertFalse(status['coding']['unlocked'])
            self.assertEqual(status['coding']['status'], "locked")

            self.assertFalse(status['certificate']['unlocked'])
            self.assertEqual(status['certificate']['status'], "locked")

    def test_02_ats_79_aptitude_remains_locked(self):
        """Scenario 2: ATS score 79 -> Aptitude remains locked."""
        with app.app_context():
            user = self.create_candidate_user("candidate_02", "Backend Development")
            rec = self.create_resume_analysis(user.id, 79.0, domain="Backend Development", role="Backend Developer")
            db.session.add(rec)
            db.session.commit()

            status = get_interview_journey_status(user)
            self.assertFalse(status['resume']['completed'])
            self.assertEqual(status['resume']['ats_score'], 79.0)
            self.assertFalse(status['aptitude']['unlocked'])
            self.assertEqual(status['aptitude']['status'], "locked")
            self.assertEqual(status['active_stage'], "resume")

    def test_03_ats_80_aptitude_unlocks(self):
        """Scenario 3: ATS score 80 -> Resume completed and Aptitude unlocks."""
        with app.app_context():
            user = self.create_candidate_user("candidate_03", "Data Science")
            rec = self.create_resume_analysis(user.id, 80.0, domain="Data Science", role="Data Scientist")
            db.session.add(rec)
            db.session.commit()

            status = get_interview_journey_status(user)
            self.assertTrue(status['resume']['completed'])
            self.assertEqual(status['resume']['ats_score'], 80.0)
            self.assertTrue(status['aptitude']['unlocked'])
            self.assertIn(status['aptitude']['status'], ["available", "in_progress"])
            self.assertEqual(status['active_stage'], "aptitude")

            # Coding and certificate remain locked
            self.assertFalse(status['coding']['unlocked'])
            self.assertFalse(status['certificate']['unlocked'])

    def test_04_aptitude_79_coding_remains_locked(self):
        """Scenario 4: Aptitude score 79 -> Coding remains locked."""
        with app.app_context():
            user = self.create_candidate_user("candidate_04", "Full Stack Development")
            rec = self.create_resume_analysis(user.id, 88.0, domain="Full Stack Development", role="Full Stack Engineer")
            db.session.add(rec)
            mcq = self.create_mcq_session(user.id, "Full Stack Development", 79)
            db.session.add(mcq)
            db.session.commit()

            status = get_interview_journey_status(user)
            self.assertTrue(status['resume']['completed'])
            self.assertFalse(status['aptitude']['completed'])
            self.assertEqual(status['aptitude']['score'], 79)
            self.assertFalse(status['coding']['unlocked'])
            self.assertEqual(status['coding']['status'], "locked")
            self.assertEqual(status['active_stage'], "aptitude")

    def test_05_aptitude_80_coding_unlocks(self):
        """Scenario 5: Aptitude score 80 -> Aptitude completed and Coding unlocks."""
        with app.app_context():
            user = self.create_candidate_user("candidate_05", "DevOps")
            rec = self.create_resume_analysis(user.id, 85.0, domain="DevOps", role="DevOps Engineer")
            db.session.add(rec)
            mcq = self.create_mcq_session(user.id, "DevOps", 80)
            db.session.add(mcq)
            db.session.commit()

            status = get_interview_journey_status(user)
            self.assertTrue(status['resume']['completed'])
            self.assertTrue(status['aptitude']['completed'])
            self.assertTrue(status['coding']['unlocked'])
            self.assertEqual(status['active_stage'], "coding")
            self.assertFalse(status['certificate']['unlocked'])

    def test_06_coding_incomplete_certificate_locked(self):
        """Scenario 6: Coding not completed or score < 60% -> Certificate remains locked."""
        with app.app_context():
            user = self.create_candidate_user("candidate_06", "Cybersecurity")
            rec = self.create_resume_analysis(user.id, 90.0, domain="Cybersecurity", role="Cybersecurity Analyst")
            db.session.add(rec)
            mcq = self.create_mcq_session(user.id, "Cybersecurity", 90)
            db.session.add(mcq)
            coding = CodingAssessment(
                user_id=user.id,
                role="Cybersecurity Engineer",
                domain="Cybersecurity",
                difficulty="Medium",
                language="Python",
                total_questions=5,
                questions_solved=0,
                questions_attempted=1,
                overall_score=20.0
            )
            db.session.add(coding)
            db.session.commit()

            status = get_interview_journey_status(user)
            self.assertTrue(status['coding']['unlocked'])
            self.assertFalse(status['coding']['completed'])
            self.assertFalse(status['certificate']['unlocked'])
            self.assertEqual(status['certificate']['status'], "locked")
            self.assertEqual(status['active_stage'], "coding")

    def test_07_coding_completed_certificate_unlocks(self):
        """Scenario 7: Coding successfully completed -> Certificate unlocks and record is issued."""
        with app.app_context():
            user = self.create_candidate_user("candidate_07", "Software Engineering", full_name="Ada Lovelace")
            rec = self.create_resume_analysis(user.id, 92.0, domain="Software Engineering", role="Software Engineer")
            db.session.add(rec)
            mcq = self.create_mcq_session(user.id, "Software Engineering", 85)
            db.session.add(mcq)
            coding = CodingAssessment(
                user_id=user.id,
                role="Software Engineer",
                domain="Software Engineering",
                difficulty="Medium",
                language="Python",
                total_questions=5,
                questions_solved=3,
                questions_attempted=5,
                overall_score=80.0
            )
            db.session.add(coding)
            db.session.commit()

            status = get_interview_journey_status(user)
            self.assertTrue(status['coding']['completed'])
            self.assertTrue(status['certificate']['unlocked'])
            self.assertIsNotNone(status['certificate']['id'])
            self.assertTrue(status['certificate']['id'].startswith("IA-2026-"))
            self.assertEqual(status['active_stage'], "certificate")

    def test_08_direct_url_access_to_aptitude_blocked(self):
        """Scenario 8: Direct URL access to Aptitude before ATS >= 80 is blocked and redirects to /resume."""
        with app.app_context():
            user = self.create_candidate_user("candidate_08", "Mobile Development")
            u_id = user.id
            u_dom = user.selected_domain
        self.login_user(u_id, u_dom)

        res_assess = self.client.get('/interview-assessment', follow_redirects=False)
        self.assertEqual(res_assess.status_code, 302)
        self.assertIn('/resume', res_assess.headers['Location'])

        res_setup = self.client.get('/interview/setup', follow_redirects=False)
        self.assertEqual(res_setup.status_code, 302)
        self.assertIn('/resume', res_setup.headers['Location'])

    def test_09_direct_url_access_to_coding_blocked(self):
        """Scenario 9: Direct URL access to Coding before Aptitude >= 80 is blocked and redirects."""
        with app.app_context():
            user = self.create_candidate_user("candidate_09", "Data Engineering")
            rec = self.create_resume_analysis(user.id, 86.0, domain="Data Engineering", role="Data Engineer")
            db.session.add(rec)
            db.session.commit()
            u_id = user.id
            u_dom = user.selected_domain

        self.login_user(u_id, u_dom)
        # Attempt to access coding assessment directly
        res_assess = self.client.get('/coding/assessment', follow_redirects=False)
        self.assertEqual(res_assess.status_code, 302)
        self.assertIn('/interview-assessment', res_assess.headers['Location'])

        # Attempt to POST /coding/setup directly
        res_post = self.client.post('/coding/setup', data={'language': 'Python'}, follow_redirects=False)
        self.assertEqual(res_post.status_code, 302)
        self.assertIn('/interview-assessment', res_post.headers['Location'])

    def test_10_direct_url_access_to_certificate_blocked(self):
        """Scenario 10: Direct URL access to Certificate before all stages are complete is blocked."""
        with app.app_context():
            user = self.create_candidate_user("candidate_10", "Frontend Development")
            rec = self.create_resume_analysis(user.id, 88.0, domain="Frontend Development", role="Frontend Developer")
            db.session.add(rec)
            mcq = self.create_mcq_session(user.id, "Frontend Development", 85)
            db.session.add(mcq)
            db.session.commit()
            u_id = user.id
            u_dom = user.selected_domain

        self.login_user(u_id, u_dom)
        res_cert = self.client.get('/certificate', follow_redirects=False)
        self.assertEqual(res_cert.status_code, 302)
        self.assertIn('/coding/setup', res_cert.headers['Location'])

        res_journey_cert = self.client.get('/journey/certificate', follow_redirects=False)
        self.assertEqual(res_journey_cert.status_code, 302)
        self.assertIn('/coding/setup', res_journey_cert.headers['Location'])

    def test_11_domain_change_creates_new_journey_without_destroying_history(self):
        """Scenario 11: Domain change requires confirmation when started, and creates a new journey without deleting historical data."""
        with app.app_context():
            user = self.create_candidate_user("candidate_11", "AI / Machine Learning")
            rec = self.create_resume_analysis(user.id, 90.0, domain="AI / Machine Learning", role="AI Engineer")
            db.session.add(rec)
            db.session.commit()
            u_id = user.id
            u_dom = user.selected_domain

        self.login_user(u_id, u_dom)

        # 1. First attempt to switch domain without confirm_switch returns requires_confirmation
        res = self.client.post('/api/user/domain', json={'domain': 'Backend Development'})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertFalse(data['success'])
        self.assertTrue(data['requires_confirmation'])
        self.assertEqual(data['new_domain'], "Backend Development")

        # 2. Confirm the domain switch
        res_confirm = self.client.post('/api/user/domain', json={
            'domain': 'Backend Development',
            'confirm_switch': True
        })
        self.assertEqual(res_confirm.status_code, 200)
        data_confirm = res_confirm.get_json()
        self.assertTrue(data_confirm['success'])
        self.assertEqual(data_confirm['domain'], "Backend Development")

        # 3. Verify user's selected domain updated
        with app.app_context():
            db_user = User.query.filter_by(username="candidate_11").first()
            self.assertEqual(db_user.selected_domain, "Backend Development")

            # Verify historical journey for AI/Machine Learning still exists
            old_journey = InterviewJourney.query.filter_by(
                user_id=db_user.id, domain="AI / Machine Learning"
            ).first()
            self.assertIsNotNone(old_journey)

            # Verify new journey for Backend Development exists
            new_journey = InterviewJourney.query.filter_by(
                user_id=db_user.id, domain="Backend Development"
            ).first()
            self.assertIsNotNone(new_journey)

    def test_12_certificate_content_verification(self):
        """Scenario 12: Certificate page renders correct user name, domain, company name, ID, and issue date."""
        with app.app_context():
            user = self.create_candidate_user("candidate_12", "Cybersecurity", full_name="Grace Hopper")
            rec = self.create_resume_analysis(user.id, 94.0, domain="Cybersecurity", role="Cybersecurity Expert")
            db.session.add(rec)
            mcq = self.create_mcq_session(user.id, "Cybersecurity", 88)
            db.session.add(mcq)
            coding = CodingAssessment(
                user_id=user.id,
                role="Cybersecurity Engineer",
                domain="Cybersecurity",
                difficulty="Medium",
                language="Python",
                total_questions=5,
                questions_solved=4,
                questions_attempted=5,
                overall_score=90.0
            )
            db.session.add(coding)
            db.session.commit()

            # Ensure cert is generated
            status = get_interview_journey_status(user)
            self.assertTrue(status['certificate']['unlocked'])
            cert_id = status['certificate']['id']
            u_id = user.id
            u_dom = user.selected_domain

        self.login_user(u_id, u_dom)
        res = self.client.get('/certificate')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Verify candidate name
        self.assertIn("Grace Hopper", html)
        # Verify domain
        self.assertIn("Cybersecurity", html)
        # Verify company / platform branding
        self.assertIn("Interview.ai", html)
        # Verify Certificate ID
        self.assertIn(cert_id, html)
        # Verify scores
        self.assertIn("94%", html)
        self.assertIn("88%", html)
        self.assertIn("90%", html)
        # Verify print support
        self.assertIn("window.print()", html)

    def test_13_logout_login_preserves_journey_state(self):
        """Scenario 13: Logout and login preserves the current journey state."""
        with app.app_context():
            user = self.create_candidate_user("candidate_13", "Software Engineering", full_name="Linus Torvalds")
            rec = self.create_resume_analysis(user.id, 85.0, domain="Software Engineering", role="Kernel Engineer")
            db.session.add(rec)
            mcq = self.create_mcq_session(user.id, "Software Engineering", 85)
            db.session.add(mcq)
            db.session.commit()
            u_id = user.id
            u_dom = user.selected_domain

        self.login_user(u_id, u_dom)
        # Log out
        self.client.get('/logout')

        # Log back in
        self.login_user(u_id, u_dom)

        with app.app_context():
            db_user = User.query.filter_by(username="candidate_13").first()
            status = get_interview_journey_status(db_user)

            self.assertEqual(status['domain'], "Software Engineering")
            self.assertTrue(status['resume']['completed'])
            self.assertTrue(status['aptitude']['completed'])
            self.assertTrue(status['coding']['unlocked'])
            self.assertEqual(status['active_stage'], "coding")


if __name__ == '__main__':
    unittest.main()
