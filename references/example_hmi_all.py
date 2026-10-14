# All POD screens in one export (text lists are shared, so they are exported once, with the screens).
# Build: python3 ~/.claude/skills/ctrlx-hmi/scripts/visugen.py hmi_all.py build/POD_Hmi.export
# `vg` is injected by visugen; the station modules get `vg` and `hc` (hmi_common).
import importlib.util
import os
import runpy

HERE = os.path.dirname(os.path.abspath(__file__))
ALLOWED_PREFIXES = ('GVL_', 'E_', 'VisuDialogs', 'VisuElems')
MODULES = ['scr_overview', 'scr_infeed', 'scr_bottomglue', 'scr_pivot', 'scr_operator', 'scr_crosstransfer',
           'scr_topglue', 'scr_printconveyor', 'scr_gluesystem', 'scr_airsystem', 'scr_wms']
ONLY = os.environ.get('HMI_ONLY', '').split(',') if os.environ.get('HMI_ONLY') else None


def _common():
    spec = importlib.util.spec_from_file_location('hmi_common', os.path.join(HERE, 'hmi_common.py'))
    hc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hc)
    hc.vg = vg
    return hc


def build(tpl):
    hc = _common()
    visus = []
    for m in MODULES:
        if ONLY and m not in ONLY:
            continue
        path = os.path.join(HERE, m + '.py')
        if os.path.exists(path):
            visus += runpy.run_path(path, init_globals={'vg': vg, 'hc': hc})['build'](tpl)
    return hc.textlist_entries(tpl) + visus
