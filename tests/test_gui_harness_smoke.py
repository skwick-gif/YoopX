import pytest

# This is a manual/CI smoke test for the GUI harness. It is skipped by default
# because it requires a Qt environment and can be slow. Run explicitly with:
#    pytest -q tests/test_gui_harness_smoke.py -k run_harness

@pytest.mark.skip(reason="GUI harness smoke test - run manually or in CI")
def test_run_harness_once():
    from importlib import util
    import os
    here = os.path.abspath(os.path.dirname(__file__))
    harness_path = os.path.abspath(os.path.join(os.path.dirname(here), 'tools', 'gui_auto_test.py'))
    spec = util.spec_from_file_location('gui_auto_test', harness_path)
    m = util.module_from_spec(spec)
    spec.loader.exec_module(m)
    # The harness calls sys.exit(0) on success; calling run() here should raise SystemExit(0)
    with pytest.raises(SystemExit) as se:
        m.run()
    assert se.value.code == 0
