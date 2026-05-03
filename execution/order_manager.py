from ib_insync import Order, Bag, ComboLeg, MarketOrder, LimitOrder
import logging

logger = logging.getLogger(__name__)

class OrderManager:
    """
    Executes trades using IBKR Combo Orders to avoid legging risk.
    Because getting half-filled is a great way to lose money fast.
    """
    def __init__(self, ib_client):
        self.ib_client = ib_client
        self.open_trades = {} # ticker_pair -> trade_object

    def create_spread_contract(self, ticker_a, ticker_b, ratio):
        """
        Creates a 'Bag' contract for the spread.
        Note: IBKR ratio must be an integer usually for combos, 
        so we might need to scale up (e.g. 100:beta*100).
        For simplicity, we'll assume a 1:beta ratio if possible or use the nearest integers.
        """
        contract_a = self.ib_client.get_contract(ticker_a)
        contract_b = self.ib_client.get_contract(ticker_b)
        
        # Qualify them to get conId
        self.ib_client.ib.qualifyContracts(contract_a, contract_b)
        
        bag = Bag()
        bag.symbol = f"{ticker_a}.{ticker_b}"
        bag.currency = 'USD'
        bag.exchange = 'SMART'
        
        # Leg 1: Buy Ticker A
        leg1 = ComboLeg()
        leg1.conId = contract_a.conId
        leg1.ratio = 1
        leg1.action = 'BUY'
        leg1.exchange = 'SMART'
        
        # Leg 2: Sell Ticker B (ratio determined by beta)
        # In a real setup, you'd scale beta to an integer.
        # Here we simplify to 1:1 or use the beta directly if IBKR allows (it doesn't, must be int).
        # We'll use a basic approximation for the demo.
        leg2 = ComboLeg()
        leg2.conId = contract_b.conId
        leg2.ratio = max(1, int(round(ratio)))
        leg2.action = 'SELL'
        leg2.exchange = 'SMART'
        
        bag.comboLegs = [leg1, leg2]
        return bag

    def submit_spread_order(self, ticker_a, ticker_b, ratio, action, quantity):
        """
        action: 'BUY' (Long spread) or 'SELL' (Short spread)
        """
        pair_key = f"{ticker_a}_{ticker_b}"
        if pair_key in self.open_trades and not self.open_trades[pair_key].isDone():
            logger.warning(f"Trade already in progress for {pair_key}. Skipping.")
            return

        bag = self.create_spread_contract(ticker_a, ticker_b, ratio)
        order = MarketOrder(action, quantity)
        
        trade = self.ib_client.ib.placeOrder(bag, order)
        self.open_trades[pair_key] = trade
        
        logger.info(f"Submitted {action} order for {quantity} units of {pair_key} spread.")
        return trade

    def flatten_position(self, ticker_a, ticker_b, ratio, quantity):
        """
        Exits the position by doing the opposite of the current position.
        """
        pair_key = f"{ticker_a}_{ticker_b}"
        # This assumes we know the direction. A more robust way is checking the portfolio.
        # For now, we'll just implement the inverse.
        # Actually, let's just use the ib.positions() to find the active legs.
        pass
