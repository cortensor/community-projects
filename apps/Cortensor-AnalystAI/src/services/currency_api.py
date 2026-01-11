# src/services/currency_api.py

"""
Real-time Currency Exchange Rate Service
Provides accurate exchange rates with caching to reduce API calls.
"""

import logging
import time
import requests
from typing import Optional

from src.config import EXCHANGE_RATE_API_URL, EXCHANGE_RATE_CACHE_DURATION, DEFAULT_API_TIMEOUT

logger = logging.getLogger(__name__)

# Cache configuration
_exchange_rate_cache = {
    'rates': {},
    'timestamp': 0,
    'base_currency': 'USD'
}
CACHE_DURATION_SECONDS = EXCHANGE_RATE_CACHE_DURATION


# --- Fallback rates (updated Jan 2026 approximations) ---
# Used when API is unavailable
FALLBACK_RATES = {
    'USD': 1.0,
    'IDR': 16200.0,  # Updated from 15000
    'EUR': 0.92,     # Updated from 0.85
    'JPY': 157.0,    # Updated from 110
    'GBP': 0.79,
    'SGD': 1.35,
    'AUD': 1.58,
    'CAD': 1.44,
    'CNY': 7.30,
    'KRW': 1450.0,
    'INR': 85.0,
    'BTC': 0.000011,  # Approximate for crypto
    'ETH': 0.00028,   # Approximate for crypto
}


def get_exchange_rates(base_currency: str = 'USD', force_refresh: bool = False) -> dict:
    """
    Fetch exchange rates from API with caching.
    
    Args:
        base_currency: The base currency for rates (default: USD)
        force_refresh: Force refresh from API, ignoring cache
        
    Returns:
        dict: Dictionary of currency codes to exchange rates
    """
    global _exchange_rate_cache
    
    current_time = time.time()
    cache_valid = (
        not force_refresh and
        _exchange_rate_cache['rates'] and
        _exchange_rate_cache['base_currency'] == base_currency and
        (current_time - _exchange_rate_cache['timestamp']) < CACHE_DURATION_SECONDS
    )
    
    if cache_valid:
        logger.debug(f"Using cached exchange rates (age: {int(current_time - _exchange_rate_cache['timestamp'])}s)")
        return _exchange_rate_cache['rates']
    
    try:
        logger.info(f"Fetching fresh exchange rates for base currency: {base_currency}")
        response = requests.get(
            f"{EXCHANGE_RATE_API_URL}/{base_currency}",
            timeout=DEFAULT_API_TIMEOUT
        )
        response.raise_for_status()
        
        data = response.json()
        rates = data.get('rates', {})
        
        if rates:
            # Update cache
            _exchange_rate_cache = {
                'rates': rates,
                'timestamp': current_time,
                'base_currency': base_currency
            }
            logger.info(f"Exchange rates updated successfully. {len(rates)} currencies available.")
            return rates
        else:
            logger.warning("API returned empty rates, using fallback")
            return FALLBACK_RATES
            
    except requests.exceptions.RequestException as e:
        logger.warning(f"Failed to fetch exchange rates from API: {e}. Using fallback rates.")
        return FALLBACK_RATES
    except Exception as e:
        logger.error(f"Unexpected error fetching exchange rates: {e}. Using fallback rates.")
        return FALLBACK_RATES


def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str = 'USD'
) -> Optional[float]:
    """
    Convert amount from one currency to another.
    
    Args:
        amount: The amount to convert
        from_currency: Source currency code (e.g., 'IDR', 'EUR')
        to_currency: Target currency code (default: 'USD')
        
    Returns:
        float: Converted amount, or None if conversion fails
    """
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()
    
    if from_currency == to_currency:
        return amount
    
    try:
        # Get rates with USD as base
        rates = get_exchange_rates('USD')
        
        # Convert from source currency to USD first
        if from_currency == 'USD':
            amount_in_usd = amount
        elif from_currency in rates:
            amount_in_usd = amount / rates[from_currency]
        else:
            logger.warning(f"Unknown source currency: {from_currency}")
            return None
        
        # Convert from USD to target currency
        if to_currency == 'USD':
            return amount_in_usd
        elif to_currency in rates:
            return amount_in_usd * rates[to_currency]
        else:
            logger.warning(f"Unknown target currency: {to_currency}")
            return None
            
    except Exception as e:
        logger.error(f"Currency conversion error: {e}")
        return None


def get_conversion_rate(from_currency: str, to_currency: str = 'USD') -> Optional[float]:
    """
    Get the conversion rate between two currencies.
    
    Args:
        from_currency: Source currency code
        to_currency: Target currency code (default: 'USD')
        
    Returns:
        float: Conversion rate (multiply by this to convert), or None if unavailable
    """
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()
    
    if from_currency == to_currency:
        return 1.0
    
    try:
        rates = get_exchange_rates('USD')
        
        if from_currency == 'USD':
            from_rate = 1.0
        elif from_currency in rates:
            from_rate = rates[from_currency]
        else:
            return None
            
        if to_currency == 'USD':
            to_rate = 1.0
        elif to_currency in rates:
            to_rate = rates[to_currency]
        else:
            return None
        
        # Rate to multiply: (to_rate / from_rate)
        return to_rate / from_rate
        
    except Exception as e:
        logger.error(f"Error getting conversion rate: {e}")
        return None


def format_currency(amount: float, currency: str, include_symbol: bool = True) -> str:
    """
    Format amount with proper currency symbol and formatting.
    
    Args:
        amount: The amount to format
        currency: Currency code
        include_symbol: Whether to include currency symbol
        
    Returns:
        str: Formatted currency string
    """
    currency = currency.upper()
    
    currency_config = {
        'USD': {'symbol': '$', 'decimals': 2, 'position': 'before'},
        'EUR': {'symbol': '€', 'decimals': 2, 'position': 'before'},
        'GBP': {'symbol': '£', 'decimals': 2, 'position': 'before'},
        'JPY': {'symbol': '¥', 'decimals': 0, 'position': 'before'},
        'IDR': {'symbol': 'Rp', 'decimals': 0, 'position': 'before'},
        'SGD': {'symbol': 'S$', 'decimals': 2, 'position': 'before'},
        'AUD': {'symbol': 'A$', 'decimals': 2, 'position': 'before'},
        'CAD': {'symbol': 'C$', 'decimals': 2, 'position': 'before'},
        'CNY': {'symbol': '¥', 'decimals': 2, 'position': 'before'},
        'KRW': {'symbol': '₩', 'decimals': 0, 'position': 'before'},
        'INR': {'symbol': '₹', 'decimals': 2, 'position': 'before'},
    }
    
    config = currency_config.get(currency, {'symbol': currency, 'decimals': 2, 'position': 'after'})
    
    # Format the number
    if config['decimals'] == 0:
        formatted_amount = f"{amount:,.0f}"
    else:
        formatted_amount = f"{amount:,.{config['decimals']}f}"
    
    if not include_symbol:
        return formatted_amount
    
    # Add symbol
    if config['position'] == 'before':
        return f"{config['symbol']}{formatted_amount}"
    else:
        return f"{formatted_amount} {config['symbol']}"


def get_supported_currencies() -> list:
    """
    Get list of supported currencies.
    
    Returns:
        list: List of supported currency codes
    """
    return list(FALLBACK_RATES.keys())


def clear_rate_cache():
    """Clear the exchange rate cache to force fresh fetch."""
    global _exchange_rate_cache
    _exchange_rate_cache = {
        'rates': {},
        'timestamp': 0,
        'base_currency': 'USD'
    }
    logger.info("Exchange rate cache cleared")
