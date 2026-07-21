import { Builder, By, until } from 'selenium-webdriver';
import { Options } from 'selenium-webdriver/chrome';
import * as fs from 'fs';

const chromeOptions = new Options();
chromeOptions.addArguments('--headless');

const driver = new Builder().forBrowser('chrome').setChromeOptions(chromeOptions).build();

describe('Frontend Results Page for Tax Summaries', () => {
  afterAll(async () => {
    await driver.quit();
  });

  it('should display tax summaries for both old and new regimes', async () => {
    await driver.get('http://localhost:3000');
    // Assume previous steps for input are done
    await driver.wait(until.elementLocated(By.css('.tax-summaries')), 5000);
    const summaries = await driver.findElement(By.css('.tax-summaries')).getText();
    expect(summaries).toContain('Old Regime Summary');
    expect(summaries).toContain('New Regime Summary');
    await driver.takeScreenshot().then((image) => fs.writeFileSync('screenshots/taxSummaries.png', image, 'base64'));
  });

  it('should present AI-generated insights in a dedicated section', async () => {
    await driver.wait(until.elementLocated(By.css('.ai-insights')), 5000);
    const aiInsights = await driver.findElement(By.css('.ai-insights')).getText();
    expect(aiInsights).toContain('AI Insight');
    await driver.takeScreenshot().then((image) => fs.writeFileSync('screenshots/aiInsights.png', image, 'base64'));
  });

  it('should allow users to download tax summaries as PDFs', async () => {
    await driver.findElement(By.css('button[type="download-summaries"]')).click();
    await driver.takeScreenshot().then((image) => fs.writeFileSync('screenshots/downloadSummaries.png', image, 'base64'));
  });

  it('should be responsive on multiple devices', async () => {
    // Assume viewport resizing is handled
    await driver.manage().window().setRect({ width: 768, height: 1024 });
    await driver.wait(until.elementLocated(By.css('.responsive-check')), 5000);
    const isResponsive = await driver.findElement(By.css('.responsive-check')).isDisplayed();
    expect(isResponsive).toBe(true);
    await driver.takeScreenshot().then((image) => fs.writeFileSync('screenshots/responsiveCheck.png', image, 'base64'));
  });
});