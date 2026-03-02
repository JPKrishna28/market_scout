from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from .cleaners import clean_soup
from .dates import from_meta, from_text


def scrape(url: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=15000)
        html = page.content()
        browser.close()

    soup = clean_soup(BeautifulSoup(html, "html.parser"))
    text = soup.get_text("\n", strip=True)

    if len(text) < 100:
        return None

    return {
        "text": text,
        "title": soup.title.string if soup.title else "",
        "date": from_meta(soup) or from_text(text),
        "tool": "playwright",
    }