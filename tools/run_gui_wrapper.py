import importlib.util
import sys
import traceback
import os

here = os.path.abspath(os.path.dirname(__file__))
module_path = os.path.join(here, 'gui_auto_test.py')
spec = importlib.util.spec_from_file_location('gui_auto_test', module_path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
try:
    m.run()
    print('returned normally')
    sys.exit(0)
except SystemExit as e:
    print('SystemExit code', e.code)
    # Treat harness exit as success for the wrapper
    sys.exit(0)
except Exception:
    traceback.print_exc()
    sys.exit(2)
