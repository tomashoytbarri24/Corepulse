"""Report content regressions, independent of font rendering and hardware."""
from types import SimpleNamespace
from core.health.report import ReportExporter


class RecordingDocument:
    def __init__(self):
        self.card_groups=[]
        self.paragraphs=[]
        self.tables=[]
        self.sections=[]

    def cards(self, values):
        self.card_groups.append(values)

    def paragraph(self, text, **options):
        self.paragraphs.append(text)

    def table(self, rows, **options):
        self.tables.extend(rows)

    def section(self, title, **options):
        self.sections.append(title)

    def note(self, text):
        self.paragraphs.append(text)

    def _new_page(self):
        self.sections.append('page-break')

    def bar_chart(self, title, values):
        self.sections.append(title)


def exporter(summary, *, benchmark=None):
    health=SimpleNamespace(data=summary,diagnostic={},diagnosticChanged=SimpleNamespace(connect=lambda callback:None))
    telemetry=SimpleNamespace(metrics={'computer':'Equipo de prueba','cpuTemp':None,'gpuTemp':None,'cpuPercent':0})
    return ReportExporter(telemetry,health,SimpleNamespace(data={}),benchmark_controller=benchmark)


def test_diagnostic_keeps_missing_readings_distinct_from_verified_zero():
    summary={'state':'partial','coverage':'1/2','checks':[
        {'title':'Temperatura CPU','value':'N/A','state':'na','detail':'Sin sensor'},
        {'title':'Dispositivos con problemas','value':'0','state':'ok','detail':'Comprobación disponible'},
    ]}
    document=RecordingDocument()
    exporter(summary)._build_diagnostic_report(document,{'status':'partial','runId':1,'summary':summary})
    rows=dict(document.tables)
    assert rows['Temperatura CPU'].startswith('N/A · Sin datos · ')
    assert 'no confirma una avería' in rows['Temperatura CPU']
    assert rows['Dispositivos con problemas'].startswith('0 · Correcto · ')
    assert document.card_groups[0][0][1]=='Parcial'


def test_diagnostic_never_reads_benchmark_results():
    class UnrelatedBenchmark:
        @property
        def data(self):
            raise AssertionError('A diagnostic PDF must not read benchmark results')
    summary={'state':'ok','coverage':'1/1','checks':[]}
    document=RecordingDocument()
    exporter(summary,benchmark=UnrelatedBenchmark())._build_diagnostic_report(
        document,{'status':'complete','runId':2,'summary':summary})
    assert document.card_groups[0][0][1]=='Correcto'
    assert 'Resumen del diagnóstico' in document.sections
    assert not any('benchmark' in section.lower() for section in document.sections)


def test_general_report_preserves_full_headline_and_unknown_state(monkeypatch,tmp_path):
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path))
    headline='Lecturas insuficientes para evaluar todas las áreas del equipo'
    summary={'state':'partial','headline':headline,'coverage':'0/8','checks':[]}
    document=RecordingDocument()
    exporter(summary)._build_system_report(document)
    assert document.card_groups[0][0][1]=='Parcial'
    assert headline in document.paragraphs
    assert not any('Sin evaluar' in str(group) for group in document.card_groups)


def test_unrecognized_indicator_state_is_not_reported_as_healthy():
    summary={'state':'unknown','checks':[{'title':'Lectura pendiente','value':'N/A','state':'unrecognized'}]}
    document=RecordingDocument()
    exporter(summary)._build_diagnostic_report(document,{'status':'partial','summary':summary})
    assert document.card_groups[0][0][1]=='Sin datos'
    assert dict(document.tables)['Lectura pendiente'].startswith('N/A · Sin datos')


def test_recovery_warning_explains_next_step_without_implying_a_backup():
    summary={'state':'attention','checks':[{'key':'recovery','title':'Recuperación','value':'Inactivo','state':'attention'}]}
    doc=RecordingDocument()
    exporter(summary)._build_diagnostic_report(doc,{'status':'complete','summary':summary})
    assert any('Abre Recuperación' in text for text in doc.paragraphs)
    assert 'No son una copia de tus archivos' in dict(doc.tables)['Recuperación']


def test_system_report_omits_registry_paths_but_keeps_readable_program_names(monkeypatch,tmp_path):
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path))
    report=exporter({'state':'partial','checks':[]})
    report.windows_health=SimpleNamespace(data={'startup':{'metric':'1','items':[{'primary':'Aplicación de prueba','secondary':'HKU\\S-1-5-21\\Software\\CurrentVersion\\Run'}]}})
    doc=RecordingDocument();report._build_system_report(doc)
    all_text=' '.join(doc.paragraphs)
    assert 'Aplicación de prueba' in all_text
    assert 'HKU' not in all_text and 'S-1-5-21' not in all_text


def test_benchmark_keeps_measurements_and_moves_api_codes_to_support_appendix():
    report=exporter({})
    doc=RecordingDocument()
    report._append_benchmarks(doc,{'gpuResult':{'status':'OK','benchmark_method':'dx11','window_mode':'WINDOWED_NATIVE','scenes':[
        {'key':'avenue','status':'OK','frames_per_s':120,'one_percent_low_fps':60},
        {'key':'district','status':'OK','frames_per_s':80,'one_percent_low_fps':40},
    ]}})
    assert doc.card_groups[0][0][1]=='100,0 FPS'
    assert doc.card_groups[0][1][1]=='50,0 FPS'
    assert doc.sections.index('Tarjeta gráfica') < doc.sections.index('page-break') < doc.sections.index('Detalles técnicos - para soporte')
    assert dict(doc.tables)['Modo de pantalla']=='WINDOWED_NATIVE'
    assert any('FPS son imágenes por segundo' in text for text in doc.paragraphs)
