package com.patientscheduler.pages;

import java.time.Duration;
import java.time.LocalDate;
import java.util.List;
import java.util.stream.Collectors;

import org.openqa.selenium.By;
import org.openqa.selenium.JavascriptExecutor;
import org.openqa.selenium.NoSuchElementException;
import org.openqa.selenium.TimeoutException;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.Select;
import org.openqa.selenium.support.ui.WebDriverWait;

/**
 * Page object for the /book page of the patient-scheduler app.
 *
 * <p>Locators mirror the ids in templates/book.html: patient_name,
 * patient_contact, appointment_date and appointment_time.
 */
public class BookingPage {

    public static final String PATH = "/book";

    private static final By PATIENT_NAME = By.id("patient_name");
    private static final By PATIENT_CONTACT = By.id("patient_contact");
    private static final By APPOINTMENT_DATE = By.id("appointment_date");
    private static final By APPOINTMENT_TIME = By.id("appointment_time");
    private static final By SUBMIT_BUTTON = By.cssSelector("form button[type='submit']");
    private static final By ERROR_MESSAGE = By.cssSelector("p.error");

    private final WebDriver driver;
    private final String baseUrl;
    private final WebDriverWait wait;

    public BookingPage(WebDriver driver, String baseUrl) {
        this.driver = driver;
        this.baseUrl = baseUrl;
        this.wait = new WebDriverWait(driver, Duration.ofSeconds(10));
    }

    /** Navigates to /book and waits for the form to be ready. */
    public BookingPage open() {
        driver.get(baseUrl + PATH);
        wait.until(ExpectedConditions.visibilityOfElementLocated(PATIENT_NAME));
        return this;
    }

    public BookingPage enterPatientName(String name) {
        WebElement field = driver.findElement(PATIENT_NAME);
        field.clear();
        field.sendKeys(name);
        return this;
    }

    public BookingPage enterPatientContact(String contact) {
        WebElement field = driver.findElement(PATIENT_CONTACT);
        field.clear();
        field.sendKeys(contact);
        return this;
    }

    /**
     * Sets the date on the native {@code <input type="date">}.
     *
     * <p>Typing into a date input depends on the browser's locale format, so
     * the value is assigned directly and the events the browser would normally
     * fire are dispatched afterwards.
     */
    public BookingPage enterAppointmentDate(LocalDate date) {
        WebElement field = driver.findElement(APPOINTMENT_DATE);
        ((JavascriptExecutor) driver).executeScript(
                "arguments[0].value = arguments[1];"
                        + "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));"
                        + "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
                field, date.toString());
        return this;
    }

    public BookingPage selectAppointmentTime(String time) {
        new Select(driver.findElement(APPOINTMENT_TIME)).selectByValue(time);
        return this;
    }

    /**
     * Clicks Book and waits for the resulting page load to finish.
     *
     * <p>A rejected submission re-renders /book, so the URL is unchanged and
     * there is nothing to wait on by address. Waiting for the old document to
     * go stale is what makes the difference observable; without it, assertions
     * can read the pre-submit page and see no error. When the browser's own
     * HTML5 validation blocks the submit no navigation happens at all, so the
     * timeout is expected and swallowed.
     */
    public BookingPage submit() {
        WebElement oldDocument = driver.findElement(By.tagName("html"));
        driver.findElement(SUBMIT_BUTTON).click();
        try {
            new WebDriverWait(driver, Duration.ofSeconds(5))
                    .until(ExpectedConditions.stalenessOf(oldDocument));
        } catch (TimeoutException e) {
            // Submission was blocked client-side; the form is still on screen.
        }
        return this;
    }

    /** The bookable times currently offered by the dropdown, in page order. */
    public List<String> getAvailableTimeSlots() {
        return new Select(driver.findElement(APPOINTMENT_TIME))
                .getOptions().stream()
                .map(option -> option.getDomAttribute("value"))
                .filter(value -> value != null && !value.isEmpty())
                .collect(Collectors.toList());
    }

    /** The first bookable time offered by the dropdown. */
    public String getFirstAvailableTimeSlot() {
        List<String> slots = getAvailableTimeSlots();
        if (slots.isEmpty()) {
            throw new IllegalStateException("The booking form offers no time slots.");
        }
        return slots.get(0);
    }

    /**
     * Drops the {@code min} attribute from the date input.
     *
     * <p>The template renders {@code min="<today>"}, so Chrome refuses to
     * submit a past date and the server-side check never runs. Tests that need
     * to exercise that server-side check call this first. It only relaxes a
     * client-side constraint; the app itself is untouched.
     */
    public BookingPage allowPastDates() {
        ((JavascriptExecutor) driver).executeScript(
                "arguments[0].removeAttribute('min');",
                driver.findElement(APPOINTMENT_DATE));
        return this;
    }

    public boolean isErrorDisplayed() {
        return !driver.findElements(ERROR_MESSAGE).isEmpty();
    }

    /** The validation error rendered by the app, or an empty string if none. */
    public String getErrorMessage() {
        List<WebElement> errors = driver.findElements(ERROR_MESSAGE);
        return errors.isEmpty() ? "" : errors.get(0).getText().trim();
    }

    /** True when the browser is still showing the booking form. */
    public boolean isDisplayed() {
        try {
            return driver.findElement(PATIENT_NAME).isDisplayed();
        } catch (NoSuchElementException e) {
            return false;
        }
    }

    /**
     * The browser's own HTML5 validation message for the name field, e.g.
     * "Please fill out this field." Empty when the field is considered valid.
     */
    public String getNameFieldValidationMessage() {
        return (String) ((JavascriptExecutor) driver).executeScript(
                "return arguments[0].validationMessage;",
                driver.findElement(PATIENT_NAME));
    }

    /** True when the name field passes the browser's own constraint check. */
    public boolean isNameFieldValid() {
        return Boolean.TRUE.equals(((JavascriptExecutor) driver).executeScript(
                "return arguments[0].checkValidity();",
                driver.findElement(PATIENT_NAME)));
    }
}
