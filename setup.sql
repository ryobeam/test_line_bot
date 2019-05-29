CREATE TABLE user (
 user_id TEXT NOT NULL PRIMARY KEY,
 display_name TEXT NOT NULL,
 picture_url TEXT,
 created_datetime TIMESTAMP DEFAULT (datetime(CURRENT_TIMESTAMP,'localtime'))
);
