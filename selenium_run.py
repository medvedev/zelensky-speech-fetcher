from selenium import webdriver
from selenium.webdriver.chrome.options import Options

print("Starting")
chromium_options = Options()
chromium_options.binary_location = "/usr/bin/chromium-browser"
for arg in ['--headless', '--remote-debugging-port=9222', '--disable-extensions']:
    chromium_options.add_argument(arg)
driver = None

try:
    driver = webdriver.Chrome(options=chromium_options)
    driver.get("https://www.president.gov.ua/news/speeches")

    title = driver.title
    print(title)
except Exception as e:
    print(f"An error occurred: {str(e)}")


finally:
    if 'driver' in locals() and driver is not None:
        driver.quit()
