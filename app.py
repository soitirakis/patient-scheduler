import os
from datetime import date, datetime
from io import BytesIO

import qrcode
from flask import (
    Flask,
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

app = Flask(__name__)

# Bookable 30-minute slots within business hours, 09:00 through 17:00
# inclusive. Used both to render the form dropdown and to validate
# submitted times.
TIME_SLOTS = [
    f"{minutes // 60:02d}:{minutes % 60:02d}"
    for minutes in range(9 * 60, 17 * 60 + 1, 30)
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
                "Please choose a time on the half hour between 09:00 and 17:00."
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


@app.route("/appointments")
def appointments():
    search = request.args.get("q", "").strip()
    return render_template(
        "appointments.html",
        appointments=get_appointments(search or None),
        search=search,
    )


@app.route("/appointments/<int:appointment_id>/cancel", methods=["POST"])
def cancel_appointment(appointment_id):
    delete_appointment(appointment_id)
    return redirect(url_for("appointments"))


@app.route("/qr")
def qr():
    booking_url = url_for("book", _external=True)
    return render_template("qr.html", booking_url=booking_url)


@app.route("/qr.png")
def qr_png():
    booking_url = url_for("book", _external=True)
    image = qrcode.make(booking_url)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return send_file(buffer, mimetype="image/png")


@app.route("/export")
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
    app.run(debug=True, port=port)
