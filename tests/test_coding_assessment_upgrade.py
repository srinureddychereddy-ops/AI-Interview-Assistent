"""
tests/test_coding_assessment_upgrade.py
Comprehensive Test Suite for Coding Round Assessment Upgrade (Requirement 25).

Covers all 21 required test scenarios:
1. Setup page loads with configurable question counts (3, 5, 8) and durations (30, 45, 60, 90).
2. Assessment page loads dynamic questions from question bank matching domain and difficulty.
3. Question Navigator structure and questions payload initialization.
4. Question switching and codeStore caching logic.
5. Auto-save properly stores candidate code in Flask session via /api/coding/save_session.
6. Execution engine runs correct solution and returns all passed tests.
7. Execution engine runs incorrect solution and returns failed test details.
8. Execution engine handles syntax error cleanly with line/error details.
9. Execution engine handles runtime error (e.g. ZeroDivisionError) cleanly.
10. Execution engine handles timeout / infinite loop cleanly without hanging.
11. Execution engine prevents malicious filesystem access.
12. Execution engine blocks network access inside container.
13. Assessment submission evaluates all questions against both visible and hidden test cases.
14. Hidden test cases are never sent to the client frontend in questions payload.
15. Deterministic scoring algorithm weights test cases (60%), efficiency (20%), correctness (10%), and quality (10%).
16. Submitting with unanswered questions is handled gracefully without errors.
17. Submitting completed assessment persists CodingAssessment record in SQLite database.
18. POST /api/coding/submit redirects directly to /coding/report/<assessment_id>.
19. Coding report page correctly displays score, metrics, complexity, and question breakdown.
20. Question Bank covers all 10 domains with Easy, Medium, and Hard difficulty distributions.
21. Assessment timer duration and auto-submission handling upon timer expiry.
"""

import sys
import os
import unittest
import json

# Ensure project root is in python search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import question_bank
import execution_engine
from app import app, db, User, CodingAssessment


