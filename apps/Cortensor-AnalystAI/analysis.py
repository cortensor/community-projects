import matplotlib.pyplot as plt
import pandas as pd
import os

def visualize_price(data, output_path="price_chart.png"):
    """
    Visualisasi grafik harga dan tabel ringkas.
    data: DataFrame dengan kolom 'date' dan 'price'
    """
    # Grafik harga
    plt.figure(figsize=(10,5))
    plt.plot(data['date'], data['price'], marker='o')
    plt.title('Price Chart')
    plt.xlabel('Date')
    plt.ylabel('Price (USD)')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    summary = data['price'].describe()
    return summary, output_path

def analyze_data(df):
    # ...existing code analisis data...
    summary, chart_path = visualize_price(df)
    result = {
        # ...existing code...
        "price_summary": summary.to_dict(),
        "price_chart_path": os.path.abspath(chart_path)
    }
    return result

def format_report(result):
    # ...existing code...
    report = f"""
💎 Analyst Report 💎
━━━━━━━━━━━━━━━━━━
📈 Topic: {result.get('topic', '-')}
{result.get('datetime', '')}

Expert Opinions:
{result.get('expert_opinions', '')}

🔑 Key Takeaway:
{result.get('key_takeaway', '')}

━━━━━━━━━━━━━━━━━━
Market Analysis:
• Current Price: {result.get('current_price', '-')}
• Price Change (24h): {result.get('price_change_24h', '-')}
• Price Change (7d): {result.get('price_change_7d', '-')}
• Price Change (30d): {result.get('price_change_30d', '-')}
• Trading Volume (24h): {result.get('trading_volume_24h', '-')}
• Market Cap: {result.get('market_cap', '-')}
Price source: CoinGecko, Market Cap source: CoinGecko

"""
    # Sisipkan grafik harga jika ada
    if "price_chart_path" in result and os.path.exists(result["price_chart_path"]):
        report += f"\n[Price Chart Image saved at: {result['price_chart_path']}]\n"
        # Jika digunakan di web/bot, lampirkan atau embed file ini secara eksplisit.
    # Sisipkan tabel ringkas harga jika ada
    if "price_summary" in result:
        report += "\nPrice Summary Table:\n"
        for k, v in result["price_summary"].items():
            report += f"• {k}: {v}\n"
    # ...existing code untuk news summary...
    report += "\nNews Summary:\n"
    report += result.get('news_summary', '')
    # Disclaimer di akhir
    report += "\n\n━━━━━━━━━━━━━━━━━━\nDisclaimer: This report is for informational purposes only and does not constitute financial advice. Please do your own research before making investment decisions."
    return report

# Contoh penggunaan:
# df = pd.read_csv('data_harga.csv')
# visualize_price(df)