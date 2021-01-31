import requests
from lxml import html
import random
import re

base_url = "gamespot.com"


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


def get_random_post(directory=None):
    """recognized board_name values are case-insensitive: 'ot', 'sw'
       any other string will be assumed to be a user's profile.
       providing no user/board arg will default to a random board."""
    board_link = None
    if not directory:
        board_link = get_board_link()
    elif directory.lower() == "ot":
        board_link = get_board_link(1)
    elif directory.lower() == "sw":
        board_link = get_board_link(2)

    if board_link:
        board_page_link = get_random_board_page(board_link)
        thread_link = get_random_thread(board_page_link)
        thread_page_link = get_random_thread_page(thread_link)
    else:
        profile_link = get_profile_link(username=directory)
        thread_page_link = get_random_thread_page(profile_link)  # actually links to profile,
        # but it can be treated the same

    post = get_post(thread_page_link)
    if not post:
        raise ValueError(f"couldn't find a post on page {thread_page_link}")
    return post


def get_profile_link(username):
    profile_link = f"https://www.gamespot.com/profile/{username}/forums/"
    r = requests.get(profile_link)
    tree = html.fromstring(r.text)
    error_found = tree.xpath('//div[@class="error"]/h1')
    if error_found:
        raise ValueError('profile not found')
    return standardize_url(base_url, profile_link)


def get_board_link(board_index=None):
    r = requests.get('https://www.gamespot.com/forums/')
    tree = html.fromstring(r.text)
    board_links = tree.xpath('//a[@class="board-name"]')
    board_links = [board_link.get('href') for board_link in board_links]
    post_counts = tree.xpath('//div[@class="inner-space-small col-postCount"]')
    post_counts = [post_count.text.strip() for post_count in post_counts]
    post_counts = [int(post_count) for post_count in post_counts if post_count != "Posts"]
    total_posts = sum(post_counts)

    if not board_index:
        # find random board_index if none provided
        random_post_number = random.randrange(total_posts)
        for i, post_count in enumerate(post_counts):
            random_post_number -= post_count
            if random_post_number < 1:
                board_index = i
                break

    board_link = standardize_url(base_url, board_links[board_index])
    return board_link


def get_random_board_page(board_link):
    r = requests.get(board_link)
    tree = html.fromstring(r.text)
    page_count = tree.xpath('//li[@class="paginate__item"]/a')[-1].text
    page_count = int(page_count)
    random_page_number = random.randrange(1, page_count + 1)
    board_page_link = board_link + f"?page={random_page_number}"
    board_page_link = standardize_url(base_url, board_page_link)
    return board_page_link


def get_random_thread(board_page_link):
    r = requests.get(board_page_link)
    tree = html.fromstring(r.text)
    threads = tree.xpath('//div[@class="inner-space-small forum-topic"]')
    thread_urls = [thread.xpath('./div/a')[0].get('href') for thread in threads]
    thread_link = random.choice(thread_urls)
    thread_link = standardize_url(base_url, thread_link)
    return thread_link


def get_random_thread_page(thread_link):
    r = requests.get(thread_link)
    tree = html.fromstring(r.text)
    pages = tree.xpath('//li[@class="paginate__item"]/a')
    if pages:
        page_count = pages[-1].text
        page_count = int(page_count)
        random_page_number = random.randrange(1, page_count + 1)
        thread_link = thread_link + f"?page={random_page_number}"
    return thread_link


def find_posts_in_page(page_link):
    r = requests.get(page_link)
    tree = html.fromstring(r.text)
    post_elements = tree.xpath('//div[@class="message-inner message-inner--forum"]')
    return post_elements


def extract_info_from_post(post_element):
    author = post_element.xpath('.//a[contains(@class,"message-user")]')[0].text
    time = post_element.xpath('.//time')[0].get('title')
    post_link = post_element.xpath('.//div[@class="message-title"]/a')[0].get('href')
    post_link = standardize_url(base_url, post_link)
    post_link = post_link.strip('/')  # a slash at the end of the url breaks the js post-finding function

    # some posts have all text simply immediately inside the article
    body = post_element.xpath('.//article[contains(@class, "message-content")]')[0].text

    # if not, the take should be in any number of p elements. unfortunately, so will quoted text,
    # it isn't clear how to differentiate the two scenarios
    if not body:
        # main quoted text is found in blockquote, so step 1 is to skip over this.
        # note there can be more quoted text outside of it
        p_elements = post_element.xpath('.//blockquote/following-sibling::p')
        if not p_elements:
            # if no blockquote was found, just collect all p elements.
            p_elements = post_element.xpath('.//p')
        # we should have p_elements, and now need to extract text from them
        body = [drill_till_text_found(p_element) for p_element in p_elements]
        body = "\n".join(body)
    body = body.strip()
    if not body:
        body = str(html.tostring(post_element)) # fuck it, just return the raw html code
    return author, time, post_link, body


def drill_till_text_found(html_element):
    """will keep looking into the first next element until text is found, or the end is reached."""
    extracted_text = html_element.text
    child = html_element
    while not extracted_text:
        child = child.xpath("/*")
        if not child:
            break  # no child found
        else:
            child = child[0]
            extracted_text = child.text
    if not extracted_text:
        extracted_text = ""
    return extracted_text


def get_post(page_link, get_longest_post=False):
    post_elements = find_posts_in_page(page_link)
    posts = []
    for post_element in post_elements:
        post = extract_info_from_post(post_element)
        posts.append(post)
    if posts:
        if get_longest_post:
            posts.sort(key=lambda x: len(x[3]), reverse=True)
            return posts[0]
        else:
            return random.choice(posts)
    else:
        return []
