import sqlite3
from datetime import datetime, timedelta

from job_finder.settings import COMPANIES, SQLITE_DB_PATH, SQLITE_NEW_TABLE_NAME, THRESHOLD_NO_APPEAR_DAYS
from dateutil import parser


def main():
    # Connect to the SQLite database
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    # Create the NO_APPEARR table if it doesn't exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS NO_APPEARR (
        company TEXT PRIMARY KEY
    )
    """)

    # Define the date threshold (THRESHOLD_NO_APPEAR_DAYS days ago)
    threshold_date = datetime.now() - timedelta(days=THRESHOLD_NO_APPEAR_DAYS)

    # Check each company
    for company in COMPANIES:
        # Query to get the most recent entry for the company in the table
        cursor.execute(f"""
        SELECT MAX(created_at) FROM {SQLITE_NEW_TABLE_NAME} WHERE company = ?
        """, (company,))
        result = cursor.fetchone()

        if result[0] is None:
            # Company not in JOBS table, add it to NO_APPEARR
            cursor.execute("""
            INSERT OR IGNORE INTO NO_APPEARR (company) VALUES (?)
            """, (company,))
        else:
            last_date = parser.parse(result[0])
            if last_date < threshold_date:
                # The most recent entry is older than THRESHOLD_NO_APPEAR_DAYS days, add company to NO_APPEARR
                cursor.execute("""
                INSERT OR IGNORE INTO NO_APPEARR (company) VALUES (?)
                """, (company,))
            else:
                # The most recent entry is within the last THRESHOLD_NO_APPEAR_DAYS days, delete the company from NO_APPEARR (if exists)
                cursor.execute("""
                DELETE FROM NO_APPEARR WHERE company = ?
                """, (company,))

    # Commit the changes and close the connection
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
