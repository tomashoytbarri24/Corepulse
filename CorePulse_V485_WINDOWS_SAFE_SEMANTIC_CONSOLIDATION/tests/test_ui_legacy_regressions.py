"""Regresiones históricas agrupadas en V481 sin eliminar pruebas."""
from __future__ import annotations


# ===== Regresión test_v424_sidebar_hover_contract (original conservado íntegramente) =====

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SidebarHoverContractTests(unittest.TestCase):
    def test_no_transparent_hover_colors_in_any_python_source(self):
        failures = []
        scanned = 0
        for source in ROOT.rglob('*.py'):
            scanned += 1
            tree = ast.parse(source.read_text(encoding='utf-8'), filename=str(source))
            for call in ast.walk(tree):
                if not isinstance(call, ast.Call):
                    continue
                for kw in call.keywords:
                    if kw.arg != 'hover_color' or not isinstance(kw.value, ast.Constant):
                        continue
                    if isinstance(kw.value.value, str) and kw.value.value.lower() == 'transparent':
                        failures.append((str(source.relative_to(ROOT)), call.lineno))
        self.assertGreater(scanned, 100)
        self.assertEqual(failures, [], f'CTkButton no admite hover_color transparente: {failures}')

    def test_personalizacion_directly_on_sidebar(self):
        source = (ROOT / 'gui' / 'dashboard.py').read_text(encoding='utf-8')
        self.assertIn('app._personalization_block = None', source)
        self.assertIn('app._theme_toggle_button = ctk.CTkButton(\n        app.sidebar,', source)
        self.assertIn('app._ai_button = ctk.CTkButton(\n        app.sidebar,', source)

    def test_initial_sidebar_button_hover_fallback_is_valid(self):
        source = (ROOT / 'main.py').read_text(encoding='utf-8')
        for attr in ('btn_overlay', 'btn_benchmark', 'btn_diagnostic', 'btn_health_center',
                     'btn_cleanup', 'btn_tweaks', 'btn_network', 'btn_smart_alerts',
                     'btn_alert_history', 'btn_session_trends'):
            self.assertIn(f'self.{attr} = ctk.CTkButton', source)
        self.assertIn("hover_color=role_color('sidebar'), hover=False", source)


if __name__ == '__main__':
    unittest.main()



# ===== Regresión test_v425_native_sidebar_surface (original conservado íntegramente) =====
import ast
import importlib.util
import tkinter as tk
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('workspace_background', ROOT/'gui'/'workspace_background.py')
# Import real por nombre de ruta, sin mutar el resto de la aplicación.
import sys
sys.path.insert(0, str(ROOT))
workspace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workspace)


class NativeSidebarSurfaceTests(unittest.TestCase):
    def test_pixel_matching_full_native_surface(self):
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f'X11 no disponible: {exc}')
        root.withdraw()
        try:
            sizes = [(1024,720),(1500,900),(1700,970)]
            palettes = [
                ('#06111f', '#0d1828', '#1b3048', '#14b8ff'),
                ('#120d1d', '#1d162c', '#493762', '#a970ff'),
                ('#101214', '#191c1f', '#3a4147', '#8aa4b8'),
            ]
            samples=0
            for width,height in sizes:
                canvas=tk.Canvas(root, width=width, height=height, highlightthickness=0)
                for palette in palettes:
                    workspace.render_native_workspace(
                        canvas, x=0,y=0,width=width,height=height,
                        full_width=width,full_height=height, tag='native',
                        palette=palette, workspace_left=315)
                    for x in (35, 95, 155, 225, 280, 360, 510):
                        for y in (60, 140, 214, 275, 390, 590, 770):
                            if y >= height: continue
                            indices=canvas.find_overlapping(x,y+2,x,y+2)
                            colors=[canvas.itemcget(item,'fill') for item in indices]
                            expected=colors[-1]
                            actual=workspace.native_surface_color_at(
                                x,y+2,width,height,palette=palette,workspace_left=315)
                            self.assertEqual(actual,expected, (width,height,x,y,palette))
                            samples+=1
                canvas.destroy()
            self.assertGreater(samples,300)
        finally:
            root.destroy()

    def test_sidebar_controls_are_explicitly_integrated(self):
        main=(ROOT/'gui'/'dashboard.py').read_text(encoding='utf-8')
        surface=(ROOT/'gui'/'workspace_background.py').read_text(encoding='utf-8')
        self.assertIn('app._personalization_block = None', main)
        self.assertIn('app.workspace_background.register_page(app.sidebar, max_depth=2)',main)
        self.assertIn('def _paint_sidebar_controls(self):',surface)
        self.assertIn('self._paint_sidebar_controls()', surface)
        self.assertIn('if active:',surface)
        self.assertIn('canvas.delete(_SIDEBAR_CONTROL_TAG)',surface)

    def test_no_transparent_hover_color_in_constructors_or_configure_calls(self):
        for file in (ROOT/'main.py', ROOT/'gui'/'dashboard.py', ROOT/'gui'/'dashboard_layout.py', ROOT/'gui'/'workspace_background.py'):
            tree=ast.parse(file.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node,ast.Call):
                    for kw in node.keywords:
                        if kw.arg=='hover_color' and isinstance(kw.value,ast.Constant):
                            self.assertNotEqual(kw.value.value,'transparent',str(file))


if __name__ == '__main__':
    unittest.main()

# Un smoke test adicional que usa Tk real en Xvfb con controles compatibles
# (no requiere importar CustomTkinter, ausente de este entorno Linux).
class SidebarWidgetPaintSmoke(unittest.TestCase):
    def test_button_and_label_inherit_first_layer_without_hiding_active(self):
        class CTkButton(tk.Frame):
            def __init__(self, parent, fg='transparent'):
                super().__init__(parent, width=200, height=38)
                self.props={'fg_color': fg, 'bg_color': 'transparent', 'hover_color':'#06111f'}
                self._canvas=tk.Canvas(self, bd=0, highlightthickness=0, width=200, height=38)
                self._canvas.pack(fill='both',expand=True)
                self._text_label=tk.Label(self, text='Prueba', bg='#000000')
                self._text_label.place(x=30,y=8)
            def cget(self,key):
                return self.props[key] if key in self.props else super().cget(key)
            def configure(self,**kwargs):
                self.props.update(kwargs)

        class CTkLabel(tk.Frame):
            def __init__(self,parent):
                super().__init__(parent,width=200,height=20)
                self.props={'fg_color':'transparent','bg_color':'transparent'}
                self._canvas=tk.Canvas(self,bd=0,highlightthickness=0,width=200,height=20)
                self._canvas.pack(fill='both',expand=True)
                self._text_label=tk.Label(self,text='MONITOREO',bg='#000000')
                self._text_label.place(x=10,y=2)
            def cget(self,key):
                return self.props[key] if key in self.props else super().cget(key)
            def configure(self,**kwargs):
                self.props.update(kwargs)

        root=tk.Tk()
        root.geometry('1024x720+1+1')
        try:
            root.sidebar=tk.Frame(root,width=260,height=550)
            root.sidebar.place(x=15,y=50)
            label=CTkLabel(root.sidebar)
            label.pack(anchor='w')
            inactive=CTkButton(root.sidebar)
            inactive.pack(anchor='w')
            active=CTkButton(root.sidebar,fg='#123f64')
            active.pack(anchor='w')
            root.update()
            ctrl=workspace.WorkspaceBackground.__new__(workspace.WorkspaceBackground)
            ctrl.parent=root
            ctrl._last_size=(1024,720)
            ctrl._palette_last=('#06111f','#0d1828','#1b3048','#14b8ff')
            ctrl._workspace_left=310
            ctrl._paint_sidebar_controls()
            self.assertRegex(inactive.cget('fg_color'),r'^#[0-9a-f]{6}$')
            self.assertNotEqual(inactive.cget('fg_color'),'#000000')
            self.assertEqual(inactive.cget('fg_color'),inactive.cget('bg_color'))
            self.assertEqual(inactive._text_label.cget('bg'),inactive.cget('fg_color'))
            self.assertEqual(active.cget('fg_color'),'#123f64')
            self.assertEqual(label.cget('fg_color'),label._text_label.cget('bg'))
            self.assertGreater(len(inactive._canvas.find_withtag(workspace._SIDEBAR_CONTROL_TAG)),0)
            self.assertEqual(len(active._canvas.find_withtag(workspace._SIDEBAR_CONTROL_TAG)),0)
            root.update()
            ctrl._paint_sidebar_controls()  # idempotencia, no confundir inactivo con seleccionado
            self.assertEqual(active.cget('fg_color'),'#123f64')
        finally:
            root.destroy()



# ===== Regresión test_v427_status_card_border_contract (original conservado íntegramente) =====
import ast
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def module_tree(relative_path):
    return ast.parse((ROOT / relative_path).read_text(encoding='utf-8'))


def named_function(tree, name):
    return next(item for item in tree.body if isinstance(item, ast.FunctionDef) and item.name == name)


def calls_cfg_border(node):
    pairs = []
    for call in ast.walk(node):
        if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name) or call.func.id != '_cfg':
            continue
        for kw in call.keywords:
            if kw.arg == 'border_width':
                pairs.append((call, kw.value))
    return pairs


