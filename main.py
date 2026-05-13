import time
import os
import sys
import subprocess
import argparse
import pandas as pd
from utils.logger import logger
from database.db_connector import DBConnector
from analysis.data_cleaner import DataCleaner
from analysis.analyzer import DataAnalyzer
from analysis.sentiment_analysis import SentimentAnalyzer
from analysis.visualizer import DataVisualizer
from config import BASE_DIR, CSV_DIR
from utils.performance_recorder import record_performance

def save_spider_data_to_csv(movies, comments, source='requests'):
    movie_columns = [
        'rank', 'title_cn', 'title_en', 'rating', 'rating_count', 'director',
        'actors', 'summary', 'detail_url', 'release_year', 'duration', 'genres',
        'imdb_rating', 'poster_path'
    ]
    comment_columns = ['movie_url', 'reviewer', 'rating', 'content', 'comment_time', 'sentiment']
    movies_path = os.path.join(CSV_DIR, f'movies_{source}.csv')
    comments_path = os.path.join(CSV_DIR, f'comments_{source}.csv')
    
    movies_df = pd.DataFrame(movies).reindex(columns=movie_columns)
    comments_df = pd.DataFrame(comments).reindex(columns=comment_columns)
    movies_df.to_csv(movies_path, index=False, encoding='utf-8-sig')
    comments_df.to_csv(comments_path, index=False, encoding='utf-8-sig')
    logger.info(f"爬虫数据已保存到CSV: {movies_path} 和 {comments_path}")

def run_requests_spider(download_posters=False):
    logger.info("="*50)
    logger.info("开始运行requests列表页 + Selenium详情页爬虫")
    logger.info("="*50)
    
    start_time = time.time()
    driver = None
    detailed_movies = []
    comments = []
    
    try:
        # 1. 使用requests + BeautifulSoup爬取列表页
        from requests_version.basic_spider import BasicMovieSpider
        basic_spider = BasicMovieSpider()
        
        # 2. 爬取列表页
        movies = basic_spider.crawl_all_pages()
        
        if len(movies) == 0:
            logger.error("列表页未获取到任何电影，终止运行")
            record_performance('requests', time.time() - start_time, success=False, movie_count=0, comment_count=0)
            return
        
        # 3. 初始化浏览器并爬取详情页和短评
        from requests_version.selenium_driver import create_chrome_driver
        from requests_version.detail_spider import DetailSpider
        driver = create_chrome_driver()
        detail_spider = DetailSpider(driver)
        detailed_movies, comments = detail_spider.crawl_movie_details(movies)
        
        # 4. 下载或跳过海报
        from requests_version.image_downloader import PosterDownloader
        poster_downloader = PosterDownloader(driver)
        detailed_movies = poster_downloader.download_all_posters(detailed_movies, download=download_posters)
        
        save_spider_data_to_csv(detailed_movies, comments)
        
        # 5. 保存到数据库
        try:
            db = DBConnector()
            logger.info("开始保存数据到数据库")
            
            for movie in detailed_movies:
                try:
                    db.insert_movie(movie)
                    movie_id = db.get_movie_id_by_url(movie['detail_url'])
                    
                    # 保存该电影的评论
                    movie_comments = [c for c in comments if c['movie_url'] == movie['detail_url']]
                    for comment in movie_comments:
                        if movie_id:
                            comment_data = comment.copy()
                            comment_data['movie_id'] = movie_id
                            del comment_data['movie_url']
                            db.insert_comment(comment_data)
                except Exception as e:
                    logger.error(f"保存电影数据失败: {movie.get('title_cn', '未知')}, 错误: {e}")
                    continue
            
            db.close()
        except Exception as e:
            logger.warning(f"数据库保存失败，已保留CSV文件用于后续分析: {e}")
        
        # 6. 关闭浏览器
        if driver:
            driver.quit()
        
        end_time = time.time()
        elapsed_seconds = end_time - start_time
        record_performance(
            'requests',
            elapsed_seconds,
            movie_count=len(detailed_movies),
            comment_count=len(comments)
        )
        logger.info(f"requests列表页 + Selenium详情页爬虫运行完成，总耗时: {elapsed_seconds:.2f}秒")
        
    except Exception as e:
        logger.error(f"爬虫运行异常: {e}")
        record_performance(
            'requests',
            time.time() - start_time,
            success=False,
            movie_count=len(detailed_movies),
            comment_count=len(comments)
        )
        try:
            if driver:
                driver.quit()
        except:
            pass

