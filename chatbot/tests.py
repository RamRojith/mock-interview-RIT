import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, SimpleTestCase, override_settings

from .views import _all_roles, _resolve_effective_role, chat, history, questions
from .chatbot_logic import ERPBot
from .question_catalog import build_question_groups
from .student_prompts import (
    STUDENT_OVERALL_PERFORMANCE_SYSTEM_PROMPT,
    STUDENT_PERFORMANCE_SYSTEM_PROMPT,
)


class ChatAuthenticationTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _request(self, method, path, user, payload=None):
        request_method = getattr(self.factory, method.lower())
        kwargs = {}
        if payload is not None:
            kwargs.update(data=json.dumps(payload), content_type="application/json")
        request = request_method(path, **kwargs)
        SessionMiddleware(lambda req: None).process_request(request)
        request.user = user
        return request

    @staticmethod
    def _faculty():
        return SimpleNamespace(
            is_authenticated=True,
            is_student=False,
            is_parent=False,
            is_superuser=False,
            Employee_id="101",
            role=SimpleNamespace(role="Faculty"),
        )

    @staticmethod
    def _admin():
        return SimpleNamespace(
            is_authenticated=True,
            is_student=False,
            is_parent=False,
            is_superuser=True,
            Employee_id="0000",
            role=None,
        )

    def test_chat_rejects_non_faculty(self):
        user = SimpleNamespace(is_authenticated=False)
        request = self._request("post", "/chatbot/api/chat/", user, {"query": "hello"})
        self.assertEqual(chat(request).status_code, 403)

    def test_chat_uses_server_side_identity_and_records_history(self):
        request = self._request(
            "post", "/chatbot/api/chat/", self._faculty(), {"query": "my students"}
        )

        with patch("chatbot.views._all_roles", return_value=["Faculty"]), patch(
            "chatbot.views.ERPBot.process_query", return_value="Scoped response"
        ) as process_query:
            response = chat(request)

        self.assertEqual(response.status_code, 200)
        process_query.assert_called_once_with(
            "my students",
            "101",
            role="Faculty",
            all_roles=["Faculty"],
            is_first_message=True,
        )
        self.assertEqual(len(request.session["erp_chat_history"]), 2)

    def test_admin_gets_server_side_full_access_role(self):
        request = self._request(
            "post", "/chatbot/api/chat/", self._admin(), {"query": "list students"}
        )

        with patch("chatbot.views._all_roles", return_value=["Admin"]), patch(
            "chatbot.views.ERPBot.process_query", return_value="Institution-wide response"
        ) as process_query:
            response = chat(request)

        self.assertEqual(response.status_code, 200)
        process_query.assert_called_once_with(
            "list students",
            "0000",
            role="Admin",
            all_roles=["Admin"],
            is_first_message=True,
        )

    def test_employee_0000_uses_existing_admin_rule(self):
        admin = self._admin()
        admin.is_superuser = False
        request = self._request("get", "/chatbot/api/history/", admin)

        self.assertEqual(history(request).status_code, 200)

    def test_authenticated_non_faculty_employee_can_open_chatbot(self):
        employee = self._faculty()
        employee.Employee_id = "415"
        employee.role = SimpleNamespace(role="Office Assistant")
        request = self._request("get", "/chatbot/api/history/", employee)

        self.assertEqual(history(request).status_code, 200)

    def test_admin_portal_session_keeps_full_access_when_switching_employee_role(self):
        switched_user = self._faculty()
        switched_user.Employee_id = "205"
        request = self._request(
            "post", "/chatbot/api/chat/", switched_user, {"query": "list students"}
        )
        request.session["app_name"] = "Admin Portal"

        with patch("chatbot.views._all_roles", return_value=["Admin"]), patch(
            "chatbot.views.ERPBot.process_query", return_value="Institution-wide response"
        ) as process_query:
            response = chat(request)

        self.assertEqual(response.status_code, 200)
        process_query.assert_called_once_with(
            "list students",
            "205",
            role="Admin",
            all_roles=["Admin"],
            is_first_message=True,
        )

    def test_hod_role_takes_precedence_for_multi_role_employee(self):
        self.assertEqual(
            _resolve_effective_role("Faculty", ["Faculty", "Mentor", "HOD"]),
            "HOD",
        )

    def test_subject_teacher_role_alias_resolves_to_faculty_scope(self):
        self.assertEqual(
            _resolve_effective_role("Subject Teacher", ["Subject Teacher"]),
            "Faculty",
        )

    def test_all_roles_includes_academic_ca_and_mentor_assignments(self):
        approval_roles = MagicMock()
        approval_roles.exclude.return_value.values_list.return_value.distinct.return_value = [
            "Faculty"
        ]
        approval_users = MagicMock()
        approval_users.using.return_value.filter.return_value = approval_roles

        faculty = SimpleNamespace(id=5, faculty_id="1603")
        active_students = MagicMock()
        active_students.filter.side_effect = [
            MagicMock(exists=MagicMock(return_value=True)),
            MagicMock(exists=MagicMock(return_value=True)),
        ]
        student_manager = MagicMock()
        student_manager.filter.return_value = active_students

        subject_assignments = MagicMock()
        subject_assignments.exists.return_value = True

        with patch("chatbot.views.USER.objects", approval_users), patch(
            "chatbot.views.general_information.objects.filter"
        ) as faculty_filter, patch(
            "chatbot.views.StudentDetails.objects", student_manager
        ), patch(
            "chatbot.views.AssignSubjectFaculty.objects.filter",
            return_value=subject_assignments,
        ):
            faculty_filter.return_value.first.return_value = faculty
            roles = _all_roles("1603", "Faculty")

        self.assertEqual(roles, ["Faculty", "Class Advisor", "Mentor"])

    def test_student_uses_self_scoped_student_router(self):
        student = SimpleNamespace(
            is_authenticated=True,
            is_student=True,
            is_parent=False,
            is_superuser=False,
            Employee_id="921000000001",
            role=SimpleNamespace(role="Student"),
        )
        request = self._request("post", "/chatbot/api/chat/", student, {"query": "hello"})
        request.session["employee_id"] = student.Employee_id
        with patch("chatbot.views.ERPBot.process_query", return_value="Student response") as process_query:
            response = chat(request)

        self.assertEqual(response.status_code, 200)
        process_query.assert_called_once_with(
            "hello",
            student.Employee_id,
            role="Student",
            all_roles=["Student"],
            is_first_message=True,
        )

    def test_parent_remains_unauthorized(self):
        parent = SimpleNamespace(
            is_authenticated=True,
            is_student=False,
            is_parent=True,
            is_superuser=False,
            Employee_id="P100",
            role=SimpleNamespace(role="Parent"),
        )
        request = self._request("post", "/chatbot/api/chat/", parent, {"query": "hello"})
        self.assertEqual(chat(request).status_code, 403)

    def test_questions_reject_unauthenticated_users(self):
        request = self._request(
            "get", "/chatbot/api/questions/", SimpleNamespace(is_authenticated=False)
        )
        self.assertEqual(questions(request).status_code, 403)

    def test_questions_returns_only_verified_employee_role_groups(self):
        request = self._request("get", "/chatbot/api/questions/", self._faculty())
        with patch(
            "chatbot.views._all_roles",
            return_value=["Faculty", "Class Advisor", "Mentor"],
        ):
            response = questions(request)

        payload = json.loads(response.content)
        titles = [group["title"] for group in payload["groups"]]
        self.assertEqual(
            titles,
            ["Common", "Subject Faculty", "Class Advisor", "Mentor"],
        )
        self.assertNotIn("Head of Department", titles)
        self.assertNotIn("Administrator", titles)

    def test_questions_keeps_student_catalog_separate(self):
        student = SimpleNamespace(
            is_authenticated=True,
            is_student=True,
            is_parent=False,
            is_superuser=False,
            Employee_id="921000000001",
            role=SimpleNamespace(role="Student"),
        )
        request = self._request("get", "/chatbot/api/questions/", student)
        response = questions(request)

        payload = json.loads(response.content)
        titles = [group["title"] for group in payload["groups"]]
        self.assertIn("Subjects and timetable", titles)
        self.assertIn("Performance analysis", titles)
        self.assertNotIn("Common", titles)
        self.assertNotIn("Subject Faculty", titles)

    def test_question_catalog_canonicalizes_roles_and_removes_duplicates(self):
        groups = build_question_groups(
            ["Subject Teacher", "Faculty", "CA", "Class Advisor"]
        )
        titles = [group["title"] for group in groups]
        all_questions = [
            question for group in groups for question in group["questions"]
        ]
        self.assertEqual(titles, ["Common", "Subject Faculty", "Class Advisor"])
        self.assertEqual(len(all_questions), len({item.casefold() for item in all_questions}))

    def test_history_clear_removes_only_chat_state(self):
        request = self._request("delete", "/chatbot/api/history/", self._faculty())
        request.session.update({
            "employee_id": "101",
            "erp_chat_history": [{"role": "user", "content": "hello"}],
            "chatbot_greeted_101": True,
            "unrelated": "keep",
        })

        response = history(request)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("erp_chat_history", request.session)
        self.assertNotIn("chatbot_greeted_101", request.session)
        self.assertEqual(request.session["unrelated"], "keep")