class BorderSingleAuthorityTests(unittest.TestCase):
    def test_status_band_style_never_restores_border(self):
        tree = module_tree('gui/dashboard_layout.py')
        fn = named_function(tree, '_style_status_band')
        zero_borders = [value for _, value in calls_cfg_border(fn)
                        if isinstance(value, ast.Constant) and value.value == 0]
        self.assertGreaterEqual(len(zero_borders), 2)
        self.assertFalse(any(isinstance(value, ast.Constant) and value.value != 0
                             for _, value in calls_cfg_border(fn)))
        # Ejecutamos la FUNCIÓN DE PRODUCCIÓN, no una réplica de su lógica.
        namespace = {'SURFACE':'#102a3f', 'BORDER':'#345678'}
        changes = []
        namespace['_cfg'] = lambda widget, **kwargs: changes.append((widget, kwargs))
        exec(compile(ast.Module(body=[fn], type_ignores=[]), 'dashboard_layout.py', 'exec'), namespace)
        status_cards = [object() for _ in range(4)]
        app = types.SimpleNamespace(_status_band=object(), _status_cards=status_cards)
        namespace['_style_status_band'](app)
        self.assertGreaterEqual(len(changes), 5)  # V434 sincroniza también fondos internos.
        for card in status_cards:
            values = next(kw for widget, kw in changes if widget is card)
            self.assertEqual(values['border_width'], 0)
            self.assertEqual(values['border_color'], '#102a3f')
            self.assertNotIn('fg_color', values)  # V436: native paint owns the fill
        # Ningún control secundario debe recuperar un borde.
        self.assertFalse(any(kwargs.get('border_width', 0) != 0 for _, kwargs in changes))

    def test_responsive_style_preserves_borderless_cards(self):
        tree = module_tree('gui/dashboard_layout.py')
        fn = named_function(tree, '_style_status_mode')
        found = [value.value for _, value in calls_cfg_border(fn)
                 if isinstance(value, ast.Constant)]
        self.assertIn(0, found)
        self.assertNotIn(1, found)

    def test_constructed_status_cards_are_borderless(self):
        tree = module_tree('gui/dashboard.py')
        for name in ('_health_status_card', '_status_card', '_build_header'):
            fn = named_function(tree, name)
            values = [kw.value.value for node in ast.walk(fn)
                      if isinstance(node, ast.Call)
                      for kw in node.keywords
                      if kw.arg == 'border_width' and isinstance(kw.value, ast.Constant)]
            self.assertIn(0, values, name)
            self.assertNotIn(1, values, name)

    def test_resource_cards_do_not_restore_frame_border(self):
        layout = module_tree('gui/dashboard_layout.py')
        for name in ('_style_hardware', '_style_storage_widgets'):
            fn = named_function(layout, name)
            self.assertIn(0, [value.value for _, value in calls_cfg_border(fn)
                              if isinstance(value, ast.Constant)], name)


if __name__ == '__main__':
    unittest.main()



# ===== Regresión test_v428_status_band_surface_contract (original conservado íntegramente) =====
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]

def source(name):
    return (ROOT / name).read_text(encoding='utf-8')

def function(name, path):
    tree = ast.parse(source(path))
    return next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)

class SummarySurfaceTests(unittest.TestCase):
    def test_header_layout_does_not_restore_large_gap(self):
        func = function('_style_header_mode', 'gui/dashboard_layout.py')
        # Run the real style routine with a small fake widget and no Tk display.
        class Fake:
            def __init__(self):
                self.options = {}
            def pack_configure(self, **kwargs):
                self.options.update(kwargs)
        header = Fake()
        applied = []
        namespace = dict(_cfg=lambda widget, **kw: applied.append((widget, kw)),
                         FONT='Segoe UI', TEXT='white', CYAN='cyan')
        exec(compile(ast.Module(body=[func], type_ignores=[]), '<dashboard_layout>', 'exec'), namespace)
        app = SimpleNamespace(_header=header, _header_identity=None)
        for mode in ('compact', 'standard', 'wide'):
            header.options.clear()
            applied.clear()
            namespace['_style_header_mode'](app, mode)
            self.assertEqual(header.options.get('pady'), (0, 2))
            self.assertTrue(any(w is header and kw.get('height') == 96 for w, kw in applied))

    def test_health_card_uses_matching_material_for_nested_grid_widgets(self):
        card = function('_health_status_card', 'gui/dashboard.py')
        src = ast.get_source_segment(source('gui/dashboard.py'), card)
        for required in (
            "body = ctk.CTkFrame(shell, fg_color=COLORS['surface']",
            "metrics_row = ctk.CTkFrame(body, fg_color=COLORS['surface']",
            "status_strip = ctk.CTkFrame(body, fg_color=COLORS['surface']",
            "health_label.configure(bg_color=COLORS['surface'])",
        ):
            self.assertIn(required, src)

    def test_status_cards_not_optically_overpainted(self):
        # Execute production installer with stubs to verify actual registration.
        install = function('install_glass_cards', 'gui/glass_cards.py')
        registered=[]
        class FakeController:
            def __init__(self, root):
                self.root = root
            def register(self, card):
                registered.append(card)
            def schedule(self):
                pass
        namespace = {'GlassCardVisuals':FakeController}
        exec(compile(ast.Module(body=[install], type_ignores=[]), '<glass_cards>', 'exec'), namespace)
        ai, cpu, ram, gpu = [object() for _ in range(4)]
        upper = [object() for _ in range(4)]
        disk = object()
        app=SimpleNamespace(_corepulse_glass_cards=None, _ai_card=ai,
                            card_cpu=cpu, card_ram=ram, card_gpu=gpu,
                            _status_cards=upper, disk_widgets={0:{'card':disk}})
        namespace['install_glass_cards'](app)
        self.assertEqual(registered, [ai, cpu, ram, gpu, disk])
        for item in upper:
            self.assertNotIn(item, registered)

    def test_other_card_material_and_sidebar_unchanged(self):
        text=source('gui/dashboard.py')
        # The outer status card remains glass and borderless.
        for name in ('_health_status_card', '_status_card'):
            func=function(name, 'gui/dashboard.py')
            src=ast.get_source_segment(text, func)
            self.assertIn("fg_color=COLORS['surface']", src)
            self.assertIn('border_width=0', src)
        # The sidebar style remains linked to the native base; no return of its frame.
        layout=source('gui/dashboard_layout.py')
        self.assertIn("fg_color='transparent'", ast.get_source_segment(layout, function('_style_sidebar', 'gui/dashboard_layout.py')))

if __name__ == '__main__':
    unittest.main()



# ===== Regresión test_v432_chart_frame_contract (original conservado íntegramente) =====
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]


def function_from_source(relpath, name, namespace):
    module = ast.parse((ROOT / relpath).read_text(encoding='utf-8'))
    node = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == name)
    code = compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(ROOT / relpath), 'exec')
    exec(code, namespace)
    return namespace[name]


class FakeAxis:
    def __init__(self):
        self.title = SimpleNamespace(set_color=lambda *_: None, set_fontsize=lambda *_: None, set_fontweight=lambda *_: None)
        self.yaxis = SimpleNamespace(grid=lambda *a, **kw: None)
        self.spines = {name: SimpleNamespace(set_visible=lambda *a: None, set_linewidth=lambda *a: None,
                                               set_color=lambda *a: None) for name in ('top','right','bottom','left')}
        self.facecolor = None
    def set_facecolor(self, color): self.facecolor = color
    def tick_params(self, **kw): pass
    def grid(self, *a, **kw): pass
    def set_axisbelow(self, *a): pass
    def set_yticks(self, *a): pass
    def set_xticks(self, *a): pass
    def set_xticklabels(self, *a): pass
    def set_ylim(self, *a): pass
    def set_xlim(self, *a): pass
    def margins(self, **kw): pass


class FakeFigure:
    def __init__(self):
        self.patch = SimpleNamespace(
            set_facecolor=lambda v: setattr(self, 'patch_color', v),
            set_edgecolor=lambda v: setattr(self, 'patch_edge', v),
            set_linewidth=lambda v: setattr(self, 'patch_linewidth', v),
        )
        self._axes = [FakeAxis() for _ in range(3)]
        self.facecolor = None
        self.frame_on = None
    def set_facecolor(self, value): self.facecolor = value
    def set_frameon(self, flag): self.frame_on = flag
    def subplots_adjust(self, **kwargs): pass


class FakeCanvas:
    def __init__(self):
        self.config = {}
        self.tk_widget = SimpleNamespace(configure=lambda **kw: self.config.update(kw))
    def get_tk_widget(self): return self.tk_widget
    def draw_idle(self): pass


