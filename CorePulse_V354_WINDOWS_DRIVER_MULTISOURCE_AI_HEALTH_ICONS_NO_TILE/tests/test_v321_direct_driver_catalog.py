from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.driver_update_manager import _version_from_title, _is_newer, _scan_targets, _query_terms_for_target


def test_version_parser_catalog_titles():
    assert _version_from_title("NVIDIA - Display - 32.0.15.7317") == "32.0.15.7317"
    assert _version_from_title("Intel net Driver Update (24.40.0.4)") == "24.40.0.4"
    assert _version_from_title("Vendor Driver") is None


def test_version_compare_numeric():
    assert _is_newer("32.0.15.7317", "32.0.15.7141")
    assert not _is_newer("1.2.3", "1.2.3")
    assert not _is_newer("1.2.2", "1.2.3")


def test_scan_targets_prefers_real_hardware_and_skips_inbox():
    rows = [
        {"DeviceName":"GPU","DriverVersion":"1.0.0.0","HardwareIds":["PCI\\VEN_10DE&DEV_1F11"],"hardware_priority":100,"microsoft_inbox_generic":False},
        {"DeviceName":"WAN Miniport","DriverVersion":"1.0.0.0","HardwareIds":["ROOT\\MS_NDISWANIP"],"hardware_priority":0,"microsoft_inbox_generic":True},
    ]
    targets = _scan_targets(rows)
    assert len(targets) == 1
    assert targets[0]["device_name"] == "GPU"


def test_deep_query_terms_include_multiple_ids_and_model():
    row = {
        "DeviceName": "Intel(R) Wireless Bluetooth(R)",
        "DriverProviderName": "Intel",
        "HardwareIds": [
            "USB\\VID_8087&PID_0033&REV_0000",
            "USB\\VID_8087&PID_0033",
        ],
    }
    terms = _query_terms_for_target(row)
    queries = [x["query"] for x in terms]
    assert any(q.startswith("USB\\VID_8087&PID_0033") for q in queries)
    assert any("Intel(R) Wireless Bluetooth(R)" in q for q in queries)


def test_monitor_is_a_scan_target_even_without_priority():
    rows = [{
        "DeviceName": "Generic Monitor",
        "DriverProviderName": "Microsoft",
        "DriverVersion": "10.0.26100.1",
        "HardwareIds": ["MONITOR\\CMN15D2"],
        "hardware_priority": 0,
        "microsoft_inbox_generic": False,
    }]
    targets = _scan_targets(rows)
    assert len(targets) == 1
    assert targets[0]["hardware_id"].startswith("MONITOR\\")
