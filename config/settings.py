import os
import yaml

# Defaults that probably won't work out of the box because life is hard
DEFAULT_CONFIG = {
    'ibkr': {
        'host': '127.0.0.1',
        'port': 7497, # TWS paper trading default
        'client_id': 1
    },
    'research': {
        'universe': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'AMD', 'INTC', 'PYPL', 'ADBE', 'CRM', 'NFLX', 'CSCO', 'ORCL'],
        'start_date': '2022-01-01',
        'pca_components': 5,
        'db_path': 'sqlite:///pairs_trading.db'
    },
    'execution': {
        'z_score_entry': 2.0,
        'z_score_exit': 0.5,
        'max_position_size': 0.1, # 10% of equity
        'stop_loss_std': 4.0
    }
}

def load_config(config_path='config/settings.yaml'):
    if not os.path.exists(config_path):
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            yaml.dump(DEFAULT_CONFIG, f)
        return DEFAULT_CONFIG
    
    with open(config_path, 'r') as f:
        return yaml.load(f, Loader=yaml.FullLoader)
