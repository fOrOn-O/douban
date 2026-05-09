from bs4 import BeautifulSoup
import re
import random
import time
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from utils.logger import logger
from config import REQUEST_DELAY_MIN, REQUEST_DELAY_MAX

class BasicMovieSpider:
    def __init__(self, driver=None):
        self.movies = []
        self.driver = driver if driver else self._init_driver()
    
    def _init_driver(self):
        chrome_options = Options()
        # 无头模式（后台运行，不显示浏览器窗口）
        # 如果想看浏览器操作，可以注释掉下面这行
        chrome_options.add_argument('--headless=new')
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # 关键：混淆浏览器指纹
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 真实User-Agent
        chrome_options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
        )
        
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        
        # 删除webdriver标志
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    
    def random_delay(self):
        delay = random.uniform(REQUEST_DELAY_MIN + 2, REQUEST_DELAY_MAX + 3)
        time.sleep(delay)
    
    def parse_list_page(self, html):
        soup = BeautifulSoup(html, 'lxml')
        items = soup.find_all('div', class_='item')
        
        for item in items:
            try:
                movie = {}
                
                # 排名
                movie['rank'] = int(item.find('div', class_='pic').em.text)
                
                # 标题
                title_div = item.find('div', class_='hd')
                titles = title_div.a.find_all('span')
                movie['title_cn'] = titles[0].text.strip()
                movie['title_en'] = titles[1].text.strip() if len(titles) > 1 else ''
                
                # 评分和评价人数
                bd_div = item.find('div', class_='bd')
                rating_div = bd_div.find('div') if bd_div else None
                
                if rating_div:
                    rating_num_elem = rating_div.find('span', class_='rating_num')
                    movie['rating'] = float(rating_num_elem.text) if rating_num_elem else 0.0
                    
                    rating_spans = rating_div.find_all('span')
                    if len(rating_spans) >= 4:
                        rating_count_text = rating_spans[-1].text
                        rating_count_match = re.search(r'\d+', rating_count_text)
                        movie['rating_count'] = int(rating_count_match.group()) if rating_count_match else 0
                    else:
                        movie['rating_count'] = 0
                else:
                    movie['rating'] = 0.0
                    movie['rating_count'] = 0
                
                # 导演和主演
                info_text = item.find('div', class_='bd').p.text.strip()
                info_lines = info_text.split('\n')
                
                director_match = re.search(r'导演: (.*?)(?:主演|$)', info_lines[0])
                movie['director'] = director_match.group(1).strip() if director_match else ''
                
                actors_match = re.search(r'主演: (.*)', info_lines[0])
                movie['actors'] = actors_match.group(1).strip() if actors_match else ''
                
                # 简介
                summary_span = item.find('p', class_='quote')
                movie['summary'] = summary_span.text.strip() if summary_span else ''
                
                # 详情链接
                movie['detail_url'] = title_div.a['href']
                
                self.movies.append(movie)
                
            except Exception as e:
                logger.error(f"解析单个电影条目失败: {e}")
                continue
    
    def crawl_all_pages(self):
        logger.info("开始爬取豆瓣电影Top250列表页（全Selenium模式）")
        
        base_url = 'https://movie.douban.com/top250'
        
        for page in tqdm(range(0, 250, 25), desc="爬取列表页"):
            url = f"{base_url}?start={page}&filter="
            
            try:
                self.driver.get(url)
                self.random_delay()
                
                # 滚动页面，模拟真人浏览
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                self.random_delay()
                
                self.parse_list_page(self.driver.page_source)
                
            except Exception as e:
                logger.error(f"第{page//25 + 1}页爬取失败: {e}")
                continue
        
        logger.info(f"列表页爬取完成，共获取{len(self.movies)}部电影信息")
        return self.movies