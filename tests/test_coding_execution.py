"""
tests/test_coding_execution.py
Phase 3 Backend Test Suite for Secure Docker Code Execution Engine.

Tests:
1. Correct Two Sum solution (Passed all test cases)
2. Wrong solution (Clean Failed status)
3. Syntax error (SyntaxError detected before execution)
4. Runtime error (ZeroDivisionError caught per test case)
5. Infinite loop / Timeout (Container killed within timeout)
6. Malicious filesystem access attempt (Read-only sandbox & host file isolation)
7. Network access attempt (Disabled network via --network none)
8. Flask API endpoint integration (POST /api/coding/run)
"""

import sys
import os
import unittest
import json

# Ensure project root is in python search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import execution_engine
from app import app, db, User


class TestCodingExecutionEngine(unittest.TestCase):

    def test_01_correct_two_sum(self):
        """Test 1: Correct Two Sum solution passes all test cases."""
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
        self.assertEqual(len(result["test_cases"]), 3)
        for tc in result["test_cases"]:
            self.assertEqual(tc["status"], "Passed")
            self.assertIsNone(tc["error"])

    def test_02_wrong_solution(self):
        """Test 2: Wrong solution fails test cases cleanly without crash."""
        code = """
def two_sum(nums, target):
    return [0, 0]
"""
        result = execution_engine.execute_python_code(code, question_id="1")
        self.assertEqual(result["status"], "Failed")
        self.assertEqual(result["passed"], 0)
        self.assertEqual(result["total"], 3)
        for tc in result["test_cases"]:
            self.assertEqual(tc["status"], "Failed")

    def test_03_syntax_error(self):
        """Test 3: Syntax error is caught cleanly with line and error details."""
        code = """
def two_sum(nums, target)
    return [0, 1]
"""
        result = execution_engine.execute_python_code(code, question_id="1")
        self.assertEqual(result["status"], "Syntax Error")
        self.assertEqual(result["error_type"], "SyntaxError")
        self.assertIn("SyntaxError", result["error"])
        self.assertEqual(result["passed"], 0)

    def test_04_runtime_error(self):
        """Test 4: Runtime error (e.g. ZeroDivisionError) is caught per test case."""
        code = """
def two_sum(nums, target):
    return 1 / 0
"""
        result = execution_engine.execute_python_code(code, question_id="1")
        self.assertEqual(result["status"], "Runtime Error")
        self.assertEqual(result["passed"], 0)
        self.assertEqual(len(result["test_cases"]), 3)
        for tc in result["test_cases"]:
            self.assertEqual(tc["status"], "Runtime Error")
            self.assertEqual(tc["error_type"], "ZeroDivisionError")
            self.assertIn("division by zero", tc["error"])

    def test_05_infinite_loop_timeout(self):
        """Test 5: Infinite loop / non-terminating code is terminated by timeout."""
        code = """
def two_sum(nums, target):
    while True:
        pass
"""
        result = execution_engine.execute_python_code(code, question_id="1", timeout_seconds=3)
        self.assertEqual(result["status"], "Timeout")
        self.assertEqual(result["error_type"], "TimeoutError")
        self.assertIn("timed out", result["error"].lower())
        self.assertEqual(result["passed"], 0)

    def test_06_malicious_filesystem_access(self):
        """Test 6: Malicious filesystem write & host file access attempts are blocked."""
        # 6a. Attempt to write to read-only container sandbox
        code_write = """
def two_sum(nums, target):
    with open('/sandbox/exploit.txt', 'w') as f:
        f.write('hacked')
    return [0, 1]
"""
        result_write = execution_engine.execute_python_code(code_write, question_id="1")
        self.assertEqual(result_write["status"], "Runtime Error")
        self.assertIn("Read-only file system", result_write["test_cases"][0]["error"])

        # 6b. Attempt to read host project files (isolated container cannot see host)
        code_read_host = """
def two_sum(nums, target):
    with open('d:/AI-Interview-Assistant/app.py') as f:
        content = f.read()
    return [0, 1]
"""
        result_read = execution_engine.execute_python_code(code_read_host, question_id="1")
        self.assertEqual(result_read["status"], "Runtime Error")
        self.assertEqual(result_read["test_cases"][0]["error_type"], "FileNotFoundError")

    def test_07_network_access_attempt(self):
        """Test 7: Outbound network calls fail immediately due to --network none."""
        code_net = """
import socket
def two_sum(nums, target):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    s.connect(('8.8.8.8', 53))
    return [0, 1]
"""
        result = execution_engine.execute_python_code(code_net, question_id="1")
        self.assertEqual(result["status"], "Runtime Error")
        self.assertIn("Network unreachable", result["test_cases"][0]["error"])

    def test_08_flask_api_endpoint(self):
        """Test 8: Flask POST /api/coding/run endpoint returns structured response."""
        client = app.test_client()
        with app.app_context():
            db.create_all()
            # Get or create a test user
            user = User.query.first()
            if not user:
                user = User(
                    username="test_exec_user",
                    email="test_exec@example.com",
                    password_hash="$2b$12$SaNvHt44MeTZFMApICHUke/Pde5NEpw0YZm4S2oy8r.WtnTQRwzVW"
                )
                db.session.add(user)
                db.session.commit()

            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True

            # Call /api/coding/run
            payload = {
                "language": "python",
                "question_id": "1",
                "code": "def two_sum(nums, target):\n    lookup = {}\n    for i, n in enumerate(nums):\n        d = target - n\n        if d in lookup: return [lookup[d], i]\n        lookup[n] = i\n    return []\n"
            }
            response = client.post(
                "/api/coding/run",
                data=json.dumps(payload),
                content_type="application/json"
            )
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data["success"])
            self.assertEqual(data["status"], "Passed")
            self.assertEqual(data["passed"], 3)
            self.assertEqual(data["total"], 3)
            self.assertIn("execution_time_ms", data)
            self.assertTrue(len(data["test_cases"]) > 0)

    def test_09_valid_palindrome(self):
        """Test 9: Valid Palindrome (Question 2) passes all test cases."""
        code = """
import re
def is_palindrome(s):
    cleaned = ''.join(c.lower() for c in s if c.isalnum())
    return cleaned == cleaned[::-1]
"""
        result = execution_engine.execute_python_code(code, question_id="2")
        self.assertEqual(result["status"], "Passed")
        self.assertEqual(result["passed"], 3)
        self.assertEqual(result["total"], 3)


if __name__ == '__main__':
    unittest.main()
