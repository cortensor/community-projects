# src/core/prompt_builder.py

def build_analyst_prompt(market_data: dict, news_data: list[dict]) -> str:
    """
    Builds a DeepSeek R1–compatible prompt for zero‑hallucination, strict sentiment alignment,
    and English‑only expert analysis.
    """
    def safe_text(value, default=''):
        if isinstance(value, str):
            return value
        if value is None:
            return default
        return str(value)

    def safe_float(value, default=0.0):
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = value.replace(',', '').strip()
            if not cleaned:
                return default
            try:
                return float(cleaned)
            except ValueError:
                return default
        return default

    asset_type_raw = market_data.get('type')
    asset_type = safe_text(asset_type_raw, 'Asset').strip() or 'Asset'

    asset_name_source = (
        market_data.get('name')
        or market_data.get('company_name')
        or market_data.get('symbol')
        or 'N/A'
    )
    asset_name = safe_text(asset_name_source, 'N/A').strip() or 'N/A'

    # Market Data block
    summary = [f"## MARKET DATA for {asset_name.upper()} ({asset_type.upper()}):"]
    if asset_type.lower() == "crypto":
        current_price = safe_float(market_data.get('current_price'))
        change_24h = safe_float(market_data.get('price_change_24h_pct'))
        change_7d = safe_float(market_data.get('price_change_7d_pct'))
        change_30d = safe_float(market_data.get('price_change_30d_pct'))
        volume_24h = safe_float(market_data.get('trading_volume_24h'))
        market_cap = safe_float(market_data.get('market_cap'))

        summary += [
            f"- Current Price: ${current_price:,.2f} USD",
            f"- 24h Change: {change_24h:+.2f}%",
            f"- 7d Change: {change_7d:+.2f}%",
            f"- 30d Change: {change_30d:+.2f}%",
            f"- 24h Volume: ${volume_24h:,.0f} USD",
            f"- Market Cap: ${market_cap:,.0f} USD"
        ]
    else: # Stock type
        current_price = safe_float(market_data.get('current_price'))
        price_change_pct = safe_float(market_data.get('price_change_pct'))
        change_7d = safe_float(market_data.get('price_change_7d_pct'))
        change_30d = safe_float(market_data.get('price_change_30d_pct'))
        trading_volume = safe_float(market_data.get('trading_volume'))
        market_cap = safe_float(market_data.get('market_cap'))

        pe_ratio_value = safe_text(market_data.get('pe_ratio'))
        eps_value = safe_text(market_data.get('eps_ttm'))

        try:
            pe_ratio_display = f"{float(pe_ratio_value):.2f}"
        except (TypeError, ValueError):
            pe_ratio_display = pe_ratio_value.strip() if pe_ratio_value and pe_ratio_value.strip() else 'N/A'

        try:
            eps_display = f"{float(eps_value):.2f}"
        except (TypeError, ValueError):
            eps_display = eps_value.strip() if eps_value and eps_value.strip() else 'N/A'

        summary += [
            f"- Current Price: ${current_price:,.2f} USD",
            f"- Today’s Change: {price_change_pct:+.2f}%",
            f"- 7d Change: {change_7d:+.2f}%",
            f"- 30d Change: {change_30d:+.2f}%",
            f"- Volume Today: {trading_volume:,.0f} shares",
            f"- Market Cap: ${market_cap:,.0f} USD",
            f"- P/E Ratio: {pe_ratio_display}",
            f"- EPS (TTM): {eps_display}"
        ]

    # News block
    if news_data:
        news_lines = ["## NEWS SUMMARY (for reference):"]
        for i, n in enumerate(news_data, start=1):
            news_lines.append(f"- News {i}: {n['title']}")
            if n.get('description'):
                news_lines.append(f"  Description: {n['description']}")
        news_instruction = (
            "You may reference news by its label (News 1, News 2, etc.). "
            "Cite “News [#]” when using an insight."
        )
    else:
        news_lines = ["## NEWS SUMMARY: No news provided."]
        news_instruction = "You MUST base all opinions solely on the market data above."

    prompt = f"""
ROLE: You are a DeepSeek R1 financial analyst. Produce factual, concise English-only analysis.
Do NOT hallucinate. Use ONLY the provided DATA and NEWS.

TASK:
1) Generate EXACTLY THREE distinct expert opinions.
2) Generate EXACTLY ONE final key takeaway sentence.

{chr(10).join(summary)}

{chr(10).join(news_lines)}

RULES FOR OPINIONS:
- Language: English only.
- Quantity: Exactly three unique opinions.
- Data exclusivity: Do NOT use or invent any external information.
- Citation: Quote data points verbatim (e.g. “+2.34%”, “$180.34 USD”). If using news, cite “News [#]”.
- Sentiment alignment:
  • Positive change (+X%): Bullish or Neutral. The justification must not repeat the sentiment word.
  • Negative change (–X%): Neutral or Bearish. The justification must not repeat the sentiment word.
  • Mixed periods: Sentiment should reflect the most recent data period cited. The justification must not repeat the sentiment word.
- {news_instruction}

RULES FOR KEY TAKEAWAY:
- Language: English only.
- Exactly one concise sentence.
- Summarize the overall sentiment and drivers from your opinions.
- Do NOT introduce any new facts or numbers.

OUTPUT FORMAT:
Opinion 1: [Sentiment]: [Justification citing data/news]
Opinion 2: [Sentiment]: [Justification citing data/news]
Opinion 3: [Sentiment]: [Justification citing data/news]
Key Takeaway: [One-sentence summary]

Begin.
"""
    return prompt