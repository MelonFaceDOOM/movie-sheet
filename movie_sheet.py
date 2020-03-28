import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import APIError
import random
from matching import find_closest_match


HEADER_ROWS_FUTURE = 1
INFO_COLUMNS_FUTURE = 2
MOVIE_COL_FUTURE = 1
CHOOSER_COL_FUTURE = 2
HEADER_ROWS_RATINGS = 1
INFO_COLUMNS_RATINGS = 2
MOVIE_COL_RATINGS = 1
CHOOSER_COL_RATINGS = 2
ID_COL_USERS = 1
NICK_COL_USERS = 2
HEADER_ROWS_USERS = 1


##################################################
## GOOGLE SHEET AUTHORIZATION
##################################################

def authorize():
    global ws_future_movies
    global ws_ratings
    global ws_users
    
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']

    credentials = ServiceAccountCredentials.from_json_keyfile_name('sheetapi-269619-39d07591cb19.json', scope)
    gs = gspread.authorize(credentials)
    gsheet = gs.open("movienight")
    ws_future_movies = gsheet.worksheet("future movie")
    ws_ratings = gsheet.worksheet("ratings")
    ws_users = gsheet.worksheet("users")
    
authorize()
    
# wraps all functions that might be directly called by discord bot
def reup_auth(func):
    def inner(*args, **kwargs):
        try:
            returned_value = func(*args, **kwargs)
        except APIError as e:
            if e.args[0]['status']=='UNAUTHENTICATED':
                authorize()
                returned_value = func(*args, **kwargs)
            else:
                raise e
        return returned_value    
    return inner


##################################################
## CONVENIENCE FUNCTIONS
##################################################

def add_movie(sheet, movie, chooser):
    if find_exact_movie(sheet, movie):
        raise ValueError("movie already exists")
    row = [movie, chooser]
    index = len(sheet.get_all_values()) + 1
    sheet.insert_row(row, index)
    return index

def delete_movie(sheet, movie):
    index = find_exact_movie(sheet, movie)
    if not index:
        raise ValueError(f'Could not delete "{movie}" because it could not be found.')
    sheet.delete_row(index)
    return None
    
def find_exact_movie(sheet, movie):
    movies = sheet.col_values(MOVIE_COL_FUTURE)[HEADER_ROWS_FUTURE:]
    movies = [movie.lower().strip() for movie in movies]
    movie = movie.lower().strip()
    try:
        index = movies.index(movie) + HEADER_ROWS_FUTURE + 1
    except ValueError:
        return None
    return index
    
def find_movie(sheet, movie):
    movies = sheet.col_values(MOVIE_COL_FUTURE)[HEADER_ROWS_FUTURE:]
    movies = [movie.lower() for movie in movies]
    best_match = find_closest_match(movie, movies)
    try:
        index = movies.index(best_match.lower()) + HEADER_ROWS_FUTURE + 1
    except ValueError:
        return None
    return index
   
def find_reviewer(reviewer):
    reviewers = ws_ratings.row_values(HEADER_ROWS_RATINGS)[INFO_COLUMNS_RATINGS:]
    reviewers = [reviewer.lower() for reviewer in reviewers]
    try:
        col = reviewers.index(reviewer.lower()) + INFO_COLUMNS_RATINGS + 1
    except ValueError:
        return None
    return col

def add_reviewer(reviewer):
    if find_reviewer(reviewer):
        raise ValueError("reviewer already exists")
    col = len(ws_ratings.row_values(HEADER_ROWS_RATINGS)) + 1
    ws_ratings.update_cell(HEADER_ROWS_RATINGS, col, reviewer)
    return col 
    
def find_endorsers(movie):
    index = find_exact_movie(ws_future_movies, movie)
    if not index:
        raise ValueError(f'Cannot find endorsers because "{movie}" could not be found.')
    movie_row = ws_future_movies.row_values(index)
    current_endorsers = [e for e in movie_row[INFO_COLUMNS_FUTURE:] if e]
    return current_endorsers
 
def find_chooser_rows(chooser):
    all_ratings = ws_ratings.get_all_values()
    chooser_rows = [r for r in all_ratings if r[CHOOSER_COL_RATINGS-1].lower() == chooser.lower()]
    return chooser_rows
    
def average_ignore_blank(str_list):
    """Returns the average of a list of ints, floats, and strings that can be converted. Blanks and letters are ignored."""
    count = 0
    total = 0
    for i in str_list:
        if i != "":
            try:
                total += float(i)
            except ValueError:
                continue
            count += 1
    if count == 0:
        return float('nan')
    return total/count  
    