class RoleStudentRoutingTests(SimpleTestCase):
    def setUp(self):
        self.bot = ERPBot()

    def test_hod_my_students_uses_department_list_not_ca_lookup(self):
        with patch.object(
            self.bot, "_handle_list_students", return_value="department students"
        ) as department_list, patch.object(self.bot, "_handle_my_students") as ca_list:
            result = self.bot._handle_role_scoped_student_list("301", "HOD", "show my students")

        self.assertEqual(result, "department students")
        department_list.assert_called_once_with(
            "301", "HOD", target_dept=None, target_batch=None
        )
        ca_list.assert_not_called()

    def test_class_advisor_my_students_uses_ca_mapping(self):
        with patch.object(
            self.bot, "_handle_my_students", return_value="assigned class"
        ) as ca_list, patch.object(self.bot, "_handle_list_students") as broad_list:
            result = self.bot._handle_role_scoped_student_list(
                "302", "Class Advisor", "show my students"
            )

        self.assertEqual(result, "assigned class")
        ca_list.assert_called_once_with(
            "302", relations={"ca"}, target_dept=None, target_batch=None
        )
        broad_list.assert_not_called()

    def test_subject_faculty_my_students_uses_subject_scope(self):
        with patch.object(
            self.bot, "_handle_list_students", return_value="enrolled students"
        ) as subject_list, patch.object(self.bot, "_handle_my_students") as ca_list:
            result = self.bot._handle_role_scoped_student_list(
                "303", "Faculty", "show my students"
            )

        self.assertEqual(result, "enrolled students")
        subject_list.assert_called_once_with(
            "303",
            "Faculty",
            target_dept=None,
            target_batch=None,
            target_course_code=None,
        )
        ca_list.assert_not_called()

    def test_hod_student_access_is_limited_to_department_fk(self):
        own_department = SimpleNamespace(id=7, Department="CSE")
        other_department = SimpleNamespace(id=8, Department="ECE")
        faculty = SimpleNamespace(department=own_department)

        self.assertTrue(
            self.bot._has_student_access(
                "301", faculty, SimpleNamespace(department=own_department), "HOD"
            )
        )
        self.assertFalse(
            self.bot._has_student_access(
                "301", faculty, SimpleNamespace(department=other_department), "HOD"
            )
        )

    def test_multi_role_hod_mentor_intent_uses_mentor_mapping(self):
        faculty = SimpleNamespace(
            name="HOD", department=SimpleNamespace(id=7, Department="CSE")
        )
        with patch.object(self.bot, "_get_faculty_info", return_value=faculty), patch.object(
            self.bot, "_extract_department", return_value=None
        ), patch.object(
            self.bot, "_handle_list_students", return_value="department students"
        ) as department_list, patch.object(self.bot, "_handle_my_students") as mentor_list:
            result = self.bot.process_query(
                "show mentor students", "301", role="HOD", all_roles=["HOD", "Mentor"]
            )

        self.assertEqual(result, mentor_list.return_value)
        mentor_list.assert_called_once_with(
            "301", relations={"mentor"}, target_dept=None, target_batch=None
        )
        department_list.assert_not_called()

    def test_multi_role_mentee_query_uses_only_mentor_scope(self):
        faculty = SimpleNamespace(name="Teacher")
        with patch.object(self.bot, "_get_faculty_info", return_value=faculty), patch.object(
            self.bot, "_extract_department", return_value=None
        ), patch.object(
            self.bot, "_handle_my_students", return_value="assigned mentees"
        ) as student_list:
            result = self.bot.process_query(
                "List my mentees.",
                "302",
                role="Class Advisor",
                all_roles=["Class Advisor", "Mentor"],
            )

        self.assertEqual(result, "assigned mentees")
        student_list.assert_called_once_with(
            "302", relations={"mentor"}, target_dept=None, target_batch=None
        )

    def test_multi_role_generic_students_requires_role_clarification(self):
        faculty = SimpleNamespace(name="Teacher")
        with patch.object(self.bot, "_get_faculty_info", return_value=faculty), patch.object(
            self.bot, "_handle_role_scoped_student_list"
        ) as student_list:
            result = self.bot.process_query(
                "Show my students.",
                "302",
                role="Class Advisor",
                all_roles=["Class Advisor", "Mentor"],
            )

        self.assertIn("Please specify which role", result)
        student_list.assert_not_called()

    def test_subject_student_query_uses_subject_faculty_scope(self):
        faculty = SimpleNamespace(name="Teacher")
        with patch.object(self.bot, "_get_faculty_info", return_value=faculty), patch.object(
            self.bot, "_extract_department", return_value=None
        ), patch.object(
            self.bot, "_handle_list_students", return_value="subject enrollment"
        ) as student_list:
            result = self.bot.process_query(
                "Students taking AD3491.",
                "302",
                role="Class Advisor",
                all_roles=["Class Advisor", "Mentor", "Subject Faculty"],
            )

        self.assertEqual(result, "subject enrollment")
        student_list.assert_called_once_with(
            "302",
            "Faculty",
            target_dept=None,
            target_batch=None,
            target_course_code="AD3491",
        )

    def test_required_student_phrases_map_to_their_roles(self):
        expected_roles = {
            "Show my mentees.": "Mentor",
            "Who are my mentees?": "Mentor",
            "My mentor students": "Mentor",
            "Students under my mentorship": "Mentor",
            "Show my class.": "Class Advisor",
            "List my class students.": "Class Advisor",
            "Show my CA students.": "Class Advisor",
            "List subject students.": "Faculty",
            "Show students for my subject.": "Faculty",
            "Show my department students.": "HOD",
        }
        for query, expected_role in expected_roles.items():
            with self.subTest(query=query):
                self.assertEqual(self.bot._student_list_role_hint(query), expected_role)

    def test_unassigned_requested_role_is_denied(self):
        faculty = SimpleNamespace(name="Teacher")
        with patch.object(self.bot, "_get_faculty_info", return_value=faculty), patch.object(
            self.bot, "_handle_role_scoped_student_list"
        ) as student_list:
            result = self.bot.process_query(
                "Who are my mentees?",
                "302",
                role="Class Advisor",
                all_roles=["Class Advisor"],
            )

        self.assertIn("requires your Mentor role", result)
        student_list.assert_not_called()

    def test_hod_analytics_are_routed_before_generic_student_list(self):
        faculty = SimpleNamespace(
            name="HOD", department=SimpleNamespace(id=7, Department="CSE")
        )
        with patch.object(self.bot, "_get_faculty_info", return_value=faculty), patch.object(
            self.bot, "_extract_department", return_value=None
        ), patch.object(
            self.bot,
            "_handle_hod_attendance_analytics",
            return_value="department attendance",
        ) as attendance, patch.object(self.bot, "_handle_list_students") as student_list:
            result = self.bot.process_query(
                "list students with attendance below 75%", "301", role="HOD"
            )

        self.assertEqual(result, "department attendance")
        attendance.assert_called_once_with("301", 75)
        student_list.assert_not_called()

    def test_hod_different_department_request_is_denied(self):
        own_department = SimpleNamespace(id=7, Department="CSE")
        other_department = SimpleNamespace(id=8, Department="ECE")
        faculty = SimpleNamespace(name="HOD", department=own_department)
        with patch.object(self.bot, "_get_faculty_info", return_value=faculty), patch.object(
            self.bot, "_extract_department", return_value=other_department
        ):
            result = self.bot._route_hod_department_query(
                "301", "show ECE department performance"
            )

        self.assertEqual(
            result, "Access denied: HOD access is limited to your mapped department."
        )


