import json
from pathlib import Path


DOCS_PATH = Path(__file__).resolve().parent / "data" / "erp_docs.json"


class KnowledgeBase:
    def __init__(self):
        self.data = self._load_data()

    def _load_data(self):
        if not DOCS_PATH.exists():
            return {}
        try:
            return json.loads(DOCS_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def search_help(self, query):
        query_lower = query.lower()
        for content in self.data.values():
            if any(keyword in query_lower for keyword in content.get("keywords", [])):
                return content.get("response")
        return None

    def get_help_text(self, role):
        if role in {"Admin", "Administrator"}:
            return (
                "As Admin, you have institution-wide chatbot access.\n"
                "- List students across departments.\n"
                "- View academic profiles, marks, attendance, and reports.\n"
                "- Query subject allocations and class performance.\n"
                "- Review daily briefings and institution-scoped early-warning indicators."
            )
        if role == "HOD":
            return (
                "As HOD, you can:\n- List students in your department.\n"
                "- Analyze permitted student performance.\n"
                "- View subject-specific class reports.\n"
                "- Get daily briefings, pending-work lists, and early-warning alerts."
            )
        if role == "Vice Principal":
            return "As Vice Principal, you can query institution-level student profiles, marks, and reports."
        if role in {"Advisor", "CA", "Class Advisor", "Mentor", "Teacher", "Faculty"}:
            return (
                "You can:\n- List students assigned to your current role.\n"
                "- View subjects you handle.\n"
                "- Retrieve permitted student marks and performance details.\n"
                "- Get a daily briefing, pending-work checklist, and early-warning alerts.\n"
                "- Draft assessments, record mentor follow-ups, and submit reports with confirmation.\n"
                "Try: 'daily briefing', 'pending work', 'early warning students', or 'assessment assistant'."
            )
        return "I can help with ERP academic data available to your current faculty role."
