import os
import secrets
from datetime import date, datetime, timedelta
from functools import wraps
from io import BytesIO
from itertools import groupby

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from openpyxl import Workbook

from db import (
    SlotTakenError,
    create_appointment,
    delete_appointment,
    get_appointments,
    get_booked_times,
    init_db,
)
from generate_qr import generate_qr

app = Flask(__name__)

# Secret key used to sign session cookies. Set FLASK_SECRET_KEY as a
# permanent, random value in production (e.g. via `python -c "import
# secrets; print(secrets.token_hex(32))"`), so sessions survive app
# restarts. If it's not set, a random key is generated on startup -- staff
# will simply be logged out any time the app restarts.
FLASK_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")

if not FLASK_SECRET_KEY:
    FLASK_SECRET_KEY = secrets.token_hex(32)
    print(
        "WARNING: FLASK_SECRET_KEY environment variable is not set. Using a "
        "randomly generated key for this process, so all staff sessions will "
        "be invalidated on every restart. Set a permanent FLASK_SECRET_KEY "
        "to keep sessions persistent."
    )

app.secret_key = FLASK_SECRET_KEY
app.permanent_session_lifetime = timedelta(minutes=30)

# Ensure the database schema exists before handling any requests, so no
# manual setup step is needed locally or on first deploy (e.g. PythonAnywhere).
init_db()

# Staff credentials checked against the /login form.
#
# Locally, set these before running the app, e.g.:
#   export STAFF_USERNAME=someusername
#   export STAFF_PASSWORD=somepassword
#   python app.py
#
# In production (PythonAnywhere), set STAFF_USERNAME and STAFF_PASSWORD as
# environment variables in the "Web" tab's WSGI configuration / dashboard --
# do not hardcode real credentials in this file or commit them anywhere.
STAFF_USERNAME = os.environ.get("STAFF_USERNAME")
STAFF_PASSWORD = os.environ.get("STAFF_PASSWORD")

if not STAFF_USERNAME or not STAFF_PASSWORD:
    print(
        "WARNING: STAFF_USERNAME and/or STAFF_PASSWORD environment variables "
        "are not set. Authentication is NOT configured and /appointments and "
        "/export are currently UNPROTECTED."
    )


def require_staff_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            next_url = request.full_path if request.query_string else request.path
            return redirect(url_for("login", next=next_url))
        return view(*args, **kwargs)

    return wrapped


def _safe_next_url(next_url):
    """Only allow redirecting back to a same-site path after login, to avoid
    an open redirect via a crafted `next` value."""
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return url_for("appointments")

# Bookable slots within business hours, from SLOT_START_MINUTES through
# SLOT_END_MINUTES inclusive, spaced SLOT_INTERVAL_MINUTES apart. Adjust
# these three values to change the schedule. Used both to render the form
# dropdown and to validate submitted times.
SLOT_START_MINUTES = 14 * 60
SLOT_END_MINUTES = 15 * 60
SLOT_INTERVAL_MINUTES = 10

TIME_SLOTS = [
    f"{minutes // 60:02d}:{minutes % 60:02d}"
    for minutes in range(
        SLOT_START_MINUTES, SLOT_END_MINUTES + 1, SLOT_INTERVAL_MINUTES
    )
]


@app.route("/")
def index():
    return "OK"


