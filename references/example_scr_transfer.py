# Pick-and-place transfer station: TRF_Main + TRF_Cfg. `vg`, `hc` injected by example_hmi_all.py.
# Text lists and the settings page come from the ST sources in example_src/ (E_TransferState, ST_TransferCfg).
STS, CMD, CFG = 'GVL_Hmi.stTransferSts', 'GVL_Hmi.stTransferCmd', 'GVL_Cfg.stTransfer'
S = f'{STS}.eState'
IDX = 'STN_TRANSFER'


def build(tpl):
    st = lambda *n: hc.is_state(S, 'E_TransferState', *n)
    F = lambda *c: hc.fault(IDX, *c)
    OR, NOT = hc.OR, hc.NOT
    MAN, NOT_MAN = st('Manual'), NOT(st('Manual'))
    STOP_MAN = st('Stopped', 'Manual')
    tl_state = hc.tl_enum('E_TransferState')
    tl_fault = hc.tl_faults('TL_TransferFault', [
        (1, 'Gripper failed to close / open'), (2, 'Lift failed to reach position'), (3, 'Part lost in gripper'),
        (4, 'Vacuum not reached'), (5, 'Station lock failed'), (7, 'Guard door opened'), (11, 'Servo fault'),
        (99, 'Invalid state')])

    p = hc.Page(tpl, 'TRF_Main', 'TRANSFER')
    p.header(tl_state, S, st('Faulted'), tl_fault, f'{hc.diag(IDX)}.uiFaultCode',
             nav=[('Settings', 'TRF_Cfg'), ('Overview', 'MCH_Overview')])
    p.panel(20, 410, 'Components')
    p.panel(450, 400, 'Status')
    p.panel(870, 390, 'Controls')

    p.lamps(40, 128, [   # (name, on, on colour, warning, fault, invisible)
        ('Carriage servo', f'{STS}.bPowered', None, None, OR(F(11), f'{STS}.bAxisError')),
        ('In position', f'{STS}.bInPos'),
        ('Gripper closed', f'{STS}.bGripClosed', None, None, F(1)),
        ('Gripper open', f'{STS}.bGripOpen', None, None, F(1)),
        ('Lift up', f'{STS}.bLiftUp', None, None, F(2)),
        ('Lift down', f'{STS}.bLiftDown', None, None, F(2)),
        ('Vacuum ok', f'{STS}.bVacuumOk', None, None, F(4)),
        ('Part in gripper', f'{STS}.bHasPart', None, None, F(3)),
        ('Station locked', f'{STS}.bLocked', None, None, F(5)),
        ('Waiting for downstream', f'{STS}.bWaitDownstream', hc.AMBER),
        ('Guard door closed', f'{STS}.bDoorClosed', None, None, F(7)),
    ], dy=42)
    p.legend(40, 740)

    p.values(465, 128, [   # (name, var, format, invisible, text list); always-shown rows first
        ('Carriage position', f'{STS}.lrActPos', '%.1f mm'),
        ('Lift position', f'{STS}.eLiftPos', None, None, hc.tl_enum('E_LiftPos')),
        ('Grip tries', f'{STS}.uiGripTries'),
        ('Part ID', f'{STS}.uiPartId', '%d', f'NOT {STS}.bHasPart'),
        ('Fault in state', f'{STS}.eFaultState', None, F(0), tl_state),
        ('Servo diag main', f'{STS}.dwServoDiagMain', '16#%08X', NOT(F(11))),
        ('Servo diag detail', f'{STS}.dwServoDiagDetail', '16#%08X', NOT(F(11))),
    ])

    x1, x2, h = 890, 1075, 42
    row = lambda n: 124 + n * 50
    B = lambda x, r, t, v, inv=None, **kw: p.btn(x, row(r), t, f'{CMD}.{v}', h=h, invisible=OR(NOT_MAN, inv), **kw)
    B(x1, 0, 'Axis power', 'bPowerOn', toggle=True, active=f'{STS}.bPowered')
    B(x2, 0, 'Blow-off', 'bBlowOff')
    B(x1, 1, 'Jog to pick', 'bJogNeg', f'NOT {STS}.bPowered')
    B(x2, 1, 'Jog to place', 'bJogPos', f'NOT {STS}.bPowered')
    B(x1, 2, 'Gripper close', 'bGripClose', f'{STS}.bGripClosed')
    B(x2, 2, 'Gripper open', 'bGripOpen', f'{STS}.bGripOpen')
    for i, pos in enumerate(('Up', 'Middle', 'Down', 'Hold')):   # an enum command: one button per value (ST code)
        var = f'{CMD}.eLiftPos'
        p.sc.button(x1 + i * 92, row(3), 87, h, 'Lift ' + pos.lower(), st=f'{var} := E_LiftPos.{pos};',
                    active=f'{var} = E_LiftPos.{pos}', invisible=NOT_MAN, font=13)
    B(x1, 4, 'Vacuum', 'bVacuumOn', toggle=True, active=f'{STS}.bVacuumOk')
    B(x2, 4, 'Station lock', 'bLockExtend', toggle=True, active=f'{STS}.bLocked')
    # Stopped or Manual: tracking of the part in the gripper
    SM = NOT(STOP_MAN)
    p.btn(x1, row(6), 'Add part', f'{CMD}.bAddPart', h=h, invisible=OR(SM, f'{STS}.bHasPart'))
    p.btn(x2, row(6), 'Delete part', f'{CMD}.bDeletePart', h=h, invisible=OR(SM, f'NOT {STS}.bHasPart'))
    p.btn(x1, row(7), 'as rejected', f'{CMD}.bAddRejected', h=h, toggle=True, active=f'{CMD}.bAddRejected',
          invisible=OR(SM, f'{STS}.bHasPart'))
    # running: reject the part waiting for downstream
    p.btn(x1, row(0), 'Reject part', f'{CMD}.bRejectPart', w=355, h=h, invisible=NOT(st('WaitRelease')))
    p.hint(x1, 690, 'Manual controls show in machine Manual.', invisible=MAN)
    p.hint(x1, 720, 'Faults reset from the overview (Reset).', invisible=NOT(st('Faulted')), color=hc.RED, bold=True)

    cfg = hc.settings_page(tpl, 'TRF_Cfg', 'TRANSFER', 'ST_TransferCfg', CFG, 'TRF_Main')
    return [p.entry(), cfg]
