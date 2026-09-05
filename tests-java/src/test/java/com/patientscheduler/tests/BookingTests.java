package com.patientscheduler.tests;

import java.time.LocalDate;
import java.util.Random;
import java.util.concurrent.atomic.AtomicInteger;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;
import org.testng.annotations.AfterClass;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.Test;

import com.patientscheduler.pages.BookingPage;
import com.patientscheduler.pages.ConfirmationPage;

import io.github.bonigarcia.wdm.WebDriverManager;

import static org.testng.Assert.assertEquals;
import static org.testng.Assert.assertFalse;
import static org.testng.Assert.assertTrue;

/**
 * End-to-end tests for the booking flow.
 *
 * <p>Requires the Flask app to already be running locally — see README.md.
 */
public class BookingTests {

    /**
     * Root URL of the running Flask app. The app defaults to port 5000 but
     * honours the PORT environment variable, and on macOS port 5000 is often
     * taken by AirPlay Receiver — change the port here to match whatever
     * `python3 app.py` actually printed on startup.
     */
    private static final String BASE_URL = "http://127.0.0.1:5000";

    /**
     * Bookings persist in db.sqlite3, so a slot booked by one run cannot be
     * booked again by the next. Each run picks a random far-future starting
     * date and each test takes the next day after that, which keeps tests
     * independent of each other and re-runnable without clearing the database.
     */
    private static final LocalDate RUN_BASE_DATE =
            LocalDate.now().plusDays(1 + new Random().nextInt(9000));

    private static final AtomicInteger DATE_OFFSET = new AtomicInteger();

    private WebDriver driver;
    private BookingPage bookingPage;
    private ConfirmationPage confirmationPage;

    @BeforeClass
    public void setUp() {
        // Downloads and wires up a ChromeDriver matching the installed Chrome.
        WebDriverManager.chromedriver().setup();

        ChromeOptions options = new ChromeOptions();
        options.addArguments("--window-size=1280,900");
        if (Boolean.parseBoolean(System.getProperty("headless", "false"))) {
            options.addArguments("--headless=new");
        }

        driver = new ChromeDriver(options);
        bookingPage = new BookingPage(driver, BASE_URL);
        confirmationPage = new ConfirmationPage(driver);
    }

    @AfterClass(alwaysRun = true)
    public void tearDown() {
        if (driver != null) {
            driver.quit();
        }
    }

    @Test
    public void testSuccessfulBooking() {
        LocalDate date = nextUnusedDate();

        bookingPage.open();
        String time = bookingPage.getFirstAvailableTimeSlot();

        bookingPage.enterPatientName("Alice Example")
                .enterPatientContact("alice@example.com")
                .enterAppointmentDate(date)
                .selectAppointmentTime(time)
                .submit();

        confirmationPage.waitUntilDisplayed();

        assertTrue(confirmationPage.isDisplayed(),
                "Expected the confirmation page after submitting a valid booking.");
        assertTrue(confirmationPage.getBannerText().contains("booked"),
                "Expected a confirmation banner, got: " + confirmationPage.getBannerText());
        assertEquals(confirmationPage.getAppointmentDate(), date.toString(),
                "Confirmation page shows the wrong date.");
        assertEquals(confirmationPage.getAppointmentTime(), time,
                "Confirmation page shows the wrong time.");
    }

    @Test
    public void testDoubleBookingPrevented() {
        LocalDate date = nextUnusedDate();

        bookingPage.open();
        String time = bookingPage.getFirstAvailableTimeSlot();

        // First booking: should succeed and take the slot.
        bookingPage.enterPatientName("Bob Example")
                .enterPatientContact("bob@example.com")
                .enterAppointmentDate(date)
                .selectAppointmentTime(time)
                .submit();

        confirmationPage.waitUntilDisplayed();
        assertTrue(confirmationPage.isDisplayed(),
                "The first booking of a free slot should have been confirmed.");

        // Second booking of the exact same date and time: should be refused.
        bookingPage.open()
                .enterPatientName("Carol Example")
                .enterPatientContact("carol@example.com")
                .enterAppointmentDate(date)
                .selectAppointmentTime(time)
                .submit();

        assertFalse(driver.getCurrentUrl().contains(ConfirmationPage.PATH),
                "Double booking the same slot should not reach the confirmation page.");
        assertTrue(bookingPage.isErrorDisplayed(),
                "Expected an error message when double booking a slot.");
        assertTrue(bookingPage.getErrorMessage().contains("already booked"),
                "Expected an 'already booked' error, got: " + bookingPage.getErrorMessage());
    }

    @Test
    public void testMissingRequiredFields() {
        LocalDate date = nextUnusedDate();

        bookingPage.open();
        String time = bookingPage.getFirstAvailableTimeSlot();

        // Name deliberately left empty; the input carries the `required`
        // attribute, so Chrome should block the submit itself.
        bookingPage.enterPatientContact("dave@example.com")
                .enterAppointmentDate(date)
                .selectAppointmentTime(time)
                .submit();

        assertTrue(driver.getCurrentUrl().contains(BookingPage.PATH),
                "Native validation should keep the browser on /book.");
        assertFalse(driver.getCurrentUrl().contains(ConfirmationPage.PATH),
                "An empty name should never reach the confirmation page.");
        assertTrue(bookingPage.isDisplayed(),
                "The booking form should still be on screen.");
        assertFalse(bookingPage.isNameFieldValid(),
                "The empty name field should fail the browser's constraint check.");
        assertFalse(bookingPage.getNameFieldValidationMessage().isEmpty(),
                "Chrome should report a validation message for the empty name field.");
    }

    @Test
    public void testPastDateRejected() {
        LocalDate pastDate = LocalDate.now().minusDays(1);

        bookingPage.open();
        String time = bookingPage.getFirstAvailableTimeSlot();

        // The date input is rendered with min="<today>", so Chrome would block
        // the submit before the request is ever sent. Relaxing that attribute
        // lets the form post so the app's own past-date check can be asserted.
        bookingPage.allowPastDates()
                .enterPatientName("Erin Example")
                .enterPatientContact("erin@example.com")
                .enterAppointmentDate(pastDate)
                .selectAppointmentTime(time)
                .submit();

        assertFalse(driver.getCurrentUrl().contains(ConfirmationPage.PATH),
                "A past date should not reach the confirmation page.");
        assertTrue(bookingPage.isErrorDisplayed(),
                "Expected an error message when booking a past date.");
        assertTrue(bookingPage.getErrorMessage().contains("cannot be in the past"),
                "Expected a past-date error, got: " + bookingPage.getErrorMessage());
    }

    /** Returns a future date not yet used by any test in this run. */
    private static LocalDate nextUnusedDate() {
        return RUN_BASE_DATE.plusDays(DATE_OFFSET.getAndIncrement());
    }
}