class TestV432(unittest.TestCase):
    def test_main_chart_root_no_border(self):
        src = (ROOT/'main.py').read_text(encoding='utf-8')
        node = next(n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Attribute) and t.attr == 'frame_charts' for t in n.targets))
        args = {kw.arg: kw.value for kw in node.value.keywords}
        self.assertEqual(args['border_width'].value, 0)
        self.assertEqual(args['fg_color'].value, 'transparent')
        self.assertNotIn('border_color', args)

    def test_mpl_initial_figure_has_real_background(self):
        src = (ROOT/'main.py').read_text(encoding='utf-8')
        node = next(n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Attribute) and t.attr == 'fig' for t in n.targets)
                    and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name)
                    and n.value.func.id == 'Figure')
        args = {kw.arg: kw.value for kw in node.value.keywords}
        self.assertTrue(args['frameon'].value)
        self.assertEqual(args['facecolor'].args[0].value, 'glass_surface')

    def test_dashboard_style_runtime_preserves_borderless_frame(self):
        configured = {}
        destroyed = []
        class Bar:
            def destroy(self): destroyed.append(True)
        fig = FakeFigure()
        cv = FakeCanvas()
        app = SimpleNamespace(frame_charts=object(), fig=fig, canvas=cv,
                              ax_cpu=fig._axes[0], ax_ram=fig._axes[1], ax_gpu=fig._axes[2],
                              _chart_top_accents=[Bar(), Bar()], background='old')
        color='#0e263a'
        namespace = {
            '_safe_config': lambda w, **kw: configured.update(kw),
            'COLORS': {'surface': color, 'muted':'#999', 'border_soft':'#333', 'border':'#444'},
            '_update_trend_titles':lambda a: None,
            '_apply_chart_geometry_alignment':lambda a: None,
        }
        fn=function_from_source('gui/dashboard.py', '_style_charts', namespace)
        fn(app)
        self.assertEqual(configured['border_width'], 0)
        self.assertEqual(configured['fg_color'], 'transparent')
        self.assertNotIn('border_color', configured)
        self.assertTrue(fig.frame_on)
        self.assertEqual(fig.patch_color, color)
        self.assertEqual(fig.patch_linewidth, 0.0)
        self.assertEqual(cv.config['bg'], color)
        self.assertEqual(len(destroyed), 2)
        self.assertEqual(app._chart_top_accents, [])

    def test_responsive_style_runtime_preserves_borderless_frame(self):
        configured = {}
        fig = FakeFigure(); cv = FakeCanvas()
        app = SimpleNamespace(frame_charts=object(), fig=fig, canvas=cv,
                              ax_cpu=fig._axes[0], ax_ram=fig._axes[1], ax_gpu=fig._axes[2],
                              max_points=25, background='old')
        color='#0e263a'
        namespace = {
            '_cfg':lambda w, **kw: configured.update(kw),
            '_chart_tick_positions':lambda n:[0,6,12,18,24],
            'SURFACE':color, 'BORDER_SOFT':'#333', 'BORDER':'#444',
            'MUTED':'#999','TEXT_2':'#eee',
        }
        fn=function_from_source('gui/dashboard_layout.py','_style_charts',namespace)
        fn(app)
        self.assertEqual(configured['border_width'],0)
        self.assertEqual(configured['fg_color'],'transparent')
        self.assertNotIn('border_color',configured)
        self.assertTrue(fig.frame_on)
        self.assertEqual(fig.patch_color,color)
        self.assertEqual(fig.patch_linewidth,0.0)
        self.assertEqual(cv.config['bg'],color)

    def test_real_matplotlib_figure_paints_matte_background(self):
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        fig=Figure(figsize=(3,1.6),dpi=72,facecolor='#0e263a',frameon=True)
        fig.patch.set_linewidth(0)
        ax=fig.add_subplot(111)
        ax.plot([0,1],[0,1])
        canvas=FigureCanvasAgg(fig)
        canvas.draw()
        pixel=bytes(canvas.buffer_rgba())[:4]
        self.assertEqual(tuple(int(x) for x in pixel[:3]),(14,38,58))


if __name__ == '__main__':
    unittest.main()



# ===== Regresión test_v434_chart_workspace_surface (original conservado íntegramente) =====
import ast
from pathlib import Path
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


class TestV434(unittest.TestCase):
    def test_sampled_gradient_matches_native_workspace_at_every_row(self):
        from gui.chart_workspace_surface import sampled_workspace_background
        from gui.workspace_background import native_surface_color_at, _palette
        p = _palette()
        width, height = 240, 260
        params = dict(x=325, y=570, root_width=1530, root_height=916,
                      palette=p, workspace_left=305)
        grad = sampled_workspace_background(width, height, **params)
        self.assertEqual(grad.shape, (height,width,3))
        for row in range(height):
            expected=native_surface_color_at(520, params['y']+row, 1530, 916,
                                             palette=p, workspace_left=305)
            color=tuple(int(expected[i:i+2],16) for i in (1,3,5))
            self.assertEqual(tuple(int(v) for v in grad[row,120]), color)
            self.assertEqual(tuple(int(v) for v in grad[row,1]), color)

    def test_matplotlib_image_draws_background_without_covering_axes(self):
        from gui.chart_workspace_surface import sampled_workspace_background
        from gui.workspace_background import _palette
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        p=_palette()
        arr=sampled_workspace_background(300,180,x=350,y=550,root_width=1530,
              root_height=920,palette=p,workspace_left=330)
        fig=Figure(figsize=(3,1.8),dpi=100,facecolor='#06111f')
        fig.figimage(arr,xo=0,yo=0,origin='upper',zorder=-100)
        ax=fig.add_axes([.2,.3,.6,.55], facecolor='#12283c')
        ax.plot([0,1],[0,1],color='#ffffff',linewidth=2)
        cv=FigureCanvasAgg(fig)
        cv.draw()
        pixels=np.asarray(cv.buffer_rgba())
        self.assertEqual(tuple(pixels[2,2,:3]),tuple(arr[2,2,:3]))
        self.assertEqual(tuple(pixels[176,2,:3]),tuple(arr[176,2,:3]))
        self.assertNotEqual(tuple(pixels[70,100,:3]),tuple(arr[70,100,:3]))

    def test_only_one_figure_background_writer_and_preserve_no_border(self):
        src=(ROOT/'gui/chart_workspace_surface.py').read_text(encoding='utf-8')
        self.assertIn('background.set_data(arr)',src)
        self.assertIn('fig.figimage(arr',src)
        src_main=(ROOT/'main.py').read_text(encoding='utf-8')
        self.assertIn("fg_color='transparent', border_width=0",src_main)
        for src_path in ('gui/dashboard_layout.py','gui/dashboard.py'):
            src_style=(ROOT/src_path).read_text(encoding='utf-8')
            self.assertIn('sync_chart_workspace_surface(app)',src_style)
            self.assertIn('border_width=0',src_style)
        self.assertIn('register_surface(app.frame_charts)',
                      (ROOT/'gui/dashboard.py').read_text(encoding='utf-8'))

if __name__ == '__main__':
    unittest.main()



# ===== Regresión test_v436_native_card_surface (original conservado íntegramente) =====
import unittest
import tkinter as tk
from pathlib import Path

from gui.workspace_background import _palette, native_surface_color_at
from gui.card_workspace_surface import CARD_TAG, paint_native_card_surface


class CTkFrame(tk.Frame):
    def __init__(self, parent, fg='#132337', **kwargs):
        super().__init__(parent, **kwargs)
        self.props = {'fg_color': fg, 'bg_color': fg, 'border_width': 0, 'border_color': fg}
        self._canvas = tk.Canvas(self, highlightthickness=0, bd=0, height=165, width=400)
        self._canvas.pack(fill='both', expand=True)

    def cget(self, key):
        return self.props[key] if key in self.props else super().cget(key)

    def configure(self, **kwargs):
        for k in list(kwargs):
            if k in self.props:
                self.props[k] = kwargs.pop(k)
        if kwargs:
            super().configure(**kwargs)


class CardSurfaceContract(unittest.TestCase):
    def test_workspace_pixels_are_exact_not_glass_mix(self):
        root = tk.Tk()
        root.geometry('1100x780+0+0')
        frame = CTkFrame(root)
        frame.place(x=290, y=320, width=400, height=165)
        root.update()
        try:
            self.assertTrue(paint_native_card_surface(
                frame, parent=root, palette=_palette(), width=1100,
                height=780, workspace_left=260))
            canvas = frame._canvas
            rects = [i for i in canvas.find_withtag(CARD_TAG)
                     if canvas.type(i) == 'rectangle']
            self.assertGreater(len(rects), 5)
            for xx, yy in ((25, 8), (25, 78), (25, 150)):
                ids = [i for i in canvas.find_overlapping(xx-1, yy-1, xx+1, yy+1)
                       if CARD_TAG in canvas.gettags(i)]
                self.assertTrue(ids)
                actual = canvas.itemcget(ids[-1], 'fill')
                expected = native_surface_color_at(290+xx, 320+yy, 1100, 780,
                            palette=_palette(), workspace_left=260)
                self.assertEqual(actual, expected)
        finally:
            root.destroy()

    def test_v435_tint_and_hover_are_bypassed(self):
        source = (Path(__file__).resolve().parents[1] / 'gui' / 'dashboard.py')
        data = source.read_text(encoding='utf-8')
        self.assertIn('return base  # V436:', data)
        self.assertIn('return fill  # V436:', data)
        self.assertIn('_cp_seamless_surface', data)


if __name__ == '__main__':
    unittest.main()



# ===== Regresión test_v437_chart_columns_and_card_glow (original conservado íntegramente) =====
import unittest
import tkinter as tk
import ast
from pathlib import Path
from types import SimpleNamespace

# Load the production helper without importing the complete CTk dashboard.
layout_src = (Path(__file__).resolve().parents[1] / 'gui' / 'dashboard_layout.py').read_text(encoding='utf-8')
layout_tree = ast.parse(layout_src)
functions = [n for n in layout_tree.body if isinstance(n, ast.FunctionDef)
             and n.name in ('_aligned_plot_rectangles', '_align_charts_to_metric_cards')]
module = ast.fix_missing_locations(ast.Module(body=functions, type_ignores=[]))
namespace = {}
exec(compile(module, 'gui/dashboard_layout.py', 'exec'), namespace)
_aligned_plot_rectangles = namespace['_aligned_plot_rectangles']
_align_charts_to_metric_cards = namespace['_align_charts_to_metric_cards']
from gui.card_workspace_surface import (
    CARD_TAG, card_hover_tone, paint_native_card_surface, apply_card_hover_accent, _accent_hover_color,
)
from gui.workspace_background import _palette, native_surface_color_at
# V481: CTkFrame declarado arriba en esta misma suite


