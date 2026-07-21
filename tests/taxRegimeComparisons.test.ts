import { Builder, By, until } from 'selenium-webdriver';
import { Options } from 'selenium-webdriver/chrome';
import * as fs from 'fs';

const chromeOptions = new Options();
chromeOptions.addArguments('--headless');

const driver = new Builder().forBrowser('chrome').setChromeOptions(chromeOptions).build();

describe('Tax Regime Comparisons', () => {
  afterAll(async () => {
    await driver.quit();
  });

  it('should perform tax calculations for old and new regimes', async () => {
    await driver.get('http://localhost:3000');
    // Assume previous steps for input are done
    await driver.findElement(By.css('button[type="calculate"]')).click();
    await driver.wait(until.elementLocated(By.css('.comparison-table')), 5000);
    const comparisonTable = await driver.findElement(By.css('.comparison-table')).getText();
    expect(comparisonTable).toContain('Old Regime');
    expect(comparisonTable).toContain('New Regime');
    await driver.takeScreenshot().then((image) => fs.writeFileSync('screenshots/comparisonTable.png', image, 'base64'));
  });

  it('should allow users to download results as PDF', async () => {
    await driver.findElement(By.css('button[type="download"]')).click();
    // Add assertions to verify download
    await driver.takeScreenshot().then((image) => fs.writeFileSync('screenshots/downloadResults.png', image, 'base64'));
  });

  it('should handle edge cases gracefully', async () => {
    // Assume input is invalid
    await driver.findElement(By.css('button[type="calculate"]')).click();
    await driver.wait(until.elementLocated(By.css('.error-message')), 5000);
    const errorMessage = await driver.findElement(By.css('.error-message')).getText();
    expect(errorMessage).toContain('Invalid input');
    await driver.takeScreenshot().then((image) => fs.writeFileSync('screenshots/edgeCaseError.png', image, 'base64'));
  });
});