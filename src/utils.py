import cv2
import numpy
import requests 
import pytesseract
from PIL import Image
from rich.console import Console
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


console = Console()


def image_to_string(image: Image.Image) -> str:
    w, h = image.size

    print(w, h)
    
    crop_dimensions = (100, 440, w - 80, 540) if (h >= 720 and w >= 720) else (100, 310, w - 80, 410)
    image = image.crop(crop_dimensions)

    image.show()
    input("Press Enter to continue...")

    cv_image = cv2.cvtColor(numpy.array(image), cv2.COLOR_RGB2BGR)
    grayscale_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    _, binary_image = cv2.threshold(grayscale_image, 200, 255, cv2.THRESH_BINARY)

    return pytesseract.image_to_string(binary_image).strip()


def download_image(url: str) -> Image:
    return Image.open(requests.get(url, stream=True).raw)


def pretty_time(seconds: int) -> str:
    # Time in the format HH\h MM\m SS\s, e.g. 01h 23m 45s or 32m 10s or 1s

    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    seconds = int(seconds)	# Remove decimal places

    time = ""
    if hours:
        time += f"{hours}h "
    if minutes:
        time += f"{minutes}m "
    if seconds:
        time += f"{seconds}s"

    return time.strip()


def find_element(driver: WebDriver, by: str, value: str, timeout: int = 10) -> WebElement:
    try:
        return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
    except TimeoutException:
        console.log(f"Element with {by}='{value}' not found")
        raise
