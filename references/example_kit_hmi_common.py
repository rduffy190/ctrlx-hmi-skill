# Shared kit for the POD screens (loaded by hmi_all.py, which sets `vg`).
# Layout of the Infeed screen made reusable, a parser for the ST sources (enums, settings structs) so text lists and
# settings screens follow the code, and the text-list registry (each list is exported once).
import glob
import os
import re

vg = None                                   # visugen, set by hmi_all.py
SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # src/

W, H = 1280, 800
GREY, GREEN, AMBER, RED, BLUE = 0xB4B9BE, 0x22B14C, 0xFFB000, 0xE02020, 0x3070C0
HEAD, PANEL, EDGE, HINT, WHITE = 0x2B3A4A, 0xFFFFFF, 0xC4CAD0, 0x606870, 0xFFFFFF

MSTS = 'GVL_Hmi.stMachineSts'
MCMD = 'GVL_Hmi.stMachineCmd'
MSTATE = f'{MSTS}.eState'
NAV = True                                  # navigation buttons (VisuElems.CurrentVisu)
# Settings are edited only while the machine is not producing (Stopped, Hold, Abort, Manual). None = always.
EDIT_LOCK = None                            # set below once mstate() exists


def OR(*xs):
    xs = [x for x in xs if x]
    return ' OR '.join(f'({x})' for x in xs) if len(xs) > 1 else (xs[0] if xs else '')


def AND(*xs):
    xs = [x for x in xs if x]
    return ' AND '.join(f'({x})' for x in xs) if len(xs) > 1 else (xs[0] if xs else '')


def NOT(x):
    return f'NOT ({x})'


def is_state(var, enum, *names):
    return OR(*(f'{var} = {enum}.{n}' for n in names))


def mstate(*names):
    return is_state(MSTATE, 'E_MachineState', *names)


EDIT_LOCK = NOT(mstate('Stopped', 'Hold', 'Abort', 'Manual'))


def diag(idx):
    return f'GVL_Machine.astDiag[GVL_Const.{idx}]'


def fault(idx, *codes):
    return OR(*(f'{diag(idx)}.uiFaultCode = {c}' for c in codes))


def warn(idx, n):
    return f'{diag(idx)}.abWarnings[{n}]'


# ---- ST sources ------------------------------------------------------------------------------------------------

def _sources():
    files = [f for f in glob.glob(os.path.join(SRC, '**', '*.st'), recursive=True)
             if '/build/' not in f and '/tests/' not in f]
    return {f: open(f, encoding='utf-8').read() for f in files}


_SRC_CACHE = None


def _type_body(name):
    global _SRC_CACHE
    if _SRC_CACHE is None:
        _SRC_CACHE = _sources()
    for text in _SRC_CACHE.values():
        m = re.search(rf'TYPE\s+{name}\s*:(.*?)END_TYPE', text, re.S)
        if m:
            return m.group(1)
    raise KeyError(name)


def enum_items(name):
    """[(value, identifier)] of an enum type."""
    body = _type_body(name)
    body = body[body.index('(') + 1:body.rindex(')')]
    body = re.sub(r'//[^\n]*', '', body)
    items, v = [], 0
    for part in body.split(','):
        part = part.strip()
        if not part:
            continue
        m = re.match(r'(\w+)\s*(?::=\s*(\d+))?', part)
        if m.group(2):
            v = int(m.group(2))
        items.append((v, m.group(1)))
        v += 1
    return items


def struct_fields(name):
    """[(field, type, comment)] of a struct type."""
    body = _type_body(name)
    out = []
    for line in body.split('\n'):
        m = re.match(r'\s*(\w+)\s*:\s*([\w.]+(?:\([^)]*\))?(?:\s*\[[^\]]*\])?)[^;]*;\s*(?://\s*(.*))?', line)
        if m and m.group(1) not in ('STRUCT',):
            out.append((m.group(1), m.group(2).strip(), (m.group(3) or '').strip()))
    return out


ACRONYMS = {'PE', 'PB', 'ID', 'IP', 'SMS', 'QID', 'WMS', 'FIFO', 'FAT', 'XT', 'ZPL'}


def humanize(ident, prefix=True):
    """lrDistPastCut -> 'Dist past cut', tPrintPEToApply -> 'Print PE to apply', SelectWaitForProduct -> 'Select wait for product'."""
    if prefix:
        ident = re.sub(r'^(udi|di|ui|lr|st|si|i|r|t|b|s|e|dw)(?=[A-Z])', '', ident)
    words = re.findall(r'[A-Z]+[0-9]*(?![a-z])|[A-Z]?[a-z]+[0-9]*|[0-9]+', ident)
    out = []
    for i, w in enumerate(words):
        base, digits = re.match(r'(\D*)(\d*)$', w).groups()
        if base.upper() in ACRONYMS or (base.isupper() and len(base) > 1):
            out.append(base.upper() + (' ' + digits if digits and base else digits))
        else:
            out.append(w.capitalize() if i == 0 else w.lower())
    return ' '.join(out)


