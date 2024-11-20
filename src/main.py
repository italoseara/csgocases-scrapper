import argparse
from time import sleep, time
from dotenv import load_dotenv

from scraper import scrape_promocode
from utils import console, pretty_time


def main() -> None:
    parser = argparse.ArgumentParser(description="csgocases.com promocode scraper")
    parser.add_argument("--force-login", action="store_true", help="Force login to the website")
    parser.add_argument("--data-dir", type=str, default="data", help="Directory to store the scraped data")
    parser.add_argument("--timer", type=int, default=3600, help="Time in seconds to wait between each scrape")

    args = parser.parse_args()
    load_dotenv()

    console.log("Starting the scraper...")

    while True:
        start_time = time()
        console.log("Checking for new promocodes...")
        console.log(f"Timer set to {pretty_time(args.timer)}")

        scrape_promocode(args.force_login, args.data_dir)        

        elapsed_time = time() - start_time
        
        console.log(f"{pretty_time(args.timer - elapsed_time)} until the next scrape")
        sleep(args.timer - elapsed_time)


if __name__ == "__main__":
    main()