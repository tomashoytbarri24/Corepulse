"""V474: cifras educativas verificadas sintéticamente y protección de sensores."""
from unittest.mock import patch

from CorePulse_AI_Server.app.guardrails import validate_model_response, POLICY_VERSION
from CorePulse_AI_Server.app.educational_guide import safe_educational_fallback
from CorePulse_AI_Server.app.model_gateway import build_messages
from CorePulse_AI_Server.app import main

Q = 'Dame un tutorial general de mantenimiento preventivo, paso a paso y sin asumir averías.'
CTX = {
    'cpu': {'temperature_c': 45, 'usage_percent': 8},
    'gpu': {'temperature_c': 36, 'usage_percent': 12},
    'ram': {'used_gb': 8, 'total_gb': 16, 'usage_percent': 50},
    'storage': [{'used_percent': 74}],
}


def test_educational_concentration_not_assumed_hardware_telemetry():
    r = validate_model_response(CTX, 'Usa alcohol isopropílico al 70% según el manual, sin verterlo sobre componentes.', question=Q)
    assert r['allowed'] and r['policy_version'] == POLICY_VERSION
    assert not validate_model_response(CTX, 'Usa alcohol isopropílico al 70% según el manual.', question='¿Cómo va la RAM?')['allowed']


def test_not_whitelist_arbitrary_percentages_or_bad_hardware_claims():
    cases = [
        'Tu CPU utiliza un 98% actualmente.',
        'La GPU está a 96 °C.',
        'La RAM está usando 93%.',
        'El disco está a un 92% de ocupación.',
        'Los FPS reales son 120 FPS.',
        'Puedes cambiar la BIOS porque ya hemos reparado Windows.',
    ]
    for text in cases:
        result = validate_model_response(CTX, text, question=Q)
        assert not result['allowed'], (text, result)


def test_unverified_external_links_remain_blocked():
    response = 'Mira este video verificado: https://youtube.com/watch?v=falso123.'
    assert 'UNVERIFIED_LINK' in validate_model_response(CTX, response, question=Q)['codes']


def test_tutorial_steps_readable_and_no_claim_of_verified_video():
    out = safe_educational_fallback(Q)
    assert '\n1.' in out and '\n2.' in out and '\n3.' in out
    assert 'No he verificado ningún video' in out


def test_production_model_rejected_if_cpu_invented_even_in_educational_mode():
    with patch.object(main, 'model_ready', return_value=True), patch.object(main, 'generate', return_value='La CPU está a 96 °C.'):
        output, mode, verdict = main._safe_generation(CTX, Q, task='chat', history=[])
    assert mode == 'evidence_fallback'
    assert 'UNSUPPORTED_TEMP' in verdict['codes']
    assert '96 °C' not in output


def test_production_allows_genuine_educational_response():
    with patch.object(main, 'model_ready', return_value=True), patch.object(main, 'generate', return_value='Para limpiar las partes externas, consulta el manual y usa alcohol isopropílico al 70% solo si el fabricante lo permite.'):
        output, mode, verdict = main._safe_generation(CTX, Q, task='chat', history=[])
    assert mode == 'model' and verdict['allowed']
    assert '70%' in output


def test_no_external_data_without_explicit_consent_contract_preserved():
    src = __import__('pathlib').Path(__file__).resolve().parents[1].joinpath('gui', 'ai_panel.py').read_text(encoding='utf-8')
    assert 'gate = _cloud_gate(self.settings)' in src
    assert 'cloud_telemetry_consent' in src
    assert 'Conectar IA' in src


def test_prompt_does_not_invent_sensor_metrics_for_educational_request():
    last=build_messages(CTX,Q)[-1]['content']
    assert 'No informes porcentajes de uso' in last
    assert 'No recomiendes líquidos directamente' in last
