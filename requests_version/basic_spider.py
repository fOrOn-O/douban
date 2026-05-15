from bs4 import BeautifulSoup
import re
from tqdm import tqdm
from utils.logger import logger
from .anti_crawl import AntiCrawlStrategy

class BasicMovieSpider(AntiCrawlStrategy):
    def __init__(self):
        super().__init__()
        self.movies = []
    
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
                
                # 简介
                quote_p = item.find('p', class_='quote')
                summary_span = quote_p.find('span') if quote_p else item.find('span', class_='inq')
                movie['summary'] = summary_span.text.strip() if summary_span else ''
                
                # 详情链接
                movie['detail_url'] = title_div.a['href']
                
                self.movies.append(movie)
                
            except Exception as e:
                logger.error(f"解析单个电影条目失败: {e}")
                continue
    
    def crawl_all_pages(self):
        logger.info("开始爬取豆瓣电影Top250列表页（requests + BeautifulSoup模式）")
        self.check_robots_txt(path='/top250')
        self.warm_up_session()

        base_url = 'https://movie.douban.com/top250'
        referer = 'https://movie.douban.com/'

        for page in tqdm(range(0, 250, 25), desc="爬取列表页"):
            url = f"{base_url}?start={page}&filter="

            try:
                response = self.get_with_retry(url, referer=referer)
                if not response:
                    logger.error(f"第{page//25 + 1}页请求失败，跳过")
                    continue
                self.parse_list_page(response.text)
                referer = url
                
            except Exception as e:
                logger.error(f"第{page//25 + 1}页爬取失败: {e}")
                continue
        
        logger.info(f"列表页爬取完成，共获取{len(self.movies)}部电影信息")
        return self.movies