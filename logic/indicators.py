import pandas as pd
import numpy as np

def ema(series, period):
	return series.ewm(span=period, adjust=False).mean()

def sma(series, period):
	return series.rolling(window=period).mean()

def atr(df, period=14):
	high = df['High']
	low = df['Low']
	close = df['Close']
	tr = np.maximum(high - low, np.abs(high - close.shift()), np.abs(low - close.shift()))
	return pd.Series(tr).rolling(window=period).mean()

def macd(series, fast=12, slow=26, signal=9):
	fast_ema = ema(series, fast)
	slow_ema = ema(series, slow)
	macd_line = fast_ema - slow_ema
	signal_line = ema(macd_line, signal)
	hist = macd_line - signal_line
	return macd_line, signal_line, hist

def stoch(df, k_period=14, d_period=3):
	low_min = df['Low'].rolling(window=k_period).min()
	high_max = df['High'].rolling(window=k_period).max()
	k = 100 * ((df['Close'] - low_min) / (high_max - low_min))
	d = k.rolling(window=d_period).mean()
	return k, d

def bbands(series, period=20, k=2):
	sma_ = sma(series, period)
	std = series.rolling(window=period).std()
	upper = sma_ + k * std
	lower = sma_ - k * std
	return upper, lower

