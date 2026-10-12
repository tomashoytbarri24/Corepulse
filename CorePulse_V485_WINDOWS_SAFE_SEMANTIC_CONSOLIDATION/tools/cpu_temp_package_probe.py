"""Sonda aislada del proveedor HardwareMonitor histórico.

No carga core.lhm_provider ni LibreHardwareMonitor oficial. Se ejecuta en un
subproceso limpio para reproducir la ruta de sensores usada por CorePulse V362.
"""
from __future__ import annotations

import argparse
import json
import time


def _enum_name(value) -> str:
    text = str(value or "")
    return text.split(".")[-1].strip() if "." in text else text.strip()


def _number(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if 5.0 <= value <= 115.0 else None


def _score(row: dict) -> int:
    name = str(row.get("sensor") or "").casefold()
    hw = str(row.get("hardware") or "").casefold()
    typ = str(row.get("hardware_type") or "").casefold()
    ident = str(row.get("identifier") or "").casefold()
    text = f"{name} {hw} {typ} {ident}"
    if any(x in text for x in ("gpu", "nvidia", "radeon gpu", "nvme", "ssd", "hdd", "storage", "battery", "ambient", "pch", "vrm", "mos")):
        return -1000
    score = 100 if typ == "cpu" else 0
    if "/cpu/" in ident or ident.startswith("/cpu"):
        score += 90
    if any(x in hw for x in ("ryzen", "processor", "cpu")):
        score += 40
    for token, pts in (
        ("cpu package", 170), ("cpu (tctl/tdie)", 165), ("tctl/tdie", 160),
        ("cpu core", 150), ("core max", 145), ("core average", 135),
        ("tdie", 125), ("tctl", 120), ("cpu temperature", 115), ("cpu temp", 115),
        ("package", 90), ("cpu", 85),
    ):
        if token in name:
            score += pts
            break
    return score


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--json-only", action="store_true")
    parser.parse_args()
    computer = None
    try:
        import HardwareMonitor
        from HardwareMonitor.Hardware import Computer
        computer = Computer()
        computer.IsCpuEnabled = True
        computer.IsMotherboardEnabled = True
        computer.IsControllerEnabled = True
        computer.Open()
        rows = []

        def walk(hw):
            try:
                hw.Update()
            except Exception:
                pass
            hname = str(getattr(hw, "Name", "") or "")
            htype = _enum_name(getattr(hw, "HardwareType", ""))
            try:
                sensors = list(hw.Sensors)
            except Exception:
                sensors = []
            for sensor in sensors:
                if _enum_name(getattr(sensor, "SensorType", "")).casefold() != "temperature":
                    continue
                value = _number(getattr(sensor, "Value", None))
                if value is None:
                    continue
                row = {
                    "value": round(value, 1),
                    "sensor": str(getattr(sensor, "Name", "") or ""),
                    "hardware": hname,
                    "hardware_type": htype,
                    "identifier": str(getattr(sensor, "Identifier", "") or ""),
                    "timestamp": time.time(),
                }
                row["score"] = _score(row)
                if row["score"] >= 90:
                    rows.append(row)
            try:
                children = list(hw.SubHardware)
            except Exception:
                children = []
            for child in children:
                walk(child)

        for hw in list(computer.Hardware):
            walk(hw)
        if not rows:
            print(json.dumps({"value": None, "error": "No valid CPU temperature sensor"}, ensure_ascii=False))
            return 2
        chosen = max(rows, key=lambda r: (r["score"], r["value"]))
        chosen.pop("score", None)
        print(json.dumps(chosen, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"value": None, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False))
        return 2
    finally:
        if computer is not None:
            try:
                computer.Close()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