@app.route("/book", methods=["GET", "POST"])
def book():
    if request.method == "POST":
        patient_name = request.form.get("patient_name", "").strip()
        patient_contact = request.form.get("patient_contact", "").strip()
        appointment_date = request.form.get("appointment_date", "").strip()
        appointment_time = request.form.get("appointment_time", "").strip()

        def show_error(message):
            return render_template(
                "book.html",
                error=message,
                form=request.form,
                time_slots=TIME_SLOTS,
                today=date.today().isoformat(),
            )

        if not all([patient_name, patient_contact, appointment_date, appointment_time]):
            return show_error("All fields are required.")

        try:
            parsed_date = datetime.strptime(appointment_date, "%Y-%m-%d").date()
        except ValueError:
            return show_error("Please enter a valid date.")

        if parsed_date < date.today():
            return show_error("The appointment date cannot be in the past.")

        if appointment_time not in TIME_SLOTS:
            return show_error(
                f"Please choose a time in {SLOT_INTERVAL_MINUTES}-minute "
                f"increments between {TIME_SLOTS[0]} and {TIME_SLOTS[-1]}."
            )

        try:
            create_appointment(
                patient_name, patient_contact, appointment_date, appointment_time
            )
        except SlotTakenError:
            return show_error(
                "This time slot is already booked. Please choose another."
            )

        return redirect(
            url_for(
                "book_confirmed", date=appointment_date, time=appointment_time
            )
        )

    return render_template(
        "book.html",
        time_slots=TIME_SLOTS,
        today=date.today().isoformat(),
    )


@app.route("/book/confirmed")
def book_confirmed():
    return render_template(
        "confirmed.html",
        appointment_date=request.args.get("date"),
        appointment_time=request.args.get("time"),
    )


@app.route("/available/<appointment_date>")
def available(appointment_date):
    return jsonify(
        {
            "date": appointment_date,
            "booked_times": get_booked_times(appointment_date),
        }
    )


def group_appointments_by_date(rows):
    """Group appointment rows (already ordered by date, then time) into
    per-day buckets for the collapsible /appointments view."""
    groups = []
    for appointment_date, day_rows in groupby(rows, key=lambda r: r["appointment_date"]):
        day_rows = list(day_rows)
        try:
            parsed = datetime.strptime(appointment_date, "%Y-%m-%d")
            display_date = f"{parsed.strftime('%A, %B')} {parsed.day}, {parsed.year}"
        except ValueError:
            display_date = appointment_date
        groups.append(
            {
                "date": appointment_date,
                "display_date": display_date,
                "count": len(day_rows),
                "appointments": day_rows,
            }
        )
    return groups


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        valid = (
            STAFF_USERNAME
            and STAFF_PASSWORD
            and secrets.compare_digest(username, STAFF_USERNAME)
            and secrets.compare_digest(password, STAFF_PASSWORD)
        )
        if valid:
            session["logged_in"] = True
            session.permanent = True
            return redirect(_safe_next_url(request.form.get("next")))
        return render_template(
            "login.html", error="Invalid credentials.", next=request.form.get("next")
        )

    return render_template(
        "login.html",
        message=request.args.get("message"),
        next=request.args.get("next"),
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login", message="You have been logged out."))


@app.route("/appointments")
@require_staff_auth
def appointments():
    search = request.args.get("q", "").strip()
    return render_template(
        "appointments.html",
        appointment_groups=group_appointments_by_date(get_appointments(search or None)),
        search=search,
    )


@app.route("/appointments/<int:appointment_id>/cancel", methods=["POST"])
def cancel_appointment(appointment_id):
    delete_appointment(appointment_id)
    return redirect(url_for("appointments"))


@app.route("/qr")
def qr():
    # Render a printable page around the generated QR image. The image is
    # regenerated fresh on every request so it always encodes the current
    # BASE_URL rather than reusing a possibly-stale cached PNG. The file
    # itself stays available at /static/qr_code.png.
    generate_qr()
    return render_template("qr.html")


@app.route("/export")
@require_staff_auth
def export():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Appointments"

    headers = [
        "ID",
        "Patient Name",
        "Contact",
        "Date",
        "Time",
        "Created At",
    ]
    sheet.append(headers)

    for row in get_appointments():
        sheet.append(
            [
                row["id"],
                row["patient_name"],
                row["patient_contact"],
                row["appointment_date"],
                row["appointment_time"],
                row["created_at"],
            ]
        )

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="appointments.xlsx",
    )


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes", "on")
    # Debug mode is off unless FLASK_DEBUG is set. Only enable it locally during
    # development (e.g. `FLASK_DEBUG=1 python app.py`) -- never in production, where
    # the reloader and the interactive debugger's remote code execution are unsafe.
    app.run(host="0.0.0.0", debug=debug, port=port)
