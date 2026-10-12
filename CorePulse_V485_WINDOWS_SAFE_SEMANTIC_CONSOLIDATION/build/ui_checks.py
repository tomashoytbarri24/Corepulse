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
import customtkinter as ctk
from gui.ui_consistency import refresh_navigation_state
from gui.internal_navigation import show_dashboard
from gui.flat_workspace_page import _accent_strip, PAGE_TAG
app=Probe()
report={}
try:
    app._reveal_main_window()
    app.update()
    for context in ('themes','ai','cleanup','dashboard'):
        refresh_navigation_state(app,context)
        assert app._theme_toggle_button.cget('text')=='Temas'
        assert app._ai_button.cget('text')=='CorePulse AI'
    report['navigation_labels']='OK'
    geometry=[]
    for scale in (1.0, 1.25, 1.5):
        ctk.set_widget_scaling(scale)
        app.update_idletasks()
        icon=app._health_icon
        label=app._status_cards[0]._cp_title_label
        right=icon.winfo_rootx()+icon.winfo_width()
        left=label.winfo_rootx()
        assert right <= left, (scale,right,left)
        geometry.append({'scale':scale,'gap_px':left-right})
    report['health_icon_spacing']=geometry
    ctk.set_widget_scaling(1.0)
    app.update_idletasks()
    routes=[('cleanup',app.run_cleanup),('themes',app.open_themes),('ai',app.open_ai_center),
            ('network',app.open_network_details),('tweaks',app.open_windows_tweaks),
            ('health_center',app.open_health_center),('benchmark',app.open_benchmark),
            ('alerts',app.open_smart_alert_window),('history',app.open_alert_history_window),
            ('trends',app.open_session_trends_window)]
    pages=[]
    report['pages']=pages
    for name,callback in routes:
        start=time.perf_counter()
        callback()
        app.update_idletasks()
        app.update()
        app.workspace_background.refresh()
        host=getattr(app,'_internal_page_host',None)
        assert getattr(app,'_active_internal_page',None)==name, (name,getattr(app,'_active_internal_page',None))
        count=0
        pending=[host]
        while pending:
            widget=pending.pop()
            if getattr(widget,'_cp_preserve_surface',False) or _accent_strip(widget):
                continue
            if isinstance(widget,ctk.CTkFrame) and widget.winfo_ismapped():
                assert widget.cget('border_width')==0, (name,str(widget))
                assert widget.cget('corner_radius')==0, (name,str(widget))
                x=widget.winfo_rootx()-app.winfo_rootx()
                y=widget.winfo_rooty()-app.winfo_rooty()
                w,h=widget.winfo_width(),widget.winfo_height()
                if w>8 and h>8 and x+w>0 and y+h>0 and x<app.winfo_width() and y<app.winfo_height():
                    assert widget._canvas.find_withtag(PAGE_TAG), (name,str(widget),'missing surface')
                count+=1
            if isinstance(widget,(ctk.CTkFrame,ctk.CTkScrollableFrame)) or type(widget).__name__ in ('Frame','Canvas'):
                pending.extend(widget.winfo_children())
        pages.append({'name':name,'flat_containers':count,'first_open_ms':round((time.perf_counter()-start)*1000,1)})
    report['pages']=pages
    show_dashboard(app)
    app.run_cleanup()
    app.update_idletasks()
    app.workspace_background.refresh()
    report['cached_cleanup']='OK'
    report['status']='PASS'
finally:
    (root/'build'/'ui_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True),flush=True)
    app.is_running=False
    if app.session_recovery is not None:
        app.session_recovery.mark_clean_shutdown()
    app.destroy()
