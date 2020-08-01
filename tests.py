import unittest
import os
from movie_db import movieNightBot
import sqlite3 


class CoreMelonBotTest(unittest.TestCase):
    def setUp(self):

        self.mnb = movieNightBot(db_file=":memory:")
        self.discord_id = 99999
        self.discord_id2 = 11111
        self.discord_id3 = 22222
        self.nick = 'test000'
        self.nick2 = 'test001'
        self.nick3 = 'test002'
        self.movie = "a test movie"
        self.movie2 = "second test movie"
        
    def test_register(self):
        self.mnb.register(discord_id=self.discord_id, nick=self.nick)
        
    def test_register_duplicate_name(self):
        self.mnb.register(discord_id=self.discord_id2, nick=self.nick2)
        with self.assertRaises(ValueError):
            self.mnb.register(discord_id=self.discord_id2, nick=self.nick2)
            
    def test_register_duplicate_discord_id(self):
        self.mnb.register(discord_id=self.discord_id2, nick=self.nick)
        with self.assertRaises(ValueError):
            self.mnb.register(discord_id=self.discord_id2, nick=self.nick)
            
    def test_suggest_movie(self):
        self.mnb.suggest_movie(movie_title=self.movie, chooser_discord_id=self.discord_id)
        movie_exists = self.mnb.suggestion_exists(self.movie)
        self.assertTrue(movie_exists)
        
    def test_add_duplicate_movie(self):
        self.mnb.suggest_movie(movie_title=self.movie2, chooser_discord_id=self.discord_id)
        with self.assertRaises(ValueError):
            self.mnb.suggest_movie(movie_title=self.movie2, chooser_discord_id=self.discord_id)
        
    def test_remove_suggestion(self):
        self.mnb.remove_suggestion(self.movie2)
        movie_exists = self.mnb.suggestion_exists(self.movie2)
        self.assertFalse(movie_exists)
        
    def test_transfer_movie(self):
        self.mnb.transfer_suggestion(movie_title=self.movie, new_chooser_discord_id=self.discord_id2)
        
    def test_find_all_user(self):
        self.mnb.register(discord_id=self.discord_id, nick=self.nick)
        self.mnb.suggest_movie(movie_title=self.movie, chooser_discord_id=self.discord_id)
        #self.mnb.suggest_movie(movie_title=self.movie2, chooser_discord_id=self.discord_id)
        # TODO: add rate_movie, as well as an assertion test for it.
        # TODO: alsoo add assertion to test that the user's rating shows up in a 2nd line
        message = self.mnb.find_all('test')
        self.assertTrue(message.find("1 movie suggestion") > -1)
        
    def test_find_all_suggestion(self):
        self.mnb.register(discord_id=self.discord_id, nick=self.nick)
        self.mnb.suggest_movie(movie_title=self.movie, chooser_discord_id=self.discord_id)
        message = self.mnb.find_all('movie')
        
    def test_endorse_suggestion(self):
        self.mnb.register(discord_id=self.discord_id, nick=self.nick)
        self.mnb.register(discord_id=self.discord_id2, nick=self.nick2)
        self.mnb.suggest_movie(movie_title=self.movie, chooser_discord_id=self.discord_id)
        self.mnb.endorse_suggestion(movie_title=self.movie, endorser_discord_id=self.discord_id2)
        self.assertTrue(self.mnb.is_endorsed(movie_title=self.movie, endorser_discord_id=self.discord_id2))
        
    def test_unendorse_movie(self):
        self.mnb.register(discord_id=self.discord_id, nick=self.nick)
        self.mnb.register(discord_id=self.discord_id2, nick=self.nick2)
        self.mnb.suggest_movie(movie_title=self.movie, chooser_discord_id=self.discord_id)
        self.mnb.endorse_suggestion(movie_title=self.movie, endorser_discord_id=self.discord_id2)
        self.mnb.unendorse_suggestion(movie_title=self.movie, endorser_discord_id=self.discord_id2)
        self.assertFalse(self.mnb.is_endorsed(movie_title=self.movie, endorser_discord_id=self.discord_id2))
        
    def test_rate_movie(self):
        self.mnb.register(discord_id=self.discord_id, nick=self.nick)
        self.mnb.register(discord_id=self.discord_id2, nick=self.nick2)
        self.mnb.suggest_movie(movie_title=self.movie, chooser_discord_id=self.discord_id)
        self.mnb.rate_movie(movie_title=self.movie, rater_discord_id=self.discord_id2,rating=10)
    
    def test_retrieve_suggestions(self):
        self.mnb.register(discord_id=self.discord_id, nick=self.nick)
        self.mnb.suggest_movie(movie_title=self.movie, chooser_discord_id=self.discord_id)
        message = self.mnb.retrieve_suggestions(chooser_discord_id=self.discord_id)
        self.assertTrue(self.movie in message)
    
    def test_top_endorsed(self):
        self.mnb.register(discord_id=self.discord_id, nick=self.nick)
        self.mnb.register(discord_id=self.discord_id2, nick=self.nick2)
        self.mnb.register(discord_id=self.discord_id3, nick=self.nick3)
        self.mnb.suggest_movie(movie_title=self.movie, chooser_discord_id=self.discord_id)
        self.mnb.suggest_movie(movie_title=self.movie2, chooser_discord_id=self.discord_id)
        self.mnb.endorse_suggestion(movie_title=self.movie, endorser_discord_id=self.discord_id2)
        self.mnb.endorse_suggestion(movie_title=self.movie2, endorser_discord_id=self.discord_id2)
        self.mnb.endorse_suggestion(movie_title=self.movie2, endorser_discord_id=self.discord_id3)
        message = self.mnb.top_endorsed()
        
    def test_unendorsed_all(self):
        self.mnb.register(discord_id=self.discord_id, nick=self.nick)
        self.mnb.register(discord_id=self.discord_id2, nick=self.nick2)
        self.mnb.suggest_movie(movie_title=self.movie, chooser_discord_id=self.discord_id)
        self.mnb.suggest_movie(movie_title=self.movie2, chooser_discord_id=self.discord_id)
        message = self.mnb.unendorsed()
        lines = message.split('\n')
        self.assertTrue(len(lines)==4)
    
    def test_unendorsed_user(self):
        self.mnb.register(discord_id=self.discord_id, nick=self.nick)
        self.mnb.register(discord_id=self.discord_id2, nick=self.nick2)
        self.mnb.suggest_movie(movie_title=self.movie, chooser_discord_id=self.discord_id)
        self.mnb.suggest_movie(movie_title=self.movie2, chooser_discord_id=self.discord_id2)
        message = self.mnb.unendorsed(chooser_discord_id=self.discord_id)
        lines = message.split('\n')
        self.assertTrue(len(lines)==3)
        
    def test_ratings_for_choosers_movies(self):
        self.mnb.register(discord_id=self.discord_id, nick=self.nick)
        self.mnb.register(discord_id=self.discord_id2, nick=self.nick2)
        self.mnb.suggest_movie(movie_title=self.movie, chooser_discord_id=self.discord_id)
        self.mnb.suggest_movie(movie_title=self.movie2, chooser_discord_id=self.discord_id)
        self.mnb.rate_movie(movie_title=self.movie, rater_discord_id=self.discord_id,rating=5)
        self.mnb.rate_movie(movie_title=self.movie2, rater_discord_id=self.discord_id,rating=6)
        self.mnb.rate_movie(movie_title=self.movie2, rater_discord_id=self.discord_id2,rating=7)
        message = self.mnb.ratings_for_choosers_movies(chooser_discord_id=self.discord_id)
        self.assertTrue(message.find('6.5') > -1 and message.find('5.0') > -1)
        
    def test_ratings_from_reviewer(self):
        self.mnb.register(discord_id=self.discord_id, nick=self.nick)
        self.mnb.register(discord_id=self.discord_id2, nick=self.nick2)
        self.mnb.suggest_movie(movie_title=self.movie, chooser_discord_id=self.discord_id)
        self.mnb.suggest_movie(movie_title=self.movie2, chooser_discord_id=self.discord_id)
        self.mnb.rate_movie(movie_title=self.movie, rater_discord_id=self.discord_id,rating=5)
        self.mnb.rate_movie(movie_title=self.movie2, rater_discord_id=self.discord_id,rating=6)
        self.mnb.rate_movie(movie_title=self.movie2, rater_discord_id=self.discord_id2,rating=7)
        message = self.mnb.ratings_from_reviewer(rater_discord_id=self.discord_id)
        self.assertTrue(message.find('5.0') > -1 and message.find('6.0') > -1)
    
    def test_missing_ratings_for_reviewer(self):
        self.mnb.register(discord_id=self.discord_id, nick=self.nick)
        self.mnb.register(discord_id=self.discord_id2, nick=self.nick2)
        self.mnb.suggest_movie(movie_title=self.movie, chooser_discord_id=self.discord_id)
        self.mnb.suggest_movie(movie_title=self.movie2, chooser_discord_id=self.discord_id)
        self.mnb.rate_movie(movie_title=self.movie, rater_discord_id=self.discord_id,rating=5)
        message = self.mnb.missing_ratings_for_reviewer(rater_discord_id=self.discord_id2)
        self.assertTrue(self.movie in message)
        
    def test_standings(self):
        self.mnb.register(discord_id=self.discord_id, nick=self.nick)
        self.mnb.register(discord_id=self.discord_id2, nick=self.nick2)
        self.mnb.suggest_movie(movie_title=self.movie, chooser_discord_id=self.discord_id)
        self.mnb.suggest_movie(movie_title=self.movie2, chooser_discord_id=self.discord_id2)
        self.mnb.rate_movie(movie_title=self.movie, rater_discord_id=self.discord_id,rating=5)
        self.mnb.rate_movie(movie_title=self.movie2, rater_discord_id=self.discord_id,rating=6)
        self.mnb.rate_movie(movie_title=self.movie2, rater_discord_id=self.discord_id2,rating=7)
        message = self.mnb.standings()
        
    def test_top_ratings(self):
        self.mnb.register(discord_id=self.discord_id, nick=self.nick)
        self.mnb.register(discord_id=self.discord_id2, nick=self.nick2)
        self.mnb.suggest_movie(movie_title=self.movie, chooser_discord_id=self.discord_id)
        self.mnb.suggest_movie(movie_title=self.movie2, chooser_discord_id=self.discord_id2)
        self.mnb.rate_movie(movie_title=self.movie, rater_discord_id=self.discord_id,rating=5)
        self.mnb.rate_movie(movie_title=self.movie2, rater_discord_id=self.discord_id,rating=6)
        self.mnb.rate_movie(movie_title=self.movie2, rater_discord_id=self.discord_id2,rating=7)
        message = self.mnb.top_ratings()
        
    def test_pick_random_movie(self):
        self.mnb.register(discord_id=self.discord_id, nick=self.nick)
        self.mnb.suggest_movie(movie_title=self.movie, chooser_discord_id=self.discord_id)
        self.mnb.suggest_movie(movie_title=self.movie2, chooser_discord_id=self.discord_id)

        
if __name__ == '__main__':
    unittest.main()