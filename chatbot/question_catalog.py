"""Role-scoped quick questions for the shared ERP chatbot panel."""


STUDENT_QUESTION_GROUPS = (
    (
        "Subjects and timetable",
        (
            "Show my subjects.",
            "Show my Semester 4 subjects.",
            "What subjects do I have this semester?",
            "Show my timetable.",
            "Show today's timetable.",
            "What classes do I have tomorrow?",
            "Show my Semester 4 timetable.",
        ),
    ),
    (
        "Attendance",
        (
            "Show my attendance.",
            "Show my attendance in Semester 4.",
            "Show subject-wise attendance.",
            "Show attendance for AL3451.",
            "Which subjects have attendance below 75%?",
            "How many classes can I miss?",
            "How many classes must I attend to reach 75%?",
            "Show my attendance shortage.",
        ),
    ),
    (
        "Marks and results",
        (
            "Show my internal marks.",
            "Show my Semester 4 internal marks.",
            "Show my IAT 1 marks for Semester 4.",
            "Show my IAT 2 marks.",
            "Show my marks for AD3491.",
            "Show my Semester 3 results.",
            "Show my GPA.",
            "Show my Semester 4 GPA.",
            "Show my CGPA.",
            "Show my semester summary.",
        ),
    ),
    (
        "Performance analysis",
        (
            "Analyze my performance.",
        ),
    ),
    (
        "Personal information",
        (
            "Show my student profile.",
            "What is my register number?",
            "Show my department and current semester.",
            "Who is my class advisor?",
            "Who is my mentor?",
            "Show my academic year and batch.",
        ),
    ),
)


COMMON_EMPLOYEE_QUESTIONS = (
    "Show my profile.",
    "Show my timetable.",
    "What is my schedule today?",
    "Give me my daily briefing.",
    "Show my pending work.",
    "Which subjects do I handle?",
    "What can you help me with?",
)


ROLE_QUESTION_GROUPS = {
    "Faculty": (
        "Subject Faculty",
        (
            "List my handled subjects.",
            "Show students for my subject <SUBJECT CODE>.",
            "Show students at risk in <SUBJECT CODE>.",
            "List students with attendance below 75% in <SUBJECT CODE>.",
            "Show low-performing students in <SUBJECT CODE>.",
            "Show pending attendance for my subjects.",
            "Show pending marks for my subjects.",
            "Class report for <SUBJECT CODE> in IAT 1 <BATCH> section <SECTION>.",
            "Show <SUBJECT CODE> marks for <REGISTER NUMBER>.",
            "Create five questions on <TOPIC>.",
            "Generate a question paper on <TOPIC>.",
            "Create an assessment rubric for <TOPIC>.",
        ),
    ),
    "Class Advisor": (
        "Class Advisor",
        (
            "Show my class students.",
            "Show my Class Advisor students.",
            "Show early warning students in my class.",
            "Show low-performing students in my class.",
            "Show students in my class who need attention.",
            "Analyze the academic performance of <REGISTER NUMBER>.",
            "Show attendance for <REGISTER NUMBER>.",
            "Show semester results for <REGISTER NUMBER>.",
            "Show internal marks for <REGISTER NUMBER>.",
            "Class report for <SUBJECT CODE> in IAT 1 <BATCH> section <SECTION>.",
            "Draft report for <REGISTER NUMBER>.",
        ),
    ),
    "Mentor": (
        "Mentor",
        (
            "Show my mentees.",
            "Show students under my mentorship.",
            "Show early warning students among my mentees.",
            "Show low-performing mentees.",
            "Which mentees need academic attention?",
            "Analyze the academic performance of <REGISTER NUMBER>.",
            "Show attendance for <REGISTER NUMBER>.",
            "Show internal marks for <REGISTER NUMBER>.",
            "Show mentor follow-up history.",
            "Record mentor follow-up for <REGISTER NUMBER>: <NOTES>.",
            "Schedule a mentor meeting for <REGISTER NUMBER>: <NOTES>.",
            "Draft report for <REGISTER NUMBER>.",
        ),
    ),
    "HOD": (
        "Head of Department",
        (
            "Show my department students.",
            "Show students from batch <BATCH> in my department.",
            "Show my department faculty.",
            "Show classes in my department.",
            "List students with attendance below 75%.",
            "Show the top 10 students in my department.",
            "Show low-performing students in my department.",
            "Which students need mentoring?",
            "Show department performance summary.",
            "Show subject-wise performance in my department.",
            "Which subject has the lowest average?",
            "Compare classes and sections in my department.",
            "Show department student projects and achievements.",
            "Show department student publications.",
            "Show department co-curricular activities.",
            "Show mentor report.",
            "Show teacher report.",
            "Show department notifications.",
            "Find student <REGISTER NUMBER>.",
            "Class report for <SUBJECT CODE> in IAT 1 <BATCH> section <SECTION>.",
        ),
    ),
    "Vice Principal": (
        "Vice Principal",
        (
            "Show all students.",
            "Show students from batch <BATCH>.",
            "Show early warning students.",
            "Analyze the academic performance of <REGISTER NUMBER>.",
            "Show attendance for <REGISTER NUMBER>.",
            "Show semester results for <REGISTER NUMBER>.",
            "Show internal marks for <REGISTER NUMBER>.",
            "Class report for <SUBJECT CODE> in IAT 1 <BATCH> section <SECTION>.",
            "Show subject reports.",
        ),
    ),
    "Admin": (
        "Administrator",
        (
            "Show all active students.",
            "Show students from <DEPARTMENT> department.",
            "Show students from batch <BATCH>.",
            "Show department faculty.",
            "Show department classes.",
            "Show institution-wide early warning students.",
            "Analyze the academic performance of <REGISTER NUMBER>.",
            "Show attendance for <REGISTER NUMBER>.",
            "Show internal marks for <REGISTER NUMBER>.",
            "Show semester results for <REGISTER NUMBER>.",
            "Class report for <SUBJECT CODE> in IAT 1 <BATCH> department <DEPARTMENT> section <SECTION>.",
        ),
    ),
}


def canonical_question_role(role):
    """Map ERP role variants to the catalog's stable authorization roles."""
    normalized = " ".join(str(role or "").strip().lower().split())
    aliases = {
        "student": "Student",
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
        "faculty": "Faculty",
        "subject faculty": "Faculty",
        "subject teacher": "Faculty",
        "teacher": "Faculty",
    }
    return aliases.get(normalized)


def build_question_groups(roles):
    """Return de-duplicated question groups authorized by verified ERP roles."""
    canonical_roles = {
        canonical
        for canonical in (canonical_question_role(role) for role in roles)
        if canonical
    }
    if canonical_roles == {"Student"}:
        return [
            {"title": title, "questions": list(questions)}
            for title, questions in STUDENT_QUESTION_GROUPS
        ]

    groups = []
    seen_questions = set()

    def add_group(title, questions):
        permitted = []
        for question in questions:
            key = question.casefold()
            if key in seen_questions:
                continue
            seen_questions.add(key)
            permitted.append(question)
        if permitted:
            groups.append({"title": title, "questions": permitted})

    add_group("Common", COMMON_EMPLOYEE_QUESTIONS)
    for role in (
        "Faculty",
        "Class Advisor",
        "Mentor",
        "HOD",
        "Vice Principal",
        "Admin",
    ):
        if role in canonical_roles:
            add_group(*ROLE_QUESTION_GROUPS[role])
    return groups