##################################################
## FUNCTIONS MEANT TO BE CALLED BY DISCORD BOT
##################################################    
@reup_auth
def register(id, nick):
    if len(nick) < 2:
        raise ValueError('nick must be at least 2 character')
    nicks = ws_users.col_values(NICK_COL_USERS)[HEADER_ROWS_USERS:]
    nicks = [nick.lower() for nick in nicks]
    if nick.lower() in nicks:
        raise ValueError(f'name {nick} already taken')
    
    ids = ws_users.col_values(ID_COL_USERS)[HEADER_ROWS_USERS:]
    try:
        index = ids.index(id) + HEADER_ROWS_USERS + 1
        ws_users.update_cell(index, NICK_COL_USERS, nick)
    except ValueError:
        index = len(ws_users.get_all_values()) + 1
        row = [id, nick]
        ws_users.insert_row(row, index)
    return None
    
@reup_auth   
def get_nick(id):
    ids = ws_users.col_values(ID_COL_USERS)[HEADER_ROWS_USERS:]
    try:
        index = ids.index(id) + HEADER_ROWS_USERS + 1
    except:
        raise ValueError('Your discord id was not found. try using !register <nick>')
    
    nick = ws_users.row_values(index)[NICK_COL_USERS-1]
    return nick
    
@reup_auth
def add_future_movie(movie, chooser):
    if find_exact_movie(ws_ratings, movie):
        raise ValueError(f"Cannot suggest {movie} becuase it has already been watched.")
    index = add_movie(ws_future_movies, movie, chooser)
    return None

@reup_auth
def remove_future_movie(movie):
    delete_movie(ws_future_movies, movie)
    return None
    
@reup_auth
def transfer_movie(movie, new_chooser):
    index = find_exact_movie(ws_future_movies, movie)
    if index:
        ws_future_movies.update_cell(index, CHOOSER_COL_FUTURE, new_chooser)
        return None
    index = find_exact_movie(ws_ratings, movie)
    if index:
        ws_ratings.update_cell(index, CHOOSER_COL_RATINGS, new_chooser)
        return None
    raise ValueError(f'Could not transfer choosership because "{movie}" was not found.')
    
@reup_auth
def find_all_movies(movie):
    future_movies = ws_future_movies.col_values(MOVIE_COL_FUTURE)[HEADER_ROWS_FUTURE:]
    future_movies = [movie.lower() for movie in future_movies]
    ratings_movies = ws_ratings.col_values(MOVIE_COL_RATINGS)[HEADER_ROWS_RATINGS:]
    ratings_movies = [movie.lower() for movie in ratings_movies]
    best_match = find_closest_match(movie, future_movies+ratings_movies)
    
    if not best_match:
        raise ValueError(f'"{movie}" was not found.')
        
    if best_match in future_movies:
        index = future_movies.index(best_match.lower()) + HEADER_ROWS_FUTURE + 1
        chooser = ws_future_movies.row_values(index)[CHOOSER_COL_FUTURE-1]
        message = f"------ {best_match.upper()} - {chooser.upper()} ------\nEndorsed by:\n"
        endorsers = find_endorsers(best_match)
        for endorser in endorsers:
            message += f"{endorser}\n"
        return message

    if best_match in ratings_movies:
        index = ratings_movies.index(best_match.lower()) + HEADER_ROWS_RATINGS + 1
        movie_row = ws_ratings.row_values(index)
        chooser = movie_row[CHOOSER_COL_RATINGS-1]
        scores = movie_row[INFO_COLUMNS_RATINGS:]
        reviewers = ws_ratings.row_values(HEADER_ROWS_RATINGS)[INFO_COLUMNS_RATINGS:]
        average = average_ignore_blank(scores)
        average = '{:02.1f}'.format(float(average))
        message = f"------ {best_match.upper()} ({chooser.upper()})------\nAverage Score: {average}\n"
        for i, score in enumerate(scores):
            if score:
                score = '{:02.1f}'.format(float(score))
                message+=(f"{reviewers[i]}: {score}\n")
        return message

    raise ValueError(f'Could not find rating because "{movie}" was not found.')

@reup_auth
def endorse_movie(movie, endorser):
    index = find_exact_movie(ws_future_movies, movie)
    if not index:
        raise ValueError(f'Cannot endorse because "{movie}" could not be found.')
    movie_row = ws_future_movies.row_values(index)
    chooser = movie_row[CHOOSER_COL_FUTURE-1]
    if endorser == chooser:
        raise ValueError(f'{endorser} cannot endorse "{movie}" because it is their movie.')
    current_endorsers = movie_row[INFO_COLUMNS_FUTURE:]
    if endorser not in current_endorsers:
        ws_future_movies.update_cell(index, len(movie_row)+1, endorser)
    return None
        
