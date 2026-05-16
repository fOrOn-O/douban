import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from config import BASE_DIR, HEADLESS_MODE
from utils.user_agents import get_random_user_agent


def create_chrome_driver():
    chrome_options = Options()
    if HEADLESS_MODE:
        chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--ignore-ssl-errors')
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument(f'user-agent={get_random_user_agent()}')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    local_driver = os.path.join(BASE_DIR, 'chromedriver.exe')
    if os.path.exists(local_driver):
        service = Service(local_driver)
    else:
        service = Service(ChromeDriverManager().install())

    # eager: DOMContentLoaded 后就返回，不等图片等资源加载完
    chrome_options.page_load_strategy = 'eager'

    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(45)
    driver.set_script_timeout(30)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver
