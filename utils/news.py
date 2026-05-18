import finnhub
from datetime import datetime, timedelta



def get_latest_news(ticker, api_key, limit=7):
    """Fetches the latest 'limit' news items for a ticker from Finnhub.

    Returns:
        list of dict: [{'date': 'YYYY-MM-DD', 'headline': '...', 'summary': '...'}, ...]
    """
    finnhub_client = finnhub.Client(api_key=api_key)

    to_date = datetime.now()
    from_date = to_date - timedelta(days=limit)

    to_date_str = to_date.strftime('%Y-%m-%d')
    from_date_str = from_date.strftime('%Y-%m-%d')

    try:
        news = finnhub_client.company_news(ticker, _from=from_date_str, to=to_date_str)

        top_news = news[:limit]

        formatted_news = []
        for article in top_news:
            article_date = datetime.fromtimestamp(article['datetime']).strftime('%Y-%m-%d')

            entry = {
                'date': article_date,
                'headline': article['headline'],
                'summary': article['summary']
            }
            formatted_news.append(entry)

        return formatted_news

    except Exception as e:
        print(f"An error occurred: {e}")
        return []