@reup_auth
def unendorse_movie(movie, endorser):
    index = find_exact_movie(ws_future_movies, movie)
    if not index:
        raise ValueError(f'Cannot unendorse because "{movie}" could not be found.')
        
    movie_row = ws_future_movies.row_values(index)
    try:
        movie_row.remove(endorser)
    except ValueError:
        return f'{endorser} cannot unendorse "{movie}" because {endorser} has not endorsed {movie}.'
    
    delete_movie(ws_future_movies, movie)
    ws_future_movies.insert_row(movie_row, index)
    return f"{endorser} has unendorsed {movie}!"

@reup_auth
def rate_movie(movie, reviewer, rating):
    if rating == "":
        pass
    elif float(rating) <1 or float(rating) >10:
        raise ValueError('rating must be between 1 and 10')
    col = find_reviewer(reviewer)
    if not col:
        col = add_reviewer(reviewer)
    ratings_index = find_exact_movie(ws_ratings, movie)
    if not ratings_index:
        ratings_index = watch_movie(movie)
    ws_ratings.update_cell(ratings_index, col, rating)
    return None      

@reup_auth
def watch_movie(movie):
    if find_exact_movie(ws_ratings, movie):
        raise ValueError(f'{movie} has already been moved to the ratings sheet.')
    index = find_exact_movie(ws_future_movies, movie)
    if not index:
        raise ValueError(f'{movie} is not on the future movie sheet. You must add the movie before you can watch it')
    chooser = ws_future_movies.row_values(index)[CHOOSER_COL_FUTURE-1]
    ratings_index = add_movie(ws_ratings, movie, chooser)
    ws_ratings.update_cell(ratings_index, MOVIE_COL_RATINGS, movie)
    ws_ratings.update_cell(ratings_index, CHOOSER_COL_RATINGS, chooser)
    delete_movie(ws_future_movies, movie)
    return ratings_index

@reup_auth
def unwatch_movie(movie):
    index = find_exact_movie(ws_ratings, movie)
    if not index:
        raise ValueError(f'"{movie}" cannot be unwatched because it could not be found in the ratings sheet.')        
    delete_movie(ws_ratings, movie)
    return None

@reup_auth
def chooser_suggestions(chooser):
    future_movies = ws_future_movies.get_all_values()
    movies = [r[MOVIE_COL_FUTURE-1] for r in future_movies if r[CHOOSER_COL_FUTURE-1].lower() == chooser.lower()]
    if not movies:
        raise ValueError(f'No suggestions found for {chooser}')
    message = f"------ SUGGESTSIONS FROM {chooser.upper()}------\n"
    for m in movies:
        message += m + "\n"
    return message

@reup_auth
def recent_suggestions(n):
    future_movies = ws_future_movies.get_all_values()
    start = len(future_movies)-n
    if start < 0:
        start = 0
    recent_movies = future_movies[start:]
    recent_movies.reverse()
    message = f"------ {n} RECENT SUGGESTIONS ------\n"
    for rm in recent_movies:
        message += f"{rm[MOVIE_COL_FUTURE-1]}, ({rm[CHOOSER_COL_FUTURE-1]})\n"
    return message

@reup_auth
def top_endorsed(n):
    """return movies with the most endorsements"""
    endorsements = ws_future_movies.get_all_values()[HEADER_ROWS_FUTURE:] # skip header row
    endorsements = [[cell for cell in row if cell] for row in endorsements] # remove all blanks
    endorsements.sort(key=len, reverse=True)
    message = "------ MOST ENDORSED MOVIES ------\n" 
    for e in endorsements[:n]:
        message += f"{e[MOVIE_COL_FUTURE-1]} ({e[CHOOSER_COL_FUTURE-1]}): {len(e[INFO_COLUMNS_FUTURE:])}\n" 
    return message
    
@reup_auth
def unendorsed():
    """return movies with no endorsements"""
    endorsements = ws_future_movies.get_all_values()[HEADER_ROWS_FUTURE:] # skip header row
    endorsements = [[cell for cell in row if cell] for row in endorsements] # remove all blanks
    endorsements = [row for row in endorsements if len(row)<=(INFO_COLUMNS_FUTURE)]
    message = "------ UNENDORSED MOVIES ------\n" 
    for e in endorsements:
        message += f"{e[MOVIE_COL_FUTURE-1]} ({e[CHOOSER_COL_FUTURE-1]})\n" 
    return message
 
