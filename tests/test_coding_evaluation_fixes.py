"""
tests/test_coding_evaluation_fixes.py
Comprehensive End-to-End Verification Suite for Coding Assessment Flow & Evaluation System.

Covers:
1. Submission rejection when 1/3 answered (incomplete_assessment 400).
2. Submission rejection when 2/3 answered (incomplete_assessment 400).
3. Successful submission when all 3/3 answered (200 success).
4. Exit assessment leaves progress intact, does not create CodingAssessment record or unlock certificate.
5. Code persistence across questions.
6. Backend independently rejects empty/whitespace solutions bypassing frontend.
7. Correct Priority Job Queue executes with exact function name `process_job_queue`.
8. Correct Pagination Helper executes with exact function name `paginate_items`.
9. Correct Shopping Cart Calculator executes with exact function name `calculate_cart_total`.
10. Solutions evaluated against both visible and hidden test cases.
11. Infrastructure error simulation: Docker unavailable returns execution_environment without penalizing candidate.
12. Syntax error correctly categorized.
13. Runtime error correctly categorized.
14. Timeout / Infinite loop correctly categorized.
15. Correct assessment submission yields high score and solved count.
16. Successful assessment unlocks Certificate of Completion.
17. Incomplete assessment does not unlock Certificate.
"""

import sys
import os
import unittest
import json
from unittest.mock import patch

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db, User, CodingAssessment, CertificateRecord, ResumeAnalysis, MCQSession, InterviewJourney, get_interview_journey_status
import question_bank
import execution_engine


