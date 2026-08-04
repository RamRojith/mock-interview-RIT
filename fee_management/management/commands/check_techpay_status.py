import requests
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from fee_management.models import Transaction
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Checks and updates TechPay payment status for recent pending transactions.'

    def handle(self, *args, **kwargs):
        fifteen_days_ago = timezone.now() - timedelta(days=15)

        transactions = Transaction.objects.filter(
            transaction_token__isnull=False,
            decision='PENDING',
            created_at__gte=fifteen_days_ago
        )

        self.stdout.write(f"Found {transactions.count()} pending transactions with tokens.")

        for txn in transactions:
            payload = {
                "token": txn.transaction_token,
                "merchantApiKey": settings.TECHPAY_API_KEY,
                "merchantApiID": settings.TECHPAY_API_ID
            }

            headers = {"Content-Type": "application/json"}

            try:
                response = requests.post(
                    "https://new.techpay.co.zm/api/v1/hc/statuscheck",
                    json=payload,
                    headers=headers,
                    timeout=10
                )

                data = response.json()
                status = data.get("status", "").upper()

                logger.info(f"Transaction {txn.transaction_uuid} - API Status: {status}")

                if status == "COMPLETE":
                    txn.decision = "SUCCESS"
                elif status == "CANCELLED":
                    txn.decision = "CANCELLED"
                elif status == "FAILED":
                    txn.decision = "FAILED"
                else:
                    continue  # Skip unrecognized statuses

                txn.save()

            except Exception as e:
                logger.error(f"Error updating transaction {txn.transaction_uuid}: {str(e)}")
                continue
