"""Construcción de evidencia de CorePulse AI en el instante de cada consulta.

La IA nunca lee sensores por su cuenta. Cada pregunta recibe una fotografía creada
por CorePulse con telemetría real, salud determinista, identidad de hardware y, si
corresponde, planes de acción ya decididos por código. El modelo sólo redacta.
"""
from __future__ import annotations

from datetime import datetime, timezone
import unicodedata
from typing import Any

from core.ai_action_intelligence import collect_ai_inventory, build_deterministic_assessment
from core.ai_client import build_runtime_context
from core.tutorial_research import enrich_plans_with_tutorials

_QUERY_POLICY = "QUERY_TIME_REAL_EVIDENCE_ONLY"
_ALERT_LEVELS = {"ATTENTION", "ELEVATED", "WARNING", "WARN", "CRITICAL", "ERROR"}


def _text(value: Any, limit: int = 300) -> str:
    return str(value or "").strip()[:limit]


def _norm(value: Any) -> str:
    raw = unicodedata.normalize("NFD", str(value or "").lower())
    return "".join(ch for ch in raw if unicodedata.category(ch) != "Mn")


def _live_findings(health: Any, agent_state: Any) -> list[dict]:
    """Convierte sólo clasificaciones ya emitidas por CorePulse en findings.

    No compara temperaturas ni crea umbrales. Si la salud actual es NORMAL, una
    temperatura numérica por sí sola nunca se convierte en hallazgo.
    """
    health = health if isinstance(health, dict) else {}
    agent_state = agent_state if isinstance(agent_state, dict) else {}
    out: list[dict] = []

    severity = _text(health.get("severity") or health.get("state"), 32).upper()
    if severity in _ALERT_LEVELS:
        for reason in list(health.get("reasons") or [])[:12]:
            reason_text = _text(reason, 400)
            if reason_text:
                out.append({
                    "severity": severity,
                    "component": "SYSTEM",
                    "title": reason_text,
                    "detail": reason_text,
                    "reason": reason_text,
                    "source": "COREPULSE_LIVE_HEALTH",
                })

    alerts = agent_state.get("alerts") if isinstance(agent_state.get("alerts"), dict) else {}
    for item in list(alerts.get("active") or [])[:12]:
        if not isinstance(item, dict):
            continue
        item_severity = _text(item.get("severity") or item.get("level"), 32).upper()
        if item_severity not in _ALERT_LEVELS:
            continue
        out.append({
            "severity": item_severity,
            "component": _text(item.get("component") or item.get("source") or "SYSTEM", 80),
            "title": _text(item.get("title") or item.get("message") or item.get("reason"), 180),
            "detail": _text(item.get("detail") or item.get("message") or item.get("reason"), 400),
            "reason": _text(item.get("reason") or item.get("message") or item.get("detail"), 400),
            "source": "COREPULSE_SUSTAINED_ALERT",
        })
    return out


def _extract_completed_assessment(diagnostic_result: Any) -> dict:
    diagnostic_result = diagnostic_result if isinstance(diagnostic_result, dict) else {}
    complete = diagnostic_result.get("complete_diagnostic") if isinstance(diagnostic_result.get("complete_diagnostic"), dict) else {}
    ai = complete.get("ai_analysis") if isinstance(complete.get("ai_analysis"), dict) else {}
    if not ai and isinstance(diagnostic_result.get("_ai_analysis"), dict):
        ai = diagnostic_result.get("_ai_analysis")
    assessment = ai.get("deterministic_assessment") if isinstance(ai.get("deterministic_assessment"), dict) else {}
    return dict(assessment) if assessment else {}


def _asks_for_completed_diagnostic(question: str) -> bool:
    q = _norm(question)
    return any(token in q for token in (
        "ultimo diagnostico", "diagnostico anterior", "resultado del diagnostico",
        "segun el diagnostico", "informe del diagnostico",
    ))


