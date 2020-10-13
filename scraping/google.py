from googleapiclient.discovery import build
import os

# custom search engine id
gcsekey = os.path.join(os.path.dirname(__file__), 'gcsekey')
with open(gcsekey) as f:
    my_cse_id = f.read()
# google search api key
gapikey = os.path.join(os.path.dirname(__file__), 'gapikey')
with open(gapikey) as f:
    my_api_key = f.read()

    
def search(search_term, api_key=my_api_key, cse_id=my_cse_id, **kwargs):
    service = build("customsearch", "v1", developerKey=api_key)
    res = service.cse().list(q=search_term, cx=cse_id, **kwargs).execute()
    return res