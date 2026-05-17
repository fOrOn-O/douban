from bs4 import BeautifulSoup
import re
from datetime import datetime
import random
import time
from tqdm import tqdm
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from utils.logger import logger
from config import REQUEST_DELAY_MIN, REQUEST_DELAY_MAX
from .anti_crawl import AntiCrawlStrategy

class DetailSpider(AntiCrawlStrategy):
    def __init__(self, driver):
        super().__init__()
        self.driver = driver
    
    def random_delay(self):
        delay = random.uniform(REQUEST_DELAY_MIN + 1, REQUEST_DELAY_MAX + 2)
        time.sleep(delay)

    def _is_block_page(self, html='', url=''):
        url = url or ''
        if 'sec.douban.com' in url or 'douban.com/misc/sorry' in url:
            return True
        html = html or ''
        html_lower = html.lower()
        block_markers = ['检测到有异常请求', '访问过于频繁', '请输入验证码', '豆瓣安全中心', '访问限制']
        return any(marker in html for marker in block_markers) or 'captcha' in html_lower or 'forbidden' in html_lower

    def _is_valid_detail_page(self, html):
        soup = BeautifulSoup(html, 'lxml')
        return bool(
            soup.find(id='info')
            or soup.find('span', property='v:itemreviewed')
            or soup.find('span', property='v:runtime')
            or soup.find('span', property='v:genre')
        )
    
    def parse_detail_page(self, html):
        soup = BeautifulSoup(html, 'lxml')
        movie_info = {}
        
        # 上映年份
        year_span = soup.find('span', class_='year')
        if year_span:
            year_match = re.search(r'\d{4}', year_span.text)
            if year_match:
                movie_info['release_year'] = int(year_match.group())
        
        # 片长
        duration_span = soup.find('span', property='v:runtime')
        if duration_span:
            movie_info['duration'] = duration_span.text.strip()
        
        # 类型
        genre_spans = soup.find_all('span', property='v:genre')
        if genre_spans:
            movie_info['genres'] = '/'.join([span.text.strip() for span in genre_spans])
        
        # IMDb编号（如 tt0111161）
        imdb_match = re.search(r'tt\d{7,}', html)
        if imdb_match:
            movie_info['imdb_id'] = imdb_match.group()
        
        return movie_info
    
    def get_comments(self, detail_url, max_comments=15):
        comments_url = f"{detail_url}comments?sort=new_score&status=P"
        comments = []
        
        try:
            self.driver.get(comments_url)
            self.random_delay()
            current_url = self.driver.current_url
            page_source = self.driver.page_source

            if self._is_block_page(page_source, current_url):
                logger.warning(f"评论页触发访问限制，跳过: {detail_url}")
                return comments
            
            # 加载更多评论直到达到要求数量
            load_attempts = 0
            while len(comments) < max_comments and load_attempts < 3:
                # 解析当前页面的评论
                soup = BeautifulSoup(self.driver.page_source, 'lxml')
                comment_items = soup.find_all('div', class_='comment-item')
                
                for item in comment_items[len(comments):]:
                    if len(comments) >= max_comments:
                        break
                    
                    comment = {}
                    reviewer_span = item.find('span', class_='comment-info')
                    reviewer_link = reviewer_span.a if reviewer_span else None
                    comment['reviewer'] = reviewer_link.text.strip() if reviewer_link else ''
                    
                    # 评分
                    rating_span = item.find('span', class_=re.compile(r'rating'))
                    if rating_span:
                        rating_class = rating_span['class'][0]
                        rating_match = re.search(r'(\d+)', rating_class)
                        comment['rating'] = int(rating_match.group()) / 10 if rating_match else None
                    else:
                        comment['rating'] = None
                    
                    # 评论内容
                    content_span = item.find('span', class_='short')
                    comment['content'] = content_span.text.strip() if content_span else ''
                    
                    # 评论时间
                    time_span = item.find('span', class_='comment-time')
                    if time_span:
                        time_str = time_span['title'] if 'title' in time_span.attrs else time_span.text.strip()
                        try:
                            comment['comment_time'] = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                        except (ValueError, TypeError):
                            comment['comment_time'] = None
                    else:
                        comment['comment_time'] = None
                    
                    comments.append(comment)
                
                # 点击"加载更多"按钮
                if len(comments) < max_comments:
                    try:
                        load_more_btn = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.ID, 'load-more'))
                        )
                        load_more_btn.click()
                        self.random_delay()
                        load_attempts += 1
                    except Exception:
                        logger.debug("没有更多评论可加载")
                        break
        
        except Exception as e:
            logger.error(f"获取评论失败: {e}")
        
        return comments[:max_comments]
    
    def crawl_movie_details(self, movies):
        logger.info("开始爬取电影详情页和短评（Selenium动态页面模式）")
        
        detailed_movies = []
        all_comments = []
        
        for movie in tqdm(movies, desc="爬取详情页"):
            try:
                page_loaded = False
                try:
                    self.driver.get(movie['detail_url'])
                    page_loaded = True
                except TimeoutException:
                    logger.warning(f"详情页加载超时，尝试解析已加载内容: {movie.get('title_cn', '未知')}")
                    # 页面可能已部分加载，继续尝试解析

                if page_loaded:
                    self.random_delay()

                # 无论是否超时，尝试解析已有的页面内容
                page_source = self.driver.page_source
                current_url = self.driver.current_url
                if page_source and len(page_source) > 500 and not self._is_block_page(page_source, current_url) and self._is_valid_detail_page(page_source):
                    detail_info = self.parse_detail_page(page_source)
                    if detail_info:
                        movie.update(detail_info)
                    else:
                        logger.warning(f"详情页未解析到有效字段，保留列表页基础数据: {movie.get('title_cn', '未知')}")

                    if page_loaded:
                        # 滚动页面以触发懒加载
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        self.random_delay()

                    # 获取短评
                    comments = self.get_comments(movie['detail_url'])
                    for comment in comments:
                        comment['movie_url'] = movie['detail_url']
                        all_comments.append(comment)
                else:
                    logger.warning(f"详情页无效或触发访问限制，保留列表页基础数据: {movie.get('title_cn', '未知')}, 当前URL: {current_url if 'current_url' in locals() else '未知'}")

                detailed_movies.append(movie)

            except Exception as e:
                logger.error(f"电影详情页爬取失败: {movie.get('title_cn', '未知')}, 错误: {e}")
                # 即使失败也添加到列表，保持进度
                detailed_movies.append(movie)
                continue
        
        logger.info(f"详情页爬取完成，共获取{len(detailed_movies)}部电影详情和{len(all_comments)}条短评")
        return detailed_movies, all_comments