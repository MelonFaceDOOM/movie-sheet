import sqlite3


def make_db(db_filename=None):
    if not db_filename:
        db_filename = 'melonbot.db'
    conn = sqlite3.connect(db_filename)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS guilds
                 (id INTEGER PRIMARY KEY NOT NULL, date datetime DEFAULT current_timestamp)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY NOT NULL, guild_id INTEGER NOT NULL,
                 date datetime DEFAULT current_timestamp,
                 FOREIGN KEY(guild_id) REFERENCES guilds (id),
                 UNIQUE(id, guild_id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS movies
                 (id INTEGER PRIMARY KEY, guild_id INTEGER NOT NULL, title TEXT NOT NULL COLLATE NOCASE,
                 date_suggested datetime DEFAULT current_timestamp, date_watched datetime,
                 user_id INTEGER NOT NULL, watched INTEGER DEFAULT 0,
                 FOREIGN KEY(guild_id) REFERENCES guilds (id),
                 FOREIGN KEY (user_id) REFERENCES users (id),
                 UNIQUE(guild_id, title))''')
    c.execute('''CREATE TABLE IF NOT EXISTS endorsements
                 (id INTEGER PRIMARY KEY, guild_id INTEGER NOT NULL,
                 date datetime DEFAULT current_timestamp, user_id INTEGER NOT NULL, 
                 movie_id INTEGER NOT NULL, 
                 FOREIGN KEY(guild_id) REFERENCES guilds (id),
                 FOREIGN KEY (user_id) REFERENCES users (id),
                 FOREIGN KEY(movie_id) REFERENCES movies (id),
                 UNIQUE(guild_id, user_id, movie_id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS ratings
                 (id INTEGER PRIMARY KEY, guild_id INTEGER NOT NULL,
                 date datetime DEFAULT current_timestamp, movie_id INTEGER NOT NULL,
                 user_id INTEGER NOT NULL, rating INTEGER NOT NULL,
                 FOREIGN KEY(guild_id) REFERENCES guilds (id),
                 FOREIGN KEY (user_id) REFERENCES users (id),
                 FOREIGN KEY(movie_id) REFERENCES movies (id),
                 UNIQUE(guild_id, user_id, movie_id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS reviews 
                 (id INTEGER PRIMARY KEY, guild_id INTEGER NOT NULL, date datetime DEFAULT current_timestamp,
                 movie_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
                 review_text TEXT NOT NULL,
                 FOREIGN KEY(guild_id) REFERENCES guilds (id),
                 FOREIGN KEY (user_id) REFERENCES users (id),
                 FOREIGN KEY(movie_id) REFERENCES movies (id),
                 UNIQUE(guild_id, user_id, movie_id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS tags 
                 (id INTEGER PRIMARY KEY, guild_id INTEGER NOT NULL,
                 date datetime DEFAULT current_timestamp, movie_id INTEGER NOT NULL, tag_text TEXT NOT NULL,
                 FOREIGN KEY(guild_id) REFERENCES guilds (id),
                 FOREIGN KEY(movie_id) REFERENCES movies (id),
                 UNIQUE(guild_id, movie_id, tag_text))''')
    conn.commit()


if __name__ == "__main__":
    make_db()