class V437ChartColumnsTest(unittest.TestCase):
    def test_each_plot_tracks_its_hardware_column(self):
        cards = [(335, 382), (731, 390), (1135, 383)]
        canvas_left = 348
        canvas_width = 1176
        positions = _aligned_plot_rectangles(cards, canvas_left, canvas_width)
        self.assertEqual(len(positions), 3)
        for (left, width), (card_left, card_width) in zip(positions, cards):
            self.assertAlmostEqual(
                canvas_left + left * canvas_width, card_left + 38, places=5
            )
            self.assertAlmostEqual(
                canvas_left + (left + width) * canvas_width,
                card_left + card_width - 29, places=5,
            )
        self.assertLess(positions[0][0] + positions[0][1], positions[1][0])
        self.assertLess(positions[1][0] + positions[1][1], positions[2][0])

    def test_real_alignment_helper_repositions_all_three_axes(self):
        class Widget:
            def __init__(self, x, width):
                self.x, self.width = x, width
            def winfo_rootx(self): return self.x
            def winfo_width(self): return self.width
            def winfo_ismapped(self): return True
        class Axis:
            position = None
            def set_position(self, position): self.position = position
        cards = [Widget(330, 390), Widget(734, 384), Widget(1130, 391)]
        axes = [Axis(), Axis(), Axis()]
        canvas = Widget(344, 1187)
        app = SimpleNamespace(canvas=SimpleNamespace(get_tk_widget=lambda: canvas),
            fig=SimpleNamespace(bbox=SimpleNamespace(width=1187)),
            card_cpu=cards[0], card_ram=cards[1], card_gpu=cards[2],
            ax_cpu=axes[0], ax_ram=axes[1], ax_gpu=axes[2])
        self.assertTrue(_align_charts_to_metric_cards(app))
        for ax, card in zip(axes, cards):
            self.assertAlmostEqual(344 + ax.position[0] * 1187,
                                   card.x + 38)
            self.assertEqual(ax.position[1], 0.20)
            self.assertEqual(ax.position[3], 0.64)

    def test_rejects_unusable_or_unmapped_geometry(self):
        self.assertFalse(_aligned_plot_rectangles([], 0, 1200))
        self.assertFalse(_aligned_plot_rectangles([(10, 100)] * 3, 0, 1200))
        self.assertFalse(_aligned_plot_rectangles([(20, 400)] * 3, 0, 1200))


class V437NativeGlowTest(unittest.TestCase):
    def test_hover_never_creates_a_second_canvas_layer(self):
        root = tk.Tk()
        root.geometry('1020x740+0+0')
        card = CTkFrame(root)
        card.place(x=285, y=300, width=400, height=165)
        root.update()
        card._cp_hover_accent = '#16d98b'
        try:
            palette = _palette()
            args = dict(parent=root, palette=palette, width=1020, height=740,
                        workspace_left=260)
            for active in (False, True, False, True, True, False):
                card._cp_hover_active = active
                self.assertTrue(paint_native_card_surface(card, **args))
                self.assertFalse(card._canvas.find_withtag(CARD_TAG + '_hover'))
            surface_ids = [i for i in card._canvas.find_overlapping(24, 78, 26, 80)
                           if CARD_TAG in card._canvas.gettags(i)]
            baseline = native_surface_color_at(285 + 25, 300 + 79, 1020, 740,
                                               palette=palette, workspace_left=260)
            self.assertEqual(card._canvas.itemcget(surface_ids[-1], 'fill'), baseline)
        finally:
            root.destroy()


    def test_per_accent_colors_are_distinct(self):
        base = '#0b1a2a'
        green = card_hover_tone(base, '#16d98b', 0.1)
        purple = card_hover_tone(base, '#a064ff', 0.1)
        cyan = card_hover_tone(base, '#14b8ff', 0.1)
        self.assertEqual(len({green, purple, cyan}), 3)
        self.assertNotEqual(card_hover_tone(base, '#16d98b', 0.1),
                            card_hover_tone(base, '#16d98b', 0.95))


if __name__ == '__main__':
    unittest.main()



# ===== Regresión test_v438_soft_hover_feather_contract (original conservado íntegramente) =====
import unittest
import tkinter as tk
from gui.workspace_background import _palette, native_surface_color_at
from gui.card_workspace_surface import CARD_TAG, card_hover_tone, paint_native_card_surface
# V481: CTkFrame declarado arriba en esta misma suite


class SoftHoverFeatherContract(unittest.TestCase):
    def test_hover_tone_fades_at_horizontal_and_vertical_boundaries(self):
        base = '#0a1b2e'
        for color in ('#14b8ff', '#16d98b', '#a064ff', '#f3b54a'):
            self.assertEqual(card_hover_tone(base, color, 0.95), base)
            self.assertEqual(card_hover_tone(base, color, .10, 0), base)
            self.assertEqual(card_hover_tone(base, color, .10, 1), base)
            self.assertEqual(card_hover_tone(base, color, .62, .5), base)
            self.assertNotEqual(card_hover_tone(base, color, .03, .5), base)
            self.assertNotEqual(card_hover_tone(base, color, .10, .5), base)
            self.assertNotEqual(card_hover_tone(base, color, .10, .3), base)
            self.assertNotEqual(card_hover_tone(base, color, .10, .1),
                                card_hover_tone(base, color, .10, .5))

    def test_no_new_hover_rectangles_or_control_tiles(self):
        root = tk.Tk()
        root.geometry('1100x780+0+0')
        card = CTkFrame(root)
        card.place(x=290, y=320, width=400, height=165)
        root.update()
        card._cp_hover_accent = '#a064ff'
        card._cp_hover_active = True
        palette = _palette()
        args = dict(parent=root, palette=palette, width=1100, height=780,
                    workspace_left=260)
        try:
            self.assertTrue(paint_native_card_surface(card, **args))
            self.assertFalse(card._canvas.find_withtag(CARD_TAG + '_hover'))
            for _ in range(8):
                card._cp_hover_active = not card._cp_hover_active
                self.assertTrue(paint_native_card_surface(card, **args))
                self.assertFalse(card._canvas.find_withtag(CARD_TAG + '_hover'))
            self.assertEqual(set(card._canvas.gettags(card._canvas.find_withtag(CARD_TAG)[0])), {CARD_TAG})
            # Native substrate stays identical after interaction.
            surface_ids = [i for i in card._canvas.find_overlapping(24, 78, 26, 80)
                           if CARD_TAG in card._canvas.gettags(i)]
            self.assertTrue(surface_ids)
            self.assertEqual(card._canvas.itemcget(surface_ids[-1], 'fill'),
                             native_surface_color_at(290 + 25, 320 + 79, 1100, 780,
                                                     palette=palette, workspace_left=260))
        finally:
            root.destroy()


if __name__ == '__main__':
    unittest.main()



# ===== Regresión test_v439_hover_without_squares (original conservado íntegramente) =====
import tkinter as tk
import unittest
try:
    import customtkinter as ctk
except ImportError:
    ctk = None
from gui.card_workspace_surface import (
    CARD_TAG, apply_card_hover_accent, _accent_hover_color, paint_native_card_surface,
)
from gui.workspace_background import _palette


class NativeHoverWithoutSquares(unittest.TestCase):
    @unittest.skipIf(ctk is None, "CustomTkinter no está instalado en el entorno de pruebas")
    def test_real_ctk_label_and_icon_are_not_repainted_on_hover(self):
        root = ctk.CTk()
        root.geometry('1020x680+0+0')
        card = ctk.CTkFrame(root, fg_color='#0b2035', border_width=0)
        card.place(x=280, y=230, width=420, height=160)
        shell = ctk.CTkFrame(card, fg_color='#0b2035')
        shell.pack(fill='both', expand=True)
        accent = ctk.CTkFrame(shell, fg_color='#16d98b', width=4)
        accent.pack(side='left', fill='y')
        accent._cp_native_accent_strip = True
        label = ctk.CTkLabel(shell, text='VALOR REAL', fg_color='transparent')
        label.pack(side='left', padx=24)
        icon = ctk.CTkLabel(shell, text='✓', width=44, height=44,
                            fg_color='#103c33', corner_radius=14)
        icon.pack(side='left', padx=10)
        card._cp_native_hover_strip = accent
        card._cp_hover_accent = '#16d98b'
        root.update()
        try:
            kwargs = dict(parent=root, palette=_palette(), width=root.winfo_width(),
                          height=root.winfo_height(), workspace_left=240)
            self.assertTrue(paint_native_card_surface(card, **kwargs))
            original_label = label.cget('text')
            original_icon_color = icon.cget('fg_color')
            self.assertEqual(str(accent.cget('fg_color')).lower(), '#16d98b')
            for _ in range(12):
                card._cp_hover_active = True
                self.assertTrue(apply_card_hover_accent(card, True))
                self.assertTrue(paint_native_card_surface(card, **kwargs))
                self.assertFalse(card._canvas.find_withtag(CARD_TAG + '_hover'))
                self.assertEqual(str(accent.cget('fg_color')).lower(), _accent_hover_color('#16d98b'))
                card._cp_hover_active = False
                self.assertTrue(apply_card_hover_accent(card, False))
                self.assertTrue(paint_native_card_surface(card, **kwargs))
                self.assertFalse(card._canvas.find_withtag(CARD_TAG + '_hover'))
                self.assertEqual(str(accent.cget('fg_color')).lower(), '#16d98b')
            self.assertEqual(label.cget('text'), original_label)
            self.assertEqual(icon.cget('fg_color'), original_icon_color)
            self.assertFalse(getattr(accent, '_cp_native_accent_strip', False) is False)
        finally:
            root.destroy()

    def test_strip_is_idempotent_and_keeps_original_color(self):
        class Strip:
            def __init__(self):
                self.color = '#16d98b'
                self._cp_native_accent_strip = True
                self.updates = 0
            def winfo_exists(self): return True
            def cget(self, key): return self.color
            def configure(self, **kwargs):
                self.color = kwargs.get('fg_color', self.color)
                self.updates += 1
        from types import SimpleNamespace
        strip = Strip()
        card = SimpleNamespace(_cp_native_hover_strip=strip, _cp_hover_accent='#16d98b')
        for i in range(20):
            self.assertTrue(apply_card_hover_accent(card, True))
            self.assertEqual(strip.color, _accent_hover_color('#16d98b'))
            self.assertTrue(apply_card_hover_accent(card, True))
            self.assertEqual(strip.color, _accent_hover_color('#16d98b'))
            self.assertTrue(apply_card_hover_accent(card, False))
            self.assertEqual(strip.color, '#16d98b')
        self.assertEqual(strip.updates, 40)
        self.assertTrue(strip._cp_native_accent_strip)

    def test_illumination_uses_only_accent_colors(self):
        self.assertNotEqual(_accent_hover_color('#14b8ff'), _accent_hover_color('#a064ff'))
        self.assertNotEqual(_accent_hover_color('#16d98b'), _accent_hover_color('#f3b54a'))


