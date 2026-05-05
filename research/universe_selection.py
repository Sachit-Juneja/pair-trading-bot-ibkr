import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
import yfinance as yf
import logging
import os

# Set up logging because I'm a professional and not a chaotic script-kiddie
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UniverseSelector:
    """
    Selects tradable pairs from a large universe using PCA and DBSCAN clustering.
    Because picking stocks at random is for people who enjoy losing money.
    """
    def __init__(self, tickers, start_date, end_date):
        self.tickers = tickers
        self.start_date = start_date
        self.end_date = end_date
        self.data = None
        self.returns = None
        self.clusters = None

    @staticmethod
    def get_sp500_tickers():
        """
        Scrapes the S&P 500 list from Wikipedia.
        """
        logger.info("Fetching S&P 500 tickers from Wikipedia...")
        try:
            import requests
            from bs4 import BeautifulSoup
            url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            # Look for the table with wikitable class, which is standard for S&P 500 page
            table = soup.find('table', {'class': 'wikitable'})
            
            if table:
                tickers = []
                for row in table.find_all('tr')[1:]:  # Skip header
                    cols = row.find_all('td')
                    if cols:
                        # The ticker is usually in the first column
                        ticker = cols[0].text.strip()
                        # Clean up and handle Wikipedia's specific ticker format
                        ticker = ticker.replace('.', '-')
                        tickers.append(ticker)
                
                if tickers:
                    logger.info(f"Successfully scraped {len(tickers)} tickers.")
                    return tickers
            
            raise ValueError("Could not find the S&P 500 table on the page.")
        except Exception as e:
            logger.error(f"Failed to fetch S&P 500 list: {e}")
            return []

    def fetch_data(self, batch_size=50):
        """
        Downloads historical data in batches because Yahoo Finance is flaky with large lists.
        """
        logger.info(f"Fetching data for {len(self.tickers)} tickers from {self.start_date} to {self.end_date}...")
        try:
            all_data = []
            for i in range(0, len(self.tickers), batch_size):
                batch = self.tickers[i:i+batch_size]
                logger.debug(f"Downloading batch {i//batch_size + 1}...")
                raw_batch = yf.download(batch, start=self.start_date, end=self.end_date, progress=False)
                
                if raw_batch.empty:
                    continue

                # If only one ticker was requested, it might not be a MultiIndex
                if len(batch) == 1:
                    if 'Adj Close' in raw_batch.columns:
                        s = raw_batch['Adj Close']
                        s.name = batch[0]
                        all_data.append(s)
                else:
                    # MultiIndex: ('Adj Close', 'Ticker')
                    if 'Adj Close' in raw_batch.columns:
                        adj_close = raw_batch['Adj Close']
                        for ticker in batch:
                            if ticker in adj_close.columns:
                                s = adj_close[ticker]
                                all_data.append(s)
            
            if not all_data:
                raise ValueError("No data could be fetched for any tickers. Yahoo might be rate-limiting you or your internet is ghosting you.")

            self.data = pd.concat(all_data, axis=1)
            
            # Drop columns with too many missing values
            self.data = self.data.dropna(axis=1, thresh=int(len(self.data) * 0.9))
            self.data = self.data.ffill().dropna()
            
            if self.data.empty:
                raise ValueError("Dataset is empty after cleaning.")

            logger.info(f"Successfully fetched data for {self.data.shape[1]} tickers.")
            return self.data
        except Exception as e:
            logger.error(f"Failed to fetch data: {e}")
            return None

    def calculate_returns(self):
        """
        Calculates log returns. Linear returns are for people who don't understand compounding.
        """
        if self.data is None:
            raise ValueError("No data found. Did you forget to call fetch_data() or is your internet just terrible?")
        
        self.returns = np.log(self.data / self.data.shift(1)).dropna()
        return self.returns

    def apply_pca(self, n_components=15):
        """
        Dimensionality reduction. Reducing the noise because most of the market is just screaming.
        """
        if self.returns is None:
            self.calculate_returns()
            
        if self.returns.empty:
            logger.error("Returns are empty. PCA skipped.")
            return np.array([]), None

        # Scale the data because PCA is sensitive to variance
        scaler = StandardScaler()
        scaled_returns = scaler.fit_transform(self.returns.T) # We want to cluster tickers, so transpose

        # PCA components cannot exceed min(n_samples, n_features)
        # n_features = returns.shape[1] (tickers), n_samples = returns.shape[0] (days)
        # scaled_returns.shape is (tickers, days)
        max_components = min(scaled_returns.shape[0], scaled_returns.shape[1])
        actual_n = min(n_components, max_components)
        
        logger.info(f"Applying PCA with {actual_n} components (requested {n_components})...")
        pca = PCA(n_components=actual_n)
        pca_features = pca.fit_transform(scaled_returns)
        
        logger.info(f"PCA complete. Explained variance ratio sum: {np.sum(pca.explained_variance_ratio_):.4f}")
        return pca_features, scaler

    def cluster_assets(self, n_components=10, eps=1.5, min_samples=2):
        """
        Groups similar assets together. Like high school, but for stocks.
        """
        features, _ = self.apply_pca(n_components=n_components)
        
        if features.size == 0:
            logger.error("No features for clustering.")
            self.clusters = pd.Series([], dtype=int)
            return self.clusters

        # DBSCAN doesn't require a pre-defined number of clusters. It finds them itself.
        clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(features)
        self.clusters = pd.Series(clustering.labels_, index=self.data.columns)
        
        n_clusters = len(set(clustering.labels_)) - (1 if -1 in clustering.labels_ else 0)
        n_noise = list(clustering.labels_).count(-1)
        
        logger.info(f"Clustering complete. Found {n_clusters} clusters and {n_noise} noise points.")
        return self.clusters

    def get_cluster_pairs(self, n_components=10, eps=1.5):
        """
        Returns a list of potential pairs grouped by cluster.
        """
        if self.clusters is None:
            self.cluster_assets(n_components=n_components, eps=eps)
            
        cluster_groups = {}
        for ticker, cluster_id in self.clusters.items():
            if cluster_id == -1:
                continue # Ignore noise
            if cluster_id not in cluster_groups:
                cluster_groups[cluster_id] = []
            cluster_groups[cluster_id].append(ticker)
            
        return cluster_groups

if __name__ == "__main__":
    # Example usage for testing. Don't worry, this won't break your prod... yet.
    # We'll use a small subset for the demo.
    tech_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'AMD', 'INTC', 'PYPL']
    selector = UniverseSelector(tech_tickers, start_date='2023-01-01', end_date='2024-01-01')
    selector.fetch_data()
    pairs = selector.get_cluster_pairs()
    
    for cid, members in pairs.items():
        print(f"Cluster {cid}: {members}")
