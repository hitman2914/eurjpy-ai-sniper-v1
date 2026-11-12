import os
from dotenv import load_dotenv

load_dotenv()

# Central paper dashboard: EUR/JPY plus 20 additional FX pairs.
SUPPORTED_PAIRS = {
    'EUR/JPY', 'CAD/JPY', 'GBP/JPY', 'GBP/AUD', 'CHF/JPY',
    'EUR/CHF', 'USD/JPY', 'GBP/USD', 'USD/CHF', 'USD/CAD',
    'GBP/CAD', 'AUD/CHF', 'GBP/CHF', 'EUR/AUD', 'AUD/CAD',
    'EUR/CAD', 'AUD/JPY', 'EUR/USD', 'CAD/CHF', 'EUR/GBP',
    'AUD/USD'
}

PAIR = os.getenv('PAIR', 'EUR/JPY').strip().upper().replace('-', '/')
if PAIR not in SUPPORTED_PAIRS:
    raise ValueError(f"Unsupported PAIR={PAIR!r}. Choose one of: {', '.join(sorted(SUPPORTED_PAIRS))}")

SYMBOL = PAIR
BOT_NAME = PAIR.replace('/', '') + ' AI SNIPER'
INTERVAL = '1min'
API_KEY = os.getenv('TWELVE_DATA_API_KEY', '').strip()
PAPER_STAKE = float(os.getenv('PAPER_STAKE', '10'))
MIN_SIGNAL_SCORE = int(os.getenv('MIN_SIGNAL_SCORE', '80'))