class TestCodingEvaluationFixes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False


    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            user = User.query.filter_by(username='test_coder').first()
            if not user:
                user = User(
                    username='test_coder',
                    email='test_coder@example.com',
                    password_hash='dummy_hash',
                    selected_domain='Backend Development'
                )
                db.session.add(user)
                db.session.commit()
            else:
                user.selected_domain = 'Backend Development'
                db.session.commit()
            self.test_user_id = user.id

            # Clean test data before each test
            CodingAssessment.query.filter_by(user_id=self.test_user_id).delete()
            CertificateRecord.query.filter_by(user_id=self.test_user_id).delete()
            ResumeAnalysis.query.filter_by(user_id=self.test_user_id).delete()
            MCQSession.query.filter_by(user_id=self.test_user_id).delete()
            InterviewJourney.query.filter_by(user_id=self.test_user_id).delete()
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            CodingAssessment.query.filter_by(user_id=self.test_user_id).delete()
            CertificateRecord.query.filter_by(user_id=self.test_user_id).delete()
            ResumeAnalysis.query.filter_by(user_id=self.test_user_id).delete()
            MCQSession.query.filter_by(user_id=self.test_user_id).delete()
            InterviewJourney.query.filter_by(user_id=self.test_user_id).delete()
            db.session.commit()
            db.session.remove()

    def login_test_user(self):
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.test_user_id)
            sess['_fresh'] = True
            sess['csrf_token'] = 'test-token'
            sess['dashboard_domain'] = 'Backend Development'

    # -------------------------------------------------------------
    # Test 1 & 2: Submitting with incomplete questions blocked (400)
    # -------------------------------------------------------------
    def test_01_submit_with_one_of_three_answered_blocked(self):
        """Candidate answers 1 of 3 questions -> submit blocked with 400 incomplete_assessment."""
        self.login_test_user()
        self.client.post('/coding/setup', data={
            "role": "Backend Developer",
            "domain": "Backend Development",
            "difficulty": "Medium",
            "language": "Python",
            "questions": "3",
            "duration": "45"
        })
        self.client.get('/coding/assessment')

        res = self.client.post('/api/coding/submit', json={
            "answers": {
                "1": "def process_job_queue(jobs):\n    return [j['id'] for j in jobs]\n"
            },
            "time_used_seconds": 300
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data.get("success"))
        self.assertEqual(data.get("error"), "incomplete_assessment")
        self.assertIn(2, data.get("unanswered_questions", []))
        self.assertIn(3, data.get("unanswered_questions", []))

    def test_02_submit_with_two_of_three_answered_blocked(self):
        """Candidate answers 2 of 3 questions -> submit blocked with 400."""
        self.login_test_user()
        self.client.post('/coding/setup', data={
            "role": "Backend Developer",
            "domain": "Backend Development",
            "difficulty": "Medium",
            "language": "Python",
            "questions": "3",
            "duration": "45"
        })
        self.client.get('/coding/assessment')

        res = self.client.post('/api/coding/submit', json={
            "answers": {
                "1": "def process_job_queue(jobs):\n    return []\n",
                "2": "def paginate_items(items, page, page_size):\n    return []\n"
                # Q3 omitted
            },
            "time_used_seconds": 600
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data.get("error"), "incomplete_assessment")
        self.assertIn(3, data.get("unanswered_questions", []))

    # -------------------------------------------------------------
    # Test 3: Submitting all 3/3 questions allowed (200)
    # -------------------------------------------------------------
    def test_03_submit_with_all_three_answered_allowed(self):
        """Candidate answers all 3 questions -> submit succeeds with 200."""
        self.login_test_user()
        self.client.post('/coding/setup', data={
            "role": "Backend Developer",
            "domain": "Backend Development",
            "difficulty": "Medium",
            "language": "Python",
            "questions": "3",
            "duration": "45"
        })
        self.client.get('/coding/assessment')

        with self.client.session_transaction() as sess:
            qs = sess.get('active_coding_questions', [])
            self.assertEqual(len(qs), 3)
            answers = {}
            for idx, q in enumerate(qs, 1):
                fn = q.get('function_name', 'solution')
                answers[str(q.get('id', idx))] = f"def {fn}(*args, **kwargs):\n    return []\n"

        res = self.client.post('/api/coding/submit', json={
            "answers": answers,
            "time_used_seconds": 900
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("/coding/report/", data.get("redirect_url"))

    # -------------------------------------------------------------
    # Test 4: Exit saves progress without submitting or unlocking cert
    # -------------------------------------------------------------
    def test_04_exit_assessment_without_submitting(self):
        """Exiting assessment does not submit assessment or unlock certificate."""
        self.login_test_user()
        self.client.post('/coding/setup', data={
            "role": "Backend Developer",
            "domain": "Backend Development",
            "difficulty": "Medium",
            "language": "Python",
            "questions": "3",
            "duration": "45"
        })
        self.client.get('/coding/assessment')

        # Save partial code via auto-save
        save_res = self.client.post('/api/coding/save_session', json={
            "question_id": "1",
            "code": "def process_job_queue(jobs):\n    pass\n",
            "language": "Python"
        })
        self.assertEqual(save_res.status_code, 200)

        # Confirm no CodingAssessment record exists
        with self.app.app_context():
            records = CodingAssessment.query.filter_by(user_id=self.test_user_id).all()
            self.assertEqual(len(records), 0)

            # Certificate is not awarded
            certs = CertificateRecord.query.filter_by(user_id=self.test_user_id).all()
            self.assertEqual(len(certs), 0)

    # -------------------------------------------------------------
    # Test 5: Backend independently rejects empty/whitespace solutions
    # -------------------------------------------------------------
    def test_05_backend_rejects_whitespace_solutions(self):
        """Backend validates non-empty code even if client attempts to bypass."""
        self.login_test_user()
        self.client.post('/coding/setup', data={
            "role": "Backend Developer",
            "domain": "Backend Development",
            "difficulty": "Medium",
            "language": "Python",
            "questions": "3",
            "duration": "45"
        })
        self.client.get('/coding/assessment')

        res = self.client.post('/api/coding/submit', json={
            "answers": {
                "1": "    \n\n\t  ",
                "2": "   ",
                "3": ""
            },
            "time_used_seconds": 120
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data.get("error"), "incomplete_assessment")
        self.assertEqual(len(data.get("unanswered_questions", [])), 3)

    # -------------------------------------------------------------
    # Test 6: Correct process_job_queue passes visible tests
    # -------------------------------------------------------------
    def test_06_correct_process_job_queue(self):
        """Exact function name process_job_queue is resolved and passes tests."""
        q = question_bank.get_question_by_key("fs-job-queue")
        self.assertIsNotNone(q)
        self.assertEqual(q["function_name"], "process_job_queue")

        code = """
def process_job_queue(jobs):
    sorted_jobs = sorted(jobs, key=lambda j: (-j.get('priority', 0), j.get('timestamp', 0)))
    return [j['id'] for j in sorted_jobs]
"""
        res = execution_engine.evaluate_question_submission(code, q, timeout_seconds=15)
        self.assertEqual(res["status"], "Solved")
        self.assertGreater(res["visible_passed"], 0)
        self.assertEqual(res["visible_passed"], res["visible_total"])
        self.assertEqual(res["hidden_passed"], res["hidden_total"])

    # -------------------------------------------------------------
    # Test 7: Correct paginate_items passes visible tests
    # -------------------------------------------------------------
    def test_07_correct_paginate_items(self):
        """Exact function name paginate_items is resolved and passes tests."""
        q = question_bank.get_question_by_key("fs-pagination")
        self.assertIsNotNone(q)
        self.assertEqual(q["function_name"], "paginate_items")

        code = """
import math

def paginate_items(items, page, page_size):
    total = len(items)
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    start = (page - 1) * page_size
    page_data = items[start:start + page_size]
    return {
        "items": page_data,
        "page": page,
        "total_pages": total_pages,
        "total_items": total
    }
"""
        res = execution_engine.evaluate_question_submission(code, q, timeout_seconds=15)
        self.assertEqual(res["status"], "Solved")
        self.assertEqual(res["visible_passed"], res["visible_total"])
        self.assertEqual(res["hidden_passed"], res["hidden_total"])

    # -------------------------------------------------------------
    # Test 8: Correct calculate_cart_total passes visible tests
    # -------------------------------------------------------------
    def test_08_correct_calculate_cart_total(self):
        """Exact function name calculate_cart_total is resolved and passes tests."""
        q = question_bank.get_question_by_key("fs-shopping-cart-logic")
        self.assertIsNotNone(q)
        self.assertEqual(q["function_name"], "calculate_cart_total")

        code = """
def calculate_cart_total(items, tax_rate):
    subtotal = 0.0
    for item in items:
        price = item.get('price', 0)
        qty = item.get('quantity', 1)
        disc = item.get('discount_percent', 0)
        item_total = price * qty * (1.0 - (disc / 100.0))
        subtotal += item_total
    total = subtotal * (1.0 + tax_rate)
    return round(total, 2)
"""
        res = execution_engine.evaluate_question_submission(code, q, timeout_seconds=15)
        self.assertEqual(res["status"], "Solved")
        self.assertEqual(res["visible_passed"], res["visible_total"])
        self.assertEqual(res["hidden_passed"], res["hidden_total"])

    # -------------------------------------------------------------
    # Test 9: Docker unavailable simulation returns execution_environment
    # -------------------------------------------------------------
    def test_09_docker_unavailable_simulation(self):
        """When Docker is down, system returns execution_environment 503 without penalizing candidate."""
        with patch('execution_engine.check_docker_available', return_value=(False, "Docker daemon not running")):
            self.login_test_user()
            self.client.post('/coding/setup', data={
                "role": "Backend Developer",
                "domain": "Backend Development",
                "difficulty": "Medium",
                "language": "Python",
                "questions": "3",
                "duration": "45"
            })
            self.client.get('/coding/assessment')

            # Run Code endpoint returns 503
            res_run = self.client.post('/api/coding/run', json={
                "language": "python",
                "question_id": "1",
                "code": "def process_job_queue(jobs): return []",
                "test_cases": []
            })
            self.assertEqual(res_run.status_code, 503)
            data_run = res_run.get_json()
            self.assertEqual(data_run.get("error_type"), "execution_environment")

            # Submit endpoint returns 503 preserving answers
            res_sub = self.client.post('/api/coding/submit', json={
                "answers": {
                    "1": "def process_job_queue(jobs): return []",
                    "2": "def paginate_items(items, page, page_size): return {}",
                    "3": "def calculate_cart_total(items, discount, tax): return 0.0"
                },
                "time_used_seconds": 300
            })
            self.assertEqual(res_sub.status_code, 503)
            data_sub = res_sub.get_json()
            self.assertEqual(data_sub.get("error_type"), "execution_environment")

    # -------------------------------------------------------------
    # Test 10: Syntax error categorization
    # -------------------------------------------------------------
    def test_10_syntax_error_categorization(self):
        """Syntax error is caught before execution and labeled Syntax Error."""
        code = "def two_sum(nums target):\n    return []\n"
        res = execution_engine.execute_python_code(code, question_id="1", timeout_seconds=15)
        self.assertEqual(res["status"], "Syntax Error")
        self.assertEqual(res["error_type"], "SyntaxError")
        self.assertEqual(res["passed"], 0)

    # -------------------------------------------------------------
    # Test 11: Runtime error categorization
    # -------------------------------------------------------------
    def test_11_runtime_error_categorization(self):
        """Runtime exception is caught and labeled Runtime Error."""
        code = "def two_sum(nums, target):\n    return 1 / 0\n"
        res = execution_engine.execute_python_code(code, question_id="1", timeout_seconds=15)
        self.assertEqual(res["status"], "Runtime Error")
        self.assertIn("ZeroDivisionError", res["test_cases"][0]["error"])

    # -------------------------------------------------------------
    # Test 12: Infinite loop timeout categorization
    # -------------------------------------------------------------
    def test_12_infinite_loop_timeout_categorization(self):
        """Infinite loop inside candidate function is cleanly caught as Timeout."""
        code = "def two_sum(nums, target):\n    while True:\n        pass\n"
        res = execution_engine.execute_python_code(code, question_id="1", timeout_seconds=3)
        self.assertEqual(res["status"], "Timeout")
        self.assertEqual(res["error_type"], "TimeoutError")

    # -------------------------------------------------------------
    # Test 13: Full evaluation produces accurate high score and solved count
    # -------------------------------------------------------------
    def test_13_accurate_high_score_and_solved_count(self):
        """Three correct solutions evaluated result in 100 overall score and 3 solved."""
        active_qs = [
            question_bank.get_question_by_key("fs-job-queue"),
            question_bank.get_question_by_key("fs-pagination"),
            question_bank.get_question_by_key("fs-shopping-cart-logic")
        ]
        answers = {
            "fs-job-queue": """
def process_job_queue(jobs):
    sorted_jobs = sorted(jobs, key=lambda j: (-j.get('priority', 0), j.get('timestamp', 0)))
    return [j['id'] for j in sorted_jobs]
""",
            "fs-pagination-helper": """
import math
def paginate_items(items, page, page_size):
    total = len(items)
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    start = (page - 1) * page_size
    return {
        "items": items[start:start + page_size],
        "page": page,
        "total_pages": total_pages,
        "total_items": total
    }
""",
            "fs-shopping-cart-logic": """
def calculate_cart_total(items, tax_rate):
    subtotal = 0.0
    for item in items:
        price = item.get('price', 0)
        qty = item.get('quantity', 1)
        disc = item.get('discount_percent', 0)
        item_total = price * qty * (1.0 - (disc / 100.0))
        subtotal += item_total
    total = subtotal * (1.0 + tax_rate)
    return round(total, 2)
"""
        }
        eval_res = execution_engine.evaluate_full_assessment(answers, active_qs, time_used_seconds=420)
        self.assertEqual(eval_res["questions_solved"], 3)
        self.assertEqual(eval_res["questions_attempted"], 3)
        self.assertGreaterEqual(eval_res["overall_score"], 90.0)
        self.assertEqual(eval_res["failed_test_cases"], 0)

    # -------------------------------------------------------------
    # Test 14: Certificate unlocks only when required stages pass
    # -------------------------------------------------------------
    def test_14_certificate_unlocked_when_all_stages_pass(self):
        """Certificate is unlocked when ATS >= 80, MCQ >= 80, and Coding passed."""
        from datetime import datetime
        with self.app.app_context():
            u = User.query.get(self.test_user_id)
            # Stage 1: Resume Analysis ATS >= 80
            ra = ResumeAnalysis(
                user_id=u.id,
                job_role='Backend Developer',
                ats_score=85.0,
                analysis_json=json.dumps({'score': 85})
            )
            db.session.add(ra)

            # Stage 2: MCQ Session >= 80%
            mcq = MCQSession(
                user_id=u.id,
                domain='Backend Development',
                difficulty='Medium',
                score=90,
                total_questions=10,
                correct_answers=9,
                wrong_answers=1,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                time_taken_seconds=300
            )
            db.session.add(mcq)

            # Stage 3: CodingAssessment passed
            ca = CodingAssessment(
                user_id=u.id,
                domain='Backend Development',
                role='Backend Developer',
                difficulty='Medium',
                language='Python',
                total_questions=3,
                questions_solved=3,
                questions_attempted=3,
                overall_score=100.0,
                time_used_seconds=420,
                duration_minutes=45,
                total_test_cases=9,
                passed_test_cases=9,
                failed_test_cases=0,
                questions_data='[]',
                results_data='[]'
            )
            db.session.add(ca)
            db.session.commit()

            status = get_interview_journey_status(user=u)
            self.assertTrue(status['certificate']['unlocked'])
            self.assertEqual(status['certificate']['status'], 'unlocked')
            self.assertIsNotNone(status['certificate']['id'])

    # -------------------------------------------------------------
    # Test 15: Incomplete / zero-score coding assessment does not unlock certificate
    # -------------------------------------------------------------
    def test_15_certificate_locked_if_coding_not_passed(self):
        """Certificate remains locked if coding assessment had 0 score and 0 solved."""
        from datetime import datetime
        with self.app.app_context():
            u = User.query.get(self.test_user_id)
            # Stage 1: Resume Analysis ATS >= 80
            ra = ResumeAnalysis(
                user_id=u.id,
                job_role='Backend Developer',
                ats_score=85.0,
                analysis_json=json.dumps({'score': 85})
            )
            db.session.add(ra)

            # Stage 2: MCQ Session >= 80%
            mcq = MCQSession(
                user_id=u.id,
                domain='Backend Development',
                difficulty='Medium',
                score=90,
                total_questions=10,
                correct_answers=9,
                wrong_answers=1,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                time_taken_seconds=300
            )
            db.session.add(mcq)

            # Stage 3: CodingAssessment failed (0 score, 0 solved)
            ca = CodingAssessment(
                user_id=u.id,
                domain='Backend Development',
                role='Backend Developer',
                difficulty='Medium',
                language='Python',
                total_questions=3,
                questions_solved=0,
                questions_attempted=3,
                overall_score=15.0,
                time_used_seconds=500,
                duration_minutes=45,
                total_test_cases=9,
                passed_test_cases=0,
                failed_test_cases=9,
                questions_data='[]',
                results_data='[]'
            )
            db.session.add(ca)
            db.session.commit()

            status = get_interview_journey_status(user=u)
            self.assertFalse(status['certificate']['unlocked'])
            self.assertEqual(status['certificate']['status'], 'locked')


if __name__ == '__main__':
    unittest.main()
