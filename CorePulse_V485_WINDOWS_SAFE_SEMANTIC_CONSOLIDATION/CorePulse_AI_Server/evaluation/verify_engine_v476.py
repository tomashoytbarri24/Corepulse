"""Validación V476 offline sin sensores locales ni conexión a proveedores."""
from datetime import datetime, timezone, timedelta
from CorePulse_AI_Server.app.evidence import sanitize_context
from CorePulse_AI_Server.app.intelligence_engine import analyze_evidence

def main():
    current=datetime.now(timezone.utc).isoformat(timespec='seconds')
    previous=(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat(timespec='seconds')
    older={'source':'COREPULSE_QUERY_SNAPSHOT','captured_at_utc':previous,'metrics':{'cpu':{'temperature_c':46}}}
    context=sanitize_context({'cpu':{'temperature_c':54},'evidence_snapshot':{'captured_at_utc':current},'observation_history':[older]})
    report=analyze_evidence(context)
    assert report['timeline']['status']=='TWO_SNAPSHOTS_COMPARABLE'
    assert report['timeline']['comparisons'][0]['delta']==8
    assert report['findings']==[]
    print('COREPULSE_INVESTIGATION_V476_PASS')
    print('1 comparación temporal sintética, sin alerta inventada; cero solicitudes de red.')

if __name__=='__main__':
    main()
