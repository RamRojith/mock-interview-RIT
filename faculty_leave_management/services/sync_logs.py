# faculty_leave_management/services/sync_logs.py

from django.db import connections
from faculty_leave_management.models import DeviceLogLocal
import re
from django.utils import timezone
import pytz


def sync_punch_to_local(userid=None):

    cursor = connections['attendance_db'].cursor()

    cursor.execute("""
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME LIKE 'DeviceLogs_%_%'
    """)

    tables = [row[0] for row in cursor.fetchall()]
    tables.sort()  # ✅ consistent order

    ist = pytz.timezone("Asia/Kolkata")

    total_processed = 0
    total_inserted = 0
    total_errors = 0

    # ✅ store table summary
    table_summary = []

    for table_name in tables:
        print(f"\n🔄 Processing Table: {table_name}")

        table_processed = 0
        table_inserted = 0
        table_errors = 0

        try:
            match = re.search(r'DeviceLogs_(\d+)_(\d+)', table_name)
            if not match:
                print(f"⛔ Skipping invalid table: {table_name}")
                continue

            month, year = match.groups()

            query = f"""
                SELECT DeviceLogId, DeviceId, UserId, LogDate, Direction
                FROM {table_name}
            """

            params = []

            if userid:
                query += " WHERE UserId = %s"
                params.append(userid)

            cursor.execute(query, params)

            columns = [col[0] for col in cursor.description]

            BATCH_SIZE = 1000

            while True:
                rows = cursor.fetchmany(BATCH_SIZE)

                if not rows:
                    break

                data = [dict(zip(columns, row)) for row in rows]
                table_processed += len(data)

                new_records = []

                for row in data:
                    try:
                        logdate = row["LogDate"]

                        # ✅ Fix timezone warning
                        if logdate and timezone.is_naive(logdate):
                            logdate = timezone.make_aware(logdate, ist)

                        new_records.append(DeviceLogLocal(
                            devicelogid=row["DeviceLogId"],
                            deviceid=row["DeviceId"],
                            userid=row["UserId"],
                            logdate=logdate,
                            direction=row["Direction"],
                            month=month,
                            year=year,
                        ))

                    except Exception as e:
                        table_errors += 1
                        print(f"❌ Row Error: {e}")

                if new_records:
                    DeviceLogLocal.objects.bulk_create(
                        new_records,
                        ignore_conflicts=True,
                        batch_size=1000
                    )
                    table_inserted += len(new_records)

            print(f"✅ {table_name} DONE")

            if table_inserted > 0:
                print(f"🔥 DATA INSERTED for {month}/{year}")

            # ✅ Save summary
            table_summary.append({
                "table": table_name,
                "rows": table_processed,
                "inserted": table_inserted
            })

            total_processed += table_processed
            total_inserted += table_inserted
            total_errors += table_errors

        except Exception as e:
            print(f"❌ TABLE ERROR: {table_name} → {e}")
            total_errors += 1

    # 🔥 FINAL OUTPUT (LIKE YOUR IMAGE)
    print("\n=========== TABLE WISE COUNT ===========")
    print(f"{'TableName':<30} {'TotalRows':>10} {'Inserted':>10}")
    print("-" * 55)

    total_rows = 0

    for item in table_summary:
        print(f"{item['table']:<30} {item['rows']:>10} {item['inserted']:>10}")
        total_rows += item['rows']

    print("-" * 55)
    print(f"{'TOTAL':<30} {total_rows:>10} {total_inserted:>10}")

    print("\n=========== FINAL SUMMARY ===========")
    print(f"📊 Total Processed: {total_processed}")
    print(f"✅ Total Inserted: {total_inserted}")
    print(f"❌ Total Errors: {total_errors}")