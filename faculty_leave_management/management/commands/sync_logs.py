# faculty_leave_management/management/commands/sync_logs.py

from django.core.management.base import BaseCommand
from faculty_leave_management.services.sync_logs import sync_punch_to_local

class Command(BaseCommand):
    help = "Sync biometric logs"

    def handle(self, *args, **kwargs):
        sync_punch_to_local()
        self.stdout.write(self.style.SUCCESS("✅ Sync completed"))