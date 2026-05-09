import sys
import os
# 【新增】添加项目根目录到搜索路径
current_file_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import scrapy
import re
from datetime import datetime
from bs4 import BeautifulSoup
from douban_scrapy.items import MovieItem, CommentItem
from utils.logger import logger

class DoubanMovieSpider(scrapy.Spider):
    name = 'douban_movie'
    allowed_domains = ['movie.douban.com']
    start_urls = ['https://movie.douban.com/top250']
    
    # 【新增】手动添加 start_requests，带完整的反爬请求头
    def start_requests(self):
        base_url = 'https://movie.douban.com/top250'
        for page in range(0, 250, 25):
            url = f"{base_url}?start={page}&filter="
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Cache-Control': 'max-age=0',
                    'Referer': 'https://www.douban.com/',
                },
                dont_filter=True
            )
    
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
                
                # 导演和主演
                info_text = item.find('div', class_='bd').p.text.strip()
                info_lines = info_text.split('\n')
                
                director_match = re.search(r'导演: (.*?)(?:主演|$)', info_lines[0])
                movie['director'] = director_match.group(1).strip() if director_match else ''
                
                actors_match = re.search(r'主演: (.*)', info_lines[0])
                movie['actors'] = actors_match.group(1).strip() if actors_match else ''
                
                # ✅ 【修复】列表页一句话简介（class从inq改成了quote）
                quote_p = item.find('p', class_='quote')
                if quote_p:
                    summary_span = quote_p.find('span')
                    movie['summary'] = summary_span.text.strip() if summary_span else ''
                else:
                    movie['summary'] = ''
                
                # 详情链接
                movie['detail_url'] = title_div.a['href']
                
                # 跟进详情页
                yield scrapy.Request(
                    url=movie['detail_url'],
                    callback=self.parse_detail,
                    meta={'movie': movie},
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
                        'Referer': 'https://movie.douban.com/top250',
                    }
                )
                
            except Exception as e:
                logger.error(f"解析列表页单个电影失败: {e}")
                continue
        
        # 下一页
        next_page = soup.find('link', rel='next')
        if next_page:
            next_url = next_page['href']
            full_next_url = response.urljoin(next_url)
            yield scrapy.Request(
                url=next_url, 
                callback=self.parse,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
                    'Referer': response.url,
                }
            )
    
    def parse_detail(self, response):
        movie = response.meta['movie']
        soup = BeautifulSoup(response.text, 'lxml')
        
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
            
            imdb_link = soup.find('a', href=re.compile(r'imdb\.com'))
            if imdb_link:
                imdb_text = imdb_link.text.strip()
                imdb_match = re.search(r'(\d+\.\d+)', imdb_text)
                movie['imdb_rating'] = float(imdb_match.group()) if imdb_match else None
            else:
                movie['imdb_rating'] = None
            
            # 海报URL
            poster_img = soup.find('img', rel='v:image')
            movie['poster_path'] = poster_img['src'] if poster_img else None
            
            yield movie
            
            # 跟进评论页
            comments_url = f"{movie['detail_url']}comments?sort=new_score&status=P"
            yield scrapy.Request(
                url=comments_url,
                callback=self.parse_comments,
                meta={'movie_url': movie['detail_url']},
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
                    'Referer': movie['detail_url'],
                }
            )
            
        except Exception as e:
            logger.error(f"解析详情页失败: {movie.get('title_cn', '未知')}, 错误: {e}")
            yield movie
    
    def parse_comments(self, response):
        movie_url = response.meta['movie_url']
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
                    time_str = time_span['title']
                    comment['comment_time'] = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                else:
                    comment['comment_time'] = None
                
                comment['sentiment'] = None  # 后续情感分析填充
                
                yield comment
                
            except Exception as e:
                logger.error(f"解析评论失败: {e}")
                continue