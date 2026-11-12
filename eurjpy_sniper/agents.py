from .strategies import evaluate_strategies
from .config import PAIR


def decide(x, threshold=80):
    c = x.iloc[-1]
    ss = evaluate_strategies(x)
    votes = [s['side'] for s in ss if s['side'] in ('CALL', 'PUT')]
    a, b = votes.count('CALL'), votes.count('PUT')
    direction = 'CALL' if a > b else 'PUT' if b > a else 'WAIT'
    trend = 'CALL' if c.ema20 > c.ema50 > c.ema200 else 'PUT' if c.ema20 < c.ema50 < c.ema200 else 'NEUTRAL'
    mom = 'CALL' if c.rsi >= 52 and c.macd > c.macd_signal else 'PUT' if c.rsi <= 48 and c.macd < c.macd_signal else 'NEUTRAL'
    hist = x.atr.tail(100).dropna()
    vol = len(hist) >= 20 and c.atr > 0 and c.atr <= hist.quantile(.90)
    score = min(100, 40 + max(a, b) * 12 + (8 if direction == trend else 0) + (8 if direction == mom else 0) + (8 if vol else 0))
    ok = max(a, b) >= 2 and (direction == trend or direction == mom) and vol
    reasons = [
        f'Market Scout: {PAIR} completed 1m candle {x.index[-1]}',
        f'Trend Agent: {trend}',
        f'Momentum Agent: {mom}; RSI {c.rsi:.1f}',
        'Price Action Agent: breakout and sweep/rejection checks completed',
        f'Strategy Selector: {a} CALL / {b} PUT votes',
        'Confirmation Agent: volatility ' + ('within recent range' if vol else 'not qualified'),
        'Risk Agent: paper-only; no real execution'
    ]
    return {
        'signal': direction if ok and score >= threshold else 'WAIT',
        'candidate': direction,
        'score': int(score),
        'strategies': ss,
        'reasons': reasons,
        'price': float(c.close),
        'rsi': float(c.rsi),
        'adx': float(c.adx),
        'updated': str(x.index[-1])
    }
