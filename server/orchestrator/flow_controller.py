from __future__ import annotations

import uuid
from typing import Any

"""Deterministic state machine orchestrating the SCID interview flow.

FlowController owns the workflow definition, keeps per-phase question caches,
and decides what agenda item should be asked next. It also tracks activation of
core modules, enforces follow-up limits, and emits structured events that the
rest of the system (SessionManager, UI, logging) can subscribe to.
"""

from packages.schemas import SchemaRegistry, register_default_schemas
from server.orchestrator.event_bus import EventBus
from server.orchestrator.events import Event
from server.orchestrator.session_state import AgendaItem, SessionState
from server.rules.differential import run_differential
from server.services.comorbidity import explore_comorbidity, load_comorbidity_config
from server.services.question_repository import QuestionItem, QuestionRepository
from server.services.workflow_loader import Workflow, WorkflowLoader
from server.utils.logger import get_logger

logger = get_logger(__name__)


class FlowController:
    """Deterministic state machine controlling the SCID interview phases."""

    MAX_FOLLOWUP_ATTEMPTS = 2
    MAX_SCHEMA_RETRIES = 5

    def __init__(
        self,
        workflow_loader: WorkflowLoader | None = None,
        question_repo: QuestionRepository | None = None,
        schema_registry: SchemaRegistry | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self.workflow_loader = workflow_loader or WorkflowLoader()
        self.workflow: Workflow = self.workflow_loader.load()
        self.questions = question_repo or QuestionRepository()
        self.schemas = schema_registry or SchemaRegistry()
        self.event_bus = event_bus or EventBus()

        config_base = self.workflow_loader.path.parent
        schemas_path = config_base / "schemas"
        if schemas_path.exists():
            self.schemas.load_from_directory(schemas_path)

        register_default_schemas(self.schemas)

        self._comorbidity_enabled = self.workflow.enable_comorbidity_appendix
        self._comorbidity_config: dict[str, Any] | None = None
        if self._comorbidity_enabled and self.workflow.comorbidity_config_path:
            try:
                self._comorbidity_config = load_comorbidity_config(self.workflow.comorbidity_config_path)
            except FileNotFoundError:
                logger.warning(
                    "comorbidity.config_missing",
                    path=str(self.workflow.comorbidity_config_path),
                )
                self._comorbidity_enabled = False

        self.phase_question_cache: dict[str, list[QuestionItem]] = {}
        self.module_question_cache: dict[str, list[QuestionItem]] = {}
        self._initialise_question_caches()

    def _initialise_question_caches(self) -> None:
        for phase in self.workflow.phases:
            phase_conf = self.workflow.phase(phase)
            if phase_conf.items_path and phase_conf.name != "CoreModules":
                self.phase_question_cache[phase_conf.name] = self.questions.questions_for_phase(
                    phase_conf.name
                )

        for manifest in self.workflow.phase("CoreModules").items_manifest:
            module = manifest["module"]
            self.module_question_cache[module] = self.questions.questions_for_module(module)

    def initialize_session(self) -> SessionState:
        """Create a new SessionState and prime it with the initial phase."""
        session = SessionState(session_id=str(uuid.uuid4()))
        session.current_phase = self.workflow.initial_phase
        logger.info("session.initialised", session_id=session.session_id, phase=session.current_phase)
        if session.current_phase:
            self.on_phase_enter(session, session.current_phase)
        return session

    def handle_event(self, session: SessionState, event: Event, payload: dict[str, Any]) -> None:
        """Central event dispatcher for schema violations, followups, risk, etc."""
        logger.info(
            "event.received",
            session_id=session.session_id,
            event_name=event.value,
            payload=payload,
        )

        context = {"session_id": session.session_id, **payload}

        if event == Event.MISSING_FIELD:
            item_id = payload.get("item_id")
            if item_id:
                attempts = session.increment_followup(item_id)
                context["attempts"] = attempts
                logger.warning(
                    "evidence.missing_field",
                    session_id=session.session_id,
                    item_id=item_id,
                    attempts=attempts,
                )
                if attempts > self.MAX_FOLLOWUP_ATTEMPTS:
                    self._handle_insufficient_evidence(
                        session,
                        item_id=item_id,
                        module=payload.get("module") or session.current_module,
                        reason="followup_exceeded",
                    )
                    return
            self.event_bus.publish(event, context)
            return

        if event == Event.SCHEMA_VIOLATION:
            item_id = payload.get("item_id")
            if item_id:
                retries = session.increment_schema_violation(item_id)
                context["retries"] = retries
                logger.warning(
                    "schema.violation",
                    session_id=session.session_id,
                    item_id=item_id,
                    retries=retries,
                )
                if retries > self.MAX_SCHEMA_RETRIES:
                    self._handle_insufficient_evidence(
                        session,
                        item_id=item_id,
                        module=payload.get("module") or session.current_module,
                        reason="schema_violation",
                    )
                    return
            self.event_bus.publish(event, context)
            return

        if event == Event.INVALID_RESPONSE:
            item_id = payload.get("item_id")
            if item_id:
                attempts = session.increment_invalid_response(item_id)
                context["attempts"] = attempts
                logger.warning(
                    "screening.invalid_response",
                    session_id=session.session_id,
                    item_id=item_id,
                    attempts=attempts,
                )
                if attempts > self.MAX_FOLLOWUP_ATTEMPTS:
                    self._handle_insufficient_evidence(
                        session,
                        item_id=item_id,
                        module=payload.get("module") or session.current_module,
                        reason="invalid_response",
                    )
                    return
            self.event_bus.publish(event, context)
            return

        if event == Event.INSUFFICIENT_EVIDENCE:
            self._handle_insufficient_evidence(
                session,
                item_id=payload.get("item_id"),
                module=payload.get("module") or session.current_module,
                reason=payload.get("reason", "external"),
            )
            if session.current_phase == "Differential":
                target_module = payload.get("module")
                if target_module:
                    if target_module not in session.activation_queue:
                        session.activation_queue.insert(0, target_module)
                session.current_phase = "CoreModules"
                session.current_module = None
                self.on_phase_enter(session, "CoreModules")
            return

        if event == Event.MODULE_DONE:
            self._complete_current_module(session)
            return

        if event == Event.PHASE_DONE:
            self.transition_to_next_phase(session)
            self.event_bus.publish(event, context)
            return

        if event == Event.RISK_ALERT:
            session.metadata["risk_alert"] = payload
            self._snapshot_risk_state(session)
            self.event_bus.publish(event, context)
            self.event_bus.publish(Event.RISK_HANDOFF_STARTED, context)
            return

        if event == Event.RISK_HANDOFF_STARTED:
            self.event_bus.publish(event, context)
            return

        if event == Event.RISK_HANDOFF_ACKED:
            if payload.get("operator"):
                session.metadata["handover_to"] = payload.get("operator")
            self.event_bus.publish(event, context)
            return

        if event == Event.RESUME_AFTER_RISK:
            self._restore_after_risk_state(session)
            session.metadata.pop("risk_alert", None)
            self.event_bus.publish(event, context)
            return

        if event in {Event.PHASE_ENTER, Event.PHASE_LEAVE}:
            self.event_bus.publish(event, context)
            return

        # default publish for unhandled events
        self.event_bus.publish(event, context)

    def get_current_agenda(self, session: SessionState) -> AgendaItem:
        """Return the AgendaItem describing what should be asked next."""
        if not session.current_phase:
            raise RuntimeError("Session has no active phase.")

        if session.current_phase == "ClinicalSignificance":
            context = {
                "phase": "ClinicalSignificance",
                "kind": "WHODAS_12_FORM",
                "items": list(range(1, 13)),
                "scale": [0, 1, 2, 3, 4],
                "recall_days": 30,
            }
            return AgendaItem(
                phase="ClinicalSignificance",
                module=None,
                item_id="WHODAS_2_0_12",
                item_type="instrument",
                schema_name="whodas_12_form",
                requires=[],
                anchors=[],
                followups={},
                context=context,
            )

        if session.current_phase == "CoreModules":
            return self._agenda_for_core_module(session)

        # Reporting phase marks the end of the interview
        if session.current_phase == "Reporting":
            logger.info("session.completed", session_id=session.session_id)
            self.event_bus.publish(Event.EXPORT_REPORT, {"session_id": session.session_id})
            session.current_phase = None
            raise RuntimeError("Session completed, no further agenda available.")

        items = self.phase_question_cache.get(session.current_phase, [])
        if not items:
            logger.info(
                "phase.skip_no_items",
                session_id=session.session_id,
                phase=session.current_phase,
            )
            self.transition_to_next_phase(session)
            if not session.current_phase:
                raise RuntimeError("Session completed, no further agenda available.")
            return self.get_current_agenda(session)

        index = min(session.current_item_index, len(items) - 1)
        question = items[index]
        context = self._build_context(session, question.item_id)
        return AgendaItem(
            phase=session.current_phase,
            module=question.module,
            item_id=question.item_id,
            item_type="anchor",
            schema_name=question.schema,
            requires=question.requires,
            anchors=question.anchors,
            followups=question.followups,
            context=context,
        )

    def _agenda_for_core_module(self, session: SessionState) -> AgendaItem:
        """Variant of get_current_agenda specialised for CoreModules traversal."""
        module = session.current_module or self._ensure_current_module(session)
        if not module:
            logger.info("core_modules.no_active_module", session_id=session.session_id)
            self.handle_event(session, Event.PHASE_DONE, {})
            if not session.current_phase:
                raise RuntimeError("Session has completed during CoreModules traversal.")
            return self.get_current_agenda(session)

        items = self.module_question_cache.get(module, [])
        if not items:
            logger.warning(
                "module.configuration_missing",
                session_id=session.session_id,
                module=module,
            )
            self._complete_current_module(session)
            if not session.activation_queue:
                self.handle_event(session, Event.PHASE_DONE, {})
                if not session.current_phase:
                    raise RuntimeError("Session has completed during CoreModules traversal.")
                return self.get_current_agenda(session)
            return self._agenda_for_core_module(session)

        index = min(session.current_item_index, len(items) - 1)
        question = items[index]
        context = self._build_context(session, question.item_id)

        return AgendaItem(
            phase="CoreModules",
            module=module,
            item_id=question.item_id,
            item_type="anchor",
            schema_name=question.schema,
            requires=question.requires,
            anchors=question.anchors,
            followups=question.followups,
            context=context,
        )

    def _ensure_current_module(self, session: SessionState) -> str | None:
        """Pick the next module from the activation queue if none is active."""
        if session.current_module:
            return session.current_module

        if not session.activation_queue:
            return None

        session.current_module = session.activation_queue[0]
        session.current_item_index = 0
        logger.info(
            "module.activated",
            session_id=session.session_id,
            module=session.current_module,
            queue=session.activation_queue,
        )
        return session.current_module

    def update_evidence(self, session: SessionState, agenda: AgendaItem, evidence: dict[str, Any]) -> None:
        """Persist validated evidence into the session ledger and reset retries."""
        key = agenda.module or agenda.phase
        phase_bucket = session.evidence_ledger.setdefault(key, {})
        phase_bucket[agenda.item_id] = evidence
        session.reset_followup(agenda.item_id)
        logger.info(
            "evidence.recorded",
            session_id=session.session_id,
            phase=agenda.phase,
            item_id=agenda.item_id,
            fields=list(evidence.keys()),
        )

        if session.current_phase == "Screening":
            self._update_activation_queue(session, agenda.item_id, evidence)

    def _update_activation_queue(self, session: SessionState, item_id: str, evidence: dict[str, Any]) -> None:
        """Map positive screening responses into modules that must be interviewed."""
        activation_map = self.questions.activation_targets_from_screening()
        module = activation_map.get(item_id)
        if not module:
            return

        if module not in self.module_question_cache:
            logger.warning(
                "module.activation_missing_config",
                session_id=session.session_id,
                module=module,
                reason=item_id,
            )
            return

        response = evidence.get("binary_response")
        # Normalize response to uppercase for robust matching
        if isinstance(response, str):
            response = response.upper().strip()
        logger.debug(
            "module.activation_check",
            session_id=session.session_id,
            item_id=item_id,
            module=module,
            response=response,
            already_queued=module in session.activation_queue,
        )
        if response in {"YES", "UNSURE"} and module not in session.activation_queue:
            session.activation_queue.append(module)
            logger.info(
                "module.queued",
                session_id=session.session_id,
                module=module,
                reason=item_id,
            )

    def check_item_complete(self, agenda: AgendaItem, evidence: dict[str, Any]) -> tuple[bool, list[str]]:
        missing = [field for field in agenda.requires if evidence.get(field) in (None, "", [])]
        return (len(missing) == 0, missing)

    def advance_item(self, session: SessionState) -> None:
        """Move the current item pointer forward within the active phase/module."""
        session.current_item_index += 1
        logger.info(
            "agenda.advance",
            session_id=session.session_id,
            phase=session.current_phase,
            index=session.current_item_index,
        )

    def check_phase_complete(self, session: SessionState) -> bool:
        """Evaluate whether the current phase has satisfied its completion rules."""
        if not session.current_phase:
            return False

        phase_conf = self.workflow.phase(session.current_phase)
        requirements = phase_conf.completion_requires

        if session.current_phase == "Screening":
            items = self.phase_question_cache.get("Screening", [])
            return session.current_item_index >= len(items)

        if session.current_phase == "Overview":
            collected = session.evidence_ledger.get("Overview", {})
            fields = {
                key
                for evidence in collected.values()
                for key, value in evidence.items()
                if value not in (None, "", [], {})
            }
            return all(requirement in fields for requirement in requirements)

        if session.current_phase == "CoreModules":
            return len(session.activation_queue) == 0 and session.current_module is None

        if session.current_phase == "ClinicalSignificance":
            return (session.whodas_score is not None) and (session.clinical_significance is not None)

        # Remaining phases (Differential, Reporting) are currently deterministic.
        return True

    def transition_to_next_phase(self, session: SessionState) -> None:
        """Advance to the next workflow phase and emit bookkeeping events."""
        if not session.current_phase:
            return

        current_phase = session.current_phase
        self.on_phase_leave(session, current_phase)

        next_phase = self._determine_next_phase(session, current_phase)

        if next_phase is None:
            logger.info("session.completed", session_id=session.session_id)
            if current_phase == "Reporting":
                self.event_bus.publish(Event.EXPORT_REPORT, {"session_id": session.session_id})
            session.current_phase = None
            return

        session.current_phase = next_phase
        session.current_item_index = 0
        session.current_module = None

        self.on_phase_enter(session, next_phase)

        logger.info(
            "phase.transition",
            session_id=session.session_id,
            from_phase=current_phase,
            to_phase=next_phase,
        )

    def _determine_next_phase(self, session: SessionState, current_phase: str) -> str | None:
        """Resolve the next phase, accounting for early exits and fallbacks."""
        phase_conf = self.workflow.phase(current_phase)

        if current_phase == "Overview":
            return phase_conf.next_phase

        if current_phase == "Screening":
            screening = session.evidence_ledger.get("Screening", {})
            any_positive = any(
                (evidence or {}).get("binary_response") in {"YES", "UNSURE"}
                for evidence in screening.values()
            )
            if not any_positive:
                return "Reporting"
            if session.activation_queue:
                return "CoreModules"
            logger.warning(
                "screening.no_modules_configured",
                session_id=session.session_id,
                activation_queue=session.activation_queue,
            )
            try:
                return self.workflow.phase("CoreModules").next_phase
            except KeyError:
                return phase_conf.next_phase

        if current_phase == "CoreModules":
            if session.activation_queue:
                return "CoreModules"
            return phase_conf.next_phase

        if current_phase == "ComorbidityAppendix":
            return phase_conf.next_phase

        if current_phase == "Differential":
            self._ensure_differential_result(session)
            result = session.differential_result or {}
            if not result.get("candidate_diagnoses"):
                logger.warning(
                    "differential.inconclusive",
                    session_id=session.session_id,
                )
            # Always proceed to ClinicalSignificance (WHODAS) regardless of differential result
            return phase_conf.next_phase

        if current_phase == "ClinicalSignificance":
            self._ensure_clinical_significance(session)
            return phase_conf.next_phase

        if current_phase == "Reporting":
            return None

        return phase_conf.next_phase

    def _complete_current_module(self, session: SessionState) -> None:
        """Pop the finished module from the activation queue and reset counters."""
        if session.current_module and session.activation_queue:
            finished_module = session.activation_queue.pop(0)
            logger.info(
                "module.completed",
                session_id=session.session_id,
                module=finished_module,
                remaining=session.activation_queue,
            )
            self.event_bus.publish(
                Event.MODULE_DONE,
                {
                    "session_id": session.session_id,
                    "module": finished_module,
                    "remaining": session.activation_queue,
                },
            )
        session.current_module = None
        session.current_item_index = 0

    def _build_context(self, session: SessionState, item_id: str) -> dict[str, Any]:
        """Assemble evidence/history snippets to feed into Interviewer prompts."""
        evidence_by_phase = session.evidence_ledger.get(session.current_phase or "", {})
        stored = evidence_by_phase.get(item_id) or {}
        pending = session.pending_evidence.get(item_id) or {}

        merged: dict[str, Any] = {}
        if stored:
            merged.update(stored)
        if pending:
            merged.update(pending)

        history = session.transcript[-10:]
        return {
            "evidence": merged or None,
            "history": history,
            "follow_up_attempts": session.follow_up_attempts.get(item_id, 0),
        }

    def on_phase_enter(self, session: SessionState, phase: str) -> None:
        """Record phase history and notify listeners when entering a new phase."""
        logger.info("phase.enter", session_id=session.session_id, phase=phase)
        session.phase_history.append(phase)
        self.event_bus.publish(
            Event.PHASE_ENTER, {"session_id": session.session_id, "phase": phase}
        )

    def on_phase_leave(self, session: SessionState, phase: str) -> None:
        """Emit phase leave events and run any phase-specific teardown hooks."""
        logger.info("phase.leave", session_id=session.session_id, phase=phase)
        self.event_bus.publish(
            Event.PHASE_LEAVE, {"session_id": session.session_id, "phase": phase}
        )
        if phase == "CoreModules":
            self._maybe_trigger_comorbidity(session)

    def _maybe_trigger_comorbidity(self, session: SessionState) -> None:
        """Run comorbidity exploration when the workflow enables the appendix."""
        if not self._comorbidity_enabled or not self._comorbidity_config:
            logger.info(
                "comorbidity.skip",
                session_id=session.session_id,
                reason="feature_disabled",
            )
            return
        result = explore_comorbidity(session, self._comorbidity_config)
        self.event_bus.publish(
            Event.COMORBIDITY_EXPLORE,
            {
                "session_id": session.session_id,
                "evidence": session.evidence_ledger,
                "result": result,
            },
        )

    def _handle_insufficient_evidence(
        self,
        session: SessionState,
        *,
        item_id: str | None,
        module: str | None,
        reason: str,
    ) -> None:
        """Mark items as pending/insufficient when retries are exhausted."""
        if not item_id:
            logger.warning(
                "insufficient_evidence.unknown_item",
                session_id=session.session_id,
                reason=reason,
            )
            return

        session.insufficient_evidence_items.add(item_id)
        session.reset_followup(item_id)
        session.pending_evidence.pop(item_id, None)
        key = module or session.current_module or session.current_phase or "unassigned"
        ledger = session.evidence_ledger.setdefault(key, {})
        ledger.setdefault(
            item_id,
            {
                "status": "insufficient",
                "reason": reason,
            },
        )
        session.metadata.setdefault("pending_items", []).append(
            {
                "module": key,
                "item_id": item_id,
                "reason": reason,
            }
        )
        logger.warning(
            "evidence.insufficient",
            session_id=session.session_id,
            item_id=item_id,
            module=module or session.current_module,
            reason=reason,
        )
        self.event_bus.publish(
            Event.INSUFFICIENT_EVIDENCE,
            {
                "session_id": session.session_id,
                "item_id": item_id,
                "module": module or session.current_module,
                "reason": reason,
            },
        )
        self.advance_item(session)

    def transition(self, session: SessionState) -> None:
        if self.check_phase_complete(session):
            self.handle_event(session, Event.PHASE_DONE, {})

    def _ensure_differential_result(self, session: SessionState) -> None:
        if session.differential_result:
            return
        session.differential_result = run_differential(session)

    def _ensure_clinical_significance(self, session: SessionState) -> None:
        if session.clinical_significance:
            return
        score = session.whodas_score or {}
        if not score:
            return
        raw_total = score.get("raw_total_0to48")
        metric = score.get("metric_0to100")
        if raw_total is None or metric is None:
            return
        decision = raw_total > 0
        rationale = (
            f"WHODAS 2.0（12 项）原始分 {raw_total}/48，标准化 {metric}/100。"
            if raw_total is not None and metric is not None
            else "待补充 WHODAS 评分结果。"
        )
        notes = score.get("notes")
        if notes:
            rationale = f"{rationale} 附注：{notes}"
        session.clinical_significance = {
            "decision": decision,
            "rationale": rationale,
        }

    def _snapshot_risk_state(self, session: SessionState) -> None:
        if session.risk_resume_snapshot:
            return
        session.risk_resume_snapshot = {
            "phase": session.current_phase,
            "module": session.current_module,
            "item_index": session.current_item_index,
            "activation_queue": list(session.activation_queue),
        }

    def _restore_after_risk_state(self, session: SessionState) -> None:
        snapshot = session.risk_resume_snapshot
        if not snapshot:
            return
        session.current_phase = snapshot.get("phase")
        session.current_module = snapshot.get("module")
        session.current_item_index = snapshot.get("item_index", 0)
        queued = snapshot.get("activation_queue")
        if isinstance(queued, list):
            session.activation_queue = list(queued)
        session.risk_resume_snapshot = None
