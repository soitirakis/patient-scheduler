"""Remove known test/sample appointments before production use.

Dry run (default) -- prints the rows that match, changes nothing:

    python clean_test_data.py

Actually delete them:

    python clean_test_data.py --yes

The matching rules below describe the Selenium fixtures and manual test
bookings used during development. Back up db.sqlite3 before deleting; the
rows cannot be recovered otherwise.
"""

import argparse
import sys

from db import get_connection

# Rows considered test data. Kept as one SQL condition so the dry run and the
# delete can never diverge. Note SQLite's LIKE is case-insensitive for ASCII,
# so '%Example%' also matches addresses like bob@example.com.
TEST_DATA_CONDITION = """
    patient_name LIKE '%Example%'
    OR patient_contact LIKE '%Example%'
    OR (patient_name = 'Andrei Anghel' AND patient_contact = '0747572755')
    OR (patient_name = 'Bob' AND patient_contact = 'b@x.com')
"""


def find_test_appointments(conn):
    """Return the appointment rows that match the test-data rules."""
    return list(
        conn.execute(
            f"SELECT * FROM appointments WHERE {TEST_DATA_CONDITION} ORDER BY id"
        )
    )


def delete_test_appointments(conn):
    """Delete the matching rows and return how many were removed."""
    with conn:
        cursor = conn.execute(f"DELETE FROM appointments WHERE {TEST_DATA_CONDITION}")
    return cursor.rowcount


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--yes",
        action="store_true",
        help="actually delete the matching rows (default is a dry run)",
    )
    args = parser.parse_args()

    conn = get_connection()
    try:
        matches = find_test_appointments(conn)
        total = conn.execute("SELECT COUNT(*) FROM appointments").fetchone()[0]

        if not matches:
            print(f"No test appointments found ({total} row(s) in table).")
            return 0

        print(f"{len(matches)} of {total} row(s) match the test-data rules:")
        for row in matches:
            print(
                f"  id={row['id']:<4} {row['patient_name']:<16}"
                f" {row['patient_contact']:<20}"
                f" {row['appointment_date']} {row['appointment_time']}"
            )

        if not args.yes:
            print("\nDry run -- nothing deleted. Re-run with --yes to delete.")
            return 0

        deleted = delete_test_appointments(conn)
        remaining = conn.execute("SELECT COUNT(*) FROM appointments").fetchone()[0]
        print(f"\nDeleted {deleted} row(s). {remaining} row(s) remaining.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
