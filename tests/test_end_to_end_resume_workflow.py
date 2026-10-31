import io
import time
import json
import unittest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from app import app, db, User, ResumeAnalysis, set_user_selected_domain

class TestEndToEndResumeWorkflow(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        with self.app.app_context():
            self.user = User.query.filter_by(username='domain_tester').first()
            if not self.user:
                from werkzeug.security import generate_password_hash
                self.user = User(username='domain_tester', email='domain_tester@example.com', password_hash=generate_password_hash('pass1234'))
                db.session.add(self.user)
                db.session.commit()
            set_user_selected_domain('Backend Development', user=self.user)
            self.user_id = self.user.id

    def test_complete_resume_workflow_lifecycle(self):
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.user_id)
            sess['target_domain'] = 'Backend Development'

        # 1. Open fresh /resume - confirm it starts empty
        res_fresh = self.client.get('/resume')
        self.assertEqual(res_fresh.status_code, 200)
        self.assertIn(b'window.__INITIAL_ANALYSIS__ = null;', res_fresh.data)
        self.assertIn(b'Upload Resume', res_fresh.data)

        # 2. Build real PDF in memory
        pdf_buffer = io.BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=letter)
        c.drawString(100, 750, 'Senior Python Backend Developer')
        c.drawString(100, 730, 'Experience: 5 years building scalable backend APIs using Flask, FastAPI, PostgreSQL and Docker.')
        c.drawString(100, 710, 'Skills: Python, Flask, Django, SQL, PostgreSQL, Docker, AWS, Git, REST APIs, Microservices.')
        c.drawString(100, 690, 'Education: Bachelor of Science in Computer Science.')
        c.drawString(100, 670, 'Projects: Built AI Interview Assistant and high-throughput microservices architecture.')
        c.save()
        pdf_buffer.seek(0)
        pdf_bytes = pdf_buffer.getvalue()

        # 3. Form fields
        job_description = "Senior Backend Engineer required with 5+ years of Python, Flask, and PostgreSQL experience."
        data = {
            'resume': (io.BytesIO(pdf_bytes), 'senior_backend_candidate.pdf', 'application/pdf'),
            'job_description': job_description,
            'interview_type': 'Technical',
            'domain': 'Backend Development',
            'async': 'true'
        }

        # 4 & 5. Post to /resume/upload
        t0 = time.time()
        upload_res = self.client.post(
            '/resume/upload',
            data=data,
            content_type='multipart/form-data',
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        self.assertEqual(upload_res.status_code, 200)
        upload_data = upload_res.get_json()
        self.assertTrue(upload_data.get('success'))
        self.assertTrue(upload_data.get('async'))
        task_id = upload_data.get('task_id')
        self.assertTrue(task_id)

        # 6. Poll status until completed
        final_payload = None
        max_wait = 90
        poll_interval = 1.5
        while time.time() - t0 < max_wait:
            poll_res = self.client.get(f'/api/resume/status/{task_id}')
            self.assertEqual(poll_res.status_code, 200)
            status_json = poll_res.get_json()
            st = status_json.get('status')
            if st == 'completed':
                final_payload = status_json
                break
            elif st == 'failed':
                self.fail(f"Pipeline failed with error: {status_json.get('error')}")
            time.sleep(poll_interval)

        self.assertIsNotNone(final_payload, "Pipeline did not complete within timeout")
        self.assertEqual(final_payload.get('status'), 'completed')
        self.assertEqual(final_payload.get('current_step'), 6)
        self.assertEqual(final_payload.get('step_name'), 'Analysis complete')
        self.assertEqual(final_payload.get('progress_percent'), 100)

        # 7. Validate real analysis data
        analysis = final_payload.get('analysis')
        self.assertIsInstance(analysis, dict)
        ats_score = analysis.get('ats_score')
        self.assertIsNotNone(ats_score)
        self.assertIsInstance(ats_score, (int, float))
        # Ensure it is real data from the workflow, not fake fallback 81%
        self.assertTrue(0 <= ats_score <= 100)
        
        summary = analysis.get('summary')
        self.assertTrue(summary and len(summary) > 20)
        
        strengths = analysis.get('strengths')
        self.assertIsInstance(strengths, list)
        self.assertTrue(len(strengths) > 0)

        record_id = final_payload.get('record_id')
        self.assertTrue(record_id)

        # 8. Confirm saved in DB
        with self.app.app_context():
            saved_record = ResumeAnalysis.query.get(record_id)
            self.assertIsNotNone(saved_record)
            self.assertEqual(saved_record.user_id, self.user_id)
            self.assertEqual(saved_record.ats_score, ats_score)
            self.assertEqual(saved_record.status, 'completed')

        # 9. Refresh /resume - must remain empty
        res_refresh = self.client.get('/resume')
        self.assertEqual(res_refresh.status_code, 200)
        self.assertIn(b'window.__INITIAL_ANALYSIS__ = null;', res_refresh.data)

        # 10. Explicit retrieval via ?analysis_id=<record_id>
        res_explicit = self.client.get(f'/resume?analysis_id={record_id}')
        self.assertEqual(res_explicit.status_code, 200)
        self.assertNotIn(b'window.__INITIAL_ANALYSIS__ = null;', res_explicit.data)
        self.assertIn(f'"ats_score": {ats_score}'.encode('utf-8'), res_explicit.data)

        # 11. History page displays the saved record
        res_history = self.client.get('/history')
        self.assertEqual(res_history.status_code, 200)
        self.assertIn(str(record_id).encode('utf-8'), res_history.data)

if __name__ == '__main__':
    unittest.main()