def run_scrapy_spider():
    logger.info("="*50)
    logger.info("开始运行Scrapy版本爬虫")
    logger.info("="*50)
    
    start_time = time.time()
    
    try:
        # 切换到scrapy目录并运行爬虫
        scrapy_dir = os.path.join(BASE_DIR, 'scrapy_version')
        subprocess.run([sys.executable, '-m', 'scrapy', 'crawl', 'douban_movie'], cwd=scrapy_dir, check=True)
        
        end_time = time.time()
        elapsed_seconds = end_time - start_time
        record_performance('scrapy', elapsed_seconds)
        logger.info(f"Scrapy版本爬虫运行完成，总耗时: {elapsed_seconds:.2f}秒")
    except Exception as e:
        elapsed_seconds = time.time() - start_time
        record_performance('scrapy', elapsed_seconds, success=False, movie_count=0, comment_count=0)
        logger.error(f"Scrapy版本爬虫运行异常: {e}")

def run_analysis_and_visualization():
    logger.info("="*50)
    logger.info("开始数据分析和可视化")
    logger.info("="*50)
    
    start_time = time.time()
    
    # 1. 数据清洗
    cleaner = DataCleaner()
    movies_df, comments_df = cleaner.run()
    
    # 2. 统计分析
    analyzer = DataAnalyzer(movies_df, comments_df)
    analysis_results = analyzer.run_all_analysis()
    
    # 3. 情感分析
    sentiment_analyzer = SentimentAnalyzer(comments_df)
    comments_with_sentiment, sentiment_stats = sentiment_analyzer.run()
    cleaner.save_cleaned_data(movies_df, comments_with_sentiment)
    
    # 4. 可视化
    visualizer = DataVisualizer(movies_df, comments_with_sentiment, analysis_results, sentiment_stats)
    visualizer.generate_all_charts()
    
    end_time = time.time()
    elapsed_seconds = end_time - start_time
    record_performance(
        'analysis',
        elapsed_seconds,
        movie_count=len(movies_df),
        comment_count=len(comments_with_sentiment)
    )
    logger.info(f"数据分析和可视化完成，总耗时: {elapsed_seconds:.2f}秒")
    
    # 打印分析结果摘要
    print("\n" + "="*50)
    print("数据分析结果摘要")
    print("="*50)
    print(f"\n评分最高的Top10电影:")
    print(analysis_results['top10_movies'].to_string(index=False))
    
    print(f"\n\n评分与评价人数的相关系数: {analysis_results['rating_reviews_correlation']:.3f}")
    
    print(f"\n\n情感分析结果:")
    print(f"正面评论: {sentiment_stats['positive']} ({sentiment_stats['positive_ratio']:.1%})")
    print(f"中性评论: {sentiment_stats['neutral']} ({sentiment_stats['neutral_ratio']:.1%})")
    print(f"负面评论: {sentiment_stats['negative']} ({sentiment_stats['negative_ratio']:.1%})")

def main():
    parser = argparse.ArgumentParser(description='豆瓣电影Top250爬虫与数据分析系统')
    parser.add_argument('--requests', action='store_true', help='运行requests列表页 + Selenium详情页爬虫')
    parser.add_argument('--scrapy', action='store_true', help='运行Scrapy版本爬虫')
    parser.add_argument('--analysis', action='store_true', help='运行数据分析和可视化')
    parser.add_argument('--all', action='store_true', help='运行requests/Selenium爬虫和数据分析')
    parser.add_argument('--download-posters', action='store_true', help='运行requests爬虫时下载海报')
    args = parser.parse_args()
    
    if args.requests:
        run_requests_spider(download_posters=args.download_posters)
        return
    if args.scrapy:
        run_scrapy_spider()
        return
    if args.analysis:
        run_analysis_and_visualization()
        return
    if args.all:
        run_requests_spider(download_posters=args.download_posters)
        run_analysis_and_visualization()
        return
    
    print("豆瓣电影Top250爬虫与数据分析系统")
    print("="*50)
    print("请选择要运行的模块:")
    print("1. 运行requests版本爬虫")
    print("2. 运行Scrapy版本爬虫")
    print("3. 运行数据分析和可视化")
    print("4. 运行全部流程")
    print("="*50)
    
    choice = input("请输入选项(1-4): ")
    
    if choice == '1':
        run_requests_spider()
    elif choice == '2':
        run_scrapy_spider()
    elif choice == '3':
        run_analysis_and_visualization()
    elif choice == '4':
        run_requests_spider()
        run_analysis_and_visualization()
    else:
        print("无效的选项")

if __name__ == "__main__":
    main()
