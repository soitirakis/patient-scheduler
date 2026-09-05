import os
import secrets
from datetime import date, datetime
from functools import wraps
from io import BytesIO
from itertools import groupby

from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
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
from generate_qr import QR_PATH, generate_qr

app = Flask(__name__)

# Ensure the database schema exists before handling any requests, so no
# manual setup step is needed locally or on first deploy (e.g. PythonAnywhere).
init_db()

# Staff credentials for HTTP Basic Auth on /appointments and /export.
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
        auth = request.authorization
        valid = (
            STAFF_USERNAME
            and STAFF_PASSWORD
            and auth
            and secrets.compare_digest(auth.username or "", STAFF_USERNAME)
            and secrets.compare_digest(auth.password or "", STAFF_PASSWORD)
        )
        if not valid:
            return Response(
                "Authentication required.",
                401,
                {"WWW-Authenticate": 'Basic realm="Staff Area"'},
            )
        return view(*args, **kwargs)

    return wrapped

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
    # Render a printable page around the generated QR image, regenerating the
    # image on the fly if it's missing so /qr always shows a working code. The
    # PNG itself stays available at /static/qr_code.png.
    if not os.path.exists(QR_PATH):
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
