from __future__ import annotations

import json
from pathlib import Path

from server.orchestrator.event_bus import EventBus
from server.orchestrator.events import Event
from server.orchestrator.flow_controller import FlowController
from server.orchestrator.session_state import AgendaItem, SessionState
from server.services.report_service import build_report_from_session
from server.services.transcript_importer import import_transcript_to_session
from server.utils.logger import configure_logging


def _record_answer(
    controller: FlowController,
    session: SessionState,
    agenda: AgendaItem,
    evidence: dict[str, object],
) -> None:
    controller.update_evidence(session, agenda, evidence)
    controller.advance_item(session)


def _finish_module_if_needed(controller: FlowController, session: SessionState) -> None:
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


def run_controller_demo() -> dict[str, object]:
    bus = EventBus()
    controller = FlowController(event_bus=bus)
    session = controller.initialize_session()

    agenda = controller.get_current_agenda(session)
    _record_answer(
        controller,
        session,
        agenda,
        {
            "presenting_problem": "Lower mood, poor sleep, and reduced enjoyment after work.",
            "onset_and_context": "Started around a month ago during a sustained deadline period.",
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
            "source_snippet": "I sleep lightly and struggle the next morning.",
        },
        "MOOD_loss_of_interest": {
            "presence": True,
            "duration_weeks": 4,
            "frequency": "several_times_week",
            "impairment_domains": ["social"],
            "source_snippet": "I skip plans because nothing sounds appealing.",
        },
        "ANX_worry_cycle": {
            "presence": True,
            "duration_weeks": 4,
            "frequency": "almost_daily",
            "impairment_domains": ["work", "social"],
            "source_snippet": "The worry keeps looping during the day.",
        },
        "ANX_panic_like_episode": {
            "unexpected_onset": True,
            "peak_in_minutes": True,
            "symptom_count": 4,
            "avoidance_behavior": False,
            "impairment_domains": ["work"],
            "source_snippet": "I had to leave the room when it spiked.",
        },
    }

    while session.current_phase == "CoreModules":
        agenda = controller.get_current_agenda(session)
        _record_answer(controller, session, agenda, module_answers[agenda.item_id])
        _finish_module_if_needed(controller, session)

    while session.current_phase in {"ComorbidityAppendix", "Differential"}:
        controller.transition(session)

    if session.current_phase == "ClinicalSignificance":
        session.whodas_score = {
            "raw_total_0to48": 10,
            "metric_0to100": 20.8,
            "notes": "Synthetic public example only.",
        }
        session.clinical_significance = {
            "decision": True,
            "rationale": "Toy WHODAS score indicates observable impairment in the demo flow.",
        }
        controller.transition(session)

    return {
        "session": session,
        "event_count": len(bus.history),
        "last_phase": session.current_phase,
        "report": build_report_from_session(session),
    }


def run_replay_demo() -> dict[str, object]:
    transcript_path = Path(__file__).resolve().parent / "transcripts" / "synthetic_case.md"
    session = import_transcript_to_session(transcript_path)
    return {
        "session": session,
        "report": build_report_from_session(session),
    }


def main() -> None:
    configure_logging()

    controller_result = run_controller_demo()
    replay_result = run_replay_demo()

    controller_report = controller_result["report"]
    replay_report = replay_result["report"]

    print("=== Controller Walkthrough ===")
    print(f"Phase history: {controller_report['phase_history']}")
    print(f"Event count: {controller_result['event_count']}")
    print(json.dumps(controller_report["differential_result"], indent=2, ensure_ascii=False))

    print("\n=== Replay From Synthetic Transcript ===")
    print(f"Imported phase history: {replay_report['phase_history']}")
    print(f"Imported core modules: {[item['module'] for item in replay_report['core_modules']]}")
    print(json.dumps(replay_report["diagnostic_impression"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
