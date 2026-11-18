// Types the transfer screen reads: the state enum (text list) and the settings struct (settings page).
TYPE E_TransferState :
(
    Stopped := 0,
    Manual,
    Aborting,
    Home,
    Ready,
    MoveToPick,
    Pick,
    MoveToPlace,
    Place,
    WaitRelease,
    Clearing,
    Cleared,
    Faulted := 99
) UINT;
END_TYPE

TYPE E_LiftPos :
(
    Hold := 0,
    Up,
    Middle,
    Down
) UINT;
END_TYPE

TYPE ST_Dynamics :
STRUCT
    lrVel   : LREAL;
    lrAcc   : LREAL;
    lrDec   : LREAL;
    lrJerk  : LREAL;
END_STRUCT
END_TYPE

TYPE ST_TransferCfg :
STRUCT
    lrPickPos       : LREAL;            // carriage position at pick (mm)
    lrPlacePos      : LREAL;            // carriage position at place (mm)
    stDyn           : ST_Dynamics;      // normal moves
    stDynSlow       : ST_Dynamics;      // moves with a part in the gripper
    tGripTimeout    : TIME;             // gripper close/open time limit
    tVacuumTimeout  : TIME;             // vacuum build-up time limit
    uiGripRetries   : UINT;             // grip attempts before a fault
    bVacuumCheck    : BOOL;             // check vacuum before lifting
    bWaitDownstream : BOOL;             // hold the part until downstream is ready
END_STRUCT
END_TYPE
