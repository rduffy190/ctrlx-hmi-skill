# Example: a cut-to-length station's operating screen CUT_Main and its text lists. Built by:
#   python3 <skill>/scripts/visugen.py example_screen_cutter.py CUT_Main.export
# Bindings: GVL_Hmi.stCutterCmd / stCutterSts (HMI -> PLC / PLC -> HMI), GVL_Cfg.stCutter (settings),
# GVL_Machine.astDiag[...] (warnings). `vg` (visugen) is injected by visugen.py when it runs this file.

W, H = 1280, 800

STS = 'GVL_Hmi.stCutterSts'
CMD = 'GVL_Hmi.stCutterCmd'
CFG = 'GVL_Cfg.stCutter'
S = f'{STS}.eState'
MANUAL = f'{S} = E_CutterState.Manual'
NOT_MANUAL = f'{S} <> E_CutterState.Manual'


def F(code):
    return f'{STS}.uiFaultCode = {code}'


def WARN(n):
    return f'GVL_Machine.astDiag[GVL_Const.STN_CUTTER].abWarnings[{n}]'


def OR(*xs):
    return ' OR '.join(f'({x})' for x in xs)


# colours
GREY, GREEN, AMBER, RED = 0xB4B9BE, 0x22B14C, 0xFFB000, 0xE02020
HEAD, PANEL, EDGE = 0x2B3A4A, 0xFFFFFF, 0xC4CAD0

STATES = ['Stopped', 'Manual', 'Aborting', 'Home cutter', 'Ready', 'Wait upstream', 'Feed', 'Clamp', 'Mark',
          'Cut', 'Unclamp', 'Eject', 'Eject clear', 'Clearing', 'Cleared', 'Faulted']
FAULTS = [(0, ''), (2, 'F2  Material out'), (3, 'F3  Servo fault'), (4, 'F4  No material detected'),
          (8, 'F8  Jam on eject'), (11, 'F11  Settings invalid'), (13, 'F13  Material failed to feed'),
          (14, 'F14  Clamp fault'), (99, 'F99  Invalid state')]
CUT_SIDES = [(0, 'Unknown'), (1, 'Left'), (2, 'Right')]


def lamp(sc, y, name, on_expr, on=GREEN, warn=None, fault=None, invisible=None):
    """<light> <name> row. Base light grey/on colour; amber and red overlays drawn on top."""
    sc.circle(40, y + 2, 26, GREY, on, on_expr, invisible)
    if warn:
        sc.circle(40, y + 2, 26, AMBER, AMBER, 'FALSE', OR(f'NOT ({warn})', invisible) if invisible else f'NOT ({warn})')
    if fault:
        sc.circle(40, y + 2, 26, RED, RED, 'FALSE', OR(f'NOT ({fault})', invisible) if invisible else f'NOT ({fault})')
    sc.label(80, y, 330, 30, name, font=18, invisible=invisible)


def value(sc, y, name, var, fmt, invisible=None, textlist=None):
    sc.label(465, y, 200, 30, name, font=17, invisible=invisible)
    if textlist:
        sc.box(670, y, 165, 30, textlist=textlist, text_index=var, font=17, bold=True, frame=EDGE,
               invisible=invisible)
    else:
        sc.box(670, y, 165, 30, fmt, text_var=var, font=17, bold=True, frame=EDGE, invisible=invisible)