if __name__ == '__main__':
    unittest.main()



# ===== Regresión test_v442_native_hover_visible (original conservado íntegramente) =====
import tkinter as tk
import unittest

from gui.card_workspace_surface import (
    CARD_TAG, CARD_GLOW_TAG, paint_native_card_surface, repaint_card_hover,
)
from gui.workspace_background import _palette
# V481: CTkFrame declarado arriba en esta misma suite


class FakeController:
    def __init__(self, root):
        self.parent = root
        self._last_size = (1050, 750)
        self._palette_last = _palette()
        self._workspace_left = 250


class NativePerimeterGlowTest(unittest.TestCase):
    def test_glow_visible_on_hover_and_fully_removed_on_leave(self):
        root = tk.Tk()
        root.geometry('1050x750+0+0')
        card = CTkFrame(root)
        card.place(x=300, y=250, width=420, height=160)
        card._cp_hover_accent = '#16d98b'
        root.update()
        ctrl = FakeController(root)
        try:
            kwargs = dict(parent=root, width=1050, height=750,
                          palette=ctrl._palette_last, workspace_left=250)
            self.assertTrue(paint_native_card_surface(card, **kwargs))
            self.assertFalse(card._canvas.find_withtag(CARD_GLOW_TAG))
            card._cp_hover_active = True
            self.assertTrue(repaint_card_hover(card, ctrl))
            glow = card._canvas.find_withtag(CARD_GLOW_TAG)
            self.assertGreaterEqual(len(glow), 1)
            self.assertLessEqual(len(glow), 3)
            self.assertTrue(all(card._canvas.type(i) == 'line' for i in glow))
            self.assertFalse(card._canvas.find_withtag(CARD_TAG + '_hover'))
            # El color de los trazos depende del acento propio.
            green = card._canvas.itemcget(glow[0], 'fill')
            card._cp_hover_accent = '#a064ff'
            self.assertTrue(repaint_card_hover(card, ctrl))
            purple = card._canvas.itemcget(card._canvas.find_withtag(CARD_GLOW_TAG)[0], 'fill')
            self.assertNotEqual(green, purple)
            card._cp_hover_active = False
            self.assertTrue(repaint_card_hover(card, ctrl))
            self.assertFalse(card._canvas.find_withtag(CARD_GLOW_TAG))
            self.assertTrue(card._canvas.find_withtag(CARD_TAG))
        finally:
            root.destroy()

    def test_repeat_hover_does_not_accumulate_paint_objects(self):
        root = tk.Tk()
        root.geometry('1050x750+0+0')
        card = CTkFrame(root)
        card.place(x=300, y=250, width=420, height=160)
        card._cp_hover_accent = '#14b8ff'
        root.update()
        ctrl = FakeController(root)
        try:
            lengths = []
            for _ in range(6):
                card._cp_hover_active = True
                self.assertTrue(repaint_card_hover(card, ctrl))
                lengths.append(len(card._canvas.find_withtag(CARD_GLOW_TAG)))
                card._cp_hover_active = False
                self.assertTrue(repaint_card_hover(card, ctrl))
                self.assertFalse(card._canvas.find_withtag(CARD_GLOW_TAG))
            self.assertEqual(len(set(lengths)), 1)
        finally:
            root.destroy()


if __name__ == '__main__':
    unittest.main()



# ===== Regresión test_v443_rounded_fast_glow (original conservado íntegramente) =====

import tkinter as tk
import unittest
from unittest.mock import patch

from gui.card_workspace_surface import (
    CARD_GLOW_TAG, CARD_TAG, _rounded_perimeter_points,
    paint_native_card_surface, repaint_card_hover,
)
from gui.workspace_background import _palette
# V481: CTkFrame declarado arriba en esta misma suite


class Controller:
    def __init__(self, root):
        self.parent = root
        self._last_size = (1000, 760)
        self._palette_last = _palette()
        self._workspace_left = 235


class V443RoundedFastGlow(unittest.TestCase):
    def test_path_leaves_both_top_corners_empty_and_stays_inside_bounds(self):
        points = _rounded_perimeter_points(2, 2, 402, 162, 14, subdivisions=8)
        vertices = list(zip(points[0::2], points[1::2]))
        self.assertEqual(vertices[0], vertices[-1])
        self.assertGreaterEqual(len(vertices), 30)
        for x, y in vertices:
            self.assertGreaterEqual(x, 2)
            self.assertLessEqual(x, 402)
            self.assertGreaterEqual(y, 2)
            self.assertLessEqual(y, 162)
            self.assertFalse(x < 4 and y < 4, 'no sharp stroke at top-left')
            self.assertFalse(x > 400 and y < 4, 'no sharp stroke at top-right')
            self.assertFalse(x < 4 and y > 160, 'no sharp stroke at bottom-left')
            self.assertFalse(x > 400 and y > 160, 'no sharp stroke at bottom-right')

    def test_hover_is_three_or_fewer_strokes_without_repainting_native_background(self):
        root = tk.Tk()
        root.geometry('1000x760+0+0')
        card = CTkFrame(root)
        card.place(x=280, y=270, width=400, height=165)
        root.update()
        ctrl = Controller(root)
        kwargs = dict(parent=root, palette=ctrl._palette_last,
                      width=1000, height=760, workspace_left=235)
        card._cp_hover_accent = '#14b8ff'
        try:
            self.assertTrue(paint_native_card_surface(card, **kwargs))
            backgrounds = set(card._canvas.find_withtag(CARD_TAG))
            self.assertGreater(len(backgrounds), 0)
            with patch('gui.card_workspace_surface.paint_native_card_surface',
                       side_effect=AssertionError('no repintado durante hover')):
                for color in ('#14b8ff', '#16d98b', '#a064ff', '#14b8ff'):
                    card._cp_hover_accent = color
                    card._cp_hover_active = True
                    self.assertTrue(repaint_card_hover(card, ctrl))
                    glow = card._canvas.find_withtag(CARD_GLOW_TAG)
                    self.assertGreater(len(glow), 0)
                    self.assertLessEqual(len(glow), 3)
                    self.assertTrue(all(card._canvas.type(item) == 'line' for item in glow))
                    for item in glow:
                        self.assertGreaterEqual(len(card._canvas.coords(item)), 32)
                    card._cp_hover_active = False
                    self.assertTrue(repaint_card_hover(card, ctrl))
                    self.assertFalse(card._canvas.find_withtag(CARD_GLOW_TAG))
            self.assertEqual(set(card._canvas.find_withtag(CARD_TAG)), backgrounds)
        finally:
            root.destroy()

    def test_repeated_active_hover_uses_cached_items(self):
        root = tk.Tk()
        root.geometry('1000x760+0+0')
        card = CTkFrame(root)
        card.place(x=280, y=270, width=400, height=165)
        card._cp_hover_accent = '#a064ff'
        root.update()
        ctrl = Controller(root)
        try:
            paint_native_card_surface(card, parent=root, palette=ctrl._palette_last,
                                      width=1000, height=760, workspace_left=235)
            card._cp_hover_active = True
            self.assertTrue(repaint_card_hover(card, ctrl))
            original = card._canvas.find_withtag(CARD_GLOW_TAG)
            for _ in range(10):
                self.assertTrue(repaint_card_hover(card, ctrl))
                self.assertEqual(original, card._canvas.find_withtag(CARD_GLOW_TAG))
            card._cp_hover_active = False
            self.assertTrue(repaint_card_hover(card, ctrl))
            self.assertEqual(card._canvas.find_withtag(CARD_GLOW_TAG), ())
        finally:
            root.destroy()


if __name__ == '__main__':
    unittest.main()



# ===== Regresión test_v444_seamless_axes_workspace (original conservado íntegramente) =====
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


