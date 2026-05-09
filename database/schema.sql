CREATE DATABASE IF NOT EXISTS douban_movies DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE douban_movies;

-- 电影主表
CREATE TABLE IF NOT EXISTS movies (
    id INT PRIMARY KEY AUTO_INCREMENT,
    `rank` INT UNIQUE NOT NULL,
    title_cn VARCHAR(255) NOT NULL,
    title_en VARCHAR(255),
    rating FLOAT NOT NULL,
    rating_count INT NOT NULL,
    director VARCHAR(255),
    actors TEXT,
    summary TEXT,
    detail_url VARCHAR(255) UNIQUE NOT NULL,
    release_year INT,
    duration VARCHAR(50),
    genres VARCHAR(255),
    imdb_rating FLOAT,
    poster_path VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 短评表
CREATE TABLE IF NOT EXISTS comments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    movie_id INT NOT NULL,
    reviewer VARCHAR(100) NOT NULL,
    rating FLOAT,
    content TEXT NOT NULL,
    comment_time DATETIME,
    sentiment FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE
);
