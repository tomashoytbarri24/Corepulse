"""Local Direct3D 11 smoke test; run manually, not from pytest."""
import ctypes
import mmap
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import psutil

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import overlay


def main():
    state_map = mmap.mmap(-1, ctypes.sizeof(overlay._GameState), tagname=overlay.GAME_STATE_NAME)
    actions = mmap.mmap(-1, 24, tagname=overlay.GAME_ACTION_NAME)
    actions[:] = bytes(24)
    output = Path(__file__).resolve().parents[1] / 'overlay_probe_result.json'
    error_log = tempfile.TemporaryFile()
    process = subprocess.Popen(
        [sys.executable, '-B', '-m', 'core.benchmark_gpu', '--profile', 'quick',
         '--output', str(output)],
        cwd=str(Path(__file__).resolve().parents[1]),
        stdout=subprocess.DEVNULL, stderr=error_log,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    try:
        deadline = time.monotonic() + 20
        modules = set()
        game_pid = process.pid
        while time.monotonic() < deadline and process.poll() is None:
            candidates = [psutil.Process(process.pid)]
            candidates.extend(candidates[0].children(recursive=True))
            for candidate in candidates:
                try:
                    modules = {Path(item.path).name.casefold()
                               for item in candidate.memory_maps(grouped=False) if item.path}
                except psutil.Error:
                    continue
                if 'd3d11.dll' in modules:
                    game_pid = candidate.pid
                    break
            if game_pid != process.pid or 'd3d11.dll' in modules:
                break
            time.sleep(0.25)
        error_log.seek(0)
        print('PID', game_pid, 'D3D11', 'd3d11.dll' in modules,
              'status', process.poll(), 'error', error_log.read(500), flush=True)
        if 'd3d11.dll' not in modules:
            return 2
        snapshot = overlay._GameState()
        snapshot.seqBegin = snapshot.seqEnd = 2
        snapshot.magic = overlay.GAME_MAGIC
        snapshot.targetPid = game_pid
        snapshot.flags = 1 | 16
        snapshot.cpu = b'10%'
        snapshot.gpu = b'20%'
        snapshot.ram = b'30%'
        snapshot.fps = b'N/A'
        snapshot.cpuName = b'CorePulse Direct3D test'
        snapshot.gpuName = b'Direct3D 11'
        def publish():
            tick = ctypes.windll.kernel32.GetTickCount64
            tick.restype = ctypes.c_ulonglong
            snapshot.tickMs = tick()
            state_map[:] = ctypes.string_at(ctypes.addressof(snapshot), ctypes.sizeof(snapshot))
        publish()
        result = overlay._inject_game_hook(game_pid)
        print('LOAD', result, flush=True)
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline and process.poll() is None:
            publish()
            hooked = int.from_bytes(actions[4:8], 'little', signed=True)
            error = int.from_bytes(actions[8:12], 'little', signed=True)
            fps = int.from_bytes(actions[12:16], 'little', signed=True)
            if hooked == game_pid:
                print('FRAMES', hooked, error, fps, flush=True)
                time.sleep(0.5)
                from PySide6.QtGui import QGuiApplication
                app = QGuiApplication.instance() or QGuiApplication([])
                screen = app.primaryScreen()
                if screen:
                    # Repeat on a 1920x1080 and a 2560x1440 display. The
                    # script does not change Windows display configuration.
                    geometry = screen.geometry()
                    resolution = f'{geometry.width()}x{geometry.height()}'
                    root = Path(__file__).resolve().parents[1]
                    for kind, flags in (('osd', 1 | 4 | 16), ('panel', 1 | 2 | 16)):
                        snapshot.flags = flags
                        publish()
                        time.sleep(0.8)
                        # Screen-grab may not capture exclusive fullscreen;
                        # verify visually in-game as well.
                        path = root / f'overlay_probe_{kind}_{resolution}.png'
                        print('SCREENSHOT', kind, resolution,
                              screen.grabWindow(0).save(str(path)), path, flush=True)
                return 0
            time.sleep(0.25)
        print('NO_FRAMES', 'process_status', process.poll(),
              'error', int.from_bytes(actions[8:12], 'little', signed=True), flush=True)
        return 1
    finally:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
        actions.close()
        state_map.close()
        output.unlink(missing_ok=True)
        error_log.close()


if __name__ == '__main__':
    raise SystemExit(main())
