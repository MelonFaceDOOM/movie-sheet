import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import APIError
global ws_future_movies
global ws_ratings
global ws_users
import sqlite3


scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']

credentials = ServiceAccountCredentials.from_json_keyfile_name('sheetapi-269619-39d07591cb19.json', scope)
gs = gspread.authorize(credentials)
gsheet = gs.open("movienight")
ws_future_movies = gsheet.worksheet("future movie")
ws_ratings = gsheet.worksheet("ratings")
ws_users = gsheet.worksheet("users")

conn = sqlite3.connect('melonbot.db')
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS users
             (discord_id INTEGER PRIMARY KEY NOT NULL UNIQUE, name TEXT NOT NULL UNIQUE COLLATE NOCASE,
             date datetime DEFAULT current_timestamp)''')
c.execute('''CREATE TABLE IF NOT EXISTS movies
            (title TEXT PRIMARY KEY NOT NULL UNIQUE COLLATE NOCASE, date datetime DEFAULT current_timestamp,
            chooser_discord_id INTEGER NOT NULL, watched INTEGER DEFAULT 0,
            FOREIGN KEY (chooser_discord_id) REFERENCES users (discord_id))''')
c.execute('''CREATE TABLE IF NOT EXISTS endorsements
            (id INTEGER PRIMARY KEY NOT NULL, date datetime DEFAULT current_timestamp,
             endorser_discord_id INTEGER NOT NULL, movie_title TEXT NOT NULL COLLATE NOCASE, 
             FOREIGN KEY (endorser_discord_id) REFERENCES users (discord_id),
             FOREIGN KEY(movie_title) REFERENCES movies (title))''')
c.execute('''CREATE TABLE IF NOT EXISTS ratings
             (id INTEGER PRIMARY KEY NOT NULL, date datetime DEFAULT current_timestamp, 
             movie_title TEXT NOT NULL COLLATE NOCASE, rater_discord_id INTEGER NOT NULL,
             rating INTEGER NOT NULL, 
             FOREIGN KEY (rater_discord_id) REFERENCES users (discord_id),
             FOREIGN KEY(movie_title) REFERENCES movies (title))''')
c.execute('''CREATE TABLE IF NOT EXISTS reviews 
             (id INTEGER PRIMARY KEY NOT NULL, date datetime DEFAULT current_timestamp,
             movie_title TEXT NOT NULL COLLATE NOCASE, reviewer_discord_id INTEGER NOT NULL,
             review_text TEXT NOT NULL,
             FOREIGN KEY (reviewer_discord_id) REFERENCES users (discord_id),
             FOREIGN KEY(movie_title) REFERENCES movies (title))''')
c.execute('''CREATE TABLE IF NOT EXISTS tags 
             (id INTEGER PRIMARY KEY NOT NULL, date datetime DEFAULT current_timestamp,
             movie_title TEXT NOT NULL COLLATE NOCASE, tag_text TEXT NOT NULL,
             FOREIGN KEY(movie_title) REFERENCES movies (title))''')
conn.commit()

users = ws_users.get_all_values()
for row in users[1:]:
    c.execute('''INSERT INTO users (discord_id, name) values (?,?)''', (row[0], row[1]))
conn.commit()

future_movies = ws_future_movies.get_all_values()
for future_movie in future_movies[1:]:
    for row in users[1:]:
        if row[1].lower() == future_movie[1].lower():
            chooser_discord_id = row[0]
            c.execute('''INSERT INTO movies (title, chooser_discord_id, watched) values (?,?,?)''',
                      (future_movie[0], chooser_discord_id, 0))
    else:
        pass  # expect some unregistered users here. just ignore

    endorsers = future_movie[2:]
    endorsers = [e for e in endorsers if e]
    for endorser in endorsers:
        for row in users[1:]:
            if row[1].lower() == endorser.lower():
                endorser_discord_id = row[0]
                c.execute('''INSERT INTO endorsements (endorser_discord_id, movie_title) values (?,?)''',
                          (endorser_discord_id, future_movie[0]))
                break
        else:
            pass  # expect some unregistered users here. just ignore

conn.commit()

rated_movies = ws_ratings.get_all_values()

raters = rated_movies[0][2:]

for rated_movie in rated_movies[1:]:
    for row in users[1:]:
        if row[1].lower() == rated_movie[1].lower():
            chooser_discord_id = row[0]
            c.execute('''INSERT INTO movies (title, chooser_discord_id, watched) values (?,?,?)''',
                      (rated_movie[0], chooser_discord_id, 1))
            break
    else:
        pass

    scores = rated_movie[2:]
    for i, score in enumerate(scores):
        if score:
            for row in users[1:]:
                if row[1].lower() == raters[i].lower():
                    rater_discord_id = row[0]
                    c.execute('''INSERT INTO ratings (movie_title, rater_discord_id, rating) values (?,?,?)''',
                              (rated_movie[0], rater_discord_id, score))
                    break
            else:
                pass

conn.commit()