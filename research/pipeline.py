import logging
from research.universe_selection import UniverseSelector
from research.cointegration import CointegrationAnalyzer
from models.database import init_db, CointegratedPair
from config.settings import load_config
import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_research_pipeline():
    """
    The main factory for finding money-making pairs. 
    Warning: Does not actually guarantee money.
    """
    config = load_config()
    res_conf = config['research']
    
    # 1. Universe Selection
    tickers = res_conf['universe']
    if tickers == 'SP500':
        tickers = UniverseSelector.get_sp500_tickers()
        if not tickers:
            logger.error("Could not fetch S&P 500 tickers. Reverting to defaults.")
            tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']

    selector = UniverseSelector(
        tickers, 
        res_conf['start_date'], 
        datetime.date.today().strftime('%Y-%m-%d')
    )
    data = selector.fetch_data()
    if data is None:
        logger.error("No data, no pairs, no money. Fix your internet.")
        return

    clusters = selector.get_cluster_pairs()
    
    # 2. Cointegration Analysis
    analyzer = CointegrationAnalyzer()
    session = init_db(res_conf['db_path'])
    
    # Clear old pairs because the market doesn't care about last year's news
    session.query(CointegratedPair).delete()
    
    found_count = 0
    for cluster_id, members in clusters.items():
        logger.info(f"Analyzing cluster {cluster_id} with {len(members)} members...")
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                t1, t2 = members[i], members[j]
                res = analyzer.analyze_pair(data[t1], data[t2])
                
                if res:
                    logger.info(f"Found cointegrated pair: {t1} - {t2} (p-value: {res['p_value']:.4f})")
                    pair = CointegratedPair(
                        ticker_a=t1,
                        ticker_b=t2,
                        beta=res['beta'],
                        alpha=res['alpha'],
                        adf_stat=res['adf_stat'],
                        p_value=res['p_value'],
                        hurst_exponent=res['hurst'],
                        half_life=res['half_life'],
                        z_score_threshold=config['execution']['z_score_entry']
                    )
                    session.add(pair)
                    found_count += 1
    
    session.commit()
    logger.info(f"Pipeline complete. Found {found_count} tradable pairs. Good luck, you'll need it.")

if __name__ == "__main__":
    run_research_pipeline()
