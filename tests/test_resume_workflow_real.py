import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import json

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import (
    app, db, User, ResumeAnalysis, InterviewJourney, bcrypt,
    call_resume_workflow, normalize_resume_analysis_response,
    execute_resume_pipeline, RESUME_ANALYSIS_TASKS, get_interview_journey_status
)

class ResumeWorkflowRealTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        cls.client = app.test_client()

        with app.app_context():
            db.create_all()
            user = User.query.filter_by(username="real_workflow_tester").first()
            if not user:
                user = User(
                    username="real_workflow_tester",
                    email="real_tester@example.com",
                    password_hash=bcrypt.generate_password_hash("Secret123!").decode('utf-8'),
                    selected_domain="Full Stack Development"
                )
                db.session.add(user)
                db.session.commit()
            cls.test_user_id = user.id

    def login_test_user(self):
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.test_user_id)
            sess['user_id'] = self.test_user_id
            sess['_fresh'] = True

    def test_call_resume_workflow_successful_parsing(self):
        """Verify call_resume_workflow parses both direct and wrapped workflow outputs."""
        fake_response = {
            "output": {
                "ats_score": 78,
                "match_level": "Good Match",
                "summary": "Solid full stack developer profile.",
                "score_breakdown": {
                    "requirements": 82,
                    "responsibilities": 75,
                    "experience": 80
                },
                "strengths": ["Strong Python skills"],
                "missing_requirements": ["GraphQL"],
                "responsibility_gaps": ["No team lead experience"],
                "resume_improvements": ["Add cloud architecture metrics"],
                "keyword_opportunities": ["FastAPI"],
                "final_recommendation": "Great candidate for mid-level."
            }
        }

        with patch('requests.post') as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = json.dumps(fake_response)
            mock_resp.json.return_value = fake_response
            mock_post.return_value = mock_resp

            payload = {
                "user_name": "Test User",
                "user_email": "real_tester@example.com",
                "resume_text": "sample text",
                "job_description": "sample job"
            }
            result = call_resume_workflow(payload)
            self.assertIn('output', result)
            self.assertEqual(result['output']['ats_score'], 78)
            self.assertEqual(result['output']['match_level'], "Good Match")
            self.assertEqual(result['output']['summary'], "Solid full stack developer profile.")
            self.assertIn("requirements", result['output']['score_breakdown'])

    def test_call_resume_workflow_error_does_not_return_mock(self):
        """Verify that when the workflow fails, RuntimeError is raised and NO mock data is produced."""
        with patch('requests.post') as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 500
            mock_resp.text = "Internal Server Error"
            mock_post.return_value = mock_resp

            payload = {
                "user_name": "Test User",
                "user_email": "real_tester@example.com",
                "resume_text": "sample text",
                "job_description": "sample job"
            }
            with self.assertRaises(RuntimeError) as cm:
                call_resume_workflow(payload, max_retries=1)

            self.assertIn("Resume analysis could not be completed. Please try again.", str(cm.exception))

    def test_normalize_resume_analysis_response_no_hallucinations(self):
        """Verify normalization does not invent summaries or categories when missing."""
        raw_data = {
            "ats_score": 65,
            # No summary, no score_breakdown, no strengths
        }
        normalized = normalize_resume_analysis_response(raw_data, "DevOps Engineer", "resume.pdf", "Some JD")
        self.assertEqual(normalized['ats_score'], 65)
        self.assertEqual(normalized['job_role'], "DevOps Engineer")
        self.assertEqual(normalized['summary'], "Summary unavailable from the analysis workflow.")
        self.assertEqual(normalized['score_breakdown'], {})
        self.assertEqual(normalized['strengths'], [])
        self.assertEqual(normalized['missing_requirements'], [])

    def test_journey_gate_ats_score_threshold(self):
        """Verify that ATS >= 80 unlocks Aptitude, while ATS < 80 keeps Aptitude locked."""
        # Case A: ATS < 80 (e.g. 67)
        with patch('app.call_resume_workflow') as mock_workflow:
            mock_workflow.return_value = {
                "output": {
                    "ats_score": 67,
                    "match_level": "Good Match",
                    "summary": "Needs more experience in Kubernetes.",
                    "score_breakdown": {"requirements": 67},
                    "strengths": ["Python"],
                    "missing_requirements": ["Kubernetes"],
                    "responsibility_gaps": [],
                    "resume_improvements": [],
                    "keyword_opportunities": [],
                    "final_recommendation": "Improve cloud skills."
                }
            }
            task_id_sub80 = "test-task-sub80"
            RESUME_ANALYSIS_TASKS[task_id_sub80] = {'status': 'processing'}
            execute_resume_pipeline(
                task_id=task_id_sub80,
                app_obj=app,
                user_id=self.test_user_id,
                resume_text="Python developer seeking cloud role.",
                job_description="Cloud engineer position",
                interview_type="Technical",
                filename="sub80.pdf",
                selected_domain="Full Stack Development"
            )
            result_sub80 = RESUME_ANALYSIS_TASKS[task_id_sub80]
            self.assertEqual(result_sub80['status'], 'completed')
            self.assertEqual(result_sub80['analysis']['ats_score'], 67)

            with app.app_context():
                user = User.query.get(self.test_user_id)
                journey_status = get_interview_journey_status(user)
                self.assertFalse(journey_status['aptitude']['unlocked'], "Aptitude should be locked when ATS < 80")

        # Case B: ATS >= 80 (e.g. 88)
        with patch('app.call_resume_workflow') as mock_workflow:
            mock_workflow.return_value = {
                "output": {
                    "ats_score": 88,
                    "match_level": "Strong Match",
                    "summary": "Excellent full stack profile with AWS and React.",
                    "score_breakdown": {"requirements": 88},
                    "strengths": ["React", "Python", "AWS"],
                    "missing_requirements": [],
                    "responsibility_gaps": [],
                    "resume_improvements": [],
                    "keyword_opportunities": [],
                    "final_recommendation": "Ready for interview."
                }
            }
            task_id_pass88 = "test-task-pass88"
            RESUME_ANALYSIS_TASKS[task_id_pass88] = {'status': 'processing'}
            execute_resume_pipeline(
                task_id=task_id_pass88,
                app_obj=app,
                user_id=self.test_user_id,
                resume_text="Senior full stack engineer.",
                job_description="Senior Full Stack position",
                interview_type="Technical",
                filename="pass88.pdf",
                selected_domain="Full Stack Development"
            )
            result_pass88 = RESUME_ANALYSIS_TASKS[task_id_pass88]
            self.assertEqual(result_pass88['status'], 'completed')
            self.assertEqual(result_pass88['analysis']['ats_score'], 88)

            with app.app_context():
                user = User.query.get(self.test_user_id)
                journey_status = get_interview_journey_status(user)
                self.assertTrue(journey_status['aptitude']['unlocked'], "Aptitude should be unlocked when ATS >= 80")

    def test_get_resume_loads_saved_analysis_from_db(self):
        """Verify GET /resume fetches the latest completed analysis from SQLite DB without re-running workflow."""
        self.login_test_user()

        with app.app_context():
            # Create a completed analysis record
            analysis_dict = {
                "ats_score": 84,
                "job_match": 84,
                "match_level": "Strong Match",
                "summary": "Saved database summary test.",
                "strengths": ["Full Stack", "Docker"],
                "missing_requirements": ["GraphQL"],
                "responsibility_gaps": ["DevOps details"],
                "resume_improvements": ["Highlight leadership"],
                "score_breakdown": {"requirements": 84, "experience": 90}
            }
            rec = ResumeAnalysis(
                user_id=self.test_user_id,
                job_role="Full Stack Development",
                ats_score=84.0,
                analysis_json=json.dumps(analysis_dict),
                filename="cached_resume.pdf",
                job_description="Senior Developer role",
                status="completed"
            )
            db.session.add(rec)
            db.session.commit()
            record_id = rec.id

        # Fresh /resume starts empty
        resp = self.client.get('/resume')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('window.__INITIAL_ANALYSIS__ = null;', html)

        # Explicit /resume?analysis_id=<id> loads the saved analysis
        explicit_resp = self.client.get(f'/resume?analysis_id={record_id}')
        self.assertEqual(explicit_resp.status_code, 200)
        explicit_html = explicit_resp.data.decode('utf-8')
        self.assertIn('"ats_score": 84', explicit_html)
        self.assertIn('Saved database summary test.', explicit_html)
        self.assertIn(f'window.__INITIAL_RECORD_ID__ = {record_id};', explicit_html)

if __name__ == '__main__':
    unittest.main()