class ChartNativeLayerTests(unittest.TestCase):
    def test_actual_axes_transparent_over_matching_native_workspace(self):
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from gui.workspace_background import _palette
        from gui.chart_workspace_surface import (sampled_workspace_background,
                                                 ensure_seamless_chart_axes)
        gradient = sampled_workspace_background(
            720, 270, x=326, y=590,
            root_width=1530, root_height=930, palette=_palette(), workspace_left=306,
        )
        fig = Figure(figsize=(7.2, 2.7), dpi=100, facecolor='#ff2244', frameon=True)
        fig.figimage(gradient, xo=0, yo=0, origin='upper', zorder=-100)
        axes = [fig.add_axes([.09+i*.31, .24, .25, .60], facecolor='#0c192b')
                for i in range(3)]
        for ax in axes:
            ax.set_xlim(0, 100)
            ax.set_ylim(0, 100)
            ax.set_xticks([])
            ax.set_yticks([])
        app = SimpleNamespace(ax_cpu=axes[0], ax_ram=axes[1], ax_gpu=axes[2])
        self.assertTrue(ensure_seamless_chart_axes(app))
        for ax in axes:
            self.assertEqual(ax.patch.get_facecolor()[-1], 0.0)
            self.assertTrue(all(not spine.get_visible() for spine in ax.spines.values()))
        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        pixels = np.asarray(canvas.buffer_rgba())
        # Interiores and edges of each graph show precisely the same master layer.
        for x in (85, 162, 265, 315, 409, 477, 571, 624, 695):
            for y in (54, 113, 174, 231):
                self.assertEqual(tuple(pixels[y, x, :3]), tuple(gradient[y, x]),
                                 (x, y))

    def test_original_plot_styles_no_longer_restore_solid_panels(self):
        main = (ROOT / 'main.py').read_text(encoding='utf-8')
        dash = (ROOT / 'gui/dashboard.py').read_text(encoding='utf-8')
        layout = (ROOT / 'gui/dashboard_layout.py').read_text(encoding='utf-8')
        surf = (ROOT / 'gui/chart_workspace_surface.py').read_text(encoding='utf-8')
        for ax in ('cpu', 'ram', 'gpu'):
            self.assertIn(f'self.ax_{ax} = self.fig.add_subplot(', main)
            self.assertIn(f'ax_{ax} = self.fig.add_subplot(', main)
        self.assertIn("ax.set_facecolor('none')", main)
        self.assertIn("ax.set_facecolor('none')", dash)
        self.assertIn("ax.set_facecolor('none')", layout)
        self.assertIn('ensure_seamless_chart_axes(app)', surf)
        self.assertIn('gridline.set_visible', surf)
        for f in (main, dash, layout):
            self.assertIn('spine.set_visible(False)', f)
        self.assertIn('sync_chart_workspace_surface(app)', dash)
        self.assertIn('sync_chart_workspace_surface(app)', layout)


if __name__ == '__main__':
    unittest.main()



# ===== Regresión test_v445_chart_left_alignment (original conservado íntegramente) =====
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace

PATH = Path(__file__).resolve().parents[1] / 'gui' / 'dashboard_layout.py'
tree = ast.parse(PATH.read_text(encoding='utf-8'))
nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef)
         and n.name in ('_aligned_plot_rectangles', '_align_charts_to_metric_cards')]
ns = {}
exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), str(PATH), 'exec'), ns)


class TestChartLeftAlignment(unittest.TestCase):
    def test_same_pixel_shift_without_changing_plot_width(self):
        cards = [(340, 390), (747, 383), (1142, 384)]
        original = ns['_aligned_plot_rectangles'](cards, 350, 1180, shift_left_px=0)
        corrected = ns['_aligned_plot_rectangles'](cards, 350, 1180)
        self.assertEqual(len(corrected), 3)
        for (base_left, base_width), (left, width) in zip(original, corrected):
            self.assertAlmostEqual((base_left-left)*1180, 20)
            self.assertAlmostEqual(width, base_width)

    def test_remains_a_20px_shift_across_resizes(self):
        for scale in (1, 1.15, 1.4):
            width = int(1180*scale)
            cards = [(int((340+i*402)*scale), int(385*scale)) for i in range(3)]
            original = ns['_aligned_plot_rectangles'](cards, int(350*scale), width, shift_left_px=0)
            corrected = ns['_aligned_plot_rectangles'](cards, int(350*scale), width)
            self.assertEqual(len(corrected), 3)
            for previous, current in zip(original, corrected):
                self.assertAlmostEqual((previous[0]-current[0])*width, 20)
                self.assertAlmostEqual(previous[1], current[1])

    def test_live_alignment_applies_shift_to_all_axes(self):
        class Widget:
            def __init__(self, x, width):
                self.x, self.width = x, width
            def winfo_rootx(self): return self.x
            def winfo_width(self): return self.width
            def winfo_ismapped(self): return True
        class Axis:
            def set_position(self, pos): self.position = pos
        canvas = Widget(348, 1187)
        cards = [Widget(330, 390), Widget(734, 384), Widget(1130, 391)]
        axes = [Axis(), Axis(), Axis()]
        app = SimpleNamespace(canvas=SimpleNamespace(get_tk_widget=lambda: canvas),
                              card_cpu=cards[0], card_ram=cards[1], card_gpu=cards[2],
                              ax_cpu=axes[0], ax_ram=axes[1], ax_gpu=axes[2])
        self.assertTrue(ns['_align_charts_to_metric_cards'](app))
        for card, ax in zip(cards, axes):
            self.assertAlmostEqual(canvas.x + ax.position[0]*canvas.width, card.x+38)
            self.assertEqual(ax.position[1], .20)
            self.assertEqual(ax.position[3], .64)


if __name__ == '__main__':
    unittest.main()



# ===== Regresión test_v447_ai_native_integrated (original conservado íntegramente) =====
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestAIHeaderBalanceContract(unittest.TestCase):
    def test_only_one_canvas_and_no_inner_ctk_label_or_frame(self):
        source = (ROOT / 'gui' / 'dashboard.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        builder = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                       and node.name == '_build_header')
        self.assertEqual(sum(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                             and node.func.id == 'AIStatusCanvas' for node in ast.walk(builder)), 1)
        self.assertIn('register_canvas(getattr(app, \'_header_ai_native_canvas\', None))', source)
        self.assertNotIn("status = ctk.CTkLabel(\n        body", source)
        self.assertNotIn("shell = ctk.CTkFrame(ai_card", source)

    def test_v445_charts_not_modified(self):
        # El código de gráficos conserva su firma contractual de V445.
        source = (ROOT / 'gui' / 'dashboard_layout.py').read_text(encoding='utf-8')
        self.assertNotIn("_cfg(getattr(app, '_ai_status', None), font=", source)
        self.assertIn('shift_left_px=20', source)
        self.assertIn('def _aligned_plot_rectangles', source)

    def test_native_canvas_with_real_workspace_and_changes(self):
        import tkinter as tk
        from gui.ai_native_status_canvas import AIStatusCanvas
        from gui.workspace_background import WorkspaceBackground

        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f'Display no disponible: {exc}')
        try:
            root.geometry('1280x800+0+0')
            master = WorkspaceBackground(root)
            card = tk.Frame(root, width=320, height=90, bd=0, highlightthickness=0)
            card.place(x=895, y=55, width=320, height=90)
            status = AIStatusCanvas(card)
            status.pack(fill='both', expand=True)
            master.register_canvas(status)
            root.update()
            master.refresh()
            root.update_idletasks()
            self.assertTrue(status.find_withtag('_corepulse_native_workspace_canvas'))
            self.assertEqual(len(status.find_withtag('ai_status_text')), 1)
            self.assertEqual(len(status.find_withtag('ai_status_title')), 1)
            self.assertEqual(len(status.find_withtag('ai_status_accent')), 1)
            self.assertEqual(status.coords('ai_status_text'), [160.0, 45.0])
            self.assertEqual(status.itemcget('ai_status_title', 'text'), 'CorePulse AI')
            self.assertEqual(int(status.cget('bd')), 0)
            self.assertEqual(int(status.cget('highlightthickness')), 0)
            self.assertEqual(status.find_all()[-1], status.find_withtag('ai_status_text')[0])

            # Cambiar estado real no dibuja nuevas tarjetas, no destruye capa.
            for state, tone in [('IA LOCAL CONECTADA', '#22d995'),
                                ('INICIANDO IA LOCAL', '#f5b83d'),
                                ('IA LOCAL DESCONECTADA', '#ff5d6c')]:
                status.text_control.configure(text=state)
                status.accent_control.configure(fg_color=tone)
                self.assertEqual(status.itemcget('ai_status_text', 'text'), state)
                self.assertEqual(status.itemcget('ai_status_accent', 'fill'), tone)
                self.assertEqual(len(status.find_withtag('ai_status_text')), 1)
                self.assertEqual(len(status.find_withtag('ai_status_title')), 1)
                self.assertTrue(status.find_withtag('_corepulse_native_workspace_canvas'))

            card.place_configure(width=270)
            root.update()
            master.refresh()
            self.assertEqual(status.coords('ai_status_text'), [135.0, 45.0])
            title_font = status.itemcget('ai_status_title', 'font')
            main_font = status.itemcget('ai_status_text', 'font')
            self.assertTrue(title_font)
            self.assertTrue(main_font)
            self.assertTrue(status.find_withtag('_corepulse_native_workspace_canvas'))
            self.assertEqual(len(status.find_withtag('ai_status_accent')), 1)
            master.destroy()
        finally:
            root.destroy()


if __name__ == '__main__':
    unittest.main()



# ===== Regresión test_v455_sidebar_native_hover (original conservado íntegramente) =====
import ast
import sys
import tkinter as tk
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from gui.sidebar_native_hover import install_native_sidebar_hover
from gui.workspace_background import WorkspaceBackground, _SIDEBAR_CONTROL_TAG

