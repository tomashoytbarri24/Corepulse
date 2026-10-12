"""Carga autocontenida de LibreHardwareMonitor oficial.

CorePulse prioriza la release estable oficial de LibreHardwareMonitor sobre el
DLL empaquetado por wrappers de terceros. Esto evita que una actualización del
wrapper cambie silenciosamente la versión real del motor de sensores.

La release se descarga una sola vez desde GitHub a ``%LOCALAPPDATA%`` y se
verifica por SHA-256. Si no hay red, CorePulse conserva el proveedor empaquetado
como fallback y sigue respetando REAL_OR_NA.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import sys
import tempfile
import urllib.request
import zipfile

LHM_VERSION = "0.9.6"
LHM_ASSET_URL = (
    "https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/"
    "releases/download/v0.9.6/LibreHardwareMonitor.zip"
)
# Digest publicado para el asset oficial v0.9.6 LibreHardwareMonitor.zip.
LHM_ASSET_SHA256 = "086d9f1b5a99e643edc2cfaaac16051685b551e4c5ac0b32a57c58c0e529c001"
_DLL_DIR_HANDLES: list[object] = []


def _base_dir() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "CorePulse" / "vendor" / "LibreHardwareMonitor" / f"v{LHM_VERSION}"
    return Path(tempfile.gettempdir()) / "CorePulse" / "vendor" / "LibreHardwareMonitor" / f"v{LHM_VERSION}"


def vendor_dir() -> Path:
    return _base_dir()


def dll_path() -> Path:
    return vendor_dir() / "LibreHardwareMonitorLib.dll"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().lower()


def _download(url: str, target: Path) -> None:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "CorePulse/381 LibreHardwareMonitor bootstrap",
            "Accept": "application/octet-stream,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=45) as response, target.open("wb") as out:
        shutil.copyfileobj(response, out)


def ensure_official_lhm(*, allow_download: bool = True) -> dict:
    """Asegura que la release oficial esté disponible localmente.

    Nunca sustituye datos por estimaciones. Si falla la descarga o validación,
    devuelve ``ok=False`` y el llamador puede degradar al proveedor secundario.
    """
    root = vendor_dir()
    dll = dll_path()
    if dll.is_file():
        return {
            "ok": True,
            "version": LHM_VERSION,
            "dll": str(dll),
            "source": "cached",
            "error": None,
        }
    if not allow_download:
        return {
            "ok": False,
            "version": LHM_VERSION,
            "dll": None,
            "source": None,
            "error": "LibreHardwareMonitor oficial no está descargado.",
        }

    root.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="corepulse_lhm_"))
    archive = work / "LibreHardwareMonitor.zip"
    extracted = work / "extract"
    try:
        _download(LHM_ASSET_URL, archive)
        digest = _sha256(archive)
        if digest != LHM_ASSET_SHA256:
            raise RuntimeError(
                "SHA-256 inesperado para LibreHardwareMonitor v0.9.6 "
                f"({digest}). Se rechazó el binario."
            )
        extracted.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive, "r") as zf:
            zf.extractall(extracted)

        matches = list(extracted.rglob("LibreHardwareMonitorLib.dll"))
        if not matches:
            raise RuntimeError("El asset oficial no contiene LibreHardwareMonitorLib.dll.")
        source_root = matches[0].parent
        staging = root.with_name(root.name + ".staging")
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(source_root, staging)
        if root.exists():
            shutil.rmtree(root, ignore_errors=True)
        staging.replace(root)
        dll = dll_path()
        if not dll.is_file():
            raise RuntimeError("La extracción terminó sin LibreHardwareMonitorLib.dll.")
        return {
            "ok": True,
            "version": LHM_VERSION,
            "dll": str(dll),
            "source": "downloaded_official_github_release",
            "error": None,
        }
    except Exception as exc:
        return {
            "ok": False,
            "version": LHM_VERSION,
            "dll": None,
            "source": None,
            "error": f"{type(exc).__name__}: {exc}",
        }
    finally:
        shutil.rmtree(work, ignore_errors=True)


def load_official_computer_class(*, allow_download: bool = True):
    """Carga ``LibreHardwareMonitor.Hardware.Computer`` desde la release oficial."""
    if os.name != "nt":
        return None, {"ok": False, "version": LHM_VERSION, "dll": None, "source": None, "error": "Windows requerido"}
    state = ensure_official_lhm(allow_download=allow_download)
    if not state.get("ok"):
        return None, state

    root = vendor_dir()
    dll = dll_path()
    try:
        # Permite resolver dependencias nativas/administradas que acompañan al DLL.
        root_s = str(root)
        if root_s not in sys.path:
            sys.path.insert(0, root_s)
        current_path = os.environ.get("PATH", "")
        if root_s.casefold() not in current_path.casefold():
            os.environ["PATH"] = root_s + os.pathsep + current_path
        if os.name == "nt" and hasattr(os, "add_dll_directory"):
            try:
                _DLL_DIR_HANDLES.append(os.add_dll_directory(root_s))
            except Exception:
                pass

        import clr
        clr.AddReference(str(dll))
        from LibreHardwareMonitor.Hardware import Computer
        state = dict(state)
        state["loaded"] = True
        return Computer, state
    except Exception as exc:
        state = dict(state)
        state["loaded"] = False
        state["error"] = f"{type(exc).__name__}: {exc}"
        return None, state
