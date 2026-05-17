import scrapy

class MovieItem(scrapy.Item):
    rank = scrapy.Field()
    title_cn = scrapy.Field()
    title_en = scrapy.Field()
    rating = scrapy.Field()
    rating_count = scrapy.Field()
    director = scrapy.Field()
    actors = scrapy.Field()
    summary = scrapy.Field()
    detail_url = scrapy.Field()
    release_year = scrapy.Field()
    duration = scrapy.Field()
    genres = scrapy.Field()
    imdb_id = scrapy.Field()
    poster_path = scrapy.Field()

class CommentItem(scrapy.Item):
    movie_url = scrapy.Field()
    reviewer = scrapy.Field()
    rating = scrapy.Field()
    content = scrapy.Field()
    comment_time = scrapy.Field()
    sentiment = scrapy.Field()
