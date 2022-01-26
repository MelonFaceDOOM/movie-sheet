import sqlite3
import random
import datetime
import statistics
import math
from matching import find_closest_match
from melon_discord import get_guild_user_info, user_to_id, id_to_user, id_from_mention


class movieNightBot:
    def __init__(self, db_file=None):
        if not db_file:
            db_file = 'movie_night_bot.db'
        self.conn = sqlite3.connect(db_file)
        self.conn.row_factory = sqlite3.Row

    async def find_exact_movie(self, guild_id, movie_title):
        """finds an exact movie (case insensitive), as opposed to the best match technique in find_all()"""
        c = self.conn.cursor()
        c.execute('''SELECT * FROM movies WHERE guild_id = ? AND title = ?''', (guild_id, movie_title))
        row = c.fetchone()
        if row:
            return row
        else:
            return None

    async def suggest_movie(self, guild_id, movie_title, user_id):
        existing_movie = await self.find_exact_movie(guild_id, movie_title)
        if existing_movie:
            if existing_movie['watched'] == 1:
                raise ValueError(f'The movie {movie_title} has already been watched.')
            elif existing_movie['watched'] == 0:
                raise ValueError(f'The movie {movie_title} has already been suggested.')
        c = self.conn.cursor()
        c.execute('''INSERT INTO movies (guild_id, title, user_id, watched) values (?,?,?,?)''',
                  (guild_id, movie_title, user_id, 0))
        self.conn.commit()

    async def remove_suggestion(self, guild_id, movie_title):
        existing_movie = await self.find_exact_movie(guild_id, movie_title)
        if not existing_movie:
            raise ValueError(f'The movie "{movie_title}" could not be found.')
        elif existing_movie['watched'] == 1:
            raise ValueError(f'The movie "{movie_title}" has already been watched, so it cannot be removed.')
        c = self.conn.cursor()
        c.execute('''DELETE FROM movies WHERE guild_id = ? AND title = ? AND watched = ?''', (guild_id, movie_title, 0))
        self.conn.commit()

    async def transfer_suggestion(self, guild_id, movie_title, recipient_user_id):
        existing_movie = await self.find_exact_movie(guild_id, movie_title)
        if not existing_movie:
            raise ValueError(f'The movie "{movie_title}" could not be found')
        # elif existing_movie['watched'] == 1:
        #     raise ValueError(f'The movie "{movie_title}" has already been watched, so it cannot be transferred')
        c = self.conn.cursor()
        c.execute('''UPDATE movies SET user_id = ? WHERE guild_id = ? AND title = ?''',
                  (recipient_user_id, guild_id, movie_title))
        self.conn.commit()
        
    async def find_all(self, ctx, guild_id, search_term):
        """requires ctx so it can lookup guild user names"""
        c = self.conn.cursor()
        if search_term.strip() == "":
            raise ValueError("search term cannot be blank")

        user_id = await id_from_mention(search_term)

        c.execute('''SELECT title FROM movies WHERE guild_id = ?''', (guild_id,))
        rows = c.fetchall()
        movies = [row['title'].lower() for row in rows]

        guild_user_info = await get_guild_user_info(ctx)
        usernames = [id_and_name[1].lower() for id_and_name in guild_user_info]

        full_search_list = movies + usernames
        best_match = find_closest_match(search_term, full_search_list)

        if best_match in usernames or user_id:
            if user_id:
                best_match = await id_to_user(ctx, user_id)
            else:
                user_id = await user_to_id(ctx, best_match)
            c.execute('''SELECT title FROM movies WHERE guild_id = ? AND user_id = ? AND watched = ?''',
                      (guild_id, user_id, 1))
            rows = c.fetchall()
            movies_watched = [row['title'] for row in rows]
            c.execute('''SELECT title FROM movies WHERE guild_id = ?  AND user_id = ? AND watched = ?''',
                      (guild_id, user_id, 0))
            rows = c.fetchall()
            suggestions = [row['title'] for row in rows]
            c.execute('''SELECT ratings.rating FROM ratings
                         INNER JOIN movies ON ratings.movie_id = movies.id
                         WHERE ratings.guild_id = ? AND movies.user_id = ? AND movies.watched = ?''',
                      (guild_id, user_id, 1))
            rows = c.fetchall()
            ratings_received = [row['rating'] for row in rows]
            c.execute('''SELECT rating FROM ratings WHERE guild_id = ? AND user_id = ?''',
                      (guild_id, user_id))
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

        if best_match in movies:
            c.execute('''SELECT id, user_id, watched, date_watched FROM movies WHERE guild_id = ? AND title = ?''',
                      (guild_id, best_match))
            movie = c.fetchone()
            username = await id_to_user(ctx, movie['user_id'])
            if not username:
                username = str(movie['user_id'])
            if movie['watched']:
                ratings = await self.get_ratings_for_movie_ids(guild_id=guild_id, movie_ids=[movie['id']])
                date_watched = movie['date_watched']
                if not ratings:
                    average = float('nan')
                else:
                    ratings_for_movie = [rating_row['rating'] for rating_row in
                                         ratings if rating_row['movie_id'] == movie['id']]
                    average = sum(ratings_for_movie) / len(ratings_for_movie)
                    if not date_watched:
                        date_watched = "????-??-??"
                message = f"------ {best_match.upper()} ({username.upper()}) ({average:.1f})------\n" \
                          f"Date Watched: {date_watched[:10]}\n"
                for row in ratings:
                    rating = '{:02.1f}'.format(float(row['rating']))
                    username = await id_to_user(ctx, row['user_id'])
                    if not username:
                        username = str(row['user_id'])
                    message += f"{username}: {rating}\n"
                return message
            else:
                message = f"------ {best_match.upper()} - {username.upper()} ------\nEndorsed by:\n"
                c.execute('''SELECT endorsements.user_id FROM endorsements
                             INNER JOIN movies ON endorsements.movie_id = movies.id
                             WHERE endorsements.guild_id = ? AND movies.title = ?''',
                          (guild_id, best_match))
                rows = c.fetchall()
                for row in rows:
                    endorser = await id_to_user(ctx, row['user_id'])
                    if not endorser:
                        endorser = str(row['user_id'])
                    message += f"{endorser}\n"
                tags = await self.find_tags(guild_id=guild_id, movie_title=best_match)
                if tags:
                    message += f"\ntags:{', '.join(tags)}"
                return message

        if not best_match:
            raise ValueError(f'"{search_term}" was not found.')

        raise ValueError(f'Could not find rating because "{search_term}" was not found.')
            
    async def is_endorsed(self, guild_id, movie_title, endorser_user_id):
        c = self.conn.cursor()
        c.execute('''SELECT endorsements.user_id FROM endorsements
                     INNER JOIN movies ON endorsements.movie_id = movies.id
                     WHERE endorsements.guild_id = ? AND movies.title = ?''',
                  (guild_id, movie_title))
        current_endorsers = c.fetchall()
        current_endorsers = [e['user_id'] for e in current_endorsers]
        if endorser_user_id in current_endorsers:
            return True
        else:
            return False
            
    async def endorse_suggestion(self, guild_id, movie_title, endorser_user_id):
        existing_movie = await self.find_exact_movie(guild_id, movie_title)
        if not existing_movie:
            raise ValueError(f'The movie "{movie_title}" could not be found.')
        elif existing_movie['watched'] == 1:
            raise ValueError(f'The movie "{movie_title}" has already been watched, so it cannot be endorsed.')
        elif existing_movie['user_id'] == endorser_user_id:
            raise ValueError(f'You cannot endorse your own movie.')
        elif await self.is_endorsed(guild_id, movie_title, endorser_user_id):
            raise ValueError(f'You have already endorsed {movie_title}.')
        c = self.conn.cursor()
        c.execute('''INSERT INTO endorsements (guild_id, user_id, movie_id) values (?,?,?)''',
                  (guild_id, endorser_user_id, existing_movie['id']))
        self.conn.commit()
        return None

    async def unendorse_suggestion(self, guild_id, movie_title, endorser_user_id):
        existing_movie = await self.find_exact_movie(guild_id, movie_title)
        if not existing_movie:
            raise ValueError(f'The movie "{movie_title}" could not be found.')
        if not await self.is_endorsed(guild_id, movie_title, endorser_user_id):
            raise ValueError(f'You have not yet endorsed {movie_title}.')
        c = self.conn.cursor()
        c.execute('''DELETE FROM endorsements WHERE guild_id = ? AND user_id = ? AND movie_id = ?''',
                  (guild_id, endorser_user_id, existing_movie['id']))
        self.conn.commit()
        return None

    async def rate_movie(self, guild_id, movie_title, rater_user_id, rating):
        if float(rating) < 1 or float(rating) > 10:
            raise ValueError('rating must be between 1 and 10')
        existing_movie = await self.find_exact_movie(guild_id, movie_title)
        if not existing_movie:
            raise ValueError(f'The movie "{movie_title}" could not be found.')
        c = self.conn.cursor()
        current_time = datetime.datetime.now()
        if existing_movie['date_watched']:
            c.execute('''UPDATE movies SET watched = ?
                         WHERE guild_id = ? AND title = ?''',
                      (1, guild_id, movie_title))
        else:
            c.execute('''UPDATE movies SET watched = ?, date_watched = ?
                         WHERE guild_id = ? AND title = ?''',
                      (1, current_time, guild_id, movie_title))
        c.execute('''SELECT rating FROM ratings where guild_id = ? AND movie_id = ? and user_id = ?''',
                  (guild_id, existing_movie['id'], rater_user_id))
        existing_rating = c.fetchone()
        if existing_rating:
            c.execute('''UPDATE ratings SET rating = ? WHERE guild_id = ? AND movie_id = ? and user_id = ?''',
                      (rating, guild_id, existing_movie['id'], rater_user_id))
        else:
            c.execute('''INSERT INTO ratings (guild_id, rating, movie_id, user_id) values (?,?,?,?)''',
                      (guild_id, rating, existing_movie['id'], rater_user_id))
        self.conn.commit()
        return None

    async def remove_rating(self, guild_id, movie_title, rater_user_id):
        existing_movie = await self.find_exact_movie(guild_id, movie_title)
        if not existing_movie:
            raise ValueError(f'The movie "{movie_title}" could not be found.')
        c = self.conn.cursor()
        c.execute('''SELECT ratings.rating FROM ratings
                     INNER JOIN movies ON ratings.movie_id = movies.id
                     WHERE ratings.guild_id = ? AND ratings.user_id = ? AND movies.title = ?''',
                  (guild_id, rater_user_id, movie_title))
        existing_rating = c.fetchone()
        if not existing_rating:
            raise ValueError(f'You have not yet rated "{movie_title}".')
        c.execute('''DELETE FROM ratings WHERE guild_id = ? AND user_id = ? AND 
                     movie_id IN (SELECT id FROM movies WHERE guild_id = ? AND title= ?)''',
                  (guild_id, rater_user_id, guild_id, movie_title))
        self.conn.commit()
        c.execute('''SELECT ratings.rating FROM ratings 
                     INNER JOIN movies ON ratings.movie_id = movies.id
                     WHERE ratings.guild_id = ? AND movies.title = ?''',
                  (guild_id, movie_title))
        rows = c.fetchall()
        ratings_count = len(rows)

        if ratings_count == 0:
            c.execute('''UPDATE movies SET watched = ?, date_watched = ?
                         WHERE guild_id = ? AND title = ?''',
                      (0, None, guild_id, movie_title))
            self.conn.commit()

    async def get_watched_movies(self, guild_id):
        c = self.conn.cursor()
        c.execute('''SELECT * FROM movies WHERE guild_id = ? AND watched = ?''',
                  (guild_id, 1))
        movies = c.fetchall()
        return movies

    async def set_date_watched(self, guild_id, movie_title, date_watched):
        existing_movie = await self.find_exact_movie(guild_id, movie_title)
        if not existing_movie:
            raise ValueError(f'The movie "{movie_title}" could not be found.')
        elif existing_movie['watched'] == 0:
            raise ValueError(f'The movie "{movie_title}" has not yet been watched.\n'
                             f'Watch it by rating it with !rate "{movie_title}" [rating])')
        else:
            date_watched = date_watched.strip() + " 00:00:01"
            date_watched = datetime.datetime.strptime(date_watched, '%Y-%m-%d %H:%M:%S')
            c = self.conn.cursor()
            c.execute('''UPDATE movies SET date_watched = ? 
                         WHERE guild_id = ? AND title = ?''',
                      (date_watched, guild_id, movie_title))
            self.conn.commit()

    async def get_ratings_for_movie_ids(self, guild_id, movie_ids):
        c = self.conn.cursor()
        query = "SELECT * FROM ratings WHERE guild_id = ? AND movie_id IN ({})".format(
            ','.join('?' * len(movie_ids)))
        params = [guild_id] + movie_ids
        c.execute(query, params)
        ratings = c.fetchall()
        return ratings

    async def get_median_votes(self, guild_id, ratings=None):
        """ratings is a list of list of dict objects which includes the movie_id"""
        if ratings is None:
            watched_movies = await self.get_watched_movies(guild_id=guild_id)
            movie_ids = [movie['id'] for movie in watched_movies]
            ratings = await self.get_ratings_for_movie_ids(guild_id=guild_id, movie_ids=movie_ids)
        rating_ids = [rating['movie_id'] for rating in ratings]  # ids will repeat for each vote
        unique_ids = set(rating_ids)
        vote_counts = []
        for unique_id in unique_ids:
            vote_counts.append(rating_ids.count(unique_id))
        median_votes = statistics.median(vote_counts)
        return median_votes

    async def review_movie(self, guild_id, movie_title, reviewer_user_id, review_text):
        existing_movie = await self.find_exact_movie(guild_id, movie_title)
        if not existing_movie:
            raise ValueError(f'The movie "{movie_title}" could not be found.')
        c = self.conn.cursor()
        c.execute('''SELECT * FROM reviews
                     INNER JOIN movies ON reviews.movie_id = movies.id
                     WHERE reviews.guild_id = ? AND reviews.user_id = ? AND movies.title = ?''',
                  (guild_id, reviewer_user_id, movie_title))
        movie = await self.find_exact_movie(guild_id, movie_title)
        existing_review = c.fetchone()
        if existing_review:
            c.execute('''DELETE FROM reviews WHERE guild_id = ? AND user_id = ? AND movie_id = ?''',
                      (guild_id, reviewer_user_id, movie['id']))
        c.execute('''INSERT INTO reviews (guild_id, movie_id, user_id, review_text) values (?,?,?,?)''',
                  (guild_id, movie['id'], reviewer_user_id, review_text))
        self.conn.commit()

    async def find_rating_for_movie_and_user_id(self, guild_id, movie_title, rater_user_id):
        c = self.conn.cursor()
        c.execute('''SELECT ratings.rating FROM ratings
                     INNER JOIN movies ON ratings.movie_id = movies.id
                     WHERE ratings.guild_id = ? AND ratings.user_id = ? AND movies.title = ?''',
                  (guild_id, rater_user_id, movie_title))
        rating = c.fetchone()
        if rating:
            return rating['rating']
        else:
            return None

    async def find_reviews(self, ctx, guild_id, movie_title=None, reviewer_user_id=None):
        c = self.conn.cursor()
        if reviewer_user_id:
            reviewer_name = await id_to_user(ctx, reviewer_user_id)
            if not reviewer_name:
                reviewer_name = str(reviewer_user_id)
            if movie_title:
                c.execute('''SELECT reviews.review_text FROM reviews
                             INNER JOIN movies ON reviews.movie_id = movies.id
                             WHERE movies.guild_id = ? AND movies.title = ? AND reviews.user_id = ?''',
                          (guild_id, movie_title, reviewer_user_id))
                review = c.fetchone()
                if not review:
                    raise ValueError(f'Could not find a review from {reviewer_name} for "{movie_title}".')
                rating = await self.find_rating_for_movie_and_user_id(guild_id, movie_title, reviewer_user_id)
                if rating:
                    rating = f'{str(rating)}/10'
                else:
                    rating = "N/A"
                message = f"------ {movie_title.upper()} reviewed by {reviewer_name.upper()} ------\n"
                message += f'{review["review_text"]}\n-{rating}'
            elif not movie_title:
                c.execute('''SELECT movies.title, reviews.review_text FROM reviews
                             INNER JOIN movies ON reviews.movie_id = movies.id 
                             WHERE reviews.user_id = ? AND reviews.guild_id = ?''',
                          (reviewer_user_id, guild_id))
                reviews = c.fetchall()
                message = f"------ REVIEWS FROM {reviewer_name.upper()} ------\n"
                for review in reviews:
                    rating = await self.find_rating_for_movie_and_user_id(guild_id, review['title'], reviewer_user_id)
                    if rating:
                        rating = f'{str(rating)}/10'
                    else:
                        rating = "N/A"
                    review_text = review['review_text']
                    if len(review_text) > 100:
                        review_text = review_text[:100] + "..."
                    message += f'{review["title"]} - {rating}:\n{review_text}\n\n'

        elif movie_title and not reviewer_user_id:
            message = f"------ REVIEWS FOR {movie_title.upper()} ------\n"
            c.execute('''SELECT reviews.review_text, reviews.user_id FROM reviews 
                         INNER JOIN movies ON reviews.movie_id = movies.id
                         WHERE movies.title = ? AND reviews.guild_id = ?''',
                      (movie_title, guild_id))
            reviews = c.fetchall()
            if not reviews:
                raise ValueError(f'Could not find any reviews for "{movie_title}".')
            for review in reviews:
                reviewer_user_id = review['user_id']
                reviewer_name = await id_to_user(ctx, review['user_id'])
                if not reviewer_name:
                    reviewer_name = str(review['user_id'])
                rating = await self.find_rating_for_movie_and_user_id(guild_id, movie_title, reviewer_user_id)
                if rating:
                    rating = f'{str(rating)}/10'
                else:
                    rating = "N/A"
                review_text = review['review_text']
                if len(review_text) > 100:
                    review_text = review_text[:100] + "..."
                message += f'{reviewer_name} ({rating}): {review_text}\n\n'
        return message

    async def tag_movie(self, guild_id, movie_title, tags):
        existing_movie = await self.find_exact_movie(guild_id, movie_title)
        if not existing_movie:
            raise ValueError(f'The movie "{movie_title}" could not be found.')
        c = self.conn.cursor()
        for tag in tags:
            c.execute('''SELECT * FROM tags WHERE guild_id = ? AND movie_id = ? and tag_text = ?''',
                      (guild_id, existing_movie['id'], tag))
            existing_tag = c.fetchone()
            if not existing_tag:
                c.execute('''INSERT INTO tags (guild_id, movie_id, tag_text) values (?,?,?)''',
                          (guild_id, existing_movie['id'], tag))
            self.conn.commit()

    async def untag_movie(self, guild_id, movie_title, tags):
        existing_movie = await self.find_exact_movie(guild_id, movie_title)
        if not existing_movie:
            raise ValueError(f'The movie "{movie_title}" could not be found.')
        c = self.conn.cursor()
        for tag in tags:
            c.execute('''SELECT * FROM tags WHERE guild_id = ? AND tag_text = ? AND movie_id IN
                         (SELECT id FROM movies WHERE guild_id = ? AND title = ?)''',
                      (guild_id, tag, guild_id, movie_title))
            existing_tag = c.fetchone()
            if existing_tag:
                c.execute('''DELETE FROM tags WHERE guild_id = ? AND tag_text = ? AND movie_id IN
                             (SELECT id FROM movies WHERE guild_id = ? AND title = ?)''',
                          (guild_id, tag, guild_id, movie_title))
        self.conn.commit()

    async def find_movies_with_tags(self, guild_id, tags, mutually_inclusive=True):
        c = self.conn.cursor()
        args = [guild_id]
        args.extend(tags)
        c.execute('''SELECT movies.title, tags.tag_text FROM tags
                     INNER JOIN movies on tags.movie_id = movies.id
                     WHERE tags.guild_id = ? AND tags.tag_text IN (%s)
                     ORDER BY movies.title'''
                  % ','.join('?' * len(tags)), args)
        rows = c.fetchall()
        if not rows:
            raise ValueError("No movies found with the provided tags.")

        # assumes all tags for the same movie will be grouped together
        movies_and_tags = {}
        previous_movie = ""
        for row in rows:
            if row['title'] == previous_movie:
                movies_and_tags[previous_movie].append(row['tag_text'])
            else:
                movies_and_tags[row['title']] = [row['tag_text']]
                previous_movie = row['title']
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

    async def find_tags(self, guild_id, movie_title):
        c = self.conn.cursor()
        c.execute('''SELECT tags.tag_text FROM tags
                             INNER JOIN movies ON tags.movie_id = movies.id
                             WHERE tags.guild_id = ? AND movies.title = ?''', (guild_id, movie_title))
        rows = c.fetchall()
        tags = [row['tag_text'] for row in rows]
        return tags

    async def find_movie_tags(self, guild_id, movie_title):
        existing_movie = await self.find_exact_movie(guild_id, movie_title)
        if not existing_movie:
            raise ValueError(f'The movie "{movie_title}" could not be found.')
        tags = await self.find_tags(guild_id=guild_id, movie_title=movie_title)
        message = f"------ TAGS FOR {movie_title.upper()} ------\n"
        for tag in tags:
            message += tag + "\n"
        return message

    async def retrieve_suggestions(self, ctx, guild_id, chooser_user_id, n=10):
        chooser_name = await id_to_user(ctx, chooser_user_id)
        if not chooser_name:
            chooser_name = str(chooser_user_id)
        c = self.conn.cursor()
        c.execute('''SELECT title FROM movies WHERE guild_id = ? AND user_id = ? and watched = ?''',
                  (guild_id, chooser_user_id, 0))
        suggestions = c.fetchall()
        suggestions = [suggestion['title'] for suggestion in suggestions]
        if n != 0:
            suggestions = suggestions[:n]
        if not suggestions:
            raise ValueError(f'No suggestions found for {chooser_name}')
        message = f"------ SUGGESTIONS FROM {chooser_name.upper()} ------\n"
        for suggestion in suggestions:
            message += suggestion + "\n"
        return message

    async def retrieve_endorsements(self, ctx, guild_id, endorser_user_id, n=10):
        endorser_name = await id_to_user(ctx, endorser_user_id)
        if not endorser_name:
            endorser_name = str(endorser_user_id)
        c = self.conn.cursor()
        c.execute('''SELECT movies.title FROM movies
                     INNER JOIN endorsements ON endorsements.movie_id = movies.id
                     WHERE endorsements.guild_id = ? AND endorsements.user_id = ? and watched = ?''',
                  (guild_id, endorser_user_id, 0))
        endorsements = c.fetchall()
        endorsements = [endorsement['title'] for endorsement in endorsements]
        if n != 0:
            endorsements = endorsements[:n]
        if not endorsements:
            raise ValueError(f'No endorsements found for {endorser_name}')
        message = f"------ ENDORSEMENTS FROM {endorser_name.upper()} ------\n"
        for endorsement in endorsements:
            message += endorsement + "\n"
        return message

    async def top_endorsed(self, ctx, guild_id, n=10):
        c = self.conn.cursor()
        """return movies with the most endorsements"""
        c.execute('''SELECT id, title, user_id FROM movies WHERE guild_id = ? AND watched = ?''',
                  (guild_id, 0))
        movies_and_choosers = c.fetchall()
        c.execute('''SELECT movie_id FROM endorsements WHERE guild_id = ?''', (guild_id,))
        endorsements = c.fetchall()  # each movie will be listed once for each endorsement
        endorsements = [e['movie_id'] for e in endorsements]
        movies_chooser_endorsements = []
        for row in movies_and_choosers:
            endorsement_count = endorsements.count(row['id'])
            chooser_name = await id_to_user(ctx, row['user_id'])
            if not chooser_name:
                chooser_name = str(row['user_id'])
            movies_chooser_endorsements.append([row['title'], chooser_name, endorsement_count])
        movies_chooser_endorsements.sort(key=lambda x: x[2], reverse=True)
        message = "------ MOST ENDORSED MOVIES ------\n"
        for row in movies_chooser_endorsements[:n]:
            message += f"{row[0]} ({row[1]}): {row[2]}\n"
        return message

    async def unendorsed(self, ctx, guild_id, chooser_user_id=None):
        c = self.conn.cursor()
        if chooser_user_id:
            chooser_name = await id_to_user(ctx, chooser_user_id)
            if not chooser_name:
                chooser_name = str(chooser_user_id)
            message = f"------ UNENDORSED MOVIES FROM {chooser_name.upper()} ------\n"
            c.execute('''SELECT title FROM movies WHERE guild_id = ? AND watched = ? AND user_id = ?
                         AND id NOT IN (SELECT DISTINCT movie_id FROM endorsements WHERE guild_id = ?)''',
                      (guild_id, 0, chooser_user_id, guild_id))
            rows = c.fetchall()
            for row in rows:
                message += f"{row['title']}\n"
        else:
            message = "------ UNENDORSED MOVIES ------\n"
            c.execute('''SELECT title FROM movies WHERE guild_id = ? AND watched = ?
                         AND id NOT IN (SELECT DISTINCT movie_id FROM endorsements WHERE guild_id = ?)''',
                      (guild_id, 0, guild_id))
            rows = c.fetchall()
            for row in rows:
                message += f"{row['title']} ({row['name']})\n"
        return message

    async def unique_preserve_order(self, items):
        seen = set()
        seen_add = seen.add
        return [x for x in items if not (x in seen or seen_add(x))]

    async def recently_watched_movies(self, ctx, guild_id, n=10):
        c = self.conn.cursor()
        c.execute('''SELECT movies.title, ratings.movie_id, movies.date_watched, ratings.rating
                     FROM ratings INNER JOIN movies ON ratings.movie_id == movies.id
                     WHERE ratings.guild_id = ? AND movies.guild_id = ? AND movies.watched = ?
                     ORDER BY datetime(movies.date_watched) DESC''',
                  (guild_id, guild_id, 1))
        movies_ids_ratings = c.fetchall()
        movies_and_ids = [(row['title'], row['movie_id']) for row in movies_ids_ratings]
        unique_movie_and_ids = await self.unique_preserve_order(movies_and_ids)
        unique_movie_and_ids = unique_movie_and_ids[:n]
        movie_chooser_rating = []
        for title, movie_id in unique_movie_and_ids:
            c.execute('''SELECT user_id FROM movies WHERE guild_id = ? AND id = ?''',
                      (guild_id, movie_id))
            user_id = c.fetchone()
            if not user_id:
                chooser_name = "???"
            else:
                chooser_name = await id_to_user(ctx, user_id['user_id'])
                if not chooser_name:
                    chooser_name = str(user_id['user_id'])
            ratings_for_movie = [row['rating'] for row in movies_ids_ratings if row['movie_id'] == movie_id]
            movie_average_rating = sum(ratings_for_movie)/len(ratings_for_movie)
            movie_chooser_rating.append([title, chooser_name, movie_average_rating])

        message = f"------ RECENTLY WATCHED MOVIES ------\n"
        i = 1
        for movie, chooser, rating in movie_chooser_rating[:n]:
            average = '{:02.1f}'.format(rating)
            message += f"{i}. {movie} ({chooser}) - {average}\n"
            i += 1
        return message

    async def ratings_for_choosers_movies(self, ctx, guild_id, chooser_user_id, n=10):
        chooser_name = await id_to_user(ctx, chooser_user_id)
        if not chooser_name:
            chooser_name = str(chooser_user_id)
        c = self.conn.cursor()
        c.execute('''SELECT id, title, date_watched FROM movies
                     WHERE guild_id = ? AND user_id = ? AND watched = ?
                     ORDER BY datetime(date_watched) DESC''',
                  (guild_id, chooser_user_id, 1))
        movies = c.fetchall()
        if not movies:
            raise ValueError(f'No watched movies were found for {chooser_name}.')
        movie_ids = [movie['id'] for movie in movies]
        ratings = await self.get_ratings_for_movie_ids(guild_id=guild_id, movie_ids=movie_ids)
        all_ratings = [rating['rating'] for rating in ratings]
        overall_average = sum(all_ratings)/len(all_ratings)
        median_votes = await self.get_median_votes(guild_id=guild_id)
        title = f'SUBMISSIONS FROM {chooser_name.upper()} - {overall_average:.1f} (AVG)'
        # n == 0 -> get full list
        table = [["Title", "Date Watched", "Rating"]]
        if n != 0:
            movies = movies[:n]
        for movie in movies:
            ratings_for_movie = [rating_row['rating'] for rating_row in
                                 ratings if rating_row['movie_id'] == movie['id']]
            average = sum(ratings_for_movie) / len(ratings_for_movie)
            if median_votes > 1:
                weighted_score = math.log(len(ratings_for_movie), median_votes) * average
            else:
                weighted_score = 0
            date_watched = movie['date_watched']
            if not date_watched:
                date_watched = "????-??-??"
            table.append([movie["title"], date_watched[:10], f'{weighted_score:.1f}', f'{average:.1f}'])
        return title, table

    async def ratings_from_rater(self, ctx, guild_id, rater_user_id, n=10):
        rater_name = await id_to_user(ctx, rater_user_id)
        if not rater_name:
            rater_name = str(rater_user_id)
        c = self.conn.cursor()
        c.execute('''SELECT movies.title, movies.date_watched, ratings.rating FROM ratings
                     INNER JOIN movies ON ratings.movie_id = movies.id
                     WHERE ratings.guild_id = ? AND ratings.user_id = ?''',
                  (guild_id, rater_user_id))
        rows = c.fetchall()
        if not rows:
            raise ValueError(f'No ratings given from {rater_name} were found.')
        all_ratings_from_rater = [row['rating'] for row in rows]
        overall_average = sum(all_ratings_from_rater)/len(all_ratings_from_rater)
        title = f"RATINGS FROM {rater_name.upper()} (avg: {overall_average:.1f})"
        rows = sorted(rows, key=lambda row: row['rating'], reverse=True)
        table = [["Title", "Date Watched", "Rating"]]
        if n != 0:
            rows = rows[:n]
        for row in rows:
            date_watched = row['date_watched']
            if not date_watched:
                date_watched = "????-??-??"
            table.append([row['title'], date_watched[:10], f"{row['rating']:.1f}"])
        return title, table
        
    async def missing_ratings_for_reviewer(self, ctx, guild_id, rater_user_id, n=10):
        rater_name = await id_to_user(ctx, rater_user_id)
        if not rater_name:
            rater_name = str(rater_user_id)
        c = self.conn.cursor()
        c.execute('''SELECT title from movies WHERE guild_id = ? AND watched = ? AND id NOT IN
                    (SELECT DISTINCT movie_id FROM ratings WHERE guild_id = ? AND user_id= ?)''',
                  (guild_id, 1, guild_id, rater_user_id))
        unrated_movies = c.fetchall()
        unrated_movies = [u['title'] for u in unrated_movies]
        if n != 0:
            unrated_movies = unrated_movies[:n]
        message = f"------ UNRATED MOVIES FROM {rater_name.upper()} ------\n"
        for movie in unrated_movies:
            message += f"{movie}\n"
        return message

    async def standings(self, ctx, guild_id):
        c = self.conn.cursor()
        c.execute('''SELECT movies.user_id, ratings.rating FROM ratings
                     INNER JOIN movies ON ratings.movie_id = movies.id
                     WHERE movies.guild_id = ? AND movies.watched = ?''',
                  (guild_id, 1))
        choosers_ratings = c.fetchall()
        choosers_ratings.sort(key=lambda x: str(x['user_id']))
        choosers_averagerating_moviecount = []
        ratings_for_current_chooser = []
        for cr in choosers_ratings:
            if len(ratings_for_current_chooser) == 0:
                current_chooser = cr['user_id']
                ratings_for_current_chooser = [cr['rating']]
            elif cr['user_id'] == current_chooser:
                ratings_for_current_chooser.append(cr['rating'])
            else:
                average_rating = sum(ratings_for_current_chooser) / len(ratings_for_current_chooser)
                choosers_averagerating_moviecount.append([current_chooser, average_rating, len(ratings_for_current_chooser)])
                current_chooser = cr['user_id']
                ratings_for_current_chooser = [cr['rating']]
        average_rating = sum(ratings_for_current_chooser) / len(ratings_for_current_chooser)
        choosers_averagerating_moviecount.append([current_chooser, average_rating, len(ratings_for_current_chooser)])
        choosers_averagerating_moviecount.sort(key=lambda x: float(x[1]), reverse=True)
        title = f"OVERALL STANDINGS"
        table = [["Chooser", "Submissions Watched", "AVG"]]
        for chooser, average_rating, movie_count in choosers_averagerating_moviecount:
            if movie_count > 0:
                chooser_name = await id_to_user(ctx, chooser)
                if not chooser_name:
                    chooser_name = "NAME NOT FOUND EEEEE"
                average = '{:02.1f}'.format(float(average_rating))
                table.append([chooser_name, str(movie_count), average])
        return title, table

    async def top_ratings(self, ctx, guild_id, top=True, n=10):
        """bottom ratings if top=False"""

        movies = await self.get_watched_movies(guild_id=guild_id)
        movie_ids = [movie['id'] for movie in movies]
        ratings = await self.get_ratings_for_movie_ids(guild_id=guild_id, movie_ids=movie_ids)

        # get chooser and average rating for each movie
        movie_chooser_rating = []
        for movie in movies:
            chooser_name = await id_to_user(ctx, movie['user_id'])
            if not chooser_name:
                chooser_name = str(movie['user_id'])
            ratings_for_movie = [rating_row['rating'] for rating_row in
                                 ratings if rating_row['movie_id'] == movie['id']]
            average = sum(ratings_for_movie)/len(ratings_for_movie)
            movie_chooser_rating.append([movie['title'], chooser_name, movie['date_watched'], average])

        movie_chooser_rating.sort(key=lambda x: float(x[3]), reverse=top)
        title = f"{'TOP' if top else 'BOTTOM'} RATED MOVIES"
        table = [["Title", "Chooser", "Date Watched", "Rating"]]
        for movie_title, chooser_name, date_watched, average in movie_chooser_rating[:n]:
            if not date_watched:
                date_watched = "????-??-??"
            table.append([movie_title, chooser_name.upper(), date_watched[:10], f"{average:.1f}"])
        return title, table

    async def top_attendance(self, ctx, guild_id,  n=10):
        """Movies ranked by attendance."""
        movies = await self.get_watched_movies(guild_id=guild_id)
        movie_ids = [movie['id'] for movie in movies]
        ratings = await self.get_ratings_for_movie_ids(guild_id=guild_id, movie_ids=movie_ids)
        # get chooser and average rating for each movie
        movie_chooser_rating_count = []
        for movie in movies:
            chooser_name = await id_to_user(ctx, movie['user_id'])
            if not chooser_name:
                chooser_name = str(movie['user_id'])
            ratings_for_movie = [rating_row['rating'] for rating_row in
                                 ratings if rating_row['movie_id'] == movie['id']]
            count = len(ratings_for_movie)
            movie_chooser_rating_count.append([movie['title'], chooser_name, movie['date_watched'], count])

        movie_chooser_rating_count.sort(key=lambda x: float(x[3]), reverse=True)
        title = f"BIGGEST MOVIE NIGHTS"
        table = [["Title", "Chooser", "Date Watched", "Attendees"]]
        for title, chooser_name, date_watched, count in movie_chooser_rating_count[:n]:
            if not date_watched:
                date_watched = "????-??-??"
            table.append([title, chooser_name.upper(), date_watched[:10], str(count)])
        return title, table

    async def pick_random_movie(self, guild_id):
        c = self.conn.cursor()
        c.execute('''SELECT title FROM movies WHERE guild_id = ? AND watched = ?''',
                  (guild_id, 0))
        movies = c.fetchall()
        movies = [m['title'] for m in movies]
        return random.choice(movies)

    async def vote_gamespot_self_destruct(self, ctx, guild_id, user_id, votes_required):
        current_time = datetime.datetime.utcnow()
        time_range = datetime.timedelta(minutes=5)
        c = self.conn.cursor()
        c.execute('''SELECT * FROM gamespot_self_destruct_votes
                     WHERE guild_id = ? AND vote_group_id=(SELECT MAX(vote_group_id) FROM gamespot_self_destruct_votes)
                     ORDER BY datetime(date) DESC''',
                  (guild_id,))
        votes = c.fetchall()
        if not votes:
            vote_group_id = 1
            c.execute('''INSERT INTO gamespot_self_destruct_votes (guild_id, user_id, vote_group_id) values (?,?,?)''',
                      (guild_id, user_id, vote_group_id))
            self.conn.commit()
            message = "You have voted for self-destruction! Currently at 1 vote."
        else:
            vote_group_start_time = votes[-1]['date']
            vote_group_start_time = datetime.datetime.strptime(vote_group_start_time, '%Y-%m-%d %H:%M:%S')
            if current_time - vote_group_start_time > time_range:
                vote_group_id = votes[0]['vote_group_id'] + 1
                c.execute('''INSERT INTO gamespot_self_destruct_votes (guild_id, user_id, vote_group_id) values (?,?,?)''',
                          (guild_id, user_id, vote_group_id))
                self.conn.commit()
                message = f"Apologies, your previous self-destruction request only got {len(votes)} votes. A new request has been lodged with 1 vote."
            else:
                voter_ids = [vote['user_id'] for vote in votes]
                if user_id in voter_ids:
                    message = "You have already voted in favor of self-destruction."
                else:
                    vote_group_id = votes[0]['vote_group_id']
                    c.execute('''INSERT INTO gamespot_self_destruct_votes (guild_id, user_id, vote_group_id) values (?,?,?)''',
                              (guild_id, user_id, vote_group_id))
                    self.conn.commit()
                    total_votes = len(votes) + 1
                    if total_votes >= votes_required:
                        message = f"Say hello, wave goodbye."
                    else:
                        message = f"You have voted for self-destruction! There are {total_votes} votes."
        return message

    async def self_destructed(self, guild_id, votes_required):
        c = self.conn.cursor()
        c.execute('''SELECT * FROM gamespot_self_destruct_votes
                     WHERE guild_id = ? AND vote_group_id=(SELECT MAX(vote_group_id) FROM gamespot_self_destruct_votes)
                             ''',
                  (guild_id,))
        votes = c.fetchall()
        if len(votes) >= votes_required:
            return True
        else:
            return False

    async def seen(self, guild_id):
        c = self.conn.cursor()
        c.execute('''SELECT COUNT(*) FROM movies WHERE guild_id = ? AND watched = ?''', (guild_id, 1))
        movie_count = c.fetchone()['COUNT(*)']
        message = f"{movie_count} movies have been seen!"
        return message