import os

def test_imports():
    import ml.train_model as tm
    assert hasattr(tm, 'train_model')

def test_settings_persistence():
    from ui.shared.settings_manager import load_settings, save_settings
    s = load_settings()
    s['ml_model'] = 'rf'
    save_settings(s)
    s2 = load_settings()
    assert s2['ml_model'] == 'rf'
