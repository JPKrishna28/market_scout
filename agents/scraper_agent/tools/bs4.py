import requests
from bs4 import BeautifulSoup
from .cleaners import clean_soup
from .dates import from_meta, from_text


def scrape(url: str):
    r = requests.get(url, timeout=10)
    soup = clean_soup(BeautifulSoup(r.text, "html.parser"))

    text = soup.get_text("\n", strip=True)
    if len(text) < 100:
        return None

    return {
        "text": text,
        "title": soup.title.string if soup.title else "",
        "date": from_meta(soup) or from_text(text),
        "tool": "beautifulsoup",
    }