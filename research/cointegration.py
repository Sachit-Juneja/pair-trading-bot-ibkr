import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller
from scipy.optimize import minimize
import logging

logger = logging.getLogger(__name__)

class CointegrationAnalyzer:
    """
    The math wizard that decides if two stocks are actually soulmates or just flirting.
    """
    
    @staticmethod
    def calculate_ssd(p1, p2):
        """
        Sum of Squared Differences on normalized prices.
        """
        # Normalize to 1.0 at start
        s1 = p1 / p1.iloc[0]
        s2 = p2 / p2.iloc[0]
        return np.sum((s1 - s2) ** 2)

    @staticmethod
    def test_cointegration(p1, p2):
        """
        OLS: p1 = alpha + beta * p2 + epsilon
        Then test epsilon for stationarity using ADF.
        """
        X = sm.add_constant(p2)
        model = sm.OLS(p1, X).fit()
        beta = model.params.iloc[1]
        alpha = model.params.iloc[0]
        residuals = model.resid
        
        # ADF Test
        adf_result = adfuller(residuals)
        adf_stat = adf_result[0]
        p_value = adf_result[1]
        
        return {
            'beta': beta,
            'alpha': alpha,
            'adf_stat': adf_stat,
            'p_value': p_value,
            'residuals': residuals
        }

    @staticmethod
    def calculate_hurst(ts):
        """
        Hurst Exponent. H < 0.5 means mean-reverting. 
        If H > 0.5, it's trending and we're in trouble.
        """
        lags = range(2, 20)
        tau = [np.sqrt(np.std(np.subtract(ts[lag:], ts[:-lag]))) for lag in lags]
        poly = np.polyfit(np.log(lags), np.log(tau), 1)
        return poly[0] * 2.0

    @staticmethod
    def calculate_half_life(ts):
        """
        Ornstein-Uhlenbeck process half-life.
        λ is the speed of mean reversion. Half-life = ln(2) / λ.
        """
        ts_lag = ts.shift(1)
        ts_diff = ts - ts_lag
        ts_lag = ts_lag.dropna()
        ts_diff = ts_diff.dropna()
        
        # Regress delta_y on y_lag
        X = sm.add_constant(ts_lag)
        model = sm.OLS(ts_diff, X).fit()
        lambda_val = -model.params.iloc[1] # Speed of reversion
        
        if lambda_val <= 0:
            return np.inf # Not mean reverting
            
        half_life = np.log(2) / lambda_val
        return half_life

    def analyze_pair(self, p1, p2):
        """
        Full suite of tests for a potential pair.
        """
        coint_res = self.test_cointegration(p1, p2)
        
        # If not cointegrated (p > 0.05), don't waste more CPU cycles
        if coint_res['p_value'] > 0.05:
            return None
            
        hurst = self.calculate_hurst(coint_res['residuals'])
        half_life = self.calculate_half_life(coint_res['residuals'])
        
        # Filter: Mean reverting (H < 0.5) and reasonable half-life (e.g. < 25 days)
        if hurst < 0.5 and 1 < half_life < 25:
            return {
                'beta': coint_res['beta'],
                'alpha': coint_res['alpha'],
                'adf_stat': coint_res['adf_stat'],
                'p_value': coint_res['p_value'],
                'hurst': hurst,
                'half_life': half_life
            }
        return None
