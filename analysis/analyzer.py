import pandas as pd
import numpy as np
from utils.logger import logger

class DataAnalyzer:
    def __init__(self, movies_df, comments_df):
        self.movies_df = movies_df
        self.comments_df = comments_df
    
    def get_top10_movies(self):
        """获取评分最高的Top10电影"""
        top10 = self.movies_df.sort_values('rating', ascending=False).head(10)
        return top10[['rank', 'title_cn', 'rating', 'rating_count', 'director']]
    
    def get_director_distribution(self, top_n=10):
        """导演作品分布"""
        director_counts = self.movies_df['director'].str.split('/').explode().str.strip().value_counts()
        return director_counts.head(top_n)
    
    def get_genre_distribution(self):
        """电影类型分布"""
        genre_counts = self.movies_df['genres_list'].explode().str.strip().value_counts()
        return genre_counts
    
    def get_rating_vs_reviews_correlation(self):
        """评分与评价人数的相关性"""
        correlation = self.movies_df['rating'].corr(self.movies_df['rating_count'])
        return correlation
    
    def get_year_distribution(self):
        """上映年份分布"""
        year_counts = self.movies_df['release_year'].value_counts().sort_index()
        return year_counts
    
    def get_rating_distribution(self):
        """评分分布"""
        rating_counts = self.movies_df['rating'].value_counts().sort_index()
        return rating_counts
    
    def run_all_analysis(self):
        logger.info("开始进行数据分析")
        
        results = {
            'top10_movies': self.get_top10_movies(),
            'director_distribution': self.get_director_distribution(),
            'genre_distribution': self.get_genre_distribution(),
            'rating_reviews_correlation': self.get_rating_vs_reviews_correlation(),
            'year_distribution': self.get_year_distribution(),
            'rating_distribution': self.get_rating_distribution()
        }
        
        logger.info("数据分析完成")
        return results
