import sqlite3

DB_PATH = "db.sqlite3"


def get_connection():
    """Return a SQLite connection with row access by column name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the database schema if it does not already exist."""
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_name TEXT NOT NULL,
                patient_contact TEXT NOT NULL,
                appointment_date TEXT NOT NULL,
                appointment_time TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (appointment_date, appointment_time)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def get_appointments(search=None):
    """Return appointments ordered by date and time.

    If ``search`` is given, only appointments whose name, contact, or date
    contains that text (case-insensitive) are returned.
    """
    conn = get_connection()
    try:
        query = """
            SELECT id, patient_name, patient_contact,
                   appointment_date, appointment_time, created_at
            FROM appointments
        """
        params = ()
        if search:
            query += """
            WHERE patient_name LIKE ?
               OR patient_contact LIKE ?
               OR appointment_date LIKE ?
            """
            like = f"%{search}%"
            params = (like, like, like)
        query += " ORDER BY appointment_date, appointment_time"
        rows = conn.execute(query, params).fetchall()
        return rows
    finally:
        conn.close()


def get_booked_times(appointment_date):
    """Return a list of already-booked times for the given date."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT appointment_time
            FROM appointments
            WHERE appointment_date = ?
            ORDER BY appointment_time
            """,
            (appointment_date,),
        ).fetchall()
        return [row["appointment_time"] for row in rows]
    finally:
        conn.close()


def delete_appointment(appointment_id):
    """Delete an appointment by id. Returns True if a row was removed."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM appointments WHERE id = ?", (appointment_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


class SlotTakenError(Exception):
    """Raised when the requested date/time slot is already booked."""


def create_appointment(patient_name, patient_contact, appointment_date, appointment_time):
    """Insert a new appointment.

    Raises SlotTakenError if the date/time slot is already booked
    (enforced by the UNIQUE constraint on appointment_date/appointment_time).
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO appointments (
                patient_name, patient_contact, appointment_date, appointment_time
            ) VALUES (?, ?, ?, ?)
            """,
            (patient_name, patient_contact, appointment_date, appointment_time),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        raise SlotTakenError(
            f"The slot on {appointment_date} at {appointment_time} is already booked."
        )
    finally:
        conn.close()
