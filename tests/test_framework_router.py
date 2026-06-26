import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from core.policy.framework_router import FrameworkRouter

def test_router_logic():
    router = FrameworkRouter()
    
    # 1. Test Band F0 (Low Delta, No OOL)
    case1 = {
        "vh_delta_identity": 0.01,
        "vl_delta_identity": 0.02,
        "vh_out_of_library_flag": False,
        "vl_out_of_library_flag": False,
        "cdrh3_length": 15,
        "vh_fr1": "A", "vh_fr2": "B", "vh_fr3": "C",
        "vl_fr1": "D", "vl_fr2": "E", "vl_fr3": "F"
    }
    res1 = router.route(case1)
    print(f"Case 1 (F0): {res1['framework_band']} -> {res1['route_id']}")
    assert res1['framework_band'] == 'F0'
    assert res1['route_id'] == 'ROUTE_I_MINIMAL'
    assert res1['has_full_fr123_pair'] == True

    # 2. Test Band F2 (p90 < Delta < p99)
    case2 = {
        "vh_delta_identity": 0.10, # p90 is 0.06
        "vl_delta_identity": 0.02,
        "vh_out_of_library_flag": False,
        "vl_out_of_library_flag": False,
        "cdrh3_length": 15,
        "vh_fr1": "A", "vh_fr2": "B", "vh_fr3": "C",
        "vl_fr1": "D", "vl_fr2": "E", "vl_fr3": "F"
    }
    res2 = router.route(case2)
    print(f"Case 2 (F2): {res2['framework_band']} -> {res2['route_id']}")
    assert res2['framework_band'] == 'F2'
    assert res2['route_id'] == 'ROUTE_III_FUNCTION_PRESERVE'

    # 3. Test Out of Library Override
    case3 = {
        "vh_delta_identity": 0.01,
        "vl_delta_identity": 0.02,
        "vh_out_of_library_flag": True,
        "vl_out_of_library_flag": False,
        "cdrh3_length": 15,
        "vh_fr1": "A", "vh_fr2": "B", "vh_fr3": "C",
        "vl_fr1": "D", "vl_fr2": "E", "vl_fr3": "F"
    }
    res3 = router.route(case3)
    print(f"Case 3 (OOL): Band={res3['framework_band']}, RiskCount={len(res3['risk_overrides'])}")
    # Band should be F2 or similar because out_of_library is False for F0/F1
    assert res3['framework_band'] == 'F2'
    assert any(o['id'] == 'HC_OUT_OF_LIBRARY_ALERT' for o in res3['risk_overrides'])

    # 4. Test Incomplete FR
    case4 = {
        "vh_delta_identity": 0.01,
        "vl_delta_identity": 0.02,
        "vh_out_of_library_flag": False,
        "vl_out_of_library_flag": False,
        "cdrh3_length": 15,
        "vh_fr1": "A", "vh_fr2": None, "vh_fr3": "C", # Missing FR2
        "vl_fr1": "D", "vl_fr2": "E", "vl_fr3": "F"
    }
    res4 = router.route(case4)
    print(f"Case 4 (Incomplete): has_full={res4['has_full_fr123_pair']}, RiskCount={len(res4['risk_overrides'])}")
    assert res4['has_full_fr123_pair'] == False
    assert any(o['id'] == 'HC_INCOMPLETE_FR' for o in res4['risk_overrides'])

    print("✅ All test cases passed!")

if __name__ == "__main__":
    test_router_logic()
