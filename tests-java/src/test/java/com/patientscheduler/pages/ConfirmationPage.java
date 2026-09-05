package com.patientscheduler.pages;

import java.time.Duration;

import org.openqa.selenium.By;
import org.openqa.selenium.NoSuchElementException;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;

/**
 * Page object for /book/confirmed, the page shown after a successful booking.
 */
public class ConfirmationPage {

    public static final String PATH = "/book/confirmed";

    private static final By BANNER = By.cssSelector("p.confirmed");
    private static final By DETAILS = By.cssSelector("dl dd");

    private final WebDriver driver;

    public ConfirmationPage(WebDriver driver) {
        this.driver = driver;
    }

    /** Waits until the browser has landed on the confirmation page. */
    public ConfirmationPage waitUntilDisplayed() {
        new WebDriverWait(driver, Duration.ofSeconds(10))
                .until(ExpectedConditions.urlContains(PATH));
        return this;
    }

    public boolean isDisplayed() {
        try {
            return driver.getCurrentUrl().contains(PATH)
                    && driver.findElement(BANNER).isDisplayed();
        } catch (NoSuchElementException e) {
            return false;
        }
    }

    public String getBannerText() {
        return driver.findElement(BANNER).getText().trim();
    }

    /** The booked date shown in the summary list. */
    public String getAppointmentDate() {
        return driver.findElements(DETAILS).get(0).getText().trim();
    }

    /** The booked time shown in the summary list. */
    public String getAppointmentTime() {
        return driver.findElements(DETAILS).get(1).getText().trim();
    }
}
