import time
import random
import os
import requests
from urllib.robotparser import RobotFileParser
from config import BASE_DIR, REQUEST_DELAY_MIN, REQUEST_DELAY_MAX, MAX_RETRIES, TIMEOUT
from utils.user_agents import get_random_user_agent
from utils.logger import logger

class AntiCrawlStrategy:
    def __init__(self):
        self.session = requests.Session()
        self.proxy_pool = self.load_proxy_pool()
        self.proxy_failures = {}
        self._session_warmed = False
        self.update_headers()
    
    def load_proxy_pool(self):
        proxy_file = os.path.join(BASE_DIR, 'proxies.txt')
        try:
            with open(proxy_file, 'r', encoding='utf-8') as f:
                proxies = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
            logger.info(f"已加载{len(proxies)}个代理IP")
            return proxies
        except FileNotFoundError:
            logger.info("未发现proxies.txt，使用直连模式")
            return []
    
    def update_headers(self, referer='https://movie.douban.com/'):
        self.session.headers.update({
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': referer,
        })

    def warm_up_session(self, base_url='https://movie.douban.com/'):
        """先访问站点首页，拿到常见 Cookie（如 bid），可降低部分 403 概率。"""
        if self._session_warmed:
            return True
        proxies = self.get_random_proxy()
        try:
            self.random_delay()
            r = self.session.get(base_url, timeout=TIMEOUT, proxies=proxies)
            if r.status_code == 200:
                self._session_warmed = True
                logger.info("会话预热成功（已访问电影首页）")
                return True
            logger.warning(f"会话预热未成功，状态码: {r.status_code}")
        except Exception as e:
            logger.warning(f"会话预热请求异常: {e}")
        return False
    
    def random_delay(self):
        delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
        time.sleep(delay)
    
    def get_random_proxy(self):
        available_proxies = [proxy for proxy in self.proxy_pool if self.proxy_failures.get(proxy, 0) < 3]
        if not available_proxies:
            return None
        proxy = random.choice(available_proxies)
        return {
            'http': proxy,
            'https': proxy
        }
    
    def record_proxy_failure(self, proxies):
        if not proxies:
            return
        proxy = proxies.get('http')
        if proxy:
            self.proxy_failures[proxy] = self.proxy_failures.get(proxy, 0) + 1
    
    def check_robots_txt(self, base_url='https://movie.douban.com/', path='/top250'):
        robots_url = f"{base_url.rstrip('/')}/robots.txt"
        try:
            parser = RobotFileParser()
            parser.set_url(robots_url)
            parser.read()
            can_fetch = parser.can_fetch(self.session.headers.get('User-Agent', '*'), path)
            logger.info(f"Robots.txt检查: {robots_url} path={path} allowed={can_fetch}")
            return can_fetch
        except Exception as e:
            logger.warning(f"Robots.txt检查失败: {e}")
            return None
    
    def get_with_retry(self, url, referer='https://movie.douban.com/'):
        for attempt in range(MAX_RETRIES):
            proxies = self.get_random_proxy()
            try:
                self.update_headers(referer=referer)
                self.random_delay()
                response = self.session.get(url, timeout=TIMEOUT, proxies=proxies)
                
                if response.status_code == 200:
                    return response
                elif response.status_code in [403, 429]:
                    logger.warning(f"遇到反爬限制，状态码: {response.status_code}，等待后重试")
                    self.record_proxy_failure(proxies)
                    time.sleep(10 * (attempt + 1))
                    self.update_headers(referer=referer)
                else:
                    logger.warning(f"请求失败，状态码: {response.status_code}")
                    self.record_proxy_failure(proxies)
                    
            except Exception as e:
                logger.error(f"请求异常: {e}，尝试次数: {attempt + 1}")
                self.record_proxy_failure(proxies)
                time.sleep(5)
        
        logger.error(f"请求失败，已达到最大重试次数: {url}")
        return None
