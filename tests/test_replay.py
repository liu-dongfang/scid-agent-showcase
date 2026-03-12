from __future__ import annotations

from pathlib import Path

from packages.schemas.export import render_schemas, validate_schema_payloads
from server.services.report_service import build_report_from_session
from server.services.transcript_importer import import_transcript_to_session


def test_schema_export_payloads_validate():
    schemas = render_schemas()
    validate_schema_payloads(schemas)
    assert "overview_evidence" in schemas
    assert "evaluator_decision" in schemas


def test_replay_import_builds_report():
    transcript_path = Path(__file__).resolve().parents[1] / "examples" / "transcripts" / "synthetic_case.md"
    session = import_transcript_to_session(transcript_path)
    report = build_report_from_session(session)

    assert report["overview"]
    assert report["screening_results"]
    assert any(module["module"] == "CORE_MODULE_ANXIETY" for module in report["core_modules"])