ROOT=Path(__file__).resolve().parents[1]

class CTkButton(tk.Frame):
    def __init__(self, master, fg='transparent', state='normal'):
        super().__init__(master, width=200, height=34, bd=0, highlightthickness=0)
        self.props = {'fg_color': fg, 'bg_color':'transparent','hover_color':'#06111f',
                      'state':state, 'hover':False}
        self.pack_propagate(False)
        self._canvas=tk.Canvas(self,bd=0,highlightthickness=0,width=200,height=34)
        self._canvas.pack(fill='both',expand=True)
        self._text_label=tk.Label(self,text='Botón de prueba',bg='#000000')
        self._text_label.place(x=25,y=7)
    def cget(self,key):
        return self.props.get(key) if key in self.props else super().cget(key)
    def configure(self,cnf=None,**kw):
        if cnf is not None: raise ValueError('unsupported')
        keys=set(self.props)&set(kw)
        self.props.update({key:kw.pop(key) for key in keys})
        if kw: super().configure(**kw)
    config=configure


class NativeSidebarHoverTests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk()
        self.root.geometry('1024x720+0+0')
        self.root._navigation_context='dashboard'
        self.root.sidebar=tk.Frame(self.root,width=245,height=580)
        self.root.sidebar.place(x=12,y=50)
        self.one=CTkButton(self.root.sidebar,fg='#154b74')
        self.one.pack(anchor='w')
        self.two=CTkButton(self.root.sidebar)
        self.two.pack(anchor='w')
        self.three=CTkButton(self.root.sidebar)
        self.three.pack(anchor='w')
        self.root._btn_summary=self.one
        self.root.btn_smart_alerts=self.two
        self.root.btn_session_trends=self.three
        self.root.update()
        ctrl=WorkspaceBackground.__new__(WorkspaceBackground)
        ctrl.parent=self.root
        ctrl._last_size=(1024,720)
        ctrl._palette_last=('#06111f','#0d1828','#1b3048','#14b8ff')
        ctrl._workspace_left=280
        # Render liviano en el MISMO canvas interno (sin montar otra tarjeta).
        def paint(canvas, tag, top=False):
            canvas.delete(tag)
            canvas.create_rectangle(0,0,200,34,fill='#081624',outline='',tags=(tag,))
        ctrl._paint=paint
        self.root.workspace_background=ctrl
        self.stub=types.ModuleType('gui.ui_consistency')
        self.stub.CONTEXT_BUTTON={'dashboard':'_btn_summary', 'alerts':'btn_smart_alerts', 'trends':'btn_session_trends'}
        self.patcher=patch.dict(sys.modules,{'gui.ui_consistency':self.stub})
        self.patcher.start()
        ctrl._paint_sidebar_controls()
        install_native_sidebar_hover(self.root,['_btn_summary','btn_smart_alerts','btn_session_trends'])

    def tearDown(self):
        self.patcher.stop()
        self.root.destroy()

    def _pass_time(self):
        self.root.after(280,self.root.quit)
        self.root.mainloop()

    def test_inactive_hover_reacts_and_restores_without_new_widgets(self):
        normal=self.two.cget('fg_color')
        before=len(self.root.sidebar.winfo_children())
        self.assertTrue(self.two._canvas.find_withtag(_SIDEBAR_CONTROL_TAG))
        self.two.event_generate('<Enter>')
        self.root.update()
        self.assertTrue(self.two._cp_sidebar_hovered)
        self.assertNotEqual(self.two.cget('fg_color'),normal)
        self.assertEqual(self.two._text_label.cget('bg'),self.two.cget('fg_color'))
        self.assertFalse(self.two._canvas.find_withtag(_SIDEBAR_CONTROL_TAG))
        self.two.event_generate('<Leave>')
        self._pass_time()
        self.assertFalse(self.two._cp_sidebar_hovered)
        self.assertEqual(self.two.cget('fg_color'),normal)
        self.assertTrue(self.two._canvas.find_withtag(_SIDEBAR_CONTROL_TAG))
        self.assertEqual(len(self.root.sidebar.winfo_children()),before)

    def test_button_states_independent_and_selected_preserved(self):
        original=self.one.cget('fg_color')
        self.one.event_generate('<Enter>')
        self.root.update()
        self.assertTrue(self.one._cp_sidebar_hovered)
        self.assertFalse(self.two._cp_sidebar_hovered)
        self.assertNotEqual(self.one.cget('fg_color'),original)
        self.one.event_generate('<Leave>')
        self._pass_time()
        # El botón seleccionado permanece seleccionado.
        self.assertNotEqual(self.one.cget('fg_color'),'transparent')

    def test_crossing_internal_elements_no_flicker(self):
        self.two.event_generate('<Enter>')
        self.root.update()
        active=self.two.cget('fg_color')
        self.two.event_generate('<Leave>')
        self.two.event_generate('<Enter>')
        self._pass_time()
        self.assertTrue(self.two._cp_sidebar_hovered)
        self.assertGreater(self.two._cp_sidebar_hover_progress, 0.99)
        self.assertNotEqual(active, self.two.cget('fg_color'))  # progreso animado

    def test_no_new_buttons_and_no_hover_disabled_by_install(self):
        before=len(self.two.bind('<Enter>'))
        install_native_sidebar_hover(self.root, ['btn_smart_alerts'])
        self.assertEqual(len(self.two.bind('<Enter>')),before)
        src=(ROOT/'gui'/'dashboard.py').read_text(encoding='utf-8')
        self.assertIn('install_native_sidebar_hover(app, SIDEBAR_LABELS)',src)
        self.assertNotIn("_safe_config(button, cursor='hand2', hover=True)",src)
        self.assertIn('hovered = kind', (ROOT/'gui'/'workspace_background.py').read_text(encoding='utf-8'))


    def test_v456_slides_existing_text_and_restores_without_layout_change(self):
        # Fake CTkButton coloca el texto con place; el proyecto real usa grid.
        self.assertEqual(int(float(self.two._text_label.place_info()['x'])),25)
        original_size=(self.two.winfo_width(), self.two.winfo_height())
        self.two.event_generate('<Enter>')
        self._pass_time()
        self.assertEqual(self.two._cp_sidebar_hover_progress, 1.0)
        self.assertEqual(int(float(self.two._text_label.place_info()['x'])),30)
        self.assertEqual((self.two.winfo_width(),self.two.winfo_height()),original_size)
        self.two.event_generate('<Leave>')
        self._pass_time()
        self.assertEqual(self.two._cp_sidebar_hover_progress,0.0)
        self.assertEqual(int(float(self.two._text_label.place_info()['x'])),25)
        self.assertIsNone(self.two._cp_sidebar_motion_state['animation'])

    def test_v456_second_button_reverses_previous_automatically(self):
        self.two.event_generate('<Enter>')
        self._pass_time()
        self.three.event_generate('<Enter>')
        self._pass_time()
        self.assertFalse(self.two._cp_sidebar_hovered)
        self.assertTrue(self.three._cp_sidebar_hovered)
        self.assertEqual(self.two._cp_sidebar_hover_progress,0.0)
        self.assertEqual(self.three._cp_sidebar_hover_progress,1.0)
        self.assertEqual(int(float(self.two._text_label.place_info()['x'])),25)
        self.assertEqual(int(float(self.three._text_label.place_info()['x'])),30)

    def test_v456_grid_label_slides_without_changing_button_geometry(self):
        from gui.sidebar_native_hover import _motion_targets, _shift_content
        holder=tk.Frame(self.root,width=180,height=40)
        holder.place(x=360,y=150,width=180,height=40)
        label=tk.Label(holder,text='Prueba movimiento')
        label.grid(row=0,column=0,padx=(4,0),sticky='w')
        class ButtonReference:
            _text_label=label
            _image_label=None
        button=ButtonReference()
        state={'offset':None,'targets':None}
        self.root.update()
        self.assertEqual(len(_motion_targets(button)),1)
        self.assertEqual(label.grid_info()['padx'],(4,0))
        _shift_content(self.root,button,state,1.0)
        self.assertEqual(label.grid_info()['padx'],(9,0))
        _shift_content(self.root,button,state,0.0)
        self.assertEqual(label.grid_info()['padx'],(4,0))
        self.assertEqual(holder.winfo_width(),180)
        holder.destroy()

    def test_v456_selected_and_disabled_motion_policies(self):
        self.one.event_generate('<Enter>')
        self._pass_time()
        self.assertTrue(self.one._cp_sidebar_hover_selected)
        self.assertGreater(self.one._cp_sidebar_hover_progress,.99)
        self.one.event_generate('<Leave>')
        self._pass_time()
        self.assertNotEqual(self.one.cget('fg_color'),'transparent')
        self.three.configure(state='disabled')
        self.three.event_generate('<Enter>')
        self._pass_time()
        self.assertEqual(self.three._cp_sidebar_hover_progress,0.)

if __name__=='__main__': unittest.main()



# ===== Regresión test_v458_disk_scroll_ai_power (original conservado íntegramente) =====

import ast
import os
import re
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def _layout_functions():
    """Extrae las funciones de geometría sin cargar CustomTkinter en Linux."""
    src = ast.parse((ROOT / 'gui/dashboard_layout.py').read_text(encoding='utf-8'))
    names = {'_storage_height_for', '_system_disk_sort_key',
             '_storage_card_bottom_padding', '_hide_storage_scrollbar_if_possible',
             '_finalize_storage_viewport'}
    selected = [node for node in src.body
                if isinstance(node, ast.FunctionDef) and node.name in names]
    ns = {'os': os, 're': re, '_cfg': lambda w, **kw: w.configure(**kw)}
    exec(compile(ast.Module(body=selected, type_ignores=[]), '<layout>', 'exec'), ns)
    return ns


