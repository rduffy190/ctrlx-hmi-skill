# 05 Cross transfer: XT_Main + XT_Cfg. `vg`, `hc` injected by hmi_all.py.
STS, CMD, CFG = 'GVL_Hmi.stCrossTransferSts', 'GVL_Hmi.stCrossTransferCmd', 'GVL_Cfg.stCrossTransfer'
S = f'{STS}.eState'
IDX = 'STN_CROSS_TRANSFER'


def build(tpl):
    st = lambda *n: hc.is_state(S, 'E_XtState', *n)
    F = lambda *c: hc.fault(IDX, *c)
    OR, AND, NOT = hc.OR, hc.AND, hc.NOT
    MAN, NOT_MAN = st('Manual'), NOT(st('Manual'))
    STOP_MAN = st('Stopped', 'Manual')
    tl_state = hc.tl_enum('E_XtState')
    tl_fault = hc.tl_faults('TL_CrossTransferFault', [
        (1, 'Clips failed to close / open'), (2, 'Carriage failed to open / close'), (3, 'Glue 2 clamp failed'),
        (4, 'Op vacuum cylinder failed'), (5, 'Station lock failed'), (6, 'Cups (SMS) fault'),
        (7, 'Door failed to close'), (8, 'Glue 2 head not clear'), (10, 'Bag stuck at Glue 2'), (11, 'Servo fault'),
        (99, 'Invalid state')])

    p = hc.Page(tpl, 'XT_Main', 'CROSS TRANSFER')
    p.header(tl_state, S, st('Faulted'), tl_fault, f'{hc.diag(IDX)}.uiFaultCode',
             nav=[('Settings', 'XT_Cfg'), ('Overview', 'MCH_Overview')])
    p.panel(20, 410, 'Components')
    p.panel(450, 400, 'Status')
    p.panel(870, 390, 'Controls')

    p.lamps(40, 128, [
        ('Carriage servo', f'{STS}.bPowered', None, None, OR(F(11), f'{STS}.bAxisError')),
        ('In position', f'{STS}.bInPos'),
        ('Clear of operator', f'{STS}.bClearOfOperator', None, None, F(8)),
        ('Clips closed', f'{STS}.bClipsClosed', None, None, F(1)),
        ('Clips open', f'{STS}.bClipsOpen', None, None, F(1)),
        ('Carriage closed', f'{STS}.bCarriageClosed', None, None, F(2)),
        ('Carriage open', f'{STS}.bCarriageOpen', None, None, F(2)),
        ('Glue 2 clamp closed', f'{STS}.bClampClosed', None, None, F(3)),
        ('Glue 2 clamp open', f'{STS}.bClampOpen', None, None, F(3)),
        ('Bag open (both sensors)', f'{STS}.bBagOpen'),
        ('Cups SMS ok', f'NOT {STS}.bCupsFault', None, None, OR(F(6), f'{STS}.bCupsFault')),
        ('Bag in slot', f'{STS}.bHasBag', None, None, F(10)),
        ('Waiting for WMS label', f'{STS}.bWmsWaiting', hc.AMBER),
        ('Door closed in time', 'FALSE', None, None, F(7)),
    ], dy=42)
    p.legend(40, 740)

    p.values(465, 128, [
        ('Carriage position', f'{STS}.lrActPos', '%.1f mm'),
        ('Cups position', f'{STS}.diCupsPos'),
        ('Open tries', f'{STS}.uiOpenTries'),
        ('Bag QID', f'{STS}.uiBagQID', '%d', f'NOT {STS}.bHasBag'),
        ('Fault in state', f'{STS}.eFaultState', None, F(0), tl_state),
        ('Cups SMS diag', f'{STS}.uiCupsDiag', '%d', NOT(F(6))),
        ('Servo diag main', f'{STS}.dwServoDiagMain', '16#%08X', NOT(F(11))),
        ('Servo diag detail', f'{STS}.dwServoDiagDetail', '16#%08X', NOT(F(11))),
    ])

    x1, x2, h = 890, 1075, 42
    row = lambda n: 124 + n * 50
    B = lambda x, r, t, v, inv=None, **kw: p.btn(x, row(r), t, f'{CMD}.{v}', h=h, invisible=OR(NOT_MAN, inv), **kw)
    B(x1, 0, 'Axis power', 'bPowerOn', toggle=True, active=f'{STS}.bPowered')
    B(x2, 0, 'Blow-off', 'bBlowOff')
    B(x1, 1, 'Jog to operator', 'bJogNeg', f'NOT {STS}.bPowered')
    B(x2, 1, 'Jog to Glue 2', 'bJogPos', f'NOT {STS}.bPowered')
    B(x1, 2, 'Clips close', 'bClipsClose', f'{STS}.bClipsClosed')
    B(x2, 2, 'Clips open', 'bClipsOpen', f'{STS}.bClipsOpen')
    B(x1, 3, 'Carriage close', 'bCarriageClose', f'{STS}.bCarriageClosed')
    B(x2, 3, 'Carriage open', 'bCarriageOpen', f'{STS}.bCarriageOpen')
    B(x1, 4, 'G2 clamp close', 'bClampClose', f'{STS}.bClampClosed')
    B(x2, 4, 'G2 clamp open', 'bClampOpen', f'{STS}.bClampOpen')
    for i, pos in enumerate(('In', 'Intermediate', 'Out', 'None')):
        var = f'{CMD}.eCupsPos'
        p.sc.button(x1 + i * 92, row(5), 87, h, 'Cups ' + {'None': 'hold', 'Intermediate': 'mid'}.get(pos, pos),
                    st=f'{var} := E_SmsPos.{pos};', active=f'{var} = E_SmsPos.{pos}', invisible=NOT_MAN, font=13)
    B(x1, 6, 'Operator vacuum', 'bOpVacOn', toggle=True)
    B(x2, 6, 'Station lock', 'bLockExtend', toggle=True)
    B(x1, 7, 'Vac cylinder out', 'bVacCylExtend')
    B(x2, 7, 'Vac cylinder in', 'bVacCylRetract')
    # Stopped or Manual: bag slot, cups settings
    SM = NOT(STOP_MAN)
    p.btn(x1, row(8), 'Write cups settings', f'{CMD}.bWriteCupsCfg', h=h, invisible=SM)
    p.btn(x1, row(9), 'Add bag', f'{CMD}.bAddBag', h=h, invisible=OR(SM, f'{STS}.bHasBag'))
    p.btn(x2, row(9), 'Delete bag', f'{CMD}.bDeleteBag', h=h, invisible=OR(SM, f'NOT {STS}.bHasBag'))
    p.btn(x1, row(10), 'with product', f'{CMD}.bAddHasProduct', h=h, toggle=True, active=f'{CMD}.bAddHasProduct',
          invisible=OR(SM, f'{STS}.bHasBag'))
    p.btn(x2, row(10), 'as rejected', f'{CMD}.bAddRejected', h=h, toggle=True, active=f'{CMD}.bAddRejected',
          invisible=OR(SM, f'{STS}.bHasBag'))
    # running: reject the bag waiting for its label
    p.btn(x1, row(0), 'Reject bag', f'{CMD}.bRejectBag', w=355, h=h, invisible=NOT(st('WaitRelease')))
    p.hint(x1, 690, 'Manual controls show in machine Manual.', invisible=MAN)
    p.hint(x1, 720, 'Faults reset from the overview (Reset).', invisible=NOT(st('Faulted')), color=hc.RED, bold=True)

    cfg = hc.settings_page(tpl, 'XT_Cfg', 'CROSS TRANSFER', 'ST_CrossTransferCfg', CFG, 'XT_Main')
    return [p.entry(), cfg]
