from io import BytesIO

import qrcode
from flask import Flask, redirect, render_template, request, send_file, url_for

from db import SlotTakenError, create_appointment, init_db

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


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