class EndSemesterResultTests(SimpleTestCase):
    def setUp(self):
        self.bot = ERPBot()

    def test_student_profile_is_resolved_from_authenticated_register_number(self):
        student = SimpleNamespace(
            name="Test Student",
            reg_no="921000000001",
            department=SimpleNamespace(Department="AI AND DS"),
            batch="2024",
            year="2",
            semester="4",
            section="A",
        )
        student_queryset = MagicMock()
        student_queryset.filter.return_value.first.return_value = student
        with patch.object(self.bot, "_student_queryset", return_value=student_queryset):
            response = self.bot.process_query(
                "Show my profile",
                "921000000001",
                role="Student",
                all_roles=["Student"],
            )

        self.assertIn("Test Student", response)
        self.assertIn("921000000001", response)
        student_queryset.filter.assert_called_once_with(
            reg_no="921000000001",
            is_active=True,
            is_discontinued=False,
        )

    def test_student_cannot_query_another_register_number(self):
        student = SimpleNamespace(name="Test Student", reg_no="921000000001")
        student_queryset = MagicMock()
        student_queryset.filter.return_value.first.return_value = student
        with patch.object(self.bot, "_student_queryset", return_value=student_queryset):
            response = self.bot.process_query(
                "Show marks for 921000000002",
                "921000000001",
                role="Student",
                all_roles=["Student"],
            )

        self.assertIn("only their own academic information", response)

    def test_student_subjects_default_to_profile_current_semester(self):
        student = SimpleNamespace(name="Test Student", reg_no="921000000001", semester="4")
        student_queryset = MagicMock()
        student_queryset.filter.return_value.first.return_value = student
        rows = [{"course__course_code": "AD3491", "course__title": "Data Science"}]
        with patch.object(self.bot, "_student_queryset", return_value=student_queryset), patch.object(
            self.bot,
            "_get_student_subject_enrollments",
            return_value=(rows, "2025-2026"),
        ) as subject_enrollments:
            response = self.bot.process_query(
                "Show my subjects",
                "921000000001",
                role="Student",
                all_roles=["Student"],
            )

        subject_enrollments.assert_called_once_with(student, 4)
        self.assertIn("Current Semester Subjects (Semester 4)", response)
        self.assertIn("AD3491", response)

    def test_explicit_historical_semester_overrides_current_semester(self):
        student = SimpleNamespace(name="Test Student", reg_no="921000000001", semester="6")
        student_queryset = MagicMock()
        student_queryset.filter.return_value.first.return_value = student
        rows = [{"course__course_code": "MA3251", "course__title": "Statistics"}]
        with patch.object(self.bot, "_student_queryset", return_value=student_queryset), patch.object(
            self.bot,
            "_get_student_subject_enrollments",
            return_value=(rows, "2023-2024"),
        ) as subject_enrollments:
            response = self.bot.process_query(
                "What subjects did I have in Semester 2?",
                "921000000001",
                role="Student",
                all_roles=["Student"],
            )

        subject_enrollments.assert_called_once_with(student, 2)
        self.assertIn("My Semester 2 Subjects", response)
        self.assertNotIn("Semester 6", response)

    def test_subject_query_requires_verified_current_semester(self):
        student = SimpleNamespace(name="Test Student", reg_no="921000000001", semester=None)
        student_queryset = MagicMock()
        student_queryset.filter.return_value.first.return_value = student
        with patch.object(self.bot, "_student_queryset", return_value=student_queryset), patch.object(
            self.bot, "_get_student_subject_enrollments"
        ) as subject_enrollments:
            response = self.bot.process_query(
                "List my courses",
                "921000000001",
                role="Student",
                all_roles=["Student"],
            )

        self.assertIn("current semester is not assigned", response)
        subject_enrollments.assert_not_called()

    def test_semester_intent_extraction_supports_required_phrases(self):
        examples = {
            "Show my Semester 1 subjects": 1,
            "List Semester 3 subjects": 3,
            "Show subjects from Semester 5": 5,
            "Display my Semester 7 courses": 7,
            "What did I study in 2nd semester?": 2,
            "Show IAT marks for 3rd sem": 3,
            "Show my subjects": None,
        }
        for query, expected in examples.items():
            with self.subTest(query=query):
                self.assertEqual(self.bot._extract_student_subject_semester(query), expected)

    def test_student_iat_marks_use_explicit_historical_semester(self):
        student = SimpleNamespace(name="Test Student", reg_no="921000000001", semester="4")
        student_queryset = MagicMock()
        student_queryset.filter.return_value.first.return_value = student
        rows = [
            {"course_code": "AD3491", "course__title": "Data Science", "exam_name": "IAT1", "obtained": 35, "maximum": 50},
            {"course_code": "AD3491", "course__title": "Data Science", "exam_name": "IAT 2", "obtained": 40, "maximum": 50},
            {"course_code": "AD3491", "course__title": "Data Science", "exam_name": "Model Exam", "obtained": 80, "maximum": 100},
        ]
        with patch.object(self.bot, "_student_queryset", return_value=student_queryset), patch.object(
            self.bot, "_get_student_subject_enrollments", return_value=([], "2024-2025")
        ) as enrollments, patch.object(
            self.bot, "_get_student_internal_mark_rows", return_value=rows
        ) as mark_rows:
            response = self.bot.process_query(
                "Show my IAT marks for 3rd sem",
                student.reg_no,
                role="Student",
                all_roles=["Student"],
            )

        enrollments.assert_called_once_with(student, 3)
        mark_rows.assert_called_once_with(
            student, 3, academic_year="2024-2025", course_code=None
        )
        self.assertIn("My Internal Marks | Semester 3", response)
        self.assertIn("IAT1", response)
        self.assertIn("IAT 2", response)
        self.assertNotIn("Model Exam", response)
        self.assertNotIn("Semester 4", response)

    def test_student_iat_marks_default_to_current_semester(self):
        student = SimpleNamespace(name="Test Student", reg_no="921000000001", semester="4")
        student_queryset = MagicMock()
        student_queryset.filter.return_value.first.return_value = student
        rows = [
            {"course_code": "AD3491", "course__title": "Data Science", "exam_name": "IAT1", "obtained": 35, "maximum": 50},
        ]
        with patch.object(self.bot, "_student_queryset", return_value=student_queryset), patch.object(
            self.bot, "_get_student_subject_enrollments", return_value=([], "2025-2026")
        ), patch.object(
            self.bot, "_get_student_internal_mark_rows", return_value=rows
        ) as mark_rows:
            response = self.bot.process_query(
                "Show my IAT 1 marks",
                student.reg_no,
                role="Student",
                all_roles=["Student"],
            )

        mark_rows.assert_called_once_with(
            student, 4, academic_year="2025-2026", course_code=None
        )
        self.assertIn("Current Semester 4", response)

    def test_student_can_request_iat_one_and_two_together(self):
        assessments = self.bot._extract_student_assessments(
            "Show my IAT 1 and IAT 2 marks"
        )
        self.assertEqual(assessments, {"iat1", "iat2"})

    def test_iat_or_choices_are_counted_once_for_hundred_mark_total(self):
        details = []
        row_id = 1
        mandatory_scores = [2, 1, 2, 2, 1, 2, 2, 2, 1, 0]
        for question, score in enumerate(mandatory_scores, start=1):
            details.append({
                "id": row_id, "course_code": "AD3491", "course__title": "Data Science",
                "exam_name": "IAT1", "part_name": "A", "question_number": str(question),
                "sub_question": None, "option_letter": None, "max_marks": 2,
                "marks_obtained": score,
            })
            row_id += 1
        for question, score in zip(range(11, 16), [9, 10, 6, 6, 4]):
            for option in ["a", "b"]:
                details.append({
                    "id": row_id, "course_code": "AD3491", "course__title": "Data Science",
                    "exam_name": "IAT1", "part_name": "B", "question_number": str(question),
                    "sub_question": "i", "option_letter": option, "max_marks": 13,
                    "marks_obtained": score if option == "a" else None,
                })
                row_id += 1
        for option, maxima, scores in [
            ("a", [8, 7], [5, 5]),
            ("b", [7, 8], [None, None]),
        ]:
            for sub_question, maximum, score in zip(["i", "ii"], maxima, scores):
                details.append({
                    "id": row_id, "course_code": "AD3491", "course__title": "Data Science",
                    "exam_name": "IAT1", "part_name": "C", "question_number": "16",
                    "sub_question": sub_question, "option_letter": option,
                    "max_marks": maximum, "marks_obtained": score,
                })
                row_id += 1

        result = self.bot._aggregate_student_mark_details(details)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["maximum"], 100)
        self.assertEqual(result[0]["obtained"], 60)

    def test_student_timetable_is_scoped_to_profile_department_semester_and_section(self):
        department = SimpleNamespace(id=7, Department="AI AND DS")
        student = SimpleNamespace(department=department, semester="4", section="A")
        monday = SimpleNamespace(
            day="Monday",
            first_period="AD3491",
            second_period=None,
            third_period=None,
            fourth_period=None,
            fifth_period=None,
            sixth_period=None,
            seventh_period=None,
            eighth_period=None,
            nineth_period=None,
            tenth_period=None,
        )
        allocations = MagicMock()
        allocations.filter.return_value = [monday]
        courses = MagicMock()
        courses.values_list.return_value = [("AD3491", "Data Science")]
        with patch("chatbot.chatbot_logic.PeriodAllocation.objects.filter", return_value=allocations) as period_filter, patch(
            "chatbot.chatbot_logic.Course.objects.filter", return_value=courses
        ):
            response = self.bot._handle_student_timetable(student, "show monday timetable")

        period_filter.assert_called_once_with(
            department=department,
            semester__iexact="4",
            section__iexact="A",
        )
        allocations.filter.assert_called_once_with(day__iexact="Monday")
        self.assertIn("P1: AD3491 - Data Science", response)

    def test_attendance_projection_reports_recovery_and_safe_absences(self):
        self.assertEqual(self.bot._attendance_projection(50, 100), (100, 0))
        self.assertEqual(self.bot._attendance_projection(80, 100), (0, 6))

    def test_student_profile_includes_advisor_and_mentor(self):
        student = SimpleNamespace(
            name="Test Student",
            reg_no="921000000001",
            department=SimpleNamespace(Department="AI AND DS"),
            batch="2024",
            year="2",
            semester="4",
            section="A",
            email="student@example.edu",
            mobile_no="9000000000",
            ca=SimpleNamespace(name="Advisor Name", college_email="advisor@example.edu"),
            mentor=SimpleNamespace(name="Mentor Name", college_email="mentor@example.edu"),
        )
        student_queryset = MagicMock()
        student_queryset.filter.return_value.first.return_value = student
        with patch.object(self.bot, "_student_queryset", return_value=student_queryset):
            response = self.bot.process_query(
                "Who is my mentor?",
                student.reg_no,
                role="Student",
                all_roles=["Student"],
            )

        self.assertIn("Class Advisor: Advisor Name", response)
        self.assertIn("Mentor: Mentor Name", response)

    def test_student_academic_overview_intent_uses_student_handler(self):
        student = SimpleNamespace(name="Test Student", reg_no="921000000001")
        student_queryset = MagicMock()
        student_queryset.filter.return_value.first.return_value = student
        with patch.object(self.bot, "_student_queryset", return_value=student_queryset), patch.object(
            self.bot, "_handle_student_academic_overview", return_value="overview"
        ) as overview:
            response = self.bot.process_query(
                "Show my academic overview",
                student.reg_no,
                role="Student",
                all_roles=["Student"],
            )

        self.assertEqual(response, "overview")
        overview.assert_called_once_with(student, "show my academic overview")

    def test_student_performance_intent_uses_student_handler(self):
        student = SimpleNamespace(name="Test Student", reg_no="921000000001")
        student_queryset = MagicMock()
        student_queryset.filter.return_value.first.return_value = student
        with patch.object(self.bot, "_student_queryset", return_value=student_queryset), patch.object(
            self.bot, "_handle_student_performance_insights", return_value="insights"
        ) as insights:
            response = self.bot.process_query(
                "Which is my weakest subject?",
                student.reg_no,
                role="Student",
                all_roles=["Student"],
            )

        self.assertEqual(response, "insights")
        insights.assert_called_once_with(student, "which is my weakest subject?")

    def test_productivity_attendance_phrase_uses_attendance_handler(self):
        student = SimpleNamespace(name="Test Student", reg_no="921000000001")
        student_queryset = MagicMock()
        student_queryset.filter.return_value.first.return_value = student
        with patch.object(self.bot, "_student_queryset", return_value=student_queryset), patch.object(
            self.bot, "_handle_student_attendance", return_value="attendance projection"
        ) as attendance:
            response = self.bot.process_query(
                "How many classes can I miss?",
                student.reg_no,
                role="Student",
                all_roles=["Student"],
            )

        self.assertEqual(response, "attendance projection")
        attendance.assert_called_once_with(student, "how many classes can i miss?")

    @override_settings(
        OLLAMA_BASE_URL="http://ollama.example.test:11434/v1",
        OLLAMA_MODEL="shared-model",
    )
    def test_student_performance_uses_separate_prompt_and_shared_ai_settings(self):
        student = SimpleNamespace(name="Test Student", semester="4")
        mark_rows = [
            {"course_code": "AD3491", "course__title": "Data Science", "percentage": 80},
            {"course_code": "MA3391", "course__title": "Statistics", "percentage": 55},
        ]
        attendance_rows = [
            {"course__course_code": "AD3491", "course__title": "Data Science", "attended": 8, "total": 10},
        ]
        ai_text = """**My AI Performance Analysis | Semester 4**

**Overall Assessment**
1. Recorded performance is developing.

**Strengths**
1. Data Science is currently strongest.

**Areas Needing Attention**
1. Statistics needs additional practice.

**Action Plan**
1. Revise Statistics topics weekly.

**Department-Related Project Ideas**
1. Build a small analytics dashboard.

**Extracurricular Development**
1. Join a technical club or project showcase.

**Attendance Guidance**
1. Maintain the recorded attendance level.

**Data Note**
1. This analysis uses only currently recorded ERP data; unpublished assessments are not included."""
        client = MagicMock()
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=ai_text))]
        )
        gpa_query = MagicMock()
        gpa_query.order_by.return_value.values.return_value.first.return_value = None
        with patch.object(
            self.bot, "_get_student_subject_enrollments", return_value=([], "2025-2026")
        ), patch.object(
            self.bot, "_student_mark_performance_rows", return_value=mark_rows
        ), patch.object(
            self.bot, "_student_hour_attendance_rows", return_value=attendance_rows
        ), patch.object(
            self.bot, "_ai_client", return_value=client
        ), patch("chatbot.chatbot_logic.GPA.objects.filter", return_value=gpa_query):
            response = self.bot._handle_student_performance_insights(
                student, "analyze my performance in semester 4"
            )

        self.assertEqual(response, ai_text)
        call = client.chat.completions.create.call_args.kwargs
        self.assertEqual(call["model"], "shared-model")
        self.assertIn("student-facing academic performance coach", call["messages"][0]["content"])
        self.assertNotIn("strict Academic Performance Analyzer", call["messages"][0]["content"])
        self.assertEqual(self.bot._ai_model(), "shared-model")

    def test_invalid_student_ai_response_uses_calculated_fallback(self):
        student = SimpleNamespace(name="Test Student", semester="4")
        mark_rows = [
            {"course_code": "AD3491", "course__title": "Data Science", "percentage": 80},
        ]
        client = MagicMock()
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="invalid response"))]
        )
        gpa_query = MagicMock()
        gpa_query.order_by.return_value.values.return_value.first.return_value = None
        with patch.object(
            self.bot, "_get_student_subject_enrollments", return_value=([], None)
        ), patch.object(
            self.bot, "_student_mark_performance_rows", return_value=mark_rows
        ), patch.object(
            self.bot, "_student_hour_attendance_rows", return_value=[]
        ), patch.object(
            self.bot, "_ai_client", return_value=client
        ), patch("chatbot.chatbot_logic.GPA.objects.filter", return_value=gpa_query):
            response = self.bot._handle_student_performance_insights(
                student, "analyze my performance in semester 4"
            )

        self.assertTrue(response.startswith("**My Performance Insights | Semester 4**"))
        self.assertIn("**Recorded subject average:** 80.0%", response)
        self.assertIn("**Department-Related Project Ideas**", response)
        self.assertIn("**Extracurricular Development**", response)
        self.assertIn("1. Build a small", response)

    def test_student_prompt_is_kept_in_separate_template_module(self):
        self.assertIn("SCOPE AND SECURITY", STUDENT_PERFORMANCE_SYSTEM_PROMPT)
        self.assertIn("authenticated student's selected-semester data", STUDENT_PERFORMANCE_SYSTEM_PROMPT)
        self.assertIn("**Department-Related Project Ideas**", STUDENT_PERFORMANCE_SYSTEM_PROMPT)
        self.assertIn("**Extracurricular Development**", STUDENT_PERFORMANCE_SYSTEM_PROMPT)
        self.assertIn("cumulative academic data", STUDENT_OVERALL_PERFORMANCE_SYSTEM_PROMPT)
        self.assertIn("**Academic Trends and Consistency**", STUDENT_OVERALL_PERFORMANCE_SYSTEM_PROMPT)

    @override_settings(
        OLLAMA_BASE_URL="http://ollama.example.test:11434/v1",
        OLLAMA_MODEL="shared-model",
    )
    def test_ai_client_uses_shared_base_url(self):
        with patch("chatbot.chatbot_logic.OpenAI") as openai:
            self.bot._ai_client()

        openai.assert_called_once_with(
            api_key="ollama",
            base_url="http://ollama.example.test:11434/v1",
            timeout=180.0,
        )

    def test_performance_analysis_explicit_semester_overrides_current_semester(self):
        student = SimpleNamespace(name="Test Student", semester="5")
        mark_rows = [
            {"course_code": "AD3491", "course__title": "Data Science", "percentage": 75},
        ]
        gpa_query = MagicMock()
        gpa_query.order_by.return_value.values.return_value.first.return_value = None
        with patch.object(
            self.bot, "_get_student_subject_enrollments", return_value=([], "2025-2026")
        ) as enrollments, patch.object(
            self.bot, "_student_mark_performance_rows", return_value=mark_rows
        ) as performance_rows, patch.object(
            self.bot, "_student_hour_attendance_rows", return_value=[]
        ) as attendance_rows, patch.object(
            self.bot, "_ai_client", side_effect=ConnectionError
        ), patch("chatbot.chatbot_logic.GPA.objects.filter", return_value=gpa_query) as gpa_filter:
            response = self.bot._handle_student_performance_insights(
                student, "analyze my performance in semester 4"
            )

        enrollments.assert_called_once_with(student, 4)
        performance_rows.assert_called_once_with(student, 4, "2025-2026")
        attendance_rows.assert_called_once_with(student, 4, "2025-2026")
        gpa_filter.assert_called_once_with(student=student, semester__iexact="4")
        self.assertTrue(response.startswith("**My Performance Insights | Semester 4**"))
        self.assertNotIn("Semester 5", response)

    def test_performance_analysis_without_semester_uses_all_recorded_semesters(self):
        student = SimpleNamespace(
            name="Test Student",
            semester="5",
            department=SimpleNamespace(Department="AI AND DS"),
        )
        snapshots = {
            2: {
                "semester": 2,
                "academic_year": "2023-2024",
                "marks": [{
                    "course_code": "MA3201", "course__title": "Mathematics",
                    "obtained": 60, "maximum": 100, "percentage": 60.0,
                }],
                "attendance": [{"attended": 80, "total": 100}],
                "gpa": {"gpa": 6.5, "cgpa": 6.5},
                "results": [{
                    "course__course_code": "MA3201", "course__title": "Mathematics",
                    "grade": "B", "grade_total": 6.0, "academic_year": "2023-2024",
                }],
            },
            4: {
                "semester": 4,
                "academic_year": "2024-2025",
                "marks": [{
                    "course_code": "AD3491", "course__title": "Data Science",
                    "obtained": 80, "maximum": 100, "percentage": 80.0,
                }],
                "attendance": [{"attended": 90, "total": 100}],
                "gpa": {"gpa": 8.0, "cgpa": 7.25},
                "results": [{
                    "course__course_code": "AD3491", "course__title": "Data Science",
                    "grade": "A", "grade_total": 8.0, "academic_year": "2024-2025",
                }],
            },
        }
        with patch.object(
            self.bot, "_student_recorded_semesters", return_value=[2, 4]
        ), patch.object(
            self.bot,
            "_student_semester_performance_snapshot",
            side_effect=lambda _student, semester: snapshots[semester],
        ) as snapshot, patch.object(
            self.bot, "_ai_client", side_effect=ConnectionError
        ), patch.object(
            self.bot, "_resolve_student_semester"
        ) as semester_resolver:
            response = self.bot._handle_student_performance_insights(
                student, "analyze my overall performance"
            )

        self.assertEqual(snapshot.call_count, 2)
        snapshot.assert_any_call(student, 2)
        snapshot.assert_any_call(student, 4)
        semester_resolver.assert_not_called()
        self.assertTrue(response.startswith("**My Overall Performance Insights**"))
        self.assertIn("**Semesters analyzed:** 2, 4", response)
        self.assertIn("**Recorded internal-mark average:** 70.0%", response)
        self.assertIn("GPA improved from 6.5 in Semester 2 to 8.0 in Semester 4", response)
        self.assertIn("all currently recorded ERP data up to today", response)

    def test_performance_analysis_without_semester_routes_to_overall_handler(self):
        student = SimpleNamespace(name="Test Student", semester="5")
        for query in [
            "Analyze my performance",
            "Analyze my overall performance",
            "Evaluate my performance",
        ]:
            with self.subTest(query=query), patch.object(
                self.bot,
                "_handle_student_overall_performance_insights",
                return_value="overall",
            ) as overall:
                response = self.bot._handle_student_performance_insights(student, query)

            self.assertEqual(response, "overall")
            overall.assert_called_once_with(student)

    def test_recorded_semesters_are_discovered_from_all_academic_sources(self):
        student = SimpleNamespace(id=91)

        def semester_source(values):
            queryset = MagicMock()
            queryset.values_list.return_value.distinct.return_value = values
            return queryset

        enrollment_source = semester_source(["1", "2"])
        mark_source = semester_source(["2", "Semester 3"])
        attendance_source = semester_source(["3", "4"])
        result_source = semester_source(["4", "5"])
        gpa_source = semester_source(["5", "6", None])
        with patch(
            "chatbot.chatbot_logic.CourseEnrollment.objects.filter",
            return_value=enrollment_source,
        ) as enrollments, patch(
            "chatbot.chatbot_logic.StudentInternalMark.objects.filter",
            return_value=mark_source,
        ), patch(
            "chatbot.chatbot_logic.HourAttendance.objects.filter",
            return_value=attendance_source,
        ), patch(
            "chatbot.chatbot_logic.Result.objects.filter",
            return_value=result_source,
        ), patch(
            "chatbot.chatbot_logic.GPA.objects.filter",
            return_value=gpa_source,
        ):
            semesters = self.bot._student_recorded_semesters(student)

        self.assertEqual(semesters, [1, 2, 3, 4, 5, 6])
        enrollments.assert_called_once_with(student=student, enroll=True)

    def test_semester_two_performance_query_is_explicitly_detected(self):
        self.assertEqual(
            self.bot._extract_student_subject_semester(
                "Analyze my Semester 2 performance"
            ),
            2,
        )

    def test_attendance_explicit_semester_overrides_current_semester(self):
        student = SimpleNamespace(semester="5")
        attendance = [{
            "course__course_code": "AD3491", "course__title": "Data Science",
            "attended": 8, "total": 10, "absent": 2,
        }]
        with patch.object(
            self.bot, "_get_student_subject_enrollments", return_value=([], "2024-2025")
        ) as enrollments, patch.object(
            self.bot, "_student_hour_attendance_rows", return_value=attendance
        ) as attendance_rows:
            response = self.bot._handle_student_attendance(
                student, "show my attendance for semester 3"
            )

        enrollments.assert_called_once_with(student, 3)
        attendance_rows.assert_called_once_with(student, 3, "2024-2025")
        self.assertTrue(response.startswith("**My Subject-wise Attendance | Semester 3**"))
        self.assertIn("**Overall Attendance**", response)
        self.assertIn("**Percentage:** **80.0%**", response)
        self.assertIn("**Classes Attended:** **8/10**", response)
        self.assertIn("**Academic Year:** **2024-2025**", response)
        self.assertIn("1. **Data Science (AD3491)**", response)
        self.assertIn("Attendance: **8/10**", response)
        self.assertIn("Percentage: **80.0%**", response)

    def test_academic_overview_explicit_semester_filters_all_metrics(self):
        student = SimpleNamespace(semester="5")
        gpa_query = MagicMock()
        gpa_query.order_by.return_value.values.return_value.first.return_value = {
            "gpa": 8.0, "cgpa": 7.8, "semester": "2", "academic_year": "2023-2024"
        }
        with patch.object(
            self.bot, "_get_student_subject_enrollments", return_value=([], "2023-2024")
        ) as enrollments, patch.object(
            self.bot, "_student_hour_attendance_rows", return_value=[]
        ) as attendance, patch.object(
            self.bot, "_student_mark_performance_rows", return_value=[]
        ) as marks, patch("chatbot.chatbot_logic.GPA.objects.filter", return_value=gpa_query) as gpa_filter:
            response = self.bot._handle_student_academic_overview(
                student, "show my semester 2 academic analytics"
            )

        enrollments.assert_called_once_with(student, 2)
        attendance.assert_called_once_with(student, 2, "2023-2024")
        marks.assert_called_once_with(student, 2, "2023-2024")
        gpa_filter.assert_called_once_with(student=student, semester__iexact="2")
        self.assertIn("My Academic Overview | Semester 2", response)

    def test_results_explicit_semester_filters_result_and_gpa_queries(self):
        student = SimpleNamespace(semester="5")
        result_query = MagicMock()
        result_query.values.return_value.order_by.return_value = [{
            "course__course_code": "MA3251", "course__title": "Statistics",
            "grade": "A", "semester": "2", "academic_year": "2023-2024",
        }]
        gpa_query = MagicMock()
        gpa_query.values.return_value.order_by.return_value = [{
            "semester": "2", "gpa": 8.0, "cgpa": 7.8, "academic_year": "2023-2024",
        }]
        with patch(
            "chatbot.chatbot_logic.Result.objects.filter", return_value=result_query
        ) as result_filter, patch(
            "chatbot.chatbot_logic.GPA.objects.filter", return_value=gpa_query
        ) as gpa_filter:
            response = self.bot._handle_student_results(
                student, "show my semester 2 results"
            )

        result_filter.assert_called_once_with(student=student, semester__iexact="2")
        gpa_filter.assert_called_once_with(student=student, semester__iexact="2")
        self.assertIn("My Semester 2 Results", response)
        self.assertNotIn("Semester 5", response)

    def test_student_end_semester_phrases_are_recognized(self):
        queries = [
            "Show the end semester marks of 953624243093.",
            "Show the semester results of 953624243093.",
            "Display the final marks of 953624243093.",
            "View ESE marks for 953624243093.",
        ]
        for query in queries:
            with self.subTest(query=query):
                self.assertTrue(self.bot._is_student_end_semester_query(query))

    def test_end_semester_query_routes_before_subject_code_requirement(self):
        faculty = SimpleNamespace(name="Advisor")
        with patch.object(
            self.bot, "_get_faculty_info", return_value=faculty
        ), patch.object(
            self.bot,
            "_handle_student_end_semester_results",
            return_value="complete ESE results",
        ) as handler, patch.object(
            self.bot, "_handle_student_subject_marks_query"
        ) as subject_handler:
            response = self.bot.process_query(
                "Show the end semester marks of 953624243093.",
                "1603",
                role="Faculty",
                all_roles=["Faculty", "Class Advisor", "Mentor"],
            )

        self.assertEqual(response, "complete ESE results")
        handler.assert_called_once_with(
            "1603",
            "Faculty",
            "Show the end semester marks of 953624243093.",
            all_roles=["Faculty", "Class Advisor", "Mentor"],
        )
        subject_handler.assert_not_called()

    def test_ca_complete_access_does_not_require_subject_code(self):
        department = SimpleNamespace(id=1, Department="AI&DS")
        student = SimpleNamespace(
            id=36,
            name="Student",
            reg_no="953624243093",
            department=department,
            batch="2024",
            section="B",
        )
        faculty = SimpleNamespace(id=5, department=department)
        student_queryset = MagicMock()
        student_queryset.filter.return_value.first.return_value = student
        result_queryset = MagicMock()
        result_queryset.select_related.return_value = result_queryset
        result_queryset.values.return_value.order_by.return_value = []

        with patch.object(
            self.bot, "_student_queryset", return_value=student_queryset
        ), patch.object(
            self.bot, "_get_faculty_info", return_value=faculty
        ), patch.object(
            self.bot, "_has_student_access", return_value=True
        ) as access, patch(
            "chatbot.chatbot_logic.Result.objects.filter",
            return_value=result_queryset,
        ):
            response = self.bot._handle_student_end_semester_results(
                "1603",
                "Faculty",
                "Show semester marks of 953624243093",
                all_roles=["Faculty", "Class Advisor"],
            )

        self.assertIn("No published end-semester results", response)
        self.assertNotIn("subject code", response.lower())
        access.assert_called_once_with("1603", faculty, student, "Class Advisor")

    def test_hod_outside_department_cannot_get_complete_results(self):
        own_department = SimpleNamespace(id=1, Department="AI&DS")
        other_department = SimpleNamespace(id=2, Department="CSE")
        student = SimpleNamespace(
            id=36,
            name="Student",
            reg_no="953624243093",
            department=other_department,
            batch="2024",
            section="B",
        )
        faculty = SimpleNamespace(id=5, department=own_department)
        student_queryset = MagicMock()
        student_queryset.filter.return_value.first.return_value = student

        with patch.object(
            self.bot, "_student_queryset", return_value=student_queryset
        ), patch.object(
            self.bot, "_get_faculty_info", return_value=faculty
        ):
            response = self.bot._handle_student_end_semester_results(
                "1603",
                "HOD",
                "Show end semester marks of 953624243093",
                all_roles=["HOD"],
            )

        self.assertIn("Access denied", response)

    def test_explicit_semester_is_extracted(self):
        self.assertEqual(
            self.bot._extract_requested_semester(
                "Show semester 4 results of 953624243093"
            ),
            "4",
        )
        self.assertEqual(
            self.bot._extract_requested_semester(
                "Show 3rd semester results of 953624243093"
            ),
            "3",
        )

    def test_ese_subject_query_selects_semester_exam(self):
        self.assertEqual(
            self.bot._extract_internal_assessment_name(
                "Show AD3491 end semester marks"
            ),
            "Semester Exam",
        )

    def test_subject_title_can_resolve_without_course_code(self):
        faculty = SimpleNamespace(id=5, name="Teacher")
        course = SimpleNamespace(course_code="MA3451", title="Mathematics")
        assignment = SimpleNamespace(course=course)
        with patch.object(
            self.bot, "_get_faculty_info", return_value=faculty
        ), patch.object(
            self.bot,
            "_resolve_subject_assignments",
            return_value=([assignment], None),
        ), patch.object(
            self.bot, "_extract_department", return_value=None
        ), patch(
            "chatbot.chatbot_logic.StudentInternalMark.objects.filter"
        ) as marks_filter:
            marks_queryset = MagicMock()
            marks_filter.return_value = marks_queryset
            marks_queryset.exclude.return_value.exclude.return_value.values_list.return_value.distinct.return_value = []
            response = self.bot._handle_subject_marks_query(
                "1603", "Faculty", "Display Mathematics end semester marks"
            )

        self.assertNotIn("Please specify the subject", response)
        marks_filter.assert_called_once_with(course_code__iexact="MA3451")


