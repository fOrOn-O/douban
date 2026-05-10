import json
import csv
import os
from database.db_connector import DBConnector
from config import CSV_DIR, JSON_DIR
from utils.logger import logger

class MySQLPipeline:
    def open_spider(self, spider):
        self.db = None
        try:
            self.db = DBConnector()
        except Exception as e:
            logger.warning(f"MySQL不可用，跳过数据库存储: {e}")
    
    def close_spider(self, spider):
        if self.db:
            self.db.close()
    
    def process_item(self, item, spider):
        if not self.db:
            return item
        
        if item.__class__.__name__ == 'MovieItem':
            try:
                self.db.insert_movie(dict(item))
                logger.debug(f"电影数据已保存: {item['title_cn']}")
            except Exception as e:
                logger.error(f"保存电影数据失败: {e}")
        
        elif item.__class__.__name__ == 'CommentItem':
            try:
                movie_id = self.db.get_movie_id_by_url(item['movie_url'])
                if movie_id:
                    comment_data = dict(item)
                    comment_data['movie_id'] = movie_id
                    del comment_data['movie_url']
                    self.db.insert_comment(comment_data)
                    logger.debug(f"评论数据已保存: {item['reviewer']}")
            except Exception as e:
                logger.error(f"保存评论数据失败: {e}")
        
        return item

class JsonPipeline:
    def open_spider(self, spider):
        self.movies_file = open(os.path.join(JSON_DIR, 'movies_scrapy.json'), 'w', encoding='utf-8')
        self.comments_file = open(os.path.join(JSON_DIR, 'comments_scrapy.json'), 'w', encoding='utf-8')
        self.movies_file.write('[\n')
        self.comments_file.write('[\n')
        self.first_movie = True
        self.first_comment = True
    
    def close_spider(self, spider):
        self.movies_file.write('\n]')
        self.comments_file.write('\n]')
        self.movies_file.close()
        self.comments_file.close()
    
    def process_item(self, item, spider):
        if item.__class__.__name__ == 'MovieItem':
            if not self.first_movie:
                self.movies_file.write(',\n')
            json.dump(dict(item), self.movies_file, ensure_ascii=False, indent=2, default=str)
            self.first_movie = False
        
        elif item.__class__.__name__ == 'CommentItem':
            if not self.first_comment:
                self.comments_file.write(',\n')
            json.dump(dict(item), self.comments_file, ensure_ascii=False, indent=2, default=str)
            self.first_comment = False
        
        return item

class CsvPipeline:
    def open_spider(self, spider):
        self.movies_writer = None
        self.comments_writer = None
        self.movies_file = open(os.path.join(CSV_DIR, 'movies_scrapy.csv'), 'w', newline='', encoding='utf-8-sig')
        self.comments_file = open(os.path.join(CSV_DIR, 'comments_scrapy.csv'), 'w', newline='', encoding='utf-8-sig')
    
    def close_spider(self, spider):
        self.movies_file.close()
        self.comments_file.close()
    
    def process_item(self, item, spider):
        if item.__class__.__name__ == 'MovieItem':
            if not self.movies_writer:
                self.movies_writer = csv.DictWriter(self.movies_file, fieldnames=item.keys())
                self.movies_writer.writeheader()
            self.movies_writer.writerow(dict(item))
        
        elif item.__class__.__name__ == 'CommentItem':
            if not self.comments_writer:
                self.comments_writer = csv.DictWriter(self.comments_file, fieldnames=item.keys())
                self.comments_writer.writeheader()
            self.comments_writer.writerow(dict(item))
        
        return item
