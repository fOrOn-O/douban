import sys
import os
# 【新增】添加项目根目录到搜索路径
current_file_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file_path))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import scrapy
import re
from urllib.parse import parse_qs, urlparse
from datetime import datetime
from bs4 import BeautifulSoup
from douban_scrapy.items import MovieItem, CommentItem
from utils.logger import logger

class DoubanMovieSpider(scrapy.Spider):
    name = 'douban_movie'
    allowed_domains = ['movie.douban.com', 'sec.douban.com', 'www.douban.com']
    start_urls = ['https://movie.douban.com/top250']
    
    def start_requests(self):
        base_url = 'https://movie.douban.com/top250'
        for page in range(0, 250, 25):
            url = f"{base_url}?start={page}&filter="
            yield scrapy.Request(url=url, callback=self.parse, dont_filter=True)
    
    def parse(self, response):
        # 解析列表页
        soup = BeautifulSoup(response.text, 'lxml')
        items = soup.find_all('div', class_='item')
        
        for item in items:
            try:
                movie = MovieItem()
                
                # 排名
                movie['rank'] = int(item.find('div', class_='pic').em.text)
                
                # 标题
                title_div = item.find('div', class_='hd')
                titles = title_div.a.find_all('span')
                movie['title_cn'] = titles[0].text.strip()
                movie['title_en'] = titles[1].text.strip() if len(titles) > 1 else ''
                
                # 评分和评价人数（适配2026年4月最新豆瓣结构）
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
                
                # 导演和主演（第1行）
                info_p = bd_div.p if bd_div else None
                info_text = info_p.text.strip() if info_p else ''
                info_lines = [line.strip() for line in info_text.split('\n') if line.strip()] if info_text else []

                director_match = re.search(r'导演: (.*?)(?:主演|$)', info_lines[0]) if info_lines else None
                movie['director'] = director_match.group(1).strip() if director_match else ''

                actors_match = re.search(r'主演: (.*)', info_lines[0]) if info_lines else None
                movie['actors'] = actors_match.group(1).strip() if actors_match else ''

                # 年份、国家、类型（第2行：如 "1994 / 美国 / 犯罪 剧情"）
                if len(info_lines) >= 2:
                    parts = [p.strip() for p in info_lines[1].split('/')]
                    year_match = re.search(r'\d{4}', parts[0]) if parts else None
                    movie['release_year'] = int(year_match.group()) if year_match else None
                    movie['genres'] = '/'.join(parts[2:]) if len(parts) >= 3 else ''
                else:
                    movie['release_year'] = None
                    movie['genres'] = ''
                
                # ✅ 【修复】列表页一句话简介（class从inq改成了quote）
                quote_p = item.find('p', class_='quote')
                if quote_p:
                    summary_span = quote_p.find('span')
                    movie['summary'] = summary_span.text.strip() if summary_span else ''
                else:
                    movie['summary'] = ''
                
                # 详情链接
                movie['detail_url'] = title_div.a['href']
                movie['duration'] = ''
                movie['imdb_id'] = None
                movie['poster_path'] = None
                
                yield scrapy.Request(
                    url=movie['detail_url'],
                    callback=self.parse_detail,
                    errback=self.parse_detail_error,
                    dont_filter=True,
                    headers={'Referer': response.url},
                    meta={
                        'movie': movie,
                        'return_block_response': True,
                        'is_detail_request': True,
                    },
                )
                
            except Exception as e:
                logger.error(f"解析列表页单个电影失败: {e}")
                continue
        
        return
    
    def parse_detail(self, response):
        movie = response.meta['movie']
        soup = BeautifulSoup(response.text, 'lxml')

        # 检测是否被重定向到安全挑战页面
        if self._is_block_page(response.url):
            logger.warning(f"详情页被重定向到访问限制页面，保存列表页基础数据: {movie.get('title_cn', '未知')}, 当前URL: {response.url}")
            yield movie
            return

        if not self._is_valid_detail_page(response):
            logger.warning(f"详情页响应无效，保存列表页基础数据: {movie.get('title_cn', '未知')}, 当前URL: {response.url}")
            yield movie
            return

        try:
            # 解析详情信息（只保留数据库有的字段）
            year_span = soup.find('span', class_='year')
            if year_span:
                year_match = re.search(r'\d{4}', year_span.text)
                movie['release_year'] = int(year_match.group()) if year_match else None
            else:
                movie['release_year'] = None
            
            duration_span = soup.find('span', property='v:runtime')
            movie['duration'] = duration_span.text.strip() if duration_span else ''
            
            genre_spans = soup.find_all('span', property='v:genre')
            movie['genres'] = '/'.join([span.text.strip() for span in genre_spans]) if genre_spans else ''
            
            # 提取 IMDb 编号（如 tt0111161）
            imdb_match = re.search(r'tt\d{7,}', response.text)
            movie['imdb_id'] = imdb_match.group() if imdb_match else None
            
            # 海报URL
            poster_img = soup.find('img', rel='v:image')
            movie['poster_path'] = poster_img['src'] if poster_img else None
            
            yield movie
            
            comments_url = f"{movie['detail_url']}comments?sort=new_score&status=P"
            yield scrapy.Request(
                url=comments_url,
                callback=self.parse_comments,
                errback=self.parse_comments_error,
                dont_filter=True,
                headers={'Referer': movie['detail_url']},
                meta={
                    'movie_url': movie['detail_url'],
                    'return_block_response': True,
                    'is_comment_request': True,
                },
            )
            
        except Exception as e:
            logger.error(f"解析详情页失败: {movie.get('title_cn', '未知')}, 错误: {e}")
            yield movie

    def parse_detail_error(self, failure):
        movie = failure.request.meta.get('movie')
        if movie:
            logger.warning(f"详情页请求失败，保存列表页基础数据: {movie.get('title_cn', '未知')}, 原因: {failure.value}")
            yield movie
    
    def parse_comments(self, response):
        movie_url = response.meta['movie_url']

        # 检测是否被重定向到安全挑战页面
        if self._is_block_page(response.url):
            logger.warning(f"评论页被重定向到访问限制页面，跳过: {movie_url}")
            return

        soup = BeautifulSoup(response.text, 'lxml')
        comment_items = soup.find_all('div', class_='comment-item')[:15]  # 取前15条
        
        for item in comment_items:
            try:
                comment = CommentItem()
                comment['movie_url'] = movie_url
                comment['reviewer'] = item.find('span', class_='comment-info').a.text.strip()
                
                rating_span = item.find('span', class_=re.compile(r'rating'))
                if rating_span:
                    rating_class = rating_span['class'][0]
                    rating_match = re.search(r'(\d+)', rating_class)
                    comment['rating'] = int(rating_match.group()) / 10 if rating_match else None
                else:
                    comment['rating'] = None
                
                comment['content'] = item.find('span', class_='short').text.strip()
                
                time_span = item.find('span', class_='comment-time')
                if time_span:
                    time_str = time_span['title'] if 'title' in time_span.attrs else time_span.text.strip()
                    try:
                        comment['comment_time'] = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                    except (ValueError, TypeError):
                        comment['comment_time'] = None
                else:
                    comment['comment_time'] = None
                
                comment['sentiment'] = None  # 后续情感分析填充
                
                yield comment
                
            except Exception as e:
                logger.error(f"解析评论失败: {e}")
                continue

    def parse_comments_error(self, failure):
        movie_url = failure.request.meta.get('movie_url')
        logger.warning(f"评论页请求失败，跳过: {movie_url}, 原因: {failure.value}")

    def _is_block_page(self, url):
        return 'sec.douban.com' in url or 'douban.com/misc/sorry' in url

    def _is_expected_detail_page(self, target_url, current_url):
        target_match = re.search(r'/subject/(\d+)/', target_url or '')
        current_match = re.search(r'/subject/(\d+)/', current_url or '')
        return bool(target_match and current_match and target_match.group(1) == current_match.group(1))

    def _is_valid_detail_page(self, response):
        if not self._is_expected_detail_page(response.meta['movie']['detail_url'], response.url):
            return False
        soup = BeautifulSoup(response.text, 'lxml')
        return bool(
            soup.find(id='info')
            or soup.find('span', property='v:itemreviewed')
            or soup.find('span', property='v:runtime')
            or soup.find('span', property='v:genre')
        )

    def _original_url_from_block(self, url):
        parsed = urlparse(url or '')
        query = parse_qs(parsed.query)
        return query.get('r', [None])[0] or query.get('original-url', [None])[0] or url
