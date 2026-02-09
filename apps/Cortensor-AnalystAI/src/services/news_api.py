# src/services/news_api.py

import logging
import requests
import yfinance as yf
from thefuzz import fuzz
from src.config import (
    NEWS_API_KEY, 
    FMP_API_KEY, 
    COINGECKO_API_URL, 
    FMP_API_URL, 
    NEWSAPI_URL,
    DEFAULT_API_TIMEOUT,
    FMP_PROFILE_TIMEOUT,
    NEWS_LOOKBACK_DAYS,
    NEWS_EXTENDED_LOOKBACK_DAYS,
    NEWS_PAGE_SIZE,
    NEWS_FUZZY_MATCH_THRESHOLD
)
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def filter_news_by_topic(articles: list[dict], topic: str, symbol: str, min_score: int = NEWS_FUZZY_MATCH_THRESHOLD) -> list[dict]:
    """
    Filters a list of articles to include only those highly relevant to the topic/symbol,
    using fuzzy matching on title and description.
    Prioritizes strong, explicit matches.
    """
    relevant_articles = []
    
    # Generate a list of keywords to search for, prioritizing exact phrases and symbols
    # Add common variations if applicable (e.g., "Solana", "SOL")
    keywords = [topic.lower()]
    if symbol and symbol.lower() != topic.lower(): # Only add symbol if it's distinct from the full topic name
        keywords.append(symbol.lower())
    
    logger.debug(f"Filtering news for keywords: {keywords}")

    for article in articles:
        title = article.get('title', '')
        description = article.get('description', '')
        content = article.get('content', '') # Also check content if available, for better relevance

        # Combine text for matching
        full_text = f"{title} {description} {content}".lower()
        
        is_relevant = False
        for kw in keywords:
            # Check for direct substring match first (most reliable)
            if kw in full_text:
                is_relevant = True
                break
            # Fallback to fuzzy match only if no direct match and score is very high
            title_score = fuzz.partial_ratio(kw, title.lower())
            desc_score = fuzz.partial_ratio(kw, description.lower())
            content_score = fuzz.partial_ratio(kw, content.lower())
            
            # If any part gets a very high fuzzy score, consider it relevant
            if max(title_score, desc_score, content_score) >= min_score:
                is_relevant = True
                logger.debug(f"Fuzzy match for '{kw}' found in '{title}' (score: {max(title_score, desc_score, content_score)})")
                break
        
        if is_relevant:
            relevant_articles.append(article)
            
    # Sort by relevance (e.g., highest score for the primary topic) or recency
    # For simplicity, we'll rely on NewsAPI's sortBy=relevancy, but local sorting could be added.
    
    return relevant_articles


def get_news_from_yahoo(topic: str, limit: int = NEWS_PAGE_SIZE) -> list[dict] | None:
    """
    Fetches news from Yahoo Finance. Specifically for STOCKS.
    """
    try:
        logger.info(f"Attempting stock news fetch for '{topic}' from Yahoo Finance.")
        stock = yf.Ticker(topic)
        news_articles = stock.news
        logger.debug(f"Yahoo Finance returned {len(news_articles) if news_articles else 0} raw articles for '{topic}'.")
        
        if not news_articles:
            return None
        
        formatted_articles = []
        # Yahoo Finance often returns relevant articles directly, but we can still filter.
        # Ensure only articles with both title and URL are kept
        for i, article in enumerate(news_articles): # Process all, then limit after filter
            title = article.get('title')
            url = article.get('link')
            if title and url:
                formatted_articles.append({"title": title, "description": article.get('summary', ''), "url": url}) # Yahoo has 'summary'

        # Apply filtering for stricter relevance from Yahoo results too
        filtered_yahoo_articles = filter_news_by_topic(formatted_articles, topic, topic) # Use topic as symbol too
        
        logger.debug(f"Yahoo Finance formatted {len(filtered_yahoo_articles)} valid articles after filtering.")
        return filtered_yahoo_articles[:limit] # Apply limit after filtering
    except Exception as e:
        logger.error(f"Error fetching from yfinance for '{topic}': {e}.")
        return []

