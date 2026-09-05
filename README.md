# patient-scheduler

A simple patient scheduling web app built with Flask and SQLite.

## Features

- **Booking form** — patients enter their name, contact, date, and time.
- **Double-booking prevention** — a UNIQUE constraint on date/time blocks conflicting bookings at the database level.
- **Appointment list** — view all booked appointments in a table.
- **Cancellation** — cancel a booking from the appointment list, freeing its slot.
- **QR code** — a scannable code that links directly to the booking form.
- **Excel export** — download all appointments as an `.xlsx` file.

## Installation

Install the dependencies (a virtual environment is recommended):

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running

```bash
python app.py
```

The app will start on http://127.0.0.1:5000/ and initialize the SQLite database (`db.sqlite3`) on first run.

To run on a different port (e.g. if port 5000 is already in use, as it is by AirPlay Receiver on macOS), set the `PORT` environment variable:

```bash
PORT=5001 python app.py
```

## Routes

| Route      | Description                                        |
| ---------- | -------------------------------------------------- |
| `/`        | Health check (returns `OK`).                       |
| `/book`    | Booking form (GET to view, POST to submit).        |
| `/appointments` | List all booked appointments in a table.      |
| `/appointments/<id>/cancel` | Cancel an appointment (POST).      |
| `/qr`      | Page displaying a QR code linking to `/book`.      |
| `/qr.png`  | The QR code image itself (PNG).                    |
| `/export`  | Download all appointments as `appointments.xlsx`.  |