class SubjectTeacherAssignmentTests(SimpleTestCase):
    def setUp(self):
        self.bot = ERPBot()
        self.faculty = SimpleNamespace(id=41, faculty_id="T001", name="Teacher")

    @staticmethod
    def _assignment(course_id, title, code, section):
        department = SimpleNamespace(Department="AI")
        course = SimpleNamespace(
            title=title, course_code=code, department=department
        )
        return SimpleNamespace(
            course_id=course_id,
            course=course,
            department=department,
            department_id=7,
            batch="2024-2025",
            section=section,
            academic_year="2024-2025",
        )

    def test_subject_teacher_gets_only_authenticated_assignments(self):
        assignments = MagicMock()
        assignments.exists.return_value = True
        assignments.order_by.return_value = [
            self._assignment(1, "Artificial Intelligence", "AI301", "A"),
            self._assignment(1, "Artificial Intelligence", "AI301", "B"),
            self._assignment(2, "Machine Learning", "AI302", "A"),
        ]

        with patch.object(
            self.bot, "_get_faculty_info", return_value=self.faculty
        ), patch.object(
            self.bot, "_subject_assignment_queryset", return_value=assignments
        ) as scoped_assignments:
            result = self.bot._handle_subjects_handled("T001", "Subject Teacher")

        scoped_assignments.assert_called_once_with(
            "T001", self.faculty, "Faculty"
        )
        self.assertIn("Artificial Intelligence (AI301)", result)
        self.assertIn("Machine Learning (AI302)", result)
        self.assertEqual(result.count("Artificial Intelligence"), 1)
        self.assertNotIn("Physics", result)

    def test_subject_teacher_no_assignment_message(self):
        assignments = MagicMock()
        assignments.exists.return_value = False
        with patch.object(
            self.bot, "_get_faculty_info", return_value=self.faculty
        ), patch.object(
            self.bot, "_subject_assignment_queryset", return_value=assignments
        ):
            result = self.bot._handle_subjects_handled("T001", "Subject Teacher")

        self.assertEqual(
            result,
            "No subject assignments were found for your account. "
            "Please contact the department administrator.",
        )

    def test_subject_allocation_phrases_route_to_assignment_handler(self):
        questions = [
            "List my handled subjects.",
            "What subject am I teach?",
            "Which subjects are assigned to me?",
            "Show my teaching subjects.",
            "Display my subject allocation.",
            "What subjects do I currently handle?",
        ]
        with patch.object(
            self.bot, "_get_faculty_info", return_value=self.faculty
        ), patch.object(
            self.bot, "_handle_subjects_handled", return_value="assigned subjects"
        ) as handler:
            for question in questions:
                with self.subTest(question=question):
                    self.assertEqual(
                        self.bot.process_query(question, "T001", role="Subject Teacher"),
                        "assigned subjects",
                    )
        self.assertEqual(handler.call_count, len(questions))

    def test_multi_role_hod_my_subjects_still_uses_personal_assignments(self):
        assignments = MagicMock()
        assignments.exists.return_value = True
        assignments.order_by.return_value = [
            self._assignment(1, "Artificial Intelligence", "AI301", "A"),
        ]
        self.faculty.department = SimpleNamespace(id=7, Department="AI")

        with patch.object(
            self.bot, "_get_faculty_info", return_value=self.faculty
        ), patch.object(
            self.bot, "_subject_assignment_queryset", return_value=assignments
        ) as scoped_assignments:
            result = self.bot._handle_subjects_handled(
                "T001", "HOD", query="List my subject handling."
            )

        scoped_assignments.assert_called_once_with("T001", self.faculty, "Faculty")
        self.assertIn("You are currently assigned to handle", result)
        self.assertNotIn("| Dept:", result)

    def test_hod_department_subjects_keeps_department_scope(self):
        assignments = MagicMock()
        assignments.exists.return_value = True
        assignments.order_by.return_value = [
            self._assignment(1, "Artificial Intelligence", "AI301", "A"),
        ]
        self.faculty.department = SimpleNamespace(id=7, Department="AI")

        with patch.object(
            self.bot, "_get_faculty_info", return_value=self.faculty
        ), patch.object(
            self.bot, "_subject_assignment_queryset", return_value=assignments
        ) as scoped_assignments:
            result = self.bot._handle_subjects_handled(
                "T001", "HOD", query="Show department subjects."
            )

        scoped_assignments.assert_called_once_with("T001", self.faculty, "HOD")
        self.assertIn("| Dept:", result)

    def test_class_report_extracts_batch_after_subject_code(self):
        self.assertEqual(
            self.bot._extract_batch("Class report for AD3491 2023\u20132027"),
            "2023-2027",
        )
        self.assertEqual(
            self.bot._extract_batch("Class report for AD3491 batch 2023-2027"),
            "2023-2027",
        )

    def test_section_a_is_not_treated_as_a_department_code(self):
        legacy_department = SimpleNamespace(
            id=34,
            Department="Computer Science and Engineering Cyber Security",
            Department_code="A",
        )
        with patch(
            "chatbot.chatbot_logic.Add_Department.objects.only",
            return_value=[legacy_department],
        ):
            department = self.bot._extract_department(
                "Class report for AL3451 in IAT 1 2024-2028 section A"
            )

        self.assertIsNone(department)

    def test_class_report_without_batch_returns_format_guidance(self):
        assignments = [
            self._assignment(1, "Data Science", "AD3491", "A"),
        ]
        with patch.object(
            self.bot, "_get_faculty_info", return_value=self.faculty
        ), patch.object(
            self.bot, "_resolve_subject_assignments", return_value=(assignments, None)
        ), patch.object(
            self.bot, "_get_class_report_assessments",
            return_value=["IAT1", "IAT2", "Model Exam", "Semester Exam"],
        ):
            result = self.bot._handle_class_report_query(
                "T001", "Faculty", "Class report for AD3491"
            )

        self.assertIn("specify both the assessment and the batch number", result)
        self.assertIn(
            "Class report for <Subject Code> in <Assessment> <Batch Number>",
            result,
        )

    def test_class_report_rejects_invalid_batch_range(self):
        assignments = [
            self._assignment(1, "Data Science", "AD3491", "A"),
        ]
        with patch.object(
            self.bot, "_get_faculty_info", return_value=self.faculty
        ), patch.object(
            self.bot, "_resolve_subject_assignments", return_value=(assignments, None)
        ), patch.object(
            self.bot, "_get_class_report_assessments", return_value=["IAT1", "IAT2"],
        ):
            result = self.bot._handle_class_report_query(
                "T001", "Faculty", "Class report for AD3491 in IAT 1 2023-2028"
            )

        self.assertIn("batch number is invalid", result)

    def test_class_report_rejects_batch_not_assigned_to_teacher(self):
        assignments = [
            self._assignment(1, "Data Science", "AD3491", "A"),
        ]
        with patch.object(
            self.bot, "_get_faculty_info", return_value=self.faculty
        ), patch.object(
            self.bot, "_resolve_subject_assignments", return_value=(assignments, None)
        ), patch.object(
            self.bot, "_get_class_report_assessments", return_value=["IAT1", "IAT2"],
        ):
            result = self.bot._handle_class_report_query(
                "T001", "Faculty", "Class report for AD3491 in IAT 1 2023-2027"
            )

        self.assertIn("not assigned to you", result)
        self.assertIn("Assigned batch(es) for AD3491", result)

    def test_class_report_batch_with_multiple_sections_requests_section(self):
        assignments = [
            self._assignment(1, "Data Science", "AD3491", "A"),
            self._assignment(1, "Data Science", "AD3491", "B"),
        ]
        with patch.object(
            self.bot, "_get_faculty_info", return_value=self.faculty
        ), patch.object(
            self.bot, "_resolve_subject_assignments", return_value=(assignments, None)
        ), patch.object(
            self.bot, "_get_class_report_assessments", return_value=["IAT1", "IAT2"],
        ):
            result = self.bot._handle_class_report_query(
                "T001", "Faculty", "Class report for AD3491 in IAT 1 2024-2028"
            )

        self.assertIn("Multiple sections are assigned", result)
        self.assertIn("A, B", result)

    def test_class_report_with_batch_but_no_assessment_returns_guidance(self):
        assignments = [
            self._assignment(1, "Data Science", "AD3491", "A"),
        ]
        with patch.object(
            self.bot, "_get_faculty_info", return_value=self.faculty
        ), patch.object(
            self.bot, "_resolve_subject_assignments", return_value=(assignments, None)
        ), patch.object(
            self.bot, "_get_class_report_assessments",
            return_value=["IAT1", "IAT2", "Model Exam"],
        ):
            result = self.bot._handle_class_report_query(
                "T001", "Faculty", "Class report for AD3491 2024-2028"
            )

        self.assertIn("specify both the assessment and the batch number", result)
        self.assertIn("Available assessments:", result)
        self.assertIn("\u2022 IAT 1", result)
        self.assertIn("\u2022 Model Exam", result)

    def test_class_report_rejects_assessment_not_available_for_batch(self):
        assignments = [
            self._assignment(1, "Data Science", "AD3491", "A"),
        ]
        with patch.object(
            self.bot, "_get_faculty_info", return_value=self.faculty
        ), patch.object(
            self.bot, "_resolve_subject_assignments", return_value=(assignments, None)
        ), patch.object(
            self.bot, "_get_class_report_assessments", return_value=["IAT1", "IAT2"]
        ):
            result = self.bot._handle_class_report_query(
                "T001", "Faculty", "Class report for AD3491 in Model Exam 2024-2028"
            )

        self.assertIn("requested assessment does not exist", result)
        self.assertIn("\u2022 IAT 1", result)

    def test_class_report_recognizes_required_assessment_formats(self):
        available = ["IAT1", "IAT2", "Model Exam", "Semester Exam"]
        examples = {
            "Class report for AD3491 in IAT 1 2024-2028": "IAT1",
            "Class report for AD3491 in IAT 2 2024-2028": "IAT2",
            "Class report for AD3491 in Model Exam 2024-2028": "Model Exam",
            "Class report for AD3491 in Semester Exam 2024-2028": "Semester Exam",
        }
        for question, expected in examples.items():
            with self.subTest(question=question):
                exam, supplied = self.bot._resolve_class_report_assessment(
                    question, available
                )
                self.assertTrue(supplied)
                self.assertEqual(exam, expected)

    def test_class_advisor_report_scope_uses_advised_class_allocations(self):
        raw_assignments = MagicMock()
        assignments = MagicMock()
        raw_assignments.select_related.return_value = assignments
        scoped_assignments = MagicMock()
        assignments.filter.return_value = scoped_assignments

        ca_students = MagicMock()
        ca_students.filter.return_value = ca_students
        ca_students.values.return_value.distinct.return_value = [{
            "department_id": 7,
            "batch": "2024",
            "section": "A",
        }]

        with patch(
            "chatbot.chatbot_logic.AssignSubjectFaculty.objects.filter",
            return_value=raw_assignments,
        ), patch.object(
            self.bot, "_get_students_by_role_id", return_value=ca_students
        ) as ca_lookup, patch.object(
            self.bot, "_build_faculty_assignment_filter"
        ) as own_teacher_filter:
            result = self.bot._class_report_assignment_queryset(
                "T001", self.faculty, "Class Advisor"
            )

        self.assertIs(result, scoped_assignments)
        ca_lookup.assert_called_once()
        own_teacher_filter.assert_not_called()

    def test_hod_report_scope_uses_department_not_own_subjects(self):
        department = SimpleNamespace(id=7, Department="AI")
        self.faculty.department = department
        raw_assignments = MagicMock()
        assignments = MagicMock()
        scoped_assignments = MagicMock()
        raw_assignments.select_related.return_value = assignments
        assignments.filter.return_value = scoped_assignments

        with patch(
            "chatbot.chatbot_logic.AssignSubjectFaculty.objects.filter",
            return_value=raw_assignments,
        ), patch.object(
            self.bot, "_build_faculty_assignment_filter"
        ) as own_teacher_filter:
            result = self.bot._class_report_assignment_queryset(
                "T001", self.faculty, "HOD"
            )

        self.assertIs(result, scoped_assignments)
        own_teacher_filter.assert_not_called()

    def test_class_advisor_can_resolve_another_teachers_subject(self):
        assignments = [
            self._assignment(1, "Machine Learning", "AL3451", "A"),
            self._assignment(1, "Machine Learning", "AL3451", "B"),
        ]
        with patch.object(
            self.bot, "_get_faculty_info", return_value=self.faculty
        ), patch.object(
            self.bot, "_resolve_subject_assignments", return_value=(assignments, None)
        ) as resolver, patch.object(
            self.bot, "_get_class_report_assessments", return_value=["IAT1"]
        ):
            response = self.bot._handle_class_report_query(
                "T001",
                "Class Advisor",
                "Class report for AL3451 in IAT 1 2024-2028",
            )

        self.assertIn("Multiple sections are assigned", response)
        self.assertTrue(resolver.call_args.kwargs["for_class_report"])

    def test_admin_class_report_requires_department_name(self):
        assignment = self._assignment(1, "Machine Learning", "AL3451", "A")
        with patch.object(
            self.bot, "_get_faculty_info", return_value=self.faculty
        ), patch.object(
            self.bot, "_resolve_subject_assignments", return_value=([assignment], None)
        ):
            response = self.bot._handle_class_report_query(
                "T001", "Admin", "Class report for AL3451 in IAT 1 2024-2028"
            )

        self.assertIn("specify the department name", response)
        self.assertIn("<Department Name>", response)

    def test_admin_class_report_does_not_require_faculty_profile(self):
        assignment = self._assignment(1, "Machine Learning", "AL3451", "A")
        with patch.object(
            self.bot, "_get_faculty_info", return_value=None
        ), patch.object(
            self.bot, "_resolve_subject_assignments", return_value=([assignment], None)
        ):
            response = self.bot._handle_class_report_query(
                "0000", "Admin", "Class report for AL3451 in IAT 1 2024-2028"
            )

        self.assertIn("specify the department name", response)
        self.assertNotIn("faculty record", response)

    def test_process_uses_all_roles_for_class_report_authorization(self):
        with patch.object(
            self.bot, "_get_faculty_info", return_value=self.faculty
        ), patch.object(
            self.bot, "_handle_class_report_query", return_value="CA report"
        ) as report_handler:
            response = self.bot.process_query(
                "Class report for AL3451 in IAT 1 2024-2028 section A",
                "T001",
                role="Faculty",
                all_roles=["Faculty", "Class Advisor"],
            )

        self.assertEqual(response, "CA report")
        report_handler.assert_called_once_with(
            "T001",
            "Class Advisor",
            "Class report for AL3451 in IAT 1 2024-2028 section A",
            all_roles=["Faculty", "Class Advisor"],
        )

    def test_class_report_infers_ca_from_student_mapping_when_role_row_missing(self):
        ca_students = MagicMock()
        ca_students.filter.return_value.exists.return_value = True
        with patch.object(
            self.bot, "_get_faculty_info", return_value=self.faculty
        ), patch.object(
            self.bot, "_get_students_by_role_id", return_value=ca_students
        ), patch.object(
            self.bot, "_resolve_subject_assignments", return_value=([], None)
        ):
            response = self.bot._handle_class_report_query(
                "T001",
                "Faculty",
                "Class report for AL3451 in IAT 1 2024-2028 section A",
                all_roles=["Faculty"],
            )

        self.assertIn("Class Advisor scope", response)
        self.assertNotIn("No accessible assignment", response)


