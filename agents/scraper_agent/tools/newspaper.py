def scrape(url: str):
    try:
        from newspaper import Article
    except ImportError:
        # Newspaper not available → agent should fall back
        return None

    try:
        article = Article(url)
        article.download()
        article.parse()

        if not article.text or len(article.text) < 100:
            return None

        return {
            "text": article.text,
            "title": article.title,
            "date": article.publish_date,
            "tool": "newspaper3k",
        }
    except Exception:
        return None