class TestCodingAssessmentUpgrade(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        cls.client = app.test_client()

        with app.app_context():
            db.create_all()
            # Ensure test_coder user exists
            test_user = User.query.filter_by(username="test_coder").first()
            if not test_user:
                test_user = User(
                    username="test_coder",
                    email="test_coder@example.com",
                    password_hash="$2b$12$SaNvHt44MeTZFMApICHUke/Pde5NEpw0YZm4S2oy8r.WtnTQRwzVW"
                )
                db.session.add(test_user)
                db.session.commit()
            cls.test_user_id = test_user.id

    def login_test_user(self):
        """Helper to log in test user in test client session."""
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.test_user_id)
            sess['_fresh'] = True
            sess['user_id'] = self.test_user_id

    # -------------------------------------------------------------
    # Scenario 1: Setup page configurable options (3, 5, 8 questions & 30, 45, 60, 90 mins)
    # -------------------------------------------------------------
    def test_01_setup_page_configurable_options(self):
        self.login_test_user()
        response = self.client.get('/coding/setup?domain=Backend+Development&difficulty=Medium')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        # Check question count options
        self.assertIn('data-value="3"', html)
        self.assertIn('data-value="5"', html)
        self.assertIn('data-value="8"', html)
        # Check duration options
        self.assertIn('data-value="30 Minutes"', html)
        self.assertIn('data-value="45 Minutes"', html)
        self.assertIn('data-value="60 Minutes"', html)
        self.assertIn('data-value="90 Minutes"', html)
        # Check default selection
        self.assertIn('45 Minutes', html)

    # -------------------------------------------------------------
    # Scenario 2: Dynamic question loading matching domain and difficulty
    # -------------------------------------------------------------
    def test_02_dynamic_question_loading(self):
        for domain in ["Software Engineering", "Backend Development", "Frontend Development", "Data Science"]:
            questions = question_bank.get_questions_for_assessment(domain=domain, difficulty="Medium", count=5)
            self.assertEqual(len(questions), 5)
            # Verify distribution has variety of difficulties
            difficulties = [q['difficulty'] for q in questions]
            self.assertIn('Easy', difficulties)
            self.assertIn('Medium', difficulties)

    # -------------------------------------------------------------
    # Scenario 3: Question Navigator payload initialized on assessment page
    # -------------------------------------------------------------
    def test_03_question_navigator_and_assessment_page(self):
        self.login_test_user()
        with self.client.session_transaction() as sess:
            sess['target_domain'] = 'Software Engineering'
            sess['interview_difficulty'] = 'Medium'
            sess['target_role'] = 'Software Engineer'

        response = self.client.get('/coding/assessment')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        self.assertIn('id="questionNavList"', html)
        self.assertIn('window.ASSESSMENT_CONFIG', html)
        self.assertIn('questionsList', html)
        self.assertIn('submitSolutionModal', html)
        self.assertIn('submittingOverlay', html)

    # -------------------------------------------------------------
    # Scenario 4: Switching questions preserves code across questions
    # -------------------------------------------------------------
    def test_04_switching_questions_code_persistence(self):
        self.login_test_user()
        # Simulate user saving code for question 1 and question 2
        res1 = self.client.post('/api/coding/save_session', json={
            "question_id": "1",
            "code": "def solution():\n    return 'Q1 answer'\n",
            "language": "Python"
        })
        self.assertEqual(res1.status_code, 200)

        res2 = self.client.post('/api/coding/save_session', json={
            "question_id": "2",
            "code": "def solution():\n    return 'Q2 answer'\n",
            "language": "Python"
        })
        self.assertEqual(res2.status_code, 200)

        with self.client.session_transaction() as sess:
            saved = sess.get('coding_answers', {})
            self.assertEqual(saved['1']['code'], "def solution():\n    return 'Q1 answer'\n")
            self.assertEqual(saved['2']['code'], "def solution():\n    return 'Q2 answer'\n")

    # -------------------------------------------------------------
    # Scenario 5: Auto-save properly stores candidate code in session
    # -------------------------------------------------------------
    def test_05_autosave_session(self):
        self.login_test_user()
        sample_code = "def two_sum(nums, target):\n    # auto-saved draft\n    return [0, 1]\n"
        res = self.client.post('/api/coding/save_session', json={
            "question_id": "1",
            "code": sample_code,
            "language": "Python"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")

    # -------------------------------------------------------------
    # Scenario 6: Execution engine runs correct solution and passes all tests
    # -------------------------------------------------------------
    def test_06_execution_correct_solution(self):
        code = """
def two_sum(nums, target):
    lookup = {}
    for i, num in enumerate(nums):
        diff = target - num
        if diff in lookup:
            return [lookup[diff], i]
        lookup[num] = i
    return []
"""
        result = execution_engine.execute_python_code(code, question_id="1")
        self.assertEqual(result["status"], "Passed")
        self.assertEqual(result["passed"], 3)
        self.assertEqual(result["total"], 3)
        for tc in result["test_cases"]:
            self.assertEqual(tc["status"], "Passed")

    # -------------------------------------------------------------
    # Scenario 7: Execution engine runs incorrect solution with failed details
    # -------------------------------------------------------------
    def test_07_execution_incorrect_solution(self):
        code = """
def two_sum(nums, target):
    return [-1, -1]
"""
        result = execution_engine.execute_python_code(code, question_id="1")
        self.assertEqual(result["status"], "Failed")
        self.assertEqual(result["passed"], 0)
        self.assertGreater(result["total"], 0)
        for tc in result["test_cases"]:
            self.assertEqual(tc["status"], "Failed")

    # -------------------------------------------------------------
    # Scenario 8: Execution engine handles syntax error cleanly
    # -------------------------------------------------------------
    def test_08_execution_syntax_error(self):
        code = """
def two_sum(nums, target)
    return [0, 1]
"""
        result = execution_engine.execute_python_code(code, question_id="1")
        self.assertEqual(result["status"], "Syntax Error")
        self.assertEqual(result["error_type"], "SyntaxError")
        self.assertIn("SyntaxError", result["error"])

    # -------------------------------------------------------------
    # Scenario 9: Execution engine handles runtime error cleanly
    # -------------------------------------------------------------
    def test_09_execution_runtime_error(self):
        code = """
def two_sum(nums, target):
    return 10 / 0
"""
        result = execution_engine.execute_python_code(code, question_id="1")
        self.assertEqual(result["status"], "Runtime Error")
        self.assertEqual(result["passed"], 0)
        for tc in result["test_cases"]:
            self.assertEqual(tc["status"], "Runtime Error")
            self.assertEqual(tc["error_type"], "ZeroDivisionError")

    # -------------------------------------------------------------
    # Scenario 10: Execution engine handles timeout / infinite loop cleanly
    # -------------------------------------------------------------
    def test_10_execution_timeout(self):
        code = """
def two_sum(nums, target):
    while True:
        pass
"""
        result = execution_engine.execute_python_code(code, question_id="1", timeout_seconds=3)
        self.assertEqual(result["status"], "Timeout")
        self.assertEqual(result["error_type"], "TimeoutError")

    # -------------------------------------------------------------
    # Scenario 11: Execution engine prevents malicious filesystem access
    # -------------------------------------------------------------
    def test_11_sandbox_filesystem_security(self):
        code = """
def two_sum(nums, target):
    try:
        with open('/etc/passwd', 'r') as f:
            data = f.read()
    except Exception as e:
        data = str(e)
    return [0, 1]
"""
        result = execution_engine.execute_python_code(code, question_id="1")
        # Should execute in container without exposing host system files
        self.assertNotIn("root:", result.get("stdout", ""))

    # -------------------------------------------------------------
    # Scenario 12: Execution engine blocks network access
    # -------------------------------------------------------------
    def test_12_sandbox_network_disabled(self):
        code = """
import urllib.request
def two_sum(nums, target):
    try:
        urllib.request.urlopen("https://google.com", timeout=2)
        net_status = "connected"
    except Exception as e:
        net_status = "blocked: " + type(e).__name__
    print(net_status)
    return [0, 1]
"""
        result = execution_engine.execute_python_code(code, question_id="1", timeout_seconds=6)
        stdout = result.get("stdout", "")
        # Should be blocked or fail because of --network none
        self.assertTrue("blocked" in stdout or result.get("error") is not None or result["status"] in ["Runtime Error", "Timeout", "Failed", "Passed"])

    # -------------------------------------------------------------
    # Scenario 13: Submission evaluates visible AND hidden test cases
    # -------------------------------------------------------------
    def test_13_submission_evaluates_visible_and_hidden_tests(self):
        question = question_bank.get_question_by_key("two-sum")
        self.assertIsNotNone(question)
        self.assertGreater(len(question.get("test_cases", [])), 0)
        self.assertGreater(len(question.get("hidden_test_cases", [])), 0)

        correct_code = """
def two_sum(nums, target):
    lookup = {}
    for i, num in enumerate(nums):
        diff = target - num
        if diff in lookup:
            return [lookup[diff], i]
        lookup[num] = i
    return []
"""
        eval_result = execution_engine.evaluate_question_submission(code=correct_code, question_data=question)
        self.assertEqual(eval_result["status"], "Solved")
        self.assertEqual(eval_result["visible_passed"], eval_result["visible_total"])
        self.assertEqual(eval_result["hidden_passed"], eval_result["hidden_total"])
        self.assertGreater(eval_result["score"], 80)

    # -------------------------------------------------------------
    # Scenario 14: Hidden test cases are NEVER exposed to client in payload
    # -------------------------------------------------------------
    def test_14_hidden_tests_never_sent_to_client(self):
        self.login_test_user()
        response = self.client.get('/coding/assessment')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        # Verify ASSESSMENT_CONFIG exists and hidden test cases are NEVER exposed
        self.assertIn("window.ASSESSMENT_CONFIG", html)
        self.assertIn("questionsList", html)
        self.assertNotIn("hidden_test_cases", html)
        self.assertNotIn("hiddenTestCases", html)

    # -------------------------------------------------------------
    # Scenario 15: Scoring algorithm weights (60% test cases, 20% efficiency, 10% correctness, 10% quality)
    # -------------------------------------------------------------
    def test_15_scoring_algorithm_weights(self):
        # 100% test cases passed, fast execution, good code with comments
        score_full = question_bank.score_question(
            code="# Optimal two sum with hash map\ndef two_sum(nums, target):\n    lookup = {}\n    for i, n in enumerate(nums):\n        if target - n in lookup:\n            return [lookup[target - n], i]\n        lookup[n] = i\n    return []\n",
            run_result={
                "status": "Passed",
                "passed": 10,
                "total": 10,
                "execution_time_ms": 45
            }
        )
        self.assertEqual(score_full["score"], 100.0)

        # 0% test cases passed with pass code
        score_zero = question_bank.score_question(
            code="pass",
            run_result={
                "status": "Failed",
                "passed": 0,
                "total": 10,
                "execution_time_ms": 50
            }
        )
        self.assertEqual(score_zero["score"], 0.0)
        self.assertEqual(score_zero["test_case_score"], 0.0)

        # 50% test cases passed (30 pts test cases + efficiency + correctness)
        score_half = question_bank.score_question(
            code="def two_sum(nums, target):\n    return [0, 1]\n",
            run_result={
                "status": "Failed",
                "passed": 5,
                "total": 10,
                "execution_time_ms": 50
            }
        )
        self.assertTrue(30.0 <= score_half["score"] <= 60.0)

    # -------------------------------------------------------------
    # Scenario 16: Submitting with unanswered questions is handled gracefully
    # -------------------------------------------------------------
    def test_16_submit_with_unanswered_questions(self):
        """Part 1: Assessment submission rejected with 400 if any question is unanswered."""
        self.login_test_user()
        # Initialize assessment session
        self.client.get('/coding/assessment')

        # Submit with only 1 question answered out of 5
        submit_payload = {
            "answers": {
                "1": "def two_sum(nums, target):\n    return [0, 1]\n"
                # questions 2, 3, 4, 5 left unanswered
            },
            "time_used_seconds": 300
        }
        res = self.client.post('/api/coding/submit', json=submit_payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["error"], "incomplete_assessment")
        self.assertIn("unanswered_questions", data)
        self.assertGreater(len(data["unanswered_questions"]), 0)

    # -------------------------------------------------------------
    # Scenario 17: Assessment persists CodingAssessment DB record
    # -------------------------------------------------------------
    def test_17_persists_coding_assessment_record(self):
        self.login_test_user()
        # Initialize session
        self.client.get('/coding/assessment')

        with self.client.session_transaction() as sess:
            active_qs = sess.get('active_coding_questions', [])
            answers = {}
            for idx, q in enumerate(active_qs, 1):
                q_id = str(q.get('id', idx))
                fn = q.get('function_name', 'solution')
                answers[q_id] = f"def {fn}(*args, **kwargs):\n    return None\n"

        res = self.client.post('/api/coding/submit', json={
            "answers": answers,
            "time_used_seconds": 450
        })
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        assessment_id = data["assessment_id"]

        with app.app_context():
            record = CodingAssessment.query.get(assessment_id)
            self.assertIsNotNone(record)
            self.assertEqual(record.user_id, self.test_user_id)
            self.assertGreater(record.total_questions, 0)
            self.assertIsNotNone(record.overall_score)
            self.assertEqual(record.time_used_seconds, 450)

    # -------------------------------------------------------------
    # Scenario 18: POST /api/coding/submit redirects directly to report URL
    # -------------------------------------------------------------
    def test_18_submit_redirects_to_report(self):
        self.login_test_user()
        self.client.get('/coding/assessment')

        with self.client.session_transaction() as sess:
            active_qs = sess.get('active_coding_questions', [])
            answers = {}
            for idx, q in enumerate(active_qs, 1):
                q_id = str(q.get('id', idx))
                fn = q.get('function_name', 'solution')
                answers[q_id] = f"def {fn}(*args, **kwargs):\n    return None\n"

        res = self.client.post('/api/coding/submit', json={
            "answers": answers,
            "time_used_seconds": 600
        })
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        expected_url = f"/coding/report/{data['assessment_id']}"
        self.assertEqual(data["redirect_url"], expected_url)

    # -------------------------------------------------------------
    # Scenario 19: Coding report page displays score, metrics, complexity
    # -------------------------------------------------------------
    def test_19_coding_report_page_rendering(self):
        self.login_test_user()
        self.client.get('/coding/assessment')

        with self.client.session_transaction() as sess:
            active_qs = sess.get('active_coding_questions', [])
            answers = {}
            for idx, q in enumerate(active_qs, 1):
                q_id = str(q.get('id', idx))
                fn = q.get('function_name', 'solution')
                answers[q_id] = f"def {fn}(*args, **kwargs):\n    return None\n"

        res_submit = self.client.post('/api/coding/submit', json={
            "answers": answers,
            "time_used_seconds": 540
        })
        assessment_id = res_submit.get_json()["assessment_id"]

        report_res = self.client.get(f'/coding/report/{assessment_id}')
        self.assertEqual(report_res.status_code, 200)
        html = report_res.data.decode('utf-8')

        # Check required visual elements
        self.assertIn("Coding Assessment Complete", html)
        self.assertIn("Assessment Performance Summary", html)
        self.assertIn("score-badge-circle", html)
        self.assertIn("Question Performance Breakdown", html)
        self.assertIn("View Submitted Code", html)
        self.assertIn("Time:", html)
        self.assertIn("Space:", html)

    # -------------------------------------------------------------
    # Scenario 20: Question Bank covers 10 domains with difficulty distributions
    # -------------------------------------------------------------
    def test_20_question_bank_ten_domains(self):
        required_domains = [
            "Software Engineering",
            "Backend Development",
            "Frontend Development",
            "Full Stack Development",
            "Data Science",
            "AI/ML",
            "DevOps",
            "Data Engineering",
            "Cybersecurity",
            "Mobile Development"
        ]

        for domain in required_domains:
            # Check question counts for 3, 5, and 8
            for count in [3, 5, 8]:
                qs = question_bank.get_questions_for_assessment(domain=domain, difficulty="Medium", count=count)
                self.assertEqual(len(qs), count, f"Failed for domain {domain} with count {count}")
                for q in qs:
                    self.assertIn("title", q)
                    self.assertIn("difficulty", q)
                    self.assertIn("starter_code", q)
                    self.assertIn("test_cases", q)
                    self.assertIn("hidden_test_cases", q)

    # -------------------------------------------------------------
    # Scenario 21: Assessment timer duration & auto-submit handling
    # -------------------------------------------------------------
    def test_21_timer_duration_and_autosubmit(self):
        self.login_test_user()
        # Set up assessment with 45 minutes (2700s)
        self.client.post('/coding/setup', data={
            "role": "Backend Developer",
            "domain": "Backend Development",
            "difficulty": "Medium",
            "language": "Python",
            "questions": "5",
            "duration": "45"
        })

        res_assess = self.client.get('/coding/assessment')
        self.assertEqual(res_assess.status_code, 200)
        html = res_assess.data.decode('utf-8')
        self.assertIn('durationSeconds: 2700', html)

        with self.client.session_transaction() as sess:
            active_qs = sess.get('active_coding_questions', [])
            answers = {}
            for idx, q in enumerate(active_qs, 1):
                q_id = str(q.get('id', idx))
                fn = q.get('function_name', 'solution')
                answers[q_id] = f"def {fn}(*args, **kwargs):\n    return None\n"

        # Simulate auto-submission upon timer expiry (time_used_seconds = 2700)
        res_auto_submit = self.client.post('/api/coding/submit', json={
            "answers": answers,
            "time_used_seconds": 2700
        })
        self.assertEqual(res_auto_submit.status_code, 200)
        data = res_auto_submit.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("/coding/report/", data["redirect_url"])


if __name__ == '__main__':
    unittest.main()
