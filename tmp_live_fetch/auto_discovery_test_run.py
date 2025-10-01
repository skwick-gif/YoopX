from PySide6.QtWidgets import QApplication
from main_content import MainContent
from PySide6.QtCore import QTimer

app = QApplication([])
mc = MainContent()
mc.show()
TAB = mc.auto_discovery_tab
TAB.manual_symbols_input.setText('AAPL,MSFT')
for b in TAB.strat_buttons[:2]:
    b.setChecked(True)
TAB._grid_json = '{"fast":[5,10],"slow":[20,30]}'
TAB.run_auto()

ticks = {'n':0}

def tick():
    ticks['n'] += 1
    if ticks['n'] % 10 == 0:
        print('PROGRESS', TAB.progress_bar.value(), 'STATUS', TAB.status_label.text())
    if ticks['n'] > 60:
        app.quit()

for i in range(1,65):
    QTimer.singleShot(150*i, tick)

app.exec()
print('FINAL_ROWS', len(getattr(TAB,'_last_results',[])))
for r in getattr(TAB,'_last_results',[])[:5]:
    print('ROW', r)
