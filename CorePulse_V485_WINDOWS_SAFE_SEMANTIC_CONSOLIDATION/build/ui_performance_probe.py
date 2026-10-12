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
started=time.perf_counter()
app=Probe()
report={'constructor_ms': (time.perf_counter()-started)*1000}
try:
    app._startup_gate_active=False
    if app._startup_gate is not None:
        app._startup_gate.close()
        app._startup_gate=None
    app.deiconify()
    app.update()
    app.workspace_background.refresh()
    profiler=cProfile.Profile()
    profiler.enable()
    times=[]
    for _ in range(5):
        started=time.perf_counter()
        app.workspace_background.refresh()
        times.append((time.perf_counter()-started)*1000)
    profiler.disable()
    report['dashboard_refresh_ms']=times
    report['sidebar_labels']=[app._theme_toggle_button.cget('text'),app._ai_button.cget('text')]
    icon=app._health_icon
    label=app._status_cards[0]._cp_title_label
    report['health_icon_right']=icon.winfo_rootx()+icon.winfo_width()
    report['health_label_left']=label.winfo_rootx()
    out=io.StringIO()
    pstats.Stats(profiler,stream=out).sort_stats('cumulative').print_stats(12)
    report['profile']=out.getvalue()
    started=time.perf_counter()
    app.run_cleanup()
    app.update()
    app.workspace_background.refresh()
    report['cleanup_open_ms']=(time.perf_counter()-started)*1000
    started=time.perf_counter()
    for _ in range(5):
        app.workspace_background.refresh()
    report['cleanup_refresh_avg_ms']=(time.perf_counter()-started)*200
    output=root / 'build' / ('ui_' + (sys.argv[1] if len(sys.argv)>1 else 'probe') + '.json')
    output.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True),flush=True)
finally:
    app.is_running=False
    if app.session_recovery is not None:
        app.session_recovery.mark_clean_shutdown()
    app.destroy()
