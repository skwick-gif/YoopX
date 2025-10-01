import sys
sys.path.insert(0, r'c:\MyProjects\YoopX Claude')
from PySide6.QtWidgets import QApplication
from ui.main_content.backtest_tab import BacktestTab

app = QApplication([])
bt = BacktestTab()
# Ensure layout is created
bt.show()
app.processEvents()

print('BacktestTab filters present:')
# Inspect left settings panel by walking children
def walk(widget, depth=0):
    from PySide6.QtWidgets import QLabel, QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QCheckBox
    indent = '  ' * depth
    try:
        for ch in widget.children():
            name = type(ch).__name__
            if isinstance(ch, QLabel):
                print(f"{indent}LABEL: {ch.text()}")
            elif isinstance(ch, QLineEdit):
                print(f"{indent}LINEEDIT: placeholder='{ch.placeholderText()}' text='{ch.text()}'")
            elif isinstance(ch, QSpinBox):
                print(f"{indent}SPINBOX: name={ch.objectName()} value={ch.value()}")
            elif isinstance(ch, QDoubleSpinBox):
                print(f"{indent}DOUBLESPIN: value={ch.value()}")
            elif isinstance(ch, QDateEdit):
                print(f"{indent}DATEEDIT: date={ch.date().toString('yyyy-MM-dd')}")
            elif isinstance(ch, QCheckBox):
                print(f"{indent}CHECKBOX: text='{ch.text()}' checked={ch.isChecked()}")
            else:
                # print basic info for other widgets
                if hasattr(ch, 'objectName'):
                    on = ch.objectName()
                else:
                    on = ''
                print(f"{indent}{name} (objName='{on}')")
            # recurse
            try:
                walk(ch, depth+1)
            except Exception:
                pass
    except Exception as e:
        print('walk error', e)

walk(bt)

bt.close()
app.quit()
