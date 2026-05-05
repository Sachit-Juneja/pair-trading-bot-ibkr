import asyncio
from ib_insync import IB, Stock, util
import logging

logger = logging.getLogger(__name__)

class IBClient:
    """
    The bridge to IBKR. If this fails, blame your internet or IBKR's legacy backend.
    """
    def __init__(self, host='127.0.0.1', port=7497, client_id=1):
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id
        self.active_contracts = {}

    async def connect(self):
        """
        Attempts to connect. Please make sure TWS is actually open.
        """
        try:
            await self.ib.connectAsync(self.host, self.port, self.client_id)
            logger.info(f"Connected to IBKR at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Connection failed: {e}. Is TWS running?")
            raise

    def get_contract(self, symbol):
        """
        Creates or returns a cached Stock contract.
        """
        if symbol not in self.active_contracts:
            self.active_contracts[symbol] = Stock(symbol, 'SMART', 'USD')
        return self.active_contracts[symbol]

    async def request_realtime_bars(self, symbols, callback):
        """
        Streams 1-minute bars. High frequency enough to feel fast, slow enough for Python.
        """
        contracts = [self.get_contract(s) for s in symbols]
        # Qualify all at once to save round trips
        await self.ib.qualifyContractsAsync(*contracts)
        
        for contract in contracts:
            bars = self.ib.reqRealTimeBars(contract, 5, 'MIDPOINT', False)
            bars.updateEvent += callback
            logger.info(f"Subscribed to realtime bars for {contract.symbol}")

    async def disconnect(self):
        self.ib.disconnect()
        logger.info("Disconnected from IBKR. Sleep tight.")
