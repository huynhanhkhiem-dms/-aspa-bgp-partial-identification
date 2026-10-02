from synthetic_identification_stress import WIDTHS, N_PER_DIRECTION, SEED as LOCAL_SEED
from synthetic_quorum_stress import WIDTHS as Q_WIDTHS, N_EVENTS_PER_WIDTH, M_SOURCES, K_QUORUM, SEED as Q_SEED


def test_local_design_is_frozen():
    assert WIDTHS==(0.01,0.05,0.10,0.25,0.50)
    assert N_PER_DIRECTION==200_000
    assert LOCAL_SEED==20260914


def test_quorum_design_is_frozen():
    assert Q_WIDTHS==(0.01,0.05,0.10,0.25,0.50)
    assert N_EVENTS_PER_WIDTH==100_000
    assert M_SOURCES==8
    assert K_QUORUM==5
    assert Q_SEED==20260914


def test_robust_coupling_design_is_frozen():
    from synthetic_robust_coupling_stress import W, SHIFTS, N, M, K, Q, SEED
    assert W==0.35
    assert SHIFTS==[0.0,0.25,0.50,1.0,2.0]
    assert N==10_000
    assert M==8 and K==5 and Q==1
    assert SEED==20260914


def test_conformal_q_calibration_design_is_frozen():
    from conformal_q_calibration import M, ALPHA, N_CAL, N_REPS, SEED
    assert M==8
    assert ALPHA==0.05
    assert N_CAL==199
    assert N_REPS==20_000
    assert SEED==20260914