def get_crypto_news_from_newsapi(topic: str, symbol: str, limit: int = NEWS_PAGE_SIZE) -> list[dict]:
    """
    Fetches crypto-focused news from NewsAPI.
    Uses both topic name and symbol in the query for better relevance.
    """
    if not NEWS_API_KEY:
        logger.warning("NEWS_API_KEY is not configured for NewsAPI. Skipping crypto news fetch.")
        return []
    
    # --- IMPROVED CRYPTO QUERY ---
    # Prioritize exact topic and symbol, then common crypto keywords
    # Use a narrower date range to get fresher results.
    today = datetime.now()
    # NewsAPI 'from' parameter is date only.
    from_date = (today - timedelta(days=NEWS_LOOKBACK_DAYS)).strftime('%Y-%m-%d')

    query_specific = f'("{topic}" OR "{symbol}") AND (cryptocurrency OR crypto OR blockchain OR web3 OR coin)'
    url_specific = f"{NEWSAPI_URL}/everything?q={query_specific}&language=en&pageSize={limit}&sortBy=relevancy&from={from_date}&apiKey={NEWS_API_KEY}"
    
    articles = []
    try:
        logger.info(f"Attempting crypto news fetch from NewsAPI with specific query: {query_specific} from {from_date}.")
        response = requests.get(url_specific, timeout=DEFAULT_API_TIMEOUT)
        logger.debug(f"NewsAPI (crypto specific) response status: {response.status_code}")
        response.raise_for_status()
        articles = response.json().get("articles", [])
        logger.debug(f"NewsAPI (crypto specific) returned {len(articles)} raw articles.")

        # If few or no specific articles are found within 2 days, try a slightly broader date range (e.g., 7 days)
        if not articles and limit > 0:
            logger.warning(f"No specific crypto articles for '{topic}' in last {NEWS_LOOKBACK_DAYS} days. Trying last {NEWS_EXTENDED_LOOKBACK_DAYS} days.")
            from_date_7d = (today - timedelta(days=NEWS_EXTENDED_LOOKBACK_DAYS)).strftime('%Y-%m-%d')
            url_broad_7d = f"{NEWSAPI_URL}/everything?q={query_specific}&language=en&pageSize={limit}&sortBy=relevancy&from={from_date_7d}&apiKey={NEWS_API_KEY}"
            response_broad_7d = requests.get(url_broad_7d, timeout=DEFAULT_API_TIMEOUT)
            logger.debug(f"NewsAPI (crypto 7-day broad) response status: {response_broad_7d.status_code}")
            response_broad_7d.raise_for_status()
            articles.extend(response_broad_7d.json().get("articles", [])) # Extend, don't overwrite
            logger.debug(f"NewsAPI (crypto 7-day broad) added {len(response_broad_7d.json().get('articles', []))} articles, total now: {len(articles)}.")


    except requests.exceptions.RequestException as req_e:
        logger.error(f"Failed to fetch from NewsAPI due to request error for '{topic}': {req_e}")
    except Exception as e:
        logger.error(f"Failed to fetch from NewsAPI for '{topic}': {e}")
    
    formatted_articles = []
    # --- POST-FILTERING AND DEDUPLICATION FOR RELEVANCE ---
    if articles and topic != 'N/A':
        filtered_articles = filter_news_by_topic(articles, topic, symbol)
        
        # If filtering is too aggressive and removes everything, fall back to unfiltered, but log it.
        if not filtered_articles and articles:
            logger.info(f"Filtering for '{topic}' was too aggressive, reverting to unfiltered news.")
            filtered_articles = articles
        
        # Ensure unique articles based on title/url to avoid duplicates from multiple queries
        seen = set()
        unique_articles = []
        for article in filtered_articles:
            key = (article.get('title'), article.get('url'))
            if key not in seen:
                seen.add(key)
                unique_articles.append(article)
        
        for i, article in enumerate(unique_articles[:limit]): # Apply limit again after filtering/deduping
            title = article.get('title')
            url = article.get('url')
            description = article.get('description', '') # Include description for AI if present
            logger.debug(f"NewsAPI Final Article {i+1}: Title='{title}', URL='{url}'")
            if title and url:
                formatted_articles.append({"title": title, "description": description, "url": url})
    
    logger.debug(f"NewsAPI formatted {len(formatted_articles)} valid articles after filtering.")
    return formatted_articles

