# tests-java

Selenium + TestNG UI tests for the patient-scheduler booking flow, written as a
standalone Maven project. Nothing here is imported by the Python app — it drives
the app from the outside through a real Chrome window.

## Prerequisites

- JDK 17 or newer
- Maven 3.8+
- Google Chrome installed (the matching ChromeDriver is fetched automatically by
  [WebDriverManager](https://bonigarcia.dev/webdrivermanager/) — no manual driver
  download, and nothing needs to be on your PATH)

## Running the tests

**The Flask app must already be running.** These are end-to-end tests against a
live server; they do not start or stop it for you.

1. From the repository root, start the app:

   ```bash
   python3 app.py
   ```

   Note the URL it prints on startup. The app listens on port 5000 by default,
   but honours the `PORT` environment variable, and on macOS port 5000 is
   usually taken by AirPlay Receiver — hence `PORT=5001 python3 app.py`.

2. From inside `tests-java/`, run:

   ```bash
   mvn test
   ```

To run headless (no visible browser window):

```bash
mvn test -Dheadless=true
```

To run a single test:

```bash
mvn test -Dtest=BookingTests#testDoubleBookingPrevented
```

## Pointing at a different port

`BASE_URL` is a single constant at the top of
`src/test/java/com/patientscheduler/tests/BookingTests.java`:

```java
private static final String BASE_URL = "http://127.0.0.1:5001";
```

It currently points at port **5001**. Change it to match whatever port your
Flask app actually printed on startup.

## Layout

```
tests-java/
├── pom.xml
└── src/test/java/com/patientscheduler/
    ├── pages/
    │   ├── BookingPage.java        # page object for /book
    │   └── ConfirmationPage.java   # page object for /book/confirmed
    └── tests/
        └── BookingTests.java       # the TestNG test cases
```

The tests follow the Page Object Model: locators live only in the `pages`
classes, and the test methods read as a sequence of user actions. `BookingPage`
locates fields by the ids in `templates/book.html` — `patient_name`,
`patient_contact`, `appointment_date` and `appointment_time`.

## Test cases

| Test | What it checks |
| --- | --- |
| `testSuccessfulBooking` | A valid future date and time submit successfully and land on the confirmation page, which echoes back the booked date and time. |
| `testDoubleBookingPrevented` | Booking a slot, then booking the exact same date and time again, shows the "already booked" error instead of a second confirmation. |
| `testMissingRequiredFields` | Submitting with an empty name is blocked by Chrome's own HTML5 `required` validation — the browser stays on `/book` and the field reports a validation message. |
| `testPastDateRejected` | A date in the past is rejected with the "cannot be in the past" error. |

## Notes

- **Bookings persist.** The app stores appointments in `db.sqlite3`, so a slot
  booked by one test run stays booked. Each run therefore picks a random
  far-future base date and gives every test its own day, which keeps the tests
  independent and re-runnable without clearing the database. Rows do accumulate
  across runs; delete `db.sqlite3` and restart the app if you want a clean
  slate.
- **The past-date test relaxes one client-side attribute.** The date input is
  rendered with `min="<today>"`, so Chrome refuses to submit a past date and the
  server-side check would never run. `BookingPage.allowPastDates()` removes that
  attribute in the browser so the form actually posts. This only affects the
  loaded page in the test browser — the app's templates and code are untouched.
- **Time slots are read from the page,** not hardcoded. The tests select
  whatever the dropdown offers, so changing the slot range in `app.py` does not
  break them.
