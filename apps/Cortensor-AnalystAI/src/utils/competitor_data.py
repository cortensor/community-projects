# Simple competitor data for demonstration
COMPETITORS = {
    'NVDA': [
        {'symbol': 'AMD', 'name': 'Advanced Micro Devices', 'summary': 'AMD is a major competitor in GPUs and CPUs, with strong growth in data center and gaming segments.'},
        {'symbol': 'INTC', 'name': 'Intel Corporation', 'summary': 'Intel is a global leader in semiconductors, focusing on CPUs, data centers, and AI hardware.'}
    ],
    # Add more symbols and their competitors here
}

def get_competitor_summaries(main_symbol):
    comps = COMPETITORS.get(main_symbol.upper(), [])
    return comps
