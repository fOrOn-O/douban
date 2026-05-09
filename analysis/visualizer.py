import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from wordcloud import WordCloud
import jieba
from config import BASE_DIR
import os
from utils.logger import logger

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class DataVisualizer:
    def __init__(self, movies_df, comments_df, analysis_results, sentiment_stats):
        self.movies_df = movies_df
        self.comments_df = comments_df
        self.analysis_results = analysis_results
        self.sentiment_stats = sentiment_stats
        self.output_dir = os.path.join(BASE_DIR, 'data', 'charts')
        os.makedirs(self.output_dir, exist_ok=True)
    
    def plot_rating_distribution(self):
        """评分分布直方图"""
        plt.figure(figsize=(12, 8))
        sns.histplot(data=self.movies_df, x='rating', bins=20, kde=True, color='skyblue')
        plt.title('豆瓣电影Top250评分分布', fontsize=16)
        plt.xlabel('评分', fontsize=12)
        plt.ylabel('电影数量', fontsize=12)
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'rating_distribution.png'), dpi=300)
        plt.close()
        logger.info("评分分布直方图已生成")
    
    def plot_genre_distribution(self):
        """电影类型饼图"""
        genre_counts = self.analysis_results['genre_distribution'].head(10)
        
        plt.figure(figsize=(12, 10))
        colors = sns.color_palette('pastel')[0:len(genre_counts)]
        wedges, texts, autotexts = plt.pie(
            genre_counts.values, 
            labels=genre_counts.index, 
            autopct='%1.1f%%',
            colors=colors,
            startangle=90
        )
        plt.title('豆瓣电影Top250类型分布', fontsize=16)
        plt.axis('equal')
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'genre_distribution.png'), dpi=300)
        plt.close()
        logger.info("类型分布饼图已生成")
    
    def plot_rating_vs_reviews(self):
        """评分与评价人数散点图"""
        plt.figure(figsize=(12, 8))
        sns.scatterplot(data=self.movies_df, x='rating', y='rating_count', alpha=0.6, s=100)
        
        # 添加趋势线
        z = np.polyfit(self.movies_df['rating'], self.movies_df['rating_count'], 1)
        p = np.poly1d(z)
        plt.plot(self.movies_df['rating'], p(self.movies_df['rating']), "r--", alpha=0.8)
        
        correlation = self.analysis_results['rating_reviews_correlation']
        plt.title(f'评分与评价人数关系 (相关系数: {correlation:.3f})', fontsize=16)
        plt.xlabel('评分', fontsize=12)
        plt.ylabel('评价人数', fontsize=12)
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'rating_vs_reviews.png'), dpi=300)
        plt.close()
        logger.info("评分与评价人数散点图已生成")
    
    def plot_year_trend(self):
        """上映年份趋势线图"""
        year_counts = self.analysis_results['year_distribution']
        
        plt.figure(figsize=(15, 8))
        sns.lineplot(x=year_counts.index, y=year_counts.values, marker='o', linewidth=2.5)
        plt.title('豆瓣电影Top250上映年份分布', fontsize=16)
        plt.xlabel('年份', fontsize=12)
        plt.ylabel('电影数量', fontsize=12)
        plt.xticks(rotation=45)
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'year_trend.png'), dpi=300)
        plt.close()
        logger.info("上映年份趋势线图已生成")
    
    def plot_sentiment_distribution(self):
        """情感分布饼图"""
        labels = ['正面', '中性', '负面']
        sizes = [
            self.sentiment_stats['positive_ratio'],
            self.sentiment_stats['neutral_ratio'],
            self.sentiment_stats['negative_ratio']
        ]
        colors = ['#66b3ff', '#99ff99', '#ff9999']
        
        plt.figure(figsize=(10, 8))
        wedges, texts, autotexts = plt.pie(
            sizes, 
            labels=labels, 
            autopct='%1.1f%%',
            colors=colors,
            startangle=90
        )
        plt.title('短评情感倾向分布', fontsize=16)
        plt.axis('equal')
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'sentiment_distribution.png'), dpi=300)
        plt.close()
        logger.info("情感分布饼图已生成")
    
    def generate_wordcloud(self):
        """短评词云"""
        # 合并所有评论
        all_comments = ' '.join(self.comments_df['content'].astype(str))
        
        # 分词
        words = jieba.cut(all_comments)
        words = [word for word in words if len(word) > 1 and word not in ['电影', '这部', '一个', '没有', '还是', '就是', '但是', '可以', '非常', '真的']]
        text = ' '.join(words)
        
        # 生成词云
        wc = WordCloud(
            font_path='C:/Windows/Fonts/simhei.ttf',
            width=1200,
            height=800,
            background_color='white',
            max_words=200,
            max_font_size=150,
            random_state=42
        ).generate(text)
        
        plt.figure(figsize=(15, 10))
        plt.imshow(wc, interpolation='bilinear')
        plt.axis('off')
        plt.title('豆瓣电影Top250短评词云', fontsize=20)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'comment_wordcloud.png'), dpi=300)
        plt.close()
        logger.info("短评词云已生成")
    
    def generate_all_charts(self):
        logger.info("开始生成所有可视化图表")
        
        self.plot_rating_distribution()
        self.plot_genre_distribution()
        self.plot_rating_vs_reviews()
        self.plot_year_trend()
        self.plot_sentiment_distribution()
        self.generate_wordcloud()
        
        logger.info(f"所有图表已生成并保存到: {self.output_dir}")
