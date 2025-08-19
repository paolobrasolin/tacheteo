#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "requests>=2.31.0",
#     "beautifulsoup4>=4.12.0",
#     "lxml>=4.9.0"
# ]
# ///

import requests
from bs4 import BeautifulSoup
import json
import time
import re
import argparse
from urllib.parse import urljoin, urlparse
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TACScraper:
    def __init__(self, base_url="http://www.tac.mta.ca/tac/"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )
        self.papers = []

    def get_page(self, url):
        """Get a page with error handling and retries"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt == max_retries - 1:
                    logger.error(f"Failed to fetch {url} after {max_retries} attempts")
                    return None
                time.sleep(2**attempt)  # Exponential backoff
        return None

    def extract_paper_links(self, html_content):
        """Extract paper links from the main TAC page"""
        soup = BeautifulSoup(html_content, "html.parser")
        paper_links = []

        # Look for links that match the pattern volumes/VOLUME_ID/PAPER_ID
        for link in soup.find_all("a", href=True):
            href = link["href"]
            # Check if it's a paper link (e.g., volumes/44/1/44-01abs.html)
            if re.match(r"volumes/\d+/\d+/.*\.html", href):
                paper_links.append(href)

        return list(set(paper_links))  # Remove duplicates

    def extract_paper_info(self, url, html_content):
        """Extract basic paper information: volume_id, paper_id, url, and raw text"""
        # Extract volume and paper ID from URL
        volume_id = ""
        paper_id = ""
        url_match = re.search(r"volumes/(\d+)/(\d+)/([^/]+)", url)
        if url_match:
            volume_id = url_match.group(1)
            paper_id = url_match.group(2)

        # Get raw plain text content
        soup = BeautifulSoup(html_content, "html.parser")
        raw_text = soup.get_text()

        return {
            "url": url,
            "volume_id": volume_id,
            "paper_id": paper_id,
            "raw_text": raw_text,
        }

    def scrape_all_papers(self, limit=None):
        """Main method to scrape all papers"""
        logger.info("Starting to scrape TAC website...")

        # Get main page
        main_response = self.get_page(self.base_url)
        if not main_response:
            logger.error("Failed to fetch main page")
            return

        # Extract paper links
        paper_links = self.extract_paper_links(main_response.text)
        logger.info(f"Found {len(paper_links)} paper links")

        # Apply limit if specified
        if limit:
            paper_links = paper_links[:limit]
            logger.info(f"Limiting to first {limit} papers for development")

        # Scrape each paper
        for i, link in enumerate(paper_links):
            full_url = urljoin(self.base_url, link)
            logger.info(f"Scraping paper {i+1}/{len(paper_links)}: {full_url}")

            # Get paper page
            paper_response = self.get_page(full_url)
            if paper_response:
                paper_info = self.extract_paper_info(full_url, paper_response.text)
                self.papers.append(paper_info)
                logger.info(f"Successfully scraped: {full_url}")
            else:
                logger.warning(f"Failed to scrape paper: {full_url}")

            # Be respectful with rate limiting
            time.sleep(1)

        logger.info(f"Scraping completed. Total papers scraped: {len(self.papers)}")

    def save_to_json(self, filename="tac.json"):
        """Save scraped data to JSON file"""
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.papers, f, indent=2, ensure_ascii=False)
        logger.info(f"Data saved to {filename}")

    def run(self, limit=None):
        """Run the complete scraping process"""
        try:
            self.scrape_all_papers(limit)
            self.save_to_json()
            return self.papers
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            return None


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Scrape TAC website for papers")
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=None,
        help="Limit number of papers to scrape (default: all papers)",
    )
    parser.add_argument(
        "--dev", action="store_true", help="Development mode: limit to 10 papers"
    )

    args = parser.parse_args()

    # Set default limit for development mode
    if args.dev:
        limit = 10
        print("Development mode: limiting to 10 papers")
    else:
        limit = args.limit

    scraper = TACScraper()
    papers = scraper.run(limit)

    if papers:
        print(f"\nScraping completed successfully!")
        print(f"Total papers scraped: {len(papers)}")
        print(f"Data saved to tac_papers.json")

        # Show a sample of the first paper
        if papers:
            print(f"\nSample paper:")
            first_paper = papers[0]
            print(f"URL: {first_paper['url']}")
            print(
                f"Volume: {first_paper['volume_id']}, Paper: {first_paper['paper_id']}"
            )
            print(f"Raw text length: {len(first_paper['raw_text'])} characters")
    else:
        print("Scraping failed. Check the logs for details.")


if __name__ == "__main__":
    main()
