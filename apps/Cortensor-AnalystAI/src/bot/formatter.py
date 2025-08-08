# src/bot/formatter.py

import logging
import re
from datetime import datetime
import pytz
from thefuzz import fuzz # Digunakan untuk validasi berita
import os

logger = logging.getLogger(__name__)

def escape_html(text: str) -> str:
    """
    Escapes characters for Telegram's HTML parse_mode.
    This should be used for all text content, but not for URLs in <a href="">.
    It also removes any lingering MarkdownV2 escape characters (backslashes).
    """
    if not isinstance(text, str):
        return ''
    
    # First, remove any MarkdownV2 specific escapes (\) that might be left
    # This is crucial because HTML doesn't use them and they appear as literal \.
    cleaned_text = text.replace('\\', '') 
    
    # Remove </s> or <s> tags if present in AI output
    cleaned_text = re.sub(r'</?s>', '', cleaned_text).strip()
    
    # Escape HTML special characters
    cleaned_text = cleaned_text.replace('&', '&amp;')
    cleaned_text = cleaned_text.replace('<', '&lt;')
    cleaned_text = cleaned_text.replace('>', '&gt;')
    cleaned_text = cleaned_text.replace('"', '&quot;')
    
    return cleaned_text

def _clean_ai_output(ai_raw_text: str, news_titles_for_validation: list[str]) -> dict:
    """
    Cleans and robustly parses the raw AI output into structured opinions and key takeaway.
    Specifically designed for DeepSeek R1's common output patterns, aggressively stripping
    unwanted formatting and ensuring consistent output structure.
    """
    opinions = []
    key_takeaway_content = "" # Initialize as empty string, will be set or fallbacked

    # Remove </s> artifacts and strip leading/trailing whitespace
    cleaned_text_initial = re.sub(r'</?s>', '', ai_raw_text).strip()
    logger.debug(f"Raw AI text for parsing:\n{cleaned_text_initial[:500]}...")

    # --- Stage 1: Isolate the FINAL AI output from internal thoughts/planning ---
    final_output_start_match = re.search(r'</\s*think\s*>', cleaned_text_initial, re.IGNORECASE)
    
    if final_output_start_match:
        text_to_parse = cleaned_text_initial[final_output_start_match.end():].strip()
        logger.debug(f"Text after </think> tag for parsing:\n{text_to_parse[:500]}...")
    else:
        logger.warning("No </think> tag found in AI output. Parsing entire text as final output.")
        text_to_parse = cleaned_text_initial

    # --- Stage 2: Extract Key Takeaway (robustly) and opinions block ---
    parts = re.split(r'KEY\s*TAKEAWAY\s*[:\-]?', text_to_parse, flags=re.IGNORECASE, maxsplit=1)
    opinions_raw_text = parts[0].strip() # Text containing opinions

    if len(parts) > 1:
        takeaway_raw_text = parts[1].strip()
        # Aggressively clean any potential prefix/suffix/newlines from the raw takeaway
        takeaway_content_cleaned = re.sub(r'^(?:\[Your final one-sentence summary based on DATA FOR ANALYSIS\]|No summary was generated\.|Key Takeaway[:\-])\s*', '', takeaway_raw_text, flags=re.IGNORECASE).strip()
        takeaway_content_cleaned = re.sub(r'[\r\n]+', ' ', takeaway_content_cleaned).strip()
        takeaway_content_cleaned = re.sub(r'^\s*\*+\s*(.*?)\s*\*+\s*$', r'\1', takeaway_content_cleaned).strip() # Remove bolding if any
        
        if takeaway_content_cleaned: # Only use if not empty after cleaning
            key_takeaway_content = takeaway_content_cleaned
        else:
            key_takeaway_content = "<i>No summary was generated.</i>"
        logger.debug(f"Parsed Key Takeaway: {key_takeaway_content[:50]}...")
        
    # --- Stage 3: Extract Individual Opinions (from the opinions_raw_text block) ---
    # Aggressively remove any "Expert Opinions:" header from the opinions_raw_text
    opinions_raw_text = re.sub(r'^\s*\*+\s*Expert\s*Opinions:\s*\*+\s*|^\s*Expert\s*Opinions:', '', opinions_raw_text, flags=re.IGNORECASE | re.MULTILINE).strip()

    # Regex lebih fleksibel: dukung angka, bullet, dash, dan label opini
    opinion_block_regex = re.compile(
        r'^\s*((?:[0-9]+[.\)\-]\s*)|(?:[\u2022\*\-]\s+)|(?:Expert\s*\d+:)|(?:Bullish:|Bearish:|Neutral:|))'
        r'(.*?)(?=\n\s*(?:[0-9]+[.\)\-]\s*|[\u2022\*\-]\s+|Expert\s*\d+:|Bullish:|Bearish:|Neutral:|)|\Z)',
        re.IGNORECASE | re.MULTILINE | re.DOTALL
    )

    extracted_opinion_candidates_raw_list = []
    for match in opinion_block_regex.finditer(opinions_raw_text):
        extracted_opinion_candidates_raw_list.append(match.group(2).strip())

    # Fallback 1: Split by paragraph jika regex gagal
    if not extracted_opinion_candidates_raw_list and opinions_raw_text:
        logger.warning("Numbered opinion regex failed. Attempting paragraph-based fallback.")
        logger.warning(f"RAW OPINION TEXT: {opinions_raw_text}")
        temp_split_blocks = re.split(r'\n{2,}', opinions_raw_text)
        extracted_opinion_candidates_raw_list = [block.strip() for block in temp_split_blocks if block.strip() and len(block.split()) > 5]

    # Fallback 2: Split per baris, deteksi opini dengan kata kunci
    if not extracted_opinion_candidates_raw_list and opinions_raw_text:
        raw_lines_fallback = [line.strip() for line in opinions_raw_text.split('\n') if line.strip()]
        current_fallback_opinion_lines = []
        for line in raw_lines_fallback:
            # Deteksi awal opini dengan label/kata kunci
            if re.match(r'^(?:\[Sentiment:.*\]:|Bullish:|Neutral:|Bearish:|Expert\s*\d+:|[\u2022\*-])', line, re.IGNORECASE):
                if current_fallback_opinion_lines:
                    extracted_opinion_candidates_raw_list.append(' '.join(current_fallback_opinion_lines))
                current_fallback_opinion_lines = [line]
            else:
                current_fallback_opinion_lines.append(line)
        if current_fallback_opinion_lines:
            extracted_opinion_candidates_raw_list.append(' '.join(current_fallback_opinion_lines))

    # Fallback 3: Jika masih gagal, ambil seluruh block sebagai satu opini
    if not extracted_opinion_candidates_raw_list and opinions_raw_text:
        extracted_opinion_candidates_raw_list = [opinions_raw_text.strip()]
        
    logger.debug(f"Raw opinion candidates for final parsing: {len(extracted_opinion_candidates_raw_list)}")

    # Now, process the successfully extracted candidates into the final opinions list
    for i, op_segment_raw_text in enumerate(extracted_opinion_candidates_raw_list): # Correctly iterate over this list
        if len(opinions) >= 3: # Limit to max 3 opinions
            break

        # Bersihkan prefix kombinasi bintang, spasi, dan label di awal opini
        current_justification = op_segment_raw_text.strip()
        current_justification = re.sub(r'^[\*\s]*Opinion\s*\d+\s*:\s*(Bullish|Bearish|Neutral)?\**:?\s*', '', current_justification, flags=re.IGNORECASE).strip()
        current_justification = re.sub(r'^[\*\s]*Opinion\s*\d+\s*:\s*', '', current_justification, flags=re.IGNORECASE).strip()
        extracted_sentiment = "Neutral" # Default sentiment

        # --- Sub-parsing each candidate segment to find Sentiment and Justification ---
        # 1. Prioritize [Sentiment: X]: pattern for extraction
        sentiment_bracket_match = re.match(r'\[Sentiment:\s*(Bullish|Neutral|Bearish)\]:\s*(.*)', current_justification, re.IGNORECASE | re.DOTALL)
        if sentiment_bracket_match:
            extracted_sentiment = sentiment_bracket_match.group(1).capitalize()
            current_justification = sentiment_bracket_match.group(2).strip()
        else:
            # 2. Fallback: Try to find sentiment word at the beginning (e.g., "Bullish: Justification")
            sentiment_word_match = re.match(r'^(Bullish|Neutral|Bearish)[:–-]?\s*(.*)', current_justification, re.IGNORECASE | re.DOTALL)
            if sentiment_word_match:
                extracted_sentiment = sentiment_word_match.group(1).capitalize()
                current_justification = sentiment_word_match.group(2).strip()
            else:
                # If no clear sentiment marker at start, search for it anywhere
                sentiment_anywhere_match = re.search(r'\b(Bullish|Neutral|Bearish)\b', current_justification, re.IGNORECASE)
                if sentiment_anywhere_match:
                    extracted_sentiment = sentiment_anywhere_match.group(1).capitalize()
                
        # --- NEW: Refined logic to remove duplicated sentiment from justification ---
        # This targets patterns like "[Bullish]: Bullish: ..." or "Bullish: Bullish: ..."
        if extracted_sentiment:
            # First, try to remove "[SENTIMENT]: SENTIMENT:" or "SENTIMENT: SENTIMENT:"
            # This is to handle the specific duplication observed, e.g., "Bullish: [Bullish]:" or "Neutral: Neutral:"
            duplicated_sentiment_complex_pattern = re.compile(
                r'^\s*(?:\[Sentiment:\s*' + re.escape(extracted_sentiment) + r'\]:|\b' + re.escape(extracted_sentiment) + r')\s*[:\s–-]*\s*\b' + re.escape(extracted_sentiment) + r'\b[:\s–-]*',
                re.IGNORECASE
            )
            current_justification = duplicated_sentiment_complex_pattern.sub('', current_justification).strip()

            # Fallback: Also remove a single sentiment word or "[Sentiment]:" prefix if it somehow remains
            # This covers cases where the first regex might not catch it, or if the AI outputs something like "Bullish: Rest of justification"
            # It also helps clean any leftover "[Sentiment]:" or "Sentiment:" that wasn't part of a full duplication.
            single_sentiment_prefix_pattern = re.compile(
                r'^\s*(?:\[Sentiment:\s*' + re.escape(extracted_sentiment) + r'\]:|\b' + re.escape(extracted_sentiment) + r')[:\s–-]*',
                re.IGNORECASE
            )
            current_justification = single_sentiment_prefix_pattern.sub('', current_justification).strip()


        # Aggressively clean other prefixes that AI might still leave behind (e.g., "**Opinion N:**", "Expert N:")
        current_justification = re.sub(r'^\s*(?:[0-9]+\.\s*|[•*]\s*|\*+\s*(?:Opinion|Expert)\s*\d+:?\s*\*+\s*|(?:Opinion|Expert)\s*\d+:?\s*|\s*\[Sentiment:\s*(?:Bullish|Neutral|Bearish)\][:\-]?)', '', current_justification, flags=re.IGNORECASE).strip()
        current_justification = current_justification.strip('"') # Remove leading/trailing quotes
        current_justification = re.sub(r'[\r\n]+', ' ', current_justification).strip() # Ensure single line

        # --- News Reference Validation (CRITICAL) ---
        # Look for "News X Title" pattern and validate against provided news_titles_for_validation
        news_citation_pattern = re.compile(r'(News\s*([0-9]+)(?:\\s*Title:?"?\\s*([^"]*)"?)?)', re.IGNORECASE) 
        news_matches = list(news_citation_pattern.finditer(current_justification))
        
        for news_match in news_matches:
            full_citation_text = news_match.group(1) # The part like "News 1 Title: '...'"
            news_index = int(news_match.group(2)) # The number (e.g., 1)
            cited_news_title_raw = news_match.group(3).strip() if news_match.group(3) else "" # The title cited by AI
            
            # Check if the cited news index is within bounds and does title vaguely match?
            if 0 < news_index <= len(news_titles_for_validation):
                actual_title = news_titles_for_validation[news_index - 1]
                # If not a strong match, or very short, replace with generic text
                if cited_news_title_raw and fuzz.partial_ratio(cited_news_title_raw.lower(), actual_title.lower()) < 70:
                    logger.warning(f"AI possibly hallucinated/mis-cited news title for News {news_index}. Cited: '{cited_news_title_raw}'. Actual: '{actual_title}'. Replacing with generic news reference.")
                    current_justification = current_justification.replace(full_citation_text, f"a relevant news report (News {news_index})")
                else:
                    # If index is valid and title matches well enough or no title given, keep it as is.
                    pass # Do nothing, keep original text
            else:
                logger.warning(f"AI hallucinated News {news_index} which does not exist. Replacing with generic news reference.")
                current_justification = current_justification.replace(full_citation_text, "a relevant news report")

        # Truncate if still too long as a safeguard
        MAX_OPINION_LENGTH = 1500 # Diperpanjang sesuai permintaan
        if len(current_justification) > MAX_OPINION_LENGTH:
            current_justification = current_justification[:MAX_OPINION_LENGTH] + "..."
            logger.warning(f"Opinion truncated due to length: {current_justification[:100]}...")

        if current_justification:
            opinions.append((extracted_sentiment, current_justification)) # Store as tuple (sentiment, text)
            logger.debug(f"Parsed Opinion {len(opinions)}: Sentiment='{extracted_sentiment}', Justification='{current_justification[:50]}...'")
        else:
            logger.warning(f"Failed to extract meaningful content for opinion {i+1} from raw candidate. Candidate data: {op_segment_raw_text}") # Corrected variable name

    return {"opinions": opinions, "key_takeaway": key_takeaway_content}


