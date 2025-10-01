import sys
sys.path.insert(0, r'c:\MyProjects\YoopX Claude')
from PySide6.QtWidgets import QApplication
from ui.sidebar.sidebar import Sidebar

app = QApplication([])
side = Sidebar()
side.show()
app.processEvents()

print('Sidebar enabled:', side.isEnabled())
print('Header enabled:', getattr(side, 'header', None).isEnabled())

uf = getattr(side, 'universe_filter', None)
print('\nUniverseFilterSection present:', uf is not None)
if uf is not None:
    print('  type:', type(uf).__name__)
    print('  title:', uf.title())
    try:
        print('  enabled:', uf.isEnabled())
    except Exception as e:
        print('  enabled error', e)
    # list child widgets
    try:
        lay = uf.layout()
        print('  child count:', lay.count())
        for i in range(lay.count()):
            item = lay.itemAt(i)
            w = item.widget()
            print('   child', i, type(w).__name__ if w else 'None')
    except Exception as e:
        print('  layout introspect error', e)

ss = getattr(side, 'strategy', None)
print('\nStrategySection present:', ss is not None)
if ss is not None:
    print('  title:', ss.title())
    print('  enabled:', ss.isEnabled())
    try:
        # iterate checkboxes
        cbs = getattr(ss, 'strategy_checkboxes', [])
        print('  checkbox count:', len(cbs))
        for cb in cbs:
            print('   cb:', cb.text(), 'enabled=', cb.isEnabled(), 'checked=', cb.isChecked())
    except Exception as e:
        print('  checkbox introspect error', e)
    try:
        pl = getattr(ss, 'params_layout', None)
        if pl is not None:
            print('  params_layout count:', pl.count())
            for i in range(pl.count()):
                w = pl.itemAt(i).widget()
                if w:
                    print('   params child', i, type(w).__name__, 'enabled=', w.isEnabled())
    except Exception as e:
        print('  params introspect error', e)

# quit
side.close()
app.quit()
