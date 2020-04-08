import requests
from lxml import html
from scraping.google import search

def ebert_lookup(movie):
    top_result_url = search(f"{movie} site:https://www.rogerebert.com/")['items'][0]['link']

    page = requests.get(top_result_url)
    tree = html.fromstring(page.content)
    
    title = tree.xpath('//h1[@class="page-content--title"]')[0].text
    author = tree.xpath('//div[@class="page-content--byline-share"]/div/span/a')[0].text
    fullstars = len(tree.xpath('//div[@class="page-content--star-rating"]/span/i[@class="icon-star-full"]'))
    halfstars = len(tree.xpath('//div[@class="page-content--star-rating"]/span/i[@class="icon-star-half"]'))
    score = str(fullstars)

    if halfstars:
        score += ".5"

    message = f'{title.upper()} - {score}/4\n- by {author}\n'

    first_paragraph = tree.xpath('//section[@class="page-content--block_editor-content js--reframe"]/p')[0]
    first_paragraph = first_paragraph.text_content()
    first_paragraph.replace("\'", "")
    message += first_paragraph
    message += "\n read full review: " + top_result_url

    return message