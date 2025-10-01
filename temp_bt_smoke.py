import pandas as pd, numpy as np
import backend
idx = pd.date_range("2024-01-01","2024-03-31", freq="B")
prices = 100 + np.cumsum(np.random.randn(len(idx))*0.5)
vol = np.random.randint(1000,5000,size=len(idx))
df = pd.DataFrame({"Open":prices,"High":prices*1.01,"Low":prices*0.99,"Close":prices,"Volume":vol}, index=idx)
figs, summary = backend.run_backtest(df,"SMA Cross",{"fast":10,"slow":20},10000,0.0005,0.0005,1.0,0.0,None,False)
print("EQUITY_LEN", len(summary.get("equity_series",[])))
print("DD_LEN", len(summary.get("drawdown_series",[])))
print("SAMPLE_EQUITY", summary.get("equity_series",[])[:2])
