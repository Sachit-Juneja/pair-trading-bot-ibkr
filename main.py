import asyncio
import sys

# Python 3.14+ fix: Ensure an event loop exists before importing ib_insync/eventkit
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import logging
from execution.ib_client import IBClient
from execution.alpha import AlphaModel
from execution.order_manager import OrderManager
from execution.risk_management import RiskManager
from models.database import init_db, CointegratedPair
from config.settings import load_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PairsBot:
    """
    The orchestrator that runs the live execution engine.
    """
    def __init__(self):
        self.config = load_config()
        self.client = IBClient(
            host=self.config['ibkr']['host'],
            port=self.config['ibkr']['port'],
            client_id=self.config['ibkr']['client_id']
        )
        self.order_manager = OrderManager(self.client)
        self.risk_manager = RiskManager(
            self.client, 
            max_pos_pct=self.config['execution']['max_position_size'],
            stop_loss_std=self.config['execution']['stop_loss_std']
        )
        self.alphas = {} # (ticker_a, ticker_b) -> AlphaModel
        self.pairs_data = {} # (ticker_a, ticker_b) -> CointegratedPair

    async def initialize(self):
        """
        Connects to IBKR and loads pairs from the database.
        """
        await self.client.connect()
        
        session = init_db(self.config['research']['db_path'])
        pairs = session.query(CointegratedPair).all()
        
        if not pairs:
            logger.warning("No cointegrated pairs found in database. Run the research pipeline first!")
            return False
            
        for pair in pairs:
            key = (pair.ticker_a, pair.ticker_b)
            self.alphas[key] = AlphaModel(pair.ticker_a, pair.ticker_b, pair.beta)
            self.pairs_data[key] = pair
            logger.info(f"Initialized live tracking for {pair.ticker_a}-{pair.ticker_b}")
            
        return True

    async def on_bar_update(self, bars, has_new_bar):
        """
        Callback for real-time bars. Updates alpha models and checks for signals.
        """
        if not has_new_bar:
            return
            
        # Note: bars is a BarDataList. We need to know which contract it belongs to.
        contract = bars.contract
        price = bars[-1].close
        
        for (t1, t2), alpha in self.alphas.items():
            if t1 == contract.symbol:
                alpha.update_prices(price_a=price)
            elif t2 == contract.symbol:
                alpha.update_prices(price_b=price)
            
            # Check for signals
            signal = alpha.get_signal(
                entry_threshold=self.config['execution']['z_score_entry'],
                exit_threshold=self.config['execution']['z_score_exit']
            )
            
            if signal is not None:
                await self.process_signal(t1, t2, signal, alpha.calculate_z_score())

    async def process_signal(self, t1, t2, signal, z_score):
        """
        Handles signal execution with risk checks.
        """
        if self.risk_manager.check_circuit_breaker(z_score):
            return

        pair_data = self.pairs_data[(t1, t2)]
        
        # Calculate quantity based on nominal value or standard risk
        # For demo, we'll use a fixed quantity of 100 shares for Leg A
        qty = 100
        
        if signal == 1: # Long spread
            await self.order_manager.submit_spread_order(t1, t2, pair_data.beta, 'BUY', qty)
        elif signal == -1: # Short spread
            await self.order_manager.submit_spread_order(t1, t2, pair_data.beta, 'SELL', qty)
        elif signal == 0: # Exit
            logger.info(f"Signal to exit position for {t1}-{t2}")

    async def background_research_task(self):
        """
        Runs the research pipeline every 7 days. 
        """
        from research.pipeline import run_research_pipeline
        while True:
            # Wait 7 days first. We already ran research to get started.
            await asyncio.sleep(60 * 60 * 24 * 7)
            
            logger.info("Starting scheduled background research pipeline...")
            try:
                await asyncio.to_thread(run_research_pipeline)
                logger.info("Background research pipeline complete. Refreshing pairs...")
                await self.initialize() # Reload pairs into the bot
            except Exception as e:
                logger.error(f"Scheduled research failed: {e}")

    async def run(self):
        """
        Main loop.
        """
        if not await self.initialize():
            return
            
        # Start background research task
        asyncio.create_task(self.background_research_task())
            
        # Subscribe to all unique tickers
        all_tickers = set()
        for t1, t2 in self.alphas.keys():
            all_tickers.add(t1)
            all_tickers.add(t2)
            
        await self.client.request_realtime_bars(list(all_tickers), self.on_bar_update)
        
        logger.info("Bot is live and hunting for alpha. Scheduled research is active.")
        
        while True:
            await asyncio.sleep(1)

if __name__ == "__main__":
    bot = PairsBot()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user. Hopefully with more money than it started with.")