def wants_tutorial_enrichment(question: str, *, analysis_request: bool = False) -> bool:
    """Limita búsquedas en línea a consultas donde realmente aportan valor."""
    if analysis_request:
        return True
    q = _norm(question)
    return any(token in q for token in (
        "tutorial", "youtube", "como instalar", "como cambiar", "como reemplazar",
        "ampliar ram", "upgrade ram", "comprar ram", "cambiar ram",
        "comprar ssd", "cambiar ssd", "reemplazar ssd", "upgrade ssd",
        "pasta termica", "mantenimiento termico", "limpiar ventilador", "desarmar",
    ))


def build_query_context(
    telemetry: Any,
    disks: Any,
    health: Any,
    *,
    question: str = "",
    agent_state: Any = None,
    diagnostic_result: Any = None,
    analysis_request: bool = False,
) -> dict:
    """Crea el contexto que se congela para UNA consulta de CorePulse AI."""
    telemetry = telemetry if isinstance(telemetry, dict) else {}
    disks = disks if isinstance(disks, list) else []
    health = health if isinstance(health, dict) else {}
    agent_state = agent_state if isinstance(agent_state, dict) else {}

    context = build_runtime_context(telemetry, disks, health)
    inventory = collect_ai_inventory(telemetry, disks)
    live_diagnostic = {
        "score": health.get("score"),
        "status": health.get("status") or health.get("state"),
        "severity": health.get("severity") or health.get("state"),
        "findings": _live_findings(health, agent_state),
    }
    assessment = build_deterministic_assessment(
        live_diagnostic,
        telemetry,
        disks,
        inventory,
        year=datetime.now().year,
    )

    assessment_source = "LIVE_QUERY_SNAPSHOT"
    completed = _extract_completed_assessment(diagnostic_result)
    if completed and _asks_for_completed_diagnostic(question):
        assessment = completed
        assessment_source = "LAST_COMPLETED_DIAGNOSTIC"

    plans = list(assessment.get("problem_recommendations") or [])
    if plans and wants_tutorial_enrichment(question, analysis_request=analysis_request):
        try:
            # Nunca transmitir el modelo del equipo a un buscador externo desde el cliente.
            # Esta ruta genera SEARCH_ONLY sin abrir conexiones de red.
            plans = enrich_plans_with_tutorials(plans, inventory, max_lookups=4, timeout=3.0, allow_network=False)
        except Exception:
            # El fallo de una búsqueda externa jamás invalida la evidencia local.
            pass
        assessment = dict(assessment)
        assessment["problem_recommendations"] = plans

    device = inventory.get("device") if isinstance(inventory.get("device"), dict) else {}
    context["device"] = dict(device)
    context["current_year"] = datetime.now().year
    context["deterministic_assessment"] = assessment
    context["evidence_snapshot"] = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "COREPULSE_LIVE_TELEMETRY",
        "policy": _QUERY_POLICY,
        "assessment_source": assessment_source,
        "telemetry_available": bool(telemetry),
        "storage_devices": len(disks),
    }

    # Reconciliación: la lista final de atención proviene de evaluaciones de
    # CorePulse, nunca de la red generativa.
    decision = context.get("decision") if isinstance(context.get("decision"), dict) else {}
    areas = list(decision.get("attention_areas") or [])
    for area in list(assessment.get("attention_areas") or []):
        area = _text(area, 48)
        if area and area not in areas:
            areas.append(area)
    decision["attention_areas"] = areas[:12]

    thermal = []
    for plan in plans:
        if not isinstance(plan, dict):
            continue
        title = _norm(plan.get("title"))
        component = _text(plan.get("component_type"), 48)
        if component and any(token in title for token in ("termica", "thermal", "temperatura")) and component not in thermal:
            thermal.append(component)
    # Sólo elevamos alertas térmicas si la inteligencia determinista de CorePulse
    # produjo un plan térmico; nunca por mirar el número de °C.
    if thermal:
        decision["thermal_alerts"] = thermal[:4]
    context["decision"] = decision
    return context


__all__ = ["build_query_context", "wants_tutorial_enrichment"]
