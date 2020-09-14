import sqlite3
from datetime import datetime
conn = sqlite3.connect('old.db')
c = conn.cursor()
conn2 = sqlite3.connect('melonbot.db')
c2 = conn2.cursor()

guild_id = 366280562190843904
date_format = '%Y-%m-%d %H:%M:%S'

c.execute('''SELECT * FROM users''')
users = c.fetchall()
c.execute('''SELECT * FROM movies''')
movies = c.fetchall()
c.execute('''SELECT * FROM endorsements''')
endorsements = c.fetchall()
c.execute('''SELECT * FROM ratings''')
ratings = c.fetchall()
c.execute('''SELECT * FROM reviews''')
reviews = c.fetchall()
c.execute('''SELECT * FROM tags''')
tags = c.fetchall()

new_users = []
for user in users:
    date = datetime.strptime(user[2], date_format)
    new_user = [user[0], guild_id, date]
    new_users.append(new_user)

new_movies = []
for movie in movies:
    date = datetime.strptime(movie[1], date_format)
    new_movie = [guild_id, movie[0], date, "", movie[2], movie[3]]
    new_movies.append(new_movie)

c2.execute('''INSERT INTO guilds (id) values (?)''', (guild_id,))
c2.executemany('''INSERT INTO users (id, guild_id, date) values (?,?,?)''', new_users)
c2.executemany('''INSERT INTO movies (guild_id, title, date_suggested, date_watched, user_id, watched) values (?,?,?,?,?,?)''',
new_movies)

conn2.commit()

additional_movies = [
    [guild_id, 'Triangle', '', '', '', 1],
    [guild_id, 'frighteners', '', '', '', 1],
    [guild_id, 'Night Porter', '', '', 281637395391184936, 0],
    [guild_id, 'george of the jungle', '', '', 323709592041291776, 0],
    [guild_id, 'top gun', '', '', 150717555529482241, 0],
    [guild_id, 'Heathers', '', '', 592487392124862515, 0],
    [guild_id, 'cats', '', '', 323709592041291776, 0],
    [guild_id, 'now you see me 2', '', '', 117340965760532487, 0]
]
c2.executemany('''INSERT INTO movies (guild_id, title, date_suggested, date_watched, user_id, watched) values (?,?,?,?,?,?)''',
additional_movies)
conn2.commit()

skipped_movies_endorsements = []
new_endorsements = []
combinations = [] # track unique guild_id, user_id, and movie_id so duplicates aren't added
for endorsement in endorsements:
    movie_name = endorsement[3]
    c2.execute('''SELECT id FROM movies WHERE title = ?''', (movie_name, ))
    movie_id = c2.fetchone()
    if movie_id:
        movie_id = movie_id[0]
        combination = [guild_id, endorsement[2], movie_id]
        if combination not in combinations:
            combinations.append(combination)
            date = datetime.strptime(endorsement[1], date_format)
            new_endorsement = [endorsement[0], guild_id, date, endorsement[2], movie_id]
            new_endorsements.append(new_endorsement)
    else:
        skipped_movies_endorsements.append(endorsement)
    
skipped_movies_ratings = []
new_ratings = []
for rating in ratings:
    movie_name = rating[2]
    c2.execute('''SELECT id FROM movies WHERE title = ?''', (movie_name, ))
    movie_id = c2.fetchone()
    if movie_id:
        movie_id = movie_id[0]
        date = datetime.strptime(rating[1], date_format)
        new_rating = [rating[0], guild_id, date, movie_id, rating[3], rating[4]]
        new_ratings.append(new_rating)
    else:
        skipped_movies_ratings.append(rating)

skipped_movies_reviews = []
new_reviews = []
for review in reviews:
    movie_name = review[2]
    c2.execute('''SELECT id FROM movies WHERE title = ?''', (movie_name, ))
    movie_id = c2.fetchone()
    if movie_id:
        movie_id = movie_id[0]
        date = datetime.strptime(review[1], date_format)
        new_review = [review[0], guild_id, date, movie_id, review[3], review[4]]
        new_reviews.append(new_review)
    else:
        skipped_movies_reviews.append(movie_name)        

skipped_movies_tags = []
new_tags = []
for tag in tags:
    movie_name = tag[2]
    c2.execute('''SELECT id FROM movies WHERE title = ?''', (movie_name, ))
    movie_id = c2.fetchone()
    if movie_id:
        movie_id = movie_id[0]
        date = datetime.strptime(tag[1], date_format)
        new_tag = [tag[0], guild_id, date, movie_id, tag[3]]
        new_tags.append(new_tag)
    else:
        skipped_movies_tags.append(movie_name)
        
c2.executemany('''INSERT INTO endorsements (id, guild_id, date, user_id, movie_id) values (?,?,?,?,?)''',
new_endorsements)
c2.executemany('''INSERT INTO ratings (id, guild_id, date, movie_id, user_id, rating) values (?,?,?,?,?,?)''',
new_ratings)
c2.executemany('''INSERT INTO reviews (id, guild_id, date, movie_id, user_id, review_text) values (?,?,?,?,?,?)''',
new_reviews)
c2.executemany('''INSERT INTO tags (id, guild_id, date, movie_id, tag_text) values (?,?,?,?,?)''',
new_tags)
conn2.commit()