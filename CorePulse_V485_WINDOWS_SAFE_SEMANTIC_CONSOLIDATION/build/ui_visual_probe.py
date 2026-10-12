import os, sys, time, json, cProfile, pstats, io
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
sys.dont_write_bytecode = True
for key, name in [('COREPULSE_DATA_DIR','data'),('COREPULSE_CONFIG_DIR','config'),('COREPULSE_CACHE_DIR','cache'),('COREPULSE_LOG_DIR','logs')]:
    os.environ[key] = str(root / 'build' / 'ui_probe' / name)
os.environ['COREPULSE_RUNTIME_BOOTSTRAPPED'] = '1'
os.environ['MPLCONFIGDIR'] = str(root / 'build' / 'ui_probe' / 'matplotlib')
from main import App
class Probe(App):
    def _after_first_frame(self):
        pass
app=Probe()
app.title('CorePulse V451 - revision visual')
app.after(500,app._reveal_main_window)
def finish():
    app.is_running=False
    if app.session_recovery is not None:
        app.session_recovery.mark_clean_shutdown()
    app.destroy()
app.protocol('WM_DELETE_WINDOW',finish)
app.after(600000,finish)
app.after(1800,app.run_cleanup)
app.after(2200,lambda: print('VISUAL PROBE', app.state(), app.winfo_ismapped(), flush=True))
app.mainloop()
