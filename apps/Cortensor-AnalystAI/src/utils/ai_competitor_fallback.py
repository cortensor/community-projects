import requests
import os

def get_ai_competitors(symbol: str, name: str = None, max_competitors: int = 3) -> list:
    """
    Query Cortensor API to get a list of main competitors for a given stock symbol.
    Returns a list of dicts: [{'symbol': ..., 'name': ..., 'summary': ...}, ...]
    """
    cortensor_url = os.getenv('CORTENSOR_API_URL', 'http://localhost:8000/v1/completions')
    cortensor_key = os.getenv('CORTENSOR_API_KEY')
    if not cortensor_url:
        return []
    prompt = f"List the top {max_competitors} main competitors for the stock {symbol}{' ('+name+')' if name else ''} with a brief description for each. Format: SYMBOL (Name): summary."
    headers = {
        'Content-Type': 'application/json',
    }
    if cortensor_key:
        headers['Authorization'] = f'Bearer {cortensor_key}'
    data = {
        "model": "cortensor-chat",
        "messages": [
            {"role": "system", "content": "You are a financial market analyst."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 8000,
        "temperature": 0.5
    }
    try:
        resp = requests.post(cortensor_url, headers=headers, json=data, timeout=10)
        resp.raise_for_status()
        content = resp.json().get('choices', [{}])[0].get('message', {}).get('content', '')
        # Parse AI response
        competitors = []
        for line in content.split('\n'):
            line = line.strip()
            if not line or ':' not in line:
                continue
            # Example: AMD (Advanced Micro Devices): summary
            try:
                left, summary = line.split(':', 1)
                if '(' in left and ')' in left:
                    symbol_part, name_part = left.split('(', 1)
                    symbol = symbol_part.strip()
                    name = name_part.strip(') ').strip()
                else:
                    symbol = left.strip()
                    name = ''
                competitors.append({
                    'symbol': symbol,
                    'name': name,
                    'summary': summary.strip()
                })
            except Exception:
                continue
        return competitors[:max_competitors]
    except Exception as e:
        return []
