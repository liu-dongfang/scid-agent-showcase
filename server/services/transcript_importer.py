"""Utilities for importing saved transcript files to reconstruct session data."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from server.orchestrator.session_state import SessionState
from server.utils.logger import get_logger

logger = get_logger(__name__)


def parse_transcript_file(file_path: str | Path) -> dict[str, Any]:
    """
    Parse a transcript markdown file and extract structured data.

    Returns a dict with:
    - session_id: generated or extracted
    - evidence_ledger: dict from JSON block
    - transcript: list of messages
    - metadata: any additional info
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Transcript file not found: {file_path}")

    content = path.read_text(encoding="utf-8")

    # Extract the JSON evidence block
    json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
    if not json_match:
        raise ValueError("No JSON evidence block found in transcript file")

    try:
        evidence_ledger = json.loads(json_match.group(1))
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse evidence JSON: {e}")

    # Extract transcript messages
    transcript = []
    # Find all messages in order
    for match in re.finditer(
        r"(\*\*(?:🔵 Doctor|Assistant):\*\* \*\*(.+?)\*\*|\*\*(?:👤 Patient|Participant):\*\* (.+?)(?=\n\n|\n\*\*|$))",
        content,
        re.DOTALL,
    ):
        full_match = match.group(0)
        if "Doctor:" in full_match or "Assistant:" in full_match:
            msg_content = match.group(2)
            transcript.append({"role": "assistant", "content": msg_content.strip()})
        elif "Patient:" in full_match or "Participant:" in full_match:
            msg_content = match.group(3)
            transcript.append({"role": "user", "content": msg_content.strip()})

    # Extract date from header if present
    date_match = re.search(r"\*\*Date:\*\* (\d{4}-\d{2}-\d{2})", content)
    created_at = datetime.fromisoformat(date_match.group(1)) if date_match else datetime.utcnow()

    # Extract case info
    case_match = re.search(r"# (?:SCID Human Evaluation|SCID Showcase Transcript) - (.+)", content)
    case_name = case_match.group(1) if case_match else "Imported Session"

    return {
        "session_id": str(uuid4()),
        "evidence_ledger": evidence_ledger,
        "transcript": transcript,
        "created_at": created_at,
        "metadata": {
            "source_file": str(path.name),
            "case_name": case_name,
            "imported": True,
        },
    }


def import_transcript_to_session(file_path: str | Path) -> SessionState:
    """
    Import a transcript file and create a SessionState object.

    This allows viewing the report for previously completed interviews.
    """
    data = parse_transcript_file(file_path)

    session = SessionState(
        session_id=data["session_id"],
        created_at=data["created_at"],
    )

    # Populate evidence ledger
    session.evidence_ledger = data["evidence_ledger"]

    # Set transcript
    for msg in data["transcript"]:
        session.transcript.append({
            "role": msg["role"],
            "content": msg["content"],
            "timestamp": data["created_at"].isoformat(),
        })

    # Set metadata
    session.metadata.update(data["metadata"])

    # Determine completed phases from evidence
    phase_history = []
    if "Overview" in session.evidence_ledger:
        phase_history.append("Overview")
    if "Screening" in session.evidence_ledger:
        phase_history.append("Screening")
    # Check for any CORE_MODULE_ keys
    core_modules = [k for k in session.evidence_ledger.keys() if k.startswith("CORE_MODULE_")]
    if core_modules:
        phase_history.append("CoreModules")

    session.phase_history = phase_history

    # Mark as completed if we have core modules
    if core_modules:
        session.current_phase = None  # Mark as completed

    logger.info(
        "transcript.imported",
        session_id=session.session_id,
        phases=phase_history,
        evidence_keys=list(session.evidence_ledger.keys()),
    )

    return session