def build(tpl):
    sc = vg.Screen(tpl, 'CUT_Main', W, H)

    # ---- header -----------------------------------------------------------------------------
    sc.box(0, 0, W, 64, fill=HEAD, frame=HEAD)
    sc.label(20, 10, 260, 44, 'CUTTER', font=30, bold=True, color=0xFFFFFF)
    sc.box(290, 10, 360, 44, textlist='TL_CutterState', text_index=S, font=22, bold=True,
           fill=0xFFFFFF, frame=0xFFFFFF, alarm=f'{S} = E_CutterState.Faulted', alarm_fill=RED)
    sc.box(670, 10, 590, 44, textlist='TL_CutterFault', text_index=f'{STS}.uiFaultCode', font=20, bold=True,
           fill=RED, frame=RED, color=0xFFFFFF, invisible=F(0))

    # ---- panels -----------------------------------------------------------------------------
    for x, w, title in ((20, 410, 'Components'), (450, 400, 'Status'), (870, 390, 'Controls')):
        sc.box(x, 80, w, 700, fill=PANEL, frame=EDGE)
        sc.label(x + 15, 88, w - 30, 30, title, font=20, bold=True, color=HEAD)

    # ---- components: <light> <name> -----------------------------------------------------------
    y0, dy = 130, 44
    rows = [   # (name, on, on colour, warning, fault, invisible); conditional rows last
        ('Cutter servo', f'{STS}.bAxisPowered', GREEN, None, F(3), None),
        ('Clamp closed', f'NOT {STS}.bUnclamped', GREEN, None, F(14), None),
        ('Cutter at left', f'{STS}.bLeftProx', GREEN, WARN(6), None, None),
        ('Cutter at right', f'{STS}.bRightProx', GREEN, WARN(6), None, None),
        ('Material sensed', f'{STS}.bMaterialSense', GREEN, WARN(7), OR(F(4), F(13)), None),
        ('Material low', f'{STS}.bMaterialLow', AMBER, None, None, None),
        ('Material out', f'{STS}.bMaterialOut', RED, None, F(2), None),
        ('Splice', OR(f'{STS}.bSplice', f'{STS}.uiSpliceCount > 0'), AMBER, None, None, None),
        ('Part in output', f'{STS}.bOutputOccupied', GREEN, f'{STS}.bOutputOccupied AND {STS}.bOutputRejected', None, None),
        ('Part eject', OR(f'{S} = E_CutterState.Eject', f'{S} = E_CutterState.EjectClear'),
         GREEN, f'{STS}.uiEjectTries > 0', F(8), None),
        ('Settings', f'{STS}.bSettingsOk', GREEN, None, OR(f'NOT {STS}.bSettingsOk', F(11)), None),
        ('Batch done', f'{STS}.bBatchDone', GREEN, None, None, f'{CFG}.uiBatchQty = 0'),
        ('Upstream ready', f'{STS}.bUpstreamReady', GREEN, WARN(10), None, f'NOT {CFG}.bWaitUpstream'),
    ]
    for i, (name, on_expr, on, warn, fault, inv) in enumerate(rows):
        lamp(sc, y0 + i * dy, name, on_expr, on, warn, fault, inv)
    sc.label(40, 728, 380, 40, 'Grey = off, green = on, amber = warning, red = fault', font=14, color=0x606870)

    # ---- status values ------------------------------------------------------------------------
    y0, dy = 130, 42
    no_fault = F(0)
    vals = [   # always shown first, conditional rows last so hidden rows leave no holes in the middle
        ('Last cut side', f'{STS}.eLastCutSide', None, None, 'TL_CutSide'),
        ('Axis position', f'{STS}.lrAxisPos', '%.1f mm', None, None),
        ('Time in step', f'{STS}.tStepElapsed', '%s', None, None),
        ('Splice rejects left', f'{STS}.uiSpliceCount', '%d', None, None),
        ('Eject tries', f'{STS}.uiEjectTries', '%d', None, None),
        ('Cut length setting', f'{CFG}.uiCutLength', '%d mm', None, None),
        ('Batch remaining', f'{STS}.uiBatchRemaining', '%d', f'{CFG}.uiBatchQty = 0', None),
        ('Output part ID', f'{STS}.uiOutputPartId', '%d', f'NOT {STS}.bOutputOccupied', None),
        ('Output part length', f'{STS}.uiOutputLength', '%d mm', f'NOT {STS}.bOutputOccupied', None),
        ('Fault in state', f'{STS}.eFaultState', None, no_fault, 'TL_CutterState'),
        ('Drive diag main', f'{STS}.dwDiagMain', '16#%08X', f'NOT ({F(3)})', None),
        ('Drive diag detail', f'{STS}.dwDiagDetail', '16#%08X', f'NOT ({F(3)})', None),
    ]
    for i, (name, var, fmt, inv, tl) in enumerate(vals):
        value(sc, y0 + i * dy, name, var, fmt, inv, tl)

    # ---- controls -----------------------------------------------------------------------------
    bx1, bx2, bw, bh = 890, 1075, 170, 56
    row = lambda n: 130 + n * 70

    # auto (not Manual)
    sc.button(bx1, row(0), bw, bh, 'Skip the wait', f'{CMD}.bSkipWait',
              invisible=f'{S} <> E_CutterState.WaitUpstream')
    sc.button(bx2, row(0), bw, bh, 'Recut last part', f'{CMD}.bRecut',
              invisible=OR(MANUAL, f'{S} = E_CutterState.Aborting', f'{S} = E_CutterState.Faulted'))
    sc.button(bx1, row(1), bw, bh, 'Load batch', f'{CMD}.bLoadBatch',
              invisible=OR(MANUAL, f'{CFG}.uiBatchQty = 0'))
    sc.label(bx2, row(1), bw, bh, 'Batch size %d', text_var=f'{CFG}.uiBatchQty', font=17,
             invisible=OR(MANUAL, f'{CFG}.uiBatchQty = 0'))
    sc.label(bx1, 690, 355, 30, 'Manual controls show in machine Manual.', font=15,
             color=0x606870, invisible=MANUAL)
    sc.label(bx1, 720, 355, 30, 'Faults reset from the machine screen.', font=15, bold=True,
             color=RED, invisible=f'{S} <> E_CutterState.Faulted')

    # manual
    sc.button(bx1, row(0), bw, bh, 'Jog reverse', f'{CMD}.bJogRev',
              invisible=OR(NOT_MANUAL, f'NOT {STS}.bAxisPowered'))
    sc.button(bx2, row(0), bw, bh, 'Jog forward', f'{CMD}.bJogFwd',
              invisible=OR(NOT_MANUAL, f'NOT {STS}.bAxisPowered'))
    sc.label(bx1, row(0), 355, bh, 'Cutter servo not powered: no jog', font=15, color=0x606870,
             invisible=OR(NOT_MANUAL, f'{STS}.bAxisPowered'))
    sc.button(bx1, row(1), bw, bh, 'Cut left', f'{CMD}.bCutLeft',
              invisible=OR(NOT_MANUAL, f'{STS}.bLeftProx'))
    sc.button(bx2, row(1), bw, bh, 'Cut right', f'{CMD}.bCutRight',
              invisible=OR(NOT_MANUAL, f'{STS}.bRightProx'))
    sc.button(bx1, row(2), bw, bh, 'Unclamp', f'{CMD}.bUnclamp', toggle=True,
              active=f'{STS}.bUnclamped', invisible=NOT_MANUAL)
    sc.button(bx2, row(2), bw, bh, 'Air blast', f'{CMD}.bAirBlast', invisible=NOT_MANUAL)
    sc.button(bx1, row(3), bw, bh, 'Eject', f'{CMD}.bEject', invisible=NOT_MANUAL)
    sc.button(bx2, row(3), bw, bh, 'Mark', f'{CMD}.bMark',
              invisible=OR(NOT_MANUAL, f'NOT {CFG}.bMarkerEnable'))
    sc.label(bx1, row(4) + 8, bw, 40, 'Cut length (mm)', font=17, invisible=NOT_MANUAL)
    sc.numeric(bx2, row(4) + 4, bw, 48, f'{CMD}.uiCutLength', '%d', 0, 2000, 'Cut length (mm)',
               invisible=NOT_MANUAL)
    sc.button(bx1, row(5), 355, bh, 'Put part in output (marked reject)', f'{CMD}.bSetOccupied',
              invisible=OR(NOT_MANUAL, f'{STS}.bOutputOccupied'))
    sc.button(bx1, row(5), 355, bh, 'Empty the output', f'{CMD}.bClearOccupied',
              invisible=OR(NOT_MANUAL, f'NOT {STS}.bOutputOccupied'))

    return [
        vg.textlist(tpl, 'TL_CutterState', list(enumerate(STATES))),
        vg.textlist(tpl, 'TL_CutterFault', FAULTS),
        vg.textlist(tpl, 'TL_CutSide', CUT_SIDES),
        sc.entry(),
    ]
