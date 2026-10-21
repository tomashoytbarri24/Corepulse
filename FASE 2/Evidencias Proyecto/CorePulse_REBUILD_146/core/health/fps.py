"""Lectura certificada de FPS desde RTSS Shared Memory, sin estimaciones."""
from __future__ import annotations

import ctypes
import os
import struct


RTSS_MEMORY_NAME = "RTSSSharedMemoryV2"
RTSS_SIGNATURE = 0x52545353
FILE_MAP_READ = 0x0004
MAX_FRESHNESS_MS = 2500


class RTSSFPSReader:
    """Lee FPS de un PID concreto usando un mapeo de solo lectura de RTSS."""

    def __init__(self):
        self._kernel = None
        self._handle = None
        self._base = None
        self._size = 0
        self._header = None
        self._error = "RTSS aún no está conectado."

    @staticmethod
    def _mapped_size(kernel, address):
        buffer = ctypes.create_string_buffer(64)
        if not kernel.VirtualQuery(address, buffer, len(buffer)):
            return 0
        pointer_size = ctypes.sizeof(ctypes.c_void_p)
        base = ctypes.c_void_p.from_buffer_copy(buffer.raw, 0).value or 0
        region_offset = 24 if pointer_size == 8 else 12
        region = ctypes.c_size_t.from_buffer_copy(buffer.raw, region_offset).value
        return max(0, base + region - address)

    def _open(self):
        if self._base:
            return True
        if os.name != "nt":
            self._error = "Los FPS directos desde RTSS solo están disponibles en Windows."
            return False
        try:
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.OpenFileMappingW.argtypes = (ctypes.c_uint32, ctypes.c_int, ctypes.c_wchar_p)
            kernel.OpenFileMappingW.restype = ctypes.c_void_p
            kernel.MapViewOfFile.argtypes = (ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32,
                                              ctypes.c_uint32, ctypes.c_size_t)
            kernel.MapViewOfFile.restype = ctypes.c_void_p
            kernel.UnmapViewOfFile.argtypes = (ctypes.c_void_p,)
            kernel.UnmapViewOfFile.restype = ctypes.c_int
            kernel.CloseHandle.argtypes = (ctypes.c_void_p,)
            kernel.CloseHandle.restype = ctypes.c_int
            kernel.VirtualQuery.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t)
            kernel.VirtualQuery.restype = ctypes.c_size_t
            handle = kernel.OpenFileMappingW(FILE_MAP_READ, False, RTSS_MEMORY_NAME)
            if not handle:
                self._error = "RTSS Shared Memory no está disponible."
                return False
            base = kernel.MapViewOfFile(handle, FILE_MAP_READ, 0, 0, 0)
            if not base:
                kernel.CloseHandle(handle)
                self._error = "No se pudo abrir RTSS Shared Memory en modo lectura."
                return False
            size = self._mapped_size(kernel, int(base))
            if size < 36:
                kernel.UnmapViewOfFile(base)
                kernel.CloseHandle(handle)
                self._error = "La memoria compartida de RTSS es demasiado pequeña."
                return False
            header = struct.unpack_from("<9I", ctypes.string_at(base, 36))
            signature, version, app_size, app_offset, app_count = header[:5]
            if (signature != RTSS_SIGNATURE or version >> 16 != 2 or
                    app_size < 284 or app_size > 1024 * 1024 or
                    app_count > 4096 or app_offset < 36 or
                    app_offset + app_size * app_count > size):
                kernel.UnmapViewOfFile(base)
                kernel.CloseHandle(handle)
                self._error = "La estructura RTSS no coincide con Shared Memory V2."
                return False
            self._kernel, self._handle, self._base = kernel, handle, int(base)
            self._size = size
            self._header = (app_size, app_offset, app_count)
            self._error = ""
            return True
        except (AttributeError, OSError, OverflowError, TypeError, ValueError, struct.error):
            self._error = "No se pudo validar RTSS Shared Memory."
            self.close()
            return False

    def snapshot(self, expected_pid=None, freshness_ms=MAX_FRESHNESS_MS):
        """Devuelve un dato solo si RTSS reporta una muestra fresca del juego esperado."""
        if isinstance(expected_pid, bool):
            expected_pid = None
        try:
            expected_pid = int(expected_pid) if expected_pid is not None else None
        except (TypeError, ValueError, OverflowError):
            expected_pid = None
        if expected_pid is None or expected_pid <= 0:
            return self._unavailable("No hay un proceso de juego activo identificado.")
        if not self._open():
            return self._unavailable(self._error)
        try:
            app_size, app_offset, app_count = self._header
            self._kernel.GetTickCount.argtypes = ()
            self._kernel.GetTickCount.restype = ctypes.c_uint32
            now_tick = int(self._kernel.GetTickCount())
            for index in range(app_count):
                address = self._base + app_offset + index * app_size
                pid, = struct.unpack_from("<I", ctypes.string_at(address, 4))
                if pid != expected_pid:
                    continue
                row = ctypes.string_at(address, min(app_size, 284))
                name = row[4:264].split(b"\0", 1)[0].decode("mbcs", errors="replace")
                time0, time1, frames, frame_time_us = struct.unpack_from("<4I", row, 268)
                age_ms = (now_tick - time1) & 0xFFFFFFFF if time1 else 0xFFFFFFFF
                if age_ms > max(0, min(int(freshness_ms), MAX_FRESHNESS_MS)):
                    return self._unavailable("RTSS no tiene una muestra fresca para este juego.")
                if not 0 < frame_time_us < 1_000_000:
                    return self._unavailable("RTSS no reporta un frametime válido para este juego.")
                instant_fps = 1_000_000.0 / frame_time_us
                elapsed_ms = (time1 - time0) & 0xFFFFFFFF
                average_fps = (1000.0 * frames / elapsed_ms
                               if time0 and time1 and elapsed_ms > 0 and frames > 0 else None)
                fps = average_fps if average_fps is not None and 0 < average_fps <= 2000 else instant_fps
                if not 0 < fps <= 2000:
                    return self._unavailable("RTSS no reporta FPS válidos para este juego.")
                return {
                    "quality": "VALID_RTSS", "fps": round(fps, 1),
                    "fps_instant": round(instant_fps, 1),
                    "frametime_ms": round(frame_time_us / 1000.0, 3),
                    "pid": pid, "process_name": name,
                    "age_ms": age_ms, "source": "RTSS Shared Memory",
                    "reason": "",
                }
            return self._unavailable("RTSS no reporta una muestra para el proceso activo.")
        except (OSError, OverflowError, TypeError, ValueError, struct.error):
            self.close()
            return self._unavailable("La lectura de RTSS falló; FPS queda como N/A.")

    @staticmethod
    def _unavailable(reason):
        return {
            "quality": "UNAVAILABLE", "fps": None, "fps_instant": None,
            "frametime_ms": None, "pid": None, "process_name": None,
            "age_ms": None, "source": "RTSS Shared Memory", "reason": reason,
        }

    def close(self):
        kernel, handle, base = self._kernel, self._handle, self._base
        self._handle = self._base = None
        self._kernel = None
        self._size = 0
        self._header = None
        if kernel is not None:
            try:
                if base:
                    kernel.UnmapViewOfFile(ctypes.c_void_p(base))
            except (AttributeError, OSError, TypeError, ValueError):
                pass
            try:
                if handle:
                    kernel.CloseHandle(ctypes.c_void_p(handle))
            except (AttributeError, OSError, TypeError, ValueError):
                pass
