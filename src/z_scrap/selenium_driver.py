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
    for arg in ['--headless=new', '--disable-javascript', '--remote-debugging-port=9222', '--disable-extensions']:
        chromium_options.add_argument(arg)
    return webdriver.Chrome(options=chromium_options)


def select_user_agent():
    with urllib.request.urlopen(AGENTS_JSON) as url:
        data = json.loads(url.read().decode())
        user_agent = random.choice(data)
    print(f"Using user-agent: {user_agent}")
    return user_agent
