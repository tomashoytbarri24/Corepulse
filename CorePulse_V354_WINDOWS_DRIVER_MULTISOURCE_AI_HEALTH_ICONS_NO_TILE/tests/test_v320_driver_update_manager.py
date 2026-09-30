from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.driver_update_manager import _hardware_ids, _match_update, _version_from_title


def test_hardware_id_exact_match():
    installed = [{
        'DeviceName': 'Example GPU',
        'DeviceID': r'PCI\VEN_10DE&DEV_1F11&SUBSYS_00000000\3&ABC',
        'HardwareIds': [r'PCI\VEN_10DE&DEV_1F11&SUBSYS_00000000', r'PCI\VEN_10DE&DEV_1F11'],
        'DriverVersion': '1.0.0.0',
    }]
    update = {'hardware_id': r'PCI\VEN_10DE&DEV_1F11&SUBSYS_00000000'}
    assert _match_update(update, installed)['DeviceName'] == 'Example GPU'


def test_hardware_ids_include_instance_prefix_without_inventing_ids():
    item = {'DeviceID': r'PCI\VEN_8086&DEV_1234\3&ABC', 'HardwareIds': []}
    ids = _hardware_ids(item)
    assert r'PCI\VEN_8086&DEV_1234' in ids


def test_version_only_when_title_contains_clear_version():
    assert _version_from_title('Intel - Extension - 31.0.101.5590') == '31.0.101.5590'
    assert _version_from_title('Vendor - Driver Update') is None
