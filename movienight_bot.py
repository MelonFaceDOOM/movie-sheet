import random
from matching import find_closest_match
import sqlite3


class movieNightBot:
    def __init__(self, db_file=None):
        if not db_file:
            db_file = 'movie_night_bot.db'
        self.conn = sqlite3.connect(db_file)
        self.conn.row_factory = sqlite3.Row
        c = self.conn.cursor()
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
        self.conn.commit()

    def register(self, discord_id, nick):
        c = self.conn.cursor()
        if len(nick) < 2:
            raise ValueError('nick must be at least 2 character.')
        name_already_taken = self.name_to_discord_id(nick)
        if name_already_taken:
            raise ValueError(f'the name "{nick}" is already taken.')
        old_nick = self.discord_id_to_name(discord_id)
        if old_nick:
            c.execute('''UPDATE users SET name = ? WHERE discord_id = ?''', (nick, discord_id))
        else:
            c.execute('''INSERT INTO users (discord_id, name) values (?,?)''', (discord_id, nick))
        self.conn.commit()

    # def delete_user(self, discord_id):
    #     c = self.conn.cursor()
    #     c.execute('''DELETE FROM users WHERE discord_id = ?''', (discord_id,))
    #     self.conn.commit()

    def name_to_discord_id(self, nick):
        c = self.conn.cursor()
        c.execute('''SELECT discord_id FROM users WHERE name = ?''', (nick,))
        row = c.fetchone()
        if row:
            return row['discord_id']
        else:
            return None

    def discord_id_to_name(self, discord_id):
        c = self.conn.cursor()
        c.execute('''SELECT name FROM users WHERE discord_id = ?''', (discord_id,))
        row = c.fetchone()
        if row:
            return row['name']
        else:
            return None

    def find_exact_movie(self, movie_title):
        """finds an exact movie (case insensitive), as opposed to the best match technique in find_all()"""
        c = self.conn.cursor()
        c.execute('''SELECT * FROM movies WHERE title = ?''', (movie_title, ))
        row = c.fetchone()
        if row:
            return row
        else:
            return False
    
    def suggest_movie(self, movie_title, chooser_discord_id):
        chooser_name = self.discord_id_to_name(chooser_discord_id)
        if not chooser_name:
            raise ValueError('Suggestion requested by unregistered user.\nPlease register with "!register <nick>".')
        existing_movie = self.find_exact_movie(movie_title)
        if existing_movie:
            if existing_movie['watched'] == 1:
                raise ValueError(f'The movie {movie_title} has already been watched.')
            elif existing_movie['watched'] == 0:
                raise ValueError(f'The movie {movie_title} has already been suggested.')
        c = self.conn.cursor()
        c.execute('''INSERT INTO movies (title, chooser_discord_id, watched) values (?,?,?)''',
                  (movie_title, chooser_discord_id, 0))
        self.conn.commit()

    def remove_suggestion(self, movie_title, deleter_discord_id):
        deleter_name = self.discord_id_to_name(deleter_discord_id)
        if not deleter_name:
            raise ValueError('Deletion requested by unregistered user.\nPlease register with "!register <nick>".')
        existing_movie = self.find_exact_movie(movie_title)
        if not existing_movie:
            raise ValueError(f'The movie "{movie_title}" could not be found.')
        elif existing_movie['watched'] == 1:
            raise ValueError(f'The movie "{movie_title}" has already been watched, so it cannot be removed.')
        elif existing_movie['chooser_discord_id'] != deleter_discord_id:
            raise ValueError(f'The movie {movie_title} can only be removed by its owner, {deleter_name}.')
        c = self.conn.cursor()
        c.execute('''DELETE FROM movies WHERE title = ? AND watched = ?''', (movie_title, 0))
        self.conn.commit()

    def transfer_suggestion(self, movie_title, transferer_discord_id, new_chooser_name):
        new_chooser_discord_id = self.name_to_discord_id(new_chooser_name)
        if not new_chooser_discord_id:
            raise ValueError(f'The user {new_chooser_name} could not be found.')
        transferer_name = self.discord_id_to_name(transferer_discord_id)
        if not transferer_name:
            raise ValueError('Transfer requested by unregistered user.\nPlease register with "!register <nick>"')
        existing_movie = self.find_exact_movie(movie_title)
        if not existing_movie:
            raise ValueError(f'The movie "{movie_title}" could not be found')
        elif existing_movie['watched'] == 1:
            raise ValueError(f'The movie "{movie_title}" has already been watched, so it cannot be transferred')
        elif existing_movie['chooser_discord_id'] != transferer_discord_id:
            chooser_name = self.discord_id_to_name(existing_movie['chooser_discord_id'])
            raise ValueError(f'The movie {movie_title} can only be transferred by its owner, {chooser_name}')
        c = self.conn.cursor()
        c.execute('''UPDATE movies SET chooser_discord_id = ? WHERE title = ?''',
                  (new_chooser_discord_id, movie_title))
        self.conn.commit()
        
    def find_all(self, search_term):
        c = self.conn.cursor()
        if search_term.strip() == "":
            raise ValueError("search term cannot be blank")

        c.execute('''SELECT title FROM movies''')
        rows = c.fetchall()
        movies = [row['title'].lower() for row in rows]

        c.execute('''SELECT name FROM users''')
        rows = c.fetchall()
        usernames = [row['name'].lower() for row in rows]

        full_search_list = movies + usernames
        best_match = find_closest_match(search_term, full_search_list)

        if not best_match:
            raise ValueError(f'"{search_term}" was not found.')

        if best_match in movies:
            c.execute('''SELECT users.name, movies.watched FROM movies
                         INNER JOIN users ON movies.chooser_discord_id = users.discord_id
                         WHERE movies.title = ?''',
                      (best_match,))
            movie = c.fetchone()

            if movie['watched']:
                c.execute('''SELECT ratings.rating, users.name FROM ratings
                             INNER JOIN users ON ratings.rater_discord_id = users.discord_id
                             WHERE ratings.movie_title = ?''',
                          (best_match,))
                ratings_with_rater_names = c.fetchall()
                ratings = [row['rating'] for row in ratings_with_rater_names]
                if not ratings:
                    average = float('nan')
                else:
                    average = sum(ratings)/len(ratings)
                    average = '{:02.1f}'.format(float(average))
                message = f"------ {best_match.upper()} ({movie['name'].upper()})------\nAverage Score: {average}\n"
                for row in ratings_with_rater_names:
                    rating = '{:02.1f}'.format(float(row['rating']))
                    message += (f"{row['name']}: {rating}\n")
                return message
            else:
                message = f"------ {best_match.upper()} - {movie['name'].upper()} ------\nEndorsed by:\n"
                c.execute('''SELECT users.name FROM users
                             INNER JOIN endorsements ON users.discord_id = endorsements.endorser_discord_id
                             WHERE endorsements.movie_title = ?''',
                          (best_match,))
                endorsers = c.fetchall()
                endorsers = [row['name'] for row in endorsers]
                for endorser in endorsers:
                    message += f"{endorser}\n"
                return message

        if best_match in usernames:
            c.execute('''SELECT movies.title FROM movies
                         INNER JOIN users ON movies.chooser_discord_id = users.discord_id
                         WHERE users.name = ? and movies.watched = ?''', (best_match, 1))
            rows = c.fetchall()
            movies_watched = [row['title'] for row in rows]
            c.execute('''SELECT ratings.rating FROM ratings
                         INNER JOIN movies ON ratings.movie_title = movies.title
                         INNER JOIN users ON movies.chooser_discord_id = users.discord_id
                         WHERE users.name = ? and movies.watched = ?''', (best_match, 1))
            rows = c.fetchall()
            ratings_received = [row['rating'] for row in rows]
            c.execute('''SELECT movies.title FROM movies 
                         INNER JOIN users ON movies.chooser_discord_id = users.discord_id
                         WHERE users.name = ? and movies.watched = ?''', (best_match, 0))
            rows = c.fetchall()
            suggestions = [row['title'] for row in rows]
            c.execute('''SELECT ratings.rating FROM ratings
                         INNER JOIN users ON ratings.rater_discord_id = users.discord_id
                         WHERE users.name = ?''', (best_match,))
            rows = c.fetchall()
            ratings_given = [row['rating'] for row in rows]

            message = f'------ {best_match.upper()} ------\n'
            if not movies_watched:
                message += f"None of {best_match.upper()}'s suggestions have been watched yet.\n"
            else:
                message += f"{len(movies_watched)} of {best_match.upper()}'s suggestions {'have' if len(movies_watched) > 1 else 'has'} been watched so far.\n"
                average_score = sum(ratings_received)/len(ratings_received)
                average_score = '{:02.1f}'.format(float(average_score))
                message += f'{best_match.upper()} receives an average score of {average_score}.\n'

            if not ratings_given:
                message += f'{best_match.upper()} has not rated any movies.\n'
            else:
                average = sum(ratings_given)/len(ratings_given)
                average = '{:02.1f}'.format(float(average))
                message += f'{best_match.upper()} has given {len(ratings_given)} rating{"s" if len(ratings_given) > 1 else ""}, with an average of {average}.\n'

            if not suggestions:
                message += f'{best_match.upper()} does not currently have any movie suggestions.\n'
            else:
                message += f'{best_match.upper()} currently has {len(suggestions)} movie suggestion{"s" if len(suggestions) > 1 else ""}.\n\n'

            message += f'find more info with !chooser {best_match}, !ratings {best_match}, or !suggestions {best_match}.'
            return message

        raise ValueError(f'Could not find rating because "{search_term}" was not found.')
            
    def is_endorsed(self, movie_title, endorser_discord_id):
        c = self.conn.cursor()
        c.execute('''SELECT endorser_discord_id FROM endorsements WHERE movie_title = ?''', (movie_title,))
        current_endorsers = c.fetchall()
        current_endorsers = [e['endorser_discord_id'] for e in current_endorsers]
        if endorser_discord_id in current_endorsers:
            return True
        else:
            return False
            
    def endorse_suggestion(self, movie_title, endorser_discord_id):
        endorser_name = self.discord_id_to_name(endorser_discord_id)
        if not endorser_name:
            raise ValueError('Endorsement requested by unregistered user.\nPlease register with "!register <nick>".')
        existing_movie = self.find_exact_movie(movie_title)
        if not existing_movie:
            raise ValueError(f'The movie "{movie_title}" could not be found.')
        elif existing_movie['watched'] == 1:
            raise ValueError(f'The movie "{movie_title}" has already been watched, so it cannot be endorsed.')
        elif existing_movie['chooser_discord_id'] == endorser_discord_id:
            raise ValueError(f'You cannot endorse your own movie.')
        elif self.is_endorsed(movie_title, endorser_discord_id):
            raise ValueError(f'{movie_title} has already been endorsed by {endorser_name}.')
        c = self.conn.cursor()
        c.execute('''INSERT INTO endorsements (endorser_discord_id, movie_title) values (?,?)''',
                  (endorser_discord_id, movie_title))
        self.conn.commit()
        return None

    def unendorse_suggestion(self, movie_title, endorser_discord_id):
        endorser_name = self.discord_id_to_name(endorser_discord_id)
        if not endorser_name:
            raise ValueError('Endorsement requested by unregistered user.\nPlease register with "!register <nick>".')
        existing_movie = self.find_exact_movie(movie_title)
        if not existing_movie:
            raise ValueError(f'The movie "{movie_title}" could not be found.')
        if not self.is_endorsed(movie_title, endorser_discord_id):
            raise ValueError(f'{movie_title} is not currently endorsed by {endorser_name}.')
        c = self.conn.cursor()
        c.execute('''DELETE FROM endorsements WHERE  endorser_discord_id = ? AND movie_title = ?''',
                  (endorser_discord_id, movie_title))
        self.conn.commit()
        return None

    def rate_movie(self, movie_title, rater_discord_id, rating):
        rater_name = self.discord_id_to_name(rater_discord_id)
        if not rater_name:
            raise ValueError(f'The user {rater_name} could not be found.')
        if float(rating) < 1 or float(rating) > 10:
            raise ValueError('rating must be between 1 and 10')
        existing_movie = self.find_exact_movie(movie_title)
        if not existing_movie:
            raise ValueError(f'The movie "{movie_title}" could not be found.')
        c = self.conn.cursor()
        c.execute('''UPDATE movies SET watched = ? WHERE title = ?''', (1, movie_title))
        c.execute('''SELECT rating FROM ratings where movie_title = ? and rater_discord_id = ?''',
                  (movie_title, rater_discord_id))
        existing_rating = c.fetchone()
        if existing_rating:
            c.execute('''UPDATE ratings SET rating = ? WHERE movie_title = ? and rater_discord_id = ?''',
                      (rating, movie_title, rater_discord_id))
        else:
            c.execute('''INSERT INTO ratings (rating, movie_title, rater_discord_id) values (?,?,?)''',
                      (rating, movie_title, rater_discord_id))
        self.conn.commit()
        return None

    def remove_rating(self, movie_title, rater_discord_id):
        rater_name = self.discord_id_to_name(rater_discord_id)
        if not rater_name:
            raise ValueError('Rating removal requested by unregistered user.\nPlease register with "!register <nick>".')
        existing_movie = self.find_exact_movie(movie_title)
        if not existing_movie:
            raise ValueError(f'The movie "{movie_title}" could not be found.')
        c = self.conn.cursor()
        c.execute('''SELECT rating FROM ratings where movie_title = ? and rater_discord_id = ?''',
                  (movie_title, rater_discord_id))
        existing_rating = c.fetchone()
        if not existing_rating:
            raise ValueError(f'A rating from {rater_name} for "{movie_title}" could not be found.')
        c.execute('''DELETE FROM ratings WHERE movie_title = ? and rater_discord_id = ?''',
                  (movie_title, rater_discord_id))
        self.conn.commit()

    def review_movie(self, movie_title, reviewer_discord_id, review_text):
        reviewer_name = self.discord_id_to_name(reviewer_discord_id)
        if not reviewer_name:
            raise ValueError('Review submitted by unregistered user.\nPlease register with "!register <nick>".')
        existing_movie = self.find_exact_movie(movie_title)
        if not existing_movie:
            raise ValueError(f'The movie "{movie_title}" could not be found.')
        c = self.conn.cursor()
        c.execute('''SELECT * FROM reviews WHERE movie_title = ? and reviewer_discord_id = ?''',
                  (movie_title, reviewer_discord_id))
        existing_review = c.fetchone()
        if existing_review:
            c.execute('''DELETE FROM reviews WHERE movie_title = ? and reviewer_discord_id = ?''',
                      (movie_title, reviewer_discord_id))
        c.execute('''INSERT INTO reviews (movie_title, reviewer_discord_id, review_text) values (?,?,?)''', (
            movie_title, reviewer_discord_id, review_text))
        self.conn.commit()

    def find_rating_for_movie_and_discord_id(self, movie_title, rater_discord_id):
        c = self.conn.cursor()
        c.execute('''SELECT rating FROM ratings WHERE movie_title = ? and rater_discord_id = ?''',
                  (movie_title, rater_discord_id))
        rating = c.fetchone()
        if rating:
            return rating['rating']
        else:
            return None

    def find_reviews(self, movie_title=None, reviewer_name=None):
        c = self.conn.cursor()
        if reviewer_name:
            reviewer_discord_id = self.name_to_discord_id(reviewer_name)
            if not reviewer_discord_id:
                raise ValueError(f'Could not find user with name {reviewer_name}.')

            if movie_title:
                c.execute('''SELECT review_text FROM reviews WHERE movie_title = ? and reviewer_discord_id = ?''',
                          (movie_title, reviewer_discord_id))
                review = c.fetchone()
                if not review:
                    raise ValueError(f'Could not find a review from {reviewer_name} for "{movie_title}".')
                rating = self.find_rating_for_movie_and_discord_id(movie_title, reviewer_discord_id)
                if rating:
                    rating = f'{str(rating)}/10'
                else:
                    rating = "N/A"
                message = f"------ {movie_title.upper()} reviewed by {reviewer_name.upper()} ------\n"
                message += f'{review["review_text"]}\n-{rating}'
            elif not movie_title:
                c.execute('''SELECT movie_title, review_text FROM reviews WHERE reviewer_discord_id = ?''',
                          (reviewer_discord_id,))
                reviews = c.fetchall()
                message = f"------ REVIEWS FROM {reviewer_name.upper()} ------\n"
                for review in reviews:
                    rating = self.find_rating_for_movie_and_discord_id(review['movie_title'], reviewer_discord_id)
                    if rating:
                        rating = f'{str(rating)}/10'
                    else:
                        rating = "N/A"
                    review_text = review['review_text']
                    if len(review_text) > 100:
                        review_text = review_text[:100] + "..."
                    message += f'{review["movie_title"]} - {rating}:\n{review_text}\n\n'

        elif movie_title and not reviewer_name:
            message = f"------ REVIEWS FOR {movie_title.upper()} ------\n"
            c.execute('''SELECT review_text, reviewer_discord_id FROM reviews WHERE movie_title = ?''',
                      (movie_title,))
            reviews = c.fetchall()
            if not reviews:
                raise ValueError(f'Could not find any reviews for "{movie_title}".')
            for review in reviews:
                reviewer_discord_id = review['reviewer_discord_id']
                reviewer = self.discord_id_to_name(reviewer_discord_id)
                rating = self.find_rating_for_movie_and_discord_id(movie_title, reviewer_discord_id)
                if rating:
                    rating = f'{str(rating)}/10'
                else:
                    rating = "N/A"
                review_text = review['review_text']
                if len(review_text) > 100:
                    review_text = review_text[:100] + "..."
                message += f'{reviewer} ({rating}): {review_text}\n\n'
        return message

    def tag_movie(self, movie_title, tag_text):
        existing_movie = self.find_exact_movie(movie_title)
        if not existing_movie:
            raise ValueError(f'The movie "{movie_title}" could not be found.')
        c = self.conn.cursor()
        c.execute('''SELECT * FROM tags WHERE movie_title = ? and tag_text = ?''', (movie_title, tag_text))
        existing_tag = c.fetchone()
        if existing_tag:
            raise ValueError(f'The movie "{movie_title}" has already been tagged as "{tag_text}".')
        c.execute('''INSERT INTO tags (movie_title, tag_text) values (?,?)''', (
            movie_title, tag_text))
        self.conn.commit()

    def untag_movie(self, movie_title, tag_text):
        existing_movie = self.find_exact_movie(movie_title)
        if not existing_movie:
            raise ValueError(f'The movie "{movie_title}" could not be found.')
        c = self.conn.cursor()
        c.execute('''SELECT * FROM tags WHERE movie_title = ? and tag_text = ?''', (movie_title, tag_text))
        existing_tag = c.fetchone()
        if not existing_tag:
            raise ValueError(f'The movie "{movie_title}" is not tagged with "{tag_text}".')
        c.execute('''DELETE FROM tags WHERE movie_title = ? AND tag_text = ?''', (
            movie_title, tag_text))
        self.conn.commit()

    def find_movies_with_tags(self, tags, mutually_inclusive=True):
        c = self.conn.cursor()
        c.execute('SELECT movie_title, tag_text FROM tags WHERE tag_text IN (%s) ORDER BY movie_title' %
                  ','.join('?' * len(tags)), tags)
        rows = c.fetchall()
        if not rows:
            raise ValueError("No movies found with the provided tags.")

        # assumes all tags for the same movie will be grouped together
        movies_and_tags = {}
        previous_movie = ""
        for row in rows:
            if row['movie_title'] == previous_movie:
                movies_and_tags[previous_movie].append(row['tag_text'])
            else:
                movies_and_tags[row['movie_title']] = [row['tag_text']]
                previous_movie = row['movie_title']
        message = f'------ MOVIES TAGGED AS {", ".join(tags).upper()} ------\n'
        movies_that_meet_criteria = []
        if mutually_inclusive:
            for movie in movies_and_tags:
                keep = True
                movie_tags = movies_and_tags[movie]
                for tag in tags:
                    if tag not in movie_tags:
                        keep = False
                        break
                if keep:
                    movies_that_meet_criteria.append(movie)
        else:
            for movie in movies_and_tags:
                keep = False
                movie_tags = movies_and_tags[movie]
                for tag in tags:
                    if tag in movie_tags:
                        keep = True
                        break
                if keep:
                    movies_that_meet_criteria.append(movie)
        for movie in movies_that_meet_criteria:
            message += movie + "\n"
        return message

    def find_movie_tags(self, movie_title):
        existing_movie = self.find_exact_movie(movie_title)
        if not existing_movie:
            raise ValueError(f'The movie "{movie_title}" could not be found.')
        c = self.conn.cursor()
        message = f"------ TAGS FOR {movie_title.upper()} ------\n"
        c.execute('''SELECT tag_text FROM tags WHERE movie_title = ?''', (movie_title,))
        rows = c.fetchall()
        tags = [row['tag_text'] for row in rows]
        for tag in tags:
            message += tag + "\n"
        return message

    def retrieve_suggestions(self, chooser_discord_id):
        chooser_name = self.discord_id_to_name(chooser_discord_id)
        if not chooser_name:
            raise ValueError(f'User associated with discord_id {chooser_discord_id} not found')
        c = self.conn.cursor()
        c.execute('''SELECT title FROM movies WHERE chooser_discord_id = ? and watched = ?''', (chooser_discord_id, 0))
        suggestions = c.fetchall()
        suggestions = [suggestion['title'] for suggestion in suggestions]
        if not suggestions:
            raise ValueError(f'No suggestions found for {chooser_name}')
        message = f"------ SUGGESTIONS FROM {chooser_name.upper()} ------\n"
        for suggestion in suggestions:
            message += suggestion + "\n"
        return message

    def top_endorsed(self, n=10):
        c = self.conn.cursor()
        """return movies with the most endorsements"""
        c.execute('''SELECT movies.title, users.name FROM movies
                 INNER JOIN users ON movies.chooser_discord_id = users.discord_id
                 ''')
        movies_and_choosers = c.fetchall()
        c.execute('''SELECT movie_title FROM endorsements''')
        endorsements = c.fetchall()  # each movie will be listed once for each endorsement
        endorsements = [e['movie_title'].lower() for e in endorsements]
        movies_chooser_endorsements = []
        for row in movies_and_choosers:
            movie_endorsements = endorsements.count(row['title'].lower())
            movies_chooser_endorsements.append([row['title'], row['name'], movie_endorsements])
        movies_chooser_endorsements.sort(key=lambda x: x[2], reverse=True)
        message = "------ MOST ENDORSED MOVIES ------\n"
        for row in movies_chooser_endorsements[:n]:
            message += f"{row[0]} ({row[1]}): {row[2]}\n"
        return message

    def unendorsed(self, chooser_discord_id=None):
        c = self.conn.cursor()
        if chooser_discord_id:
            chooser_name = self.discord_id_to_name(chooser_discord_id)
            if not chooser_name:
                raise ValueError(f'User associated with discord if {chooser_discord_id} not found')
            message = f"------ UNENDORSED MOVIES FROM {chooser_name.upper()} ------\n"
            c.execute('''SELECT movies.title, users.name FROM movies 
                         INNER JOIN users ON movies.chooser_discord_id = users.discord_id
                         WHERE movies.watched = ? AND movies.chooser_discord_id = ?
                         AND movies.title NOT IN (SELECT DISTINCT movie_title FROM endorsements)''',
                      (0, chooser_discord_id))
            rows = c.fetchall()
            for row in rows:
                message += f"{row['title']}\n"
        else:
            message = "------ UNENDORSED MOVIES ------\n"
            c.execute('''SELECT movies.title, users.name FROM movies
                         INNER JOIN users ON movies.chooser_discord_id = users.discord_id
                         WHERE movies.watched = ? AND movies.title NOT IN
                         (SELECT DISTINCT movie_title FROM endorsements)''',
                      (0,))
            rows = c.fetchall()
            for row in rows:
                message += f"{row['title']} ({row['name']})\n"
        return message

    def ratings_for_choosers_movies(self, chooser_discord_id):
        chooser_name = self.discord_id_to_name(chooser_discord_id)
        if not chooser_name:
            raise ValueError(f'User associated with discord if {chooser_discord_id} not found')
        c = self.conn.cursor()
        c.execute('''SELECT movie_title, rating FROM ratings WHERE movie_title IN
                 (SELECT movies.title FROM movies 
                  INNER JOIN users ON movies.chooser_discord_id = users.discord_id
                  WHERE movies.chooser_discord_id = ? and watched = ?)''', (chooser_discord_id, 1))
        rows = c.fetchall()
        if not rows:
            raise ValueError(f'No watched movies were found for {chooser_name}.')
        rows = [dict(row) for row in rows]
        for row in rows:
            row['movie_title'] = row['movie_title'].lower()
        movies_and_ratings = {}
        all_ratings = []
        for row in rows:
            all_ratings.append(row['rating'])
            try:
                movies_and_ratings[row['movie_title']].append(row['rating'])
            except:
                movies_and_ratings[row['movie_title']] = [row['rating']]
        overall_average = sum(all_ratings)/len(all_ratings)
        overall_average = '{:02.1f}'.format(overall_average)
        message = f'------ SUBMISSIONS FROM {chooser_name.upper()} ({overall_average}) ------\n'
        for key in movies_and_ratings.keys():
            average = sum(movies_and_ratings[key])/len(movies_and_ratings[key])
            average = '{:02.1f}'.format(average)
            message += f'{key} - {average}\n'
        return message

    def ratings_from_reviewer(self, rater_discord_id):
        rater_name = self.discord_id_to_name(rater_discord_id)
        if not rater_name:
            raise ValueError(f'User associated with discord if {rater_discord_id} not found')
        c = self.conn.cursor()
        c.execute('''SELECT movie_title, rating FROM ratings WHERE rater_discord_id = ?''', (rater_discord_id,))
        rows = c.fetchall()
        if not rows:
            raise ValueError(f'No ratings given from {rater_name} were found.')
        all_ratings_from_rater = [row['rating'] for row in rows]
        overall_average = sum(all_ratings_from_rater)/len(all_ratings_from_rater)
        overall_average = '{:02.1f}'.format(overall_average)
        message = f"------ RATINGS FROM {rater_name.upper()} (avg: {overall_average})------\n"
        rows = sorted(rows, key = lambda row: row['rating'], reverse=True) 
        for row in rows:
            rating = '{:02.1f}'.format(row['rating'])
            message += f"{row['movie_title']} - {rating}\n"
        return message
        
    def missing_ratings_for_reviewer(self, rater_discord_id):
        rater_name = self.discord_id_to_name(rater_discord_id)
        if not rater_name:
            raise ValueError(f'User associated with discord if {rater_discord_id} not found')
        c = self.conn.cursor()
        c.execute('''SELECT title from movies WHERE watched = ? AND title NOT IN
                    (SELECT DISTINCT movie_title FROM ratings WHERE rater_discord_id = ?)''',
                  (1, rater_discord_id))
        unrated_movies = c.fetchall()
        unrated_movies = [u['title'] for u in unrated_movies]
        message = f"------ UNRATED MOVIES FROM {rater_name.upper()} ------\n"
        for movie in unrated_movies:
            message += f"{movie}\n"
        return message
        
    def standings(self):
        c = self.conn.cursor()
        c.execute('''SELECT movies.title, users.name FROM movies
                     INNER JOIN users ON movies.chooser_discord_id = users.discord_id
                     WHERE watched = ?''', (1,))
        movies_and_choosers = c.fetchall()
        choosers = [row['name'] for row in movies_and_choosers]  # 1 row per movie (choosers will be repeated)
        unique_choosers = set(choosers)
        
        choosers_moviecount_averagerating = []
        for chooser in unique_choosers:
            n_movies = choosers.count(chooser)
            c.execute('''SELECT ratings.rating FROM ratings
                     INNER JOIN movies ON ratings.movie_title = movies.title
                     INNER JOIN users ON movies.chooser_discord_id = users.discord_id
                     WHERE users.name = ?''', (chooser,))
            ratings_for_chooser = c.fetchall()
            if ratings_for_chooser:
                ratings_for_chooser = [r['rating'] for r in ratings_for_chooser]
                average_score_for_chooser_movies = sum(ratings_for_chooser)/len(ratings_for_chooser)
                choosers_moviecount_averagerating.append([chooser, n_movies, average_score_for_chooser_movies])
            
        choosers_moviecount_averagerating.sort(key=lambda x: float(x[2]), reverse=True)
        message = f"------ OVERALL STANDINGS ------\n"
        i = 1
        for chooser, n_movies, average in choosers_moviecount_averagerating:
            average = '{:02.1f}'.format(float(average))
            message += f"{i}. {chooser} ({n_movies}) - {average}\n"
            i += 1
        return message
        
    def top_ratings(self, n=10):    
        c = self.conn.cursor()
        c.execute('''SELECT movie_title, rating FROM ratings''')
        movies_and_ratings = c.fetchall()
        movies = [row['movie_title'].lower() for row in movies_and_ratings]
        unique_movies = set(movies)
        movie_chooser_rating = []
        for movie in unique_movies:
            c.execute('''SELECT users.name FROM users
                         INNER JOIN movies ON users.discord_id = movies.chooser_discord_id
                         WHERE movies.title = ?''', (movie,))
            chooser = c.fetchone()
            if not chooser:
                chooser = "???"
            else:
                chooser = chooser['name']
            ratings_for_movie = [row['rating'] for row in movies_and_ratings if row['movie_title'].lower() == movie]
            movie_average_rating = sum(ratings_for_movie)/len(ratings_for_movie)
            movie_chooser_rating.append([movie, chooser, movie_average_rating])

        movie_chooser_rating.sort(key=lambda x: float(x[2]), reverse=True)
        message = f"------ TOP RATED MOVIES ------\n"
        i = 1
        for movie, chooser, rating in movie_chooser_rating[:n]:
            average = '{:02.1f}'.format(rating)
            message += f"{i}. {movie} ({chooser}) - {average}\n"
            i += 1
        return message

    def pick_random_movie(self):
        c = self.conn.cursor()
        c.execute('''SELECT title FROM movies WHERE watched = ?''', (0,))
        movies = c.fetchall()
        movies = [m['title'] for m in movies]
        return random.choice(movies)
