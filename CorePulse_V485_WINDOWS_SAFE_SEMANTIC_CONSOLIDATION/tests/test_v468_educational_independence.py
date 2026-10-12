"""V468: educación sin alucinaciones, independencia del LLM y UI plegable."""
from __future__ import annotations
import sys
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / 'CorePulse_AI_Server'
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))

from app import main, model_gateway
from app.educational_guide import educational_intent, safe_educational_fallback
from app.evidence import sanitize_context, fallback_answer
from app.guardrails import validate_model_response

CTX = sanitize_context({
    'cpu': {'temperature_c': None, 'usage_percent': 2},
    'gpu': {'temperature_c': None},
    'storage': [{'used_percent': 75, 'health_percent': None, 'model': 'Disco sin SMART'}],
    'decision': {'attention_areas': [], 'thermal_alerts': []},
    'deterministic_assessment': {'problem_recommendations': []},
})


def test_preventive_tutorial_does_not_require_alarm_or_model():
    question = 'Puedes darme un tutorial de mantención pls'
    assert educational_intent(question) == 'preventive_maintenance'
    answer = fallback_answer(CTX, question)
    assert 'mantenimiento preventivo' in answer
    assert '1.' in answer
    assert 'no es un diagnóstico' in answer
    assert 'problem_recommendations' not in answer
    assert 'https://' not in answer
    assert '75%' not in answer  # No confundir ocupación con salud.


def test_physical_tutorial_limits_specific_instructions():
    answer = safe_educational_fallback('tutorial de limpieza de ventiladores', CTX)
    assert 'manual oficial' in answer
    assert 'técnico' in answer
    assert 'video específico verificado' in answer
    assert 'https://' not in answer


def test_hardware_measurements_still_real_or_na():
    answer = fallback_answer(CTX, '¿Cómo están las temperaturas de mi CPU y GPU?')
    assert 'N/A' in answer
    assert educational_intent('¿Cómo están las temperaturas de mi CPU y GPU?') == ''
    assert 'mantenimiento preventivo' not in answer


def test_prompt_prioritizes_tutorial_before_problem_recommendations():
    focus = model_gateway._focus_instruction('Dame tutorial de mantención')
    assert 'tutorial' in focus.lower()
    assert 'no dependas' in focus
    messages = model_gateway.build_messages(CTX,'Dame tutorial de mantención')
    assert 'mantenimiento preventivo' in messages[0]['content'].lower()
    assert 'No menciones campos JSON' in messages[-1]['content']


def test_model_cannot_expose_json_internal_fields():
    for field in ['problem_recommendations', 'deterministic_assessment', 'evidence_snapshot', 'telemetry_available']:
        verdict = validate_model_response(CTX, f'Consulta {field} y vuelve luego.')
        assert not verdict['allowed']
        assert 'INTERNAL_IMPLEMENTATION_LEAK' in verdict['codes']


def test_safe_educational_reply_passes_guardrails():
    answer = safe_educational_fallback('tutorial de mantenimiento', CTX)
    assert validate_model_response(CTX, answer)['allowed']


def test_model_bad_educational_reply_replaced_with_safe_fallback():
    with patch.object(main,'model_ready',return_value=True),patch.object(main,'generate',return_value='No hay tutorial porque problem_recommendations está vacío.'):
        text, mode, verdict = main._safe_generation(CTX,'tutorial de mantenimiento',task='chat',history=[])
    assert mode=='evidence_fallback'
    assert 'mantenimiento preventivo' in text
    assert verdict['codes'] == ['INTERNAL_IMPLEMENTATION_LEAK']


def test_model_unavailable_gives_useful_tutorial_without_fabrication():
    with patch.object(main,'model_ready',return_value=False):
        text, mode, verdict = main._safe_generation(CTX,'tutorial de mantención',task='chat',history=[])
    assert mode=='evidence_fallback'
    assert verdict['allowed']
    assert 'pasos' not in text.lower() or '1.' in text
    assert 'Windows' in text


def test_gui_toggle_includes_existing_consent_and_onboarding():
    text=(ROOT/'gui/ai_panel.py').read_text(encoding='utf8')
    assert 'self.cloud_bar.pack_forget()' in text
    assert 'before=self.body_frame' in text
    assert 'command=self._toggle_connection_settings' in text
    assert 'self._connection_expanded = False' in text
    assert 'self._sync_consent_controls()' in text
    assert 'Mantención' in text
    assert 'self.cloud_consent' in text and 'save_ai_settings' in text


def test_inference_remains_remote_and_adapter_reusable():
    prompt=(ROOT/'CorePulse_AI_Server/app/model_gateway.py').read_text(encoding='utf8')
    assert 'MODEL_BASE_URL' in prompt
    assert "MODEL_BASE_URL + '/chat/completions'" in prompt
    assert "if MODEL_PROVIDER == 'groq':" in prompt
    assert not (ROOT/'CorePulse_AI_Server/app/educational_guide.py').read_text(encoding='utf8').find('import torch') >= 0
