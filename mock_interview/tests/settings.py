"""Isolated settings for mock-interview SimpleTestCase tests.

The project has an optional SQL Server attendance database. Its backend is not
needed for these unit tests and is not installed in every development machine.
"""

from rit_academic_system.settings import *  # noqa: F403


DATABASES["default"] = {  # noqa: F405
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": ":memory:",
}
DATABASES["attendance_db"] = {  # noqa: F405
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": ":memory:",
}