def format_final_message(
    topic: str,
    ai_raw_text: str,
    market_data: dict,
    news_data: list[dict],
    price_chart_path: str = None,
    competitors: list = None,
    analysis_type: str = "manual"  # "manual" for /analyze, "scheduled" for scheduled analysis
) -> str:
    """
    Assembles the final HTML report, with fallback summary if AI omitted it.
    analysis_type: "manual" for /analyze command, "scheduled" for scheduled analysis
    """
    # Extract news titles for hallucination validation in _clean_ai_output
    news_titles_for_validation = [item['title'] for item in news_data]

    parsed = _clean_ai_output(ai_raw_text, news_titles_for_validation) # Pass news_titles_for_validation
    opinions = parsed["opinions"] # opinions is now a list of (sentiment, justification) tuples
    takeaway = parsed["key_takeaway"]

    # build fallback takeaway if missing or empty after cleaning
    if not takeaway: # Check if key_takeaway_content is empty string
        pct_30d = market_data.get('price_change_30d_pct', 0)
        pct_24h = market_data.get('price_change_24h_pct', 0)
        fallback = (f"{topic.title()}’s {pct_30d:+.2f}% monthly gain, "
                    f"despite a {pct_24h:+.2f}% 24h dip, "
                    "signals cautious bullish momentum")
        if len(news_data) > 1 and news_data[1].get('title'):
            fallback += f", supported by {news_data[1]['title']}"
        fallback += "."
        takeaway = fallback

    # escape for HTML
    escaped_topic = escape_html(topic)
    now = escape_html(datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'))
    escaped_takeaway = escape_html(takeaway) # Escape the fallback or parsed takeaway

    company_name = market_data.get('company_name', '').strip()
    ticker = market_data.get('symbol', topic.upper()).strip().upper()
    asset_type = market_data.get('type', '').strip().lower()
    # --- HEADER LABEL LOGIC ---
    if asset_type == 'crypto':
        header_label = 'Crypto'
        company_name = market_data.get('name', ticker)
    elif asset_type == 'stock':
        header_label = 'Company'
        company_name = market_data.get('company_name', '').strip()
        if not company_name or company_name.upper() == ticker:
            company_name = f"Unknown Company"
    else:
        header_label = 'Asset'
        company_name = market_data.get('company_name', ticker)
    # --- END HEADER LABEL LOGIC ---
    # Highlight sentiment with emoji
    sentiment_emoji = {
        'Bullish': '🟢',
        'Bearish': '🔴',
        'Neutral': '🟡',
    }
    final_opinions_list = []
    for i in range(3):
        if i < len(opinions):
            sent, text = opinions[i]
        else:
            sent, text = "Neutral", "No opinion generated."
        sent_html = escape_html(sent)
        text_html = escape_html(text)
        # Remove leading sentiment and "Opinion N:" or "**" from justification if duplicated
        text_html = re.sub(
            rf"^(Opinion\s*{i+1}[:\s]*)?(\*+)?\s*{sent_html}[:\s\*–-]*", "", text_html, flags=re.IGNORECASE
        ).strip()
        text_html = re.sub(r'^(?:\*+\s*)+', '', text_html).strip()
        emoji = sentiment_emoji.get(sent_html.capitalize(), '🟡')
        final_opinions_list.append(f"• <b>[Expert {i+1}]</b> – {emoji} <b>{sent_html}:</b> {text_html}")

    # Get current time in Jakarta timezone
    jakarta_tz = pytz.timezone('Asia/Jakarta')
    current_time = datetime.now(jakarta_tz)
    
    # Format date and time
    date_str = current_time.strftime('%A, %d %B %Y')  # e.g., "Thursday, 31 July 2025"
    time_str = current_time.strftime('%H:%M WIB')     # e.g., "19:30 WIB"
    
    # Create different headers based on analysis type
    if analysis_type == "scheduled":
        report_title = "📊 <b>Scheduled Analyst Report</b> 📊"
        analysis_indicator = "🤖 <i>Automated Daily Analysis</i>"
    else:  # manual analysis
        report_title = "💎 <b>Analyst Report</b> 💎"
        analysis_indicator = "👤 <i>On-Demand Analysis</i>"
    
    # Clean takeaway text
    clean_takeaway = re.sub(r'^(?:\*+\s*)+', '', escape_html(takeaway)).strip()
    
    lines = [
        report_title,
        f"📈 <b>{header_label}:</b> <code>{escape_html(company_name)}</code> (<b>{escape_html(ticker)}</b>)",
        analysis_indicator,
        f"📅 <i>{escape_html(date_str)}</i>",
        f"🕐 <i>{escape_html(time_str)}</i>",
        "",
        "━━━━━━━━━━━━━━━━━━",
        "<b>Expert Opinions:</b>",
        *final_opinions_list,
        "",
        "━━━━━━━━━━━━━━━━━━",
        "🔑 <b>Key Takeaway:</b>",
        f"<i>{clean_takeaway}</i>",
        ""
    ]

    # ...removed redundant block that referenced market_lines and summary_table before definition...

    # ...sources block will be included at the bottom of the summary table, not as a separate section...

    # News block with blank line between each news item
    lines.append("━━━━━━━━━━━━━━━━━━")
    lines.append("<b>News Summary:</b>")
    if news_data:
        for i, n in enumerate(news_data, start=1):
            if n.get('url'):
                title_html = f'<a href="{escape_html(n["url"])}">{escape_html(n["title"])} </a>'
            else:
                title_html = escape_html(n['title'])
            lines.append(f"• <b>News {i}:</b> {title_html}")
            if n.get('description'):
                lines.append(f"  <i>{escape_html(n['description'])}</i>")
            lines.append("")  # Add blank line after each news item
    else:
        lines.append("• No news provided.")
        lines.append("")

    # Disclaimer with analysis type information
    if analysis_type == "scheduled":
        disclaimer_text = (
            "<i>📊 <b>Automated Analysis:</b> This report was generated automatically by your scheduled analysis. "
            "The information is for informational purposes only and does not constitute financial advice. "
            "Please do your own research before making investment decisions.</i>"
        )
    else:  # manual analysis
        disclaimer_text = (
            "<i>👤 <b>On-Demand Analysis:</b> This report was generated in response to your analysis request. "
            "The information is for informational purposes only and does not constitute financial advice. "
            "Please do your own research before making investment decisions.</i>"
        )
    
    lines.append(disclaimer_text)
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━")
    lines.append("")

    # --- FIX SUMMARY TABLE: Only insert if not already present ---
    summary_table_str = "<b>Summary Table:</b>"
    # sources_lines removed, now handled in source table
    if not any(summary_table_str in l for l in lines):
        try:
            idx = next(i for i, l in enumerate(lines) if 'Market Analysis:' in l)
            for j in range(idx+1, len(lines)):
                if lines[j].strip() == "":
                    insert_idx = j+1
                    break
            else:
                insert_idx = idx+1
            # Build summary table based on asset type, append sources at the end
            if asset_type == 'crypto':
                summary_table = [
                    summary_table_str,
                    "<pre>Price           : ${:,.2f} USD\nChange (24h)    : {:+.2f}%\nChange (7d)     : {:+.2f}%\nChange (30d)    : {:+.2f}%\nVolume (24h)    : {:,}\nMarket Cap      : ${:,}\nCirculating Supply: {}\n24H High / Low  : ${:,} / ${:,}</pre>".format(
                        market_data.get('current_price', 0),
                        market_data.get('price_change_24h_pct', 0),
                        market_data.get('price_change_7d_pct', 0),
                        market_data.get('price_change_30d_pct', 0),
                        market_data.get('trading_volume_24h', 0),
                        market_data.get('market_cap', 0),
                        market_data.get('circulating_supply', 'N/A'),
                        int(market_data.get('high_24h', 0) or 0),
                        int(market_data.get('low_24h', 0) or 0)
                    ),
                    f"<i>Price source: {escape_html(str(market_data.get('price_source', 'N/A')))}</i>",
                    f"<i>Market Cap source: {escape_html(str(market_data.get('market_cap_source', 'N/A')))}</i>",
                    ""
                ]
            else:  # stock/company
                summary_table = [
                    summary_table_str,
                    "<pre>Price        : ${:,.2f} USD\nChange (1d)  : {:+.2f}%\nChange (7d)  : {:+.2f}%\nChange (30d) : {:+.2f}%\nVolume       : {:,}\nP/E Ratio    : {}\nEPS (TTM)    : {}\n52W High/Low : ${:,} / ${:,}\nMarket Cap   : ${:,}</pre>".format(
                        market_data.get('current_price', 0),
                        market_data.get('price_change_pct', 0),
                        market_data.get('price_change_7d_pct', 0),
                        market_data.get('price_change_30d_pct', 0),
                        market_data.get('trading_volume', 0),
                        market_data.get('pe_ratio', 'N/A'),
                        market_data.get('eps_ttm', 'N/A'),
                        int(market_data.get('high_52w', 0) or 0),
                        int(market_data.get('low_52w', 0) or 0),
                        int(market_data.get('market_cap', 0) or 0)
                    ),
                    f"<i>Price source: {escape_html(str(market_data.get('price_source', 'N/A')))}</i>",
                    f"<i>Market Cap source: {escape_html(str(market_data.get('market_cap_source', 'N/A')))}</i>",
                    ""
                ]
            lines[insert_idx:insert_idx] = summary_table
        except StopIteration:
            lines.append("")
            lines.append(summary_table_str)
            lines.append("<pre>Price        : ${:,.2f} USD\nChange (1d)  : {:+.2f}%\nChange (7d)  : {:+.2f}%\nChange (30d) : {:+.2f}%\nVolume       : {:,}\nP/E Ratio    : {}\nEPS (TTM)    : {}\n52W High/Low : ${:,} / ${:,}\nMarket Cap   : ${:,}</pre>".format(
                market_data.get('current_price', 0),
                market_data.get('price_change_pct', 0),
                market_data.get('price_change_7d_pct', 0),
                market_data.get('price_change_30d_pct', 0),
                market_data.get('trading_volume', 0),
                market_data.get('pe_ratio', 'N/A'),
                market_data.get('eps_ttm', 'N/A'),
                int(market_data.get('high_52w', 0) or 0),
                int(market_data.get('low_52w', 0) or 0),
                int(market_data.get('market_cap', 0) or 0)
            ))
            lines.append(f"<i>Price source: {escape_html(str(market_data.get('price_source', 'N/A')))}</i>")
            lines.append(f"<i>Market Cap source: {escape_html(str(market_data.get('market_cap_source', 'N/A')))}</i>")
            lines.append("")

    # --- MARKET ANALYSIS BLOCK ---
    # Remove any existing Market Analysis block to avoid duplicates
    lines = [l for l in lines if not l.strip().startswith('Market Analysis:')]
    # Insert Market Analysis at the right place (after opinions), with price/source info below
    market_lines = []
    if asset_type == 'crypto':
        market_lines.append('Market Analysis:')
        market_lines.append(f"• Current Price: ${market_data.get('current_price', 0):,.2f} USD")
        market_lines.append(f"• Price Change (24h): {market_data.get('price_change_24h_pct', 0):+.2f}%")
        market_lines.append(f"• Trading Volume (24h): ${market_data.get('trading_volume_24h', 0):,} USD")
        market_lines.append(f"• Market Cap: ${market_data.get('market_cap', 0):,} USD")
        market_lines.append(f"<i>Price source: {escape_html(str(market_data.get('price_source', 'N/A')))}</i>")
        market_lines.append(f"<i>Market Cap source: {escape_html(str(market_data.get('market_cap_source', 'N/A')))}</i>")
    else:
        market_lines.append('Market Analysis:')
        market_lines.append(f"• Current Price: ${market_data.get('current_price', 0):,.2f} USD")
        market_lines.append(f"• Price Change (today): {market_data.get('price_change_pct', 0):+.2f}%")
        market_lines.append(f"• P/E Ratio: {market_data.get('pe_ratio', 'N/A')}")
        market_lines.append(f"<i>Price source: {escape_html(str(market_data.get('price_source', 'N/A')))}</i>")
        market_lines.append(f"<i>Market Cap source: {escape_html(str(market_data.get('market_cap_source', 'N/A')))}</i>")
    # Insert after opinions
    try:
        idx = next(i for i, l in enumerate(lines) if l.strip().startswith('<b>Expert Opinions'))
        insert_idx = idx + 1
        lines[insert_idx:insert_idx] = [''] + market_lines + ['']
    except StopIteration:
        lines.extend([''] + market_lines + [''])
    # --- END MARKET ANALYSIS BLOCK ---

    # --- SUMMARY TABLE BLOCK ---
    summary_table_str = "<b>Summary Table:</b>"
    if not any(summary_table_str in l for l in lines):
        try:
            idx = next(i for i, l in enumerate(lines) if 'Market Analysis:' in l)
            for j in range(idx+1, len(lines)):
                if lines[j].strip() == "":
                    insert_idx = j+1
                    break
            else:
                insert_idx = idx+1
            if asset_type == 'crypto':
                summary_table = [
                    summary_table_str,
                    "<pre>Price           : ${:,.2f} USD\nChange (24h)    : {:+.2f}%\nChange (7d)     : {:+.2f}%\nChange (30d)    : {:+.2f}%\nVolume (24h)    : {:,}\nMarket Cap      : ${:,}\nCirculating Supply: {}\n24H High / Low  : ${:,} / ${:,}</pre>".format(
                        market_data.get('current_price', 0),
                        market_data.get('price_change_24h_pct', 0),
                        market_data.get('price_change_7d_pct', 0),
                        market_data.get('price_change_30d_pct', 0),
                        market_data.get('trading_volume_24h', 0),
                        market_data.get('market_cap', 0),
                        market_data.get('circulating_supply', 'N/A'),
                        int(market_data.get('high_24h', 0) or 0),
                        int(market_data.get('low_24h', 0) or 0)
                    ),
                    ""
                ]
            else:
                summary_table = [
                    summary_table_str,
                    "<pre>Price        : ${:,.2f} USD\nChange (1d)  : {:+.2f}%\nChange (7d)  : {:+.2f}%\nChange (30d) : {:+.2f}%\nVolume       : {:,}\nP/E Ratio    : {}\nEPS (TTM)    : {}\n52W High/Low : ${:,} / ${:,}\nMarket Cap   : ${:,}</pre>".format(
                        market_data.get('current_price', 0),
                        market_data.get('price_change_pct', 0),
                        market_data.get('price_change_7d_pct', 0),
                        market_data.get('price_change_30d_pct', 0),
                        market_data.get('trading_volume', 0),
                        market_data.get('pe_ratio', 'N/A'),
                        market_data.get('eps_ttm', 'N/A'),
                        int(market_data.get('high_52w', 0) or 0),
                        int(market_data.get('low_52w', 0) or 0),
                        int(market_data.get('market_cap', 0) or 0)
                    ),
                    ""
                ]
            lines[insert_idx:insert_idx] = summary_table
        except StopIteration:
            lines.append("")
            lines.append(summary_table_str)
            lines.append("<pre>Price        : ${:,.2f} USD\nChange (1d)  : {:+.2f}%\nChange (7d)  : {:+.2f}%\nChange (30d) : {:+.2f}%\nVolume       : {:,}\nP/E Ratio    : {}\nEPS (TTM)    : {}\n52W High/Low : ${:,} / ${:,}\nMarket Cap   : ${:,}</pre>".format(
                market_data.get('current_price', 0),
                market_data.get('price_change_pct', 0),
                market_data.get('price_change_7d_pct', 0),
                market_data.get('price_change_30d_pct', 0),
                market_data.get('trading_volume', 0),
                market_data.get('pe_ratio', 'N/A'),
                market_data.get('eps_ttm', 'N/A'),
                int(market_data.get('high_52w', 0) or 0),
                int(market_data.get('low_52w', 0) or 0),
                int(market_data.get('market_cap', 0) or 0)
            ))
            lines.append("")

    # --- HEADER LABEL LOGIC (force Bitcoin as Crypto) ---
    if ticker == 'BTC' or asset_type == 'crypto':
        header_label = 'Crypto'
        company_name = market_data.get('name', ticker)
    elif asset_type == 'stock':
        header_label = 'Company'
        company_name = market_data.get('company_name', '').strip()
        if not company_name or company_name.upper() == ticker:
            company_name = f"Unknown Company"
    else:
        header_label = 'Asset'
        company_name = market_data.get('company_name', ticker)
    lines[2] = f"📈 <b>{header_label}:</b> <code>{escape_html(company_name)}</code> (<b>{escape_html(ticker)}</b>)"

    # ...sources block now only appears at the bottom of the summary table, not as a separate section...

    # --- REMOVE DUPLICATE HEADER, DATE, AND SECTION SEPARATORS AT THE TOP ---
    def clean_header(lines):
        new_lines = []
        header_found = False
        company_found = False
        date_found = False
        separator_count = 0
        for l in lines:
            if not header_found and 'Analyst Report' in l:
                header_found = True
                new_lines.append(l)
                continue
            if not company_found and l.strip().startswith('📈'):
                company_found = True
                new_lines.append(l)
                continue
            if not date_found and l.strip().startswith('<i>') and 'UTC' in l:
                date_found = True
                new_lines.append(l)
                continue
            if l.strip() == '━━━━━━━━━━━━━━━━━━':
                if separator_count < 1:
                    separator_count += 1
                    new_lines.append(l)
                continue
            if l.strip() == '':
                if len(new_lines) == 0 or new_lines[-1].strip() == '':
                    continue  # skip extra blank lines at the top
            # Skip duplicate header lines
            if header_found and 'Analyst Report' in l:
                continue
            if company_found and l.strip().startswith('📈'):
                continue
            if date_found and l.strip().startswith('<i>') and 'UTC' in l:
                continue
            new_lines.append(l)
        return new_lines
    lines = clean_header(lines)

    # --- REMOVE ALL Market Analysis and Summary Table blocks before re-inserting ---
    def remove_blocks(lines):
        new_lines = []
        skip_market = False
        skip_summary = False
        for l in lines:
            # Remove Market Analysis block
            if l.strip().startswith('Market Analysis:'):
                skip_market = True
                continue
            if skip_market:
                if l.strip() == '' or l.strip().startswith('<b>Summary Table:'):
                    skip_market = False
                continue
            # Remove Summary Table block
            if l.strip().startswith('<b>Summary Table:') or l.strip().startswith('Summary Table:'):
                skip_summary = True
                continue
            if skip_summary:
                if l.strip() == '':
                    skip_summary = False
                continue
            new_lines.append(l)
        return new_lines
    lines = remove_blocks(lines)

    # Now re-insert Market Analysis and Summary Table after Key Takeaway
    market_lines = []
    if asset_type == 'crypto':
        market_lines.append('Market Analysis:')
        market_lines.append(f"• Current Price: ${market_data.get('current_price', 0):,.2f} USD")
        market_lines.append(f"• Price Change (24h): {market_data.get('price_change_24h_pct', 0):+.2f}%")
        market_lines.append(f"• Trading Volume (24h): ${market_data.get('trading_volume_24h', 0):,} USD")
        market_lines.append(f"• Market Cap: ${market_data.get('market_cap', 0):,} USD")
        market_lines.append(f"<i>Price source: {escape_html(str(market_data.get('price_source', 'N/A')))}</i>")
        market_lines.append(f"<i>Market Cap source: {escape_html(str(market_data.get('market_cap_source', 'N/A')))}</i>")
    else:
        market_lines.append('Market Analysis:')
        market_lines.append(f"• Current Price: ${market_data.get('current_price', 0):,.2f} USD")
        market_lines.append(f"• Price Change (today): {market_data.get('price_change_pct', 0):+.2f}%")
        market_lines.append(f"• P/E Ratio: {market_data.get('pe_ratio', 'N/A')}")
        market_lines.append(f"<i>Price source: {escape_html(str(market_data.get('price_source', 'N/A')))}</i>")
        market_lines.append(f"<i>Market Cap source: {escape_html(str(market_data.get('market_cap_source', 'N/A')))}</i>")
    summary_table_str = "<b>Summary Table:</b>"
    if asset_type == 'crypto':
        summary_table = [
            summary_table_str,
            "<pre>Price           : ${:,.2f} USD\nChange (24h)    : {:+.2f}%\nChange (7d)     : {:+.2f}%\nChange (30d)    : {:+.2f}%\nVolume (24h)    : {:,}\nMarket Cap      : ${:,}\nCirculating Supply: {}\n24H High / Low  : ${:,} / ${:,}</pre>".format(
                market_data.get('current_price', 0),
                market_data.get('price_change_24h_pct', 0),
                market_data.get('price_change_7d_pct', 0),
                market_data.get('price_change_30d_pct', 0),
                market_data.get('trading_volume_24h', 0),
                market_data.get('market_cap', 0),
                market_data.get('circulating_supply', 'N/A'),
                int(market_data.get('high_24h', 0) or 0),
                int(market_data.get('low_24h', 0) or 0)
            ),
            ""
        ]
    else:
        summary_table = [
            summary_table_str,
            "<pre>Price        : ${:,.2f} USD\nChange (1d)  : {:+.2f}%\nChange (7d)  : {:+.2f}%\nChange (30d) : {:+.2f}%\nVolume       : {:,}\nP/E Ratio    : {}\nEPS (TTM)    : {}\n52W High/Low : ${:,} / ${:,}\nMarket Cap   : ${:,}</pre>".format(
                market_data.get('current_price', 0),
                market_data.get('price_change_pct', 0),
                market_data.get('price_change_7d_pct', 0),
                market_data.get('price_change_30d_pct', 0),
                market_data.get('trading_volume', 0),
                market_data.get('pe_ratio', 'N/A'),
                market_data.get('eps_ttm', 'N/A'),
                int(market_data.get('high_52w', 0) or 0),
                int(market_data.get('low_52w', 0) or 0),
                int(market_data.get('market_cap', 0) or 0)
            ),
            f"<i>Price source: {escape_html(str(market_data.get('price_source', 'N/A')))}</i>",
            f"<i>Market Cap source: {escape_html(str(market_data.get('market_cap_source', 'N/A')))}</i>",
            ""
        ]
    # Insert after Key Takeaway
    try:
        idx = next(i for i, l in enumerate(lines) if l.strip().startswith('🔑 <b>Key Takeaway:'))
        insert_idx = idx + 2
        lines[insert_idx:insert_idx] = ['━━━━━━━━━━━━━━━━━━', ''] + market_lines + ['', '━━━━━━━━━━━━━━━━━━', ''] + summary_table
    except StopIteration:
        lines.extend(['━━━━━━━━━━━━━━━━━━', ''] + market_lines + ['', '━━━━━━━━━━━━━━━━━━', ''] + summary_table)

    # Remove any queue/acknowledgement message from the lines list before joining
    def is_queue_line(l):
        return (
            l.strip().startswith('✅ Request Acknowledged') or
            l.strip().startswith('Your analysis for') or
            l.strip().startswith('Request ID:') or
            l.strip().startswith('The final report will be sent as a new message upon completion')
        )
    lines = [l for l in lines if not is_queue_line(l)]

    # --- PROFESSIONAL SPACING & POLISH ---
    # 1. Add blank line before Disclaimer if not present
    for i, l in enumerate(lines):
        if l.strip().startswith('<i>Disclaimer:') and i > 0 and lines[i-1].strip() != '':
            lines.insert(i, '')
            break
    # 2. Add blank line before News Summary if not present
    for i, l in enumerate(lines):
        if l.strip().startswith('<b>News Summary:') and i > 0 and lines[i-1].strip() != '':
            lines.insert(i, '')
            break
    # 3. Add blank line after Summary Table if not present
    for i, l in enumerate(lines):
        if l.strip().startswith('<b>Summary Table:'):
            # Find the end of the summary table block
            for j in range(i+1, len(lines)):
                if lines[j].strip() == '' and (j+1 >= len(lines) or lines[j+1].strip() != ''):
                    break
                if lines[j].strip() == '' and (j+1 < len(lines) and lines[j+1].strip() == ''):
                    # Remove extra blank lines
                    del lines[j+1]
                    break
            else:
                # If no blank line after, add one
                lines.insert(i+2, '')
            break
    # 4. Add blank line after News Summary block if not present
    for i, l in enumerate(lines):
        if l.strip().startswith('<b>News Summary:'):
            # Find the end of the news block (next separator or disclaimer)
            for j in range(i+1, len(lines)):
                if lines[j].strip() == '━━━━━━━━━━━━━━━━━━' or lines[j].strip().startswith('<i>Disclaimer:'):
                    if lines[j-1].strip() != '':
                        lines.insert(j, '')
                    break
            break
    # 5. Add blank line after Disclaimer if not present
    for i, l in enumerate(lines):
        if l.strip().startswith('<i>Disclaimer:'):
            if i+1 < len(lines) and lines[i+1].strip() != '':
                lines.insert(i+1, '')
            break
    # 6. Remove double blank lines
    i = 1
    while i < len(lines):
        if lines[i] == '' and lines[i-1] == '':
            del lines[i]
        else:
            i += 1
    # 7. Add blank line after header separator for clarity
    for i, l in enumerate(lines):
        if l.strip() == '━━━━━━━━━━━━━━━━━━' and i < 3:
            if i+1 < len(lines) and lines[i+1].strip() != '':
                lines.insert(i+1, '')
            break
    # 8. Remove trailing blank lines
    while lines and lines[-1] == '':
        lines.pop()

    result = '\n'.join(lines).strip()
    if not result:
        result = '[ERROR] Analyst report is empty. Please check input data and formatter logic.'
    return result