# Contoh sumber data
PRICE_SOURCE = "CoinGecko API"
MARKET_CAP_SOURCE = "CoinGecko API"

# Contoh inisialisasi variabel price dan market_cap
price = 0  # Ganti dengan logika pengambilan harga sebenarnya
market_cap = 0  # Ganti dengan logika pengambilan market cap sebenarnya

def get_price():
    # ...existing code...
    # return price, source
    return price, PRICE_SOURCE

def get_market_cap():
    # ...existing code...
    # return market_cap, source
    return market_cap, MARKET_CAP_SOURCE

def display_data():
    price, price_source = get_price()
    market_cap, market_cap_source = get_market_cap()
    print(f"Harga: {price} (Sumber: {price_source})")
    print(f"Market Cap: {market_cap} (Sumber: {market_cap_source})")
    # Contoh penggunaan repr jika ingin menampilkan objek
    print("Harga:", repr(price))
    print("Market Cap:", repr(market_cap))