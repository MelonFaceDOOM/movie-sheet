import requests
from lxml import html
import random
import re


def standardize_url(domain, path, protocol='https'):
    """domain should just be google.com, not https://www.google.com
    path is meant to contain the url path along with an unknown amount of preceeding url components.
    this will return a full url+subdirectory"""
    pattern = "(https*)*(:\/\/)*(www\.)*(\w+)*(\.\w+)*(\/)*(.*)"
    match = re.match(pattern, path)
    protocol_from_path = match.groups()[0]
    host = match.groups()[2]  # host is www. or None
    domain_from_path = (match.groups()[3] if match.groups()[3] else '') + (
        match.groups()[4] if match.groups()[4] else '')
    path = match.groups()[6]

    protocol = protocol_from_path if protocol_from_path else protocol
    domain = domain_from_path if domain_from_path else domain
    standardized_url = (protocol if protocol else '') + "://" + (host if host else '') + (
        domain if domain else '') + "/" + (path if path else '')
    if standardized_url[-1] != "/":
        standardized_url += "/"
    return standardized_url


def random_gamespot_post(board_name=""):
    """recognized board_name values are case-insensitive: 'ot', 'sw'"""
    base_url = 'gamespot.com'
    r = requests.get('https://www.gamespot.com/forums/')

    tree = html.fromstring(r.text)
    board_links = tree.xpath('//a[@class="board-name"]')
    board_links = [board_link.get('href') for board_link in board_links]

    if board_name.lower() == "ot":
        board_link = board_links[1]
    elif board_name.lower() == "sw":
        board_link = board_links[2]
    else:
        post_counts = tree.xpath('//div[@class="inner-space-small col-postCount"]')
        post_counts = [post_count.text.strip() for post_count in post_counts]
        post_counts = [int(post_count) for post_count in post_counts if post_count != "Posts"]
        total_posts = sum(post_counts)
        random_post_number = random.randrange(total_posts)

        for i, post_count in enumerate(post_counts):
            random_post_number -= post_count
            if random_post_number < 1:
                board_index = i
                break
        board_link = board_links[board_index]

    board_link = standardize_url(base_url, board_link)

    r = requests.get(board_link)
    tree = html.fromstring(r.text)
    page_count = tree.xpath('//li[@class="paginate__item"]/a')[-1].text
    page_count = int(page_count)
    random_page_number = random.randrange(1, page_count + 1)
    board_page_link = board_link + f"?page={random_page_number}"

    r = requests.get(board_page_link)
    tree = html.fromstring(r.text)
    threads = tree.xpath('//div[@class="inner-space-small forum-topic"]')
    thread_urls = [thread.xpath('./div/a')[0].get('href') for thread in threads]
    thread_link = random.choice(thread_urls)
    thread_link = standardize_url(base_url, thread_link)

    r = requests.get(thread_link)
    tree = html.fromstring(r.text)
    pages = tree.xpath('//li[@class="paginate__item"]/a')
    if pages:
        page_count = pages[-1].text
        page_count = int(page_count)
        random_page_number = random.randrange(1, page_count + 1)
        thread_page_link = thread_link + f"?page={random_page_number}"
        r = requests.get(thread_page_link)
        tree = html.fromstring(r.text)

    post_elements = tree.xpath('//div[@class="message-inner message-inner--forum"]')
    posts = []
    for post_element in post_elements:
        author = post_element.xpath('.//a[contains(@class,"message-user")]')[0].text
        time = post_element.xpath('.//time')[0].get('title')
        post_link = post_element.xpath('.//div[@class="message-title"]/a')[0].get('href')
        post_link = standardize_url(base_url, post_link)
        lines = post_element.xpath('.//blockquote/following-sibling::p')
        if not lines:
            lines = post_element.xpath('.//p')
        if not lines:
            post = post_element.text
        else:
            post = [line.text for line in lines if line.text]
            post = "\n".join(post)
        if post:
            posts.append((author, time, post_link, post))
        if posts:
            posts.sort(key=lambda x: len(x[3]), reverse=True)
            return posts[0]
        else:
            return random_gamespot_post(board_name=board_name)