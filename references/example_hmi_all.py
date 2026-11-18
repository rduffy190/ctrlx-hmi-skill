# Build entry for a multi-screen machine HMI: every station screen in one export (text lists are shared, so they
# are exported once, with the screens). In a project this is hmi_all.py next to hmi_common.py and one scr_<station>.py
# per station. Build:
#   python3 <skill>/scripts/visugen.py example_hmi_all.py build/Machine_Hmi.export
# `vg` is injected by visugen; the station modules get `vg` and `hc` (the kit).
import importlib.util
import os
import runpy

HERE = os.path.dirname(os.path.abspath(__file__))
ALLOWED_PREFIXES = ('GVL_', 'E_', 'VisuDialogs', 'VisuElems')
KIT = 'example_kit_hmi_common.py'
SRC = os.path.join(HERE, 'example_src')        # the project's ST sources (enums and settings structs)
MODULES = ['example_scr_transfer']             # one module per station, in screen order
ONLY = os.environ.get('HMI_ONLY', '').split(',') if os.environ.get('HMI_ONLY') else None


def _common():
    spec = importlib.util.spec_from_file_location('hmi_common', os.path.join(HERE, KIT))
    hc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hc)
    hc.vg = vg
    hc.SRC = SRC
    return hc


def build(tpl):
    hc = _common()
    visus = []
    for m in MODULES:
        if ONLY and m not in ONLY:
            continue
        visus += runpy.run_path(os.path.join(HERE, m + '.py'), init_globals={'vg': vg, 'hc': hc})['build'](tpl)
    return hc.textlist_entries(tpl) + visus