@reup_auth
def average_reviewer_rating(reviewer):
    col = find_reviewer(reviewer)
    if not col:
        raise ValueError(f'No ratings from {reviewer} were found.')
    scores = ws_ratings.col_values(col)[HEADER_ROWS_RATINGS:]
    average = average_ignore_blank(scores)
    average = '{:02.1f}'.format(float(average))
    message = f"{reviewer} gives an average score of {average}."
    return message

@reup_auth
def ratings_from_chooser(chooser):
    chooser_rows = find_chooser_rows(chooser)
    if not chooser_rows:
        raise ValueError(f'No watched movies were found for the chooser, {chooser}.')
        
    average_scores = [[r[MOVIE_COL_RATINGS-1], average_ignore_blank(r[INFO_COLUMNS_RATINGS:])] for r in chooser_rows]
    average_scores.sort(key=lambda x: float(x[1]), reverse=True)
    overall_average = average_ignore_blank([score[1] for score in average_scores])
    overall_average = '{:02.1f}'.format(float(overall_average))
    message = f'------ SUBMISSIONS FROM {chooser.upper()} ({overall_average}) ------\n'
    for score in average_scores:
        average = '{:02.1f}'.format(float(score[1]))
        message += f'{score[0]} - {average}\n'
    return message

@reup_auth
def ratings_from_reviewer(reviewer):
    col = find_reviewer(reviewer)
    if not col:
        raise ValueError(f'No ratings from {reviewer} were found.')
    all_ratings = ws_ratings.get_all_values()[HEADER_ROWS_RATINGS:]
    reviewer_ratings = [[r[MOVIE_COL_RATINGS-1], float(r[col-1])] for r in all_ratings if r[col-1]]
    reviewer_ratings.sort(key=lambda x: x[1], reverse=True)
    average = average_ignore_blank([r[1] for r in reviewer_ratings])
    average = '{:02.1f}'.format(float(average))
    message = f"------ RATINGS FROM {reviewer.upper()} (avg: {average})------\n"
    for r in reviewer_ratings:
        score = '{:02.1f}'.format(r[1])
        message += f"{r[0]} - {score}\n"
    return message
    
@reup_auth
def missing_ratings_for_reviewer(reviewer):
    col = find_reviewer(reviewer)
    if not col:
        raise ValueError(f'No ratings from {reviewer} were found.')
    all_ratings = ws_ratings.get_all_values()[HEADER_ROWS_RATINGS:]
    reviewer_ratings = [r[MOVIE_COL_RATINGS-1] for r in all_ratings if not r[col-1]]
    message = f"------ UNRATED MOVIES FOR {reviewer.upper()}------\n"
    for r in reviewer_ratings:
        message += f"{r}\n"
    return message
    
@reup_auth
def standings():
    nicks = ws_users.col_values(NICK_COL_USERS)[HEADER_ROWS_USERS:]
    nicks = [nick.lower() for nick in nicks]
    chooser_list = ws_ratings.col_values(CHOOSER_COL_RATINGS)[HEADER_ROWS_USERS:]
    chooser_list = [c.lower() for c in chooser_list]
    standings = []
    for nick in nicks:
        n = chooser_list.count(nick)
        chooser_rows = find_chooser_rows(nick)
        average = average_ignore_blank([average_ignore_blank(r[INFO_COLUMNS_FUTURE:]) for r in chooser_rows])
        if average == average: # ignore nan
            standings.append([nick, n, average])
    standings.sort(key=lambda x: float(x[2]), reverse=True)
    message = f"------ OVERALL STANDINGS ------\n"
    i = 1
    for s in standings:
        average = '{:02.1f}'.format(float(s[2]))
        message += f"{i}. {s[0]} ({s[1]}) - {average}\n"
        i += 1
    return message
    
@reup_auth
def top_ratings(n):
    all_ratings = ws_ratings.get_all_values()[HEADER_ROWS_RATINGS:]
    average_ratings = []
    for movie_row in all_ratings:
        scores = movie_row[INFO_COLUMNS_FUTURE:]
        average = average_ignore_blank(scores)
        average_ratings.append([movie_row[0], movie_row[1], average])
    average_ratings.sort(key=lambda x: float(x[2]), reverse=True)
    average_ratings = average_ratings[:n]
    message = f"------ TOP RATED MOVIES ------\n"
    i = 1
    for a in average_ratings:
        average = '{:02.1f}'.format(float(a[2]))
        message += f"{i}. {a[0]} ({a[1]}) - {average}\n"
        i += 1
    return message

@reup_auth
def pick_random_movie():
    movies = ws_future_movies.col_values(MOVIE_COL_FUTURE)[HEADER_ROWS_FUTURE:]
    return random.choice(movies)