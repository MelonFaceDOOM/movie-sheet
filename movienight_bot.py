import sqlite3
import random
from datetime import datetime
from matching import find_closest_match
from melon_discord import get_guild_user_info, user_to_id, id_to_user, id_from_mention


# TODO: separate sql stuff and add the pragma foreign_keys true thing


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
                         INNER JOIN users ON movies.user_id = users.id
                         WHERE ratings.guild_id = ? AND users.id = ? AND movies.watched = ?''',
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
            c.execute('''SELECT user_id, watched FROM movies WHERE guild_id = ? AND title = ?''',
                      (guild_id, best_match))
            movie = c.fetchone()
            username = await id_to_user(ctx, movie['user_id'])
            if not username:
                username = str(movie['user_id'])
            if movie['watched']:
                c.execute('''SELECT ratings.rating, ratings.user_id FROM ratings
                             INNER JOIN movies ON ratings.movie_id = movies.id
                             WHERE ratings.guild_id = ? AND movies.title = ?''',
                          (guild_id, best_match))
                ratings_and_ids = c.fetchall()
                ratings = [row['rating'] for row in ratings_and_ids]
                if not ratings:
                    average = float('nan')
                else:
                    average = sum(ratings)/len(ratings)
                    average = '{:02.1f}'.format(float(average))
                message = f"------ {best_match.upper()} ({username.upper()})------\nAverage Score: {average}\n"
                for row in ratings_and_ids:
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
        current_time = datetime.now()
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

    async def tag_movie(self, guild_id, movie_title, tag_text):
        existing_movie = await self.find_exact_movie(guild_id, movie_title)
        if not existing_movie:
            raise ValueError(f'The movie "{movie_title}" could not be found.')
        c = self.conn.cursor()
        c.execute('''SELECT * FROM tags WHERE guild_id = ? AND movie_id = ? and tag_text = ?''',
                  (guild_id, existing_movie['id'], tag_text))
        existing_tag = c.fetchone()
        if existing_tag:
            raise ValueError(f'The movie "{movie_title}" has already been tagged as "{tag_text}".')
        c.execute('''INSERT INTO tags (guild_id, movie_id, tag_text) values (?,?,?)''',
                  (guild_id, existing_movie['id'], tag_text))
        self.conn.commit()

    async def untag_movie(self, guild_id, movie_title, tag_text):
        existing_movie = await self.find_exact_movie(guild_id, movie_title)
        if not existing_movie:
            raise ValueError(f'The movie "{movie_title}" could not be found.')
        c = self.conn.cursor()
        c.execute('''SELECT * FROM tags WHERE guild_id = ? AND tag_text = ? AND movie_id IN
                     (SELECT id FROM movies WHERE guild_id = ? AND title = ?)''',
                  (guild_id, tag_text, guild_id, movie_title))
        existing_tag = c.fetchone()
        if not existing_tag:
            raise ValueError(f'The movie "{movie_title}" is not tagged with "{tag_text}".')
        c.execute('''DELETE FROM tags WHERE guild_id = ? AND tag_text = ? AND movie_id IN
                     (SELECT id FROM movies WHERE guild_id = ? AND title = ?)''',
                  (guild_id, tag_text, guild_id, movie_title))
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

    async def retrieve_suggestions(self, ctx, guild_id, chooser_user_id):
        chooser_name = await id_to_user(ctx, chooser_user_id)
        if not chooser_name:
            chooser_name = str(chooser_user_id)
        c = self.conn.cursor()
        c.execute('''SELECT title FROM movies WHERE guild_id = ? AND user_id = ? and watched = ?''',
                  (guild_id, chooser_user_id, 0))
        suggestions = c.fetchall()
        suggestions = [suggestion['title'] for suggestion in suggestions]
        if not suggestions:
            raise ValueError(f'No suggestions found for {chooser_name}')
        message = f"------ SUGGESTIONS FROM {chooser_name.upper()} ------\n"
        for suggestion in suggestions:
            message += suggestion + "\n"
        return message

    async def retrieve_endorsements(self, ctx, guild_id, endorser_user_id):
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
        c.execute('''SELECT movies.title, ratings.movie_id, ratings.rating FROM ratings
                     INNER JOIN movies ON ratings.movie_id == movies.id
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


        # c = self.conn.cursor()
        # c.execute('''SELECT movies.title, ratings.rating FROM movies
        #              INNER JOIN ratings ON movies.id = ratings.movie_id
        #              WHERE movies.guild_id = ? AND movies.watched = ?
        #              ORDER BY movies.date_watched''',
        #           (guild_id, 1))
        # movies_watched = c.fetchall()
        # message = '------ MOST RECENTLY WATCHED MOVIES ------\n'
        # for movie in movies_watched[:n]:
        #     rating = '{:02.1f}'.format(movie['rating'])
        #     message += (f'{movie["title"]} - {rating}\n')
        # return message

    async def ratings_for_choosers_movies(self, ctx, guild_id, chooser_user_id):
        chooser_name = await id_to_user(ctx, chooser_user_id)
        if not chooser_name:
            chooser_name = str(chooser_user_id)
        c = self.conn.cursor()
        c.execute('''SELECT movies.title, ratings.rating FROM ratings 
                     INNER JOIN movies ON ratings.movie_id = movies.id
                     WHERE movies.guild_id = ? AND movies.user_id = ? AND watched = ?''',
                  (guild_id, chooser_user_id, 1))
        rows = c.fetchall()
        if not rows:
            raise ValueError(f'No watched movies were found for {chooser_name}.')
        rows = [dict(row) for row in rows]
        for row in rows:
            row['title'] = row['title'].lower()
        movies_and_ratings = {}
        all_ratings = []
        for row in rows:
            all_ratings.append(row['rating'])
            try:
                movies_and_ratings[row['title']].append(row['rating'])
            except:
                movies_and_ratings[row['title']] = [row['rating']]
        overall_average = sum(all_ratings)/len(all_ratings)
        overall_average = '{:02.1f}'.format(overall_average)
        message = f'------ SUBMISSIONS FROM {chooser_name.upper()} ({overall_average}) ------\n'
        for key in movies_and_ratings.keys():
            average = sum(movies_and_ratings[key])/len(movies_and_ratings[key])
            average = '{:02.1f}'.format(average)
            message += f'{key} - {average}\n'
        return message

    async def ratings_from_reviewer(self, ctx, guild_id, rater_user_id):
        rater_name = await id_to_user(ctx, rater_user_id)
        if not rater_name:
            rater_name = str(rater_user_id)
        c = self.conn.cursor()
        c.execute('''SELECT movies.title, ratings.rating FROM ratings
                     INNER JOIN movies ON ratings.movie_id = movies.id
                     WHERE ratings.guild_id = ? AND ratings.user_id = ?''',
                  (guild_id, rater_user_id))
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
            message += f"{row['title']} - {rating}\n"
        return message
        
    async def missing_ratings_for_reviewer(self, ctx, guild_id, rater_user_id):
        rater_name = await id_to_user(ctx, rater_user_id)
        if not rater_name:
            rater_name = str(rater_user_id)
        c = self.conn.cursor()
        c.execute('''SELECT title from movies WHERE guild_id = ? AND watched = ? AND id NOT IN
                    (SELECT DISTINCT movie_id FROM ratings WHERE guild_id = ? AND user_id= ?)''',
                  (guild_id, 1, guild_id, rater_user_id))
        unrated_movies = c.fetchall()
        unrated_movies = [u['title'] for u in unrated_movies]
        message = f"------ UNRATED MOVIES FROM {rater_name.upper()} ------\n"
        for movie in unrated_movies:
            message += f"{movie}\n"
        return message

    async def standings(self, ctx, guild_id):
        c = self.conn.cursor()
        c.execute('''SELECT id FROM users WHERE guild_id = ?''', (guild_id, ))
        user_ids = c.fetchall()
        choosers_moviecount_averagerating = []
        for row in user_ids:
            user_id = row['id']
            chooser_name = await id_to_user(ctx, user_id)
            if not chooser_name:
                chooser_name = str(user_id)
            c.execute('''SELECT movies.title, ratings.rating FROM ratings 
                         INNER JOIN movies ON ratings.movie_id = movies.id
                         WHERE movies.guild_id = ? AND movies.user_id = ? AND watched = ?''',
                      (guild_id, user_id, 1))
            movies_ratings = c.fetchall()
            movies = [row['title'] for row in movies_ratings]  # movies repeated for each time rated
            unique_movies = set(movies)
            movie_count = len(unique_movies)
            ratings_received = [row['rating'] for row in movies_ratings]
            if ratings_received:
                average_rating = sum(ratings_received) / len(ratings_received)
            else:
                average_rating = 0
            choosers_moviecount_averagerating.append([chooser_name, movie_count, average_rating])

        choosers_moviecount_averagerating.sort(key=lambda x: float(x[2]), reverse=True)
        message = f"------ OVERALL STANDINGS ------\n"
        i = 1
        for chooser, n_movies, average in choosers_moviecount_averagerating:
            average = '{:02.1f}'.format(float(average))
            message += f"{i}. {chooser} ({n_movies}) - {average}\n"
            i += 1
        return message

    async def top_ratings(self, ctx, guild_id, top=True, n=10):
        """bottom ratings if top=False"""
        c = self.conn.cursor()
        c.execute('''SELECT movies.title, ratings.movie_id, ratings.rating FROM ratings
                     INNER JOIN movies ON ratings.movie_id == movies.id
                     WHERE ratings.guild_id = ? AND movies.guild_id = ?''',
                  (guild_id, guild_id))
        movies_ids_ratings = c.fetchall()
        movies_and_ids = [(row['title'], row['movie_id']) for row in movies_ids_ratings]
        unique_movie_and_ids = set(movies_and_ids)
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

        movie_chooser_rating.sort(key=lambda x: float(x[2]), reverse=top)
        message = f"------ {'TOP' if top else 'BOTTOM'} RATED MOVIES ------\n"
        i = 1
        for movie, chooser, rating in movie_chooser_rating[:n]:
            average = '{:02.1f}'.format(rating)
            message += f"{i}. {movie} ({chooser}) - {average}\n"
            i += 1
        return message

    async def pick_random_movie(self, guild_id):
        c = self.conn.cursor()
        c.execute('''SELECT title FROM movies WHERE guild_id = ? AND watched = ?''',
                  (guild_id, 0))
        movies = c.fetchall()
        movies = [m['title'] for m in movies]
        return random.choice(movies)
