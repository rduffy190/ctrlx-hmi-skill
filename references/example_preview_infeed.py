# Preview scenarios for screen_infeed.py (python3 preview.py build/INF_Main.export preview_infeed.py build/preview)
STATES = ['Stopped', 'Manual', 'Aborting', 'CheckState', 'SelectWait', 'HomeCutter', 'InitialIndex', 'SelectIndex',
          'StartComplete', 'SelectBag', 'HoldQueue', 'Index', 'Clamp', 'TearFire', 'TearDelay', 'Cut', 'Wait', 'Drop',
          'PullDown', 'DropClear', 'Nudge', 'NewFeed', 'Clearing', 'Cleared', 'Faulted']
ENUMS = {'E_InfeedState': STATES}
S = 'GVL_Hmi.stInfeedSts.'
base = {S + 'bAxisPowered': True, S + 'bSettingsOk': True, S + 'bBoardSense': True, S + 'bLeftProx': True,
        S + 'eLastCutSide': 1, S + 'lrAxisPos': 1234.5, S + 'tStepElapsed': 'T#1S200MS',
        'GVL_Cfg.stInfeed.uiBagLength': 400, 'GVL_Hmi.stInfeedCmd.uiBagLength': 400}
SCENARIOS = {
    'running_wait': {**base, S + 'eState': STATES.index('Wait'), S + 'bSlotOccupied': True, S + 'uiSlotQID': 1042,
                     S + 'uiSlotLength': 400, S + 'bMaterialLow': True,
                     'GVL_Cfg.stInfeed.uiBatchQty': 20, S + 'uiBatchRemaining': 7},
    'manual': {**base, S + 'eState': STATES.index('Manual'), S + 'bUnclamped': True},
    'servo_fault': {**base, S + 'eState': STATES.index('Faulted'), S + 'uiFaultCode': 3,
                    S + 'eFaultState': STATES.index('Index'), S + 'bAxisPowered': False,
                    S + 'dwDiagMain': 0xF2025, S + 'dwDiagDetail': 0x0},
    'hold_queue': {**base, S + 'eState': STATES.index('HoldQueue'), 'GVL_Cfg.stInfeed.bFollowScanner': True,
                   'GVL_Machine.astDiag[GVL_Const.STN_INFEED].abWarnings[10]': True, S + 'bSplice': True,
                   S + 'uiSpliceCount': 2},
}
