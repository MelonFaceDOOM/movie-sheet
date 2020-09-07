import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import APIError
import random
from matching import find_closest_match
import string


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
STATIC_SHEETS = ['future_movies', 'ratings', 'users']

##################################################
## GOOGLE SHEET AUTHORIZATION
##################################################

def authorize():
    global ws_future_movies
    global ws_ratings
    global ws_users
    global gsheet
    
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
    if movie.strip() == "":
        raise ValueError("movie name cannot be blank")
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
    if col > ws_ratings.col_count:
        ws_ratings.add_cols(col - ws_ratings.col_count)
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
        raise ValueError(f"Cannot suggest {movie} because it has already been watched.")
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
def find_all(search_term):
    if search_term.strip() == "":
        raise ValueError("search term cannot be blank")
    future_movies = ws_future_movies.col_values(MOVIE_COL_FUTURE)[HEADER_ROWS_FUTURE:]
    future_movies = [movie.lower() for movie in future_movies]
    ratings_movies = ws_ratings.col_values(MOVIE_COL_RATINGS)[HEADER_ROWS_RATINGS:]
    ratings_movies = [movie.lower() for movie in ratings_movies]
    usernames = ws_users.col_values(NICK_COL_USERS)[HEADER_ROWS_USERS:]
    usernames = [username.lower() for username in usernames]
    
    full_search_list = future_movies + ratings_movies + usernames
    best_match = find_closest_match(search_term, full_search_list)
    
    if not best_match:
        raise ValueError(f'"{search_term}" was not found.')
        
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
        
    if best_match in usernames:
        message = f'------ {best_match.upper()} ------\n'
        chooser_rows = find_chooser_rows(best_match)
        if len(chooser_rows) == 0:
            message += f"None of {best_match.upper()}'s suggestions have been watched yet.\n"
        else:
            message += f"{len(chooser_rows)} of {best_match.upper()}'s suggestions {'have' if len(chooser_rows)>1 else 'has'} been watched so far.\n"
            average_score = average_ignore_blank([average_ignore_blank(r[INFO_COLUMNS_RATINGS:]) for r in chooser_rows])
            average_score = '{:02.1f}'.format(float(average_score))
            message += f'{best_match.upper()} receives an average score of {average_score}.\n'
            
        col = find_reviewer(best_match)
        if not col:
            message += f'{best_match.upper()} has not rated any movies.\n'
        else:
            scores = ws_ratings.col_values(col)[HEADER_ROWS_RATINGS:]
            average = average_ignore_blank(scores)
            average = '{:02.1f}'.format(float(average))
            n_scores = len([score for score in scores if score != ''])
            message += f'{best_match.upper()} has given {n_scores} rating{"s" if n_scores>1 else ""}, with an average of {average}.\n'
            
        future_movies = ws_future_movies.get_all_values()
        suggestions = [r[MOVIE_COL_FUTURE-1] for r in future_movies if r[CHOOSER_COL_FUTURE-1].lower() == best_match]
        if not suggestions:
            message += f'{best_match.upper()} does not currently have any movie suggestions.\n'
        else:
            message += f'{best_match.upper()} currently has {len(suggestions)} movie suggestion{"s" if len(suggestions)>1 else ""}.\n\n'
        
        message += f'find more info with !chooser {best_match}, !ratings {best_match}, or !suggestions {best_match}.'
        return message

    raise ValueError(f'Could not find rating because "{search_term}" was not found.')

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
        if len(movie_row)+1 > ws_future_movies.col_count:
            ws_future_movies.add_cols(1)
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
    message = f"------ SUGGESTIONS FROM {chooser.upper()} ------\n"
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
    if n > len(endorsements):
        n = len(endorsements)
    if n < 0:
        n = 0
    endorsements = endorsements[:n]
    message = "------ MOST ENDORSED MOVIES ------\n"
    for e in endorsements:
        message += f"{e[MOVIE_COL_FUTURE-1]} ({e[CHOOSER_COL_FUTURE-1]}): {len(e[INFO_COLUMNS_FUTURE:])}\n" 
    return message
    
