from io import BytesIO

import qrcode
from flask import Flask, redirect, render_template, request, send_file, url_for
from openpyxl import Workbook

from db import (
    SlotTakenError,
    create_appointment,
    get_appointments,
    init_db,
)

app = Flask(__name__)


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

        if not all([patient_name, patient_contact, appointment_date, appointment_time]):
            return render_template(
                "book.html",
                error="All fields are required.",
                form=request.form,
            )

        try:
            create_appointment(
                patient_name, patient_contact, appointment_date, appointment_time
            )
        except SlotTakenError as exc:
            return render_template(
                "book.html",
                error=str(exc),
                form=request.form,
            )

        return redirect(url_for("book", booked=1))

    return render_template("book.html", booked=request.args.get("booked"))


@app.route("/appointments")
def appointments():
    return render_template("appointments.html", appointments=get_appointments())


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
    app.run(debug=True)
