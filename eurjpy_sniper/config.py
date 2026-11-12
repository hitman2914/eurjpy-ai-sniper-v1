import os
from dotenv import load_dotenv
load_dotenv()
SYMBOL='EUR/JPY'
INTERVAL='1min'
API_KEY=os.getenv('TWELVE_DATA_API_KEY','').strip()
PAPER_STAKE=float(os.getenv('PAPER_STAKE','10'))
MIN_SIGNAL_SCORE=int(os.getenv('MIN_SIGNAL_SCORE','80'))
