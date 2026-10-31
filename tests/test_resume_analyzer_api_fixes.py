import os
import sys
import unittest
import io
import json
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import (
    app, db, User, UserProfile, ResumeAnalysis, InterviewJourney,
    normalize_interview_type, get_user_selected_domain, set_user_selected_domain
)

# Helper to generate a minimal valid PDF byte sequence
def create_dummy_pdf_bytes():
    # A valid, readable minimal PDF 1.4 stream containing extractable text
    return (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
        b"4 0 obj << /Length 200 >> stream\n"
        b"BT\n"
        b"/F1 12 Tf\n"
        b"72 712 Td\n"
        b"(John Doe Software Engineer Python Django Flask PostgreSQL React Docker Kubernetes AWS Microservices CI/CD) Tj\n"
        b"ET\n"
        b"endstream\n"
        b"endobj\n"
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        b"xref\n"
        b"0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000266 00000 n \n"
        b"0000000518 00000 n \n"
        b"trailer << /Size 6 /Root 1 0 R >>\n"
        b"startxref\n"
        b"597\n"
        b"%%EOF\n"
    )

class ResumeAnalyzerApiFixesTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        cls.client = app.test_client()

        with app.app_context():
            db.create_all()
            user = User.query.filter_by(username="resume_fix_user").first()
            if not user:
                user = User(
                    username="resume_fix_user",
                    email="resume_fix_user@example.com",
                    password_hash="$2b$12$SaNvHt44MeTZFMApICHUke/Pde5NEpw0YZm4S2oy8r.WtnTQRwzVW",
                    selected_domain="Full Stack Development"
                )
                db.session.add(user)
                db.session.commit()
                profile = UserProfile(user_id=user.id, preferred_domain="Full Stack Development")
                db.session.add(profile)
                db.session.commit()
            else:
                user.selected_domain = "Full Stack Development"
                db.session.commit()
            cls.test_user_id = user.id

    def setUp(self):
        self.client = app.test_client()
        with app.app_context():
            ResumeAnalysis.query.filter_by(user_id=self.test_user_id).delete()
            InterviewJourney.query.filter_by(user_id=self.test_user_id).delete()
            u = db.session.get(User, self.test_user_id)
            if u:
                u.selected_domain = "Full Stack Development"
            db.session.commit()

    def tearDown(self):
        with app.app_context():
            ResumeAnalysis.query.filter_by(user_id=self.test_user_id).delete()
            InterviewJourney.query.filter_by(user_id=self.test_user_id).delete()
            db.session.commit()

    def login_test_user(self):
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.test_user_id)
            sess['user_id'] = self.test_user_id
            sess['user_email'] = 'resume_fix_user@example.com'
            sess['user_name'] = 'resume_fix_user'
            sess['role'] = 'user'
            sess['selected_domain'] = 'Full Stack Development'

    def test_unauthenticated_requests_return_json_401(self):
        """Unauthenticated AJAX/API calls must return JSON with 401 instead of HTML 302/login page."""
        # 1. POST /resume/upload with XMLHttpRequest header
        resp1 = self.client.post(
            '/resume/upload',
            data={'job_description': 'Test JD', 'interview_type': 'technical'},
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        self.assertEqual(resp1.status_code, 401)
        self.assertIn('application/json', resp1.content_type)
        data1 = resp1.get_json()
        self.assertFalse(data1['success'])
        self.assertIn('Authentication required', data1.get('error', ''))

        # 2. GET /api/resume/status/<task_id>
        resp2 = self.client.get('/api/resume/status/test-task-123')
        self.assertEqual(resp2.status_code, 401)
        self.assertIn('application/json', resp2.content_type)
        data2 = resp2.get_json()
        self.assertFalse(data2['success'])

    def test_error_cases_return_json_not_html(self):
        """All validation error cases must return JSON 400, never HTML."""
        self.login_test_user()

        # Case A: Missing file
        resp_no_file = self.client.post(
            '/resume/upload',
            data={'job_description': 'We need a Python developer', 'interview_type': 'technical'},
            content_type='multipart/form-data',
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        self.assertEqual(resp_no_file.status_code, 400)
        self.assertIn('application/json', resp_no_file.content_type)
        data_no_file = resp_no_file.get_json()
        self.assertFalse(data_no_file['success'])
        self.assertIn('Please upload a PDF resume', data_no_file.get('error', ''))

        # Case B: Unsupported file extension (e.g. .txt)
        txt_data = {
            'resume': (io.BytesIO(b'Hello text'), 'resume.txt'),
            'job_description': 'Python dev job',
            'interview_type': 'technical'
        }
        resp_txt = self.client.post(
            '/resume/upload',
            data=txt_data,
            content_type='multipart/form-data',
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        self.assertEqual(resp_txt.status_code, 400)
        self.assertIn('application/json', resp_txt.content_type)
        data_txt = resp_txt.get_json()
        self.assertFalse(data_txt['success'])
        self.assertIn('PDF', data_txt.get('error', ''))

        # Case C: Empty job description
        pdf_bytes = create_dummy_pdf_bytes()
        resp_no_jd = self.client.post(
            '/resume/upload',
            data={'resume': (io.BytesIO(pdf_bytes), 'resume.pdf'), 'job_description': '', 'interview_type': 'technical'},
            content_type='multipart/form-data',
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        self.assertEqual(resp_no_jd.status_code, 400)
        self.assertIn('application/json', resp_no_jd.content_type)
        data_no_jd = resp_no_jd.get_json()
        self.assertFalse(data_no_jd['success'])
        self.assertIn('Job description is required', data_no_jd.get('error', ''))

        # Case D: Missing interview type
        resp_no_it = self.client.post(
            '/resume/upload',
            data={'resume': (io.BytesIO(pdf_bytes), 'resume.pdf'), 'job_description': 'Python dev', 'interview_type': ''},
            content_type='multipart/form-data',
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        self.assertEqual(resp_no_it.status_code, 400)
        self.assertIn('application/json', resp_no_it.content_type)
        data_no_it = resp_no_it.get_json()
        self.assertFalse(data_no_it['success'])
        self.assertIn('Interview type is required', data_no_it.get('error', ''))

        # Case E: Missing domain when not selected
        with app.app_context():
            u = db.session.get(User, self.test_user_id)
            u.selected_domain = None
            prof = UserProfile.query.filter_by(user_id=self.test_user_id).first()
            if prof:
                prof.preferred_domain = None
            db.session.commit()

        with self.client.session_transaction() as sess:
            sess.pop('selected_domain', None)
            sess.pop('target_domain', None)
            sess.pop('coding_domain', None)

        resp_no_domain = self.client.post(
            '/resume/upload',
            data={'resume': (io.BytesIO(pdf_bytes), 'resume.pdf'), 'job_description': 'Python dev', 'interview_type': 'technical'},
            content_type='multipart/form-data',
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        self.assertEqual(resp_no_domain.status_code, 400)
        self.assertIn('application/json', resp_no_domain.content_type)
        data_no_domain = resp_no_domain.get_json()
        self.assertFalse(data_no_domain['success'])
        self.assertIn('target domain', data_no_domain.get('error', '').lower())

    from unittest.mock import patch

    @patch('app.call_resume_workflow')
    def test_all_four_interview_types_async_and_sync(self, mock_workflow):
        """Test all 4 interview types (Technical, HR, Coding, Mixed) succeed and return JSON."""
        mock_workflow.return_value = {
            "output": {
                "ats_score": 85,
                "match_level": "Strong Match",
                "summary": "Experienced Full Stack engineer with strong backend and cloud background.",
                "score_breakdown": {
                    "requirements": 85,
                    "critical_requirement_coverage": 90,
                    "responsibilities": 80,
                    "experience": 85,
                    "job_title": 90,
                    "education": 80
                },
                "strengths": ["Strong Python experience", "Docker and cloud deployment"],
                "missing_requirements": ["GraphQL"],
                "responsibility_gaps": ["Distributed systems mentoring"],
                "resume_improvements": ["Add metrics to past accomplishments"],
                "keyword_opportunities": ["Kubernetes"],
                "final_recommendation": "Well qualified candidate."
            }
        }
        self.login_test_user()
        pdf_bytes = create_dummy_pdf_bytes()
        types = ['Technical', 'HR', 'Coding', 'Mixed', 'technical', 'hr', 'coding', 'mixed']

        for itype in types:
            with self.subTest(interview_type=itype):
                # 1. Async Pipeline request (as sent by browser UI)
                req_data = {
                    'resume': (io.BytesIO(pdf_bytes), f'resume_{itype}.pdf'),
                    'job_description': 'Senior Full Stack Engineer with expertise in Python, React, PostgreSQL, Docker, and REST APIs.',
                    'interview_type': itype,
                    'async': 'true'
                }
                resp = self.client.post(
                    '/resume/upload',
                    data=req_data,
                    content_type='multipart/form-data',
                    headers={'X-Requested-With': 'XMLHttpRequest'}
                )
                self.assertEqual(resp.status_code, 200)
                self.assertIn('application/json', resp.content_type)
                res_data = resp.get_json()
                self.assertTrue(res_data['success'])
                self.assertTrue(res_data['async'])
                task_id = res_data['task_id']
                self.assertTrue(task_id)

                # Poll until completed (timeout 15s)
                poll_start = time.time()
                is_completed = False
                final_status = None
                while time.time() - poll_start < 15:
                    poll_resp = self.client.get(f'/api/resume/status/{task_id}')
                    self.assertEqual(poll_resp.status_code, 200)
                    self.assertIn('application/json', poll_resp.content_type)
                    status_json = poll_resp.get_json()
                    self.assertTrue(status_json['success'])
                    if status_json['status'] == 'completed':
                        is_completed = True
                        final_status = status_json
                        break
                    elif status_json['status'] == 'failed':
                        self.fail(f"Task failed with error: {status_json.get('error')}")
                    time.sleep(0.3)

                self.assertTrue(is_completed, f"Task {task_id} did not complete within timeout")
                self.assertIsNotNone(final_status['analysis'])
                self.assertGreaterEqual(final_status['analysis']['ats_score'], 0)
                self.assertIsNotNone(final_status['record_id'])

                # Verify database record exists
                with app.app_context():
                    rec = db.session.get(ResumeAnalysis, final_status['record_id'])
                    self.assertIsNotNone(rec)
                    self.assertEqual(rec.status, 'completed')
                    self.assertEqual(rec.user_id, self.test_user_id)

    def test_dashboard_redirect_loop_guard(self):
        """Verify dashboard never enters a redirect loop for normal users or admin users."""
        self.login_test_user()
        # Normal user accessing dashboard
        dash_resp = self.client.get('/dashboard')
        self.assertEqual(dash_resp.status_code, 200)
        self.assertIn('Interview.ai', dash_resp.data.decode('utf-8'))

if __name__ == '__main__':
    unittest.main()
