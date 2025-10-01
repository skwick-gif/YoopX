import os, json, math
from typing import Dict, Any
import pandas as pd

TRANSFORMER_MODEL_PATH = 'ml/model_transformer.pt'

def _build_sequences(df: pd.DataFrame, seq_len: int = 32):
    """Return list of (seq_tensor, label) using simple return-based sequence.
    Sequence features: percent returns and rolling volatility (naive).
    Label: future 5-bar pct change > 0 => 1 else 0.
    """
    if 'Close' not in df.columns or len(df) < seq_len + 10:
        return []
    closes = df['Close'].astype(float).reset_index(drop=True)
    rets = closes.pct_change().fillna(0.0)
    vol = rets.rolling(10).std().fillna(0.0)
    data = pd.DataFrame({'ret': rets, 'vol': vol})
    rows = []
    for i in range(seq_len, len(data)-6):
        seq = data.iloc[i-seq_len:i].values  # shape (seq_len, 2)
        fut_ret = (closes.iloc[i+5] / closes.iloc[i] - 1.0)
        label = 1 if fut_ret > 0 else 0
        rows.append((seq, label))
    return rows

def train_transformer(data_map: Dict[str, pd.DataFrame], seq_len: int = 32, epochs: int = 4, lr: float = 1e-3) -> Dict[str, Any]:
    try:
        import torch
        from torch import nn
        from torch.utils.data import Dataset, DataLoader
        from .transformer_model import PriceTransformer
    except Exception as e:
        raise RuntimeError(f"PyTorch not installed or transformer model missing: {e}")

    sequences = []
    sym_count = 0
    for sym, df in data_map.items():
        try:
            seqs = _build_sequences(df, seq_len)
            if seqs:
                sequences.extend(seqs)
                sym_count += 1
        except Exception:
            continue
    if not sequences:
        raise ValueError('No sequences generated for transformer training')

    # Train/val split
    split = int(len(sequences)*0.8)
    train_data = sequences[:split]
    val_data = sequences[split:] if split < len(sequences) else []

    class SeqDS(Dataset):
        def __init__(self, rows): self.rows = rows
        def __len__(self): return len(self.rows)
        def __getitem__(self, idx):
            x, y = self.rows[idx]
            return torch.tensor(x, dtype=torch.float32), torch.tensor([y], dtype=torch.float32)

    train_loader = DataLoader(SeqDS(train_data), batch_size=64, shuffle=True)
    val_loader = DataLoader(SeqDS(val_data), batch_size=128, shuffle=False) if val_data else None

    model = PriceTransformer(input_dim=2, d_model=32, nhead=4, num_layers=1, dim_feedforward=64, dropout=0.1)
    device = 'cuda' if (hasattr(torch, 'cuda') and torch.cuda.is_available()) else 'cpu'
    model.to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.BCELoss()

    def run_epoch(loader, train=True):
        if train: model.train()
        else: model.eval()
        total_loss = 0.0
        preds_all = []
        y_all = []
        for xb, yb in loader:
            xb = xb.to(device)  # (B, seq_len, 2)
            yb = yb.to(device)
            if train:
                opt.zero_grad()
            out = model(xb)  # (B, 1)
            loss = criterion(out, yb)
            if train:
                loss.backward(); opt.step()
            total_loss += float(loss.item()) * xb.size(0)
            preds_all.extend(out.detach().cpu().numpy().ravel().tolist())
            y_all.extend(yb.detach().cpu().numpy().ravel().tolist())
        avg_loss = total_loss / max(1, len(loader.dataset))
        return avg_loss, preds_all, y_all

    history = []
    for ep in range(epochs):
        tr_loss, _, _ = run_epoch(train_loader, True)
        if val_loader:
            val_loss, val_preds, val_y = run_epoch(val_loader, False)
        else:
            val_loss, val_preds, val_y = float('nan'), [], []
        history.append({'epoch': ep+1, 'train_loss': tr_loss, 'val_loss': val_loss})

    # Validation metrics
    auc = None
    try:
        if val_loader and val_y and len(set(val_y)) == 2:
            from sklearn.metrics import roc_auc_score
            auc = float(roc_auc_score(val_y, val_preds))
    except Exception:
        pass

    os.makedirs(os.path.dirname(TRANSFORMER_MODEL_PATH), exist_ok=True)
    import torch
    torch.save({'state_dict': model.state_dict(), 'seq_len': seq_len}, TRANSFORMER_MODEL_PATH)

    return {
        'path': TRANSFORMER_MODEL_PATH,
        'samples': len(sequences),
        'symbols': sym_count,
        'train_size': len(train_data),
        'val_size': len(val_data),
        'history': history,
        'val_auc': auc,
        'model_type': 'transformer'
    }

def load_transformer(path: str = TRANSFORMER_MODEL_PATH):
    try:
        import torch
        from .transformer_model import PriceTransformer
        if not os.path.exists(path):
            return None
        ckpt = torch.load(path, map_location='cpu')
        seq_len = ckpt.get('seq_len', 32)
        model = PriceTransformer(input_dim=2, d_model=32, nhead=4, num_layers=1, dim_feedforward=64, dropout=0.1)
        model.load_state_dict(ckpt['state_dict'])
        model.eval()
        return {'model': model, 'seq_len': seq_len, 'type': 'transformer'}
    except Exception:
        return None

def predict_transformer_latest(df: pd.DataFrame, model_obj) -> float | None:
    try:
        import torch, math
    except Exception:
        return None
    if model_obj is None or 'model' not in model_obj:
        return None
    seq_len = model_obj.get('seq_len', 32)
    rows = _build_sequences(df, seq_len)
    if not rows:
        return None
    seq, _ = rows[-1]
    x = torch.tensor(seq, dtype=torch.float32).unsqueeze(0)  # (1, seq_len, 2)
    with torch.no_grad():
        prob = model_obj['model'](x).item()
    return float(prob)
