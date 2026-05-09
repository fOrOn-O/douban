import time
import os
from utils.logger import logger
from database.db_connector import DBConnector
from requests_version.basic_spider import BasicMovieSpider
from requests_version.detail_spider import DetailSpider
from requests_version.image_downloader import PosterDownloader
from analysis.data_cleaner import DataCleaner
from analysis.analyzer import DataAnalyzer
from analysis.sentiment_analysis import SentimentAnalyzer
from analysis.visualizer import DataVisualizer

def run_requests_spider():
    logger.info("="*50)
    logger.info("开始运行全Selenium版本爬虫")
    logger.info("="*50)
    
    start_time = time.time()
    
    try:
        # 1. 初始化浏览器（只启动一次，共用）
        from requests_version.basic_spider import BasicMovieSpider
        basic_spider = BasicMovieSpider()
        driver = basic_spider.driver
        
        # 2. 爬取列表页
        movies = basic_spider.crawl_all_pages()
        
        if len(movies) == 0:
            logger.error("列表页未获取到任何电影，终止运行")
            return
        
        # 3. 爬取详情页和短评（共用同一个浏览器）
        from requests_version.detail_spider import DetailSpider
        detail_spider = DetailSpider(driver)
        detailed_movies, comments = detail_spider.crawl_movie_details(movies)
        
        # 4. 跳过海报下载（为了快速完成）
        for movie in detailed_movies:
            movie['poster_path'] = None
        
        # 5. 保存到数据库
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
                        comment['movie_id'] = movie_id
                        del comment['movie_url']
                        db.insert_comment(comment)
            except Exception as e:
                logger.error(f"保存电影数据失败: {movie.get('title_cn', '未知')}, 错误: {e}")
                continue
        
        db.close()
        
        # 6. 关闭浏览器
        driver.quit()
        
        end_time = time.time()
        logger.info(f"全Selenium版本爬虫运行完成，总耗时: {end_time - start_time:.2f}秒")
        
    except Exception as e:
        logger.error(f"爬虫运行异常: {e}")
        try:
            driver.quit()
        except:
            pass

def run_scrapy_spider():
    logger.info("="*50)
    logger.info("开始运行Scrapy版本爬虫")
    logger.info("="*50)
    
    start_time = time.time()
    
    # 切换到scrapy目录并运行爬虫
    os.chdir('D:\Python爬虫\project2.0\douban_movie_analyzer\scrapy_version')
    os.system('scrapy crawl douban_movie')
    os.chdir('..')
    
    end_time = time.time()
    logger.info(f"Scrapy版本爬虫运行完成，总耗时: {end_time - start_time:.2f}秒")

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
    
    # 4. 可视化
    visualizer = DataVisualizer(movies_df, comments_with_sentiment, analysis_results, sentiment_stats)
    visualizer.generate_all_charts()
    
    end_time = time.time()
    logger.info(f"数据分析和可视化完成，总耗时: {end_time - start_time:.2f}秒")
    
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
