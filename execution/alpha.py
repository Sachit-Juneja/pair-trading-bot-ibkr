import numpy as np
import pandas as pd
from collections import deque
import logging

logger = logging.getLogger(__name__)

class AlphaModel:
    """
    The brain of the operation. Calculates spreads and Z-scores.
    Logic: Z = (Spread - mean) / std. Simple, yet effective (hopefully).
    """
    def __init__(self, ticker_a, ticker_b, beta, window=60):
        self.ticker_a = ticker_a
        self.ticker_b = ticker_b
        self.beta = beta
        self.window = window
        self.prices_a = deque(maxlen=window)
        self.prices_b = deque(maxlen=window)
        self.spreads = deque(maxlen=window)

    def update_prices(self, price_a=None, price_b=None):
        """
        Updates the price buffers. If one is missing, we just wait.
        """
        if price_a: self.prices_a.append(price_a)
        if price_b: self.prices_b.append(price_b)
        
        # We need both prices at the same time to calculate a new spread point
        # This is a simplified version; in reality, you'd align timestamps.
        if len(self.prices_a) == len(self.prices_b) and price_a and price_b:
            spread = price_a - (self.beta * price_b)
            self.spreads.append(spread)

    def calculate_z_score(self):
        """
        Calculates the current Z-score.
        """
        if len(self.spreads) < self.window:
            return None # Not enough data to be statistically relevant
            
        spread_arr = np.array(self.spreads)
        mean = np.mean(spread_arr)
        std = np.std(spread_arr)
        
        if std == 0:
            return 0
            
        current_spread = spread_arr[-1]
        z_score = (current_spread - mean) / std
        return z_score

    def get_signal(self, entry_threshold=2.0, exit_threshold=0.5):
        """
        Entry/Exit logic based on Z-score.
        Returns: 1 (Long spread), -1 (Short spread), 0 (Flat), None (No signal/Insufficient data)
        """
        z = self.calculate_z_score()
        if z is None:
            return None
            
        if z > entry_threshold:
            return -1 # Short the spread
        elif z < -entry_threshold:
            return 1 # Long the spread
        elif abs(z) < exit_threshold:
            return 0 # Exit
            
        return None # Hold current position or stay out
