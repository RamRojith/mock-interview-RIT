import re
import random
import math
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.signals import user_logged_out
from django.db.models import Avg, Max, Min, Count, Q, Sum
from django.dispatch import receiver
from chatbot.models import Notification
from .knowledge_base import KnowledgeBase
from .student_prompts import (
    FACULTY_STUDENT_PERFORMANCE_SYSTEM_PROMPT,
    STUDENT_OVERALL_PERFORMANCE_SYSTEM_PROMPT,
    STUDENT_PERFORMANCE_SYSTEM_PROMPT,
)
from openai import OpenAI
from faculty_management.models import (
    Announcement,
    Assessment_master,
    AssessmentMark,
    general_information,
)
from examination_management.models import GPA, InternalAssessment, Result, StudentInternalMark
from course_management.models import (
    Course,
    CourseEnrollment,
    AssignSubjectFaculty,
    PeriodAllocation,
)
from user_accounts.models import USER, StudentDetails, Add_Department
from student_management.models import (
    Daily_Attendance,
    HourAttendance,
    StudentAchievements,
    StudentCO_EX_Curricular,
    StudentProjects,
    StudentPublication,
)


FACULTY_CANONICAL_SECTIONS = [
    "Student Details",
    "Strengths",
    "Weaknesses",
    "How to Overcome",
    "Recommendations",
    "Conclusion",
    "Data Note",
]

FACULTY_CORE_SECTIONS = [
    "Strengths",
    "Weaknesses",
    "How to Overcome",
    "Recommendations",
    "Conclusion",
]

FACULTY_SECTION_KEYS = {
    " ".join(section.split()).lower(): section
    for section in FACULTY_CANONICAL_SECTIONS
}

FACULTY_DATA_NOTE = (
    "**Data Note**\n"
    "1. This analysis uses only the ERP data supplied for the selected student "
    "within the authenticated faculty role's scope.\n"
    "2. Missing or unpublished records are shown as N/A and are not interpreted "
    "as poor performance."
)

logger = logging.getLogger(__name__)