# ---- text lists ------------------------------------------------------------------------------------------------

TEXTLISTS = {}


def tl(name, items):
    TEXTLISTS.setdefault(name, items)
    return name


def tl_enum(enum, name=None):
    return tl(name or 'TL_' + enum[2:], [(v, humanize(i, prefix=False)) for v, i in enum_items(enum)])


def tl_faults(name, faults):
    return tl(name, [(0, '')] + [(c, f'F{c}  {t}') for c, t in faults])


tl('TL_OnOff', [(0, 'Off'), (1, 'On')])


def textlist_entries(tpl):
    return [vg.textlist(tpl, n, items) for n, items in TEXTLISTS.items()]


# ---- page kit --------------------------------------------------------------------------------------------------

class Page:
    """One 1280x800 screen in the Infeed layout: header, panels, lamp rows, value rows, buttons."""

    def __init__(self, tpl, name, title):
        self.sc = vg.Screen(tpl, name, W, H)
        self.name = name
        self.sc.box(0, 0, W, 64, fill=HEAD, frame=HEAD)
        self.sc.label(20, 10, 270, 44, title, font=26, bold=True, color=WHITE)

    def header(self, state_tl=None, state_var=None, faulted=None, fault_tl=None, fault_var=None,
               state_text=None, nav=()):
        """State text (text list), red when faulted; fault banner (hidden at 0); nav = [(text, visu), ...]."""
        if state_tl:
            self.sc.box(290, 10, 330, 44, textlist=state_tl, text_index=state_var, font=20, bold=True,
                        fill=WHITE, frame=WHITE, alarm=faulted, alarm_fill=RED)
        elif state_text:
            self.sc.box(290, 10, 330, 44, state_text, font=20, bold=True, fill=WHITE, frame=WHITE)
        right = W - 20
        if NAV:
            for text, visu in reversed(nav):
                right -= 125
                self.nav(right, 12, 120, 40, text, visu)
                right -= 5
        if fault_tl:
            self.sc.box(635, 10, right - 640, 44, textlist=fault_tl, text_index=fault_var, font=18, bold=True,
                        fill=RED, frame=RED, color=WHITE, invisible=f'{fault_var} = 0')

    def nav(self, x, y, w, h, text, visu, font=15):
        if NAV:
            self.sc.button(x, y, w, h, text, st=f"VisuElems.CurrentVisu := '{visu}';", font=font)

    def panel(self, x, w, title, y=80, h=700):
        self.sc.box(x, y, w, h, fill=PANEL, frame=EDGE)
        self.sc.label(x + 15, y + 8, w - 30, 30, title, font=20, bold=True, color=HEAD)

    def lamp(self, x, y, name, on_expr, on=GREEN, warn=None, fault=None, invisible=None, w=330, font=17):
        """<light> <name>: grey/on base, amber overlay on warn, red overlay on fault."""
        self.sc.circle(x, y + 2, 26, GREY, on, on_expr or 'FALSE', invisible)
        if warn:
            self.sc.circle(x, y + 2, 26, AMBER, AMBER, 'FALSE', OR(NOT(warn), invisible))
        if fault:
            self.sc.circle(x, y + 2, 26, RED, RED, 'FALSE', OR(NOT(fault), invisible))
        self.sc.label(x + 40, y, w, 30, name, font=font, invisible=invisible)

    def lamps(self, x, y0, rows, dy=40, w=330):
        """rows: (name, on_expr, on, warn, fault, invisible); conditional rows should come last."""
        for i, r in enumerate(rows):
            r = tuple(r) + (None,) * (6 - len(r))
            self.lamp(x, y0 + i * dy, r[0], r[1], r[2] or GREEN, r[3], r[4], r[5], w=w)
        return y0 + len(rows) * dy

    def legend(self, x, y):
        self.sc.label(x, y, 380, 30, 'Grey = off, green = on, amber = warning, red = fault', font=13, color=HINT)

    def value(self, x, y, name, var, fmt='%d', textlist=None, invisible=None, lw=200, vw=165, font=16):
        self.sc.label(x, y, lw, 30, name, font=font, invisible=invisible)
        if textlist:
            self.sc.box(x + lw + 5, y, vw, 30, textlist=textlist, text_index=var, font=font, bold=True, frame=EDGE,
                        invisible=invisible)
        else:
            self.sc.box(x + lw + 5, y, vw, 30, fmt, text_var=var, font=font, bold=True, frame=EDGE,
                        invisible=invisible)

    def values(self, x, y0, rows, dy=38, lw=200, vw=165):
        """rows: (name, var, fmt, invisible, textlist); always-shown rows first."""
        for i, r in enumerate(rows):
            r = tuple(r) + (None,) * (5 - len(r))
            self.value(x, y0 + i * dy, r[0], r[1], r[2] or '%d', r[4], r[3], lw, vw)

    def btn(self, x, y, text, var=None, w=170, h=48, **kw):
        kw.setdefault('font', 15)
        return self.sc.button(x, y, w, h, text, var, **kw)

    def hint(self, x, y, text, invisible=None, w=355, color=HINT, bold=False):
        self.sc.label(x, y, w, 30, text, font=14, color=color, bold=bold, invisible=invisible)

    def entry(self):
        return self.sc.entry()