def get_stock_news_fallback(topic: str, symbol: str, limit: int = NEWS_PAGE_SIZE) -> list[dict]:
    """
    Fallback for stock news if yfinance fails. Uses company name and symbol with NewsAPI.
    """
    if not NEWS_API_KEY:
        logger.warning("NEWS_API_KEY is not configured for stock news fallback. Skipping stock news fallback.")
        return []
    
    company_name = topic # Start with the given topic
    resolved_symbol = symbol # Start with the given symbol

    try:
        if FMP_API_KEY:
            # Try to get company name from FMP if topic is a symbol
            symbol_for_fmp = topic.upper().replace(".JK", "") # Clean for FMP (e.g., remove .JK for Indonesian stocks)
            logger.debug(f"Trying to get company profile from FMP for symbol: {symbol_for_fmp}")
            url = f"{FMP_API_URL}/profile"
            response = requests.get(
                url,
                params={"symbol": symbol_for_fmp, "apikey": FMP_API_KEY},
                timeout=FMP_PROFILE_TIMEOUT
            )
            profile_data = response.json()
            if profile_data and profile_data[0].get('companyName'):
                company_name = profile_data[0]['companyName']
                logger.info(f"Resolved symbol '{topic}' to company name: '{company_name}' using FMP.")
    except Exception as e:
        logger.warning(f"Could not get company name from FMP for '{topic}': {e}")

    logger.info(f"Attempting general news fetch for '{company_name}' / '{resolved_symbol}' from NewsAPI (stock fallback).")
    today = datetime.now()
    from_date = (today - timedelta(days=NEWS_LOOKBACK_DAYS)).strftime('%Y-%m-%d')
    
    query_stock_fallback = f'("{company_name}" OR "{resolved_symbol}")'
    url_stock_fallback = f"{NEWSAPI_URL}/everything?q={query_stock_fallback}&language=en&pageSize={limit}&sortBy=relevancy&from={from_date}&apiKey={NEWS_API_KEY}"
    
    articles = []
    try:
        response = requests.get(url_stock_fallback, timeout=DEFAULT_API_TIMEOUT)
        logger.debug(f"NewsAPI (stock fallback) response status: {response.status_code}")
        response.raise_for_status()
        articles = response.json().get("articles", [])
        logger.debug(f"NewsAPI (stock fallback) returned {len(articles)} raw articles.")

    except requests.exceptions.RequestException as req_e:
        logger.error(f"Failed to fetch from NewsAPI (stock fallback) due to request error for '{company_name}': {req_e}")
    except Exception as e:
        logger.error(f"Failed to fetch from NewsAPI (stock fallback) for '{company_name}': {e}")
    
    formatted_articles = []
    if articles and topic != 'N/A': # Apply filtering even for stock fallback
        filtered_articles = filter_news_by_topic(articles, topic, symbol)
        if not filtered_articles and articles: # Revert if filter too aggressive
            logger.info(f"Stock news fallback filtering for '{topic}' was too aggressive, reverting to unfiltered news.")
            filtered_articles = articles
        
        seen = set()
        unique_articles = []
        for article in filtered_articles:
            key = (article.get('title'), article.get('url'))
            if key not in seen:
                seen.add(key)
                unique_articles.append(article)

        for i, article in enumerate(unique_articles[:limit]):
            title = article.get('title')
            url = article.get('url')
            description = article.get('description', '') # Include description
            logger.debug(f"NewsAPI Fallback Article {i+1}: Title='{title}', URL='{url}'")
            if title and url:
                formatted_articles.append({"title": title, "description": description, "url": url})
        
    logger.debug(f"NewsAPI Fallback formatted {len(formatted_articles)} valid articles after filtering.")
    return formatted_articles


def fetch_relevant_news(topic: str, asset_type: str, symbol: str) -> list[dict]:
    """
    DEFINITIVE VERSION: Fetches news using the BEST source based on asset type.
    Passes both topic name and symbol for better relevance.
    """
    logger.info(f"Fetching news for '{topic}' (Asset Type: {asset_type}, Symbol: {symbol})")

    news = []

    if asset_type == "Stock":
        news = get_news_from_yahoo(topic) # Yahoo Finance usually works well for exact stock tickers
        if not news:
            logger.info(f"Yahoo Finance found no news for '{topic}', trying stock news fallback.")
            news = get_stock_news_fallback(topic, symbol)
    
    elif asset_type == "Crypto":
        news = get_crypto_news_from_newsapi(topic, symbol)
        
    else:
        logger.warning(f"Unknown asset type '{asset_type}', falling back to general news search for '{topic}' / '{symbol}'.")
        news = get_crypto_news_from_newsapi(topic, symbol) # Fallback to general NewsAPI for unknown type

    logger.info(f"Finished fetching news for '{topic}'. Total articles found: {len(news)}")
    return news