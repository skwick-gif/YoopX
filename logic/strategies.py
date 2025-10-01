# ...existing imports...
import backtrader as bt

class BaseStrategy(bt.Strategy):
	params = (
		('stake', 1),
		('long_only', True),
		('stop_loss_pct', 0.0),
		('take_profit_pct', 0.0),
		('use_atr_sizer', False),
		('risk_pct', 0.01),
		('atr_period', 14),
		('atr_mult', 2.0),
		('use_regime', False),
		('regime_ma', 200),
		('use_weekly_filter', False),
		('weekly_ma', 200),
	)
	def __init__(self):
		# common bookkeeping
		self._last_order = None
		self._entry_price = None
		self._stop_order = None
		self._tp_order = None
		# convenience handles
		self.data_close = self.datas[0].close
		# ATR indicator for sizing/stop calculations
		try:
			self.atr = bt.indicators.ATR(self.datas[0], period=self.params.atr_period)
		except Exception:
			self.atr = None

	def size_for_price(self, price: float) -> int:
		"""Compute size based on either fixed stake or ATR risk sizing."""
		if price is None or price <= 0:
			return 0
		# fixed stake (dollars per symbol)
		if not getattr(self.params, 'use_atr_sizer', False):
			try:
				stake = float(getattr(self.params, 'stake', 1))
				return max(0, int(stake))
			except Exception:
				return 0
		# ATR sizing
		try:
			atr_val = None
			if self.atr is not None and len(self.atr) > 0:
				atr_val = float(self.atr[0]) if not hasattr(self.atr, 'iloc') else float(self.atr[ -1 ])
			if atr_val is None or atr_val <= 0:
				return 0
			risk_pct = float(getattr(self.params, 'risk_pct', 0.01))
			account_val = float(self.broker.getvalue())
			risk_per_trade = account_val * float(risk_pct)
			risk_per_share = max(1e-9, atr_val * float(getattr(self.params, 'atr_mult', 1.0)))
			qty = int(risk_per_trade / risk_per_share)
			return max(0, qty)
		except Exception:
			return 0

	def notify_order(self, order):
		# basic order bookkeeping and place stop/take orders after an entry
		if order.status in [order.Submitted, order.Accepted]:
			return
		if order.status in [order.Completed]:
			if order.isbuy():
				self._entry_price = getattr(order.executed, 'price', None)
				self._last_order = order
				# place stop / take-profit if configured
				try:
					stop_pct = float(getattr(self.params, 'stop_loss_pct', 0.0))
					tp_pct = float(getattr(self.params, 'take_profit_pct', 0.0))
					sz = int(getattr(order.executed, 'size', 0) or 0)
					if sz > 0 and (stop_pct > 0 or tp_pct > 0):
						entry = float(self._entry_price)
						if stop_pct > 0:
							stop_price = entry * (1.0 - stop_pct) if stop_pct > 0 else None
							if stop_price is not None:
								# place stop sell
								self._stop_order = self.sell(exectype=bt.Order.Stop, price=stop_price, size=sz)
						if tp_pct > 0:
							tp_price = entry * (1.0 + tp_pct)
							self._tp_order = self.sell(exectype=bt.Order.Limit, price=tp_price, size=sz)
				except Exception:
					pass
			elif order.issell():
				# if we close, clear trackers
				self._entry_price = None
				self._stop_order = None
				self._tp_order = None
		elif order.status in [order.Canceled, order.Margin, order.Rejected]:
			# order failed
			self._last_order = None

	def notify_trade(self, trade):
		if not trade.isclosed:
			return
		# can log PnL, or keep last profit
		try:
			pnl = getattr(trade, 'pnl', None) or getattr(trade, 'pnlcomm', None)
			self._last_trade_pnl = float(pnl) if pnl is not None else None
		except Exception:
			self._last_trade_pnl = None

class SmaCross(BaseStrategy):
	params = (('fast', 10), ('slow', 20))
	def __init__(self):
		super().__init__()
		self.sma_fast = bt.indicators.SMA(self.datas[0], period=self.params.fast)
		self.sma_slow = bt.indicators.SMA(self.datas[0], period=self.params.slow)

	def next(self):
		if not self.position:
			if self.sma_fast[0] > self.sma_slow[0]:
				self.buy()
		else:
			if self.sma_fast[0] < self.sma_slow[0]:
				self.close()

class EmaCross(SmaCross):
	params = (('fast', 10), ('slow', 20))
	def __init__(self):
		super().__init__()
		self.ema_fast = bt.indicators.EMA(self.datas[0], period=self.params.fast)
		self.ema_slow = bt.indicators.EMA(self.datas[0], period=self.params.slow)

	def next(self):
		if not self.position:
			if self.ema_fast[0] > self.ema_slow[0]:
				self.buy()
		else:
			if self.ema_fast[0] < self.ema_slow[0]:
				self.close()

class DonchianBreakout(BaseStrategy):
	params = (('upper', 20), ('lower', 10))
	def __init__(self):
		super().__init__()
		self.highest = bt.indicators.Highest(self.datas[0].high, period=self.params.upper)
		self.lowest = bt.indicators.Lowest(self.datas[0].low, period=self.params.lower)

	def next(self):
		if not self.position:
			if self.datas[0].close[0] > self.highest[-1]:
				self.buy()
		else:
			if self.datas[0].close[0] < self.lowest[-1]:
				self.close()

class MACDTrend(BaseStrategy):
	params = (('ema_trend', 200), ('fast', 12), ('slow', 26), ('signal', 9))
	def __init__(self):
		super().__init__()
		self.macd = bt.indicators.MACD(self.datas[0], period_me1=self.params.fast, period_me2=self.params.slow, period_signal=self.params.signal)
		self.ema_trend = bt.indicators.EMA(self.datas[0], period=self.params.ema_trend)

	def next(self):
		if not self.position:
			if self.datas[0].close[0] > self.ema_trend[0] and self.macd.macd[0] > self.macd.signal[0] and self.macd.macd[-1] <= self.macd.signal[-1]:
				self.buy()
		else:
			if self.macd.macd[0] < self.macd.signal[0] or self.datas[0].close[0] < self.ema_trend[0]:
				self.close()

class RSIBBMeanRev(BaseStrategy):
	params = (('rsi_p', 2), ('rsi_buy', 10), ('rsi_exit', 60), ('bb_p', 20), ('bb_k', 2.0))
	def __init__(self):
		super().__init__()
		self.rsi = bt.indicators.RSI(self.datas[0], period=self.params.rsi_p)
		self.bb = bt.indicators.BollingerBands(self.datas[0], period=self.params.bb_p, devfactor=self.params.bb_k)

	def next(self):
		if not self.position:
			if self.rsi[0] <= self.params.rsi_buy and self.datas[0].close[0] <= self.bb.lines.bot[0]:
				self.buy()
		else:
			if self.rsi[0] >= self.params.rsi_exit or self.datas[0].close[0] >= self.bb.lines.top[0]:
				self.close()

STRAT_MAP = {
	"SMA Cross": SmaCross,
	"EMA Cross": EmaCross,
	"Donchian Breakout": DonchianBreakout,
	"MACD Trend": MACDTrend,
	"RSI(2) @ Bollinger": RSIBBMeanRev,
}
# Trading strategies logic