class FacultyProductivityWorkflowTests(SimpleTestCase):
    def setUp(self):
        self.state = {}
        self.bot = ERPBot(conversation_state=self.state)
        self.faculty = SimpleNamespace(
            id=10,
            faculty_id="T001",
            name="Faculty One",
            department=SimpleNamespace(id=7, Department="AI"),
        )

    def test_daily_briefing_intent_routes_before_legacy_queries(self):
        with patch.object(
            self.bot, "_get_faculty_info", return_value=self.faculty
        ), patch.object(
            self.bot, "_handle_daily_briefing", return_value="Daily Faculty Briefing"
        ) as handler:
            response = self.bot.process_query(
                "What do I have today?", "T001", role="Faculty"
            )

        self.assertEqual(response, "Daily Faculty Briefing")
        handler.assert_called_once_with("T001", "Faculty")

    def test_early_warning_intent_is_role_scoped(self):
        with patch.object(
            self.bot, "_get_faculty_info", return_value=self.faculty
        ), patch.object(
            self.bot, "_handle_early_warning", return_value="Early Warning Students"
        ) as handler:
            response = self.bot.process_query(
                "Show at-risk students", "T001", role="Mentor"
            )

        self.assertEqual(response, "Early Warning Students")
        handler.assert_called_once_with("T001", "Mentor")

    def test_cancel_removes_pending_action(self):
        self.state["erp_chat_pending_action"] = {"type": "send_report"}
        with patch.object(
            self.bot, "_get_faculty_info", return_value=self.faculty
        ):
            response = self.bot.process_query("cancel", "T001", role="Faculty")

        self.assertIn("cancelled", response)
        self.assertNotIn("erp_chat_pending_action", self.state)

    def test_confirmation_without_preview_does_not_write(self):
        with patch.object(
            self.bot, "_get_faculty_info", return_value=self.faculty
        ), patch("chatbot.chatbot_logic.Notification.objects.create") as create:
            response = self.bot.process_query(
                "confirm send report", "T001", role="Faculty"
            )

        self.assertIn("no pending", response.lower())
        create.assert_not_called()

    def test_assessment_assistant_requires_course_code(self):
        response = self.bot._handle_assessment_assistant(
            "T001", "Faculty", "Create five questions on recursion"
        )

        self.assertIn("course code", response)

    def test_report_draft_intent_routes_to_workflow(self):
        with patch.object(
            self.bot, "_get_faculty_info", return_value=self.faculty
        ), patch.object(
            self.bot, "_handle_report_workflow", return_value="Faculty Report Draft"
        ) as handler:
            response = self.bot.process_query(
                "Draft report for 123456789012", "T001", role="Mentor"
            )

        self.assertEqual(response, "Faculty Report Draft")
        handler.assert_called_once_with(
            "T001", "Mentor", "Draft report for 123456789012", self.state
        )

    def test_workflow_message_parser_supports_due_status_and_notes(self):
        parsed = self.bot._parse_workflow_message(
            "MENTOR_FOLLOWUP|due=2026-07-25|status=open|notes=Review attendance"
        )

        self.assertEqual(parsed["due"], "2026-07-25")
        self.assertEqual(parsed["status"], "open")
        self.assertEqual(parsed["notes"], "Review attendance")

    def test_subject_risk_wording_routes_before_generic_marks_listing(self):
        with patch.object(
            self.bot, "_get_faculty_info", return_value=self.faculty
        ), patch.object(
            self.bot,
            "_handle_subject_risk_students",
            return_value="Subject Attention List",
        ) as handler:
            response = self.bot.process_query(
                "Show students with low attendance or marks in AD3491",
                "T001",
                role="Faculty",
            )

        self.assertEqual(response, "Subject Attention List")
        handler.assert_called_once_with(
            "T001",
            "Faculty",
            "Show students with low attendance or marks in AD3491",
        )

    def test_subject_mark_percentage_is_bounded_when_source_marks_exceed_maximum(self):
        detail = {
            "student_id": 1,
            "student__name": "Student One",
            "student__reg_no": "123456789012",
            "reg_no": "123456789012",
            "student__department__Department": "AI",
            "batch": "2024",
            "section": "A",
        }
        queryset = MagicMock()
        queryset.values.return_value.order_by.return_value = [detail]
        with patch.object(
            self.bot,
            "_aggregate_student_mark_details",
            return_value=[{"obtained": 160, "maximum": 100}],
        ):
            rows = self.bot._subject_performance_mark_rows(queryset)

        self.assertEqual(rows[0]["obtained"], 100)
        self.assertEqual(rows[0]["maximum"], 100)
        self.assertEqual(rows[0]["percentage"], 100)
        self.assertTrue(rows[0]["adjusted"])

    def test_subject_mark_normalization_displays_obtained_maximum_and_percentage(self):
        detail = {
            "student_id": 1,
            "student__name": "Student One",
            "student__reg_no": "123456789012",
            "reg_no": "123456789012",
            "student__department__Department": "AI",
            "batch": "2024",
            "section": "A",
        }
        queryset = MagicMock()
        queryset.values.return_value.order_by.return_value = [detail]
        with patch.object(
            self.bot,
            "_aggregate_student_mark_details",
            return_value=[
                {"obtained": 80, "maximum": 100},
                {"obtained": 80, "maximum": 100},
            ],
        ):
            rows = self.bot._subject_performance_mark_rows(queryset)

        self.assertEqual(rows[0]["total_marks"], "80/100")

    def test_analyze_performance_query_routes_registration_number_to_student_handler(self):
        with patch.object(
            self.bot, "_get_faculty_info", return_value=self.faculty
        ), patch.object(
            self.bot, "_handle_student_query", return_value="Scoped AI analysis"
        ) as handler:
            response = self.bot.process_query(
                "Analyze the academic performance of 953624243093",
                "T001",
                role="Faculty",
            )

        self.assertEqual(response, "Scoped AI analysis")
        handler.assert_called_once_with(
            "T001",
            "953624243093",
            "analyze the academic performance of 953624243093",
            "Faculty",
        )

    def test_faculty_performance_query_variants_route_to_scoped_student_handler(self):
        queries = [
            "Analyze the performance of 953624243093",
            "Evaluate the performance of 953624243093",
            "Show the performance analysis of 953624243093",
            "Analyze the performance of 953624243093 in Semester 4",
            "Evaluate 953624243093 for Semester 2",
            "Analyze Semester 6 performance of 953624243093",
        ]
        for query in queries:
            with self.subTest(query=query), patch.object(
                self.bot, "_get_faculty_info", return_value=self.faculty
            ), patch.object(
                self.bot, "_handle_student_query", return_value="Scoped analysis"
            ) as handler:
                response = self.bot.process_query(
                    query, "T001", role="Faculty"
                )

            self.assertEqual(response, "Scoped analysis")
            handler.assert_called_once_with(
                "T001", "953624243093", query.lower(), "Faculty"
            )

    def test_subject_faculty_analysis_requires_actual_course_enrollment(self):
        department = SimpleNamespace(id=7, Department="AI")
        student = SimpleNamespace(
            id=99,
            name="Student One",
            reg_no="953624243093",
            department=department,
            batch="2024",
            section="A",
            ca_id=None,
            mentor_id=None,
        )
        student_queryset = MagicMock()
        student_queryset.filter.return_value.first.return_value = student
        assignments = MagicMock()
        filtered_assignments = MagicMock()
        assignments.filter.return_value = filtered_assignments
        filtered_assignments.filter.return_value = filtered_assignments
        filtered_assignments.values_list.return_value.distinct.return_value = [77]
        enrollments = MagicMock()
        enrollments.values_list.return_value.distinct.return_value = []

        with patch.object(
            self.bot, "_student_queryset", return_value=student_queryset
        ), patch.object(
            self.bot, "_get_faculty_info", return_value=self.faculty
        ), patch.object(
            self.bot, "_is_role_id_11_user", return_value=False
        ), patch.object(
            self.bot, "_subject_assignment_queryset", return_value=assignments
        ), patch(
            "chatbot.chatbot_logic.CourseEnrollment.objects.filter",
            return_value=enrollments,
        ):
            response = self.bot._handle_student_query(
                "T001",
                "953624243093",
                "Analyze the academic performance of 953624243093",
                "Faculty",
            )

        self.assertIn("actively enrolled", response)

    def test_faculty_student_analysis_uses_stable_format_when_metrics_are_missing(self):
        student = SimpleNamespace(
            name="RAMROJITH V",
            year="3",
            section="A",
            department=SimpleNamespace(
                Department="ARTIFICIAL INTELLIGENCE AND DATA SCIENCE"
            ),
        )

        response = self.bot._format_student_performance_analysis(
            current_scope="All Subjects (ARTIFICIAL INTELLIGENCE AND DATA SCIENCE)",
            student=student,
            semester=5,
            latest_cgpa="N/A",
            performance_rows=[],
            attendance_rows=[],
            activity_counts={
                "achievements": "0",
                "co_curricular": "0",
                "publications": "0",
                "projects": "0",
            },
        )

        self.assertTrue(
            response.startswith("**Student Performance Analysis | Semester 5**")
        )
        self.assertIn("**Recorded Academic Summary**", response)
        self.assertIn("**Semester CGPA:** N/A", response)
        self.assertNotIn("GCPA", response)
        self.assertNotIn("performance is inconsistent", response.lower())
        self.assertIn("Missing or unpublished data is shown as N/A", response)

    def test_faculty_student_analysis_calculates_factual_summary(self):
        student = SimpleNamespace(
            name="Student One",
            year="3",
            section="A",
            department=SimpleNamespace(Department="AI AND DS"),
        )
        response = self.bot._format_student_performance_analysis(
            current_scope="All Subjects (AI AND DS)",
            student=student,
            semester=4,
            latest_cgpa=7.8,
            performance_rows=[
                {
                    "course_code": "AD3491",
                    "course__title": "Data Science",
                    "obtained": 80,
                    "maximum": 100,
                    "percentage": 80.0,
                },
                {
                    "course_code": "MA3391",
                    "course__title": "Statistics",
                    "obtained": 40,
                    "maximum": 100,
                    "percentage": 40.0,
                },
            ],
            attendance_rows=[{"attended": 85, "total": 100}],
            activity_counts={
                "achievements": "1",
                "co_curricular": "2",
                "publications": "0",
                "projects": "1",
            },
        )

        self.assertIn("**Internal-Mark Average:** 60.0%", response)
        self.assertIn("**Attendance:** 85/100 (85.0%)", response)
        self.assertIn("Strongest recorded subject: Data Science (AD3491) - 80.0%", response)
        self.assertIn("Subject requiring the most attention: Statistics (MA3391) - 40.0%", response)

    def test_faculty_ai_recommendations_are_limited_to_action_items(self):
        student = SimpleNamespace(
            department=SimpleNamespace(Department="AI AND DS")
        )
        snapshot = {
            "semester": 4,
            "marks": [{
                "course_code": "MA3391", "course__title": "Statistics",
                "percentage": 40.0,
            }],
            "attendance": [{
                "course__course_code": "MA3391", "course__title": "Statistics",
                "attended": 70, "total": 100,
            }],
        }
        client = MagicMock()
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=(
                "1. Review Statistics concepts weekly.\n"
                "2. Practise assessment questions.\n"
                "3. Attend upcoming classes consistently."
            )))]
        )
        with patch.object(self.bot, "_ai_client", return_value=client):
            actions = self.bot._faculty_ai_recommendations(
                "semester", student, [snapshot]
            )

        self.assertEqual(len(actions), 3)
        self.assertEqual(actions[0], "Review Statistics concepts weekly.")
        self.assertEqual(
            client.chat.completions.create.call_args.kwargs["model"],
            self.bot._ai_model(),
        )

    def test_faculty_explicit_semester_analysis_uses_only_requested_semester(self):
        department = SimpleNamespace(id=7, Department="AI AND DS")
        student = SimpleNamespace(
            id=99,
            name="Student One",
            reg_no="953624243093",
            year="3",
            semester="6",
            section="A",
            batch="2023",
            department=department,
            ca_id=None,
            mentor_id=None,
        )
        faculty = SimpleNamespace(id=5, faculty_id="H001", department=department)
        student_queryset = MagicMock()
        student_queryset.filter.return_value.first.return_value = student
        legacy_marks = MagicMock()
        legacy_marks.exists.return_value = True
        legacy_marks.values.return_value.order_by.return_value = []
        snapshot = {
            "semester": 2,
            "academic_year": "2023-2024",
            "marks": [{
                "course_code": "MA3201", "course__title": "Mathematics",
                "obtained": 75, "maximum": 100, "percentage": 75.0,
            }],
            "attendance": [{"attended": 80, "total": 100}],
            "gpa": {"gpa": 7.0, "cgpa": 7.0},
            "results": [{
                "course__course_code": "MA3201",
                "course__title": "Mathematics",
                "grade": "A",
                "grade_total": 8.0,
                "academic_year": "2023-2024",
            }],
        }
        with patch.object(
            self.bot, "_student_queryset", return_value=student_queryset
        ), patch.object(
            self.bot, "_get_faculty_info", return_value=faculty
        ), patch.object(
            self.bot, "_is_role_id_11_user", return_value=False
        ), patch(
            "chatbot.chatbot_logic.AssessmentMark.objects.filter",
            return_value=legacy_marks,
        ), patch.object(
            self.bot,
            "_student_semester_performance_snapshot",
            return_value=snapshot,
        ) as semester_snapshot, patch.object(
            self.bot, "_faculty_ai_recommendations", return_value=None
        ), patch.object(
            self.bot, "_student_recorded_semesters"
        ) as recorded_semesters:
            response = self.bot._handle_student_query(
                "H001",
                student.reg_no,
                "Evaluate 953624243093 for Semester 2",
                "HOD",
            )

        semester_snapshot.assert_called_once_with(student, 2)
        recorded_semesters.assert_not_called()
        self.assertTrue(
            response.startswith("**Student Performance Analysis | Semester 2**")
        )
        self.assertIn("**Published End-Semester Subject Results**", response)
        self.assertIn("Mathematics (MA3201)", response)
        self.assertNotIn("Semester 6", response)

    def test_faculty_overall_analysis_uses_all_recorded_semesters(self):
        department = SimpleNamespace(id=7, Department="AI AND DS")
        student = SimpleNamespace(
            id=99,
            name="Student One",
            reg_no="953624243093",
            year="3",
            semester="6",
            section="A",
            batch="2023",
            department=department,
            ca_id=None,
            mentor_id=None,
        )
        faculty = SimpleNamespace(id=5, faculty_id="H001", department=department)
        student_queryset = MagicMock()
        student_queryset.filter.return_value.first.return_value = student
        legacy_marks = MagicMock()
        legacy_marks.exists.return_value = True
        legacy_marks.values.return_value.order_by.return_value = []

        def snapshot(semester):
            return {
                "semester": semester,
                "academic_year": "2023-2024" if semester == 2 else "2024-2025",
                "marks": [{
                    "course_code": f"SUB{semester}",
                    "course__title": f"Subject {semester}",
                    "obtained": 60 + semester,
                    "maximum": 100,
                    "percentage": float(60 + semester),
                }],
                "attendance": [{"attended": 80 + semester, "total": 100}],
                "gpa": {"gpa": 6.0 + semester / 10, "cgpa": 6.5 + semester / 10},
                "results": [{
                    "course__course_code": f"SUB{semester}",
                    "course__title": f"Subject {semester}",
                    "grade": "B",
                    "grade_total": 7.0,
                    "academic_year": "2024-2025",
                }],
            }

        count_queryset = MagicMock()
        count_queryset.count.return_value = 1
        with patch.object(
            self.bot, "_student_queryset", return_value=student_queryset
        ), patch.object(
            self.bot, "_get_faculty_info", return_value=faculty
        ), patch.object(
            self.bot, "_is_role_id_11_user", return_value=False
        ), patch(
            "chatbot.chatbot_logic.AssessmentMark.objects.filter",
            return_value=legacy_marks,
        ), patch.object(
            self.bot, "_student_recorded_semesters", return_value=[2, 4]
        ), patch.object(
            self.bot,
            "_student_semester_performance_snapshot",
            side_effect=lambda _student, semester: snapshot(semester),
        ) as semester_snapshot, patch(
            "chatbot.chatbot_logic.ERPBot._faculty_ai_recommendations",
            return_value=None,
        ), patch(
            "chatbot.chatbot_logic.StudentAchievements.objects.filter",
            return_value=count_queryset,
        ), patch(
            "chatbot.chatbot_logic.StudentCO_EX_Curricular.objects.filter",
            return_value=count_queryset,
        ), patch(
            "chatbot.chatbot_logic.StudentPublication.objects.filter",
            return_value=count_queryset,
        ), patch(
            "chatbot.chatbot_logic.StudentProjects.objects.filter",
            return_value=count_queryset,
        ):
            response = self.bot._handle_student_query(
                "H001",
                student.reg_no,
                "Analyze the academic performance of 953624243093",
                "HOD",
            )

        self.assertEqual(semester_snapshot.call_count, 2)
        semester_snapshot.assert_any_call(student, 2)
        semester_snapshot.assert_any_call(student, 4)
        self.assertTrue(response.startswith("**Overall Student Performance Analysis**"))
        self.assertIn("**Recorded Semesters:** 2, 4", response)
        self.assertIn("**Average Published Grade Total:** 7.0", response)
        self.assertIn("**Academic Trends and Consistency**", response)
        self.assertIn("all currently recorded ERP data available up to today", response)

    def test_faculty_requested_semester_without_data_does_not_use_current_semester(self):
        department = SimpleNamespace(id=7, Department="AI AND DS")
        student = SimpleNamespace(
            id=99, name="Student One", reg_no="953624243093", year="3",
            semester="6", section="A", batch="2023", department=department,
            ca_id=None, mentor_id=None,
        )
        faculty = SimpleNamespace(id=5, faculty_id="H001", department=department)
        student_queryset = MagicMock()
        student_queryset.filter.return_value.first.return_value = student
        legacy_marks = MagicMock()
        legacy_marks.exists.return_value = True
        legacy_marks.values.return_value.order_by.return_value = []
        empty_snapshot = {
            "semester": 2, "academic_year": None, "marks": [],
            "attendance": [], "gpa": None, "results": [],
        }
        with patch.object(
            self.bot, "_student_queryset", return_value=student_queryset
        ), patch.object(
            self.bot, "_get_faculty_info", return_value=faculty
        ), patch.object(
            self.bot, "_is_role_id_11_user", return_value=False
        ), patch(
            "chatbot.chatbot_logic.AssessmentMark.objects.filter",
            return_value=legacy_marks,
        ), patch.object(
            self.bot,
            "_student_semester_performance_snapshot",
            return_value=empty_snapshot,
        ) as semester_snapshot:
            response = self.bot._handle_student_query(
                "H001", student.reg_no,
                "Analyze Semester 2 performance of 953624243093", "HOD",
            )

        semester_snapshot.assert_called_once_with(student, 2)
        self.assertIn("No recorded academic data exists for Semester 2", response)
        self.assertNotIn("Semester 6", response)

    def test_faculty_quick_action_prepares_input_instead_of_auto_submitting(self):
        project_root = Path(__file__).resolve().parent.parent
        widget = (project_root / "templates" / "chatbot" / "widget.html").read_text(
            encoding="utf-8"
        )
        script = (project_root / "static" / "chatbot" / "chatbot.js").read_text(
            encoding="utf-8"
        )

        self.assertIn("Analyze Student Performance", widget)
        self.assertIn(
            'data-chat-template-prefix="Analyze the performance of "',
            widget,
        )
        self.assertIn('querySelectorAll("[data-chat-template-prefix]")', script)
        self.assertIn("input.setSelectionRange", script)

    def test_student_question_browser_is_searchable_copyable_and_click_to_fill(self):
        project_root = Path(__file__).resolve().parent.parent
        widget = (project_root / "templates" / "chatbot" / "widget.html").read_text(
            encoding="utf-8"
        )
        script = (project_root / "static" / "chatbot" / "chatbot.js").read_text(
            encoding="utf-8"
        )
        stylesheet = (
            project_root / "static" / "chatbot" / "chatbot.css"
        ).read_text(encoding="utf-8")
        style_partial = (
            project_root / "templates" / "chatbot" / "styles.html"
        ).read_text(encoding="utf-8")

        catalog = (
            project_root / "chatbot" / "question_catalog.py"
        ).read_text(encoding="utf-8")

        self.assertIn('id="erpChatQuestionsToggle"', widget)
        self.assertIn('id="erpChatQuestionsSearch"', widget)
        self.assertIn('id="erpChatQuestionsList"', widget)
        self.assertIn('data-questions-url="{% url \'chatbot:questions\' %}"', widget)
        self.assertIn("Show my Semester 4 subjects.", catalog)
        self.assertIn("Show my attendance in Semester 4.", catalog)
        self.assertIn("Analyze my performance.", catalog)
        self.assertNotIn("Analyze my performance in Semester 4.", catalog)
        self.assertIn("Head of Department", catalog)
        self.assertIn("function useQuestion(question)", script)
        self.assertIn("fetch(root.dataset.questionsUrl", script)
        self.assertIn("navigator.clipboard.writeText(question)", script)
        self.assertIn("faculty-chatbot__question-panel", stylesheet)
        self.assertIn("height: calc(100% - 74px)", stylesheet)
        self.assertIn("overflow-y: auto", stylesheet)
        self.assertIn("overflow-x: hidden", stylesheet)
        self.assertIn("-webkit-overflow-scrolling: touch", stylesheet)
        self.assertIn("grid-template-columns: minmax(0, 1fr) 40px", stylesheet)
        self.assertIn("chatbot/chatbot.css", style_partial)
        self.assertIn("?v=20260720-3", style_partial)
        for template_name in (
            "base.html",
            "student_dashboard.html",
            "faculty_dashboard.html",
        ):
            template = (project_root / "templates" / template_name).read_text(
                encoding="utf-8"
            )
            self.assertIn('{% include "chatbot/styles.html" %}', template)