# ---- settings screen -------------------------------------------------------------------------------------------

SUB = {   # nested settings structs: child labels
    'ST_Dynamics': {'lrVel': 'velocity', 'lrAcc': 'acceleration', 'lrDec': 'deceleration', 'lrJerk': 'jerk'},
    'ST_SmsCfg': {'diPosIn': 'position In', 'diPosIntermediate': 'position Intermediate', 'diPosOut': 'position Out',
                  'uiSpeed': 'speed (0-255)', 'uiForce': 'force (0-255)'},
}
GROUP = {'stDyn': 'Dynamics', 'stDynSweep': 'Sweep dynamics', 'stSms': 'Pivot SMS', 'stCups': 'Cups SMS',
         'stHead': 'Head SMS'}


def _flatten(cfg_type, var):
    rows = []
    for f, t, c in struct_fields(cfg_type):
        if t in SUB:
            g = GROUP.get(f, humanize(f))
            for sf, st, sc in struct_fields(t):
                rows.append((f'{g}: {SUB[t].get(sf, humanize(sf))}', f'{var}.{f}.{sf}', st, sc))
        else:
            rows.append((humanize(f), f'{var}.{f}', t, c))
    return rows


def settings_page(tpl, name, title, cfg_type, cfg_var, back, nav_overview='MCH_Overview', labels=None):
    """Every field of a settings struct as label + edit field, in columns of 17 rows.
    Numbers: numpad; TIME and STRING: keypad; BOOL: On/Off with a toggle button."""
    labels = labels or {}
    p = Page(tpl, name, title)
    p.header(state_text='Settings', nav=[('Back', back), ('Overview', nav_overview)])
    rows = _flatten(cfg_type, cfg_var)
    per_col, dy, y0 = 16, 38, 132
    cols = (len(rows) + per_col - 1) // per_col
    assert cols <= 3, f'{cfg_type}: {len(rows)} settings do not fit one page'
    cw = (W - 40) // 3
    for c in range(3):
        if c < cols:
            p.panel(20 + c * cw + (5 if c else 0), cw - 5, 'Settings' if c == 0 else '')
    for i, (label, var, typ, comment) in enumerate(rows):
        c, r = divmod(i, per_col)
        x, y = 35 + c * cw, y0 + r * dy
        label = labels.get(var.split('.', 2)[-1], label)
        p.sc.label(x, y, 225, 30, label, font=15)
        fx = x + 228
        if typ == 'BOOL':
            p.sc.box(fx, y, 70, 30, textlist='TL_OnOff', text_index=f'SEL({var}, 0, 1)', font=15, bold=True,
                     frame=EDGE, alarm=var, alarm_fill=0xC8EBCF)
            p.sc.button(fx + 75, y, 75, 30, 'Change', var, toggle=True, active=var, font=13, deactivate=EDIT_LOCK)
        elif typ == 'TIME' or typ.startswith('STRING'):
            p.sc.numeric(fx, y, 150, 30, var, '%s', '', '', label, font=15, dialog='VisuDialogs.Keypad',
                         deactivate=EDIT_LOCK)
        elif typ in ('LREAL', 'REAL'):
            p.sc.numeric(fx, y, 150, 30, var, '%.1f', '', '', label, font=15, deactivate=EDIT_LOCK)
        else:
            p.sc.numeric(fx, y, 150, 30, var, '%d', '', '', label, font=15, deactivate=EDIT_LOCK)
    if EDIT_LOCK:
        p.hint(35, 742, 'Settings can be changed when the machine is Stopped, in Hold, Abort or Manual.',
               w=800, invisible=NOT(EDIT_LOCK), color=RED, bold=True)
    return p.entry()
