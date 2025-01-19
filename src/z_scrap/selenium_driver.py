from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json
import urllib.request
import random

AGENTS_JSON = 'https://raw.githubusercontent.com/Said-Ait-Driss/user-agents/main/userAgents.json'


def create_driver():
    chromium_options = Options()
    chromium_options.binary_location = "/usr/bin/chromium-browser"
    chromium_options.add_argument(f"user-agent={select_user_agent()}")
    arguments = ['--headless=new',
                 '--disable-javascript',
                 '--remote-debugging-port=9222',
                 '--disable-extensions',
                 '--no-sandbox',
                 '--disable-dev-shm-usage',
                 '--disable-gpu']
    for arg in arguments:
        chromium_options.add_argument(arg)
    chrome = webdriver.Chrome(options=chromium_options)
    print("Chrome driver created")
    return chrome


def select_user_agent():
    with urllib.request.urlopen(AGENTS_JSON) as url:
        data = json.loads(url.read().decode())
        user_agent = random.choice(data)
    print(f"Using user-agent: {user_agent}")
    return user_agent
