import uuid

from django.test import SimpleTestCase
from django.urls import reverse


class MockInterviewUrlTests(SimpleTestCase):
    def test_uuid_session_routes_reverse(self):
        public_id = uuid.uuid4()
        self.assertEqual(
            reverse("mock_interview:room", args=[public_id]),
            f"/mock-interview/session/{public_id}/",
        )
        self.assertEqual(
            reverse("mock_interview:session_status", args=[public_id]),
            f"/mock-interview/api/sessions/{public_id}/status/",
        )
        self.assertEqual(
            reverse("mock_interview:generate_report", args=[public_id]),
            f"/mock-interview/api/sessions/{public_id}/generate-report/",
        )
        self.assertEqual(
            reverse("mock_interview:runtime_status"),
            "/mock-interview/api/runtime/status/",
        )
