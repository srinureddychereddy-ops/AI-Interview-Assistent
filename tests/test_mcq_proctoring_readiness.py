import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db, User, ResumeAnalysis, set_user_selected_domain

class TestMCQProctoringReadiness(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        with self.app.app_context():
            self.user = User.query.filter_by(username='proctor_tester').first()
            if not self.user:
                self.user = User(username='proctor_tester', email='proctor_tester@example.com')
                self.user.password_hash = 'fakehash'
                db.session.add(self.user)
                db.session.commit()
            set_user_selected_domain('Backend Development', user=self.user)
            self.user_id = self.user.id

            # Add completed resume analysis with ATS >= 80 to unlock aptitude round
            existing_analysis = ResumeAnalysis.query.filter_by(user_id=self.user_id).first()
            if not existing_analysis:
                analysis = ResumeAnalysis(
                    user_id=self.user_id,
                    job_role='Backend Development',
                    ats_score=85.0,
                    analysis_json='{"ats_score": 85.0}',
                    status='completed'
                )
                db.session.add(analysis)
                db.session.commit()

    def test_interview_template_elements(self):
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.user_id)
            sess['target_domain'] = 'Backend Development'

        # Fetch /interview/setup page
        res = self.client.get('/interview/setup')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Verify essential DOM elements for hardware and proctoring
        self.assertIn('id="hardware-check-view"', html)
        self.assertIn('id="webcam-feed"', html)
        self.assertIn('id="camera-select-row"', html)
        self.assertIn('id="camera-source-select"', html)
        self.assertIn('id="camera-status-badge"', html)
        self.assertIn('id="mic-status-badge"', html)
        self.assertIn('id="network-status-badge"', html)
        self.assertIn('id="camera-retry-btn"', html)
        self.assertIn('id="hardware-retry-btn"', html)
        self.assertIn('id="permission-alert"', html)
        self.assertIn('id="start-interview-btn"', html)
        self.assertIn('disabled', html)

    def test_interview_javascript_compliance(self):
        js_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'js', 'interview.js')
        with open(js_path, encoding='utf-8') as f:
            js_code = f.read()

        # 1. Combined mediaDevices.getUserMedia with { video: true, audio: true }
        self.assertIn('navigator.mediaDevices.getUserMedia', js_code)
        self.assertIn('video: true', js_code)
        self.assertIn('audio: true', js_code)

        # 2. Distinct error handling for all 5 error types
        self.assertIn('NotAllowedError', js_code)
        self.assertIn('NotFoundError', js_code)
        self.assertIn('NotReadableError', js_code)
        self.assertIn('SecurityError', js_code)
        self.assertIn('AbortError', js_code)

        # 3. Precise browser settings instruction
        self.assertIn('Camera or microphone access is blocked', js_code)
        self.assertIn('address bar', js_code)
        self.assertIn('Retry', js_code)

        # 4. Device enumeration & Built-in laptop camera prioritization
        self.assertIn('navigator.mediaDevices.enumerateDevices', js_code)
        self.assertIn('scoreCameraDevice', js_code)
        self.assertIn('switchCameraDevice', js_code)
        self.assertIn('setupCameraSelection', js_code)
        self.assertIn('deviceId: { exact:', js_code)

        # 5. Verification of actual tracks
        self.assertIn('getVideoTracks()', js_code)
        self.assertIn('getAudioTracks()', js_code)

        # 6. Live preview attachment & loadedmetadata
        self.assertIn('webcamFeed.srcObject', js_code)
        self.assertIn('loadedmetadata', js_code)
        self.assertIn('webcamFeed.play()', js_code)

        # 7. Start button gating strictly requiring cameraCheckPassed && microphoneCheckPassed && networkCheckPassed
        self.assertIn('cameraCheckPassed && microphoneCheckPassed && networkCheckPassed', js_code)

        # 8. Cleanup handling on window unload/pagehide
        self.assertIn('beforeunload', js_code)
        self.assertIn('pagehide', js_code)
        self.assertIn('track.stop()', js_code)

    def test_camera_stream_lifecycle_and_recovery(self):
        js_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'js', 'interview.js')
        with open(js_path, encoding='utf-8') as f:
            js_code = f.read()

        # 1. Central recovery function & device resolution
        self.assertIn('async function recoverCamera()', js_code)
        self.assertIn('async function resolveTargetCameraDevice', js_code)
        self.assertIn('selectedCameraDeviceId', js_code)

        # 2. Race condition prevention
        self.assertIn('cameraRecoveryInProgress', js_code)

        # 3. Request new stream FIRST before stopping old stream
        self.assertIn('let newVideoStream = null;', js_code)
        self.assertIn('activeVideoStream.getVideoTracks().forEach', js_code)

        # 4. Strict verification of active video track and dimensions
        self.assertIn('waitForVideoReady', js_code)
        self.assertIn('videoWidth > 0', js_code)
        self.assertIn('videoHeight > 0', js_code)
        self.assertIn('readyState >= 2', js_code)

        # 5. Non-destructive track replacement preserving microphone
        self.assertIn('activeAudioStream', js_code)
        self.assertIn('new MediaStream([newVideoTrack, ...existingAudioTracks])', js_code)

        # 6. Busy device error message
        self.assertIn('Camera is currently being used by another application', js_code)

        # 7. Devicechange hotplug safety during assessment
        self.assertIn('HardwareMonitor] Currently selected camera was disconnected from the system!', js_code)
        self.assertIn('enforceProctoringLock("camera")', js_code)

        # 8. Reconnect button wired to recoverCamera
        self.assertIn('const cameraRecovered = await recoverCamera();', js_code)

if __name__ == '__main__':
    unittest.main()
