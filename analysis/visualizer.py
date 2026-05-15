import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from wordcloud import WordCloud
import jieba
from config import BASE_DIR
import os
from matplotlib import font_manager
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
    
    def get_wordcloud_font_path(self):
        candidates = [
            os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', 'simhei.ttf'),
            os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', 'msyh.ttc'),
            '/System/Library/Fonts/PingFang.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'
        ]
        for font_path in candidates:
            if os.path.exists(font_path):
                return font_path
        for font_path in font_manager.findSystemFonts():
            lower_path = font_path.lower()
            if any(name in lower_path for name in ['simhei', 'msyh', 'pingfang', 'wqy', 'noto']):
                return font_path
        return None
    
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
        valid_df = self.movies_df[['rating', 'rating_count']].dropna()
        if len(valid_df) >= 2 and valid_df['rating'].nunique() >= 2:
            z = np.polyfit(valid_df['rating'], valid_df['rating_count'], 1)
            p = np.poly1d(z)
            plt.plot(valid_df['rating'], p(valid_df['rating']), "r--", alpha=0.8)
        
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
        year_counts = year_counts[year_counts.index > 0]
        
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
        if sum(sizes) == 0:
            sizes = [0, 1, 0]
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
        if not text.strip():
            text = '暂无评论 数据分析 电影 评分 可视化'
        
        # 生成词云
        wc_kwargs = dict(
            font_path=self.get_wordcloud_font_path(),
            width=1200,
            height=800,
            background_color='white',
            max_words=200,
            max_font_size=150,
            random_state=42
        )
        if not wc_kwargs['font_path']:
            wc_kwargs.pop('font_path')
        wc = WordCloud(**wc_kwargs).generate(text)
        
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

        chart_methods = [
            ('评分分布', self.plot_rating_distribution),
            ('类型分布', self.plot_genre_distribution),
            ('评分与评论关系', self.plot_rating_vs_reviews),
            ('上映年份趋势', self.plot_year_trend),
            ('情感分布', self.plot_sentiment_distribution),
            ('短评词云', self.generate_wordcloud),
        ]

        success_count = 0
        for name, method in chart_methods:
            try:
                method()
                success_count += 1
            except Exception as e:
                logger.error(f"图表「{name}」生成失败: {e}")

        logger.info(f"图表生成完成: {success_count}/{len(chart_methods)} 成功，保存到: {self.output_dir}")
