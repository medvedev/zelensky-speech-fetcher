from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json
import urllib.request
import random

print("Starting")

with urllib.request.urlopen('https://raw.githubusercontent.com/Said-Ait-Driss/user-agents/main/userAgents.json') as url:
    data = json.loads(url.read().decode())
    user_agent = random.choice(data)

print(f"Using user-agent: {user_agent}")
chromium_options = Options()
chromium_options.binary_location = "/usr/bin/chromium-browser"
chromium_options.add_argument(user_agent)
for arg in ['--headless', '--remote-debugging-port=9222', '--disable-extensions']:
    chromium_options.add_argument(arg)
driver = None

try:
    driver = webdriver.Chrome(options=chromium_options)
    driver.get("https://www.president.gov.ua/news/speeches?date-from=27-11-2022&date-to=27-11-2023&page=2")

    title = driver.title
    print(title)
except Exception as e:
    print(f"An error occurred: {str(e)}")


finally:
    if 'driver' in locals() and driver is not None:
        driver.quit()
