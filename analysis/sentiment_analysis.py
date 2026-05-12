import jieba
from snownlp import SnowNLP
import pandas as pd
from tqdm import tqdm
import os
from config import BASE_DIR
from utils.logger import logger

class SentimentAnalyzer:
    def __init__(self, comments_df):
        self.comments_df = comments_df
        # 加载停用词
        self.stopwords = self._load_stopwords()
    
    def _load_stopwords(self):
        stopwords = set()
        try:
            stopwords_path = os.path.join(BASE_DIR, 'utils', 'stopwords.txt')
            with open(stopwords_path, 'r', encoding='utf-8') as f:
                for line in f:
                    stopwords.add(line.strip())
        except:
            logger.warning("停用词文件未找到，使用默认空集合")
        return stopwords
    
    def preprocess_text(self, text):
        """文本预处理：分词、去停用词"""
        words = jieba.cut(text)
        words = [word for word in words if word not in self.stopwords and word.strip()]
        return ' '.join(words)
    
    def analyze_sentiment(self, text):
        """使用SnowNLP进行情感分析"""
        try:
            s = SnowNLP(text)
            return s.sentiments
        except:
            return 0.5  # 中性
    
    def run(self):
        logger.info("开始进行短评情感分析")
        if self.comments_df.empty:
            self.comments_df['sentiment'] = []
            sentiment_stats = {
                'positive': 0,
                'positive_ratio': 0,
                'neutral': 0,
                'neutral_ratio': 0,
                'negative': 0,
                'negative_ratio': 0
            }
            logger.info("情感分析完成: 无评论数据")
            return self.comments_df, sentiment_stats
        
        self.comments_df['content'] = self.comments_df['content'].fillna('').astype(str)
        if 'sentiment' not in self.comments_df.columns:
            self.comments_df['sentiment'] = pd.NA
        self.comments_df['sentiment'] = pd.to_numeric(self.comments_df['sentiment'], errors='coerce')
        
        missing_sentiment = self.comments_df['sentiment'].isna()
        if missing_sentiment.any():
            tqdm.pandas(desc="情感分析")
            self.comments_df.loc[missing_sentiment, 'sentiment'] = (
                self.comments_df.loc[missing_sentiment, 'content'].progress_apply(self.analyze_sentiment)
            )
        else:
            logger.info("检测到已有情感分析结果，跳过重复计算")
        
        # 统计情感分布
        positive = len(self.comments_df[self.comments_df['sentiment'] > 0.6])
        neutral = len(self.comments_df[(self.comments_df['sentiment'] >= 0.4) & (self.comments_df['sentiment'] <= 0.6)])
        negative = len(self.comments_df[self.comments_df['sentiment'] < 0.4])
        
        total = len(self.comments_df)
        sentiment_stats = {
            'positive': positive,
            'positive_ratio': positive / total,
            'neutral': neutral,
            'neutral_ratio': neutral / total,
            'negative': negative,
            'negative_ratio': negative / total
        }
        
        logger.info(f"情感分析完成: 正面{positive}({positive/total:.1%}), 中性{neutral}({neutral/total:.1%}), 负面{negative}({negative/total:.1%})")
        
        return self.comments_df, sentiment_stats
