import os
from PIL import Image
from dataclasses import dataclass
from discord_webhook import DiscordWebhook, DiscordEmbed

import instaloader as il

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.remote.webdriver import WebDriver

from utils import download_image, console, find_element, image_to_string


@dataclass
class Post:
    """A class to represent a social media post"""

    author: str
    text: str
    image: Image
    url: str
    image_url: str


class TwitterScraper:
    def __init__(self, driver: WebDriver, force_login: bool, data_dir: str) -> None:
        self.force_login = force_login
        self.data_dir = os.path.abspath(data_dir)
        self.driver = driver
        self.is_logged_in = False

    def login(self) -> None:
        username = input('Enter the username (email or phone number) for Twitter: ')
        password = input(f'Enter the password for {username}: ')

        self.driver.get('https://x.com/i/flow/login')

        find_element(self.driver, By.CSS_SELECTOR, 'input[autocomplete="username"]')\
            .send_keys(username + Keys.RETURN)

        find_element(self.driver, By.CSS_SELECTOR, 'input[autocomplete="current-password"]')\
            .send_keys(password + Keys.RETURN)

        try:
            code_input = find_element(self.driver, By.CSS_SELECTOR, 'input[autocomplete]', timeout=5)
            if self.driver.current_url != 'https://x.com/home':
                code = input('Enter the confirmation code: ')
                code_input.send_keys(code + Keys.RETURN)
        except TimeoutException:
            pass

        WebDriverWait(self.driver, 10).until(EC.url_matches('https://x.com/home'))

        self.is_logged_in = True

    def get_last_tweet(self) -> Post:
        if not self.is_logged_in and self.force_login:
            self.login()

        self.driver.get(f'https://x.com/{os.getenv("TWITTER_USERNAME")}')

        try:
            tweet = find_element(self.driver, By.CSS_SELECTOR, 'article')

            text = tweet.find_element(By.CSS_SELECTOR, 'div[data-testid="tweetText"]').text
            author = tweet.find_element(By.CSS_SELECTOR, 'a > div > span').text[1:]
            if image_elm := tweet.find_element(By.CSS_SELECTOR, 'div[data-testid="tweetPhoto"] > img'):
                image = download_image(image_elm.get_attribute('src'))
            else:
                image = None
            url = tweet.find_element(By.CSS_SELECTOR, 'a:has(time)').get_attribute('href')

            return Post(author, text, image, url, image_elm.get_attribute('src'))
        except TimeoutException:
            console.log('Could not find the last tweet')
            return None

class InstagramScraper:
    def __init__(self, force_login: bool, data_dir: str) -> None:
        self.force_login = force_login
        self.data_dir = data_dir

    def login(self) -> None:
        self.L = il.Instaloader(quiet=True)

        if self.force_login:
            username = input('Enter the username for Instagram: ')
            password = input(f'Enter the password for {username}: ')

            self.L.login(username, password)
            self.L.save_session_to_file(filename=f"{self.data_dir}/session")
        else:
            self.L.load_session_from_file(username="user", filename=f"{self.data_dir}/session")

    def get_last_post(self) -> Post:
        self.login()

        profile = il.Profile.from_username(self.L.context, os.getenv('INSTAGRAM_USERNAME'))
        post = next(profile.get_posts())

        image = download_image(post.url)
        text = post.caption
        author = post.owner_username

        return Post(author, text, image, f"https://instagram.com/{profile.username}", post.url)


class FacebookScraper:
    def __init__(self, driver: WebDriver, force_login: bool, data_dir: str) -> None:
        self.force_login = force_login
        self.data_dir = os.path.abspath(data_dir)
        self.driver = driver
        self.is_logged_in = False

    def login(self) -> None:
        raise NotImplementedError

    def get_last_post(self) -> Post:
        self.driver.get(f'https://facebook.com/{os.getenv("FACEBOOK_USERNAME")}')

        try:
            last_post = (By.CSS_SELECTOR, 'div[data-virtualized="false"] > div > div> div > div > div:has(img)')
            WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located(last_post))
            last_post = self.driver.find_element(*last_post)

            author = last_post.find_element(By.CSS_SELECTOR, 'strong > span').text
            text = last_post.find_element(By.CSS_SELECTOR, 'div > span[dir=auto]').text
            image_elm = last_post.find_element(By.CSS_SELECTOR, 'div > img')
            image = download_image(image_elm.get_attribute('src'))
            url = last_post.find_element(By.CSS_SELECTOR, 'a:has(span > span)').get_attribute('href')

            return Post(author, text, image, url, image_elm.get_attribute('src'))
        except TimeoutException:
            return None


def scrape_twitter(driver: WebDriver, force_login: bool, data_dir: str) -> Post:
    scraper = TwitterScraper(driver, force_login, data_dir)
    tweet = scraper.get_last_tweet()

    if not tweet:
        console.log('Could not scrape the last tweet')

    return tweet

def scrape_instagram(force_login: bool, data_dir: str) -> Post:
    scraper = InstagramScraper(force_login, data_dir)
    post = scraper.get_last_post()

    if not post:
        console.log('Could not scrape the last post')

    return post

def scrape_facebook(driver: WebDriver, force_login: bool, data_dir: str) -> Post:
    scraper = FacebookScraper(driver, force_login, data_dir)
    post = scraper.get_last_post()

    if not post:
        console.log('Could not scrape the last post')

    return post


def post_to_discord(post: Post, code: str) -> None:
    if post is None or code is None:
        return

    console.log('Sending message...')
    webhook = DiscordWebhook(url=os.getenv('DISCORD_WEBHOOK_URL'), content='<@&1308897892240723979>')

    embed = DiscordEmbed(title=f"New promocode `{code}`", description=f"Click [here]({post.url}) to see the post", color="6dc176")
    embed.set_author(name=post.author, 
                     icon_url="https://csgocases.com/images/avatar.jpg", 
                     url='https://csgocases.com')
    embed.set_image(url=post.image_url)
    embed.set_timestamp()

    webhook.add_embed(embed)

    response = webhook.execute()
    if response.ok:
        console.log('Message sent successfully!\n')
    else:
        console.log('Could not send the message\n')

def scrape_promocode(force_login: bool, data_dir: str) -> None:
    data_dir = os.path.abspath(data_dir)
    
    options = Options()
    options.add_argument('--headless')
    options.add_argument("--user-data-dir=" + data_dir) if data_dir else None
    options.add_argument('--log-level=0')
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")
    options.add_argument("--enable-unsafe-swiftshader")
    options.add_argument("--output=/dev/null")

    prefs = {"profile.managed_default_content_settings.stylesheets": 2}
    options.add_experimental_option("prefs", prefs)
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
        
    twitter_post = scrape_twitter(driver, force_login, data_dir)
    instagram_post = scrape_instagram(force_login, data_dir)
    facebook_post = scrape_facebook(driver, force_login, data_dir)

    codes = []
    for post in [twitter_post, instagram_post, facebook_post]:
        if post is None:
            continue
        
        if 'promocode' in post.text:
            code = image_to_string(post.image)
            if code:
                codes.append((post, code))

    with open('promocodes.txt', 'w+') as file:
        announced_codes = file.read().splitlines()

    for post, code in codes:
        if code not in announced_codes:
            with open('promocodes.txt', 'a') as file:
                file.write(code + '\n')

            print(f'New promocode: {code}\n')
            post_to_discord(post, code)
    
    driver.quit()