@reup_auth
def unendorsed(chooser=None):
    """return movies with no endorsements"""
    endorsements = ws_future_movies.get_all_values()[HEADER_ROWS_FUTURE:] # skip header row
    endorsements = [[cell for cell in row if cell] for row in endorsements] # remove all blanks
    endorsements = [row for row in endorsements if len(row)<=(INFO_COLUMNS_FUTURE)]
    if chooser:
        endorsements = [row for row in endorsements if row[CHOOSER_COL_FUTURE-1].lower()==chooser.lower()]
        message = f"------ UNENDORSED MOVIES FROM {chooser.upper()} ------\n" 
        for e in endorsements:
            message += f"{e[MOVIE_COL_FUTURE-1]}\n" 

    else:
        message = "------ UNENDORSED MOVIES ------\n" 
        for e in endorsements:
            message += f"{e[MOVIE_COL_FUTURE-1]} ({e[CHOOSER_COL_FUTURE-1]})\n" 
    return message

@reup_auth
def ratings_for_chooser(chooser):
    if chooser.strip() == "":
        raise ValueError("chooser cannot be blank")
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
    if n > len(average_ratings):
        n = len(average_ratings)
    if n < 0:
        n = 0
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
    

##################################################
## FUNCS TO FACILITATE EVENT SCHEDULING
##################################################

@reup_auth
def find_table(table_name):
    if len(gsheet.worksheets()) == len(STATIC_SHEETS):
        return None
    try:
        index = [sheet.title for sheet in gsheet.worksheets()].index(table_name)
        return gsheet.worksheets()[index]
    except ValueError:
        return None

@reup_auth
def most_recent_table():
    if len(gsheet.worksheets()) == len(STATIC_SHEETS):
        return None
    return gsheet.worksheets()[-1].title

@reup_auth
def create_table(table_name, rows=1000, cols=4):
    if len(table_name) > 50:
        raise ValueError('table name cannot exceed 50 characters.')
    if find_table(table_name):
        raise ValueError(f'The name "{table_name}" is already in use.')
        
    new_sheet = gsheet.add_worksheet(title=table_name, rows=rows, cols=cols)
    return new_sheet

@reup_auth
def duplicate_table(table_name):
    table = find_table(table_name)
    if not table:
        raise ValueError(f'A sheet with name "{table_name}" could not be found.')
    index = len(gsheet.worksheets())
    retries = 0
    while retries < 10: 
        letters = string.ascii_lowercase
        sheetname = ''.join(random.choice(letters) for i in range(10))
        try:
            new_table = table.duplicate(insert_sheet_index=index, new_sheet_name=sheetname)
            break
        except:
            retries += 1
    return new_table

@reup_auth
def delete_table(table_name):
    table = find_table(table_name)
    if not table:
        raise ValueError(f'A sheet with name "{table_name}" could not be found.')
    gsheet.del_worksheet(table)
    return None

@reup_auth
def add_row(table_name, values):
    table = find_table(table_name)
    if not table:
        raise ValueError(f'could not find a sheet named "{table_name}".')
    index = len(table.get_all_values()) + 1
    table.insert_row(values, index)
    return None

@reup_auth
def find_rows(table_name, filter_columns=[], criteria=[]):
    """returns results in two lists: first has row numbers, second has values."""
    if len(filter_columns) != len(criteria) or type(filter_columns) != list or type(criteria) != list:
        raise ValueError('filter_columns and criteria must be lists of equal length')
    table = find_table(table_name)
    if not table:
        raise ValueError(f'A sheet with name "{table_name}" could not be found.')
    values = table.get_all_values()
    headers = [value.lower() for value in values[0]]
    filter_indices = []
    for col in filter_columns:
        try:
            filter_indices.append(headers.index(col.lower()))
        except ValueError:
            raise ValueError(f'the column {col} could not be found')
    result_rows = []
    result_row_indices = []
    row_index=2 # row 1 (i.e. header row) is skipped
    for row in values[1:]:
        i = 0
        for filter_index in filter_indices:
            if row[filter_index] != criteria[i]:
                break
            i += 1
        else:
            result_row_indices.append(row_index)
            result_rows.append(row)
        row_index += 1
    return (result_row_indices, result_rows)

@reup_auth
def remove_rows(table_name, filter_columns=[], criteria=[]):
    rows = find_rows(table_name, filter_columns, criteria)
    if rows:
        table = find_table(table_name)
        # reverse removes the issue of indices changing as rows are removed
        for index in reversed(rows[0]):
            table.delete_row(index)
    return None
