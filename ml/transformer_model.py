"""Placeholder lightweight Transformer time-series classifier.
Not wired yet; provides a future hook if we decide to model sequences directly.
"""
from typing import List, Dict, Any
import torch
import torch.nn as nn

class PriceTransformer(nn.Module):
    def __init__(self, input_dim: int, d_model: int = 64, nhead: int = 4, num_layers: int = 2, dim_feedforward: int = 128, dropout: float = 0.1):
        super().__init__()
        self.proj = nn.Linear(input_dim, d_model)
        enc_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=nhead, dim_feedforward=dim_feedforward, dropout=dropout, batch_first=True)
        self.encoder = nn.TransformerEncoder(enc_layer, num_layers=num_layers)
        self.cls = nn.Sequential(nn.LayerNorm(d_model), nn.Linear(d_model, 1))
    def forward(self, x):  # x: (B, T, F)
        h = self.proj(x)
        h = self.encoder(h)
        # take last token
        last = h[:, -1, :]
        out = self.cls(last)
        return out.squeeze(-1)

# Training/eval utilities would be added when moving this from placeholder to production.
