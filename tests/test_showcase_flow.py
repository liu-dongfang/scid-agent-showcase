from __future__ import annotations

from server.orchestrator.event_bus import EventBus
from server.orchestrator.events import Event
from server.orchestrator.flow_controller import FlowController
from server.services.report_service import build_report_from_session


def _record_answer(controller, session, agenda, evidence):
    controller.update_evidence(session, agenda, evidence)
    controller.advance_item(session)


def _finish_module_if_needed(controller, session):
    if session.current_phase != "CoreModules" or not session.current_module:
        return
    items = controller.module_question_cache.get(session.current_module, [])
    if session.current_item_index >= len(items):
        controller.handle_event(
            session,
            Event.MODULE_DONE,
            {"session_id": session.session_id, "module": session.current_module},
        )
        controller.transition(session)


def test_showcase_flow_reaches_reporting():
    bus = EventBus()
    controller = FlowController(event_bus=bus)
    session = controller.initialize_session()

    agenda = controller.get_current_agenda(session)
    _record_answer(
        controller,
        session,
        agenda,
        {
            "presenting_problem": "Difficulty sleeping and lower motivation.",
            "onset_and_context": "Began four weeks ago after workload increased.",
        },
    )
    controller.transition(session)

    screening_answers = {
        "SCR_low_mood": {"binary_response": "YES"},
        "SCR_high_arousal": {"binary_response": "YES"},
    }
    while session.current_phase == "Screening":
        agenda = controller.get_current_agenda(session)
        _record_answer(controller, session, agenda, screening_answers[agenda.item_id])
        controller.transition(session)

    module_answers = {
        "MOOD_sleep_disruption": {
            "presence": True,
            "duration_weeks": 4,
            "frequency": "almost_daily",
            "impairment_domains": ["work"],
        },
        "MOOD_loss_of_interest": {
            "presence": True,
            "duration_weeks": 4,
            "frequency": "several_times_week",
            "impairment_domains": ["social"],
        },
        "ANX_worry_cycle": {
            "presence": True,
            "duration_weeks": 4,
            "frequency": "almost_daily",
            "impairment_domains": ["work", "social"],
        },
        "ANX_panic_like_episode": {
            "unexpected_onset": True,
            "peak_in_minutes": True,
            "symptom_count": 4,
            "impairment_domains": ["work"],
        },
    }
    while session.current_phase == "CoreModules":
        agenda = controller.get_current_agenda(session)
        _record_answer(controller, session, agenda, module_answers[agenda.item_id])
        _finish_module_if_needed(controller, session)

    while session.current_phase in {"ComorbidityAppendix", "Differential"}:
        controller.transition(session)

    session.whodas_score = {"raw_total_0to48": 8, "metric_0to100": 16.7}
    session.clinical_significance = {"decision": True, "rationale": "Synthetic impairment marker."}
    controller.transition(session)

    report = build_report_from_session(session)

    assert session.current_phase == "Reporting"
    assert report["differential_result"]["candidate_diagnoses"]
    assert any(event is Event.COMORBIDITY_EXPLORE for event, _ in bus.history)
    assert any(entry["module"] == "CORE_MODULE_MOOD" for entry in report["core_modules"])
