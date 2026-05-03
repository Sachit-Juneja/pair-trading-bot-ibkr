import logging

logger = logging.getLogger(__name__)

class RiskManager:
    """
    The designated adult in the room. Prevents the bot from blowing up the account.
    """
    def __init__(self, ib_client, max_pos_pct=0.1, stop_loss_std=4.0):
        self.ib_client = ib_client
        self.max_pos_pct = max_pos_pct
        self.stop_loss_std = stop_loss_std

    def get_account_equity(self):
        """
        Fetches the current Net Liquidation Value.
        """
        for summary in self.ib_client.ib.accountSummary():
            if summary.tag == 'NetLiquidation':
                return float(summary.value)
        return 0.0

    def calculate_position_size(self, price_a, price_b, beta):
        """
        Calculates quantity based on available equity and risk limits.
        """
        equity = self.get_account_equity()
        if equity <= 0:
            logger.warning("Zero equity detected. Are we broke already?")
            return 0
            
        target_value = equity * self.max_pos_pct
        # Value of 1 unit of spread = price_a + (beta * price_b)
        spread_unit_price = price_a + (beta * price_b)
        
        quantity = int(target_value / spread_unit_price)
        return max(0, quantity)

    def check_circuit_breaker(self, z_score):
        """
        If the Z-score is out of control, the relationship is broken. Eject.
        """
        if abs(z_score) > self.stop_loss_std:
            logger.critical(f"CIRCUIT BREAKER: Z-score {z_score} exceeded threshold {self.stop_loss_std}. Relationship broken.")
            return True
        return False