class FakeCard:
    def __init__(self):
        self.forgets = 0
        self.pack_calls = []
    def pack_propagate(self, *_): pass
    def pack_forget(self): self.forgets += 1
    def pack_configure(self, **kw): self.pack_calls.append(kw)
    def pack(self, **kw): self.pack_calls.append(kw)


class FakeScrollbar:
    def __init__(self): self.state = None
    def grid(self): self.state = 'visible'
    def grid_remove(self): self.state = 'hidden'


class FakeHost:
    def __init__(self):
        self.height = None
        self._scrollbar = FakeScrollbar()
        self.content = SimpleNamespace(update_idletasks=lambda: None)
        self.position = 0.0
        self.scrollresets = 0
    def configure(self, **kw): self.height = kw.get('height', self.height)
    def grid_propagate(self, *_): pass
    def pack_configure(self, **_kw): pass
    def update_idletasks(self): pass
    def yview_moveto(self, position): self.position = position; self.scrollresets += 1
    def _schedule_geometry(self, *_): pass


class TestStorageScrolling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.funcs = _layout_functions()

    def test_one_disc_high_even_when_three_are_detected(self):
        for n in (1, 2, 3, 9):
            self.assertEqual(86, self.funcs['_storage_height_for'](
                SimpleNamespace(disk_widgets=dict.fromkeys(range(n))), 'large'))

    def test_windows_system_volume_first(self):
        key = self.funcs['_system_disk_sort_key']
        disks = {1: {'mount_points': 'D:\\'}, 5: {'mount_points': 'C:\\'},
                 7: {'mount_points': 'E:\\'}}
        self.assertEqual([5, 1, 7], sorted(disks, key=lambda x: key(x, disks[x])))
        self.assertEqual(0, key(9, {'mount_points': 'C:; D:'})[0])

    def test_do_not_reset_scroll_when_sensors_refresh(self):
        host = FakeHost()
        disks = {0: {'card': FakeCard()}, 1: {'card': FakeCard()}}
        app = SimpleNamespace(
            disk_widgets=disks, latest_disks=[
                {'index': 0, 'mount_points': 'C:\\'},
                {'index': 1, 'mount_points': 'D:\\'},
            ], scroll_disks=host,
            _layout_mode='compact',
            after=lambda *a: None, after_idle=lambda *a: None,
        )
        layout = self.funcs['_finalize_storage_viewport']
        layout(app, 'compact')
        self.assertEqual(host.height, 86)
        self.assertEqual(host._scrollbar.state, 'visible')
        host.position = 0.63
        resets = host.scrollresets
        layout(app, 'compact')
        self.assertEqual(host.position, 0.63)
        self.assertEqual(host.scrollresets, resets)
        self.assertEqual([disks[k]['card'].forgets for k in (0,1)], [1,1])
        app.disk_widgets.pop(1)
        app.latest_disks.pop()
        layout(app, 'compact')
        self.assertEqual(host._scrollbar.state, 'hidden')
        self.assertEqual(host.position, 0.0)


class TestLocalAIPower(unittest.TestCase):
    def test_preference_survives_reload_and_defaults_on(self):
        from core import ai_user_control as control
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / 'ai_power.json'
            with patch.object(control, '_file', return_value=destination):
                self.assertTrue(control.load_ai_enabled())
                control.save_ai_enabled(False)
                self.assertFalse(control.load_ai_enabled())
                control.save_ai_enabled(True)
                self.assertTrue(control.load_ai_enabled())

    def test_stop_terminates_only_owned_runtime_process(self):
        import threading
        from core.ai_runtime_manager import LocalAIRuntimeManager

        class FakeProcess:
            def __init__(self): self.terminated = False
            def poll(self): return 0 if self.terminated else None
            def terminate(self): self.terminated = True
            def wait(self, timeout=None): return 0
            def kill(self): self.terminated = True

        manager = object.__new__(LocalAIRuntimeManager)
        manager._lock = threading.RLock()
        manager._stop_event = threading.Event()
        proc = FakeProcess()
        external = FakeProcess()
        manager._owned_processes = {'corepulse_ai_model': proc}
        manager._embedded_server = None
        manager._embedded_server_thread = None
        manager._log_handles = []
        manager._state = {'state':'READY'}
        manager.stop()
        self.assertTrue(proc.terminated)
        self.assertFalse(external.terminated)
        self.assertEqual(manager.status()['state'], 'STOPPED')

    def test_canvas_power_switch_is_on_same_tk_surface(self):
        from gui.ai_native_status_canvas import AIStatusCanvas
        root = tk.Tk()
        try:
            root.geometry('500x220+0+0')
            canvas = AIStatusCanvas(root)
            canvas.place(x=40, y=35, width=320, height=90)
            root.update()
            calls = []
            canvas.set_power_action(lambda: calls.append('toggle'))
            self.assertEqual(canvas._power_click(SimpleNamespace(x=300, y=19)), 'break')
            self.assertEqual(calls, ['toggle'])
            self.assertIsNone(canvas._power_click(SimpleNamespace(x=125, y=60)))
            canvas.set_power_enabled(False)
            self.assertEqual(canvas.itemcget(canvas._power_hint_id, 'text'), 'Encender IA')
            canvas._power_motion(SimpleNamespace(x=300, y=19))
            self.assertEqual(canvas.itemcget(canvas._power_hint_id, 'state'), 'normal')
            canvas._power_leave()
            self.assertEqual(canvas.itemcget(canvas._power_hint_id, 'state'), 'hidden')
            self.assertEqual(len(canvas.find_withtag('ai_power')), 3)
        finally:
            root.destroy()


if __name__ == '__main__':
    unittest.main()

# ===== Regresión V440: contratos de cabeceras, GUI_ROOT local =====
import ast
from pathlib import Path
import re
import unittest

GUI_ROOT = Path(__file__).resolve().parents[1] / 'gui'
PAGES = (
    'benchmark_panel.py', 'cleaning_center.py', 'windows_tweaks_panel.py',
    'network_detail_panel.py', 'gaming_panel.py', 'ai_panel.py',
    'theme_panel.py', 'alert_panel.py', 'alert_history_panel.py',
    'session_trends_panel.py', 'overlay_config_panel.py', 'diagnostic_view.py',
    'health_center_panel.py', 'cpu_detail_panel.py', 'gpu_detail_panel.py',
    'ram_detail_panel.py', 'storage_detail_panel.py', 'telemetry_detail_panel.py',
)


def _source_path(fname: str) -> Path:
    """V478: localizar módulos GUI reagrupados sin omitir ninguna verificación.

    Los contratos de cabeceras se aplican al archivo auténtico, no a un stub.
    """
    direct = GUI_ROOT / fname
    if direct.is_file():
        return direct
    locations = list(GUI_ROOT.glob(f'*/{fname}'))
    if len(locations) != 1:
        raise FileNotFoundError(f'Se esperaba un único módulo GUI {fname}: {locations}')
    return locations[0]


class TestPageHeaderRemoval(unittest.TestCase):
    def test_page_modules_still_parse(self):
        for fname in PAGES:
            with self.subTest(fname=fname):
                ast.parse((_source_path(fname)).read_text(encoding='utf-8'))

    def test_introductory_header_not_mapped(self):
        for fname in PAGES:
            with self.subTest(fname=fname):
                src = (_source_path(fname)).read_text(encoding='utf-8')
                decl = re.search(r'(?m)^\s*header = ctk\.CTkFrame\(', src)
                self.assertIsNotNone(decl, f'{fname}: no top-level header')
                # The first header in these page builders is the intro hero.
                nearby = src[decl.end():decl.end() + 280]
                self.assertNotRegex(nearby, r'(?m)^\s*header\.(?:pack|grid)\(')

    def test_tweaks_does_not_restore_header_after_restore_center(self):
        src = (GUI_ROOT / 'windows_tweaks_panel.py').read_text(encoding='utf-8')
        self.assertNotRegex(src, r'(?m)^\s*self\.header_bar\.pack\(')
        self.assertIn('self.header_bar.pack_forget()', src)

    def test_benchmark_tabs_and_content_remain(self):
        src = (GUI_ROOT / 'benchmark_panel.py').read_text(encoding='utf-8')
        self.assertIn("self._run_tab.pack(side='left'", src)
        self.assertIn("self._history_tab.pack(side='left'", src)
        self.assertIn("self._content.pack(fill='both'", src)

    def test_diagnostic_controls_remain_accessible_below_header(self):
        src = (GUI_ROOT / 'diagnostic_view.py').read_text(encoding='utf-8')
        self.assertIn("detail_actions.grid(row=0, column=1", src)
        self.assertIn('self.btn_cancel.grid_remove()', src)
        self.assertIn('command=self._open_sensor_compatibility', src)
        self.assertIn("command=getattr(self.app, 'cancel_diagnostic_session'", src)

    def test_storage_and_telemetry_refresh_still_accessible(self):
        for fname in ('storage_detail_panel.py', 'telemetry_detail_panel.py'):
            with self.subTest(fname=fname):
                src = (_source_path(fname)).read_text(encoding='utf-8')
                self.assertIn("actions.pack(fill='x'", src)
                self.assertIn("text='Actualizar'", src)


if __name__ == '__main__':
    unittest.main()
