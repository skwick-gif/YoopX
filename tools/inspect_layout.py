import sys
sys.path.insert(0, r'c:\MyProjects\YoopX Claude')
from PySide6.QtWidgets import QApplication
from main_window import QuantDeskMainWindow

app = QApplication([])
w = QuantDeskMainWindow()
w.show()
# process events to ensure geometry/layout is updated
app.processEvents()

cw = w.centralWidget()
lay = cw.layout()
try:
    m = lay.contentsMargins()
    print('centralWidget.layout.contentsMargins:', m.left(), m.top(), m.right(), m.bottom())
except Exception as e:
    print('centralWidget.layout.contentsMargins: ERROR', e)

print('main_layout spacing:', lay.spacing())

sidebar = getattr(w, 'sidebar', None)
if sidebar is not None:
    print('sidebar.pos:', sidebar.pos().x(), sidebar.pos().y())
    geom = sidebar.geometry()
    print('sidebar.geom:', geom.x(), geom.y(), geom.width(), geom.height())
    header = getattr(sidebar, 'header', None)
    print('has header', header is not None)
    if header is not None:
        try:
            hm = header.layout().contentsMargins()
            print('header.layout.contentsMargins:', hm.left(), hm.top(), hm.right(), hm.bottom())
        except Exception as e:
            print('header.layout.contentsMargins: ERROR', e)
        try:
            hg = header.geometry()
            print('header.geom:', hg.x(), hg.y(), hg.width(), hg.height())
        except Exception as e:
            print('header.geom: ERROR', e)

main_content = getattr(w, 'main_content', None)
if main_content is not None:
    tab = getattr(main_content, 'tab_widget', None)
    if tab is not None:
        bg = tab.geometry()
        print('tab_widget.geom:', bg.x(), bg.y(), bg.width(), bg.height())
        try:
            bar = tab.tabBar()
            bm = bar.contentsMargins()
            print('tabBar.contentsMargins:', bm.left(), bm.top(), bm.right(), bm.bottom())
            bgeom = bar.geometry()
            print('tabBar.geom:', bgeom.x(), bgeom.y(), bgeom.width(), bgeom.height())
        except Exception as e:
            print('tabBar: ERROR', e)

print('QMainWindow styleSheet length', len(w.styleSheet() or ''))

# Additional diagnostics: window and central widget sizes; list children sizes
try:
    print('MainWindow geom:', w.geometry().x(), w.geometry().y(), w.geometry().width(), w.geometry().height())
    print('centralWidget geom:', cw.geometry().x(), cw.geometry().y(), cw.geometry().width(), cw.geometry().height())
    # layout children
    print('Main layout child count:', lay.count())
    for i in range(lay.count()):
        item = lay.itemAt(i)
        widget = item.widget()
        if widget is not None:
            g = widget.geometry()
            print(f' child[{i}] type={type(widget).__name__} geom={g.x()},{g.y()},{g.width()},{g.height()}')
        else:
            print(f' child[{i}] is not a widget')
except Exception as e:
    print('extra diagnostics error', e)

# close and quit
w.close()
app.quit()
