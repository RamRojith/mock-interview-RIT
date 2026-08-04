# utils_intake.py (place alongside your views or in a utils module)
import re
from typing import Optional
from django.db.models import Q

from nba.models import SanctionedIntake

YEAR_RE = re.compile(r"^(19|20)\d{2}$")

def _to_year_int(year_str: str) -> Optional[int]:
    if not year_str:
        return None
    s = str(year_str).strip()
    if YEAR_RE.match(s):
        try:
            return int(s)
        except ValueError:
            return None
    return None

def get_effective_intake(department_id: int, degree_id: int, target_year: int) -> int:
    """
    Return the sanctioned_intake for the latest record with year <= target_year.
    If nothing matches, return 0.
    """
    qs = SanctionedIntake.objects.filter(
        department_id=department_id,
        degree_id=degree_id
    ).values("year", "sanctioned_intake")

    # Pull to Python; robust across DBs and string year storage
    best_year = None
    best_intake = 0

    for row in qs:
        y = _to_year_int(row.get("year"))
        if y is None:
            continue
        if y <= target_year and (best_year is None or y > best_year):
            best_year = y
            best_intake = int(row.get("sanctioned_intake") or 0)

    return best_intake
