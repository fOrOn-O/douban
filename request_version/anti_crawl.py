import time
import random
import requests
from config import REQUEST_DELAY_MIN, REQUEST_DELAY_MAX, MAX_RETRIES, TIMEOUT
from utils.user_agents import get_random_user_agent
from utils.logger import logger

class AntiCrawlStrategy:
    def __init__(self):
        self.session = requests.Session()
        self.update_headers()
    
    def update_headers(self):
        self.session.headers.update({
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def random_delay(self):
        delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
        time.sleep(delay)
    
    def get_with_retry(self, url):
        for attempt in range(MAX_RETRIES):
            try:
                self.random_delay()
                response = self.session.get(url, timeout=TIMEOUT)
                
                if response.status_code == 200:
                    return response
                elif response.status_code in [403, 429]:
                    logger.warning(f"遇到反爬限制，状态码: {response.status_code}，等待后重试")
                    time.sleep(10 * (attempt + 1))
                    self.update_headers()
                else:
                    logger.warning(f"请求失败，状态码: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"请求异常: {e}，尝试次数: {attempt + 1}")
                time.sleep(5)
        
        logger.error(f"请求失败，已达到最大重试次数: {url}")
        return None
