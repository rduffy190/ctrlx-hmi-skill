# Preview scenarios for example_screen_cutter.py:
#   python3 <skill>/scripts/preview.py build/CUT_Main.export example_preview_cutter.py build/preview
STATES = ['Stopped', 'Manual', 'Aborting', 'HomeCutter', 'Ready', 'WaitUpstream', 'Feed', 'Clamp', 'Mark', 'Cut',
          'Unclamp', 'Eject', 'EjectClear', 'Clearing', 'Cleared', 'Faulted']
ENUMS = {'E_CutterState': STATES}
S = 'GVL_Hmi.stCutterSts.'
base = {S + 'bAxisPowered': True, S + 'bSettingsOk': True, S + 'bMaterialSense': True, S + 'bLeftProx': True,
        S + 'eLastCutSide': 1, S + 'lrAxisPos': 1234.5, S + 'tStepElapsed': 'T#1S200MS',
        'GVL_Cfg.stCutter.uiCutLength': 400, 'GVL_Hmi.stCutterCmd.uiCutLength': 400}
SCENARIOS = {
    'running_feed': {**base, S + 'eState': STATES.index('Feed'), S + 'bOutputOccupied': True,
                     S + 'uiOutputPartId': 1042, S + 'uiOutputLength': 400, S + 'bMaterialLow': True,
                     'GVL_Cfg.stCutter.uiBatchQty': 20, S + 'uiBatchRemaining': 7},
    'manual': {**base, S + 'eState': STATES.index('Manual'), S + 'bUnclamped': True},
    'servo_fault': {**base, S + 'eState': STATES.index('Faulted'), S + 'uiFaultCode': 3,
                    S + 'eFaultState': STATES.index('Feed'), S + 'bAxisPowered': False,
                    S + 'dwDiagMain': 0xF2025, S + 'dwDiagDetail': 0x0},
    'wait_upstream': {**base, S + 'eState': STATES.index('WaitUpstream'), 'GVL_Cfg.stCutter.bWaitUpstream': True,
                      'GVL_Machine.astDiag[GVL_Const.STN_CUTTER].abWarnings[10]': True, S + 'bSplice': True,
                      S + 'uiSpliceCount': 2},
}
