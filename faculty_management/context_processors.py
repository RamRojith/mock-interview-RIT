from faculty_management.models import general_information

# All fields the employee must fill — pay details (basic_pay, agp, allowances, pay_scale_notes) excluded
_FIELDS = [
    # (model_field,                     friendly_label,              fa_icon,          group)
    # ── Personal ──────────────────────────────────────────────────────────────
    ('gender',                          'Gender',                    'venus-mars',     'Personal'),
    ('dob',                             'Date of Birth',             'cake-candles',   'Personal'),
    ('phone',                           'Phone Number',              'phone',          'Personal'),
    ('personal_email',                  'Personal Email',            'envelope',       'Personal'),
    ('address',                         'Address',                   'location-dot',   'Personal'),
    ('blood_group',                     'Blood Group',               'droplet',        'Personal'),
    # ── Demographics ──────────────────────────────────────────────────────────
    ('community',                       'Community',                 'people-group',   'Personal'),
    ('caste',                           'Caste',                     'list-ul',        'Personal'),
    ('religion',                        'Religion',                  'place-of-worship','Personal'),
    # ── Identity & IDs ────────────────────────────────────────────────────────
    ('PAN_number',                      'PAN Number',                'id-card',        'Documents'),
    ('Aadhar_number',                   'Aadhaar Number',            'id-badge',       'Documents'),
    ('apaar_id',                        'APAAR ID',                  'fingerprint',    'Documents'),
    ('anu_id',                          'Anna University ID',        'university',     'Documents'),
    ('aicte_id',                        'AICTE ID',                  'building-columns','Documents'),
    ('annauniversity_affiliation_id',   'Anna Univ. Affiliation ID', 'link',           'Documents'),
    # ── Document Uploads ──────────────────────────────────────────────────────
    ('PAN_certificate',                 'PAN Certificate (PDF)',      'file-pdf',       'Documents'),
    ('Aadhar_certificate',              'Aadhaar Certificate (PDF)', 'file-pdf',       'Documents'),
    # ── Employment / Service ──────────────────────────────────────────────────
    ('doj',                             'Date of Joining',           'calendar-days',  'Employment'),
    ('appointment_type',                'Appointment Type',          'briefcase',      'Employment'),
    ('recruitment_mode',                'Recruitment Mode',          'clipboard-list', 'Employment'),
    ('nature_of_duties',                'Nature of Duties',          'list-check',     'Employment'),
]

_TOTAL = len(_FIELDS)


def _is_empty(val):
    if val is None:
        return True
    if hasattr(val, 'name'):      # FileField
        return not val.name
    return str(val).strip() == ''


def profile_completion(request):
    if not request.user.is_authenticated:
        return {}

    emp_id = getattr(request.user, 'Employee_id', None)
    if not emp_id:
        return {}

    if getattr(request.user, 'is_student', False):
        return {}

    try:
        faculty_id_int = int(str(emp_id).strip())
    except (ValueError, TypeError):
        return {}

    try:
        faculty = general_information.objects.filter(faculty_id=faculty_id_int).first()
        if not faculty:
            return {}

        missing = [
            {'field': f, 'label': lbl, 'icon': ico, 'group': grp}
            for f, lbl, ico, grp in _FIELDS
            if _is_empty(getattr(faculty, f, None))
        ]

        filled = _TOTAL - len(missing)
        pct    = round(filled / _TOTAL * 100) if _TOTAL else 100

        return {
            'profile_missing_fields': missing,
            'profile_missing_count':  len(missing),
            'profile_completion_pct': pct,
            'profile_faculty_db_id':  faculty.id,
        }
    except Exception:
        return {}
