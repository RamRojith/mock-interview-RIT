import json
from collections import defaultdict, OrderedDict

from django.contrib import messages
from django.db import transaction
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import render, redirect

from course_management.models import Regulations
from user_accounts.models import Degree
from examination_management.models import (
    ExamPattern, Part, Question, OptionMarks, Assessments, InternalAssessment,
)
import json
from collections import defaultdict, OrderedDict

from django.contrib import messages
from django.db import transaction
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import render, redirect



def question(request):
    """
    Question Paper Generator

    - GET:
      Renders filters and prefilled latest pattern for keys.
      Exam choices include:
        * "Semester X" (once semester is chosen)
        * QP-required Assessments for the degree
        * Internal Assessments (InternalAssessment.iat) for the degree

    - POST (action=preview, AJAX):
      Returns JSON with:
        * selected, exam_choices, prefilled_questions, parts_segments, pattern_options

    - POST (action=save):
      Creates/updates ExamPattern for given keys and persists structure + options.
    """

    # --------------------- helpers ---------------------
    def load_qp_assessments_for_degree(degree_id):
        if not degree_id:
            return []
        return list(
            Assessments.objects.filter(
                degree_id=degree_id,
                question_paper_required=True
            ).values_list("assessment_name", flat=True)
        )

    def load_internal_iats_for_degree(degree_id):
        if not degree_id:
            return []
        names = list(
            InternalAssessment.objects
            .filter(degree_id=degree_id)
            .values_list("iat", flat=True)
        )
        return [n.strip() for n in names if n and str(n).strip()]

    def build_exam_choices(degree_id, semester):
        choices = []
        if semester:
            choices.append(f"Semester {semester}")

        qp = load_qp_assessments_for_degree(degree_id) if degree_id else []
        internal = load_internal_iats_for_degree(degree_id) if degree_id else []

        seen = set()
        merged = []
        for group in (qp, internal):
            for name in group:
                key = str(name).strip()
                lk = key.lower()
                if key and lk not in seen:
                    seen.add(lk)
                    merged.append(key)

        return choices + merged

    def pattern_signature(parts):
        by_label = defaultdict(lambda: defaultdict(int))
        order, seen = [], set()
        for seg in parts:
            label = str(seg.get("label", "")).strip().upper()
            marks = int(seg.get("marks") or 0)
            count = int(seg.get("count") or 0)
            if not label or marks < 1 or count < 1:
                continue
            by_label[label][marks] += count
            if label not in seen:
                order.append(label)
                seen.add(label)
        chunks = []
        for lab in order:
            marks_map = by_label[lab]
            inner = "+".join(f"{marks_map[m]}x{m}" for m in sorted(marks_map))
            chunks.append(f"{lab}:{inner}")
        return "|".join(chunks) if chunks else "CUSTOM"

    def parse_parts_json(raw):
        try:
            data = json.loads(raw or "[]")
            if not isinstance(data, list):
                return []
        except Exception:
            return []
        out = []
        for seg in data:
            label = str(seg.get("label", "")).strip().upper()
            try:
                marks = int(seg.get("marks") or 0)
                count = int(seg.get("count") or 0)
                start = seg.get("start")
                start = int(start) if start not in (None, "",) else None
            except Exception:
                continue
            if not label or marks < 1 or count < 1:
                continue
            one = {"label": label, "marks": marks, "count": count}
            if start and start > 0:
                one["start"] = start
            out.append(one)
        return out

    def base_pattern_qs():
        return ExamPattern.objects.prefetch_related(
            Prefetch(
                'parts',
                queryset=Part.objects.prefetch_related(
                    Prefetch('questions', queryset=Question.objects.prefetch_related('options'))
                )
            )
        )

    def get_pattern_by_id(pid):
        if not pid:
            return None
        try:
            return base_pattern_qs().get(id=pid)
        except ExamPattern.DoesNotExist:
            return None

    def latest_pattern_for_keys(reg_id, deg_id, year, semester, exam, academic_year):
        return (
            base_pattern_qs()
            .filter(
                regulation_id=reg_id,
                degree_id=deg_id,
                year=year,
                semester=semester,
                for_exam=exam,
                academic_year=academic_year
            )
            .order_by('-id')
            .first()
        )

    def list_patterns_for_keys(reg_id, deg_id, year, semester, exam, academic_year):
        qs = (
            ExamPattern.objects
            .filter(
                regulation_id=reg_id,
                degree_id=deg_id,
                year=year,
                semester=semester,
                for_exam=exam,
                academic_year=academic_year
            )
            .order_by('-id')
        )
        out = []
        for idx, ep in enumerate(qs, start=1):
            sig = ep.pattern or "CUSTOM"
            out.append({"id": str(ep.id), "label": f"{idx}) {sig} (#{ep.id})"})
        return out

    def build_prefilled_from_ep(ep):
        if not ep:
            return {}
        pre = {}
        for part in ep.parts.all():
            for q in part.questions.all():
                if q.total_marks and q.total_marks >= 5:
                    for opt in q.options.all():
                        pre[f"q{q.number}_{opt.option_letter}_i"] = opt.marks_i or 0
                        pre[f"q{q.number}_{opt.option_letter}_ii"] = opt.marks_ii or 0
        return pre

    def build_prefilled_latest(reg_id, deg_id, year, semester, exam, academic_year):
        ep = latest_pattern_for_keys(reg_id, deg_id, year, semester, exam, academic_year)
        return build_prefilled_from_ep(ep)

    def build_segments_from_ep(ep):
        if not ep:
            return []
        segments = []
        parts_qs = ep.parts.all().order_by('name')
        for part in parts_qs:
            qs = list(part.questions.all().order_by('number'))
            if not qs:
                continue
            i = 0
            while i < len(qs):
                j = i + 1
                current_marks = int(qs[i].total_marks or 0)
                run_start_no = int(qs[i].number)
                prev_no = run_start_no
                while (
                    j < len(qs)
                    and int(qs[j].total_marks or 0) == current_marks
                    and int(qs[j].number) == prev_no + 1
                ):
                    prev_no = int(qs[j].number)
                    j += 1
                run_len = j - i
                segments.append({
                    "label": str(part.name).upper(),
                    "marks": current_marks,
                    "count": run_len,
                    "start": run_start_no,
                })
                i = j
        return segments
    # ---------------------------------------------------

    regulations = Regulations.objects.all()
    degrees = Degree.objects.filter(is_active=True)
    context = {
        "regulations": regulations,
        "degrees": degrees,
        "exam_choices": [],
        "pattern_options": [],
        "selected": {
            "regulation_id": "",
            "degree_id": "",
            "regulation_year": "",
            "year": "",
            "semester": "",
            "exam": "",
            "academic_year": "",
            "pattern_id": "",
        },
        "prefilled_questions": {},
    }

    # ---------- AJAX PREVIEW ----------
    if request.method == "POST" and request.POST.get("action") == "preview":
        regulation_id = request.POST.get("regulation") or ""
        degree_id     = request.POST.get("degree") or ""
        year          = request.POST.get("year") or ""
        semester      = request.POST.get("semester") or ""
        exam          = request.POST.get("exam") or ""
        academic_year = request.POST.get("academic_year") or ""
        pattern_id    = request.POST.get("pattern_id") or ""

        try:
            regulation_year = Regulations.objects.only("year").get(id=regulation_id).year
        except Regulations.DoesNotExist:
            regulation_year = ""

        pattern_options = []
        if all([regulation_id, degree_id, year, semester, exam, academic_year]):
            pattern_options = list_patterns_for_keys(
                regulation_id, degree_id, year, semester, exam, academic_year
            )

        ep = get_pattern_by_id(pattern_id) if pattern_id else None

        payload = {
            "selected": {
                "regulation_id": regulation_id,
                "degree_id": degree_id,
                "regulation_year": regulation_year or "",
                "year": year,
                "semester": semester,
                "exam": exam,
                "academic_year": academic_year,
                "pattern_id": str(ep.id) if ep else "",
            },
            "exam_choices": build_exam_choices(degree_id, semester),
            "prefilled_questions": build_prefilled_from_ep(ep) if ep else {},
            "parts_segments": build_segments_from_ep(ep) if ep else [],
            "pattern_options": pattern_options,
        }
        return JsonResponse(payload, status=200)

    # ---------- SAVE ----------
    if request.method == "POST":
        action = request.POST.get("action")
        regulation_id = request.POST.get("regulation")
        degree_id     = request.POST.get("degree")
        year          = request.POST.get("year")
        semester      = request.POST.get("semester")
        exam          = request.POST.get("exam")
        academic_year = request.POST.get("academic_year")
        pattern_id    = request.POST.get("pattern_id") or ""
        parts_raw     = request.POST.get("parts_json")

        try:
            regulation_year = Regulations.objects.only("year").get(id=regulation_id).year
        except Regulations.DoesNotExist:
            regulation_year = ""

        context["selected"].update({
            "regulation_id": regulation_id or "",
            "degree_id": degree_id or "",
            "regulation_year": regulation_year or "",
            "year": year or "",
            "semester": semester or "",
            "exam": exam or "",
            "academic_year": academic_year or "",
            "pattern_id": pattern_id or "",
        })
        context["exam_choices"] = build_exam_choices(degree_id, semester)

        required = [regulation_id, degree_id, year, semester, exam, academic_year]

        if action == "save" and not all(required):
            messages.error(request, "Please complete all filters before saving.")
            if all(required):
                context["pattern_options"] = list_patterns_for_keys(
                    regulation_id, degree_id, year, semester, exam, academic_year
                )
            return render(request, "examination_management/question_entry/question.html", context)

        parts = parse_parts_json(parts_raw)
        if action == "save" and not parts:
            messages.error(request, "Add at least one Part in 'Create Pattern' and click Build Paper before saving.")
            if all(required):
                context["pattern_options"] = list_patterns_for_keys(
                    regulation_id, degree_id, year, semester, exam, academic_year
                )
            return render(request, "examination_management/question_entry/question.html", context)

        if action == "save":
            signature = pattern_signature(parts)

            with transaction.atomic():
                if pattern_id:
                    exam_pattern = get_pattern_by_id(pattern_id)
                    if not exam_pattern:
                        messages.error(request, "Selected pattern not found.")
                        if all(required):
                            context["pattern_options"] = list_patterns_for_keys(
                                regulation_id, degree_id, year, semester, exam, academic_year
                            )
                        return render(request, "examination_management/question_entry/question.html", context)

                    exam_pattern.regulation_id = regulation_id
                    exam_pattern.degree_id     = degree_id
                    exam_pattern.year          = year
                    exam_pattern.semester      = semester
                    exam_pattern.for_exam      = exam
                    exam_pattern.academic_year = academic_year
                    exam_pattern.pattern       = signature
                    exam_pattern.save()

                    Part.objects.filter(exam_pattern=exam_pattern).delete()
                else:
                    exam_pattern = ExamPattern.objects.create(
                        regulation_id=regulation_id,
                        degree_id=degree_id,
                        year=year,
                        semester=semester,
                        for_exam=exam,
                        academic_year=academic_year,
                        pattern=signature,
                    )

                # total questions per part
                totals_by_label = defaultdict(int)

                # max marks per part
                max_marks_by_label = defaultdict(int)

                for seg in parts:
                    label = seg["label"]
                    marks = int(seg["marks"])
                    count = int(seg["count"])

                    totals_by_label[label] += count
                    max_marks_by_label[label] = max(max_marks_by_label[label], marks)

                part_objs = {
                    label: Part.objects.create(
                        exam_pattern=exam_pattern,
                        name=label,
                        total_questions=total_q,
                        max_marks=max_marks_by_label[label],   # ✅ stored here
                    )
                    for label, total_q in totals_by_label.items()
                }

                questions_spec = OrderedDict()
                last_q = 0
                for seg in parts:
                    label = seg["label"]
                    marks = seg["marks"]
                    count = seg["count"]
                    start = seg.get("start")
                    q_start = start if (start and start > 0) else (last_q + 1)

                    for i in range(count):
                        q_num = q_start + i
                        questions_spec[q_num] = (part_objs[label], marks)

                    last_q = max(last_q, q_start + count - 1)

                q_objs = {}
                for q_num, (pobj, expected_marks) in questions_spec.items():
                    q_objs[q_num] = Question.objects.create(
                        part=pobj,
                        number=q_num,
                        total_marks=expected_marks
                    )

                for q_num, (_, expected_marks) in questions_spec.items():
                    if expected_marks >= 5:
                        for letter in ("a", "b"):
                            OptionMarks.objects.create(
                                question=q_objs[q_num],
                                option_letter=letter,
                                marks_i=0,
                                marks_ii=0
                            )

                updates = []
                for key, value in request.POST.items():
                    if not key.startswith("q") or "_" not in key:
                        continue

                    bits = key.split("_")
                    if len(bits) != 3:
                        continue

                    try:
                        q_number = int(bits[0][1:])
                    except ValueError:
                        continue

                    option_letter = bits[1]
                    subpart = bits[2]

                    if q_number not in questions_spec:
                        continue

                    _, expected_marks = questions_spec[q_number]
                    if expected_marks < 5:
                        continue

                    try:
                        ivalue = int(value)
                    except (TypeError, ValueError):
                        ivalue = 0

                    updates.append((q_number, option_letter, subpart, ivalue))

                for q_number, option_letter, subpart, ivalue in updates:
                    q_obj = q_objs[q_number]
                    opt_obj = q_obj.options.filter(option_letter=option_letter).first()
                    if not opt_obj:
                        opt_obj = OptionMarks.objects.create(
                            question=q_obj,
                            option_letter=option_letter,
                            marks_i=0,
                            marks_ii=0
                        )

                    if subpart == "i":
                        opt_obj.marks_i = ivalue
                    elif subpart == "ii":
                        opt_obj.marks_ii = ivalue
                    opt_obj.save()

                for q_num, (_, expected_marks) in questions_spec.items():
                    q_obj = q_objs[q_num]

                    if expected_marks < 5:
                        q_obj.total_marks = expected_marks
                    else:
                        opt_a = q_obj.options.filter(option_letter="a").first()
                        if opt_a:
                            total = ((opt_a.marks_i or 0) + (opt_a.marks_ii or 0))
                            q_obj.total_marks = total if total > 0 else expected_marks
                        else:
                            q_obj.total_marks = expected_marks

                    q_obj.save()

            messages.success(request, "Pattern saved successfully.")
            return redirect("question")

        if all([regulation_id, degree_id, year, semester, exam, academic_year]):
            context["pattern_options"] = list_patterns_for_keys(
                regulation_id, degree_id, year, semester, exam, academic_year
            )

        return render(request, "examination_management/question_entry/question.html", context)

    # ---------- GET ----------
    regulation_id = request.GET.get("regulation") or ""
    degree_id     = request.GET.get("degree") or ""
    year          = request.GET.get("year") or ""
    semester      = request.GET.get("semester") or ""
    exam          = request.GET.get("exam") or ""
    academic_year = request.GET.get("academic_year") or ""
    pattern_id    = request.GET.get("pattern_id") or ""

    if regulation_id:
        try:
            regulation_year = Regulations.objects.only("year").get(id=regulation_id).year
        except Regulations.DoesNotExist:
            regulation_year = ""
        context["selected"]["regulation_id"] = regulation_id
        context["selected"]["regulation_year"] = regulation_year

    context["selected"]["degree_id"] = degree_id
    context["selected"]["year"] = year
    context["selected"]["semester"] = semester
    context["selected"]["exam"] = exam
    context["selected"]["academic_year"] = academic_year
    context["selected"]["pattern_id"] = pattern_id

    context["exam_choices"] = build_exam_choices(degree_id, semester)

    if all([regulation_id, degree_id, year, semester, exam, academic_year]):
        context["pattern_options"] = list_patterns_for_keys(
            regulation_id, degree_id, year, semester, exam, academic_year
        )

    prefilled = {}
    if all([regulation_id, degree_id, year, semester, exam, academic_year]):
        prefilled = build_prefilled_latest(
            regulation_id, degree_id, year, semester, exam, academic_year
        )

    context["prefilled_questions"] = prefilled

    return render(request, "examination_management/question_entry/question.html", context)