class ERPBot:
    def __init__(self, conversation_state=None):
        self.kb = KnowledgeBase()
        self.conversation_state = conversation_state

    def _ai_client(self):
        return OpenAI(
            api_key=getattr(settings, "OLLAMA_API_KEY", "ollama"),
            base_url=settings.OLLAMA_BASE_URL,
            timeout=getattr(settings, "OLLAMA_TIMEOUT", 20.0),
        )

    def _ai_model(self):
        return settings.OLLAMA_MODEL

    def _ai_max_tokens(self):
        return getattr(settings, "OLLAMA_MAX_TOKENS", 900)

    def _student_queryset(self):
        """
        Restrict student selects to columns that exist in the live DB table.
        """
        return StudentDetails.objects.select_related("department", "ca", "mentor").only(
            "id",
            "name",
            "reg_no",
            "department",
            "department__id",
            "department__Department",
            "batch",
            "year",
            "semester",
            "section",
            "email",
            "mobile_no",
            "ca",
            "ca__name",
            "ca__college_email",
            "mentor",
            "mentor__name",
            "mentor__college_email",
        )

    def _get_latest_gcpa(self, student):
        """
        Use the latest available GPA/CGPA entry when present; otherwise return N/A.
        """
        try:
            latest_gpa = (
                GPA.objects.filter(student_id=student.id)
                .order_by("-academic_year", "-semester", "-id")
                .values_list("cgpa", flat=True)
                .first()
            )
            if latest_gpa is None:
                return "N/A"
            return str(round(float(latest_gpa), 2))
        except Exception:
            return "N/A"

    def _strip_model_reasoning(self, text, preserve_bold=False):
        cleaned = re.sub(
            r'<think>.*?(?:</think>|$)',
            '',
            text or '',
            flags=re.DOTALL | re.IGNORECASE,
        )
        if not preserve_bold:
            cleaned = cleaned.replace("**", "")
        return cleaned.strip()

    def _extract_named_section(self, text, header, next_headers=None):
        if not text:
            return ""

        next_headers = next_headers or []
        header_pattern = re.escape(header)
        if next_headers:
            next_pattern = "|".join(re.escape(item) for item in next_headers)
            pattern = (
                rf'(?is)(?:^|\n)\s*{header_pattern}\s*:\s*(.*?)'
                rf'(?=\n\s*(?:{next_pattern})\s*:|\Z)'
            )
        else:
            pattern = rf'(?is)(?:^|\n)\s*{header_pattern}\s*:\s*(.*)\Z'

        match = re.search(pattern, text)
        return match.group(1).strip() if match else ""

    def _is_placeholder_analysis_text(self, value):
        if value is None:
            return True

        normalized = " ".join(str(value).split()).strip()
        if not normalized:
            return True

        lowered = normalized.lower()
        if lowered in {"n/a", "na"}:
            return False

        placeholder_patterns = [
            r"^<[^>]+>$",
            r"^\{\{[^}]+\}\}$",
            r"\bstrength_\d+\b",
            r"\bweakness_\d+\b",
            r"\brecommendation_\d+\b",
            r"\bclear_summary_and_faculty_insight\b",
            r"\b1 to 3 concise points\b",
            r"\b1 to 3 actionable points\b",
            r"\bone concise summary paragraph\b",
            r"\bactual point\b",
            r"\bactual concise summary paragraph\b",
        ]
        return any(re.search(pattern, lowered) for pattern in placeholder_patterns)

    def _extract_section_items(self, section_text, limit=3):
        if not section_text:
            return []

        items = []
        for raw_line in section_text.splitlines():
            line = raw_line.strip()
            line = line.lstrip("\u2022").strip()
            line = re.sub(r'^(?:[-*•]+|\d+[.)])\s*', '', line)
            if line and not self._is_placeholder_analysis_text(line):
                items.append(" ".join(line.split()))

        if not items:
            compact = " ".join(section_text.split())
            if compact:
                sentence_items = [
                    chunk.strip()
                    for chunk in re.split(r'(?<=[.!?])\s+', compact)
                    if chunk.strip()
                ]
                items = sentence_items or [compact]

        return items[:limit]

    def _format_student_performance_analysis(
        self,
        current_scope,
        student,
        semester,
        latest_cgpa,
        performance_rows,
        attendance_rows,
        activity_counts=None,
        result_rows=None,
        recommendation_override=None,
    ):
        """Build a stable, evidence-based faculty view from ERP-calculated data."""
        total_obtained = sum(row.get("obtained") or 0 for row in performance_rows)
        total_maximum = sum(row.get("maximum") or 0 for row in performance_rows)
        mark_average = (
            round((total_obtained / total_maximum) * 100, 2)
            if total_maximum else None
        )
        ranked = sorted(
            performance_rows,
            key=lambda row: (
                -row.get("percentage", 0),
                str(row.get("course_code") or ""),
            ),
        )
        strongest = ranked[0] if ranked else None
        weakest = ranked[-1] if ranked else None

        attended_hours = sum(row.get("attended") or 0 for row in attendance_rows)
        total_hours = sum(row.get("total") or 0 for row in attendance_rows)
        attendance_percentage = (
            round((attended_hours / total_hours) * 100, 2)
            if total_hours else None
        )
        result_rows = list(result_rows or [])
        grade_totals = [
            row.get("grade_total") for row in result_rows
            if row.get("grade_total") is not None
        ]
        grade_total_average = (
            round(sum(grade_totals) / len(grade_totals), 2)
            if grade_totals else None
        )

        strengths = []
        if strongest:
            strengths.append(
                f"Strongest recorded subject: {strongest.get('course__title') or 'Subject'} "
                f"({strongest.get('course_code') or 'N/A'}) - {strongest.get('percentage')}%."
            )
        if attendance_percentage is not None and attendance_percentage >= 75:
            strengths.append(f"Overall recorded attendance is {attendance_percentage}%.")
        if not strengths:
            strengths.append(
                "No evidence-based strength can be identified because the required academic metrics are not recorded."
            )

        attention = []
        if weakest:
            attention.append(
                f"Subject requiring the most attention: {weakest.get('course__title') or 'Subject'} "
                f"({weakest.get('course_code') or 'N/A'}) - {weakest.get('percentage')}%."
            )
        if attendance_percentage is not None and attendance_percentage < 75:
            attention.append(
                f"Recorded attendance is {attendance_percentage}%, below the required 75% level."
            )
        if not attention:
            attention.append(
                "No evidence-based area of weakness is identified from the currently recorded metrics."
            )

        recommendations = []
        if weakest:
            recommendations.append(
                f"Review the lowest-scoring topics in {weakest.get('course__title') or 'the subject needing attention'} "
                "and discuss unresolved concepts with the subject faculty."
            )
        if attendance_percentage is not None and attendance_percentage < 75:
            recommendations.append(
                "Prioritize upcoming classes and confirm the attendance recovery requirement with the class advisor."
            )
        if not recommendations:
            recommendations.append(
                "Review this analysis after marks or attendance are published; the current ERP record is insufficient for targeted advice."
            )
        if recommendation_override:
            recommendations = recommendation_override

        department_name = (
            getattr(getattr(student, "department", None), "Department", None)
            or "N/A"
        )
        lines = [
            f"**Student Performance Analysis | Semester {semester or 'N/A'}**",
            "",
            "**Student Details**",
            f"1. **Student Name:** {student.name or 'N/A'}",
            f"2. **Department:** {department_name}",
            f"3. **Year / Section:** {student.year or 'N/A'} / {student.section or 'N/A'}",
            f"4. **Access Scope:** {current_scope}",
            "",
            "**Recorded Academic Summary**",
            (
                f"1. **Internal-Mark Average:** {mark_average}%"
                if mark_average is not None
                else "1. **Internal-Mark Average:** N/A"
            ),
            (
                f"2. **Attendance:** {attended_hours}/{total_hours} ({attendance_percentage}%)"
                if attendance_percentage is not None
                else "2. **Attendance:** N/A"
            ),
            f"3. **Semester CGPA:** {latest_cgpa or 'N/A'}",
            f"4. **Published End-Semester Results:** {len(result_rows)}",
            (
                f"5. **Average Published Grade Total:** {grade_total_average}"
                if grade_total_average is not None
                else "5. **Average Published Grade Total:** N/A"
            ),
        ]
        if activity_counts is not None:
            lines.extend([
                f"6. **Achievements:** {activity_counts.get('achievements', 'N/A')}",
                f"7. **Co-Curricular Records:** {activity_counts.get('co_curricular', 'N/A')}",
                f"8. **Publications:** {activity_counts.get('publications', 'N/A')}",
                f"9. **Projects:** {activity_counts.get('projects', 'N/A')}",
            ])
        if result_rows:
            lines.extend(["", "**Published End-Semester Subject Results**"])
            for index, row in enumerate(result_rows, start=1):
                lines.append(
                    f"{index}. **{row.get('course__title') or 'Subject'} "
                    f"({row.get('course__course_code') or 'N/A'})** - "
                    f"Grade: {row.get('grade') or 'N/A'} | "
                    f"Grade Total: {row.get('grade_total') if row.get('grade_total') is not None else 'N/A'}"
                )
        lines.extend(["", "**Strengths**"])
        lines.extend(
            f"{index}. {item}" for index, item in enumerate(strengths, start=1)
        )
        lines.extend(["", "**Areas Needing Attention**"])
        lines.extend(
            f"{index}. {item}" for index, item in enumerate(attention, start=1)
        )
        lines.extend(["", "**Recommendations**"])
        lines.extend(
            f"{index}. {item}" for index, item in enumerate(recommendations, start=1)
        )
        lines.extend([
            "",
            "**Data Note**",
            "1. This analysis uses only ERP records currently available within the authenticated user's role scope.",
            "2. Missing or unpublished data is shown as N/A and is not interpreted as poor performance.",
        ])
        return "\n".join(lines)

    def _filter_faculty_performance_snapshot(self, snapshot, permitted_codes=None, include_gpa=True):
        """Apply the already-authorized Subject Faculty course scope to one snapshot."""
        permitted = {
            str(code or "").strip().upper()
            for code in (permitted_codes or [])
            if str(code or "").strip()
        }
        if permitted_codes is None:
            marks = list(snapshot["marks"])
            attendance = list(snapshot["attendance"])
            results = list(snapshot["results"])
        else:
            marks = [
                row for row in snapshot["marks"]
                if str(row.get("course_code") or "").strip().upper() in permitted
            ]
            attendance = [
                row for row in snapshot["attendance"]
                if str(row.get("course__course_code") or "").strip().upper() in permitted
            ]
            results = [
                row for row in snapshot["results"]
                if str(row.get("course__course_code") or "").strip().upper() in permitted
            ]
        return {
            **snapshot,
            "marks": marks,
            "attendance": attendance,
            "results": results,
            "gpa": snapshot["gpa"] if include_gpa else None,
        }

    def _faculty_snapshot_has_data(self, snapshot):
        return bool(
            snapshot["marks"]
            or snapshot["attendance"]
            or snapshot["results"]
            or snapshot["gpa"]
        )

    def _faculty_ai_recommendations(self, analysis_scope, student, snapshots):
        """Ask Ollama only for grounded action items; factual sections stay deterministic."""
        mark_lines = []
        attendance_lines = []
        for snapshot in snapshots:
            semester = snapshot["semester"]
            mark_lines.extend(
                f"Semester {semester}: {row.get('course__title') or 'Subject'} "
                f"({row.get('course_code') or 'N/A'}) {row.get('percentage')}%"
                for row in snapshot["marks"]
            )
            attendance_lines.extend(
                f"Semester {semester}: {row.get('course__title') or 'Subject'} "
                f"({row.get('course__course_code') or 'N/A'}) "
                f"{round(((row.get('attended') or 0) / row.get('total')) * 100, 2)}%"
                for row in snapshot["attendance"]
                if row.get("total")
            )
        if not mark_lines and not attendance_lines:
            return None

        if analysis_scope == "overall":
            focus = (
                "Give 4 to 6 long-term academic and career actions covering consistency, "
                "technical skills, projects or internships, certifications, placement or "
                "higher-study preparation, communication, and attendance when relevant."
            )
        else:
            focus = (
                "Give 3 to 5 short-term actions only for the selected semester, focusing on "
                "weak subjects, attendance, assessment preparation, and study strategy."
            )
        prompt = (
            "You create action recommendations for a faculty-facing ERP performance report. "
            "Use only the supplied authorized metrics. Do not invent marks, attendance, GPA, "
            "participation, causes, rankings, or personal facts. Return only numbered imperative "
            f"action items with no heading or conclusion. {focus}"
        )
        context = (
            f"Scope: {analysis_scope}\n"
            f"Department: {getattr(getattr(student, 'department', None), 'Department', None) or 'N/A'}\n"
            f"Recorded marks:\n{chr(10).join(mark_lines) or 'N/A'}\n"
            f"Recorded attendance:\n{chr(10).join(attendance_lines) or 'N/A'}"
        )
        try:
            response = self._ai_client().chat.completions.create(
                model=self._ai_model(),
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": context},
                ],
                temperature=0.1,
                max_tokens=min(self._ai_max_tokens(), 450),
            )
            cleaned = self._strip_model_reasoning(
                response.choices[0].message.content,
                preserve_bold=False,
            )
            actions = []
            for raw_line in cleaned.splitlines():
                line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", raw_line).strip()
                if not line:
                    continue
                lowered = line.lower()
                if re.search(r"\b(?:student|they|he|she)\s+(?:is|has|shows|scored)\b", lowered):
                    return None
                actions.append(line)
            minimum = 4 if analysis_scope == "overall" else 3
            maximum = 6 if analysis_scope == "overall" else 5
            if minimum <= len(actions) <= maximum:
                return actions
        except Exception:
            pass
        return None

    def _faculty_student_details_block(self, student):
        department_name = (
            getattr(getattr(student, "department", None), "Department", None)
            or "N/A"
        )
        return "\n".join([
            "**Student Details**",
            f"1. **Name:** {getattr(student, 'name', None) or 'N/A'}",
            f"2. **Register Number:** {getattr(student, 'reg_no', None) or 'N/A'}",
            f"3. **Department:** {department_name}",
            f"4. **Batch:** {getattr(student, 'batch', None) or 'N/A'}",
            f"5. **Year:** {getattr(student, 'year', None) or 'N/A'}",
            f"6. **Semester:** {getattr(student, 'semester', None) or 'N/A'}",
            f"7. **Section:** {getattr(student, 'section', None) or 'N/A'}",
        ])

    @staticmethod
    def _normalize_faculty_heading(line):
        line = line.strip()
        line = re.sub(r"^[#>*_~`\-\s]+", "", line)
        line = re.sub(r"^\d+[.)]\s*", "", line)
        line = re.sub(r"^[#>*_~`\-\s]+", "", line)
        line = line.strip("#*>_~`").strip()
        line = re.sub(r"[:.,\-\s]+$", "", line)
        return " ".join(line.split()).lower()

    def _canonicalize_faculty_headings(self, text):
        lines = []
        for raw_line in (text or "").splitlines():
            line = raw_line.strip()
            if re.fullmatch(r"`{3,}|~{3,}", line):
                continue
            if re.fullmatch(r"[*_\-]{3,}", line):
                continue
            normalized = self._normalize_faculty_heading(line)
            if normalized in FACULTY_SECTION_KEYS:
                lines.append(f"**{FACULTY_SECTION_KEYS[normalized]}**")
                continue
            line = re.sub(r"^#{1,6}\s+", "", line)
            lines.append(line)
        return "\n".join(lines).strip()

    def _found_faculty_sections(self, text):
        return {
            section
            for section in FACULTY_CANONICAL_SECTIONS
            if f"**{section}**" in (text or "")
        }

    def _faculty_ai_student_performance_report(
        self,
        analysis_scope,
        student,
        snapshots,
        activity_counts=None,
    ):
        """Ask Ollama for the full faculty-facing student performance report.

        Returns the validated AI report text or None so the caller can fall
        back to the deterministic formatted analysis on any failure.
        """
        if not snapshots:
            return None

        department_name = (
            getattr(getattr(student, "department", None), "Department", None)
            or "N/A"
        )
        lines = [
            f"Name: {getattr(student, 'name', None) or 'N/A'}",
            f"Register Number: {getattr(student, 'reg_no', None) or 'N/A'}",
            f"Department: {department_name}",
            f"Batch: {getattr(student, 'batch', None) or 'N/A'}",
            f"Year: {getattr(student, 'year', None) or 'N/A'}",
            f"Semester: {getattr(student, 'semester', None) or 'N/A'}",
            f"Section: {getattr(student, 'section', None) or 'N/A'}",
        ]

        for snapshot in snapshots:
            semester = snapshot.get("semester")
            academic_year = snapshot.get("academic_year") or "N/A"
            lines.append("")
            lines.append(f"Semester {semester} ({academic_year}):")
            marks = snapshot.get("marks") or []
            if marks:
                lines.append("Recorded subject marks:")
                lines.extend(
                    f"- {row.get('course__title') or 'Subject'} "
                    f"({row.get('course_code') or 'N/A'}): "
                    f"{row.get('percentage') if row.get('percentage') is not None else 'N/A'}%"
                    for row in marks
                )
            else:
                lines.append("Recorded subject marks: N/A")
            attendance = snapshot.get("attendance") or []
            if attendance:
                lines.append("Recorded attendance:")
                for row in attendance:
                    if row.get("total"):
                        percentage = round(
                            ((row.get("attended") or 0) / row["total"]) * 100, 2
                        )
                    else:
                        percentage = None
                    lines.append(
                        f"- {row.get('course__title') or 'Subject'} "
                        f"({row.get('course__course_code') or 'N/A'}): "
                        f"{percentage if percentage is not None else 'N/A'}%"
                    )
            else:
                lines.append("Recorded attendance: N/A")
            gpa = snapshot.get("gpa") or {}
            lines.append(
                f"GPA/CGPA: GPA {gpa.get('gpa') if gpa.get('gpa') is not None else 'N/A'}, "
                f"CGPA {gpa.get('cgpa') if gpa.get('cgpa') is not None else 'N/A'}"
            )
            results = snapshot.get("results") or []
            if results:
                lines.append("Published end-semester results:")
                lines.extend(
                    f"- {row.get('course__title') or 'Subject'} "
                    f"({row.get('course__course_code') or 'N/A'}): "
                    f"Grade {row.get('grade') or 'N/A'}, "
                    f"grade total {row.get('grade_total') if row.get('grade_total') is not None else 'N/A'}"
                    for row in results
                )
            else:
                lines.append("Published end-semester results: N/A")

        if activity_counts is not None:
            lines.extend([
                "",
                "Recorded development activities:",
                f"- Achievements: {activity_counts.get('achievements', 'N/A')}",
                f"- Co-curricular records: {activity_counts.get('co_curricular', 'N/A')}",
                f"- Publications: {activity_counts.get('publications', 'N/A')}",
                f"- Projects: {activity_counts.get('projects', 'N/A')}",
            ])
        else:
            lines.extend(["", "Recorded development activities: N/A"])

        user_message = "\n".join(lines)
        try:
            response = self._ai_client().chat.completions.create(
                model=self._ai_model(),
                messages=[
                    {
                        "role": "system",
                        "content": FACULTY_STUDENT_PERFORMANCE_SYSTEM_PROMPT,
                    },
                    {"role": "user", "content": user_message},
                ],
                temperature=0.1,
                max_tokens=min(max(self._ai_max_tokens(), 1500), 4096),
            )
            ai_text = self._strip_model_reasoning(
                response.choices[0].message.content,
                preserve_bold=True,
            )
            canonical_text = self._canonicalize_faculty_headings(ai_text)
            found = self._found_faculty_sections(canonical_text)
            if found.issuperset(FACULTY_CORE_SECTIONS):
                if "Student Details" not in found:
                    canonical_text = (
                        self._faculty_student_details_block(student)
                        + "\n\n"
                        + canonical_text
                    )
                if "Data Note" not in found:
                    canonical_text = canonical_text + "\n\n" + FACULTY_DATA_NOTE
                return canonical_text
            logger.warning(
                "Faculty AI performance report rejected for %s: missing sections %s",
                getattr(student, "reg_no", "N/A"),
                sorted(set(FACULTY_CORE_SECTIONS) - found),
            )
        except Exception as exc:
            logger.warning(
                "Faculty AI performance report call failed for %s: %s",
                getattr(student, "reg_no", "N/A"),
                exc,
            )
        return None

    def _format_overall_student_performance_analysis(
        self,
        current_scope,
        student,
        snapshots,
        activity_counts,
        recommendation_override=None,
    ):
        """Format an authorized cumulative faculty analysis across recorded semesters."""
        mark_records = []
        semester_summaries = []
        total_attended = 0
        total_hours = 0
        published_results = 0
        result_grade_totals = []
        for snapshot in snapshots:
            semester = snapshot["semester"]
            marks = snapshot["marks"]
            obtained = sum(row.get("obtained") or 0 for row in marks)
            maximum = sum(row.get("maximum") or 0 for row in marks)
            mark_average = round((obtained / maximum) * 100, 2) if maximum else None
            attended = sum(row.get("attended") or 0 for row in snapshot["attendance"])
            hours = sum(row.get("total") or 0 for row in snapshot["attendance"])
            attendance_percentage = round((attended / hours) * 100, 2) if hours else None
            total_attended += attended
            total_hours += hours
            published_results += len(snapshot["results"])
            result_grade_totals.extend(
                row.get("grade_total") for row in snapshot["results"]
                if row.get("grade_total") is not None
            )
            for row in marks:
                mark_records.append({**row, "semester": semester})
            semester_summaries.append({
                "semester": semester,
                "academic_year": snapshot["academic_year"],
                "mark_average": mark_average,
                "attendance_percentage": attendance_percentage,
                "gpa": (snapshot["gpa"] or {}).get("gpa"),
                "cgpa": (snapshot["gpa"] or {}).get("cgpa"),
            })

        obtained = sum(row.get("obtained") or 0 for row in mark_records)
        maximum = sum(row.get("maximum") or 0 for row in mark_records)
        cumulative_average = round((obtained / maximum) * 100, 2) if maximum else None
        cumulative_attendance = (
            round((total_attended / total_hours) * 100, 2) if total_hours else None
        )
        gpa_summaries = [
            summary for summary in semester_summaries if summary["gpa"] is not None
        ]
        latest_cgpa = next(
            (
                summary["cgpa"]
                for summary in reversed(semester_summaries)
                if summary["cgpa"] is not None
            ),
            None,
        )
        end_semester_average = (
            round(sum(result_grade_totals) / len(result_grade_totals), 2)
            if result_grade_totals else None
        )

        ranked = sorted(
            mark_records,
            key=lambda row: (-row.get("percentage", 0), row["semester"], str(row.get("course_code") or "")),
        )
        strongest_rows = ranked[:3]
        weakest_rows = sorted(
            mark_records,
            key=lambda row: (row.get("percentage", 0), row["semester"], str(row.get("course_code") or "")),
        )[:3]

        trend_points = gpa_summaries or [
            summary for summary in semester_summaries
            if summary["mark_average"] is not None
        ]
        trend_text = "N/A - at least two comparable semesters are required."
        if len(trend_points) >= 2:
            uses_gpa = bool(gpa_summaries)
            metric = "gpa" if uses_gpa else "mark_average"
            first = trend_points[0]
            latest = trend_points[-1]
            change = round(latest[metric] - first[metric], 2)
            direction = "improved" if change > 0 else "declined" if change < 0 else "remained consistent"
            suffix = "" if uses_gpa else "%"
            label = "GPA" if uses_gpa else "internal-mark average"
            trend_text = (
                f"{label} {direction} from {first[metric]}{suffix} in Semester {first['semester']} "
                f"to {latest[metric]}{suffix} in Semester {latest['semester']}."
            )

        department_name = (
            getattr(getattr(student, "department", None), "Department", None) or "N/A"
        )
        semester_labels = ", ".join(
            str(snapshot["semester"]) for snapshot in snapshots
        )
        strengths = [
            f"{row.get('course__title') or 'Subject'} ({row.get('course_code') or 'N/A'}), "
            f"Semester {row['semester']} - {row.get('percentage')}%."
            for row in strongest_rows
        ] or ["No evidence-based academic strength is available in the recorded data."]
        attention = [
            f"{row.get('course__title') or 'Subject'} ({row.get('course_code') or 'N/A'}), "
            f"Semester {row['semester']} - {row.get('percentage')}%."
            for row in weakest_rows
        ] or ["No evidence-based academic weakness is available in the recorded data."]
        if cumulative_attendance is not None and cumulative_attendance < 75:
            attention.append(
                f"Cumulative recorded attendance is {cumulative_attendance}%, below 75%."
            )

        lines = [
            "**Overall Student Performance Analysis**",
            "",
            "**Student Details**",
            f"1. **Student Name:** {student.name or 'N/A'}",
            f"2. **Register Number:** {student.reg_no or 'N/A'}",
            f"3. **Department:** {department_name}",
            f"4. **Year / Section:** {student.year or 'N/A'} / {student.section or 'N/A'}",
            f"5. **Access Scope:** {current_scope}",
            "",
            "**Cumulative Academic Summary**",
            f"1. **Recorded Semesters:** {semester_labels}",
            (
                f"2. **Cumulative Internal-Mark Average:** {cumulative_average}%"
                if cumulative_average is not None
                else "2. **Cumulative Internal-Mark Average:** N/A"
            ),
            (
                f"3. **Cumulative Attendance:** {total_attended}/{total_hours} ({cumulative_attendance}%)"
                if cumulative_attendance is not None
                else "3. **Cumulative Attendance:** N/A"
            ),
            f"4. **Latest CGPA:** {latest_cgpa if latest_cgpa is not None else 'N/A'}",
            f"5. **Published End-Semester Subject Results:** {published_results}",
            (
                f"6. **Average Published Grade Total:** {end_semester_average}"
                if end_semester_average is not None
                else "6. **Average Published Grade Total:** N/A"
            ),
            "",
            "**Long-Term Strengths**",
        ]
        lines.extend(f"{index}. {item}" for index, item in enumerate(strengths, start=1))
        lines.extend(["", "**Recurring Areas Needing Attention**"])
        lines.extend(f"{index}. {item}" for index, item in enumerate(attention, start=1))
        lines.extend(["", "**Academic Trends and Consistency**", f"1. {trend_text}"])
        for index, summary in enumerate(semester_summaries, start=2):
            lines.append(
                f"{index}. Semester {summary['semester']}: "
                f"Internal average {summary['mark_average'] if summary['mark_average'] is not None else 'N/A'}%, "
                f"attendance {summary['attendance_percentage'] if summary['attendance_percentage'] is not None else 'N/A'}%, "
                f"GPA {summary['gpa'] if summary['gpa'] is not None else 'N/A'}."
            )
        action_plan = recommendation_override or [
            "Maintain a semester-by-semester study plan and review progress after every assessment.",
            "Strengthen technical fundamentals through coding practice, problem-solving, and subject-related projects.",
            "Pursue relevant internships, hackathons, certifications, research, or project-showcase opportunities.",
            "Build a portfolio containing verified projects, achievements, certifications, and practical work.",
            "Improve communication, aptitude, interview, and teamwork skills for placement readiness.",
            "Discuss higher-study or career goals with the mentor and align elective, project, and certification choices accordingly.",
        ]
        if cumulative_attendance is not None and cumulative_attendance < 75:
            action_plan.append(
                "Give immediate priority to attendance recovery in accordance with ERP and department rules."
            )
        lines.extend([
            "",
            "**Long-Term Academic and Career Action Plan**",
        ])
        lines.extend(
            f"{index}. {action}" for index, action in enumerate(action_plan, start=1)
        )
        lines.extend([
            "",
            "**Recorded Development Activities**",
            f"1. **Achievements:** {activity_counts.get('achievements', 'N/A')}",
            f"2. **Co-Curricular Records:** {activity_counts.get('co_curricular', 'N/A')}",
            f"3. **Publications:** {activity_counts.get('publications', 'N/A')}",
            f"4. **Projects:** {activity_counts.get('projects', 'N/A')}",
            "",
            "**Data Note**",
            "1. This overall analysis uses all currently recorded ERP data available up to today within the authenticated user's role scope.",
            "2. Missing or unpublished records are shown as N/A and are not interpreted as poor performance.",
        ])
        return "\n".join(lines)

    def clear_chatbot_logout_state(self, request=None, user=None):
        """
        Remove chatbot-only session/message state on faculty logout without touching reports.
        """
        if request and getattr(request, "session", None):
            session_keys = [
                key
                for key in list(request.session.keys())
                if key.startswith("greeted_")
                or key.startswith("chatbot_")
                or key.startswith("erp_chat_")
            ]
            for key in session_keys:
                request.session.pop(key, None)
            if session_keys:
                request.session.modified = True

        candidate_ids = set()
        if request and getattr(request, "session", None):
            employee_id = request.session.get("employee_id")
            if employee_id:
                candidate_ids.add(str(employee_id).strip())

        if user:
            for attr in ("Employee_id", "employee_id", "id"):
                value = getattr(user, attr, None)
                if value not in (None, ""):
                    candidate_ids.add(str(value).strip())

        if not candidate_ids:
            return

        faculty_lookup = Q()
        for value in candidate_ids:
            faculty_lookup |= Q(faculty_id=value)
            if str(value).isdigit():
                faculty_lookup |= Q(id=int(value))

        faculty_record_ids = list(
            general_information.objects.filter(faculty_lookup).values_list("id", flat=True)
        )
        if not faculty_record_ids:
            return

        Notification.objects.filter(
            Q(message__startswith="CHATBOT|") | Q(message__startswith="ERP_CHAT|"),
            Q(sender_id__in=faculty_record_ids) | Q(receiver_id__in=faculty_record_ids),
        ).delete()

    def _approval_db_alias(self):
        if "approval_system" in settings.DATABASES:
            return "approval_system"
        if "rit_approval_system" in settings.DATABASES:
            return "rit_approval_system"
        return None

    def _approval_user_queryset(self):
        alias = self._approval_db_alias()
        if alias:
            return USER.objects.using(alias).all()
        return USER.objects.all()

    def _get_approval_user(self, faculty_id):
        try:
            return (
                self._approval_user_queryset()
                .select_related("role", "Department")
                .filter(Employee_id=str(faculty_id), is_active=1)
                .order_by("id")
                .first()
            )
        except Exception:
            return None

    def _is_role_id_11_user(self, faculty_id, active_role=None):
        active_role_normalized = (active_role or "").strip().upper()
        if active_role_normalized == "JA":
            return True

        approval_user = self._get_approval_user(faculty_id)
        return bool(approval_user and approval_user.role_id == 11)

    def _normalize_role_name(self, active_role):
        return re.sub(r"\s+", " ", str(active_role or "")).strip().lower()

    def _is_admin_role(self, active_role):
        return self._normalize_role_name(active_role) in {"admin", "administrator"}

    def _is_vp_role(self, active_role):
        return self._normalize_role_name(active_role) == "vice principal" or self._is_admin_role(active_role)

    def _is_hod_role(self, active_role):
        return self._normalize_role_name(active_role) in {
            "hod", "head of department", "head of the department"
        }

    def _is_ca_role(self, active_role):
        return self._normalize_role_name(active_role) in {"advisor", "ca", "class advisor"}

    def _is_mentor_role(self, active_role):
        return self._normalize_role_name(active_role) == "mentor"

    def _has_role(self, target, active_role, all_roles=None):
        """Return True if the user holds *target* in active_role or any all_roles entry."""
        if self._is_ca_role(target):
            if self._is_ca_role(active_role):
                return True
            return any(self._is_ca_role(r) for r in (all_roles or []))
        if self._is_mentor_role(target):
            if self._is_mentor_role(active_role):
                return True
            return any(self._is_mentor_role(r) for r in (all_roles or []))
        normalized_target = self._normalize_role_name(target)
        return (
            self._normalize_role_name(active_role) == normalized_target
            or any(self._normalize_role_name(r) == normalized_target for r in (all_roles or []))
        )

    def _resolve_effective_role(self, active_role, all_roles):
        """Pick the highest-scope role the user holds from all_roles."""
        if not all_roles:
            return active_role
        role_precedence = [
            ({"admin", "administrator"}, "Admin"),
            ({"vice principal"}, "Vice Principal"),
            ({"hod", "head of department", "head of the department"}, "HOD"),
            ({"advisor", "ca", "class advisor"}, "Class Advisor"),
            ({"mentor"}, "Mentor"),
            ({"subject faculty", "subject teacher", "teacher", "faculty"}, "Faculty"),
        ]
        normalized_map = {}
        for role in all_roles:
            normalized_map[self._normalize_role_name(role)] = role
        for aliases, canonical in role_precedence:
            if aliases.intersection(normalized_map):
                return canonical
        return active_role

    def _is_teacher_role(self, active_role):
        return self._normalize_role_name(active_role) in {
            "teacher", "faculty", "subject faculty", "subject teacher"
        }

    def _is_student_role(self, active_role):
        return self._normalize_role_name(active_role) == "student"

    def _canonical_role(self, role):
        normalized = self._normalize_role_name(role)
        aliases = {
            "admin": "Admin",
            "administrator": "Admin",
            "vice principal": "Vice Principal",
            "hod": "HOD",
            "head of department": "HOD",
            "head of the department": "HOD",
            "advisor": "Class Advisor",
            "ca": "Class Advisor",
            "class advisor": "Class Advisor",
            "mentor": "Mentor",
            "teacher": "Faculty",
            "faculty": "Faculty",
            "subject faculty": "Faculty",
            "subject teacher": "Faculty",
        }
        return aliases.get(normalized, str(role or "").strip())

    def _student_list_role_hint(self, query):
        """Return the role explicitly named by a student-list request.

        An empty string means the request is a student list but does not identify
        which of the user's roles should supply the scope. None means it is not a
        student-list request and normal intent routing should continue.
        """
        text = self._normalize_role_name(query)
        analytics_terms = [
            "attendance", "marks", "performance", "report", "top", "top student",
            "low student", "cgpa", "gpa", "result", "need mentoring",
            "publication", "published", "project", "achievement",
            "co-curricular", "co curricular", "curricular",
        ]
        if any(term in text for term in analytics_terms):
            return None

        mentor_terms = [
            "mentee", "mentees", "mentor student", "mentor students",
            "my mentor students", "under my mentorship", "under mentorship",
            "advisee", "advisees",
        ]
        if any(term in text for term in mentor_terms):
            return "Mentor"

        department_terms = [
            "department students", "department student", "my department students",
            "students in my department", "students from my department",
        ]
        if any(term in text for term in department_terms):
            return "HOD"

        class_terms = [
            "my class", "my classes", "class students", "class student", "my ca students",
            "ca students", "advisor students", "class advisor students",
        ]
        if any(term in text for term in class_terms):
            return "Class Advisor"

        subject_terms = [
            "subject students", "subject student", "students for my subject",
            "students in my subject", "my subject students", "students enrolled in",
        ]
        students_taking_subject = bool(
            re.search(r"\bstudents?\s+(?:taking|studying)\s+[a-z]{2,}\d{3,}[a-z]*\b", text)
        )
        if any(term in text for term in subject_terms) or students_taking_subject:
            return "Faculty"

        generic_terms = [
            "my students", "my student", "list students", "show students",
            "get students", "student list", "display students", "show me students",
            "who are the students",
        ]
        if any(term in text for term in generic_terms):
            return ""
        return None

    def _resolve_student_list_role(self, query, active_role, all_roles=None):
        requested_role = self._student_list_role_hint(query)
        if requested_role is None:
            return None, None

        assigned_roles = {
            self._canonical_role(role)
            for role in (all_roles or [active_role])
            if str(role or "").strip()
        }
        active_canonical = self._canonical_role(active_role)
        if active_canonical:
            assigned_roles.add(active_canonical)

        # Institution-wide roles retain their normal broad authorization.
        if "Admin" in assigned_roles:
            return "Admin", None
        if "Vice Principal" in assigned_roles:
            return "Vice Principal", None

        if requested_role:
            if requested_role not in assigned_roles:
                return None, (
                    f"Access denied: this request requires your {requested_role} role, "
                    "but that role is not assigned to your account."
                )
            return requested_role, None

        student_roles = assigned_roles.intersection(
            {"HOD", "Class Advisor", "Mentor", "Faculty"}
        )
        if len(student_roles) == 1:
            return next(iter(student_roles)), None
        if len(student_roles) > 1:
            labels = ", ".join(sorted(student_roles))
            return None, (
                "Please specify which role to use for this student request "
                f"({labels}), for example: 'my mentees', 'my class students', "
                "'subject students', or 'my department students'."
            )
        return None, "Access denied: none of your assigned roles can list students."

    def _student_analytics_role_hint(self, query):
        """Return the explicit student scope named inside an analytics request."""
        text = self._normalize_role_name(query)

        mentor_terms = [
            "mentee", "mentees", "mentor student", "mentor students",
            "my mentor students", "under my mentorship", "under mentorship",
            "advisee", "advisees",
        ]
        if any(term in text for term in mentor_terms):
            return "Mentor"

        department_terms = [
            "department students", "department student", "my department students",
            "students in my department", "students from my department",
        ]
        if any(term in text for term in department_terms):
            return "HOD"

        class_terms = [
            "my class", "my classes", "class students", "class student",
            "my ca students", "ca students", "advisor students",
            "class advisor students",
        ]
        if any(term in text for term in class_terms):
            return "Class Advisor"

        return None

    def _resolve_student_analytics_role(self, query, active_role, all_roles=None):
        """Choose the authorized role for scoped student analytics queries."""
        requested_role = self._student_analytics_role_hint(query)
        if not requested_role:
            return active_role, None

        assigned_roles = {
            self._canonical_role(role)
            for role in (all_roles or [active_role])
            if str(role or "").strip()
        }
        active_canonical = self._canonical_role(active_role)
        if active_canonical:
            assigned_roles.add(active_canonical)

        if requested_role not in assigned_roles:
            return None, (
                f"Access denied: this request requires your {requested_role} role, "
                "but that role is not assigned to your account."
            )
        return requested_role, None

    def _resolve_class_report_role(self, active_role, all_roles=None):
        """Choose the broadest verified academic role for a class report."""
        assigned_roles = {
            self._canonical_role(role)
            for role in (all_roles or [active_role])
            if str(role or "").strip()
        }
        assigned_roles.add(self._canonical_role(active_role))
        active_canonical = self._canonical_role(active_role)
        if active_canonical == "Mentor" and "Mentor" in assigned_roles:
            return "Mentor"
        for role in (
            "Admin", "Vice Principal", "HOD", "Class Advisor", "Faculty", "Mentor"
        ):
            if role in assigned_roles:
                return role
        return self._canonical_role(active_role)

    def _department_name(self, department_obj):
        if not department_obj:
            return ""
        return (
            getattr(department_obj, "Department", None)
            or getattr(department_obj, "department", None)
            or ""
        ).strip().lower()

    def _same_department(self, left_dept, right_dept):
        if not left_dept or not right_dept:
            return False

        left_id = getattr(left_dept, "id", None)
        right_id = getattr(right_dept, "id", None)
        if left_id is not None and right_id is not None and left_id == right_id:
            return True

        left_name = self._department_name(left_dept)
        right_name = self._department_name(right_dept)
        if left_name and right_name and left_name == right_name:
            return True

        return False

    def _department_student_queryset(self, department_obj):
        if not department_obj:
            return self._student_queryset().none()

        return self._student_queryset().filter(department=department_obj)
    
    def process_query(
        self,
        user_query,
        faculty_id,
        role=None,
        all_roles=None,
        is_first_message=False,
        conversation_state=None,
    ):
        """
        Main entry point for processing user queries.
        active_role: The currently selected role in the ERP dashboard.
        """
        raw_query = user_query.strip()
        query = raw_query.lower()
        active_role = role  # Strict authority
        if conversation_state is None:
            conversation_state = self.conversation_state

        # ROLE RESOLUTION: If the user holds a higher-scope role (e.g.
        # Class Advisor, Mentor, HOD) in all_roles, promote active_role so
        # every downstream handler sees the correct authorization scope.
        if all_roles and not self._is_student_role(active_role):
            active_role = self._resolve_effective_role(active_role, all_roles)

        # FAIL-SAFE: If active role is missing or invalid, do not answer or deny.
        if not active_role:
             return "I'm sorry, I cannot perform any actions without an active role selection from your dashboard."

        # FAIL-SAFE: We need at least a faculty_id
        if not faculty_id:
             return "I'm sorry, I cannot perform any actions without a valid user identity."

        # Student requests use a separate self-service router and never enter
        # faculty, HOD, or administrator data-access paths.
        if self._is_student_role(active_role):
            return self._process_student_query(
                raw_query,
                str(faculty_id).strip(),
                is_first_message=is_first_message,
            )
        
        faculty_name = None
        faculty_info = self._get_faculty_info(faculty_id)
        if faculty_info:
            faculty_name = faculty_info.name
        
        # AUTHENTICATION FAILURE: Name is mandatory
        if self._is_admin_role(active_role) and not faculty_name:
            faculty_name = "Administrator"
        elif not faculty_name:
            return f"Authentication Error: Unable to retrieve your profile information. Please contact system administrator. (ID: {faculty_id})"
        
        # 0. Greeting & help keywords (expanded for better conversational detection)
        greeting_keywords = [
            "hi", "hello", "hey", "hey there", "hi there", "start",
            "good morning", "good afternoon", "good evening", "greetings",
            "morning", "afternoon", "evening", "what's up", "whats up", "hola"
        ]
        help_keywords = [
            "help", "what can you do", "can you help", "how to use", "guide",
            "who are you", "usage", "options", "commands", "what do you do"
        ]

        def normalized_short_message(text):
            return " ".join(str(text or "").split()).strip(" ?!.,").lower()

        def is_simple_greeting(text):
            normalized = normalized_short_message(text)
            return (not normalized) or normalized in greeting_keywords

        # 0. Strict First-Time Greeting (Only appears once after login)
        # If the first message is a greeting or empty, greet; otherwise, proceed to answer the question.
        if is_first_message and is_simple_greeting(query):
            return f"Hello {faculty_name}!\nWhat would you like me to help you with today?"
        
        # 0.1 Diverse Greeting & Help Logic

        if normalized_short_message(query) in greeting_keywords and len(query.split()) < 3:
            greet = random.choice([
                f"How can I assist you today, {faculty_name}?",
                "Ready for your query. What are you looking for?"
            ])
            return f"Hello {faculty_name}! {greet}"
        
        if any(word in query for word in help_keywords):
            return self.kb.get_help_text(active_role)

        # Explicit confirmation is required before any chatbot workflow writes
        # an ERP notification or mentoring record.
        if query in {"confirm", "confirm action", "confirm send", "confirm send report"}:
            return self._handle_confirmed_action(
                faculty_id, active_role, conversation_state
            )
        if query in {"cancel", "cancel action", "cancel report"}:
            return self._cancel_pending_action(conversation_state)

        if any(phrase in query for phrase in [
            "daily briefing", "today's briefing", "todays briefing",
            "brief me", "what do i have today", "my day today",
        ]):
            return self._handle_daily_briefing(faculty_id, active_role)

        if any(phrase in query for phrase in [
            "pending work", "pending tasks", "what is pending",
            "what's pending", "whats pending", "incomplete marks",
            "pending attendance",
        ]):
            return self._handle_pending_work(faculty_id, active_role)

        _mentor_attention_terms = [
            "mentees need academic attention", "mentees need attention",
            "need academic attention", "mentees academic attention",
            "which mentees need", "show low-performing mentees",
            "low-performing mentees", "low performing mentees",
            "who needs academic attention", "which of my mentees",
            "mentees performing poorly", "identify students who need support",
        ]
        _low_perf_terms = [
            "low performer", "low-performing", "low performing",
            "weak student", "weak students", "students below",
        ]
        course_code = self._extract_course_code(raw_query)
        _mentor_attention_requested = any(
            phrase in query for phrase in _mentor_attention_terms
        )
        _mentor_attendance_requested = "mentee" in query and "attendance" in query
        _risk_with_course = (
            course_code
            and any(term in query for term in ["at risk", "at-risk"])
        )
        _has_low_perf = any(term in query for term in _low_perf_terms) or _risk_with_course
        _has_early_warning = any(phrase in query for phrase in [
            "early warning", "at risk", "at-risk", "risk students",
            "students needing attention", "students need attention",
            "low attendance or marks", "low attendance or low marks",
        ])

        analytics_role = active_role
        if _mentor_attention_requested or _mentor_attendance_requested or _has_low_perf or _has_early_warning:
            analytics_role, analytics_role_error = self._resolve_student_analytics_role(
                raw_query, active_role, all_roles=all_roles
            )
            if analytics_role_error:
                return analytics_role_error

        if (
            (_mentor_attention_requested or _mentor_attendance_requested or _has_low_perf)
            and self._is_mentor_role(analytics_role)
            and not course_code
        ):
            return self._handle_mentor_attention_students(
                faculty_id, analytics_role, raw_query
            )

        if _mentor_attention_requested and self._is_mentor_role(analytics_role):
            return self._handle_ca_low_performing(
                faculty_id, analytics_role, course_code=course_code
            )

        if _has_low_perf and self._is_ca_role(analytics_role):
            return self._handle_ca_low_performing(
                faculty_id, analytics_role, course_code=course_code
            )

        if _has_low_perf and self._is_mentor_role(analytics_role):
            return self._handle_ca_low_performing(
                faculty_id, analytics_role, course_code=course_code
            )

        if self._is_subject_risk_query(raw_query):
            return self._handle_subject_risk_students(
                faculty_id, active_role, raw_query
            )

        if _has_early_warning:
            return self._handle_early_warning(faculty_id, analytics_role)

        if any(phrase in query for phrase in [
            "create question", "generate question", "question paper",
            "question bank", "model answer", "create rubric",
            "generate rubric", "assessment assistant",
        ]):
            return self._handle_assessment_assistant(
                faculty_id, active_role, raw_query
            )

        if any(phrase in query for phrase in [
            "mentor follow-up", "mentor follow up", "mentoring follow-up",
            "mentoring follow up", "record follow-up", "record follow up",
            "schedule mentor meeting", "schedule mentoring meeting",
        ]):
            return self._handle_mentor_followup(
                faculty_id, active_role, raw_query, conversation_state
            )

        if any(phrase in query for phrase in [
            "draft report", "send report", "submit report", "report history",
        ]):
            return self._handle_report_workflow(
                faculty_id, active_role, raw_query, conversation_state
            )

        if any(phrase in query for phrase in ["my profile", "my faculty details", "my details"]):
            return self._handle_my_faculty_profile(faculty_id)

        if "timetable" in query or "time table" in query or "schedule today" in query:
            return self._handle_faculty_timetable(faculty_id, active_role)

        # Resolve student-list scope from the query before any high-precedence
        # role router runs. This is essential for faculty with multiple roles.
        student_list_role, student_list_error = self._resolve_student_list_role(
            raw_query, active_role, all_roles=all_roles
        )
        if student_list_error:
            return student_list_error
        if student_list_role:
            target_dept = self._extract_department(query)
            batch_match = re.search(r'\b(20\d{2})\b', query)
            target_batch = batch_match.group(1) if batch_match else None
            return self._handle_role_scoped_student_list(
                faculty_id,
                student_list_role,
                query,
                target_dept=target_dept,
                target_batch=target_batch,
            )

        # HOD is a department administrator. Route department searches and
        # analytics before any CA, mentor, or subject-teacher intent can run.
        if self._is_hod_role(active_role):
            hod_response = self._route_hod_department_query(
                faculty_id, raw_query
            )
            if hod_response is not None:
                return hod_response

        # 1. INTENT RECOGNITION
        # 1.0 Subject Handling Intent
        subject_phrases = [
            "which subject", "which subjects", "my subjects", "my courses",
            "department subjects", "department courses", "subjects in my department",
            "handled subject", "handled subjects", "teaching subject", "teaching subjects",
            "subject allocation", "subject allocations",
            "subject i handle", "subjects i handle", "subject i'm handling",
            "subjects i'm handling", "subject i am handling", "subjects i am handling",
            "handling subject", "handling subjects", "subject handling", "subjects handling",
            "assigned subject", "assigned subjects", "subjects assigned",
            "what do i teach", "what am i teaching", "courses i teach", "course i teach"
        ]
        subject_terms = ["subject", "subjects", "course", "courses"]
        subject_intent = any(p in query for p in subject_phrases) or (
            any(k in query for k in ["handle", "handling", "assigned", "teach", "teaching"])
            and any(t in query for t in subject_terms)
        )
        if subject_intent:
            return self._handle_subjects_handled(
                faculty_id, active_role, query=raw_query
            )

        if any(phrase in query for phrase in ["department faculty", "list faculty", "show faculty"]):
            return self._handle_faculty_directory(faculty_id, active_role)

        if any(phrase in query for phrase in ["department classes", "list classes", "show classes"]):
            return self._handle_class_directory(faculty_id, active_role)

        # 1.06 Class report for a handled subject
        if self._is_class_report_query(raw_query):
            report_role = self._resolve_class_report_role(
                active_role, all_roles=all_roles
            )
            return self._handle_class_report_query(
                faculty_id,
                report_role,
                raw_query,
                all_roles=all_roles,
            )

        # 1.065 Published end-semester results for a specific student. This
        # must run before the generic student-subject marks intent, which may
        # otherwise require a course code.
        if self._is_student_end_semester_query(raw_query):
            return self._handle_student_end_semester_results(
                faculty_id,
                active_role,
                raw_query,
                all_roles=all_roles,
            )

        # 1.07 Subject-wise marks intent
        if self._is_subject_marks_query(raw_query):
            return self._handle_subject_marks_query(faculty_id, active_role, raw_query)

        # 1.1 List Students Intent
        list_keywords = [
            "list", "show students", "get students", "who are the students",
            "students for", "student list", "display students", "show me students",
            "fetch students", "list students"
        ]
        if "list" in query or "students" in query:
            if any(k in query for k in ["list", "show", "get", "who are"]):
                target_dept = self._extract_department(query)
                batch_match = re.search(r'\b(20\d{2})\b', query)
                target_batch = batch_match.group(1) if batch_match else None
                return self._handle_list_students(faculty_id, active_role, target_dept=target_dept, target_batch=target_batch)

        # 1.3 View Subject-Specific Reports (For Advisors)
        if any(k in query for k in ["view report", "show report", "subject report", "class report", "report history"]):
             # If "send" not in query and "submit" not in query, it's viewing
             if "send" not in query and "submit" not in query:
                return self._handle_view_subject_reports(faculty_id, query, active_role=active_role)

        # 1.35 Student-specific subject marks intent
        if self._is_student_subject_marks_query(raw_query):
            return self._handle_student_subject_marks_query(faculty_id, active_role, raw_query)

        # 1.4 Student Marks Chart Intent
        if any(k in query for k in ["chart", "graph", "plot", "visualize", "compare", "marks of"]):
            student_regs = re.findall(r'\b\d{12}\b', query)
            if student_regs:
                return self._handle_marks_chart(faculty_id, student_regs, query, active_role)

        # 2. DEFAULT FALLBACK: Student Search or Academic Query
        # Check for 12-digit reg no in the query
        reg_match = re.search(r'\b\d{12}\b', query)
        if reg_match:
            student_reg_no = reg_match.group(0)
            if "attendance" in query or "present" in query or "absent" in query:
                return self._handle_student_attendance_query(
                    faculty_id, student_reg_no, active_role, raw_query
                )
            if any(token in query for token in ["semester result", "semester results", "gpa", "cgpa", "grade"]):
                return self._handle_student_semester_results(
                    faculty_id, student_reg_no, active_role
                )
            return self._handle_student_query(faculty_id, student_reg_no, query, active_role)

        # Final Fallback to Knowledge Base
        kb_response = self.kb.search_help(query)
        if kb_response:
            return kb_response

        return "I'm not sure how to help with that. Could you please specify a student registration number, or a task like 'list students' or 'analyze performance'?"

    def _process_student_query(self, user_query, reg_no, is_first_message=False):
        """Answer only from the authenticated student's own ERP records."""
        student = self._student_queryset().filter(
            reg_no=reg_no,
            is_active=True,
            is_discontinued=False,
        ).first()
        if not student:
            return "Authentication Error: Your student profile is not mapped to this login. Please contact the ERP administrator."

        query = self._normalize_role_name(user_query)
        mentioned_regs = set(re.findall(r"\b\d{10,15}\b", user_query))
        if any(value != str(student.reg_no) for value in mentioned_regs):
            return "Student accounts can access only their own academic information."

        greeting_terms = {
            "hi", "hello", "hey", "start", "good morning",
            "good afternoon", "good evening",
        }
        if (is_first_message and (not query or query in greeting_terms)) or query in greeting_terms:
            return f"Hello {student.name or 'Student'}! How can I help with your academic information today?"

        if any(term in query for term in ["help", "what can you do", "options", "commands"]):
            return (
                "I can securely show your own ERP information:\n"
                "- My profile, Class Advisor, and mentor\n"
                "- My current or historical semester subjects\n"
                "- Today's or weekly timetable\n"
                "- My attendance and attendance insights\n"
                "- My internal marks, academic overview, and performance insights\n"
                "- My semester results or CGPA\n\n"
                "Your login cannot access another student's records."
            )

        if any(term in query for term in [
            "timetable", "time table", "next class", "today's classes",
            "classes today", "weekly schedule", "class schedule",
            "tomorrow", "yesterday",
        ]):
            return self._handle_student_timetable(student, query)

        if any(term in query for term in [
            "register number", "register no", "reg no", "reg number",
            "roll number", "roll no",
        ]):
            return (
                f"Your register number is {student.reg_no or 'N/A'}."
            )

        if any(term in query for term in [
            "academic year", "my batch", "batch", "year of admission",
            "my year", "which year", "current year",
        ]):
            return (
                f"Academic Year: {student.year or 'N/A'}\n"
                f"Batch: {student.batch or 'N/A'}"
            )

        if any(term in query for term in [
            "my profile", "my details", "student profile", "about me",
            "my information", "my department", "my batch", "my section",
            "my semester", "which semester", "what semester",
            "class advisor", "class adviser", "my advisor", "my adviser",
            "my mentor", "mentor details", "advisor details",
        ]):
            if any(term in query for term in [
                "attendance", "present", "absent", "classes can i miss",
                "classes should i attend", "classes required", "reach 75",
            ]):
                return self._handle_student_attendance(student, query)
            if "mark" in query or "iat" in query or "model exam" in query or "internal" in query:
                return self._handle_student_internal_marks(student, query)
            if any(term in query for term in ["result", "grade", "gpa", "cgpa"]):
                return self._handle_student_results(student, query)
            department = getattr(getattr(student, "department", None), "Department", None) or "N/A"
            advisor = getattr(student, "ca", None)
            mentor = getattr(student, "mentor", None)
            return "\n".join([
                "Student Profile",
                f"Name: {student.name or 'N/A'}",
                f"Register Number: {student.reg_no or 'N/A'}",
                f"Department: {department}",
                f"Batch: {student.batch or 'N/A'}",
                f"Year: {student.year or 'N/A'}",
                f"Semester: {student.semester or 'N/A'}",
                f"Section: {student.section or 'N/A'}",
                f"Email: {getattr(student, 'email', None) or 'N/A'}",
                f"Mobile Number: {getattr(student, 'mobile_no', None) or 'N/A'}",
                f"Class Advisor: {getattr(advisor, 'name', None) or 'Not assigned'}",
                f"Class Advisor Email: {getattr(advisor, 'college_email', None) or 'N/A'}",
                f"Mentor: {getattr(mentor, 'name', None) or 'Not assigned'}",
                f"Mentor Email: {getattr(mentor, 'college_email', None) or 'N/A'}",
            ])

        if any(term in query for term in [
            "academic overview", "academic summary", "academic dashboard",
            "my academic status", "overall academic", "semester summary",
            "academic analytics", "academic analysis",
        ]):
            return self._handle_student_academic_overview(student, query)

        if any(term in query for term in [
            "performance insight", "performance analysis", "analyze my performance",
            "analyse my performance", "strongest subject", "weakest subject",
            "subjects need attention", "subject needs attention", "study recommendation",
            "study recommendations", "how can i improve", "my performance",
            "which subject should i focus", "where should i improve",
            "how did i perform", "how am i performing", "evaluate my",
        ]) or "performance" in query or "performing" in query:
            return self._handle_student_performance_insights(student, query)

        if any(term in query for term in [
            "attendance", "present", "absent", "classes can i miss",
            "classes should i attend", "classes required", "reach 75",
        ]):
            return self._handle_student_attendance(student, query)

        if self._is_student_subject_list_query(query):
            target_semester, is_historical_request = self._resolve_student_semester(
                student,
                query,
            )
            if target_semester is None:
                return (
                    "Your current semester is not assigned in the ERP student profile. "
                    "Please contact the department office to verify it."
                )

            enrollments, academic_year = self._get_student_subject_enrollments(
                student,
                target_semester,
            )
            if not enrollments:
                if is_historical_request:
                    return f"No enrolled subjects were found for you in Semester {target_semester}."
                return (
                    f"No active subject enrollments were found for your current semester "
                    f"(Semester {target_semester}). Please contact the department office."
                )
            heading = (
                f"My Semester {target_semester} Subjects"
                if is_historical_request
                else f"My Current Semester Subjects (Semester {target_semester})"
            )
            lines = [heading]
            if academic_year:
                lines.append(f"Academic Year: {academic_year}")
            for item in enrollments:
                code = item["course__course_code"] or "N/A"
                title = item["course__title"] or "Untitled Subject"
                lines.append(f"- {title} ({code})")
            return "\n".join(lines)

        if "mark" in query or "iat" in query or "model exam" in query or "internal" in query:
            return self._handle_student_internal_marks(student, query)

        if any(term in query for term in ["result", "grade", "gpa", "cgpa", "semester performance"]):
            return self._handle_student_results(student, query)

        return (
            "I can help with your own profile, subjects, attendance, internal marks, and semester results. "
            "Try asking: 'Show my attendance' or 'Show my internal marks'."
        )

    def _is_student_subject_list_query(self, query):
        """Recognize current or explicitly requested semester subject lists."""
        text = self._normalize_role_name(query)
        if not any(term in text for term in ["subject", "subjects", "course", "courses"]):
            return False
        if any(term in text for term in ["mark", "grade", "result", "attendance", "report"]):
            return False
        return any(term in text for term in [
            "my subject", "my course", "enrolled subject", "enrolled course",
            "semester", "this semester", "current subject", "current course",
            "list subject", "list course", "show subject", "show course",
            "display subject", "display course", "what subject", "what course",
            "study", "studied",
        ])

    def _extract_student_subject_semester(self, query):
        """Return an explicitly requested semester number, otherwise None."""
        text = self._normalize_role_name(query)
        match = re.search(r"\b(?:semester|sem)\s*[-:]?\s*(\d{1,2})\b", text)
        if not match:
            match = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)\s+(?:semester|sem)\b", text)
        return int(match.group(1)) if match else None

    def _resolve_student_semester(self, student, query):
        """Resolve explicit semester first; otherwise use the ERP current semester."""
        requested = self._extract_student_subject_semester(query)
        if requested is not None:
            return requested, True
        return self._semester_number(getattr(student, "semester", None)), False

    def _extract_student_assessments(self, query):
        """Return every explicitly named assessment in a student marks query."""
        text = self._normalize_role_name(query)
        assessments = {
            self._normalize_exam_name(f"IAT{number}")
            for number in re.findall(r"\b(?:iat|internal)\s*[-:]?\s*(\d+)\b", text)
        }
        roman_map = {"i": "1", "ii": "2", "iii": "3"}
        for roman in re.findall(r"\b(?:iat|internal)\s*[-:]?\s*(i{1,3})\b", text):
            if roman in roman_map:
                assessments.add(self._normalize_exam_name(f"IAT{roman_map[roman]}"))
        if "model exam" in text or "model examination" in text:
            assessments.add(self._normalize_exam_name("Model Exam"))
        return assessments

    def _semester_number(self, value):
        """Normalize the ERP semester value without supplying a default."""
        match = re.search(r"\d{1,2}", str(value or ""))
        return int(match.group(0)) if match else None

    def _academic_year_sort_key(self, value):
        years = [int(year) for year in re.findall(r"\d{4}", str(value or ""))]
        if not years:
            return (0, 0, str(value or ""))
        return (years[0], years[-1], str(value or ""))

    def _get_student_subject_enrollments(self, student, semester):
        """Fetch one semester and its latest ERP academic-year allocation."""
        semester_text = str(semester)
        enrollments = CourseEnrollment.objects.filter(
            student=student,
            enroll=True,
            semester__iexact=semester_text,
        )

        academic_years = list(
            enrollments.exclude(academic_year__isnull=True)
            .exclude(academic_year__exact="")
            .values_list("academic_year", flat=True)
            .distinct()
        )
        academic_year = (
            max(academic_years, key=self._academic_year_sort_key)
            if academic_years
            else None
        )
        if academic_year:
            enrollments = enrollments.filter(academic_year=academic_year)

        rows = list(
            enrollments.values(
                "course__course_code",
                "course__title",
                "semester",
                "academic_year",
            )
            .distinct()
            .order_by("course__course_code")
        )
        return rows, academic_year

    def _get_student_internal_mark_rows(
        self,
        student,
        semester,
        academic_year=None,
        course_code=None,
    ):
        base_marks = StudentInternalMark.objects.filter(
            student=student,
            semester__iexact=str(semester),
        )
        if course_code:
            base_marks = base_marks.filter(course_code__iexact=course_code)

        def aggregate(queryset):
            details = list(
                queryset.values(
                    "id",
                    "course_code",
                    "course__title",
                    "exam_name",
                    "part_name",
                    "question_number",
                    "sub_question",
                    "option_letter",
                    "max_marks",
                    "marks_obtained",
                ).order_by(
                    "course_code",
                    "exam_name",
                    "part_name",
                    "question_number",
                    "option_letter",
                    "sub_question",
                )
            )
            return self._aggregate_student_mark_details(details)

        marks = aggregate(
            base_marks.filter(academic_year=academic_year)
            if academic_year
            else base_marks
        )
        if academic_year and not marks:
            marks = aggregate(base_marks)
        return marks

    def _aggregate_student_mark_details(self, details):
        """Aggregate question rows while counting only one side of OR choices."""
        assessments = {}
        for row in details:
            assessment_key = (
                row.get("course_code"),
                row.get("course__title"),
                row.get("exam_name"),
            )
            assessment = assessments.setdefault(
                assessment_key,
                {"questions": {}},
            )
            question_number = str(row.get("question_number") or "").strip()
            question_key = (
                str(row.get("part_name") or "").strip(),
                question_number or f"row-{row.get('id')}",
            )
            question = assessment["questions"].setdefault(
                question_key,
                {
                    "mandatory_max": 0,
                    "mandatory_obtained": 0,
                    "option_max": {},
                    "option_obtained": {},
                },
            )
            max_marks = row.get("max_marks") or 0
            marks_obtained = row.get("marks_obtained") or 0
            option = str(row.get("option_letter") or "").strip().lower()
            if option:
                question["option_max"][option] = (
                    question["option_max"].get(option, 0) + max_marks
                )
                question["option_obtained"][option] = (
                    question["option_obtained"].get(option, 0) + marks_obtained
                )
            else:
                question["mandatory_max"] += max_marks
                question["mandatory_obtained"] += marks_obtained

        results = []
        for (course_code, title, exam_name), assessment in assessments.items():
            maximum = 0
            obtained = 0
            for question in assessment["questions"].values():
                maximum += question["mandatory_max"]
                obtained += question["mandatory_obtained"]
                if question["option_max"]:
                    maximum += max(question["option_max"].values())
                    obtained += max(question["option_obtained"].values(), default=0)
            results.append({
                "course_code": course_code,
                "course__title": title,
                "exam_name": exam_name,
                "obtained": obtained,
                "maximum": maximum,
            })
        return sorted(
            results,
            key=lambda item: (
                str(item["course_code"] or ""),
                str(item["exam_name"] or ""),
            ),
        )

    def _handle_student_internal_marks(self, student, query):
        semester, is_historical_request = self._resolve_student_semester(
            student,
            query,
        )
        if semester is None:
            return (
                "Your current semester is not assigned in the ERP profile. "
                "Please contact the department office before requesting marks."
            )

        _subjects, academic_year = self._get_student_subject_enrollments(
            student,
            semester,
        )
        course_code = self._extract_course_code(query)
        marks = self._get_student_internal_mark_rows(
            student,
            semester,
            academic_year=academic_year,
            course_code=course_code,
        )

        requested_assessments = self._extract_student_assessments(query)
        query_requests_all_iats = "iat" in query and not requested_assessments
        if requested_assessments:
            marks = [
                item for item in marks
                if self._normalize_exam_name(item["exam_name"]) in requested_assessments
            ]
        elif query_requests_all_iats:
            marks = [
                item for item in marks
                if self._normalize_exam_name(item["exam_name"]).startswith("iat")
            ]

        if not marks:
            assessment_label = (
                " and ".join(sorted(requested_assessments)).upper()
                if requested_assessments
                else "IAT" if query_requests_all_iats else "internal"
            )
            subject_label = f" for {course_code}" if course_code else ""
            return (
                f"No {assessment_label} marks were found{subject_label} in Semester {semester} "
                "for your account."
            )

        heading_scope = (
            f"Semester {semester}"
            if is_historical_request
            else f"Current Semester {semester}"
        )

        exam_order = {"iat1": 1, "iat2": 2, "iat3": 3}
        by_course = {}
        all_exams = set()
        for item in marks:
            code = item["course_code"] or "N/A"
            title = item["course__title"] or "Subject"
            exam = item["exam_name"] or "Assessment"
            normalized = self._normalize_exam_name(exam)
            key = (code, title)
            by_course.setdefault(key, {})[normalized] = item
            all_exams.add(normalized)

        sorted_exams = sorted(all_exams, key=lambda e: exam_order.get(e, 99))
        exam_labels = {
            "iat1": "IAT 1",
            "iat2": "IAT 2",
            "iat3": "IAT 3",
        }

        lines = [f"My Internal Marks | {heading_scope}"]
        if academic_year:
            lines.append(f"Academic Year: {academic_year}")
        lines.append("")

        if len(sorted_exams) >= 2:
            header_cols = ["Subject"] + [exam_labels.get(e, e.upper()) for e in sorted_exams]
            all_rows = []
            for (code, title), exam_map in by_course.items():
                row = [f"{title} ({code})"]
                for exam in sorted_exams:
                    item = exam_map.get(exam)
                    if item and item.get("obtained") is not None and item.get("maximum") is not None:
                        row.append(f"{item['obtained']}/{item['maximum']}")
                    else:
                        row.append("N/A")
                all_rows.append(row)
            lines.append(" | ".join(header_cols))
            lines.append(" | ".join(["---"] * len(header_cols)))
            for row in all_rows:
                lines.append(" | ".join(row))
        else:
            for (code, title), exam_map in by_course.items():
                for exam in sorted_exams:
                    item = exam_map.get(exam)
                    exam_label = exam_labels.get(exam, exam.upper())
                    if item and item.get("obtained") is not None and item.get("maximum") is not None:
                        lines.append(f"- {title} ({code}) | {exam_label}: {item['obtained']}/{item['maximum']}")
                    else:
                        lines.append(f"- {title} ({code}) | {exam_label}: N/A")

        return "\n".join(lines)

    def _handle_student_results(self, student, query):
        semester, is_historical_request = self._resolve_student_semester(
            student,
            query,
        )
        if semester is None:
            return (
                "Your current semester is not assigned in the ERP profile. "
                "Please contact the department office before requesting results."
            )
        results = list(
            Result.objects.filter(
                student=student,
                semester__iexact=str(semester),
            )
            .values(
                "course__course_code",
                "course__title",
                "grade",
                "semester",
                "academic_year",
            )
            .order_by("academic_year", "course__course_code")
        )
        gpa_rows = list(
            GPA.objects.filter(
                student=student,
                semester__iexact=str(semester),
            )
            .values("semester", "gpa", "cgpa", "academic_year")
            .order_by("academic_year")
        )
        if not results and not gpa_rows:
            scope = "requested" if is_historical_request else "current"
            return f"No published {scope}-semester results were found for Semester {semester}."
        heading = (
            f"My Semester {semester} Results"
            if is_historical_request
            else f"My Current Semester Results (Semester {semester})"
        )
        lines = [heading]
        for item in gpa_rows:
            gpa = item["gpa"] if item["gpa"] is not None else "N/A"
            cgpa = item["cgpa"] if item["cgpa"] is not None else "N/A"
            lines.append(
                f"- GPA: {gpa} | CGPA: {cgpa} | AY: {item['academic_year'] or 'N/A'}"
            )
        for item in results:
            code = item["course__course_code"] or "N/A"
            title = item["course__title"] or "Subject"
            lines.append(
                f"- {title} ({code}) | Grade: {item['grade'] or 'N/A'} | "
                f"AY: {item['academic_year'] or 'N/A'}"
            )
        return "\n".join(lines)

    def _handle_student_timetable(self, student, query):
        semester, _is_historical_request = self._resolve_student_semester(
            student,
            query,
        )
        department = getattr(student, "department", None)
        section = str(getattr(student, "section", "") or "").strip()
        if not department or semester is None or not section:
            return (
                "Your department, current semester, or section is missing from the ERP profile. "
                "Please contact the department office to verify your timetable mapping."
            )

        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        requested_day = next(
            (day for day in weekdays if re.search(rf"\b{day.lower()}\b", query)),
            None,
        )
        weekly = any(term in query for term in ["weekly", "whole week", "full timetable", "week timetable"])

        if not requested_day and not weekly:
            if "tomorrow" in query:
                tomorrow = datetime.now() + timedelta(days=1)
                requested_day = tomorrow.strftime("%A")
            elif "yesterday" in query:
                yesterday = datetime.now() - timedelta(days=1)
                requested_day = yesterday.strftime("%A")

        target_day = requested_day or (None if weekly else datetime.now().strftime("%A"))

        allocations = PeriodAllocation.objects.filter(
            department=department,
            semester__iexact=str(semester),
            section__iexact=section,
        )
        if target_day:
            allocations = allocations.filter(day__iexact=target_day)
        allocation_rows = list(allocations)
        if not allocation_rows:
            scope = target_day or "the current week"
            return f"No timetable allocation was found for {scope}, Semester {semester}, Section {section}."

        day_order = {day.lower(): index for index, day in enumerate(weekdays)}
        allocation_rows.sort(key=lambda row: day_order.get(str(row.day or "").lower(), 99))
        period_fields = [
            "first_period", "second_period", "third_period", "fourth_period",
            "fifth_period", "sixth_period", "seventh_period", "eighth_period",
            "nineth_period", "tenth_period",
        ]
        used_codes = {
            str(getattr(row, field, "") or "").strip()
            for row in allocation_rows
            for field in period_fields
            if str(getattr(row, field, "") or "").strip()
        }
        course_titles = {
            str(code).strip().upper(): title
            for code, title in Course.objects.filter(course_code__in=used_codes)
            .values_list("course_code", "title")
            if code
        }

        heading = (
            f"**My Weekly Timetable | Semester {semester} | Section {section}**"
            if not target_day
            else f"**My Timetable for {target_day} | Semester {semester} | Section {section}**"
        )
        lines = [heading, ""]
        if "next class" in query:
            lines.append(
                "Note: ERP stores period order but no bell-time mapping, so the exact next period cannot be calculated."
            )
        for allocation in allocation_rows:
            if not target_day:
                lines.append(f"**{allocation.day}**")
            for number, field in enumerate(period_fields, start=1):
                code = str(getattr(allocation, field, "") or "").strip()
                if not code:
                    continue
                title = course_titles.get(code.upper())
                label = f"{title}" if title else ""
                lines.append(f"{number}. **P{number}** — {code}{': ' + label if label else ''}")
            lines.append("")
        return "\n".join(lines).rstrip()

    def _student_hour_attendance_rows(self, student, semester, academic_year=None):
        base_attendance = HourAttendance.objects.filter(
            student=student,
            semester__iexact=str(semester),
        )
        attendance = (
            base_attendance.filter(academic_year=academic_year)
            if academic_year
            else base_attendance
        )
        rows = list(
            attendance.values(
                "course_id", "course__course_code", "course__title"
            )
            .annotate(
                total=Count("id"),
                attended=Count("id", filter=Q(status__in=["Present", "On Duty"])),
                absent=Count("id", filter=Q(status="Absent")),
            )
            .order_by("course__course_code")
        )
        if academic_year and not rows:
            rows = list(
                base_attendance.values(
                    "course_id", "course__course_code", "course__title"
                )
                .annotate(
                    total=Count("id"),
                    attended=Count("id", filter=Q(status__in=["Present", "On Duty"])),
                    absent=Count("id", filter=Q(status="Absent")),
                )
                .order_by("course__course_code")
            )
        return rows

    def _student_daily_attendance_summary(self, student, semester, academic_year=None):
        """Fallback: query Daily_Attendance when HourAttendance has no records."""
        base = Daily_Attendance.objects.filter(student=student, semester__iexact=str(semester))
        if academic_year:
            base = base.filter(academic_year=academic_year)
        records = list(base.values_list("morning_status", "afternoon_status"))
        if academic_year and not records:
            records = list(
                Daily_Attendance.objects.filter(
                    student=student, semester__iexact=str(semester),
                ).values_list("morning_status", "afternoon_status")
            )
        return records

    def _attendance_projection(self, attended, total, threshold=75):
        if total <= 0:
            return 0, 0
        ratio = threshold / 100
        percentage = (attended / total) * 100
        if percentage < threshold:
            required = math.ceil(max(0, (ratio * total - attended) / (1 - ratio)))
            return required, 0
        safe_absences = math.floor(max(0, attended / ratio - total))
        return 0, safe_absences

    def _handle_student_attendance(self, student, query):
        semester, is_historical_request = self._resolve_student_semester(
            student,
            query,
        )
        if semester is None:
            return "Your current semester is not assigned in the ERP profile. Please contact the department office."
        _subjects, academic_year = self._get_student_subject_enrollments(student, semester)
        rows = self._student_hour_attendance_rows(student, semester, academic_year)
        if not rows:
            daily_records = self._student_daily_attendance_summary(student, semester, academic_year)
            if daily_records:
                statuses = [s for pair in daily_records for s in pair if s]
                present = sum(s in {"Present", "On Duty"} for s in statuses)
                absent = sum(s == "Absent" for s in statuses)
                percentage = round((present / len(statuses)) * 100, 2) if statuses else 0
                required, safe_absences = self._attendance_projection(present, len(statuses))
                guidance = (
                    f"Attend the next **{required}** session(s) to reach **75%**."
                    if required
                    else f"Up to **{safe_absences}** additional absence(s) before dropping below **75%**."
                )
                lines = [
                    f"**My Attendance | Semester {semester}**",
                    "",
                    "**Daily Attendance Summary**",
                    f"- **Percentage:** **{percentage}%**",
                    f"- **Sessions Attended:** **{present}/{len(statuses)}**",
                    f"- **Absent:** **{absent}**",
                    f"- **Guidance:** {guidance}",
                ]
                if academic_year:
                    lines.append(f"- **Academic Year:** **{academic_year}**")
                lines.append("")
                lines.append("_Showing daily (morning + afternoon) attendance. Period-wise subject attendance will appear once faculty mark it._")
                return "\n".join(lines)
            scope = "requested" if is_historical_request else "current"
            return f"No attendance records were found for your {scope} semester (Semester {semester}). Attendance may not have been marked yet."

        requested_code = self._extract_course_code(query)
        if requested_code:
            rows = [
                row for row in rows
                if str(row["course__course_code"] or "").upper() == requested_code.upper()
            ]
            if not rows:
                return f"No Semester {semester} attendance was found for subject code {requested_code}."

        below_only = "below 75" in query or "shortage" in query
        calculated = []
        for row in rows:
            total = row["total"] or 0
            attended = row["attended"] or 0
            percentage = round((attended / total) * 100, 2) if total else 0
            required, safe_absences = self._attendance_projection(attended, total)
            calculated.append((row, percentage, required, safe_absences))

        overall_attended = sum((item[0]["attended"] or 0) for item in calculated)
        overall_total = sum((item[0]["total"] or 0) for item in calculated)
        overall_percentage = (
            round((overall_attended / overall_total) * 100, 2)
            if overall_total
            else 0
        )
        if below_only:
            calculated = [item for item in calculated if item[1] < 75]
            if not calculated:
                return f"None of your Semester {semester} subjects are below 75% attendance."

        lines = [
            f"**My Subject-wise Attendance | Semester {semester}**",
            "",
            "**Overall Attendance**",
            f"- **Percentage:** **{overall_percentage}%**",
            f"- **Classes Attended:** **{overall_attended}/{overall_total}**",
        ]
        if academic_year:
            lines.append(f"- **Academic Year:** **{academic_year}**")
        lines.extend(["", "**Subject-wise Details**"])
        for index, (row, percentage, required, safe_absences) in enumerate(calculated, start=1):
            code = row["course__course_code"] or "N/A"
            title = row["course__title"] or "Subject"
            status = (
                f"Attend the next **{required}** class(es) to reach **75%**."
                if required
                else f"Up to **{safe_absences}** additional absence(s) before dropping below **75%**."
            )
            lines.extend([
                f"{index}. **{title} ({code})**",
                f"   - Attendance: **{row['attended']}/{row['total']}**",
                f"   - Percentage: **{percentage}%**",
                f"   - Guidance: {status}",
            ])
        return "\n".join(lines)

    def _student_mark_performance_rows(self, student, semester, academic_year=None):
        assessment_rows = self._get_student_internal_mark_rows(
            student,
            semester,
            academic_year=academic_year,
        )
        courses = {}
        for assessment in assessment_rows:
            key = (assessment["course_code"], assessment["course__title"])
            course = courses.setdefault(
                key,
                {
                    "course_code": assessment["course_code"],
                    "course__title": assessment["course__title"],
                    "obtained": 0,
                    "maximum": 0,
                },
            )
            course["obtained"] += assessment["obtained"] or 0
            course["maximum"] += assessment["maximum"] or 0
        results = []
        for row in courses.values():
            maximum = row["maximum"] or 0
            if maximum <= 0:
                continue
            row["percentage"] = round(((row["obtained"] or 0) / maximum) * 100, 2)
            results.append(row)
        return sorted(results, key=lambda row: str(row["course_code"] or ""))

    def _handle_student_academic_overview(self, student, query=""):
        semester, is_historical_request = self._resolve_student_semester(
            student,
            query,
        )
        if semester is None:
            return "Your current semester is not assigned in the ERP profile. Please contact the department office."
        subjects, academic_year = self._get_student_subject_enrollments(student, semester)
        attendance = self._student_hour_attendance_rows(student, semester, academic_year)
        marks = self._student_mark_performance_rows(student, semester, academic_year)
        total_hours = sum(row["total"] or 0 for row in attendance)
        attended_hours = sum(row["attended"] or 0 for row in attendance)
        attendance_percentage = round((attended_hours / total_hours) * 100, 2) if total_hours else None
        total_maximum = sum(row["maximum"] or 0 for row in marks)
        total_obtained = sum(row["obtained"] or 0 for row in marks)
        mark_percentage = round((total_obtained / total_maximum) * 100, 2) if total_maximum else None
        latest_gpa = (
            GPA.objects.filter(student=student, semester__iexact=str(semester))
            .order_by("-academic_year", "-id")
            .values("gpa", "cgpa", "semester", "academic_year")
            .first()
        )
        scope = f"Semester {semester}" if is_historical_request else f"Current Semester {semester}"
        lines = [f"My Academic Overview | {scope}"]
        if academic_year:
            lines.append(f"Academic Year: {academic_year}")
        lines.extend([
            f"Current subjects: {len(subjects)}",
            f"Overall subject attendance: {attendance_percentage if attendance_percentage is not None else 'N/A'}%" if attendance_percentage is not None else "Overall subject attendance: N/A",
            f"Recorded internal-mark average: {mark_percentage if mark_percentage is not None else 'N/A'}%" if mark_percentage is not None else "Recorded internal-mark average: N/A",
        ])
        if latest_gpa:
            lines.append(
                f"Latest published GPA/CGPA: {latest_gpa['gpa'] if latest_gpa['gpa'] is not None else 'N/A'} / "
                f"{latest_gpa['cgpa'] if latest_gpa['cgpa'] is not None else 'N/A'} "
                f"(Semester {latest_gpa['semester'] or 'N/A'})"
            )
        else:
            lines.append("Latest published GPA/CGPA: N/A")
        return "\n".join(lines)

    _CUMULATIVE_KEYWORDS = (
        "overall", "cumulative", "all semester", "every semester",
        "complete academic", "across all", "entire academic",
    )

    def _is_cumulative_request(self, query):
        """Return True when the student explicitly asks for multi-semester analysis."""
        text = self._normalize_role_name(query)
        return any(term in text for term in self._CUMULATIVE_KEYWORDS)

    def _handle_student_performance_insights(self, student, query=""):
        requested_semester = self._extract_student_subject_semester(query)
        if requested_semester is not None:
            return self._handle_student_semester_performance_insights(
                student, query, requested_semester,
            )
        if self._is_cumulative_request(query):
            return self._handle_student_overall_performance_insights(student)
        return self._handle_student_current_semester_performance(student)

    @staticmethod
    def _build_student_context_block(student, semester, academic_year):
        """Return the common student-details block reused by both semester and cumulative prompts."""
        department_name = (
            getattr(getattr(student, "department", None), "Department", None)
            or "N/A"
        )
        return {
            "student": student,
            "department_name": department_name,
            "semester": semester,
            "academic_year": academic_year,
            "student_block": (
                f"Student Name: {getattr(student, 'name', None) or 'N/A'}\n"
                f"Register Number: {getattr(student, 'reg_no', None) or 'N/A'}\n"
                f"Department: {department_name}\n"
                f"Batch: {getattr(student, 'batch', None) or 'N/A'}\n"
                f"Year: {getattr(student, 'year', None) or 'N/A'}\n"
                f"Semester: {semester}\n"
                f"Section: {getattr(student, 'section', None) or 'N/A'}"
            ),
        }

    def _build_semester_user_message(self, ctx, ranked, attendance_rows, average, latest_gpa):
        """Build the deterministic user message sent to the LLM for a single semester."""
        mark_context = "\n".join(
            f"- {row['course__title'] or 'Subject'} ({row['course_code'] or 'N/A'}): "
            f"Obtained {row.get('obtained') or 0}/{row.get('maximum') or 0} ({row['percentage']}%)"
            for row in ranked
        ) or "No recorded marks."
        attendance_context = "\n".join(
            f"- {row['course__title'] or 'Subject'} ({row['course__course_code'] or 'N/A'}): "
            f"{round(((row['attended'] or 0) / row['total']) * 100, 2) if row['total'] else 0}%"
            for row in attendance_rows
        ) or "N/A"
        gpa_context = "N/A"
        if latest_gpa:
            gpa_context = (
                f"GPA {latest_gpa['gpa'] if latest_gpa['gpa'] is not None else 'N/A'}, "
                f"CGPA {latest_gpa['cgpa'] if latest_gpa['cgpa'] is not None else 'N/A'}, "
                f"Semester {latest_gpa['semester'] or 'N/A'}"
            )
        fallback_used = ctx.get("fallback_used", False)
        current_semester = ctx.get("current_semester")
        fallback_reason = ctx.get("fallback_reason")
        if fallback_used and current_semester:
            fallback_header = (
                f"FALLBACK NOTICE: The student's current semester is Semester {current_semester}, "
                f"but published academic results are not yet available for that semester. "
                f"This analysis uses the latest available academic results from Semester {ctx['semester']}. "
                f"Reason: {fallback_reason}. "
                f"You MUST include a clear fallback transparency statement at the top of your response, "
                f"explaining that Semester {current_semester} results are not published and Semester {ctx['semester']} is used instead.\n\n"
            )
            analysis_mode = (
                f"Analysis mode: Latest available semester performance (Semester {ctx['semester']}) "
                f"[Fallback from Semester {current_semester}]\n"
            )
        else:
            fallback_header = ""
            analysis_mode = f"Analysis mode: Current semester performance (Semester {ctx['semester']})\n"
        return (
            f"{fallback_header}"
            f"{ctx['student_block']}\n\n"
            f"{analysis_mode}"
            f"Academic year: {ctx['academic_year'] or 'N/A'}\n"
            f"Recorded subject average: {average}%\n"
            f"Latest GPA/CGPA: {gpa_context}\n\n"
            f"Subject performance (internal marks):\n{mark_context}\n\n"
            f"Subject attendance:\n{attendance_context}\n\n"
            f"INSTRUCTIONS: Analyze ONLY Semester {ctx['semester']} data shown above. "
            f"Do NOT reference any other semester. Do NOT calculate values yourself; use the numbers provided. "
            f"Do NOT claim knowledge, intelligence, personality, motivation, career interest, or any personal attribute. "
            f"Only state what the marks, attendance, and GPA data directly support."
        )

    def _build_semester_fallback(self, ctx, ranked, attendance_rows, average, latest_gpa):
        """Deterministic fallback when the LLM call fails or returns invalid output."""
        semester = ctx["semester"]
        department_name = ctx["department_name"]
        student = ctx["student"]
        fallback_used = ctx.get("fallback_used", False)
        current_semester = ctx.get("current_semester")
        strongest = ranked[0] if ranked else None
        weakest = ranked[-1] if ranked else None

        attended_hours = sum(row.get("attended") or 0 for row in attendance_rows)
        total_hours = sum(row.get("total") or 0 for row in attendance_rows)
        attendance_pct = (
            round((attended_hours / total_hours) * 100, 2) if total_hours else None
        )

        strengths = []
        if strongest:
            strengths.append(
                f"Highest recorded internal score: {strongest['course__title'] or 'Subject'} "
                f"({strongest['course_code'] or 'N/A'}) at {strongest['percentage']}% "
                f"({strongest.get('obtained') or 0}/{strongest.get('maximum') or 0})."
            )
        if attendance_pct is not None and attendance_pct >= 75:
            strengths.append(f"Attendance is {attendance_pct}%, above the 75% monitoring threshold.")
        if latest_gpa and latest_gpa.get("gpa") is not None:
            strengths.append(f"Published GPA for Semester {semester} is {latest_gpa['gpa']}.")
        if not strengths:
            strengths.append("No evidence-based strength can be identified from the currently recorded Semester data.")

        weaknesses = []
        if weakest:
            weaknesses.append(
                f"Lowest recorded internal score: {weakest['course__title'] or 'Subject'} "
                f"({weakest['course_code'] or 'N/A'}) at {weakest['percentage']}% "
                f"({weakest.get('obtained') or 0}/{weakest.get('maximum') or 0})."
            )
        if attendance_pct is not None and attendance_pct < 75:
            weaknesses.append(
                f"Attendance is {attendance_pct}%, below the 75% monitoring threshold."
            )
        if not weaknesses:
            weaknesses.append("No evidence-based weakness can be identified from the currently recorded Semester data.")

        overcome = []
        if weakest:
            overcome.append(
                f"Weakness: Lowest recorded score in {weakest['course__title'] or 'the subject needing attention'} "
                f"({weakest['percentage']}%).\n"
                f"   Suggestion: Allocate additional weekly practice time to this subject, "
                f"review low-scoring assessment topics, and discuss unresolved areas with the subject faculty."
            )
        if attendance_pct is not None and attendance_pct < 75:
            overcome.append(
                "Weakness: Attendance below 75%.\n"
                f"   Suggestion: Prioritize upcoming classes and confirm the attendance recovery "
                "requirement with the class advisor."
            )
        if not overcome:
            overcome.append("No specific weakness identified that requires an overcoming suggestion.")

        recs = [
            f"Technical Skills: Review and strengthen core concepts from {strongest['course__title'] if strongest else 'your strongest subject'} and {weakest['course__title'] if weakest else 'a subject needing attention'}.",
            f"Project Ideas: Build a small {department_name} project applying concepts from {weakest['course__title'] if weakest else 'a recorded subject'} to a practical problem.",
            "Co-Curricular Activities: Participate in a technical club, hackathon, paper presentation, or project showcase.",
        ]

        lines = [
            f"My AI Performance Analysis | Semester {semester}",
            "",
        ]
        if fallback_used and current_semester:
            lines.extend([
                "Current Semester Note:",
                f"Your current semester is Semester {current_semester}, but published academic results "
                f"are not yet available. This analysis uses your latest available academic results "
                f"from Semester {semester}.",
                "",
            ])
        lines.extend([
            "Student Details",
            f"1. Name: {getattr(student, 'name', None) or 'N/A'}",
            f"2. Register Number: {getattr(student, 'reg_no', None) or 'N/A'}",
            f"3. Department: {department_name}",
            f"4. Batch: {getattr(student, 'batch', None) or 'N/A'}",
            f"5. Year: {getattr(student, 'year', None) or 'N/A'}",
            f"6. Semester: {semester}",
            f"7. Section: {getattr(student, 'section', None) or 'N/A'}",
            "",
            "Strengths",
        ])
        for i, s in enumerate(strengths, 1):
            lines.append(f"{i}. {s}")
        lines.append("")
        lines.append("Weaknesses")
        for i, w in enumerate(weaknesses, 1):
            lines.append(f"{i}. {w}")
        lines.append("")
        lines.append("How to Overcome")
        for i, item in enumerate(overcome, 1):
            lines.append(f"{i}. {item}")
        lines.append("")
        lines.append("Recommendations")
        for i, r in enumerate(recs, 1):
            lines.append(f"{i}. {r}")
        lines.append("")
        lines.append("Conclusion")
        lines.append(
            f"1. Your Semester {semester} recorded internal-mark average is {average}%. "
            f"Your strongest subject is {strongest['course__title'] if strongest else 'N/A'} "
            f"({strongest['percentage']}%) and your weakest subject is {weakest['course__title'] if weakest else 'N/A'} "
            f"({weakest['percentage']}%). "
            f"{'Attendance is ' + str(attendance_pct) + '%.' if attendance_pct is not None else 'Attendance data is N/A.'} "
            f"Focus on the areas needing attention and continue building on your strengths."
        )
        lines.extend([
            "",
            "Data Note",
            "1. This analysis uses only the authenticated student's ERP data supplied for the selected semester.",
            "2. Missing or unpublished records are shown as N/A and are not interpreted as poor performance.",
        ])
        return "\n".join(lines)

    def _handle_student_semester_performance_insights(
        self, student, query, semester,
        current_semester=None, fallback_used=False, fallback_reason=None,
    ):
        """Mode B: Analyze a specific explicitly-requested semester only."""
        _subjects, academic_year = self._get_student_subject_enrollments(student, semester)
        rows = self._student_mark_performance_rows(student, semester, academic_year)
        if not rows:
            return (
                f"Academic performance data for Semester {semester} is not currently available."
            )

        ranked = sorted(rows, key=lambda row: (-row["percentage"], str(row["course_code"] or "")))
        average = round(sum(row["percentage"] for row in rows) / len(rows), 2)

        attendance_rows = self._student_hour_attendance_rows(student, semester, academic_year)
        latest_gpa = (
            GPA.objects.filter(student=student, semester__iexact=str(semester))
            .order_by("-academic_year", "-id")
            .values("gpa", "cgpa", "semester", "academic_year")
            .first()
        )
        ctx = self._build_student_context_block(student, semester, academic_year)
        ctx["fallback_used"] = fallback_used
        ctx["current_semester"] = current_semester
        ctx["fallback_reason"] = fallback_reason
        fallback = self._build_semester_fallback(ctx, ranked, attendance_rows, average, latest_gpa)

        user_message = self._build_semester_user_message(
            ctx, ranked, attendance_rows, average, latest_gpa,
        )
        required_sections = [
            f"My AI Performance Analysis | Semester {semester}",
            "Student Details",
            "Strengths",
            "Weaknesses",
            "How to Overcome",
            "Recommendations",
            "Conclusion",
            "Data Note",
        ]
        try:
            response = self._ai_client().chat.completions.create(
                model=self._ai_model(),
                messages=[
                    {
                        "role": "system",
                        "content": STUDENT_PERFORMANCE_SYSTEM_PROMPT.format(
                            semester=semester
                        ),
                    },
                    {"role": "user", "content": user_message},
                ],
                temperature=0.1,
                max_tokens=self._ai_max_tokens(),
            )
            ai_text = self._strip_model_reasoning(
                response.choices[0].message.content,
                preserve_bold=True,
            )
            if ai_text and all(section in ai_text for section in required_sections):
                return ai_text
        except Exception:
            pass
        return fallback

    def _handle_student_current_semester_performance(self, student):
        """Mode A: Analyze the latest semester with meaningful published academic results.

        When the current semester has no meaningful academic data, the system
        falls back to the most recent previous semester that does.
        """
        current_semester = self._semester_number(getattr(student, "semester", None))
        if current_semester is None:
            return (
                "Your current semester is not assigned in the ERP student profile. "
                "Please contact the department office to verify your semester."
            )
        selected_semester, fallback_used, fallback_reason = (
            self._find_latest_available_semester(student, current_semester)
        )
        if selected_semester is None:
            return (
                "Academic performance data is not currently available. "
                "Please check again after your academic records are published in the ERP."
            )
        return self._handle_student_semester_performance_insights(
            student,
            "",
            selected_semester,
            current_semester=current_semester,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
        )

    def _student_recorded_semesters(self, student):
        """Return normalized semesters having any recorded academic data."""
        semester_values = []
        sources = [
            CourseEnrollment.objects.filter(student=student, enroll=True),
            StudentInternalMark.objects.filter(student=student),
            HourAttendance.objects.filter(student=student),
            Result.objects.filter(student=student),
            GPA.objects.filter(student=student),
        ]
        for source in sources:
            semester_values.extend(source.values_list("semester", flat=True).distinct())

        semesters = {
            semester
            for value in semester_values
            for semester in [self._semester_number(value)]
            if semester is not None
        }
        return sorted(semesters)

    def _semester_has_meaningful_academic_data(self, student, semester):
        """Return True when the semester has meaningful published academic results.

        A semester is considered usable when at least one of the following
        metrics is officially recorded:
          1. End-semester marks (Result)
          2. Internal marks (StudentInternalMark)
          3. GPA
          4. Practical marks (part of internal marks)
          5. Assignment marks (part of internal marks)

        Attendance alone is NOT treated as meaningful academic performance
        when no marks/GPA data exists.
        """
        _subjects, academic_year = self._get_student_subject_enrollments(student, semester)
        has_internal_marks = StudentInternalMark.objects.filter(
            student=student, semester__iexact=str(semester),
        ).exclude(
            Q(marks_obtained__isnull=True) & Q(max_marks__isnull=True),
        ).filter(
            Q(marks_obtained__gt=0) | Q(max_marks__gt=0),
        ).exists()
        has_results = Result.objects.filter(
            student=student, semester__iexact=str(semester),
        ).exclude(
            Q(grade__isnull=True) & Q(grade_total__isnull=True),
        ).filter(
            Q(grade__isnull=False) | Q(grade_total__gt=0),
        ).exists()
        has_gpa = GPA.objects.filter(
            student=student, semester__iexact=str(semester),
        ).exclude(
            Q(gpa__isnull=True) & Q(cgpa__isnull=True),
        ).filter(
            Q(gpa__gt=0) | Q(cgpa__gt=0),
        ).exists()
        return has_internal_marks or has_results or has_gpa

    def _find_latest_available_semester(self, student, current_semester):
        """Find the latest semester with meaningful published academic results.

        Returns (selected_semester, fallback_used, fallback_reason).
        If no usable semester exists, returns (None, False, None).
        """
        if current_semester is not None and self._semester_has_meaningful_academic_data(student, current_semester):
            return current_semester, False, None
        recorded = self._student_recorded_semesters(student)
        for sem in reversed(recorded):
            if sem is not None and sem != current_semester and self._semester_has_meaningful_academic_data(student, sem):
                return sem, True, (
                    f"Semester {current_semester} academic results are not published"
                )
        if current_semester is not None and self._semester_has_meaningful_academic_data(student, current_semester):
            return current_semester, False, None
        return None, False, None

    def _student_semester_performance_snapshot(self, student, semester):
        """Build a database-scoped performance snapshot for one semester."""
        _subjects, academic_year = self._get_student_subject_enrollments(student, semester)
        marks = self._student_mark_performance_rows(student, semester, academic_year)
        attendance = self._student_hour_attendance_rows(student, semester, academic_year)
        gpa = (
            GPA.objects.filter(student=student, semester__iexact=str(semester))
            .order_by("-academic_year", "-id")
            .values("gpa", "cgpa", "semester", "academic_year")
            .first()
        )
        results = list(
            Result.objects.filter(student=student, semester__iexact=str(semester))
            .values("course__course_code", "course__title", "grade", "grade_total", "academic_year")
            .order_by("course__course_code")
        )
        return {
            "semester": semester,
            "academic_year": academic_year,
            "marks": marks,
            "attendance": attendance,
            "gpa": gpa,
            "results": results,
        }

    def _handle_student_overall_performance_insights(self, student):
        semesters = self._student_recorded_semesters(student)
        if not semesters:
            return (
                "No recorded academic data is available for your overall performance analysis. "
                "Please check again after your academic records are published in the ERP."
            )

        snapshots = [
            self._student_semester_performance_snapshot(student, semester)
            for semester in semesters
        ]
        if not any(
            snapshot["marks"] or snapshot["attendance"]
            or snapshot["gpa"] or snapshot["results"]
            for snapshot in snapshots
        ):
            return (
                "No recorded marks, attendance, GPA, or semester results are available "
                "for your overall performance analysis."
            )

        mark_records = []
        semester_summaries = []
        all_attended = 0
        all_hours = 0
        for snapshot in snapshots:
            marks = snapshot["marks"]
            total_obtained = sum(row.get("obtained") or 0 for row in marks)
            total_maximum = sum(row.get("maximum") or 0 for row in marks)
            mark_average = (
                round((total_obtained / total_maximum) * 100, 2)
                if total_maximum else None
            )
            semester_attended = sum(row.get("attended") or 0 for row in snapshot["attendance"])
            semester_hours = sum(row.get("total") or 0 for row in snapshot["attendance"])
            attendance_percentage = (
                round((semester_attended / semester_hours) * 100, 2)
                if semester_hours else None
            )
            all_attended += semester_attended
            all_hours += semester_hours
            for row in marks:
                mark_records.append({**row, "semester": snapshot["semester"]})
            semester_summaries.append({
                "semester": snapshot["semester"],
                "academic_year": snapshot["academic_year"],
                "mark_average": mark_average,
                "attendance_percentage": attendance_percentage,
                "gpa": (snapshot["gpa"] or {}).get("gpa"),
                "cgpa": (snapshot["gpa"] or {}).get("cgpa"),
                "results": snapshot["results"],
            })

        overall_obtained = sum(row.get("obtained") or 0 for row in mark_records)
        overall_maximum = sum(row.get("maximum") or 0 for row in mark_records)
        overall_mark_average = (
            round((overall_obtained / overall_maximum) * 100, 2)
            if overall_maximum else None
        )
        overall_attendance = (
            round((all_attended / all_hours) * 100, 2) if all_hours else None
        )
        ranked = sorted(
            mark_records,
            key=lambda row: (-row["percentage"], row["semester"], str(row.get("course_code") or "")),
        )
        strongest = ranked[0] if ranked else None
        weakest = ranked[-1] if ranked else None

        subject_history = {}
        for row in sorted(mark_records, key=lambda item: item["semester"]):
            course_key = str(row.get("course_code") or row.get("course__title") or "").strip()
            if course_key:
                subject_history.setdefault(course_key, []).append(row)
        subject_trends = []
        for history in subject_history.values():
            if len(history) < 2:
                continue
            first, latest = history[0], history[-1]
            change = round(latest["percentage"] - first["percentage"], 2)
            if change == 0:
                direction = "remained consistent"
            elif change > 0:
                direction = "improved"
            else:
                direction = "declined"
            subject_trends.append(
                f"{latest['course__title'] or 'Subject'} ({latest['course_code'] or 'N/A'}) "
                f"{direction} from {first['percentage']}% in Semester {first['semester']} "
                f"to {latest['percentage']}% in Semester {latest['semester']}."
            )

        gpa_points = [
            (summary["semester"], summary["gpa"])
            for summary in semester_summaries
            if summary["gpa"] is not None
        ]
        trend_text = "Insufficient comparable semester data to calculate a trend."
        if len(gpa_points) >= 2:
            difference = round(gpa_points[-1][1] - gpa_points[0][1], 2)
            direction = "improved" if difference > 0 else "declined" if difference < 0 else "remained consistent"
            trend_text = (
                f"GPA {direction} from {gpa_points[0][1]} in Semester {gpa_points[0][0]} "
                f"to {gpa_points[-1][1]} in Semester {gpa_points[-1][0]}."
            )
        else:
            mark_points = [
                (summary["semester"], summary["mark_average"])
                for summary in semester_summaries
                if summary["mark_average"] is not None
            ]
            if len(mark_points) >= 2:
                difference = round(mark_points[-1][1] - mark_points[0][1], 2)
                direction = "improved" if difference > 0 else "declined" if difference < 0 else "remained consistent"
                trend_text = (
                    f"Recorded internal-mark average {direction} from {mark_points[0][1]}% "
                    f"in Semester {mark_points[0][0]} to {mark_points[-1][1]}% "
                    f"in Semester {mark_points[-1][0]}."
                )

        department_name = (
            getattr(getattr(student, "department", None), "Department", None)
            or "your department"
        )
        strongest_text = (
            f"{strongest['course__title'] or 'Subject'} ({strongest['course_code'] or 'N/A'}), "
            f"Semester {strongest['semester']} - {strongest['percentage']}%"
            if strongest else "N/A"
        )
        weakest_text = (
            f"{weakest['course__title'] or 'Subject'} ({weakest['course_code'] or 'N/A'}), "
            f"Semester {weakest['semester']} - {weakest['percentage']}%"
            if weakest else "N/A"
        )
        fallback_lines = [
            "**My Overall AI Performance Analysis**",
            "",
            "**Cumulative Assessment**",
            f"1. Analyzed semesters: {', '.join(str(value) for value in semesters)}. "
            f"Recorded internal-mark average: "
            f"{overall_mark_average if overall_mark_average is not None else 'N/A'}%. "
            f"Overall recorded attendance: "
            f"{overall_attendance if overall_attendance is not None else 'N/A'}%.",
            "",
            "**Long-Term Strengths**",
            f"1. Strongest recorded subject: {strongest_text}",
            "",
            "**Areas Needing Attention**",
            f"1. Lowest recorded subject: {weakest_text}",
            "",
            "**Academic Trends and Consistency**",
            f"1. {trend_text}",
            *[
                f"{index}. {text}"
                for index, text in enumerate(subject_trends[:3], start=2)
            ],
            "",
            "**Action Plan**",
            "1. Review the weakest recorded topics and discuss unresolved areas with the relevant subject faculty.",
            "2. Compare each new assessment with the previous recorded semester and adjust the study schedule early.",
            "3. Maintain attendance at or above 75% in every subject.",
            "",
            "**Department-Related Project Ideas**",
            f"1. Build a small {department_name} project using concepts from {weakest['course__title'] if weakest else 'a recorded subject'}.",
            f"2. Extend a concept from {strongest['course__title'] if strongest else 'a strong subject'} into a demonstrable mini-project.",
            "",
            "**Extracurricular Development**",
            "1. Participate in a technical club, hackathon, paper presentation, or project showcase.",
            "2. Add a sport, cultural activity, volunteering opportunity, or communication activity for balanced development.",
            "",
            "**Attendance Guidance**",
            (
                f"1. Your cumulative recorded attendance is {overall_attendance}%. "
                "Review any semester or subject below 75%."
                if overall_attendance is not None
                else "1. N/A - no attendance records are currently available."
            ),
            "",
            "**Data Note**",
            "1. This analysis uses all currently recorded ERP data up to today; missing or unpublished records are not included.",
        ]
        fallback = "\n".join(fallback_lines)

        semester_context = []
        for summary in semester_summaries:
            result_context = ", ".join(
                f"{row['course__course_code'] or 'N/A'}: grade {row['grade'] or 'N/A'}, "
                f"grade total {row['grade_total'] if row['grade_total'] is not None else 'N/A'}"
                for row in summary["results"]
            ) or "N/A"
            semester_context.append(
                f"Semester {summary['semester']} | AY {summary['academic_year'] or 'N/A'} | "
                f"Internal average {summary['mark_average'] if summary['mark_average'] is not None else 'N/A'} | "
                f"Attendance {summary['attendance_percentage'] if summary['attendance_percentage'] is not None else 'N/A'} | "
                f"GPA {summary['gpa'] if summary['gpa'] is not None else 'N/A'} | "
                f"CGPA {summary['cgpa'] if summary['cgpa'] is not None else 'N/A'} | "
                f"Published grades {result_context}"
            )
        subject_context = "\n".join(
            f"- Semester {row['semester']}: {row['course__title'] or 'Subject'} "
            f"({row['course_code'] or 'N/A'}) {row['percentage']}%"
            for row in ranked
        ) or "N/A"
        user_message = (
            f"Authenticated student: {getattr(student, 'name', None) or 'Student'}\n"
            f"ERP department: {department_name}\n"
            f"Analysis mode: Cumulative / overall performance across all recorded semesters\n"
            f"Analysis date: {timezone.localdate().isoformat()}\n"
            f"Recorded semesters: {', '.join(str(value) for value in semesters)}\n"
            f"Cumulative internal-mark average: {overall_mark_average if overall_mark_average is not None else 'N/A'}\n"
            f"Cumulative attendance: {overall_attendance if overall_attendance is not None else 'N/A'}\n"
            f"Calculated trend: {trend_text}\n\n"
            f"Comparable subject trends:\n{chr(10).join(subject_trends) if subject_trends else 'N/A'}\n\n"
            f"Semester summaries:\n{chr(10).join(semester_context)}\n\n"
            f"Recorded subject performance:\n{subject_context}\n\n"
            f"INSTRUCTIONS: This is a cumulative analysis across all recorded semesters. "
            f"Do NOT limit analysis to any single semester. "
            f"Do NOT calculate values yourself; use the numbers provided. "
            f"Do NOT claim knowledge, intelligence, personality, motivation, career interest, or any personal attribute. "
            f"Only state what the marks, attendance, and GPA data directly support."
        )
        try:
            response = self._ai_client().chat.completions.create(
                model=self._ai_model(),
                messages=[
                    {"role": "system", "content": STUDENT_OVERALL_PERFORMANCE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.1,
                max_tokens=self._ai_max_tokens(),
            )
            ai_text = self._strip_model_reasoning(
                response.choices[0].message.content,
                preserve_bold=True,
            )
            required_sections = [
                "**My Overall AI Performance Analysis**",
                "**Cumulative Assessment**",
                "**Long-Term Strengths**",
                "**Areas Needing Attention**",
                "**Academic Trends and Consistency**",
                "**Action Plan**",
                "**Department-Related Project Ideas**",
                "**Extracurricular Development**",
                "**Attendance Guidance**",
                "**Data Note**",
            ]
            if ai_text and all(section in ai_text for section in required_sections):
                return ai_text
        except Exception:
            pass
        return fallback

    def _hod_department_context(self, faculty_id):
        """Return the HOD profile and its authoritative department mapping."""
        faculty = self._get_faculty_info(faculty_id)
        if not faculty:
            return None, None, "Authentication Error: Faculty profile not found."
        department = getattr(faculty, "department", None)
        if not department:
            return faculty, None, "Your HOD account is not mapped to an ERP department."
        return faculty, department, None

    def _hod_students(self, department):
        return self._department_student_queryset(department).filter(
            is_active=True, is_discontinued=False
        )

    def _hod_attendance_percentages(self, students):
        student_map = {
            student.id: {"student": student, "present": 0, "total": 0}
            for student in students
        }
        if not student_map:
            return []
        rows = Daily_Attendance.objects.filter(
            student_id__in=student_map
        ).values_list("student_id", "morning_status", "afternoon_status")
        for student_id, morning, afternoon in rows:
            item = student_map.get(student_id)
            if not item:
                continue
            for status in (morning, afternoon):
                if status:
                    item["total"] += 1
                    if status in {"Present", "On Duty"}:
                        item["present"] += 1
        result = []
        for item in student_map.values():
            if item["total"]:
                item["percentage"] = round(
                    item["present"] * 100 / item["total"], 2
                )
                result.append(item)
        return result

    def _hod_mark_percentages(self, department):
        rows = StudentInternalMark.objects.filter(
            student__department=department,
            student__is_active=True,
            student__is_discontinued=False,
            marks_obtained__isnull=False,
            max_marks__isnull=False,
        ).values(
            "student_id", "student__name", "student__reg_no",
            "student__year", "student__semester", "student__section",
        ).annotate(obtained=Sum("marks_obtained"), maximum=Sum("max_marks"))
        result = []
        for row in rows:
            maximum = row["maximum"] or 0
            if maximum:
                row["percentage"] = round((row["obtained"] or 0) * 100 / maximum, 2)
                result.append(row)
        return result

    def _format_hod_top_students_by_year(self, department, rows, limit=10):
        rows = sorted(rows, key=lambda item: item["percentage"], reverse=True)
        if not rows:
            return "No internal-mark records are available in your department."

        grouped = {}
        for row in rows:
            year = row.get("student__year") or "N/A"
            grouped.setdefault(year, []).append(row)

        lines = [f"Top {limit} Students by Year - {department.Department}"]
        for year in sorted(grouped, key=lambda value: str(value)):
            ranked = grouped[year][:limit]
            table_rows = []
            for index, row in enumerate(ranked, start=1):
                table_rows.append([
                    index,
                    row.get("student__name"),
                    row.get("student__reg_no"),
                    row.get("student__year") or "N/A",
                    row.get("student__semester") or "N/A",
                    row.get("student__section") or "N/A",
                    f"{row['percentage']}%",
                ])
            lines.extend([
                "",
                f"Year {year} - showing {len(ranked)} of {len(grouped[year])} students",
                self._format_pipe_table(
                    ["Rank", "Student", "Register Number", "Year", "Semester", "Section", "Marks"],
                    table_rows,
                ),
            ])
        return "\n".join(lines)

    def _format_hod_ranked_students(self, heading, rows, reverse=False, limit=10):
        rows = sorted(rows, key=lambda item: item["percentage"], reverse=reverse)[:limit]
        if not rows:
            return "No internal-mark records are available in your department."
        lines = [heading]
        for index, row in enumerate(rows, start=1):
            lines.append(
                f"{index}. {row['student__name']} ({row['student__reg_no']}) - "
                f"{row['percentage']}%"
            )
        return "\n".join(lines)

    def _handle_hod_student_search(self, faculty_id, query):
        faculty, department, error = self._hod_department_context(faculty_id)
        if error:
            return error
        search_text = re.sub(
            r"(?i)\b(?:search|find|show|view|get|student|details|profile|for)\b",
            " ",
            query,
        )
        search_text = " ".join(search_text.split()).strip(" ?.-")
        if not search_text:
            return "Please provide the student's name or register number."
        students = self._hod_students(department).filter(
            Q(reg_no__iexact=search_text) | Q(name__icontains=search_text)
        ).order_by("name")[:20]
        if not students:
            # A matching record in another department must not be disclosed.
            outside = self._student_queryset().filter(
                Q(reg_no__iexact=search_text) | Q(name__icontains=search_text)
            ).exclude(department=department).exists()
            if outside:
                return "Access denied: HOD access is limited to your mapped department."
            return f"No student matching '{search_text}' was found in your department."
        lines = [f"Students in {department.Department}:"]
        for student in students:
            mentor = getattr(getattr(student, "mentor", None), "name", None) or "N/A"
            advisor = getattr(getattr(student, "ca", None), "name", None) or "N/A"
            lines.append(
                f"- {student.name} ({student.reg_no}) | Year {student.year or 'N/A'} | "
                f"Section {student.section or 'N/A'} | Mentor: {mentor} | CA: {advisor}"
            )
        return "\n".join(lines)

    def _handle_hod_attendance_analytics(self, faculty_id, threshold=75):
        faculty, department, error = self._hod_department_context(faculty_id)
        if error:
            return error
        rows = self._hod_attendance_percentages(list(self._hod_students(department)))
        if threshold is not None:
            rows = [item for item in rows if item["percentage"] < threshold]
        rows.sort(key=lambda item: item["percentage"])
        if not rows:
            if threshold is None:
                return f"No attendance records were found in {department.Department}."
            return f"No students with recorded attendance below {threshold}% were found in {department.Department}."
        if threshold is None:
            lines = [f"Department attendance - {department.Department}:"]
        else:
            lines = [f"Students below {threshold}% attendance - {department.Department}:"]
        for item in rows[:100]:
            student = item["student"]
            lines.append(f"- {student.name} ({student.reg_no}) - {item['percentage']}%")
        lines.append(f"Total: {len(rows)}")
        return "\n".join(lines)

    def _handle_hod_subject_analytics(self, faculty_id):
        faculty, department, error = self._hod_department_context(faculty_id)
        if error:
            return error
        rows = StudentInternalMark.objects.filter(
            student__department=department,
            student__is_active=True,
            student__is_discontinued=False,
            marks_obtained__isnull=False,
            max_marks__isnull=False,
        ).values(
            "student__year", "student__semester",
            "course_id", "course__course_code", "course__title",
        ).annotate(
            obtained=Sum("marks_obtained"),
            maximum=Sum("max_marks"),
            students=Count("student_id", distinct=True),
        )
        results = []
        for row in rows:
            if row["maximum"]:
                row["percentage"] = round(row["obtained"] * 100 / row["maximum"], 2)
                results.append(row)
        results.sort(key=lambda row: (
            str(row.get("student__year") or ""),
            str(row.get("student__semester") or ""),
            row["percentage"],
        ))
        if not results:
            return "No subject mark records are available in your department."

        grouped = {}
        for row in results:
            key = (row.get("student__year") or "N/A", row.get("student__semester") or "N/A")
            grouped.setdefault(key, []).append(row)

        lines = [f"Subject-wise Performance - {department.Department}"]
        overall_lowest = min(results, key=lambda row: row["percentage"])
        lowest_rows = []
        for key in sorted(grouped, key=lambda item: (str(item[0]), str(item[1]))):
            year, semester = key
            subject_rows = []
            for row in sorted(grouped[key], key=lambda item: item["percentage"]):
                subject_rows.append([
                    row.get("course__title") or row.get("course__course_code") or "Unknown subject",
                    row.get("course__course_code"),
                    row.get("students"),
                    f"{row['percentage']}%",
                ])
            lowest = min(grouped[key], key=lambda item: item["percentage"])
            lowest_rows.append([
                year,
                semester,
                lowest.get("course__title") or lowest.get("course__course_code") or "Unknown subject",
                lowest.get("course__course_code"),
                f"{lowest['percentage']}%",
            ])
            lines.extend([
                "",
                f"Year {year} | Semester {semester}",
                self._format_pipe_table(
                    ["Subject", "Code", "Students", "Average"],
                    subject_rows,
                ),
            ])

        lines.extend([
            "",
            "Lowest Average By Year/Semester",
            self._format_pipe_table(
                ["Year", "Semester", "Subject", "Code", "Average"],
                lowest_rows,
            ),
            "",
            "Overall Lowest Average",
            self._format_pipe_table(
                ["Subject", "Code", "Year", "Semester", "Average"],
                [[
                    overall_lowest.get("course__title") or overall_lowest.get("course__course_code") or "Unknown subject",
                    overall_lowest.get("course__course_code"),
                    overall_lowest.get("student__year") or "N/A",
                    overall_lowest.get("student__semester") or "N/A",
                    f"{overall_lowest['percentage']}%",
                ]],
            ),
        ])
        return "\n".join(lines)

    def _handle_hod_class_analytics(self, faculty_id):
        faculty, department, error = self._hod_department_context(faculty_id)
        if error:
            return error
        rows = StudentInternalMark.objects.filter(
            student__department=department,
            student__is_active=True,
            student__is_discontinued=False,
            marks_obtained__isnull=False,
            max_marks__isnull=False,
        ).values("student__year", "student__semester", "student__section").annotate(
            obtained=Sum("marks_obtained"), maximum=Sum("max_marks"),
            students=Count("student_id", distinct=True),
        )
        results = []
        for row in rows:
            if row["maximum"]:
                row["percentage"] = round(row["obtained"] * 100 / row["maximum"], 2)
                results.append(row)
        results.sort(key=lambda row: (
            str(row.get("student__year") or ""),
            str(row.get("student__semester") or ""),
            str(row.get("student__section") or ""),
        ))
        if not results:
            return "No class-level mark records are available in your department."
        rows = []
        for row in results:
            rows.append([
                row.get("student__year") or "N/A",
                row.get("student__semester") or "N/A",
                row.get("student__section") or "N/A",
                row.get("students"),
                f"{row['percentage']}%",
            ])
        lowest = min(results, key=lambda item: item["percentage"])
        return "\n".join([
            f"Class and Section Comparison - {department.Department}",
            "",
            self._format_pipe_table(
                ["Year", "Semester", "Section", "Students With Marks", "Average Internal Marks"],
                rows,
            ),
            "",
            "Lowest Class Average",
            self._format_pipe_table(
                ["Year", "Semester", "Section", "Average Internal Marks"],
                [[
                    lowest.get("student__year") or "N/A",
                    lowest.get("student__semester") or "N/A",
                    lowest.get("student__section") or "N/A",
                    f"{lowest['percentage']}%",
                ]],
            ),
        ])

    def _format_pipe_table(self, headers, rows):
        def clean(value):
            if value is None or value == "":
                return "N/A"
            return str(value).replace("|", "/").strip() or "N/A"

        lines = [" | ".join(clean(header) for header in headers)]
        lines.append(" | ".join("---" for _ in headers))
        for row in rows:
            lines.append(" | ".join(clean(cell) for cell in row))
        return "\n".join(lines)

    def _activity_student_cells(self, record):
        student = getattr(record, "student", None)
        department = getattr(record, "department", None) or getattr(student, "department", None)
        return [
            getattr(student, "name", None),
            getattr(student, "reg_no", None),
            getattr(department, "Department", None),
            getattr(record, "year", None) or getattr(student, "year", None),
            getattr(record, "semester", None) or getattr(student, "semester", None),
            getattr(record, "section", None) or getattr(student, "section", None),
        ]

    def _department_activity_queryset(self, model, department):
        return (
            model.objects.filter(Q(student__department=department) | Q(department=department))
            .select_related("student", "student__department", "department")
            .distinct()
        )

    def _format_department_publications(self, department, records, total_count):
        if not records:
            return f"Department Student Publications - {department.Department}\nNo student publication records were found."
        rows = []
        for record in records:
            rows.append(
                self._activity_student_cells(record)
                + [
                    getattr(record, "title", None),
                    getattr(record, "program_name", None),
                    getattr(record, "publication_date", None),
                    getattr(record, "status", None),
                ]
            )
        return "\n".join([
            f"Department Student Publications - {department.Department}",
            f"Total records: {total_count}",
            "",
            self._format_pipe_table(
                [
                    "Student", "Register Number", "Department", "Year",
                    "Semester", "Section", "Publication Title", "Program",
                    "Publication Date", "Status",
                ],
                rows,
            ),
        ])

    def _format_department_co_curricular(self, department, records, total_count):
        if not records:
            return f"Department Co-curricular Activities - {department.Department}\nNo co-curricular activity records were found."
        rows = []
        for record in records:
            date_range = "N/A"
            from_date = getattr(record, "from_date", None)
            to_date = getattr(record, "to_date", None)
            if from_date and to_date:
                date_range = f"{from_date} to {to_date}"
            elif from_date:
                date_range = str(from_date)
            rows.append(
                self._activity_student_cells(record)
                + [
                    getattr(record, "activity_type", None),
                    getattr(record, "event_name", None),
                    getattr(record, "level", None),
                    date_range,
                    getattr(record, "status", None),
                ]
            )
        return "\n".join([
            f"Department Co-curricular Activities - {department.Department}",
            f"Total records: {total_count}",
            "",
            self._format_pipe_table(
                [
                    "Student", "Register Number", "Department", "Year",
                    "Semester", "Section", "Activity Type", "Event Name",
                    "Level", "Date", "Status",
                ],
                rows,
            ),
        ])

    def _format_department_projects(self, department, records, total_count):
        if not records:
            return f"Department Student Projects - {department.Department}\nNo student project records were found."
        rows = []
        for record in records:
            rows.append(
                self._activity_student_cells(record)
                + [
                    getattr(record, "title", None),
                    getattr(record, "domain", None),
                    getattr(record, "activity_name", None),
                    getattr(record, "organisation", None),
                    getattr(record, "status", None),
                ]
            )
        return "\n".join([
            f"Department Student Projects - {department.Department}",
            f"Total records: {total_count}",
            "",
            self._format_pipe_table(
                [
                    "Student", "Register Number", "Department", "Year",
                    "Semester", "Section", "Project Title", "Domain",
                    "Activity", "Organisation", "Status",
                ],
                rows,
            ),
        ])

    def _format_department_achievements(self, department, records, total_count):
        if not records:
            return f"Department Student Achievements - {department.Department}\nNo student achievement records were found."
        rows = []
        for record in records:
            rows.append(
                self._activity_student_cells(record)
                + [
                    getattr(record, "award_name", None),
                    getattr(record, "contest", None),
                    getattr(record, "given_by", None),
                    getattr(record, "date", None),
                    getattr(record, "status", None),
                ]
            )
        return "\n".join([
            f"Department Student Achievements - {department.Department}",
            f"Total records: {total_count}",
            "",
            self._format_pipe_table(
                [
                    "Student", "Register Number", "Department", "Year",
                    "Semester", "Section", "Achievement", "Contest",
                    "Given By", "Date", "Status",
                ],
                rows,
            ),
        ])

    def _handle_hod_activity_records(self, faculty_id, query):
        faculty, department, error = self._hod_department_context(faculty_id)
        if error:
            return error

        query_text = query.lower()
        sections = []

        if "publication" in query_text or "published" in query_text:
            qs = self._department_activity_queryset(StudentPublication, department)
            total_count = qs.count()
            records = list(qs.order_by("-publication_date", "-created_at")[:100])
            sections.append(self._format_department_publications(department, records, total_count))

        if "co-curricular" in query_text or "co curricular" in query_text:
            qs = self._department_activity_queryset(StudentCO_EX_Curricular, department)
            total_count = qs.count()
            records = list(qs.order_by("-from_date", "-created_at")[:100])
            sections.append(self._format_department_co_curricular(department, records, total_count))

        if "project" in query_text:
            qs = self._department_activity_queryset(StudentProjects, department)
            total_count = qs.count()
            records = list(qs.order_by("-date", "-created_at")[:100])
            sections.append(self._format_department_projects(department, records, total_count))

        if "achievement" in query_text:
            qs = self._department_activity_queryset(StudentAchievements, department)
            total_count = qs.count()
            records = list(qs.order_by("-date", "-created_at")[:100])
            sections.append(self._format_department_achievements(department, records, total_count))

        return "\n\n".join(sections) if sections else None

    def _handle_hod_people_report(self, faculty_id, query):
        faculty, department, error = self._hod_department_context(faculty_id)
        if error:
            return error
        students = self._hod_students(department)
        is_mentor_report = "mentor" in query.lower()
        if is_mentor_report:
            rows = students.values("mentor_id", "mentor__name", "mentor__faculty_id").annotate(
                students=Count("id")
            ).order_by("mentor__name")
            heading = f"Mentor report - {department.Department}"
            person_label = "Mentor"
            name_field, id_field = "mentor__name", "mentor__faculty_id"
        else:
            rows = students.values("ca_id", "ca__name", "ca__faculty_id").annotate(
                students=Count("id")
            ).order_by("ca__name")
            heading = f"Class advisor report - {department.Department}"
            person_label = "Class Advisor"
            name_field, id_field = "ca__name", "ca__faculty_id"

        grouped = {}
        for row in rows:
            name = row.get(name_field) or "Unassigned"
            employee_id = row.get(id_field) or "N/A"
            key = (name, employee_id)
            grouped[key] = grouped.get(key, 0) + (row.get("students") or 0)

        ordered_rows = sorted(
            grouped.items(),
            key=lambda item: (item[0][0] == "Unassigned", item[0][0].casefold(), str(item[0][1])),
        )
        assigned_rows = [item for item in ordered_rows if item[0][0] != "Unassigned"]
        assigned_students = sum(count for (name, _employee_id), count in ordered_rows if name != "Unassigned")
        unassigned_students = sum(count for (name, _employee_id), count in ordered_rows if name == "Unassigned")

        lines = [heading, "", "Summary"]
        lines.append(self._format_pipe_table(
            ["Metric", "Count"],
            [
                ["Total active students", students.count()],
                [f"Assigned {person_label.lower()}s", len(assigned_rows)],
                ["Students assigned", assigned_students],
                ["Students unassigned", unassigned_students],
            ],
        ))
        if ordered_rows:
            lines.extend(["", f"{person_label} Assignments"])
            lines.append(self._format_pipe_table(
                [person_label, "Employee ID", "Students"],
                [[name, employee_id, count] for (name, employee_id), count in ordered_rows],
            ))
        return "\n".join(lines)

    def _hod_faculty_role_map(self, faculty_ids):
        employee_ids = [str(item) for item in faculty_ids if item not in (None, "")]
        if not employee_ids:
            return {}
        try:
            users = self._approval_user_queryset().select_related("role").filter(
                Employee_id__in=employee_ids,
                is_active=1,
            )
            return {
                str(user.Employee_id): getattr(getattr(user, "role", None), "role", None)
                for user in users
            }
        except Exception:
            return {}

    def _hod_staff_group_label(self, staff, role_map):
        category = getattr(getattr(staff, "category", None), "category_name", None)
        if category:
            return category
        employee_id = getattr(staff, "faculty_id", None)
        role_name = role_map.get(str(employee_id)) if employee_id not in (None, "") else None
        if role_name:
            return role_name
        designation = getattr(staff, "designation", None)
        designation_name = getattr(designation, "designation_name", None)
        if getattr(designation, "is_teaching", False):
            return "Teaching Staff"
        return designation_name or "Uncategorized Staff"

    def _handle_hod_teacher_report(self, faculty_id):
        faculty, department, error = self._hod_department_context(faculty_id)
        if error:
            return error
        teachers = list(
            general_information.objects.filter(department=department)
            .select_related("designation", "category")
            .order_by("category__category_name", "designation__designation_name", "name")[:500]
        )
        assignments = AssignSubjectFaculty.objects.filter(
            Q(department=department) | Q(course__department=department),
            is_active=True,
        ).values("faculty_id").annotate(subjects=Count("course_id", distinct=True))
        assignment_counts = {row["faculty_id"]: row["subjects"] for row in assignments}
        role_map = self._hod_faculty_role_map([getattr(staff, "faculty_id", None) for staff in teachers])

        grouped = {}
        for staff in teachers:
            group = self._hod_staff_group_label(staff, role_map)
            grouped.setdefault(group, []).append(staff)

        lines = [f"Teacher report - {department.Department}", "", "Summary"]
        summary_rows = []
        for group in sorted(grouped):
            staff_members = grouped[group]
            active_subjects = sum(assignment_counts.get(getattr(staff, "id", None), 0) for staff in staff_members)
            summary_rows.append([group, len(staff_members), active_subjects])
        lines.append(self._format_pipe_table(["Staff Category", "Staff Count", "Active Subjects"], summary_rows))

        for group in sorted(grouped):
            rows = []
            for staff in grouped[group]:
                designation = getattr(getattr(staff, "designation", None), "designation_name", None)
                rows.append([
                    getattr(staff, "name", None),
                    getattr(staff, "faculty_id", None),
                    designation,
                    assignment_counts.get(getattr(staff, "id", None), 0),
                ])
            lines.extend(["", group])
            lines.append(self._format_pipe_table(
                ["Staff", "Employee ID", "Designation", "Active Subjects"],
                rows,
            ))
        return "\n".join(lines)

    def _handle_hod_notifications(self, faculty_id):
        faculty, department, error = self._hod_department_context(faculty_id)
        if error:
            return error
        notices = Announcement.objects.filter(is_active=True).filter(
            Q(departments=department)
            | Q(users=faculty)
            | Q(faculty__department=department)
            | Q(roles__role__iexact="HOD")
            | Q(departments__isnull=True, users__isnull=True, roles__isnull=True)
        ).distinct().order_by("-created_at")[:20]
        if not notices:
            return f"No active notifications were found for {department.Department}."
        lines = [f"Department notifications - {department.Department}:"]
        for notice in notices:
            lines.append(f"- {notice.title or 'Untitled'}: {notice.message or 'No message'}")
        return "\n".join(lines)

    def _handle_hod_performance_summary(self, faculty_id):
        faculty, department, error = self._hod_department_context(faculty_id)
        if error:
            return error
        students = list(self._hod_students(department))
        marks = self._hod_mark_percentages(department)
        attendance = self._hod_attendance_percentages(students)
        mark_average = round(sum(row["percentage"] for row in marks) / len(marks), 2) if marks else None
        attendance_average = round(sum(row["percentage"] for row in attendance) / len(attendance), 2) if attendance else None

        student_groups = {}
        for student in students:
            key = (
                getattr(student, "year", None) or "N/A",
                getattr(student, "semester", None) or "N/A",
                getattr(student, "section", None) or "N/A",
            )
            student_groups.setdefault(key, {"active": 0, "student_ids": set()})
            student_groups[key]["active"] += 1
            student_id = getattr(student, "id", None)
            if student_id is not None:
                student_groups[key]["student_ids"].add(student_id)

        group_rows = []
        all_keys = set(student_groups)
        for row in marks:
            all_keys.add((
                row.get("student__year") or "N/A",
                row.get("student__semester") or "N/A",
                row.get("student__section") or "N/A",
            ))
        for item in attendance:
            student = item["student"]
            all_keys.add((
                getattr(student, "year", None) or "N/A",
                getattr(student, "semester", None) or "N/A",
                getattr(student, "section", None) or "N/A",
            ))

        for key in sorted(all_keys, key=lambda item: (str(item[0]), str(item[1]), str(item[2]))):
            year, semester, section = key
            group = student_groups.get(key, {"active": 0, "student_ids": set()})
            group_marks = [
                row for row in marks
                if (row.get("student__year") or "N/A", row.get("student__semester") or "N/A", row.get("student__section") or "N/A") == key
            ]
            group_attendance = [
                row for row in attendance
                if (
                    getattr(row["student"], "year", None) or "N/A",
                    getattr(row["student"], "semester", None) or "N/A",
                    getattr(row["student"], "section", None) or "N/A",
                ) == key
            ]
            avg_marks = round(sum(row["percentage"] for row in group_marks) / len(group_marks), 2) if group_marks else None
            avg_attendance = round(sum(row["percentage"] for row in group_attendance) / len(group_attendance), 2) if group_attendance else None
            group_rows.append([
                year,
                semester,
                section,
                group["active"],
                len(group_marks),
                f"{avg_marks}%" if avg_marks is not None else "N/A",
                f"{avg_attendance}%" if avg_attendance is not None else "N/A",
                sum(row["percentage"] < 50 for row in group_marks),
                sum(row["percentage"] < 75 for row in group_attendance),
            ])

        low_mark_all = [row for row in marks if row["percentage"] < 50]
        low_mark_rows = []
        for row in sorted(
            low_mark_all,
            key=lambda item: item["percentage"],
        )[:100]:
            low_mark_rows.append([
                row.get("student__name"),
                row.get("student__reg_no"),
                row.get("student__year") or "N/A",
                row.get("student__semester") or "N/A",
                row.get("student__section") or "N/A",
                f"{row['percentage']}%",
            ])

        low_attendance_all = [row for row in attendance if row["percentage"] < 75]
        low_attendance_rows = []
        for row in sorted(
            low_attendance_all,
            key=lambda item: item["percentage"],
        )[:100]:
            student = row["student"]
            low_attendance_rows.append([
                getattr(student, "name", None),
                getattr(student, "reg_no", None),
                getattr(student, "year", None) or "N/A",
                getattr(student, "semester", None) or "N/A",
                getattr(student, "section", None) or "N/A",
                f"{row['percentage']}%",
            ])

        lines = [
            f"Department Performance Summary - {department.Department}",
            "",
            "Overview",
            self._format_pipe_table(
                ["Metric", "Value"],
                [
                    ["Active students", len(students)],
                    ["Students with internal marks", len(marks)],
                    ["Average internal marks", f"{mark_average}%" if mark_average is not None else "N/A"],
                    ["Average recorded attendance", f"{attendance_average}%" if attendance_average is not None else "N/A"],
                    ["Students below 50% marks", len(low_mark_all)],
                    ["Students below 75% attendance", len(low_attendance_all)],
                ],
            ),
            "",
            "Year/Semester/Section Summary",
            self._format_pipe_table(
                [
                    "Year", "Semester", "Section", "Active Students",
                    "Students With Marks", "Average Marks", "Average Attendance",
                    "Below 50% Marks", "Below 75% Attendance",
                ],
                group_rows,
            ),
        ]

        if low_mark_rows:
            lines.extend([
                "",
                "Students Below 50% Marks",
                self._format_pipe_table(
                    ["Student", "Register Number", "Year", "Semester", "Section", "Marks"],
                    low_mark_rows,
                ),
            ])
        else:
            lines.extend(["", "Students Below 50% Marks", "No students are below 50% marks based on recorded internal marks."])

        if low_attendance_rows:
            lines.extend([
                "",
                "Students Below 75% Attendance",
                self._format_pipe_table(
                    ["Student", "Register Number", "Year", "Semester", "Section", "Attendance"],
                    low_attendance_rows,
                ),
            ])
        else:
            lines.extend(["", "Students Below 75% Attendance", "No students are below 75% attendance based on recorded attendance."])

        return "\n".join(lines)

    def _handle_hod_mentoring_report(self, faculty_id):
        faculty, department, error = self._hod_department_context(faculty_id)
        if error:
            return error

        students = list(self._hod_students(department))
        student_lookup = {getattr(student, "id", None): student for student in students}
        marks = {row["student_id"]: row for row in self._hod_mark_percentages(department)}
        attendance = {
            getattr(row["student"], "id", None): row
            for row in self._hod_attendance_percentages(students)
        }

        grouped = {}
        total_risk = 0
        for student_id in set(marks) | set(attendance):
            mark_row = marks.get(student_id, {})
            attendance_row = attendance.get(student_id, {})
            student = attendance_row.get("student") or student_lookup.get(student_id)
            mark = mark_row.get("percentage")
            attend = attendance_row.get("percentage")
            mark_gap = 50 - mark if mark is not None and mark < 50 else 0
            attendance_gap = 75 - attend if attend is not None and attend < 75 else 0
            if mark_gap <= 0 and attendance_gap <= 0:
                continue

            year = mark_row.get("student__year") or getattr(student, "year", None) or "N/A"
            semester = mark_row.get("student__semester") or getattr(student, "semester", None) or "N/A"
            section = mark_row.get("student__section") or getattr(student, "section", None) or "N/A"
            name = getattr(student, "name", None) or mark_row.get("student__name")
            reg_no = getattr(student, "reg_no", None) or mark_row.get("student__reg_no")
            reasons = []
            if mark_gap > 0:
                reasons.append("Marks below 50%")
            if attendance_gap > 0:
                reasons.append("Attendance below 75%")
            severity = mark_gap + attendance_gap
            grouped.setdefault((year, semester, section), []).append({
                "name": name,
                "reg_no": reg_no,
                "year": year,
                "semester": semester,
                "section": section,
                "mark": mark,
                "attendance": attend,
                "reason": " and ".join(reasons),
                "severity": severity,
            })
            total_risk += 1

        if not grouped:
            return "No students currently meet the mentoring-risk thresholds (marks below 50% or attendance below 75%)."

        lines = [
            f"Students Needing Mentoring - {department.Department}",
            "Thresholds: marks below 50% or attendance below 75%.",
            "Showing top 3 most severe students in each Year/Semester/Section group.",
            f"Total students meeting criteria: {total_risk}",
        ]
        for key in sorted(grouped, key=lambda item: (str(item[0]), str(item[1]), str(item[2]))):
            rows = sorted(
                grouped[key],
                key=lambda item: (-item["severity"], item["mark"] if item["mark"] is not None else 101, item["attendance"] if item["attendance"] is not None else 101),
            )
            year, semester, section = key
            table_rows = []
            for item in rows[:3]:
                table_rows.append([
                    item["name"],
                    item["reg_no"],
                    item["year"],
                    item["semester"],
                    item["section"],
                    f"{item['mark']}%" if item["mark"] is not None else "N/A",
                    f"{item['attendance']}%" if item["attendance"] is not None else "N/A",
                    item["reason"],
                ])
            lines.extend([
                "",
                f"Year {year} | Semester {semester} | Section {section} - showing {len(table_rows)} of {len(rows)} students",
                self._format_pipe_table(
                    [
                        "Student", "Register Number", "Year", "Semester",
                        "Section", "Marks", "Attendance", "Reason",
                    ],
                    table_rows,
                ),
            ])
        return "\n".join(lines)

    def _route_hod_department_query(self, faculty_id, raw_query):
        """HOD-first intent router; returns None when normal routing should continue."""
        query = raw_query.lower()
        faculty, own_department, context_error = self._hod_department_context(faculty_id)
        if context_error:
            return context_error
        requested_department = self._extract_department(query)
        if requested_department and not self._same_department(
            requested_department, own_department
        ):
            return "Access denied: HOD access is limited to your mapped department."
        if any(term in query for term in ["attendance below", "below 75", "low attendance"]):
            match = re.search(r"below\s+(\d{1,3})", query)
            threshold = int(match.group(1)) if match else 75
            return self._handle_hod_attendance_analytics(faculty_id, threshold)
        if "attendance records" in query or "department attendance" in query:
            return self._handle_hod_attendance_analytics(faculty_id, None)
        if "top performer" in query or re.search(r"\btop\s+\d*\s*students?\b", query):
            match = re.search(r"\btop\s+(\d+)", query)
            limit = min(int(match.group(1)), 100) if match else 10
            faculty, department, error = self._hod_department_context(faculty_id)
            return error or self._format_hod_top_students_by_year(
                department,
                self._hod_mark_percentages(department),
                limit=limit,
            )
        if "low performer" in query or "low-performing" in query:
            faculty, department, error = self._hod_department_context(faculty_id)
            return error or self._format_hod_ranked_students(
                f"Low-performing students - {department.Department}:",
                [row for row in self._hod_mark_percentages(department) if row["percentage"] < 50],
                limit=100,
            )
        if "need mentoring" in query or "needs mentoring" in query:
            return self._handle_hod_mentoring_report(faculty_id)
        if "placement-ready" in query or "placement ready" in query:
            faculty, department, error = self._hod_department_context(faculty_id)
            if error:
                return error
            students = list(self._hod_students(department))
            attendance = {row["student"].id: row["percentage"] for row in self._hod_attendance_percentages(students)}
            ready = []
            for student in students:
                try:
                    cgpa = float(self._get_latest_gcpa(student))
                except (TypeError, ValueError):
                    continue
                if cgpa >= 7 and attendance.get(student.id, 0) >= 75:
                    ready.append((student, cgpa, attendance[student.id]))
            lines = [f"Placement-ready students - {department.Department} (CGPA >= 7.0 and attendance >= 75%):"]
            lines.extend(f"- {student.name} ({student.reg_no}) | CGPA: {cgpa} | Attendance: {attend}%" for student, cgpa, attend in ready[:100])
            return "\n".join(lines) if ready else lines[0] + "\nNo students currently meet this reporting threshold."
        if any(term in query for term in [
            "lowest average", "subject-wise", "subject wise",
            "all subject marks", "department marks",
        ]):
            return self._handle_hod_subject_analytics(faculty_id)
        if "compare" in query or "average marks by class" in query or "class average" in query:
            return self._handle_hod_class_analytics(faculty_id)
        if any(term in query for term in ["department performance", "performance summary", "department summary"]):
            return self._handle_hod_performance_summary(faculty_id)
        if any(term in query for term in ["project", "publication", "achievement", "co-curricular", "curricular"]):
            return self._handle_hod_activity_records(faculty_id, query)
        if "mentor report" in query or "mentor details" in query:
            return self._handle_hod_people_report(faculty_id, query)
        if "teacher report" in query:
            return self._handle_hod_teacher_report(faculty_id)
        if "class advisor details" in query or "class advisor report" in query:
            return self._handle_hod_people_report(faculty_id, query)
        if "notification" in query or "announcement" in query:
            return self._handle_hod_notifications(faculty_id)
        if re.match(r"(?i)^\s*(?:search|find|show|view|get)\s+(?:for\s+)?student\b", raw_query):
            return self._handle_hod_student_search(faculty_id, raw_query)
        return None

    def _handle_role_scoped_student_list(
        self, faculty_id, active_role, query, target_dept=None, target_batch=None
    ):
        """Route student lists through the logged-in user's active ERP role."""
        if self._is_admin_role(active_role) or self._is_hod_role(active_role):
            return self._handle_list_students(
                faculty_id,
                active_role,
                target_dept=target_dept,
                target_batch=target_batch,
            )

        if self._is_ca_role(active_role):
            return self._handle_my_students(
                faculty_id,
                relations={"ca"},
                target_dept=target_dept,
                target_batch=target_batch,
            )

        if self._is_mentor_role(active_role):
            return self._handle_my_students(
                faculty_id,
                relations={"mentor"},
                target_dept=target_dept,
                target_batch=target_batch,
            )

        if self._is_teacher_role(active_role):
            target_course_code = self._extract_course_code(query)
            return self._handle_list_students(
                faculty_id,
                active_role,
                target_dept=target_dept,
                target_batch=target_batch,
                target_course_code=target_course_code,
            )

        return self._handle_list_students(
            faculty_id,
            active_role,
            target_dept=target_dept,
            target_batch=target_batch,
        )

    def _has_student_access(self, faculty_id, faculty_info, student, active_role):
        """Return whether the active ERP role may read this student."""
        if self._is_vp_role(active_role):
            return True
        if self._is_hod_role(active_role):
            return self._same_department(faculty_info.department, student.department)
        if self._is_ca_role(active_role):
            return self._get_students_by_role_id(
                "ca_id",
                faculty_info,
                faculty_id,
                ["CA", "Advisor", "Class Advisor"],
                strict_ids=self._build_strict_ids(faculty_id, faculty_info),
            ).filter(id=student.id).exists()
        if self._is_mentor_role(active_role):
            return self._get_students_by_role_id(
                "mentor_id",
                faculty_info,
                faculty_id,
                ["Mentor"],
                strict_ids=self._build_strict_ids(faculty_id, faculty_info),
            ).filter(id=student.id).exists()
        if self._is_teacher_role(active_role):
            return AssignSubjectFaculty.objects.filter(
                self._build_faculty_assignment_filter(faculty_id, faculty_info),
                department=student.department,
                batch=student.batch,
                section=student.section,
                is_active=True,
            ).exists()
        if self._is_role_id_11_user(faculty_id, active_role):
            return self._same_department(faculty_info.department, student.department)
        return False

    def _handle_faculty_directory(self, faculty_id, active_role):
        faculty = self._get_faculty_info(faculty_id)
        if not faculty:
            return "Faculty profile not found."

        directory = general_information.objects.select_related("department", "designation", "category")
        if self._is_hod_role(active_role):
            if not faculty.department:
                return "Your HOD account is not mapped to an ERP department."
            directory = directory.filter(department=faculty.department)
        elif not self._is_admin_role(active_role):
            return "Access denied: Faculty directories require HOD or Admin access."

        rows = list(directory.order_by("department__Department", "category__category_name", "designation__designation_name", "name")[:200])
        if not rows:
            return "No faculty records found in your accessible scope."

        role_map = self._hod_faculty_role_map([getattr(member, "faculty_id", None) for member in rows])
        grouped = {}
        for member in rows:
            group = self._hod_staff_group_label(member, role_map)
            grouped.setdefault(group, []).append(member)

        heading = "Faculty Directory"
        if self._is_hod_role(active_role) and getattr(faculty, "department", None):
            heading = f"Department Faculty Directory - {faculty.department.Department}"

        lines = [heading, "", "Summary"]
        lines.append(self._format_pipe_table(
            ["Role/Category", "Staff Count"],
            [[group, len(members)] for group, members in sorted(grouped.items())],
        ))

        for group in sorted(grouped):
            table_rows = []
            for member in grouped[group]:
                department = getattr(member.department, "Department", None) or "N/A"
                designation = getattr(getattr(member, "designation", None), "designation_name", None) or str(getattr(member, "designation", None) or "N/A")
                table_rows.append([
                    member.name or "N/A",
                    member.faculty_id or "N/A",
                    group,
                    designation,
                    department,
                ])
            lines.extend([
                "",
                group,
                self._format_pipe_table(
                    ["Faculty", "Employee ID", "Role/Category", "Designation", "Department"],
                    table_rows,
                ),
            ])
        return "\n".join(lines)

    def _handle_class_directory(self, faculty_id, active_role):
        faculty = self._get_faculty_info(faculty_id)
        if not faculty:
            return "Faculty profile not found."

        classes = self._student_queryset().filter(is_active=True, is_discontinued=False)
        if self._is_hod_role(active_role):
            if not faculty.department:
                return "Your HOD account is not mapped to an ERP department."
            classes = classes.filter(department=faculty.department)
        elif not self._is_admin_role(active_role):
            return "Access denied: Class directories require HOD or Admin access."

        rows = list(
            classes.values(
                "department__Department", "batch", "year", "semester", "section"
            ).annotate(student_count=Count("id")).order_by(
                "department__Department", "batch", "year", "section"
            )[:200]
        )
        if not rows:
            return "No classes found in your accessible scope."

        lines = [
            f"- {row['department__Department'] or 'N/A'} | Batch {row['batch'] or 'N/A'} | "
            f"Year {row['year'] or 'N/A'} | Semester {row['semester'] or 'N/A'} | "
            f"Section {row['section'] or 'N/A'} | Students: {row['student_count']}"
            for row in rows
        ]
        return "Class Directory:\n" + "\n".join(lines)

    def _handle_student_semester_results(self, faculty_id, reg_no, active_role):
        faculty = self._get_faculty_info(faculty_id)
        student = self._student_queryset().filter(reg_no=reg_no).first()
        if not faculty or not student:
            return "Faculty or student record not found."
        if not self._has_student_access(faculty_id, faculty, student, active_role):
            return "Access denied: This student's results are outside your current role scope."

        results = GPA.objects.filter(student=student).order_by("semester", "academic_year", "id")
        rows = list(results.values("semester", "gpa", "cgpa", "academic_year"))
        if not rows:
            return f"No semester results found for {student.name} ({student.reg_no})."

        lines = [f"Semester Results: {student.name} ({student.reg_no})"]
        for row in rows:
            lines.append(
                f"- Semester {row['semester'] or 'N/A'} | GPA: {row['gpa'] if row['gpa'] is not None else 'N/A'} | "
                f"CGPA: {row['cgpa'] if row['cgpa'] is not None else 'N/A'} | "
                f"Academic Year: {row['academic_year'] or 'N/A'}"
            )
        return "\n".join(lines)

    def _handle_my_faculty_profile(self, faculty_id):
        faculty = self._get_faculty_info(faculty_id)
        if not faculty:
            return "Faculty profile not found."

        department = self._department_name(getattr(faculty, "department", None)) or "N/A"
        designation = getattr(getattr(faculty, "designation", None), "designation", None)
        if not designation:
            designation = str(getattr(faculty, "designation", None) or "N/A")

        return "\n".join([
            "My Faculty Profile",
            f"Name: {getattr(faculty, 'name', None) or 'N/A'}",
            f"Employee ID: {getattr(faculty, 'faculty_id', None) or faculty_id}",
            f"Department: {department}",
            f"Designation: {designation}",
            f"College email: {getattr(faculty, 'college_email', None) or 'N/A'}",
        ])

    def _handle_faculty_timetable(self, faculty_id, active_role=None):
        from course_management.models import PeriodAllocation

        faculty = self._get_faculty_info(faculty_id)
        if not faculty:
            return "Faculty profile not found."

        assignments = AssignSubjectFaculty.objects.filter(is_active=True)
        if self._is_hod_role(active_role):
            if not faculty.department:
                return "Your HOD account is not mapped to an ERP department."
            assignments = assignments.filter(
                Q(department=faculty.department) | Q(course__department=faculty.department)
            )
        elif not self._is_admin_role(active_role):
            assignments = assignments.filter(
                Q(faculty=faculty) | Q(skilled_faculty=faculty)
            )
        assignments = assignments.select_related("course", "department")
        latest_year = (
            assignments.exclude(academic_year__isnull=True)
            .exclude(academic_year="")
            .order_by("-academic_year")
            .values_list("academic_year", flat=True)
            .first()
        )
        if latest_year:
            assignments = assignments.filter(academic_year=latest_year)

        assignment_rows = list(assignments)
        course_map = {
            item.course.course_code: item.course
            for item in assignment_rows
            if item.course and item.course.course_code
        }
        if not course_map:
            return "No active subject assignments were found for your timetable."

        allocations = PeriodAllocation.objects.filter(
            department_id__in={item.department_id for item in assignment_rows if item.department_id},
            semester__in={item.course.semester for item in assignment_rows if item.course},
            section__in={item.section for item in assignment_rows if item.section},
        ).select_related("department")

        period_fields = [
            "first_period", "second_period", "third_period", "fourth_period",
            "fifth_period", "sixth_period", "seventh_period", "eighth_period",
            "nineth_period", "tenth_period",
        ]
        day_order = {
            "Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4,
            "Friday": 5, "Saturday": 6, "Sunday": 7,
        }
        entries = []
        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for allocation in allocations:
            for index, field_name in enumerate(period_fields, start=1):
                code = getattr(allocation, field_name, None)
                if code in course_map:
                    course = course_map[code]
                    entries.append((
                        day_order.get(allocation.day, 99),
                        index,
                        f"{allocation.day} - Period {index}: {course.course_code} "
                        f"{course.title or ''} (Year {allocation.year}, Section {allocation.section})",
                        allocation.day,
                        course.course_code,
                        course.title or "",
                        allocation.year,
                        allocation.section,
                    ))

        if not entries:
            return "No timetable periods are currently mapped to your active subjects."
        entries.sort(key=lambda item: (item[0], item[1]))
        if self._is_admin_role(active_role):
            heading = f"**Institution Timetable ({latest_year})**" if latest_year else "**Institution Timetable**"
        elif self._is_hod_role(active_role):
            heading = f"**Department Timetable ({latest_year})**" if latest_year else "**Department Timetable**"
        else:
            heading = f"**My Timetable ({latest_year})**" if latest_year else "**My Timetable**"

        grouped = {}
        for entry in entries:
            day_name = entry[3]
            grouped.setdefault(day_name, []).append(entry)

        lines = [heading, ""]
        for day_name in weekdays:
            day_entries = grouped.get(day_name)
            if not day_entries:
                continue
            lines.append(f"**{day_name}**")
            for entry in day_entries:
                period_num = entry[1]
                code = entry[4]
                title = entry[5]
                label = f"{title}" if title else ""
                lines.append(f"{period_num}. **P{period_num}** — {code}{': ' + label if label else ''}")
            lines.append("")
        return "\n".join(lines).rstrip()

    def _handle_student_attendance_query(self, faculty_id, reg_no, active_role, query=None):
        from student_management.models import Daily_Attendance

        faculty = self._get_faculty_info(faculty_id)
        student = self._student_queryset().filter(reg_no=reg_no).first()
        if not faculty or not student:
            return "Faculty or student record not found."

        if not self._has_student_access(faculty_id, faculty, student, active_role):
            return "Access denied: This student's attendance is outside your current role scope."

        requested_semester = self._extract_requested_semester(query)
        records = Daily_Attendance.objects.filter(student=student).order_by("date")
        if requested_semester:
            records = records.filter(semester__iexact=str(requested_semester))
        if self._is_teacher_role(active_role):
            records = records.filter(Q(faculty=faculty) | Q(marked_by=faculty))

        status_values = list(records.values_list("morning_status", "afternoon_status"))
        semester_text = f"Semester {requested_semester}" if requested_semester else "All recorded semesters"
        if not status_values:
            return f"No accessible attendance records found for {student.name} ({student.reg_no}) in {semester_text}."

        statuses = [status for pair in status_values for status in pair if status]
        present = sum(status in {"Present", "On Duty"} for status in statuses)
        absent = sum(status == "Absent" for status in statuses)
        percentage = round((present / len(statuses)) * 100, 2) if statuses else 0
        return "\n".join([
            f"Attendance Summary: {student.name} ({student.reg_no})",
            f"Scope: {semester_text}",
            "",
            "Metric | Value",
            "--- | ---",
            f"Recorded sessions | {len(statuses)}",
            f"Present/On Duty | {present}",
            f"Absent | {absent}",
            f"Attendance percentage | {percentage}%",
        ])

    def _handle_list_students(
        self,
        faculty_id,
        active_role,
        target_role=None,
        target_dept=None,
        target_batch=None,
        target_course_code=None,
    ):
        """
        Retrieves and lists students based on the ACTIVE role scope.
        Respects the database assignments for CA, Mentor, Subject Teacher, HOD, or VP.
        """
        try:
            faculty_info = self._get_faculty_info(faculty_id)
            if not faculty_info:
                return "Error: Could not find your faculty record."

            if self._is_hod_role(active_role):
                if not faculty_info.department:
                    return "Your HOD account is not mapped to an ERP department."
                if target_dept and not self._same_department(
                    target_dept, faculty_info.department
                ):
                    return "Access denied: HOD access is limited to your mapped department."

            strict_ids = self._build_strict_ids(faculty_id, faculty_info)
            is_role_11_user = self._is_role_id_11_user(faculty_id, active_role)

            # Enforce role-based scope (do not aggregate across roles)
            role_scope = set()
            if self._is_vp_role(active_role):
                role_scope.add('vp')
            elif self._is_hod_role(active_role):
                role_scope.add('hod')
            elif self._is_ca_role(active_role):
                role_scope.add('ca')
            elif self._is_mentor_role(active_role):
                role_scope.add('mentor')
            elif self._is_teacher_role(active_role):
                role_scope.add('subject')
            elif is_role_11_user:
                role_scope.add('dept_view')
            else:

                return "Access denied: Your current role is not permitted to list students."

            # Collect all accessible students based on different responsibilities
            accessible_students = {} # {student_id: (student_obj, [reasons])}
            
            # Helper to add students
            def add_students(queryset, reason):
                for s in queryset:
                    if s.id not in accessible_students:
                        accessible_students[s.id] = {'obj': s, 'reasons': set()}
                    accessible_students[s.id]['reasons'].add(reason)

            # 1. VICE PRINCIPAL (Global Access)
            if 'vp' in role_scope:
                add_students(self._student_queryset().all(), "Vice Principal")

            # 2. HOD (Department Access)
            # Check if user is HOD (strict check)
            if 'hod' in role_scope and faculty_info.department:
                add_students(
                    self._department_student_queryset(faculty_info.department),
                    f"HOD of {faculty_info.department.Department}",
                )

            if 'dept_view' in role_scope and faculty_info.department:
                dept_qs = self._department_student_queryset(faculty_info.department)
                add_students(dept_qs, f"{active_role or 'JA'} Department Access")

            # 3. CLASS ADVISOR (CA)
            # Find students where this faculty is the CA
            # Match strictly by ID strings (robust check)
            if 'ca' in role_scope:
                ca_students = self._get_students_by_role_id(
                    field_name="ca_id",
                    faculty_info=faculty_info,
                    faculty_id=faculty_id,
                    role_names=["CA", "Advisor", "Class Advisor"],
                    strict_ids=strict_ids
                )
                add_students(ca_students, "Class Advisor")

            # 4. MENTOR
            # Find students where this faculty is the Mentor
            if 'mentor' in role_scope:
                mentor_students = self._get_students_by_role_id(
                    field_name="mentor_id",
                    faculty_info=faculty_info,
                    faculty_id=faculty_id,
                    role_names=["Mentor"],
                    strict_ids=strict_ids
                )
                add_students(mentor_students, "Mentor")

            # 5. SUBJECT TEACHER
            # Find students enrolled in subjects assigned to this faculty.
            if 'subject' in role_scope:
                assignments = list(
                    self._subject_assignment_queryset(
                        faculty_id, faculty_info, active_role
                    )
                )
                if target_course_code:
                    assignments = [
                        assignment
                        for assignment in assignments
                        if getattr(getattr(assignment, "course", None), "course_code", "").upper()
                        == target_course_code.upper()
                    ]
                enrollment_scope = Q()
                for assignment in assignments:
                    scope = Q(course_id=assignment.course_id)
                    if assignment.department_id:
                        scope &= (
                            Q(department_id=assignment.department_id)
                            | Q(department_id__isnull=True)
                        )
                    if assignment.batch:
                        scope &= (
                            Q(batch__iexact=assignment.batch)
                            | Q(batch__isnull=True)
                            | Q(batch__exact="")
                        )
                    if assignment.section:
                        scope &= (
                            Q(section__iexact=assignment.section)
                            | Q(section__isnull=True)
                            | Q(section__exact="")
                        )
                    if assignment.academic_year:
                        scope &= (
                            Q(academic_year__iexact=assignment.academic_year)
                            | Q(academic_year__isnull=True)
                            | Q(academic_year__exact="")
                        )
                    enrollment_scope |= scope

                if enrollment_scope:
                    student_ids = CourseEnrollment.objects.filter(
                        enrollment_scope,
                        enroll=True,
                        student__is_active=True,
                        student__is_discontinued=False,
                    ).values_list("student_id", flat=True).distinct()
                    add_students(
                        self._student_queryset().filter(id__in=student_ids),
                        "Subject Teacher",
                    )

            # --- FILTERING ---
            final_list = []
            
            # If no students found at all
            if not accessible_students:
                 return "No students found under your assigned responsibilities for this role."

            # Convert to list of objects
            all_students_objs = [v['obj'] for k, v in accessible_students.items()]
            
            # Apply Request Filters (Department / Batch)
            if target_dept:
                all_students_objs = [s for s in all_students_objs if s.department_id == target_dept.id]
            if target_batch:
                all_students_objs = [s for s in all_students_objs if s.batch == target_batch]

            # Sort by name
            all_students_objs.sort(key=lambda s: s.name)

            if not all_students_objs:
                 return f"No students matched your criteria within your accessible scope."

            # Format Output
            student_lines = []
            for s in all_students_objs[:100]: # Limit to 100
                reasons = accessible_students[s.id]['reasons']
                # Determine relationship label
                rel_label = ""
                if "Vice Principal" in reasons: rel_label = ""
                elif "Class Advisor" in reasons: rel_label = "[My Class]"
                elif "Mentor" in reasons: rel_label = "[Mentee]"
                elif "Subject Teacher" in reasons: rel_label = "[Student]"
                elif "HOD" in reasons: rel_label = "" # Implicit for HOD
                
                student_lines.append(f"- {s.name} ({s.reg_no}) {rel_label}")

            count_str = f"Total: {len(all_students_objs)}"
            if len(all_students_objs) > 100: count_str += " (Showing first 100)"
            
            if self._is_hod_role(active_role):
                header = f"Showing all students from the {faculty_info.department.Department} department"
            else:
                header = "Student List"
            if target_batch: header += f" (Batch {target_batch})"
            
            return f"{header}:\n\n" + "\n".join(student_lines) + f"\n\n{count_str}"

        except Exception as e:
            return f"Error retrieving student list: {str(e)}"

    def _handle_my_students(self, faculty_id, relations=None, target_dept=None, target_batch=None):
        """
        Lists students strictly based on CA and/or Mentor assignments.
        This is used for queries like "my students", "my class", "my mentees".
        """
        try:
            faculty_info = self._get_faculty_info(faculty_id)
            if not faculty_info:
                return "Error: Could not find your faculty record."

            relations = relations or {"ca", "mentor"}
            strict_ids = self._build_strict_ids(faculty_id, faculty_info)

            accessible_students = {}

            def add_students(queryset, reason):
                for s in queryset:
                    if s.id not in accessible_students:
                        accessible_students[s.id] = {'obj': s, 'reasons': set()}
                    accessible_students[s.id]['reasons'].add(reason)

            if "ca" in relations:
                ca_students = self._get_students_by_role_id(
                    field_name="ca_id",
                    faculty_info=faculty_info,
                    faculty_id=faculty_id,
                    role_names=["CA", "Advisor", "Class Advisor"],
                    strict_ids=strict_ids
                )
                add_students(ca_students, "Class Advisor")

            if "mentor" in relations:
                mentor_students = self._get_students_by_role_id(
                    field_name="mentor_id",
                    faculty_info=faculty_info,
                    faculty_id=faculty_id,
                    role_names=["Mentor"],
                    strict_ids=strict_ids
                )
                add_students(mentor_students, "Mentor")

            if not accessible_students:
                subject_assignments = AssignSubjectFaculty.objects.filter(faculty=faculty_info, is_active=1)
                if subject_assignments.exists():
                    if relations == {"mentor"}:
                        return "No students found under your Mentor role ID. If you want students from your subject handling, ask: 'list subject students'."
                    if relations == {"ca"}:
                        return "No students found under your CA role ID. If you want students from your subject handling, ask: 'list subject students'."
                    return "No students found under your CA/Mentor assignments. If you want students from your subject handling, ask: 'list subject students'."
                if relations == {"mentor"}:
                    return "No students found under your Mentor role ID."
                if relations == {"ca"}:
                    return "No students found under your CA role ID."
                return "No students found under your CA/Mentor assignments."

            all_students_objs = [v['obj'] for k, v in accessible_students.items()]
            if target_dept:
                all_students_objs = [s for s in all_students_objs if s.department_id == target_dept.id]
            if target_batch:
                all_students_objs = [s for s in all_students_objs if s.batch == target_batch]

            all_students_objs.sort(key=lambda s: s.name)

            if not all_students_objs:
                return "No students matched your criteria within your CA/Mentor scope."

            student_lines = []
            for s in all_students_objs[:100]:
                reasons = accessible_students[s.id]['reasons']
                rel_label = ""
                if "Class Advisor" in reasons and "Mentor" in reasons:
                    rel_label = "[My Class, Mentee]"
                elif "Class Advisor" in reasons:
                    rel_label = "[My Class]"
                elif "Mentor" in reasons:
                    rel_label = "[Mentee]"

                student_lines.append(f"- {s.name} ({s.reg_no}) {rel_label}")

            count_str = f"Total: {len(all_students_objs)}"
            if len(all_students_objs) > 100:
                count_str += " (Showing first 100)"

            if relations == {"mentor"}:
                header = "My Mentees"
            elif relations == {"ca"}:
                header = "My Students (CA)"
            else:
                header = "My Students"
            if target_batch:
                header += f" (Batch {target_batch})"

            return f"{header}:\n\n" + "\n".join(student_lines) + f"\n\n{count_str}"

        except Exception as e:
            return f"Error retrieving my students: {str(e)}"

    def _handle_subjects_handled(self, faculty_id, active_role, query=None):
        """
        Lists the subjects a faculty member is currently handling, based strictly on DB assignments.
        """
        try:
            faculty_info = self._get_faculty_info(faculty_id)
            if not faculty_info:
                return "Error: Could not find your faculty record."

            if not any([
                self._is_vp_role(active_role),
                self._is_hod_role(active_role),
                self._is_ca_role(active_role),
                self._is_mentor_role(active_role),
                self._is_teacher_role(active_role),
            ]):
                return "Access denied: Your current role is not permitted to view subject handling."

            normalized_query = self._normalize_role_name(query)
            department_scope_phrases = {
                "department subjects",
                "department courses",
                "subjects in my department",
                "courses in my department",
                "all department subjects",
                "all subjects in the department",
            }
            institution_scope_phrases = {
                "institution subjects",
                "institution courses",
                "all institution subjects",
            }
            wants_department_scope = any(
                phrase in normalized_query for phrase in department_scope_phrases
            )
            wants_institution_scope = any(
                phrase in normalized_query for phrase in institution_scope_phrases
            )

            # Personal wording such as "my subjects" or "what do I teach"
            # always means the authenticated faculty's own assignment rows.
            # This remains true for multi-role employees whose effective role
            # is HOD. Broad scope requires an explicit department/institution
            # phrase and the corresponding privileged role.
            personal_scope = not (
                (self._is_hod_role(active_role) and wants_department_scope)
                or (self._is_admin_role(active_role) and (
                    wants_department_scope or wants_institution_scope
                ))
            )
            assignment_role = "Faculty" if personal_scope else active_role
            assignments = self._subject_assignment_queryset(
                faculty_id, faculty_info, assignment_role
            )

            if not assignments.exists():
                if personal_scope:
                    return (
                        "No subject assignments were found for your account. "
                        "Please contact the department administrator."
                    )
                return "No active subject assignments found for your profile."

            seen = set()
            lines = []
            ordered = assignments.order_by(
                'department__Department', 'batch', 'section', 'course__course_code', 'course__title'
            )
            for a in ordered:
                course_title = a.course.title if a.course else "Unknown Course"
                course_code = a.course.course_code if a.course and a.course.course_code else ""
                dept_name = None
                if a.department and a.department.Department:
                    dept_name = a.department.Department
                elif a.course and a.course.department and a.course.department.Department:
                    dept_name = a.course.department.Department
                else:
                    dept_name = "N/A"

                batch = a.batch or "N/A"
                section = a.section or "N/A"
                academic_year = a.academic_year or "N/A"
                # Avoid hitting regulation table (column mismatch in DB); show AY instead
                regulation = a.academic_year or "N/A"

                if personal_scope:
                    # A course allocated to several sections is still one
                    # handled subject for this question.
                    key = (a.course_id, course_code, course_title)
                else:
                    key = (course_title, course_code, dept_name, batch, section, academic_year, regulation)
                if key in seen:
                    continue
                seen.add(key)

                subject_label = f"{course_title}"
                if course_code:
                    subject_label += f" ({course_code})"

                if personal_scope:
                    semester_val = getattr(a.course, 'semester', None) or "N/A"
                    lines.append((semester_val, subject_label))
                else:
                    lines.append(
                        f"- {subject_label} | Dept: {dept_name} | Batch: {batch} | Section: {section} | AY: {academic_year} | Reg: {regulation}"
                    )

            header = (
                "You are currently assigned to handle"
                if personal_scope
                else "Subjects You Are Handling"
            )

            if personal_scope:
                from collections import defaultdict
                semester_groups = defaultdict(list)
                for sem, label in lines:
                    semester_groups[sem].append(label)
                semesters_sorted = sorted(
                    semester_groups.keys(),
                    key=lambda s: int(s) if str(s).isdigit() else 99
                )
                output_lines = []
                for sem in semesters_sorted:
                    output_lines.append(f"**Semester {sem}**")
                    for idx, label in enumerate(semester_groups[sem], 1):
                        output_lines.append(f"{idx}. {label}")
                    output_lines.append("")
                count_str = f"Total: {len(lines)}"
                return f"{header}:\n\n" + "\n".join(output_lines).rstrip() + f"\n\n{count_str}"
            else:
                count_str = f"Total: {len(lines)}"
                return f"{header}:\n\n" + "\n".join(lines) + f"\n\n{count_str}"

        except Exception as e:
            return f"Error retrieving subject assignments: {str(e)}"

    def _is_student_information_query(self, query):
        text = self._normalize_role_name(query)
        return bool(re.search(r'\b\d{12}\b', text)) and any(phrase in text for phrase in [
            "give information", "show information", "student information",
            "give details", "show details", "student details",
            "profile of", "student profile", "give profile", "show profile",
        ])

    def _format_faculty_student_profile(self, student):
        department = getattr(getattr(student, "department", None), "Department", None) or "N/A"
        mentor = getattr(getattr(student, "mentor", None), "name", None) or "N/A"
        class_advisor = getattr(getattr(student, "ca", None), "name", None) or "N/A"
        return "\n".join([
            f"Student Profile: {getattr(student, 'name', None) or 'N/A'}",
            f"Registration No: {getattr(student, 'reg_no', None) or 'N/A'}",
            f"Department: {department}",
            f"Batch: {getattr(student, 'batch', None) or 'N/A'}",
            f"Year/Semester: {getattr(student, 'year', None) or 'N/A'} / {getattr(student, 'semester', None) or 'N/A'}",
            f"Section: {getattr(student, 'section', None) or 'N/A'}",
            f"Mentor: {mentor}",
            f"Class Advisor: {class_advisor}",
            f"Email: {getattr(student, 'email', None) or 'N/A'}",
            f"Mobile: {getattr(student, 'mobile_no', None) or 'N/A'}",
        ])

    def _internal_exam_column(self, exam_name):
        normalized = self._normalize_exam_name(exam_name)
        if normalized == "iat1":
            return "Internal 1"
        if normalized == "iat2":
            return "Internal 2"
        return None

    def _format_internal_mark_value(self, obtained, maximum):
        if obtained is None:
            return "Not listed"
        if maximum is None:
            return str(obtained)
        return f"{obtained}/{maximum}"

    def _format_current_internal_marks_response(self, reg_nos, students_by_reg, mark_rows):
        rows_by_student = {}
        for row in mark_rows:
            reg_no = str(row.get("reg_no") or "")
            column = self._internal_exam_column(row.get("exam_name"))
            if not reg_no or not column:
                continue
            course_key = (
                row.get("course_code") or "N/A",
                row.get("course__title") or "Unknown Subject",
            )
            rows_by_student.setdefault(reg_no, {}).setdefault(course_key, {})[column] = self._format_internal_mark_value(
                row.get("total_marks"), row.get("maximum_marks")
            )

        lines = []
        for reg_no in reg_nos:
            student = students_by_reg.get(reg_no)
            if not student:
                lines.extend([f"Current Semester Internal Marks: {reg_no}", "Student not found."])
                continue

            if lines:
                lines.append("")
            lines.extend([
                f"Current Semester Internal Marks: {getattr(student, 'name', None) or 'N/A'} ({reg_no})",
                f"Semester: {getattr(student, 'semester', None) or 'N/A'}",
                "",
            ])
            course_marks = rows_by_student.get(reg_no, {})
            if not course_marks:
                lines.append("No current-semester internal marks are available within your authorized scope.")
                continue

            table_rows = []
            for (course_code, course_title), values in sorted(course_marks.items(), key=lambda item: (item[0][1], item[0][0])):
                table_rows.append([
                    course_title,
                    course_code,
                    values.get("Internal 1", "Not listed"),
                    values.get("Internal 2", "Not listed"),
                ])
            lines.append(self._format_pipe_table(
                ["Subject", "Course Code", "Internal 1", "Internal 2"],
                table_rows,
            ))
        return "\n".join(lines)

    def _handle_current_student_internal_marks_query(self, faculty_id, active_role, query, reg_nos, faculty_info):
        students = list(self._student_queryset().filter(reg_no__in=reg_nos))
        students_by_reg = {str(student.reg_no): student for student in students}
        if not students_by_reg:
            return "No matching students were found for the requested registration number(s)."

        student_scope = Q()
        for student in students:
            semester = str(getattr(student, "semester", None) or "").strip()
            if semester:
                student_scope |= Q(reg_no__iexact=str(student.reg_no), semester=semester)
        if not student_scope:
            return "Current semester is not available for the requested student(s)."

        marks_qs = StudentInternalMark.objects.filter(student_scope)
        available_exam_names = list(
            marks_qs.exclude(exam_name__isnull=True)
            .exclude(exam_name__exact="")
            .values_list("exam_name", flat=True)
            .distinct()
        )
        internal_exam_names = [
            name for name in available_exam_names
            if self._internal_exam_column(name) in {"Internal 1", "Internal 2"}
        ]
        if not internal_exam_names:
            return self._format_current_internal_marks_response(reg_nos, students_by_reg, [])
        marks_qs = marks_qs.filter(exam_name__in=internal_exam_names)

        if self._is_teacher_role(active_role):
            assigned_codes = set()
            assignments_qs = self._subject_assignment_queryset(faculty_id, faculty_info, active_role)
            for student in students:
                student_assignments = assignments_qs.filter(
                    Q(department=student.department) | Q(course__department=student.department)
                )
                if getattr(student, "batch", None):
                    student_assignments = student_assignments.filter(
                        Q(batch__isnull=True) | Q(batch="") | Q(batch=student.batch)
                    )
                if getattr(student, "section", None):
                    student_assignments = student_assignments.filter(
                        Q(section__isnull=True) | Q(section="") | Q(section__iexact=student.section)
                    )
                assigned_codes.update(
                    code for code in student_assignments.values_list("course__course_code", flat=True)
                    if code
                )
            marks_qs = marks_qs.filter(course_code__in=sorted(assigned_codes)) if assigned_codes else StudentInternalMark.objects.none()
        else:
            marks_qs = self._scope_student_internal_marks_queryset(
                marks_qs, faculty_id, faculty_info, active_role
            )

        grouped_rows = list(
            marks_qs.values(
                "reg_no",
                "student__name",
                "semester",
                "course_code",
                "course__title",
                "exam_name",
            ).annotate(
                total_marks=Sum("marks_obtained"),
                maximum_marks=Sum("max_marks"),
            ).order_by("reg_no", "course__title", "course_code", "exam_name")
        )
        return self._format_current_internal_marks_response(reg_nos, students_by_reg, grouped_rows)

    def _handle_student_query(self, faculty_id, student_reg_no, query, active_role):
        try:
            student = self._student_queryset().filter(reg_no__iexact=student_reg_no).first()
            if not student:
                 return f"Student {student_reg_no} not found."
            
            faculty_info = self._get_faculty_info(faculty_id)
            if not faculty_info and self._is_vp_role(active_role):
                class InstitutionAnalysisIdentity:
                    id = None
                    faculty_id = None
                    name = "Administrator"
                    department = None
                faculty_info = InstitutionAnalysisIdentity()
            if not faculty_info:
                return "Authentication Error."

            is_role_11_user = self._is_role_id_11_user(faculty_id, active_role)
            query_lower = query.lower()
            is_performance_request = any(keyword in query_lower for keyword in [
                "performance", "analyze", "analyse", "analysis", "evaluate",
            ])
            subject_faculty_course_ids = None

            # Intelligent RBAC: Check access strictly based on active_role and official assignments
            is_authorized = False
            auth_reason = ""
            
            if self._is_vp_role(active_role):
                is_authorized = True
            
            elif self._is_hod_role(active_role):
                is_authorized = self._same_department(
                    student.department, faculty_info.department
                )
                if not is_authorized:
                    auth_reason = "Access denied: HOD access is limited to the mapped department."
            elif is_role_11_user:
                if self._same_department(student.department, faculty_info.department):
                    is_authorized = True
                else:
                    auth_reason = "Access Denied: You can view only students from your department."
            elif self._is_ca_role(active_role):
                ca_id_str = str(student.ca_id).strip() if student.ca_id else ""
                _, ca_candidate_ids = self._get_candidate_ids(
                    faculty_id, faculty_info, ["CA", "Advisor", "Class Advisor"]
                )
                is_authorized = (ca_id_str in ca_candidate_ids)
            
            elif self._is_mentor_role(active_role):
                mentor_id_str = str(student.mentor_id).strip() if student.mentor_id else ""
                _, mentor_candidate_ids = self._get_candidate_ids(
                    faculty_id, faculty_info, ["Mentor"]
                )
                is_authorized = (mentor_id_str in mentor_candidate_ids)
            
            elif self._is_teacher_role(active_role):
                if is_performance_request:
                    assigned_courses_qs = self._subject_assignment_queryset(
                        faculty_id, faculty_info, active_role
                    ).filter(
                        Q(department=student.department)
                        | Q(course__department=student.department)
                    )
                    if student.batch:
                        assigned_courses_qs = assigned_courses_qs.filter(
                            Q(batch__isnull=True)
                            | Q(batch="")
                            | Q(batch=student.batch)
                        )
                    if student.section:
                        assigned_courses_qs = assigned_courses_qs.filter(
                            Q(section__isnull=True)
                            | Q(section="")
                            | Q(section__iexact=student.section)
                        )
                    assigned_course_ids = list(
                        assigned_courses_qs.values_list("course_id", flat=True).distinct()
                    )
                    subject_faculty_course_ids = list(
                        CourseEnrollment.objects.filter(
                            student=student,
                            enroll=True,
                            course_id__in=assigned_course_ids,
                        ).values_list("course_id", flat=True).distinct()
                    )
                    is_authorized = bool(subject_faculty_course_ids)
                    if not is_authorized:
                        auth_reason = (
                            "Access denied: Subject Faculty can analyze only students "
                            "actively enrolled in subjects assigned to them."
                        )
                else:
                    # Preserve legacy auto-detection for non-analysis profile queries.
                    ca_id_str = str(student.ca_id).strip() if student.ca_id else ""
                    _, ca_candidate_ids = self._get_candidate_ids(
                        faculty_id, faculty_info, ["CA", "Advisor", "Class Advisor"]
                    )
                    is_ca_for_student = (ca_id_str in ca_candidate_ids)
                    if is_ca_for_student:
                        is_authorized = True
                        active_role = 'CA'
                        auth_reason = "Auto-elevated to Class Advisor access (you are CA for this student)"
                    else:
                        mentor_id_str = str(student.mentor_id).strip() if student.mentor_id else ""
                        _, mentor_candidate_ids = self._get_candidate_ids(
                            faculty_id, faculty_info, ["Mentor"]
                        )
                        is_mentor_for_student = (mentor_id_str in mentor_candidate_ids)
                        if is_mentor_for_student:
                            is_authorized = True
                            active_role = 'Mentor'
                            auth_reason = "Auto-elevated to Mentor access (you are Mentor for this student)"
                        else:
                            assignments = AssignSubjectFaculty.objects.filter(
                                faculty=faculty_info,
                                department=student.department,
                                batch=student.batch,
                                section=student.section
                            )
                            if assignments.exists():
                                is_authorized = True
                            else:
                                auth_reason = f"Access Denied: You are not assigned to {student.department.Department} - Section {student.section}."
            
            if not is_authorized:
                return auth_reason or "I'm unable to provide that information under your current role selection."

            if self._is_student_information_query(query):
                return self._format_faculty_student_profile(student)

            # ===== MARKS FILTERING BASED ON ROLE AND SCOPE =====
            # Retrieve all marks for this student
            marks = AssessmentMark.objects.filter(student_id=student.id)
            
            # ROLE-BASED FILTERING:
            # - Vice Principal, CA, Advisor, Mentor: FULL ACCESS to all marks (no filtering)
            # - HOD: Filtered to their department's subjects only
            # - Teacher/Faculty: Filtered to their explicitly assigned subjects only
            
            current_scope = "All Subjects"  # Default for unrestricted roles
            
            no_marks_notice = None

            if is_role_11_user:
                marks = AssessmentMark.objects.none()
                current_scope = "Student Details Only"
                no_marks_notice = "\nYou can view student details only. Academic marks and performance analysis are not available for your role."

            elif (
                self._is_vp_role(active_role)
                or self._is_ca_role(active_role)
                or self._is_mentor_role(active_role)
            ):
                # UNRESTRICTED ACCESS: Class Advisors, Mentors, and VPs see ALL marks
                # No filtering applied - they have complete visibility into student performance
                current_scope = "All Subjects (Full Access)"
                
            elif self._is_hod_role(active_role):
                # The student is already protected by the department access check.
                # HODs may see every subject mark recorded for their students,
                # including common/institution subjects owned by another department.
                current_scope = f"All Subjects ({faculty_info.department.Department})"
                
                # Verify if any marks exist in their scope
                if not marks.exists():
                    no_marks_notice = f"\nNo assessment marks found for {current_scope}. (Access restricted to your department subjects only)."
                    
            elif self._is_teacher_role(active_role):
                # TEACHER: Strictly restricted to their assigned subjects
                if subject_faculty_course_ids is not None:
                    assigned_course_ids = subject_faculty_course_ids
                    assigned_courses_qs = self._subject_assignment_queryset(
                        faculty_id, faculty_info, active_role
                    ).filter(course_id__in=assigned_course_ids)
                else:
                    assigned_courses_qs = self._subject_assignment_queryset(
                        faculty_id, faculty_info, active_role
                    ).filter(
                        department=student.department,
                        batch=student.batch,
                        section=student.section,
                    )
                    assigned_course_ids = list(
                        assigned_courses_qs.values_list("course_id", flat=True)
                    )

                if assigned_course_ids:
                    # Explicit assignment exists - filter to assigned courses
                    course_names = ", ".join(list(assigned_courses_qs.values_list('course__title', flat=True)))
                    marks = marks.filter(assessment__course__id__in=assigned_course_ids)
                    current_scope = f"Assigned Subjects ({course_names})"
                else:
                    marks = marks.none()
                    current_scope = "Assigned Subjects"
                
                # Verify if any marks exist in their scope
                if not marks.exists():
                    no_marks_notice = f"\nNo assessment marks found for your {current_scope} scope. (Access restricted to your assigned subjects only)."

            mark_rows = list(
                marks.values(
                    'assessment__Assessmentname',
                    'assessment__course__title',
                    'marks_raw',
                ).order_by('assessment__course__title', 'assessment__Assessmentname', 'id')
            )

            # Generate marks string for display
            marks_str = ", ".join(
                [
                    f"{(row['assessment__Assessmentname'] or 'Assessment')}: {row['marks_raw']}"
                    for row in mark_rows
                ]
            ) if mark_rows else "No assessment marks available"
            
            # ===== DETERMINE RESPONSE TYPE =====
            # Check if user is asking for detailed performance analysis or just basic info
            analysis_keywords = [
                'performance', 'analyze', 'analysis', 'report', 'evaluate', 'assessment',
                'recommend', 'recommendation', 'suggest', 'suggestion', 'advice',
                'improve', 'improvement', 'guidance', 'plan', 'action plan'
            ]
            wants_analysis = any(keyword in query_lower for keyword in analysis_keywords)
            if is_role_11_user:
                wants_analysis = False

            def bold_label(label, value):
                # Bold the label, keep the value normal for readability
                return f"**{label}**: {value}"
            
            # Default to a clear profile view for any role unless analysis is explicitly requested
            if not wants_analysis:
                dept_name = student.department.Department if student.department else "N/A"
                mentor_name = getattr(getattr(student, "mentor", None), "name", None) or "N/A"
                class_advisor_name = getattr(getattr(student, "ca", None), "name", None) or "N/A"

                profile_info = [
                    f"Student Profile: {student.name}",
                    bold_label("Registration No", student.reg_no),
                    bold_label("Department", dept_name),
                    bold_label("Batch", student.batch or "N/A"),
                    bold_label("Year/Semester", f"{student.year or 'N/A'} / {student.semester or 'N/A'}"),
                    bold_label("Section", student.section or "N/A"),
                    bold_label("Mentor", mentor_name),
                    bold_label("Class Advisor", class_advisor_name),
                    bold_label("Email", student.email or "N/A"),
                    bold_label("Mobile", student.mobile_no or "N/A"),
                ]

                # Add marks summary (already filtered to the viewer's scope above)
                # Add marks summary
                if is_role_11_user:
                    profile_info.append(
                        "\nYou can view student details only. Performance analysis and academic marks are not available for your role."
                    )
                elif mark_rows:
                    profile_info.append(f"\nAcademic Marks ({current_scope}):")

                    marks_by_subject = {}
                    for row in mark_rows:
                        subject = row['assessment__course__title'] or "Unknown Subject"
                        marks_by_subject.setdefault(subject, []).append(
                            f"{(row['assessment__Assessmentname'] or 'Assessment')}: {row['marks_raw']}"
                        )

                    for subject, subject_marks in sorted(marks_by_subject.items()):
                        profile_info.append(f"\n**{subject}**:")
                        for mark in subject_marks:
                            profile_info.append(f"  - {mark}")

                return "\n".join(profile_info)


            # ===== ROLE-SCOPED PERFORMANCE ANALYSIS =====
            requested_semester = self._extract_student_subject_semester(query)
            permitted_codes = None
            include_gpa = subject_faculty_course_ids is None
            if subject_faculty_course_ids is not None:
                permitted_codes = list(
                    Course.objects.filter(
                        id__in=subject_faculty_course_ids
                    ).values_list("course_code", flat=True)
                )

            if requested_semester is not None:
                snapshot = self._student_semester_performance_snapshot(
                    student, requested_semester
                )
                snapshot = self._filter_faculty_performance_snapshot(
                    snapshot,
                    permitted_codes=permitted_codes,
                    include_gpa=include_gpa,
                )
                if not self._faculty_snapshot_has_data(snapshot):
                    return (
                        f"No recorded academic data exists for Semester {requested_semester} "
                        f"within your authorized scope for student {student.reg_no}."
                    )
                semester_cgpa = (
                    (snapshot["gpa"] or {}).get("cgpa")
                    if include_gpa else "N/A (outside Subject Faculty scope)"
                )
                ai_report = self._faculty_ai_student_performance_report(
                    "semester", student, [snapshot]
                )
                if ai_report:
                    return ai_report
                ai_recommendations = self._faculty_ai_recommendations(
                    "semester", student, [snapshot]
                )
                return self._format_student_performance_analysis(
                    current_scope=current_scope,
                    student=student,
                    semester=requested_semester,
                    latest_cgpa=semester_cgpa,
                    performance_rows=snapshot["marks"],
                    attendance_rows=snapshot["attendance"],
                    activity_counts=None,
                    result_rows=snapshot["results"],
                    recommendation_override=ai_recommendations,
                )

            semesters = self._student_recorded_semesters(student)
            snapshots = []
            for semester in semesters:
                snapshot = self._student_semester_performance_snapshot(student, semester)
                snapshot = self._filter_faculty_performance_snapshot(
                    snapshot,
                    permitted_codes=permitted_codes,
                    include_gpa=include_gpa,
                )
                if self._faculty_snapshot_has_data(snapshot):
                    snapshots.append(snapshot)
            if not snapshots:
                return (
                    "No recorded academic data is available for an overall performance "
                    f"analysis within your authorized scope for student {student.reg_no}."
                )

            if subject_faculty_course_ids is not None:
                activity_counts = {
                    "achievements": "N/A (outside Subject Faculty scope)",
                    "co_curricular": "N/A (outside Subject Faculty scope)",
                    "publications": "N/A (outside Subject Faculty scope)",
                    "projects": "N/A (outside Subject Faculty scope)",
                }
            else:
                activity_counts = {
                    "achievements": str(
                        StudentAchievements.objects.filter(student=student).count()
                    ),
                    "co_curricular": str(
                        StudentCO_EX_Curricular.objects.filter(student=student).count()
                    ),
                    "publications": str(
                        StudentPublication.objects.filter(student=student).count()
                    ),
                    "projects": str(
                        StudentProjects.objects.filter(student=student).count()
                    ),
                }
            ai_report = self._faculty_ai_student_performance_report(
                "overall", student, snapshots, activity_counts=activity_counts
            )
            if ai_report:
                return ai_report
            ai_recommendations = self._faculty_ai_recommendations(
                "overall", student, snapshots
            )
            return self._format_overall_student_performance_analysis(
                current_scope=current_scope,
                student=student,
                snapshots=snapshots,
                activity_counts=activity_counts,
                recommendation_override=ai_recommendations,
            )
        except Exception as e:
            return f"Error: {str(e)}"

    def _handle_view_subject_reports(self, faculty_id, query, active_role=None):
        if not (
            self._is_ca_role(active_role)
            or self._is_hod_role(active_role)
            or self._is_vp_role(active_role)
        ):
            return "Access Denied."
        
        # Simplified report viewing logic
        try:
            reports = Notification.objects.filter(receiver__faculty_id=faculty_id, message__startswith="REPORT|")
            if self._is_vp_role(active_role):
                reports = Notification.objects.filter(message__startswith="REPORT|")
            elif self._is_hod_role(active_role):
                faculty = self._get_faculty_info(faculty_id)
                if not faculty or not faculty.department:
                    return "Your HOD account is not mapped to an ERP department."
                reports = Notification.objects.filter(
                    sender__department=faculty.department,
                    message__startswith="REPORT|",
                )

            if not reports.exists():
                return "No reports found."

            resp = "Subject Reports:\n\n"
            for report in reports.select_related("sender")[:10]:
                parts = report.message.split("|")
                body = parts[2] if len(parts) > 2 else report.message
                resp += f"• From {report.sender.name}: {body}\n"
            return resp
        except Exception:
            return "No chatbot reports are available in this deployment."

    def _handle_marks_chart(self, faculty_id, student_identifiers, query, active_role):
        return {"text": "Comparison chart", "type": "chart", "data": {"Sample": 80}}

    def _build_strict_ids(self, faculty_id, faculty_info):
        """
        Prefer exact matches using faculty_id, primary key, and legacy faculty_id field.
        """
        ids = set()
        if faculty_id:
            ids.add(str(faculty_id).strip())
        if faculty_info:
            if faculty_info.id is not None:
                ids.add(str(faculty_info.id).strip())
            if getattr(faculty_info, "faculty_id", None):
                ids.add(str(faculty_info.faculty_id).strip())
        return ids

    def _get_role_ids(self, faculty_id, role_names):
        role_ids = set()
        try:
            base_qs = self._approval_user_queryset().filter(
                Employee_id=faculty_id,
                is_active=1
            )
            if role_names:
                qs = base_qs.select_related('role').filter(role__role__in=role_names)
                for u in qs:
                    if u.id is not None:
                        role_ids.add(str(u.id))
        except Exception:
            pass
        return role_ids

    def _get_candidate_ids(self, faculty_id, faculty_info, role_names):
        role_ids = self._get_role_ids(faculty_id, role_names)
        candidate_ids = set(role_ids)
        if faculty_info:
            if faculty_info.id is not None:
                candidate_ids.add(str(faculty_info.id))
            if faculty_info.faculty_id:
                candidate_ids.add(str(faculty_info.faculty_id))
        if faculty_id:
            candidate_ids.add(str(faculty_id))
        return role_ids, candidate_ids

    def _get_students_by_role_id(self, field_name, faculty_info, faculty_id, role_names, strict_ids=None):
        """
        Fetch students by CA/Mentor (or other role) id with strict preference:
        1) Exact matches to strict_ids (faculty_id, pk, legacy faculty_id)
        2) Approval-system role ids (cross-db mappings)
        3) Fallback to any available ids from faculty_info/faculty_id
        """
        strict_ids = strict_ids or set()

        if strict_ids:
            qs = self._student_queryset().filter(**{f"{field_name}__in": list(strict_ids)})
            if qs.exists():
                return qs

        role_ids = self._get_role_ids(faculty_id, role_names)
        if role_ids:
            qs = self._student_queryset().filter(**{f"{field_name}__in": list(role_ids)})
            if qs.exists():
                return qs

        fallback_ids = set()
        if faculty_info:
            if faculty_info.id is not None:
                fallback_ids.add(str(faculty_info.id))
            if faculty_info.faculty_id:
                fallback_ids.add(str(faculty_info.faculty_id))
        if not fallback_ids and faculty_id:
            fallback_ids.add(str(faculty_id))

        if fallback_ids:
            return self._student_queryset().filter(**{f"{field_name}__in": list(fallback_ids)})

        return self._student_queryset().none()

    def _extract_department(self, query):
        clean_query = re.sub(r'[^a-zA-Z0-9\s]', ' ', query.lower())
        for d in Add_Department.objects.only("id", "Department", "Department_code"):
            dept_name = (d.Department or "").lower()
            dept_code = (d.Department_code or "").lower()
            if dept_name and dept_name in clean_query:
                return d
            # One-character legacy department codes (for example "A")
            # collide with section labels such as "section A" and must not
            # be interpreted as an explicitly requested department.
            if len(dept_code) >= 2 and f" {dept_code} " in f" {clean_query} ":
                return d
        return None

    def _extract_course_code(self, query):
        match = re.search(r'\b([A-Za-z]{2,}\d{3,}[A-Za-z]*)\b', query or "", re.IGNORECASE)
        return match.group(1).upper() if match else None

    def _extract_section(self, query):
        match = re.search(r'\b(?:section|sec)\s*[-:]?\s*([a-z0-9]+)\b', query or "", re.IGNORECASE)
        return match.group(1).upper() if match else None

    def _extract_batch(self, query):
        """Extract an explicit batch or the shorthand after a subject code."""
        text = query or ""
        patterns = [
            r'\b(20\d{2}\s*[-\u2013]\s*20\d{2})\b',
            r'\bbatch\s*[-:]?\s*(20\d{2}\s*[-\u2013]\s*20\d{2})\b',
            r'\b[A-Za-z]{2,}\d{3,}[A-Za-z]*\s+(20\d{2}\s*[-\u2013]\s*20\d{2})\b',
            r'\bbatch\s*[-:]?\s*(20\d{2})(?!\s*[-\u2013])\b',
            r'\b[A-Za-z]{2,}\d{3,}[A-Za-z]*\s+(20\d{2})(?!\s*[-\u2013])\b',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return re.sub(r'\s+', '', match.group(1)).replace('\u2013', '-')
        return None

    def _is_valid_batch_value(self, batch):
        if re.fullmatch(r'20\d{2}', batch or ""):
            return True
        match = re.fullmatch(r'(20\d{2})-(20\d{2})', batch or "")
        return bool(match and int(match.group(2)) - int(match.group(1)) == 4)

    def _batch_matches(self, stored_batch, requested_batch):
        stored = str(stored_batch or "").strip().replace('\u2013', '-')
        requested = str(requested_batch or "").strip().replace('\u2013', '-')
        if stored == requested:
            return True
        stored_start = re.match(r'^20\d{2}', stored)
        requested_start = re.match(r'^20\d{2}', requested)
        return bool(
            stored_start and requested_start
            and stored_start.group(0) == requested_start.group(0)
        )

    def _display_batch(self, batch):
        value = str(batch or "").strip().replace('\u2013', '-')
        if re.fullmatch(r'20\d{2}', value):
            start = int(value)
            return f"{start}\u2013{start + 4}"
        return value.replace('-', '\u2013') or "N/A"

    def _class_report_batch_guidance(self, course_code, assignments, invalid=False):
        batches = sorted({
            self._display_batch(getattr(assignment, "batch", None))
            for assignment in assignments
            if getattr(assignment, "batch", None)
        })
        if invalid:
            opening = f"The batch number is invalid or is not assigned to you for {course_code}."
        elif len(batches) > 1:
            opening = (
                "I found multiple batches assigned to this subject. "
                "Please specify the batch number to generate the correct class report."
            )
        else:
            opening = "Please specify the batch number to generate the correct class report."
        lines = [opening]
        if batches:
            lines.append(f"Assigned batches for {course_code}: {', '.join(batches)}")
        lines.extend([
            "Correct format:",
            "Class report for <Subject Code> <Batch Number>",
            "Example:",
            f"Class report for {course_code} {batches[0] if batches else '2023\u20132027'}",
        ])
        return "\n".join(lines)

    def _extract_requested_semester(self, query):
        text = (query or "").lower()
        patterns = [
            r'\bsemester\s*[-:]?\s*([1-8])\b',
            r'\b([1-8])(?:st|nd|rd|th)\s+semester\b',
            r'\bsem\s*[-:]?\s*([1-8])\b',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None

    def _is_student_end_semester_query(self, query):
        text = (query or "").lower()
        if not re.search(r'\b\d{12}\b', text):
            return False
        end_semester_terms = [
            "end semester", "end-semester", "semester mark", "semester marks",
            "semester result", "semester results", "final semester",
            "final mark", "final marks", "ese mark", "ese marks",
            "ese result", "ese results",
        ]
        return any(term in text for term in end_semester_terms)

    def _handle_student_end_semester_results(
        self, faculty_id, active_role, query, all_roles=None
    ):
        reg_match = re.search(r'\b\d{12}\b', query or "")
        if not reg_match:
            return "Please provide a valid 12-digit student registration number."

        reg_no = reg_match.group(0)
        student = self._student_queryset().filter(reg_no=reg_no).first()
        if not student:
            return f"No student was found with registration number {reg_no}."

        canonical_roles = {
            self._canonical_role(role)
            for role in (all_roles or [active_role])
            if str(role or "").strip()
        }
        canonical_roles.add(self._canonical_role(active_role))

        is_institution_admin = bool(
            canonical_roles.intersection({"Admin", "Vice Principal"})
        )
        faculty_info = None if is_institution_admin else self._get_faculty_info(faculty_id)
        if not is_institution_admin and not faculty_info:
            return "Authentication Error: Unable to retrieve your faculty profile."

        complete_access = is_institution_admin
        if not complete_access and "HOD" in canonical_roles:
            complete_access = self._same_department(
                getattr(faculty_info, "department", None), student.department
            )
        if not complete_access and "Class Advisor" in canonical_roles:
            complete_access = self._has_student_access(
                faculty_id, faculty_info, student, "Class Advisor"
            )
        if not complete_access and "Mentor" in canonical_roles:
            complete_access = self._has_student_access(
                faculty_id, faculty_info, student, "Mentor"
            )

        requested_semester = self._extract_requested_semester(query)
        access_label = "Complete authorized result"
        assigned_course_ids = None
        if not complete_access:
            if "Faculty" not in canonical_roles:
                return (
                    "Access denied: This student's end-semester results are "
                    "outside your assigned role scope."
                )

            assignments = self._subject_assignment_queryset(
                faculty_id, faculty_info, "Faculty"
            ).filter(
                Q(department=student.department)
                | Q(course__department=student.department)
            )
            if student.batch:
                assignments = assignments.filter(
                    Q(batch__isnull=True) | Q(batch="") | Q(batch=student.batch)
                )
            if student.section:
                assignments = assignments.filter(
                    Q(section__isnull=True) | Q(section="") | Q(section__iexact=student.section)
                )

            assigned_course_ids = assignments.values_list("course_id", flat=True).distinct()
            requested_course_code = self._extract_course_code(query)
            if requested_course_code:
                assignments = assignments.filter(
                    course__course_code__iexact=requested_course_code
                )
                assigned_course_ids = assignments.values_list(
                    "course_id", flat=True
                ).distinct()
            access_label = "Subject Faculty allocation only"

        results = Result.objects.filter(student=student).select_related("course")
        if requested_semester:
            results = results.filter(semester=requested_semester)
        if assigned_course_ids is not None:
            results = results.filter(course_id__in=assigned_course_ids)

        rows = list(results.values(
            "course_id",
            "course__course_code",
            "course__title",
            "semester",
            "academic_year",
            "grade",
            "credit",
            "grade_total",
        ).order_by("semester", "course__course_code", "course__title"))

        if not rows:
            if complete_access:
                semester_text = f" for semester {requested_semester}" if requested_semester else ""
                return (
                    f"No published end-semester results{semester_text} were found "
                    f"for {student.name} ({student.reg_no})."
                )
            return (
                "No published end-semester results were found for this student "
                "within your assigned subject allocation."
            )

        course_codes = {
            row["course__course_code"] for row in rows if row["course__course_code"]
        }
        mark_rows = StudentInternalMark.objects.filter(
            student=student,
            course_code__in=course_codes,
        ).exclude(exam_name__isnull=True).exclude(exam_name__exact="")
        semester_exam_names = [
            name
            for name in mark_rows.values_list("exam_name", flat=True).distinct()
            if self._normalize_exam_name(name) == "semesterexam"
        ]
        numeric_marks = {}
        if semester_exam_names:
            numeric_marks = {
                (row["course_code"], row["semester"]): (row["marks"], row["maximum"])
                for row in mark_rows.filter(exam_name__in=semester_exam_names)
                .values("course_code", "semester")
                .annotate(marks=Sum("marks_obtained"), maximum=Sum("max_marks"))
            }

        lines = [
            f"End Semester Results: {student.name} ({student.reg_no})",
            f"Scope: {access_label}",
        ]
        current_semester = None
        for row in rows:
            semester = row["semester"] or "N/A"
            if semester != current_semester:
                lines.append(f"\nSemester {semester}")
                current_semester = semester
            code = row["course__course_code"] or "N/A"
            title = row["course__title"] or "Untitled Subject"
            mark, maximum = numeric_marks.get((code, str(semester)), (None, None))
            mark_text = (
                f"{mark}/{maximum}" if mark is not None and maximum is not None else "N/A"
            )
            lines.append(
                f"- {code} - {title} | Mark: {mark_text} | "
                f"Grade: {row['grade'] or 'N/A'} | Credit: {row['credit'] or 'N/A'} | "
                f"Grade Total: {row['grade_total'] if row['grade_total'] is not None else 'N/A'} | "
                f"Academic Year: {row['academic_year'] or 'N/A'}"
            )
        return "\n".join(lines)

    def _get_class_report_assessments(self, course_code, assignments):
        """Return assessment names only from the selected faculty assignments."""
        assignment_scope = Q()
        for assignment in assignments:
            department = assignment.department or (
                assignment.course.department if assignment.course else None
            )
            scope = Q()
            if department:
                scope &= Q(student__department_id=department.id)
            if assignment.batch:
                batch_value = str(assignment.batch).strip()
                batch_candidates = {batch_value}
                batch_start = re.match(r'^20\d{2}', batch_value)
                if batch_start:
                    batch_candidates.add(batch_start.group(0))
                scope &= Q(batch__in=batch_candidates)
            if assignment.section:
                scope &= Q(section__iexact=str(assignment.section).strip())
            assignment_scope |= scope

        marks = StudentInternalMark.objects.filter(
            course_code__iexact=course_code
        ).exclude(exam_name__isnull=True).exclude(exam_name__exact="")
        if assignment_scope:
            marks = marks.filter(assignment_scope)
        else:
            return []
        return list(marks.values_list("exam_name", flat=True).distinct())

    def _display_assessment_name(self, exam_name):
        normalized = self._normalize_exam_name(exam_name)
        iat_match = re.fullmatch(r'iat(\d+)', normalized)
        if iat_match:
            return f"IAT {iat_match.group(1)}"
        if normalized == "modelexam":
            return "Model Exam"
        if normalized == "semesterexam":
            return "Semester Exam"
        return str(exam_name or "").strip()

    def _resolve_class_report_assessment(self, query, available_exam_names):
        """Return (stored exam name, assessment_was_explicitly_supplied)."""
        requested = self._extract_internal_assessment_name(query)
        query_lower = (query or "").lower()
        if not requested and re.search(r'\bmodel\s+(?:exam|examination)\b', query_lower):
            requested = "Model Exam"
        if not requested and re.search(r'\bsemester\s+(?:exam|examination)\b', query_lower):
            requested = "Semester Exam"

        if requested:
            requested_normalized = self._normalize_exam_name(requested)
            for name in available_exam_names:
                if self._normalize_exam_name(name) == requested_normalized:
                    return name, True
            return None, True

        normalized_query = self._normalize_exam_name(query)
        for name in sorted(
            available_exam_names,
            key=lambda item: len(self._normalize_exam_name(item)),
            reverse=True,
        ):
            normalized_name = self._normalize_exam_name(name)
            if normalized_name and normalized_name in normalized_query:
                return name, True
        return None, False

    def _class_report_request_guidance(
        self, course_code, assignments, available_exam_names, error=None
    ):
        batches = sorted({
            self._display_batch(getattr(assignment, "batch", None))
            for assignment in assignments
            if getattr(assignment, "batch", None)
        })
        assessments = sorted({
            self._display_assessment_name(name)
            for name in available_exam_names if name
        })
        lines = []
        if error:
            lines.append(error)
        lines.append(
            "Please specify both the assessment and the batch number to generate "
            "the correct class report."
        )
        lines.append("")
        lines.append(f"Assigned batch(es) for {course_code}:")
        lines.extend(f"\u2022 {batch}" for batch in batches)
        if not batches:
            lines.append("\u2022 No assigned batches found")
        lines.append("")
        lines.append("Available assessments:")
        lines.extend(f"\u2022 {assessment}" for assessment in assessments)
        if not assessments:
            lines.append("\u2022 No assessment marks found")
        lines.extend([
            "",
            "Correct format:",
            "Class report for <Subject Code> in <Assessment> <Batch Number>",
            "",
            "Example:",
        ])
        example_batch = batches[0] if batches else "2024\u20132028"
        example_assessments = assessments[:2] or ["IAT 1", "IAT 2"]
        lines.extend(
            f"\u2022 Class report for {course_code} in {assessment} {example_batch}"
            for assessment in example_assessments
        )
        return "\n".join(lines)

    def _extract_internal_assessment_name(self, query):
        clean_query = (query or "").lower()

        if any(term in clean_query for term in [
            "end semester", "end-semester", "semester exam",
            "semester examination", "ese mark", "ese result", "final exam",
        ]):
            return "Semester Exam"

        match = re.search(r'\b(?:internal|iat)\s*[-:]?\s*(\d+)\b', clean_query)
        if match:
            return f"IAT{match.group(1)}"

        roman_map = {"i": "1", "ii": "2", "iii": "3"}
        match = re.search(r'\b(?:internal|iat)\s*[-:]?\s*(i{1,3})\b', clean_query)
        if match:
            roman = match.group(1)
            if roman in roman_map:
                return f"IAT{roman_map[roman]}"

        return None

    def _normalize_exam_name(self, value):
        normalized = re.sub(r'[^a-z0-9]+', '', (value or '').lower())
        normalized = normalized.replace("internalassessment", "iat")
        normalized = normalized.replace("internal", "iat")
        return normalized

    def _is_subject_marks_query(self, query):
        query_lower = (query or "").lower()
        if re.search(r'\b\d{12}\b', query_lower):
            return False
        return any(token in query_lower for token in [
            "mark", "marks", "internal", "iat", "score", "scores", "subject-wise"
        ])

    def _is_class_report_query(self, query):
        query_lower = (query or "").lower()
        return "class report" in query_lower or "subject report" in query_lower

    def _is_student_subject_marks_query(self, query):
        query_lower = (query or "").lower()
        if not re.search(r'\b\d{12}\b', query_lower):
            return False
        if any(token in query_lower for token in ["chart", "graph", "plot", "visualize", "compare"]):
            return False
        return any(token in query_lower for token in ["mark", "marks", "score", "scores"])

    def _subject_assignment_queryset(self, faculty_id, faculty_info, active_role):
        assignments = AssignSubjectFaculty.objects.filter(is_active=1).select_related(
            "course", "department", "course__department"
        )

        if self._is_vp_role(active_role):
            return assignments

        if self._is_hod_role(active_role):
            if not faculty_info.department:
                return assignments.none()

            return assignments.filter(
                Q(department=faculty_info.department)
                | Q(course__department=faculty_info.department)
            )

        if (
            self._is_teacher_role(active_role)
            or self._is_ca_role(active_role)
            or self._is_mentor_role(active_role)
        ):
            return assignments.filter(self._build_faculty_assignment_filter(faculty_id, faculty_info))

        return assignments.none()

    def _class_report_assignment_queryset(self, faculty_id, faculty_info, active_role):
        """Return subject allocations visible to a role for class reporting."""
        assignments = AssignSubjectFaculty.objects.filter(is_active=1).select_related(
            "course", "department", "course__department", "faculty", "skilled_faculty"
        )

        if self._is_vp_role(active_role):
            return assignments

        if self._is_hod_role(active_role):
            if not faculty_info or not faculty_info.department:
                return assignments.none()
            return assignments.filter(
                Q(department=faculty_info.department)
                | Q(course__department=faculty_info.department)
            )

        if self._is_ca_role(active_role):
            ca_students = self._get_students_by_role_id(
                field_name="ca_id",
                faculty_info=faculty_info,
                faculty_id=faculty_id,
                role_names=["CA", "Advisor", "Class Advisor"],
                strict_ids=self._build_strict_ids(faculty_id, faculty_info),
            ).filter(is_active=True, is_discontinued=False)
            class_rows = ca_students.values(
                "department_id", "batch", "section"
            ).distinct()
            class_scope = Q()
            for row in class_rows:
                department_scope = (
                    Q(department_id=row["department_id"])
                    | Q(course__department_id=row["department_id"])
                )
                allocation_scope = department_scope
                if row["batch"]:
                    allocation_scope &= Q(batch=row["batch"])
                if row["section"]:
                    allocation_scope &= Q(section__iexact=row["section"])
                class_scope |= allocation_scope
            return assignments.filter(class_scope) if class_scope else assignments.none()

        if self._is_mentor_role(active_role):
            mentor_students = self._get_students_by_role_id(
                field_name="mentor_id",
                faculty_info=faculty_info,
                faculty_id=faculty_id,
                role_names=["Mentor"],
                strict_ids=self._build_strict_ids(faculty_id, faculty_info),
            ).filter(is_active=True, is_discontinued=False)
            mentee_rows = mentor_students.values(
                "department_id", "batch", "section"
            ).distinct()
            mentee_scope = Q()
            for row in mentee_rows:
                department_scope = (
                    Q(department_id=row["department_id"])
                    | Q(course__department_id=row["department_id"])
                )
                allocation_scope = department_scope
                if row["batch"]:
                    allocation_scope &= Q(batch=row["batch"])
                if row["section"]:
                    allocation_scope &= Q(section__iexact=row["section"])
                mentee_scope |= allocation_scope
            return assignments.filter(mentee_scope) if mentee_scope else assignments.none()

        if self._is_teacher_role(active_role):
            return assignments.filter(
                self._build_faculty_assignment_filter(faculty_id, faculty_info)
            )

        return assignments.none()

    def _resolve_subject_assignments(
        self, query, faculty_id, faculty_info, active_role, for_class_report=False
    ):
        if for_class_report:
            assignments_qs = self._class_report_assignment_queryset(
                faculty_id, faculty_info, active_role
            )
        else:
            assignments_qs = self._subject_assignment_queryset(
                faculty_id, faculty_info, active_role
            )
        target_dept = self._extract_department(query)
        if target_dept:
            assignments_qs = assignments_qs.filter(
                Q(department=target_dept) | Q(course__department=target_dept)
            )

        course_code = self._extract_course_code(query)
        if course_code:
            exact_qs = assignments_qs.filter(course__course_code__iexact=course_code)
            if exact_qs.exists():
                return list(exact_qs), target_dept

        assignments = list(assignments_qs)
        if not assignments:
            return [], target_dept

        normalized_query = re.sub(r'[^a-z0-9\s]+', ' ', query.lower())
        matched = []
        for assignment in assignments:
            course = assignment.course
            if not course:
                continue

            code = (course.course_code or "").lower().strip()
            title = re.sub(r'[^a-z0-9\s]+', ' ', (course.title or "").lower()).strip()

            title_tokens = [token for token in title.split() if len(token) > 3]
            matched_by_title = title and (
                title in normalized_query or
                (title_tokens and sum(1 for token in title_tokens if token in normalized_query) >= min(3, len(title_tokens)))
            )

            if (code and f" {code} " in f" {normalized_query} ") or matched_by_title:
                matched.append(assignment)

        if matched:
            return matched, target_dept

        unique_courses = {(a.course_id, a.department_id) for a in assignments if a.course_id}
        if len(unique_courses) == 1:
            return assignments, target_dept

        return [], target_dept

    def _exam_sort_key(self, exam_name):
        normalized = self._normalize_exam_name(exam_name)
        match = re.search(r'(\d+)', normalized)
        exam_number = int(match.group(1)) if match else 0
        return (exam_number, normalized)

    def _format_ranked_students(self, rows, limit):
        table_rows = []
        row_limit = limit if limit is not None else len(rows)

        for idx in range(row_limit):
            if idx < len(rows):
                row = rows[idx]
                name = row.get("student__name") or row.get("student_name") or "Unknown Student"
                reg_no = row.get("reg_no") or "N/A"
                marks = row.get("total_marks")
                marks_value = str(marks if marks is not None else 0)
            else:
                name = "-"
                reg_no = "-"
                marks_value = "-"

            table_rows.append((idx + 1, str(name), str(reg_no), marks_value))

        lines = [
            "S.No | Name | Reg No | Marks",
            "--- | --- | --- | ---",
        ]
        for sno, name, reg_no, marks in table_rows:
            lines.append(f"{sno} | {name} | {reg_no} | {marks}")
        return "\n".join(lines)

    def _format_student_subject_marks(self, rows):
        if not rows:
            return "No marks available."

        exam_chunks = []
        for row in rows:
            exam_name = row["exam_name"] or "Exam"
            exam_chunks.append(f"{exam_name}: {row['total_marks'] or 0}")
        return ", ".join(exam_chunks)

    def _format_student_internal_exam_marks(self, rows):
        if not rows:
            return []

        formatted_rows = []
        for row in rows:
            course_title = row.get("course__title") or "Unknown Subject"
            course_code = row.get("course_code") or "N/A"
            total_marks = row.get("total_marks")
            formatted_rows.append(
                f"- {course_title} ({course_code}): {total_marks if total_marks is not None else 0}"
            )
        return formatted_rows

    def _build_faculty_assignment_filter(self, faculty_id, faculty_info):
        employee_ids = {
            int(str(value).strip())
            for value in (faculty_id, getattr(faculty_info, "faculty_id", None))
            if value not in (None, "") and str(value).strip().isdigit()
        }
        profile_ids = set()
        if getattr(faculty_info, "id", None) is not None:
            profile_ids.add(faculty_info.id)
        if str(faculty_id or "").isdigit():
            profile_ids.add(int(faculty_id))

        assignment_filter = Q(pk__in=[])
        for employee_id in employee_ids:
            assignment_filter |= Q(faculty__faculty_id=employee_id)
            assignment_filter |= Q(skilled_faculty__faculty_id=employee_id)
        for profile_id in profile_ids:
            assignment_filter |= Q(faculty_id=profile_id)
            assignment_filter |= Q(skilled_faculty_id=profile_id)
        if getattr(faculty_info, "id", None):
            assignment_filter |= Q(faculty_id=faculty_info.id)
            assignment_filter |= Q(skilled_faculty_id=faculty_info.id)
        if getattr(faculty_info, "_meta", None):
            assignment_filter |= Q(faculty=faculty_info)
            assignment_filter |= Q(skilled_faculty=faculty_info)
        return assignment_filter

    def _scope_subject_marks_queryset(self, queryset, faculty_id, faculty_info, active_role, course_code):
        if self._is_vp_role(active_role):
            return queryset

        if self._is_hod_role(active_role):
            if not faculty_info.department:
                return queryset.none()

            return queryset.filter(student__department=faculty_info.department)

        if self._is_ca_role(active_role):
            ca_students = self._get_students_by_role_id(
                field_name="ca_id",
                faculty_info=faculty_info,
                faculty_id=faculty_id,
                role_names=["CA", "Advisor", "Class Advisor"],
                strict_ids=self._build_strict_ids(faculty_id, faculty_info),
            )
            student_ids = list(ca_students.values_list("id", flat=True))
            return queryset.filter(student_id__in=student_ids) if student_ids else queryset.none()

        if self._is_mentor_role(active_role):
            mentor_students = self._get_students_by_role_id(
                field_name="mentor_id",
                faculty_info=faculty_info,
                faculty_id=faculty_id,
                role_names=["Mentor"],
                strict_ids=self._build_strict_ids(faculty_id, faculty_info),
            )
            student_ids = list(mentor_students.values_list("id", flat=True))
            return queryset.filter(student_id__in=student_ids) if student_ids else queryset.none()

        if self._is_teacher_role(active_role):
            assignments = AssignSubjectFaculty.objects.filter(
                self._build_faculty_assignment_filter(faculty_id, faculty_info),
                is_active=1,
                course__course_code__iexact=course_code,
            ).values("department_id", "batch", "section")

            assignment_scope = Q()
            for assignment in assignments:
                assignment_scope |= Q(
                    student__department_id=assignment["department_id"],
                    batch=assignment["batch"],
                    section=assignment["section"],
                )

            return queryset.filter(assignment_scope) if assignment_scope else queryset.none()

        return queryset.none()

    def _scope_student_internal_marks_queryset(self, queryset, faculty_id, faculty_info, active_role):

        if self._is_vp_role(active_role):
            return queryset

        if self._is_hod_role(active_role):
            if not faculty_info.department:
                return queryset.none()

            return queryset.filter(student__department=faculty_info.department)

        if self._is_ca_role(active_role):
            ca_students = self._get_students_by_role_id(
                field_name="ca_id",
                faculty_info=faculty_info,
                faculty_id=faculty_id,
                role_names=["CA", "Advisor", "Class Advisor"],
                strict_ids=self._build_strict_ids(faculty_id, faculty_info),
            )
            student_ids = list(ca_students.values_list("id", flat=True))
            return queryset.filter(student_id__in=student_ids) if student_ids else queryset.none()

        if self._is_mentor_role(active_role):
            mentor_students = self._get_students_by_role_id(
                field_name="mentor_id",
                faculty_info=faculty_info,
                faculty_id=faculty_id,
                role_names=["Mentor"],
                strict_ids=self._build_strict_ids(faculty_id, faculty_info),
            )
            student_ids = list(mentor_students.values_list("id", flat=True))
            return queryset.filter(student_id__in=student_ids) if student_ids else queryset.none()

        return queryset.none()

    def _handle_subject_marks_query(self, faculty_id, active_role, query):
        try:
            faculty_info = self._get_faculty_info(faculty_id)
            if not faculty_info:
                return "Error: Could not find your faculty record."

            course_code = self._extract_course_code(query)
            if not course_code:
                matched_assignments, _ = self._resolve_subject_assignments(
                    query, faculty_id, faculty_info, active_role
                )
                matched_codes = sorted({
                    assignment.course.course_code
                    for assignment in matched_assignments
                    if assignment.course and assignment.course.course_code
                })
                if len(matched_codes) == 1:
                    course_code = matched_codes[0]
                else:
                    return (
                        "Please specify the subject name or course code, "
                        "for example: 'Show AD3491 end semester marks'."
                    )

            target_dept = self._extract_department(query)
            target_exam = self._extract_internal_assessment_name(query)

            marks_qs = StudentInternalMark.objects.filter(course_code__iexact=course_code)
            if target_dept:
                marks_qs = marks_qs.filter(student__department_id=target_dept.id)

            exam_label = "All Internal Assessments"
            if target_exam:
                available_exam_names = list(
                    marks_qs.exclude(exam_name__isnull=True)
                    .exclude(exam_name__exact="")
                    .values_list("exam_name", flat=True)
                    .distinct()
                )
                matched_exam_names = [
                    name for name in available_exam_names
                    if self._normalize_exam_name(name) == self._normalize_exam_name(target_exam)
                ]
                if not matched_exam_names:
                    return f"No marks found for {course_code} in {target_exam}."
                marks_qs = marks_qs.filter(exam_name__in=matched_exam_names)
                exam_label = matched_exam_names[0]

            scoped_qs = self._scope_subject_marks_queryset(
                marks_qs, faculty_id, faculty_info, active_role, course_code
            )

            mark_rows = self._subject_performance_mark_rows(scoped_qs)
            lower_only = any(term in query.lower() for term in [
                "low mark", "low score", "lower mark", "lower score",
                "marks below", "scores below", "weak student", "at risk",
                "at-risk",
            ])
            if lower_only:
                threshold_match = re.search(r"\bbelow\s+(\d{1,3})\b", query.lower())
                threshold = min(int(threshold_match.group(1)), 100) if threshold_match else 50
                mark_rows = [
                    row for row in mark_rows if row["percentage"] < threshold
                ]

            if not mark_rows:
                if lower_only:
                    return (
                        f"No students with recorded {course_code} marks below "
                        f"{threshold}% were found within your current role scope."
                    )
                return "No marks matched your request within your current role scope."

            course_info = Course.objects.filter(course_code__iexact=course_code)
            if target_dept:
                course_info = course_info.filter(department=target_dept)
            course_title = course_info.values_list("title", flat=True).first() or course_code

            header_parts = [f"**{course_code} - {course_title}**", exam_label]
            if target_dept:
                header_parts.append(target_dept.Department)
            if lower_only:
                header_parts.append(f"Below {threshold}% only")

            count_str = f"Total: {len(mark_rows)}"
            if len(mark_rows) > 100:
                count_str += " (Showing first 100)"

            table_text = self._format_student_marks_table(mark_rows[:100])

            return " | ".join(header_parts) + "\n\n" + table_text + f"\n\n{count_str}"

        except Exception as e:
            return f"Error retrieving marks: {str(e)}"

    def _handle_student_subject_marks_query(self, faculty_id, active_role, query):
        try:
            faculty_info = self._get_faculty_info(faculty_id)
            if not faculty_info:
                return "Error: Could not find your faculty record."

            reg_nos = []
            seen_regs = set()
            for reg_no in re.findall(r'\b\d{12}\b', query):
                if reg_no not in seen_regs:
                    seen_regs.add(reg_no)
                    reg_nos.append(reg_no)

            if not reg_nos:
                return "Please provide at least one valid registration number."

            effective_role = active_role
            if self._is_teacher_role(active_role):
                requested_students = list(
                    self._student_queryset().filter(reg_no__in=reg_nos)
                )
                requested_student_ids = {student.id for student in requested_students if student.id is not None}

                if requested_student_ids:
                    ca_students = self._get_students_by_role_id(
                        field_name="ca_id",
                        faculty_info=faculty_info,
                        faculty_id=faculty_id,
                        role_names=["CA", "Advisor", "Class Advisor"],
                        strict_ids=self._build_strict_ids(faculty_id, faculty_info),
                    )
                    ca_student_ids = set(ca_students.values_list("id", flat=True))

                    mentor_students = self._get_students_by_role_id(
                        field_name="mentor_id",
                        faculty_info=faculty_info,
                        faculty_id=faculty_id,
                        role_names=["Mentor"],
                        strict_ids=self._build_strict_ids(faculty_id, faculty_info),
                    )
                    mentor_student_ids = set(mentor_students.values_list("id", flat=True))

                    if requested_student_ids.issubset(ca_student_ids):
                        effective_role = "Class Advisor"
                    elif requested_student_ids.issubset(mentor_student_ids):
                        effective_role = "Mentor"

            course_code = self._extract_course_code(query)
            target_exam = self._extract_internal_assessment_name(query)
            if not course_code:
                if target_exam and (
                    self._is_vp_role(effective_role)
                    or self._is_hod_role(effective_role)
                    or self._is_ca_role(effective_role)
                    or self._is_mentor_role(effective_role)
                ):
                    marks_qs = StudentInternalMark.objects.filter(reg_no__in=reg_nos)

                    available_exam_names = list(
                        marks_qs.exclude(exam_name__isnull=True)
                        .exclude(exam_name__exact="")
                        .values_list("exam_name", flat=True)
                        .distinct()
                    )
                    matched_exam_names = [
                        name for name in available_exam_names
                        if self._normalize_exam_name(name) == self._normalize_exam_name(target_exam)
                    ]
                    if not matched_exam_names:
                        return f"No marks found in {target_exam} for the requested student(s)."

                    exam_label = matched_exam_names[0]
                    marks_qs = marks_qs.filter(exam_name__in=matched_exam_names)
                    scoped_qs = self._scope_student_internal_marks_queryset(
                        marks_qs, faculty_id, faculty_info, effective_role
                    )

                    grouped_rows = list(
                        scoped_qs.values(
                            "reg_no",
                            "student__name",
                            "course_code",
                            "course__title",
                        ).annotate(
                            total_marks=Sum("marks_obtained"),
                        ).order_by("reg_no", "course_code", "course__title")
                    )

                    if not grouped_rows:
                        return f"No accessible {exam_label} marks found for the requested student(s) within your current role scope."

                    marks_by_student = {}
                    for row in grouped_rows:
                        marks_by_student.setdefault(row["reg_no"], {
                            "student_name": row["student__name"] or "Unknown Student",
                            "rows": [],
                        })
                        marks_by_student[row["reg_no"]]["rows"].append(row)

                    lines = [f"**{exam_label} Marks**"]
                    for reg_no in reg_nos:
                        student_data = marks_by_student.get(reg_no)
                        if student_data:
                            lines.append(f"\n**{student_data['student_name']} ({reg_no})**")
                            lines.extend(self._format_student_internal_exam_marks(student_data["rows"]))
                        else:
                            lines.append(f"\n**{reg_no}**")
                            lines.append("- No accessible marks found.")

                    return "\n".join(lines)

                if any(token in (query or "").lower() for token in ["internal", "iat"]):
                    return self._handle_current_student_internal_marks_query(
                        faculty_id, effective_role, query, reg_nos, faculty_info
                    )

                return "Please provide the subject code to retrieve marks for a particular student or students."

            if self._is_teacher_role(effective_role):
                matched_assignments, _ = self._resolve_subject_assignments(
                    query, faculty_id, faculty_info, effective_role
                )
                if not matched_assignments:
                    return f"You are not assigned to subject code {course_code} in your current role scope."

            marks_qs = StudentInternalMark.objects.filter(
                course_code__iexact=course_code,
                reg_no__in=reg_nos,
            )

            if target_exam:
                available_exam_names = list(
                    marks_qs.exclude(exam_name__isnull=True)
                    .exclude(exam_name__exact="")
                    .values_list("exam_name", flat=True)
                    .distinct()
                )
                matched_exam_names = [
                    name for name in available_exam_names
                    if self._normalize_exam_name(name) == self._normalize_exam_name(target_exam)
                ]
                if not matched_exam_names:
                    return f"No marks found for {course_code} in {target_exam} for the requested student(s)."
                marks_qs = marks_qs.filter(exam_name__in=matched_exam_names)

            scoped_qs = self._scope_subject_marks_queryset(
                marks_qs, faculty_id, faculty_info, effective_role, course_code
            )

            grouped_rows = list(
                scoped_qs.values(
                    "reg_no",
                    "student__name",
                    "exam_name",
                ).annotate(
                    total_marks=Sum("marks_obtained"),
                ).order_by("reg_no", "exam_name")
            )

            if not grouped_rows:
                return f"No subject marks found for subject code {course_code} and the requested student(s) within your accessible scope."

            marks_by_student = {}
            for row in grouped_rows:
                marks_by_student.setdefault(row["reg_no"], {
                    "student_name": row["student__name"] or "Unknown Student",
                    "rows": [],
                })
                marks_by_student[row["reg_no"]]["rows"].append(row)

            course_title = (
                Course.objects.filter(course_code__iexact=course_code)
                .values_list("title", flat=True)
                .first()
                or course_code
            )

            lines = [f"marks for {course_title} ({course_code}):"]
            for reg_no in reg_nos:
                student_data = marks_by_student.get(reg_no)
                if student_data:
                    marks_text = self._format_student_subject_marks(student_data["rows"])
                    lines.append(f"- {student_data['student_name']} ({reg_no}): {marks_text}")
                else:
                    lines.append(f"- {reg_no}: No accessible marks found for {course_code}.")

            return "\n".join(lines)

        except Exception as e:
            return f"Error retrieving student subject marks: {str(e)}"

    def _handle_class_report_query(
        self, faculty_id, active_role, query, all_roles=None
    ):
        try:
            active_role = self._resolve_class_report_role(
                active_role, all_roles=all_roles
            )
            faculty_info = self._get_faculty_info(faculty_id)
            if not faculty_info:
                if self._is_admin_role(active_role):
                    class AdminReportIdentity:
                        id = None
                        faculty_id = None
                        department = None
                        name = "Administrator"
                    faculty_info = AdminReportIdentity()
                else:
                    return "Error: Could not find your faculty record."

            # Some deployments store CA as an academic student mapping without
            # a matching approval-system role row. Treat that mapping as the
            # authority when the login role otherwise resolves only to Faculty.
            if self._is_teacher_role(active_role) and all_roles is not None:
                ca_students = self._get_students_by_role_id(
                    field_name="ca_id",
                    faculty_info=faculty_info,
                    faculty_id=faculty_id,
                    role_names=["CA", "Advisor", "Class Advisor"],
                    strict_ids=self._build_strict_ids(faculty_id, faculty_info),
                )
                if ca_students.filter(
                    is_active=True, is_discontinued=False
                ).exists():
                    active_role = "Class Advisor"

            requested_course_code = self._extract_course_code(query)
            if not requested_course_code:
                return (
                    "Please provide the subject code, assessment, and batch number.\n"
                    "Correct format:\n"
                    "Class report for <Subject Code> in <Assessment> <Batch Number>\n"
                    "Example:\nClass report for AD3491 in IAT 1 2024\u20132028"
                )

            target_section = self._extract_section(query)

            matched_assignments, target_dept = self._resolve_subject_assignments(
                query,
                faculty_id,
                faculty_info,
                active_role,
                for_class_report=True,
            )
            if not matched_assignments:
                if (
                    self._is_hod_role(active_role)
                    and target_dept
                    and not self._same_department(target_dept, faculty_info.department)
                ):
                    return "Access denied: HOD class reports are limited to your mapped department."
                if self._is_ca_role(active_role):
                    return (
                        f"No {requested_course_code} allocation was found for students "
                        "under your Class Advisor scope."
                    )
                if self._is_hod_role(active_role):
                    return (
                        f"No {requested_course_code} allocation was found in your HOD department."
                    )
                return (
                    f"No accessible assignment was found for subject code "
                    f"{requested_course_code}."
                )

            if self._is_admin_role(active_role) and not target_dept:
                available_departments = sorted({
                    assignment.department.Department
                    if assignment.department
                    else assignment.course.department.Department
                    for assignment in matched_assignments
                    if assignment.department
                    or (assignment.course and assignment.course.department)
                })
                if available_departments:
                    return "\n".join([
                        f"Please specify the department name for the Admin class "
                        f"report of {requested_course_code}.",
                        "Available departments:",
                        *[f"- {name}" for name in available_departments],
                        "Correct format:",
                        "Class report for <Subject Code> in <Assessment> "
                        "<Batch Number> <Department Name>",
                    ])

            course = next((assignment.course for assignment in matched_assignments if assignment.course), None)
            if not course:
                return "No valid subject assignment found for this class report request."

            course_code = course.course_code or self._extract_course_code(query)
            if not course_code:
                return "Unable to determine the subject for the class report."

            target_batch = self._extract_batch(query)
            available_exam_names = self._get_class_report_assessments(
                course_code, matched_assignments
            )
            exam_label, assessment_supplied = self._resolve_class_report_assessment(
                query, available_exam_names
            )
            if not target_batch or not assessment_supplied:
                error = None
                if assessment_supplied and not exam_label:
                    error = "The requested assessment does not exist for this subject."
                return self._class_report_request_guidance(
                    course_code, matched_assignments, available_exam_names, error=error
                )
            if not self._is_valid_batch_value(target_batch):
                return self._class_report_request_guidance(
                    course_code,
                    matched_assignments,
                    available_exam_names,
                    error="The batch number is invalid. Please use a four-year range such as 2024\u20132028.",
                )

            batch_assignments = [
                assignment for assignment in matched_assignments
                if self._batch_matches(assignment.batch, target_batch)
            ]
            if not batch_assignments:
                return self._class_report_request_guidance(
                    course_code,
                    matched_assignments,
                    available_exam_names,
                    error=f"The requested batch is not assigned to you for {course_code}.",
                )

            batch_exam_names = self._get_class_report_assessments(
                course_code, batch_assignments
            )
            exam_label, assessment_supplied = self._resolve_class_report_assessment(
                query, batch_exam_names
            )
            if not exam_label:
                return self._class_report_request_guidance(
                    course_code,
                    batch_assignments,
                    batch_exam_names,
                    error=(
                        f"The requested assessment does not exist for {course_code} "
                        f"batch {self._display_batch(target_batch)}."
                    ),
                )

            if target_section:
                section_assignments = [
                    assignment for assignment in batch_assignments
                    if str(assignment.section or "").strip().upper() == target_section
                ]
                if not section_assignments:
                    sections = sorted({
                        str(item.section).strip().upper()
                        for item in batch_assignments if item.section
                    })
                    return (
                        f"Section {target_section} is not assigned to you for {course_code} "
                        f"batch {self._display_batch(target_batch)}. Available sections: "
                        f"{', '.join(sections) or 'N/A'}."
                    )
                matched_assignments = section_assignments
            else:
                sections = sorted({
                    str(item.section).strip().upper()
                    for item in batch_assignments if item.section
                })
                if len(sections) > 1:
                    return (
                        f"Multiple sections are assigned for {course_code} batch "
                        f"{self._display_batch(target_batch)}: {', '.join(sections)}. "
                        "Please specify the section.\n"
                        f"Example: Class report for {course_code} "
                        f"{self._display_batch(target_batch)} section {sections[0]}"
                    )
                matched_assignments = batch_assignments

            department_names = []
            batch_values = set()
            section_values = set()
            year_values = set()
            department_ids = set()

            for assignment in matched_assignments:
                dept_obj = assignment.department or (assignment.course.department if assignment.course else None)
                if dept_obj and dept_obj.id not in department_ids:
                    department_ids.add(dept_obj.id)
                    department_names.append(dept_obj.Department)

                if assignment.batch:
                    batch_values.add(str(assignment.batch))
                if assignment.section:
                    section_values.add(str(assignment.section))
                if assignment.course and assignment.course.year:
                    year_values.add(str(assignment.course.year))

            if target_section:
                section_values = {target_section}

            marks_qs = StudentInternalMark.objects.filter(course_code__iexact=course_code)

            if department_ids:
                marks_qs = marks_qs.filter(student__department_id__in=list(department_ids))
            elif target_dept:
                marks_qs = marks_qs.filter(student__department_id=target_dept.id)

            if batch_values:
                marks_qs = marks_qs.filter(batch__in=list(batch_values))
            if section_values:
                marks_qs = marks_qs.filter(section__in=list(section_values))

            marks_qs = marks_qs.filter(exam_name=exam_label)

            scoped_qs = self._scope_subject_marks_queryset(
                marks_qs, faculty_id, faculty_info, active_role, course_code
            )

            report_rows = list(
                scoped_qs.values(
                    "student_id",
                    "student__name",
                    "reg_no",
                    "student__gender",
                    "student__department__Department",
                    "student__year",
                    "course__year",
                    "section",
                ).annotate(
                    total_marks=Sum("marks_obtained"),
                    max_marks=Sum("max_marks"),
                ).order_by("-total_marks", "reg_no", "student__name")
            )

            if not report_rows:
                return "No class report data matched your request within your current role scope."

            if not year_values:
                year_values = {
                    str(row["course__year"] or row["student__year"])
                    for row in report_rows
                    if row["course__year"] or row["student__year"]
                }
            if not section_values:
                section_values = {
                    str(row["section"])
                    for row in report_rows
                    if row["section"]
                }
            if not department_names:
                department_names = sorted({
                    row["student__department__Department"]
                    for row in report_rows
                    if row["student__department__Department"]
                })

            pass_mark = 50
            total_students = len(report_rows)
            passed_students = sum(1 for row in report_rows if (row["total_marks"] or 0) >= pass_mark)
            pass_percentage = round((passed_students / total_students) * 100, 2) if total_students else 0

            boys = [
                row for row in report_rows
                if (row["student__gender"] or "").strip().lower() == "male"
            ]
            girls = [
                row for row in report_rows
                if (row["student__gender"] or "").strip().lower() == "female"
            ]

            subject_name = course.title or course_code
            if course.course_code:
                subject_name = f"{subject_name} ({course.course_code})"
            if exam_label:
                subject_name = f"{subject_name} - {exam_label}"

            department_text = ", ".join(sorted(filter(None, department_names))) or (
                target_dept.Department if target_dept else "N/A"
            )
            year_text = ", ".join(sorted(year_values)) if year_values else "N/A"
            section_text = ", ".join(sorted(section_values)) if section_values else "N/A"

            response_lines = [
                f"class report for {subject_name}:",
                f"batch: {self._display_batch(target_batch)}",
                f"department: {department_text}",
                f"year/section: {year_text}/{section_text}",
                "",
                f"overall class pass percentage: {pass_percentage}%",
                "",
                "Overall performance:",
                "list top 5 high scored students followed name (reg no) and marks.",
                self._format_ranked_students(report_rows, 5),
                "",
                "Top performance in boys:",
                "followed name (reg no), marks",
                self._format_ranked_students(boys, 3),
                "",
                "Top performance in girls:",
                "followed name (reg no), marks",
                self._format_ranked_students(girls, 3),
            ]

            return "\n".join(response_lines)

        except Exception as e:
            return f"Error generating class report: {str(e)}"

    def _get_faculty_info(self, faculty_id):
        try:
            f = None
            if str(faculty_id or "").strip().isdigit():
                f = general_information.objects.filter(
                    faculty_id=int(str(faculty_id).strip())
                ).first()
            if f: return f
            # Legacy/Approval System lookup (ORM only)
            try:
                cr_user = self._approval_user_queryset().select_related('Department').filter(
                    Employee_id=faculty_id
                ).first()
                if cr_user:
                    name = cr_user.username
                    dept_name = cr_user.Department.Department if cr_user.Department else None
                    dept = Add_Department.objects.filter(Department__iexact=dept_name).first() if dept_name else None
                    class TransientFaculty:
                        def __init__(self, name, dept): self.name, self.department, self.id = name, dept, 0
                    return TransientFaculty(name, dept)
            except Exception:
                pass
        except: pass
        return None

    # ------------------------------------------------------------------
    # Faculty productivity workflows
    # ------------------------------------------------------------------

    def _active_students_for_role(self, faculty_id, active_role):
        """Return the narrowest student queryset authorized by the active role."""
        faculty = self._get_faculty_info(faculty_id)
        base = self._student_queryset().filter(
            is_active=True, is_discontinued=False
        )
        if self._is_vp_role(active_role):
            return base
        if not faculty:
            return base.none()
        if self._is_hod_role(active_role):
            return base.filter(department=getattr(faculty, "department", None))
        strict_ids = self._build_strict_ids(faculty_id, faculty)
        if self._is_ca_role(active_role):
            return self._get_students_by_role_id(
                "ca_id", faculty, faculty_id,
                ["CA", "Advisor", "Class Advisor"], strict_ids=strict_ids,
            ).filter(is_active=True, is_discontinued=False)
        if self._is_mentor_role(active_role):
            return self._get_students_by_role_id(
                "mentor_id", faculty, faculty_id, ["Mentor"],
                strict_ids=strict_ids,
            ).filter(is_active=True, is_discontinued=False)
        if self._is_teacher_role(active_role):
            assignments = list(
                AssignSubjectFaculty.objects.filter(
                    self._build_faculty_assignment_filter(faculty_id, faculty),
                    is_active=True,
                ).values("department_id", "batch", "section")
            )
            scope = Q(pk__in=[])
            for item in assignments:
                scope |= Q(
                    department_id=item["department_id"],
                    batch=item["batch"],
                    section=item["section"],
                )
            return base.filter(scope).distinct() if assignments else base.none()
        return base.none()

    def _can_access_workflow_student(self, faculty_id, active_role, student):
        if not student:
            return False
        return self._active_students_for_role(
            faculty_id, active_role
        ).filter(pk=student.pk).exists()

    def _faculty_assignments(self, faculty_id):
        faculty = self._get_faculty_info(faculty_id)
        if not faculty:
            return AssignSubjectFaculty.objects.none()
        return AssignSubjectFaculty.objects.filter(
            self._build_faculty_assignment_filter(faculty_id, faculty),
            is_active=True,
        ).select_related("course", "department")

    def _handle_daily_briefing(self, faculty_id, active_role):
        faculty = self._get_faculty_info(faculty_id)
        if not faculty:
            return "Faculty profile not found."
        today = timezone.localdate()
        day_name = today.strftime("%A")
        timetable = self._handle_faculty_timetable(faculty_id, active_role)
        today_periods = [
            line for line in timetable.splitlines()
            if line.lstrip("- ").startswith(f"{day_name} -")
        ]
        unread = 0
        try:
            unread = Notification.objects.filter(
                receiver=faculty, is_read=False
            ).count()
        except Exception:
            pass

        pending = self._pending_work_rows(faculty_id, active_role)
        notices = []
        try:
            notice_qs = Announcement.objects.filter(is_active=True).filter(
                Q(users=faculty)
                | Q(departments=getattr(faculty, "department", None))
                | Q(departments__isnull=True, users__isnull=True, roles__isnull=True)
            ).distinct().order_by("-created_at")[:3]
            notices = [item.title or "Untitled announcement" for item in notice_qs]
        except Exception:
            pass

        lines = [
            f"Daily Faculty Briefing | {today.strftime('%d %B %Y')}",
            f"Good day, {getattr(faculty, 'name', None) or 'Faculty'}.",
            "",
            f"Today's classes ({len(today_periods)}):",
        ]
        lines.extend(today_periods or ["- No mapped classes for today."])
        lines.extend([
            "",
            "Pending academic work:",
            f"- Attendance/mark items requiring attention: {len(pending)}",
            f"- Unread chatbot notifications: {unread}",
            "",
            "Latest announcements:",
        ])
        lines.extend([f"- {title}" for title in notices] or ["- No active announcements."])
        return "\n".join(lines)

    def _pending_work_rows(self, faculty_id, active_role=None):
        today = timezone.localdate()
        rows = []
        faculty = self._get_faculty_info(faculty_id)
        assignments = self._faculty_assignments(faculty_id)
        if self._is_hod_role(active_role) and faculty and faculty.department:
            assignments = AssignSubjectFaculty.objects.filter(
                Q(department=faculty.department) | Q(course__department=faculty.department),
                is_active=True,
            ).select_related("course", "department")
        for assignment in assignments[:100]:
            course = getattr(assignment, "course", None)
            if not course:
                continue
            students = self._student_queryset().filter(
                is_active=True,
                is_discontinued=False,
                department_id=assignment.department_id,
                batch=assignment.batch,
                section=assignment.section,
            )
            expected = students.count()
            if not expected:
                continue
            recorded_today = HourAttendance.objects.filter(
                faculty_id__in=[assignment.faculty_id, assignment.skilled_faculty_id],
                course=course,
                date=today,
                student_id__in=students.values("id"),
            ).values("student_id").distinct().count()
            if recorded_today < expected:
                rows.append(
                    f"Attendance: {course.course_code or 'N/A'} Section "
                    f"{assignment.section or 'N/A'} - {recorded_today}/{expected} recorded today"
                )

            assessments = Assessment_master.objects.filter(
                assigned_faculty=assignment
            ).order_by("id")
            for assessment in assessments:
                marked = AssessmentMark.objects.filter(
                    assignment=assignment, assessment=assessment
                ).values("student_id").distinct().count()
                if marked < expected:
                    rows.append(
                        f"Marks: {course.course_code or 'N/A'} - "
                        f"{assessment.Assessmentname or assessment.customAssessmentname or 'Assessment'}: "
                        f"{marked}/{expected} entered"
                    )
        return rows

    def _handle_pending_work(self, faculty_id, active_role):
        rows = self._pending_work_rows(faculty_id, active_role)
        if not rows:
            return "Pending Work\nNo incomplete attendance or mark-entry items were found for your active assignments."
        return "Pending Work\n" + "\n".join(
            f"{index}. {row}" for index, row in enumerate(rows[:50], start=1)
        )

    def _is_subject_risk_query(self, query):
        query_lower = (query or "").lower()
        if not self._extract_course_code(query):
            return False
        risk_term = any(term in query_lower for term in [
            "low", "lower", "below", "shortage", "at risk", "at-risk",
            "weak", "needs attention", "need attention",
        ])
        return risk_term

    def _subject_performance_mark_rows(self, queryset):
        """Normalize question-level marks into bounded student percentages."""
        details = list(
            queryset.values(
                "id",
                "student_id",
                "student__name",
                "student__reg_no",
                "reg_no",
                "student__department__Department",
                "batch",
                "section",
                "course_code",
                "course__title",
                "exam_name",
                "part_name",
                "question_number",
                "sub_question",
                "option_letter",
                "max_marks",
                "marks_obtained",
            ).order_by(
                "student_id", "exam_name", "part_name", "question_number",
                "option_letter", "sub_question",
            )
        )
        grouped = {}
        for detail in details:
            grouped.setdefault(detail["student_id"], []).append(detail)

        results = []
        for student_id, student_details in grouped.items():
            assessments = self._aggregate_student_mark_details(student_details)
            maximum = 0
            obtained = 0
            adjusted = False
            for assessment in assessments:
                assessment_max = max(0, assessment.get("maximum") or 0)
                assessment_obtained = max(0, assessment.get("obtained") or 0)
                if assessment_max <= 0:
                    continue
                if assessment_obtained > assessment_max:
                    assessment_obtained = assessment_max
                    adjusted = True
                maximum += assessment_max
                obtained += assessment_obtained
            if maximum <= 0:
                continue
            percentage = round(min(100, max(0, obtained * 100 / maximum)), 2)
            percentage_text = f"{percentage:.2f}".rstrip("0").rstrip(".")
            first = student_details[0]
            results.append({
                "student_id": student_id,
                "student__name": first.get("student__name"),
                "reg_no": first.get("student__reg_no") or first.get("reg_no"),
                "student__department__Department": first.get(
                    "student__department__Department"
                ),
                "batch": first.get("batch"),
                "section": first.get("section"),
                "obtained": obtained,
                "maximum": maximum,
                "percentage": percentage,
                "adjusted": adjusted,
                "total_marks": f"{percentage_text}/100",
            })
        return sorted(
            results,
            key=lambda row: (row["percentage"], str(row["reg_no"] or "")),
        )

    def _subject_students_for_assignments(
        self, faculty_id, active_role, assignments
    ):
        students = self._active_students_for_role(faculty_id, active_role)
        scope = Q(pk__in=[])
        for assignment in assignments:
            assignment_scope = Q()
            department_id = assignment.department_id or getattr(
                getattr(assignment, "course", None), "department_id", None
            )
            if department_id:
                assignment_scope &= Q(department_id=department_id)
            if assignment.batch:
                assignment_scope &= Q(batch=assignment.batch)
            if assignment.section:
                assignment_scope &= Q(section__iexact=assignment.section)
            scope |= assignment_scope
        return students.filter(scope).distinct() if assignments else students.none()

    def _handle_subject_risk_students(self, faculty_id, active_role, query):
        faculty = self._get_faculty_info(faculty_id)
        if not faculty:
            return "Error: Could not find your faculty record."
        course_code = self._extract_course_code(query)
        assignment_qs = self._class_report_assignment_queryset(
            faculty_id, faculty, active_role
        ).filter(course__course_code__iexact=course_code)
        assignments = list(assignment_qs)
        if not assignments:
            return (
                f"Access denied: no active {course_code} assignment is available "
                "within your current role scope."
            )
        students = list(
            self._subject_students_for_assignments(
                faculty_id, active_role, assignments
            )[:500]
        )
        if not students:
            return f"No active students are mapped to your {course_code} assignment."
        student_map = {student.id: student for student in students}
        student_ids = list(student_map)

        current_semester_scope = Q(pk__in=[])
        for student in students:
            semester = self._semester_number(getattr(student, "semester", None))
            student_scope = Q(student_id=student.id)
            if semester is not None:
                student_scope &= Q(semester__iexact=str(semester))
            current_semester_scope |= student_scope

        hour_rows = HourAttendance.objects.filter(
            current_semester_scope,
            student_id__in=student_ids,
            course__course_code__iexact=course_code,
        ).values("student_id").annotate(
            total=Count("id"),
            attended=Count("id", filter=Q(status__in=["Present", "On Duty"])),
        )
        hour_attendance = {
            row["student_id"]: {
                "attended": row["attended"] or 0,
                "total": row["total"] or 0,
                "percentage": round(
                    (row["attended"] or 0) * 100 / row["total"], 2
                ) if row["total"] else None,
            }
            for row in hour_rows
        }

        day_qs = Daily_Attendance.objects.filter(student_id__in=student_ids)
        day_counts = {
            student_id: {"attended": 0, "total": 0}
            for student_id in student_ids
        }
        for student_id, morning, afternoon in day_qs.values_list(
            "student_id", "morning_status", "afternoon_status"
        ):
            item = day_counts[student_id]
            for status in (morning, afternoon):
                if status:
                    item["total"] += 1
                    if status in {"Present", "On Duty"}:
                        item["attended"] += 1
        day_attendance = {}
        for student_id, item in day_counts.items():
            if item["total"]:
                item["percentage"] = round(
                    item["attended"] * 100 / item["total"], 2
                )
                day_attendance[student_id] = item

        marks_qs = StudentInternalMark.objects.filter(
            current_semester_scope,
            student_id__in=student_ids,
            course_code__iexact=course_code,
            marks_obtained__isnull=False,
            max_marks__isnull=False,
        )
        marks_qs = self._scope_subject_marks_queryset(
            marks_qs, faculty_id, faculty, active_role, course_code
        )
        marks = self._subject_performance_mark_rows(marks_qs)
        low_marks = [row for row in marks if row["percentage"] < 50]

        low_attendance = []
        for student in students:
            hour = hour_attendance.get(student.id)
            day = day_attendance.get(student.id)
            if (
                (hour and hour["percentage"] < 75)
                or (day and day["percentage"] < 75)
            ):
                low_attendance.append((student, hour, day))
        low_attendance.sort(
            key=lambda item: min(
                item[1]["percentage"] if item[1] else 101,
                item[2]["percentage"] if item[2] else 101,
            )
        )

        course = assignments[0].course
        lines = [
            f"Subject Attention List | {course_code} - {course.title or course_code}",
            "Thresholds: attendance below 75%; normalized marks below 50%.",
            "",
            f"Low Attendance ({len(low_attendance)}):",
        ]
        if low_attendance:
            for index, (student, hour, day) in enumerate(
                low_attendance[:100], start=1
            ):
                hour_text = (
                    f"{hour['attended']}/{hour['total']} ({hour['percentage']}%)"
                    if hour else "N/A"
                )
                day_text = (
                    f"{day['attended']}/{day['total']} ({day['percentage']}%)"
                    if day else "N/A"
                )
                lines.append(
                    f"{index}. {student.name or 'N/A'} ({student.reg_no}) | "
                    f"Hour attendance: {hour_text} | Day attendance: {day_text}"
                )
        else:
            lines.append("- No students with recorded attendance below 75%.")

        lines.extend(["", f"Low Marks ({len(low_marks)}):"])
        if low_marks:
            for index, row in enumerate(low_marks[:100], start=1):
                note = " | Invalid source rows normalized" if row["adjusted"] else ""
                percentage_text = (
                    f"{row['percentage']:.2f}".rstrip("0").rstrip(".")
                )
                lines.append(
                    f"{index}. {row['student__name'] or 'N/A'} ({row['reg_no']}) | "
                    f"Normalized marks: {percentage_text}/100{note}"
                )
        else:
            lines.append("- No students with recorded marks below 50%.")
        return "\n".join(lines)

    def _handle_early_warning(self, faculty_id, active_role):
        students = list(self._active_students_for_role(faculty_id, active_role)[:500])
        if not students:
            return "No students are mapped to your active role."
        student_ids = [student.id for student in students]
        attendance = {
            item["student"].id: item["percentage"]
            for item in self._hod_attendance_percentages(students)
        }
        mark_rows = StudentInternalMark.objects.filter(
            student_id__in=student_ids,
            marks_obtained__isnull=False,
            max_marks__isnull=False,
        ).values("student_id").annotate(
            obtained=Sum("marks_obtained"), maximum=Sum("max_marks")
        )
        marks = {
            row["student_id"]: round((row["obtained"] or 0) * 100 / row["maximum"], 2)
            for row in mark_rows if row["maximum"]
        }
        risks = []
        for student in students:
            reasons = []
            attendance_value = attendance.get(student.id)
            mark_value = marks.get(student.id)
            if attendance_value is not None and attendance_value < 75:
                reasons.append(f"attendance {attendance_value}%")
            if mark_value is not None and mark_value < 50:
                reasons.append(f"marks {mark_value}%")
            if reasons:
                risks.append((len(reasons), attendance_value or 101, student, reasons))
        risks.sort(key=lambda item: (-item[0], item[1], item[2].name or ""))
        if not risks:
            return "Early Warning\nNo students currently cross the configured thresholds (attendance below 75% or marks below 50%)."
        lines = [
            "Early Warning Students",
            "Thresholds: attendance below 75% or aggregate marks below 50%.",
        ]
        for index, (_, __, student, reasons) in enumerate(risks[:100], start=1):
            lines.append(
                f"{index}. {student.name or 'N/A'} ({student.reg_no}) - "
                + "; ".join(reasons)
            )
        lines.append("These indicators support faculty review; they are not disciplinary decisions.")
        return "\n".join(lines)

    def _handle_ca_low_performing(self, faculty_id, active_role, course_code=None):
        filter_course_code = course_code
        students = list(self._active_students_for_role(faculty_id, active_role)[:500])
        if not students:
            return "No students are mapped to your class."
        student_ids = [student.id for student in students]

        current_semester_scope = Q(pk__in=[])
        for student in students:
            semester = self._semester_number(getattr(student, "semester", None))
            student_scope = Q(student_id=student.id)
            if semester is not None:
                student_scope &= Q(semester__iexact=str(semester))
            current_semester_scope |= student_scope

        marks_qs = StudentInternalMark.objects.filter(
            current_semester_scope,
            student_id__in=student_ids,
            marks_obtained__isnull=False,
            max_marks__isnull=False,
        )
        if filter_course_code:
            marks_qs = marks_qs.filter(course_code__iexact=filter_course_code)
        marks_qs = self._scope_subject_marks_queryset(
            marks_qs, faculty_id,
            self._get_faculty_info(faculty_id), active_role, filter_course_code,
        )
        details = list(
            marks_qs.values(
                "student_id", "course_code", "exam_name",
                "part_name", "question_number", "sub_question",
                "option_letter", "max_marks", "marks_obtained",
            ).order_by(
                "student_id", "course_code", "exam_name",
                "part_name", "question_number", "option_letter", "sub_question",
            )
        )

        # Group marks by (student, course, exam_name) — each IAT evaluated separately
        iat_totals = {}
        for detail in details:
            sid = detail["student_id"]
            course_code = detail.get("course_code")
            exam_name = detail.get("exam_name") or ""
            if not course_code:
                continue
            key = (sid, course_code, exam_name)
            entry = iat_totals.setdefault(key, {"obtained": 0, "max": 0})
            option = str(detail.get("option_letter") or "").strip().lower()
            if option:
                opt_key = f"opt_{option}"
                prev_max = entry.get(f"{opt_key}_max", 0)
                prev_obt = entry.get(f"{opt_key}_obt", 0)
                entry[f"{opt_key}_max"] = prev_max + (detail.get("max_marks") or 0)
                entry[f"{opt_key}_obt"] = prev_obt + (detail.get("marks_obtained") or 0)
            else:
                entry["obtained"] += detail.get("marks_obtained") or 0
                entry["max"] += detail.get("max_marks") or 0

        # Compute percentage per IAT per course per student
        student_iat_results = {}
        for (sid, course_code, exam_name), entry in iat_totals.items():
            opt_max = max(
                (entry.get(f"opt_{o}_max") or 0)
                for o in "abcde"
                if entry.get(f"opt_{o}_max")
            ) if any(entry.get(f"opt_{o}_max") for o in "abcde") else 0
            opt_obt = max(
                (entry.get(f"opt_{o}_obt") or 0)
                for o in "abcde"
                if entry.get(f"opt_{o}_max")
            ) if opt_max else 0
            total_max = entry["max"] + opt_max
            total_obt = entry["obtained"] + opt_obt
            if total_max <= 0:
                continue
            percentage = round(min(100, max(0, total_obt * 100 / total_max)), 2)
            student_iat_results.setdefault(sid, {})
            student_iat_results[sid].setdefault(course_code, {})[exam_name] = percentage

        # Build a set of all course_codes that have marks in the system
        all_courses_with_marks = set()
        for sid, courses in student_iat_results.items():
            for course_code in courses:
                all_courses_with_marks.add((sid, course_code))

        student_map = {s.id: s for s in students}
        low_performing = []
        no_marks_students = []

        for student in students:
            sid = student.id
            courses_with_iats = student_iat_results.get(sid, {})
            if not courses_with_iats:
                # Student has no marks at all
                no_marks_students.append(student)
                continue
            flagged_subjects = []
            for course_code, iats in sorted(courses_with_iats.items()):
                for exam_name in sorted(iats.keys()):
                    pct = iats[exam_name]
                    if pct < 60:
                        flagged_subjects.append((course_code, exam_name, pct))
            if flagged_subjects:
                low_performing.append((student, flagged_subjects))

        low_performing.sort(key=lambda r: (r[0].name or "", r[0].id))

        if filter_course_code:
            lines = [f"Low-Performing Students | {filter_course_code}", ""]
        else:
            lines = ["Low-Performing Students", ""]

        if low_performing:
            lines.append("Students scoring below 60% in IAT1/IAT2:")
            lines.append("")
            lines.append("Student | Register Number | Subject | IAT | Marks")
            lines.append("--- | --- | --- | --- | ---")
            for student, subjects in low_performing:
                for course_code, exam_name, pct in sorted(subjects, key=lambda s: (s[0], s[1])):
                    pct_text = f"{pct:.2f}".rstrip("0").rstrip(".")
                    lines.append(
                        f"{student.name or 'N/A'} | "
                        f"{student.reg_no or 'N/A'} | "
                        f"{course_code or 'N/A'} | "
                        f"{exam_name or 'N/A'} | "
                        f"{pct_text}%"
                    )
            lines.append("")

        if no_marks_students:
            lines.append("Students with no marks listed:")
            lines.append("")
            lines.append("Student | Register Number | Status")
            lines.append("--- | --- | ---")
            for student in no_marks_students:
                lines.append(
                    f"{student.name or 'N/A'} | "
                    f"{student.reg_no or 'N/A'} | "
                    "Mark was not listed"
                )
            lines.append("")

        if not low_performing and not no_marks_students:
            lines.append("No students scored below 60% in any IAT.")

        return "\n".join(lines).rstrip()

    def _handle_mentor_attention_students(self, faculty_id, active_role, query=None):
        """Evidence-based mentee academic attention analysis.

        Mentor scope is resolved by the backend. Each mentee is analyzed against
        the latest semester that contains usable ERP data, so unpublished
        current-semester marks do not make historical academic records disappear.
        """
        if not self._is_mentor_role(active_role):
            return "Access denied: this request requires your Mentor role."

        students = list(self._active_students_for_role(faculty_id, active_role)[:500])
        if not students:
            return "No mentees are mapped to your account."

        text = self._normalize_role_name(query or "")
        attendance_only = "attendance" in text and not any(
            term in text for term in [
                "academic attention", "attention", "low-performing",
                "low performing", "low performer", "marks", "mark",
                "performance", "score", "scores",
            ]
        )
        low_performance_only = any(term in text for term in [
            "low-performing", "low performing", "low performer",
            "low academic", "poor academic", "weak academic",
        ]) and "attendance" not in text and "attention" not in text

        academic_threshold = 50
        attendance_threshold = 75

        def pct(value):
            return f"{value:.2f}".rstrip("0").rstrip(".") if value is not None else "N/A"

        def snapshot_has_attendance(snapshot):
            return bool(sum(row.get("total") or 0 for row in snapshot.get("attendance") or []))

        def attendance_percentage(snapshot):
            attended = sum(row.get("attended") or 0 for row in snapshot.get("attendance") or [])
            total = sum(row.get("total") or 0 for row in snapshot.get("attendance") or [])
            return round(attended * 100 / total, 2) if total else None

        def internal_percentage(snapshot):
            marks = snapshot.get("marks") or []
            obtained = sum(row.get("obtained") or 0 for row in marks)
            maximum = sum(row.get("maximum") or 0 for row in marks)
            return round(obtained * 100 / maximum, 2) if maximum else None

        def result_percentage(snapshot):
            values = [
                row.get("grade_total") for row in snapshot.get("results") or []
                if row.get("grade_total") is not None
            ]
            return round(sum(values) / len(values), 2) if values else None

        def gpa_percentage(snapshot):
            gpa = snapshot.get("gpa") or {}
            value = gpa.get("gpa") if gpa.get("gpa") is not None else gpa.get("cgpa")
            return round(float(value) * 10, 2) if value is not None else None

        def academic_percentage(snapshot):
            for resolver in (result_percentage, internal_percentage, gpa_percentage):
                value = resolver(snapshot)
                if value is not None:
                    return value
            return None

        def latest_attendance_semester(student, current_semester):
            recorded = self._student_recorded_semesters(student)
            candidates = []
            if current_semester is not None:
                candidates.append(current_semester)
            candidates.extend(sem for sem in reversed(recorded) if sem != current_semester)
            seen = set()
            for semester in candidates:
                if semester is None or semester in seen:
                    continue
                seen.add(semester)
                snapshot = self._student_semester_performance_snapshot(student, semester)
                if snapshot_has_attendance(snapshot):
                    return semester, snapshot, semester != current_semester
            return None, None, False

        attention_required = []
        no_concern = []
        data_unavailable = []
        fallback_used = False
        seen_regs = set()

        for student in students:
            reg = str(getattr(student, "reg_no", "") or "").strip()
            if reg in seen_regs:
                continue
            seen_regs.add(reg)

            current_semester = self._semester_number(getattr(student, "semester", None))
            analysis_semester, used_fallback, _reason = self._find_latest_available_semester(
                student, current_semester,
            )
            snapshot = None
            if analysis_semester is not None:
                snapshot = self._student_semester_performance_snapshot(student, analysis_semester)
            elif attendance_only:
                analysis_semester, snapshot, used_fallback = latest_attendance_semester(
                    student, current_semester,
                )

            if not snapshot:
                data_unavailable.append({
                    "student": student,
                    "current_semester": current_semester,
                    "analysis_semester": None,
                    "classification": "academic_data_unavailable",
                    "reason": "No marks, GPA, result, or attendance records are available across recorded semesters.",
                })
                continue

            fallback_used = fallback_used or used_fallback
            academic_value = academic_percentage(snapshot)
            attendance_value = attendance_percentage(snapshot)

            academic_low = academic_value is not None and academic_value < academic_threshold
            attendance_low = attendance_value is not None and attendance_value < attendance_threshold
            has_any_data = academic_value is not None or attendance_value is not None

            if not has_any_data:
                data_unavailable.append({
                    "student": student,
                    "current_semester": current_semester,
                    "analysis_semester": analysis_semester,
                    "classification": "academic_data_unavailable",
                    "reason": "No marks, GPA, result, or attendance records are available for the latest usable semester.",
                })
                continue

            evidence = []
            if academic_value is not None:
                evidence.append(f"aggregate {pct(academic_value)}%")
            else:
                evidence.append("academic marks unavailable")
            if attendance_value is not None:
                evidence.append(f"attendance {pct(attendance_value)}%")
            else:
                evidence.append("attendance unavailable")

            if academic_low and attendance_low:
                classification = "academic_attendance_concern"
                reason = (
                    f"Aggregate performance is {pct(academic_value)}%, below the configured "
                    f"{academic_threshold}% threshold, and attendance is {pct(attendance_value)}%, "
                    f"below the configured {attendance_threshold}% threshold."
                )
            elif academic_low:
                classification = "confirmed_low_performing"
                reason = (
                    f"Aggregate performance is {pct(academic_value)}%, below the configured "
                    f"{academic_threshold}% attention threshold."
                )
            elif attendance_low:
                classification = "attendance_concern"
                reason = (
                    f"Attendance is {pct(attendance_value)}%, below the configured "
                    f"{attendance_threshold}% threshold."
                )
            else:
                classification = "no_immediate_concern"
                reason = "Latest available ERP data shows " + " and ".join(evidence) + "."

            row = {
                "student": student,
                "current_semester": current_semester,
                "analysis_semester": analysis_semester,
                "fallback_used": used_fallback,
                "academic_percentage": academic_value,
                "attendance_percentage": attendance_value,
                "classification": classification,
                "reason": reason,
            }

            if low_performance_only:
                if academic_low:
                    attention_required.append(row)
                elif academic_value is not None:
                    row["reason"] = (
                        f"Aggregate performance is {pct(academic_value)}%, at or above the configured "
                        f"{academic_threshold}% academic threshold."
                    )
                    no_concern.append(row)
                elif attendance_value is not None:
                    row["reason"] = "Attendance data available; academic marks unavailable."
                    no_concern.append(row)
                else:
                    data_unavailable.append(row)
            elif attendance_only:
                if attendance_low:
                    attention_required.append(row)
                elif attendance_value is not None:
                    row["reason"] = (
                        f"Attendance is {pct(attendance_value)}%, at or above the configured "
                        f"{attendance_threshold}% threshold."
                    )
                    no_concern.append(row)
                else:
                    data_unavailable.append(row)
            elif classification == "no_immediate_concern":
                no_concern.append(row)
            else:
                attention_required.append(row)

        attention_required.sort(key=lambda row: (row["student"].name or "", row["student"].id))
        no_concern.sort(key=lambda row: (row["student"].name or "", row["student"].id))
        data_unavailable.sort(key=lambda row: (row["student"].name or "", row["student"].id))

        lines = [
            "**Mentee Academic Attention Report**",
            "",
            f"Total mentees: {len(attention_required) + len(no_concern) + len(data_unavailable)}",
            f"Academic attention required: {len(attention_required)}",
            f"No immediate concern: {len(no_concern)}",
            f"Academic data unavailable: {len(data_unavailable)}",
            "",
            f"Thresholds: aggregate marks below {academic_threshold}% or attendance below {attendance_threshold}%.",
        ]
        if fallback_used:
            lines.extend([
                "",
                "Academic analysis uses each mentee's latest semester with published academic results. Current-semester records were skipped where academic results were not yet published.",
            ])

        if attention_required:
            lines.extend([
                "",
                "---",
                "",
                "**Mentees Requiring Academic Attention**",
                "",
                "Student | Register Number | Analysis Semester | Reason",
                "--- | --- | --- | ---",
            ])
            for row in attention_required:
                student = row["student"]
                semester = row["analysis_semester"]
                lines.append(
                    f"{student.name or 'N/A'} | {student.reg_no or 'N/A'} | "
                    f"Semester {semester if semester is not None else 'N/A'} | {row['reason']}"
                )
        else:
            lines.extend([
                "",
                "No mentees currently meet the configured academic-attention criteria based on the available published ERP data.",
            ])

        if no_concern:
            lines.extend([
                "",
                "---",
                "",
                "**No Immediate Concern**",
                "",
                "Student | Register Number | Analysis Semester | Evidence",
                "--- | --- | --- | ---",
            ])
            for row in no_concern:
                student = row["student"]
                semester = row["analysis_semester"]
                lines.append(
                    f"{student.name or 'N/A'} | {student.reg_no or 'N/A'} | "
                    f"Semester {semester if semester is not None else 'N/A'} | {row['reason']}"
                )

        if data_unavailable:
            lines.extend([
                "",
                "---",
                "",
                "**Academic Data Unavailable**",
                "",
                "Student | Register Number | Status",
                "--- | --- | ---",
            ])
            for row in data_unavailable:
                student = row["student"]
                lines.append(
                    f"{student.name or 'N/A'} | {student.reg_no or 'N/A'} | {row['reason']}"
                )

        return "\n".join(lines).rstrip()

    def _handle_assessment_assistant(self, faculty_id, active_role, query):
        course_code = self._extract_course_code(query)
        if not course_code:
            return "Please include an assigned course code, for example: 'Create 5 questions for CS3501 on recursion'."
        assignment = self._faculty_assignments(faculty_id).filter(
            course__course_code__iexact=course_code
        ).first()
        if not assignment:
            return f"Access denied: {course_code} is not one of your active subject assignments."
        count_match = re.search(r"\b(\d{1,2})\s+questions?\b", query, re.IGNORECASE)
        question_count = min(int(count_match.group(1)), 20) if count_match else 5
        marks_match = re.search(r"\b(\d{1,3})\s*marks?\b", query, re.IGNORECASE)
        marks = int(marks_match.group(1)) if marks_match else 5
        topic_match = re.search(
            r"\b(?:on|about|topic)\s+(.+?)(?:\s+(?:for|with)\s+\d+\s*(?:questions?|marks?)|$)",
            query,
            re.IGNORECASE,
        )
        topic = topic_match.group(1).strip(" .") if topic_match else "the assigned syllabus"
        course = assignment.course
        system_prompt = (
            "You are an assessment-design assistant. Produce faculty-review material only. "
            "Do not claim that generated questions are institution-approved. Return plain text "
            "with numbered questions, marks, Bloom level, a concise answer key, and a rubric."
        )
        user_prompt = (
            f"Course: {course.title or course_code} ({course_code}). Topic: {topic}. "
            f"Create {question_count} questions worth {marks} marks each. Use a useful spread "
            "of Bloom levels and include CO placeholders where an exact CO mapping is unavailable."
        )
        try:
            response = self._ai_client().chat.completions.create(
                model=self._ai_model(),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=self._ai_max_tokens(),
            )
            generated = self._strip_model_reasoning(
                response.choices[0].message.content, preserve_bold=True
            )
            if generated:
                return (
                    f"Assessment Draft | {course_code}\n{generated}\n\n"
                    "Faculty review required before use or publication."
                )
        except Exception:
            pass
        lines = [f"Assessment Draft | {course_code} | Topic: {topic}"]
        for index in range(1, question_count + 1):
            lines.append(
                f"{index}. Draft a {marks}-mark question on {topic} "
                f"(Bloom level: Apply/Analyze; CO mapping: faculty to verify)."
            )
        lines.append("Faculty review required before use or publication.")
        return "\n".join(lines)

    def _set_pending_action(self, state, action):
        if state is None:
            return False
        state["erp_chat_pending_action"] = action
        return True

    def _cancel_pending_action(self, state):
        if state is None or not state.pop("erp_chat_pending_action", None):
            return "There is no pending chatbot action to cancel."
        return "The pending chatbot action was cancelled."

    def _handle_mentor_followup(self, faculty_id, active_role, query, state):
        if not self._is_mentor_role(active_role) and not self._is_ca_role(active_role):
            return "Mentor follow-ups can be recorded only in Mentor or Class Advisor scope."
        faculty = self._get_faculty_info(faculty_id)
        query_lower = query.lower()
        if any(token in query_lower for token in ["show mentor", "list mentor", "pending mentor"]):
            try:
                records = Notification.objects.filter(
                    sender=faculty,
                    receiver=faculty,
                    message__startswith="MENTOR_FOLLOWUP|",
                ).select_related("student")[:50]
                if not records:
                    return "Mentor Follow-ups\nNo saved follow-ups were found."
                lines = ["Mentor Follow-ups"]
                for record in records:
                    fields = self._parse_workflow_message(record.message)
                    status = fields.get("status", "open")
                    if "pending mentor" in query_lower and status == "complete":
                        continue
                    lines.append(
                        f"- {getattr(record.student, 'name', 'N/A')} "
                        f"({getattr(record.student, 'reg_no', 'N/A')}) | "
                        f"Due: {fields.get('due', 'Not scheduled')} | "
                        f"Status: {status.title()} | {fields.get('notes', '')[:160]}"
                    )
                return "\n".join(lines) if len(lines) > 1 else "Mentor Follow-ups\nNo pending follow-ups were found."
            except Exception:
                return "Mentor follow-up history is temporarily unavailable."
        reg_match = re.search(r"\b\d{12}\b", query)
        if not reg_match:
            return "Please include the student's 12-digit registration number and follow-up notes."
        student = self._student_queryset().filter(reg_no=reg_match.group()).first()
        if not self._can_access_workflow_student(faculty_id, active_role, student):
            return "Access denied: this student is not assigned to your active role."
        if any(token in query_lower for token in ["complete", "completed", "close follow-up", "close follow up"]):
            action = {"type": "complete_followup", "student_id": student.id}
            if not self._set_pending_action(state, action):
                return "A session is required to confirm this update. Please use the dashboard chatbot."
            return (
                f"Complete Follow-up Preview\nStudent: {student.name} ({student.reg_no})\n\n"
                "Reply 'confirm' to mark the latest open follow-up complete or 'cancel' to discard."
            )
        notes_match = re.search(r"(?:notes?|about|:)\s*(.+)$", query, re.IGNORECASE)
        notes = notes_match.group(1).strip() if notes_match else ""
        if not notes:
            return "Please add follow-up notes after a colon, for example: 'Record mentor follow-up for 123456789012: Discussed attendance plan'."
        notes = notes.replace("|", "/").replace("\r", " ").replace("\n", " ")
        due_match = re.search(
            r"\b(?:due|next meeting|on)\s+(20\d{2}-\d{2}-\d{2})\b",
            query,
            re.IGNORECASE,
        )
        due_date = due_match.group(1) if due_match else ""
        if due_date:
            try:
                datetime.strptime(due_date, "%Y-%m-%d")
            except ValueError:
                return "The follow-up date is invalid. Use YYYY-MM-DD, for example 2026-07-25."
        action = {
            "type": "mentor_followup",
            "student_id": student.id,
            "notes": notes[:1000],
            "due": due_date,
        }
        if not self._set_pending_action(state, action):
            return "A session is required to confirm and save a mentor follow-up. Please use the dashboard chatbot."
        return (
            f"Mentor Follow-up Preview\nStudent: {student.name} ({student.reg_no})\n"
            f"Notes: {notes[:1000]}\nDue/next meeting: {due_date or 'Not scheduled'}\n\n"
            "Reply 'confirm' to save or 'cancel' to discard."
        )

    def _parse_workflow_message(self, message):
        fields = {}
        for part in str(message or "").split("|")[1:]:
            if "=" in part:
                key, value = part.split("=", 1)
                fields[key] = value
        return fields

    def _draft_student_report(self, student):
        attendance_rows = self._hod_attendance_percentages([student])
        attendance = attendance_rows[0]["percentage"] if attendance_rows else None
        marks = StudentInternalMark.objects.filter(
            student=student,
            marks_obtained__isnull=False,
            max_marks__isnull=False,
        ).aggregate(obtained=Sum("marks_obtained"), maximum=Sum("max_marks"))
        mark_percentage = None
        if marks.get("maximum"):
            mark_percentage = round(
                (marks.get("obtained") or 0) * 100 / marks["maximum"], 2
            )
        concerns = []
        if attendance is not None and attendance < 75:
            concerns.append("attendance intervention")
        if mark_percentage is not None and mark_percentage < 50:
            concerns.append("academic support")
        concern_text = ", ".join(concerns) if concerns else "continued routine monitoring"
        return (
            f"Academic follow-up for {student.name} ({student.reg_no}). "
            f"Recorded attendance: {attendance if attendance is not None else 'N/A'}%. "
            f"Aggregate internal marks: {mark_percentage if mark_percentage is not None else 'N/A'}%. "
            f"Recommended focus: {concern_text}. Faculty verification is required before submission."
        )

    def _report_receiver(self, student, query):
        query_lower = query.lower()
        if "hod" in query_lower:
            try:
                employee_ids = self._approval_user_queryset().filter(
                    Department__Department=getattr(student.department, "Department", None),
                    role__role__iexact="HOD",
                    is_active=True,
                ).values_list("Employee_id", flat=True)
                return general_information.objects.filter(
                    faculty_id__in=list(employee_ids)
                ).first(), "HOD"
            except Exception:
                return None, "HOD"
        return getattr(student, "ca", None), "Class Advisor"

    def _handle_report_workflow(self, faculty_id, active_role, query, state):
        if "report history" in query.lower():
            faculty = self._get_faculty_info(faculty_id)
            if not faculty:
                return "Faculty profile not found."
            try:
                reports = Notification.objects.filter(
                    sender=faculty, message__startswith="FACULTY_REPORT|"
                ).select_related("receiver", "student")[:20]
                if not reports:
                    return "Report History\nNo submitted chatbot reports were found."
                lines = ["Report History"]
                for item in reports:
                    body = item.message.split("|", 1)[-1]
                    lines.append(
                        f"- {item.timestamp:%d-%m-%Y %H:%M} | "
                        f"{getattr(item.student, 'reg_no', 'N/A')} -> "
                        f"{getattr(item.receiver, 'name', 'N/A')}: {body[:120]}"
                    )
                return "\n".join(lines)
            except Exception:
                return "Report history is temporarily unavailable."

        reg_match = re.search(r"\b\d{12}\b", query)
        if not reg_match:
            return "Please include the student's 12-digit registration number."
        student = self._student_queryset().filter(reg_no=reg_match.group()).first()
        if not self._can_access_workflow_student(faculty_id, active_role, student):
            return "Access denied: this student is outside your active role scope."
        if "draft report" in query.lower():
            return (
                "Faculty Report Draft\n"
                + self._draft_student_report(student)
                + "\n\nReview the draft, then use 'Send report for <registration number> to CA/HOD: <final text>'."
            )
        receiver, receiver_role = self._report_receiver(student, query)
        if not receiver:
            return f"No active {receiver_role} recipient is mapped for this student."
        content_match = re.search(r"(?:about|summary|:)\s*(.+)$", query, re.IGNORECASE)
        content = content_match.group(1).strip() if content_match else ""
        if not content:
            return (
                "Please include the report content after a colon, for example: "
                f"'Send report for {student.reg_no} to CA: Attendance intervention required'."
            )
        action = {
            "type": "send_report",
            "student_id": student.id,
            "receiver_id": receiver.id,
            "content": content[:2000],
        }
        if not self._set_pending_action(state, action):
            return "A session is required to confirm report submission. Please use the dashboard chatbot."
        return (
            f"Report Submission Preview\nStudent: {student.name} ({student.reg_no})\n"
            f"Recipient: {receiver.name} ({receiver_role})\nReport: {content[:2000]}\n\n"
            "Reply 'confirm send report' to submit or 'cancel' to discard."
        )

    def _handle_confirmed_action(self, faculty_id, active_role, state):
        if state is None:
            return "There is no dashboard session available for confirmation."
        action = state.get("erp_chat_pending_action")
        if not action:
            return "There is no pending chatbot action to confirm."
        faculty = self._get_faculty_info(faculty_id)
        student = self._student_queryset().filter(pk=action.get("student_id")).first()
        if not faculty or not self._can_access_workflow_student(
            faculty_id, active_role, student
        ):
            state.pop("erp_chat_pending_action", None)
            return "The action was cancelled because its authorization scope is no longer valid."
        try:
            if action.get("type") == "mentor_followup":
                Notification.objects.create(
                    sender=faculty,
                    receiver=faculty,
                    student=student,
                    message=(
                        f"MENTOR_FOLLOWUP|due={action.get('due', '')}|"
                        f"status=open|notes={action['notes']}"
                    ),
                )
                result = f"Mentor follow-up saved for {student.name} ({student.reg_no})."
            elif action.get("type") == "complete_followup":
                record = Notification.objects.filter(
                    sender=faculty,
                    receiver=faculty,
                    student=student,
                    message__startswith="MENTOR_FOLLOWUP|",
                ).order_by("-timestamp").first()
                if not record:
                    state.pop("erp_chat_pending_action", None)
                    return "No saved mentor follow-up was found for this student."
                fields = self._parse_workflow_message(record.message)
                record.message = (
                    f"MENTOR_FOLLOWUP|due={fields.get('due', '')}|status=complete|"
                    f"notes={fields.get('notes', '')}"
                )
                record.save(update_fields=["message"])
                result = f"Latest mentor follow-up marked complete for {student.name} ({student.reg_no})."
            elif action.get("type") == "send_report":
                receiver = general_information.objects.filter(
                    pk=action.get("receiver_id")
                ).first()
                if not receiver:
                    state.pop("erp_chat_pending_action", None)
                    return "The report recipient is no longer available; nothing was submitted."
                Notification.objects.create(
                    sender=faculty,
                    receiver=receiver,
                    student=student,
                    message=f"FACULTY_REPORT|{action['content']}",
                )
                result = f"Report submitted to {receiver.name} for {student.name} ({student.reg_no})."
            else:
                return "The pending action type is not supported."
        except Exception:
            return "The action could not be saved. Please verify that the chatbot notification table is available."
        state.pop("erp_chat_pending_action", None)
        return result

    def _handle_send_report(self, faculty_id, query, active_role=None):
        return self._handle_report_workflow(
            faculty_id, active_role, query, self.conversation_state
        )


@receiver(user_logged_out)
def _cleanup_chatbot_state_on_logout(sender, request, user, **kwargs):
    try:
        ERPBot().clear_chatbot_logout_state(request=request, user=user)
    except Exception:
        pass
