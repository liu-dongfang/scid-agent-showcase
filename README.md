# scid-agent-showcase

A public showcase of the orchestration layer behind a structured clinical interview research prototype, using only synthetic configuration and toy replay examples.

This repository is a public showcase version for research communication and engineering demonstration. It is not a clinical diagnostic tool or medical device.

## Project Overview

This is a research prototype / showcase repo derived from a larger private SCID project. The goal of this public version is to expose the engineering shape of the system without exposing the full research repository, real data, private prompts, or paper-specific experimental assets.

The code here focuses on deterministic interview flow control, schema-backed evidence collection, structured logging, and transcript replay. All included examples are synthetic.

## Start Here

If you're reviewing this repository for research or engineering collaboration, start with:

1. `docs/architecture.md` for the system layout and the rationale for the public subset
2. `examples/run_showcase.py` for the minimal executable showcase path
3. `docs/public_release_manifest.md` for what is included and intentionally excluded
4. `tests/` for lightweight behavior checks on the public subset

## System Architecture

![Architecture overview](assets/fig1.png)

The public subset centers on four pieces:

- `server/orchestrator/flow_controller.py`: deterministic phase and module progression
- `packages/schemas/`: Pydantic models, schema registry, and JSON schema export
- `server/utils/logger.py`: structured logging wrapper used across orchestration components
- `server/services/transcript_importer.py` and `server/services/report_service.py`: replay/import and compact report reconstruction

Architecture notes and diagram: [docs/architecture.md](docs/architecture.md)

## What I Was Responsible For

This showcase is structured around the parts I want interviewers to review:

- Workflow and state-machine design for phase transitions, module activation, and failure handling
- Schema design for structured extraction contracts and exportable JSON schemas
- Observability primitives, including event history, trace capture, and replay/report reconstruction
- Developer-facing examples and tests that make the orchestration behavior inspectable without private assets

## Public Scope

This public repository includes:

- Safe-to-share orchestration, controller, schema, logging, and replay code
- Synthetic workflow definitions and toy question manifests
- Example transcript replay assets
- Minimal packaging, environment templates, and architecture documentation

This public repository does not include:

- Real or sensitive data
- Private keys, tokens, or local environment files
- The full paper experiment set, evaluation resources, notebooks, or unpublished prompt assets
- Large logs, unreviewed outputs, or internal deployment leftovers

## Limitations

- This is not the full research repository.
- The workflow files are intentionally synthetic and much smaller than the private project.
- No clinical claims should be made from these examples.
- Replay examples are for engineering inspection only and do not represent real patient records.

## Collaboration

I am especially open to collaboration on:

- workflow orchestration for LLM agents
- schema-governed extraction and structured outputs
- replay and evaluation for long-horizon dialogue systems
- safe synthetic benchmarks for mental-health-related AI workflows

If you want to discuss research or engineering collaboration, please open an issue first. For small improvements to the public subset, see `CONTRIBUTING.md`.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python -m packages.schemas.export --check
pytest
python examples/run_showcase.py
```

Useful files:

- [config.example.yaml](config.example.yaml)
- [.env.example](.env.example)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [docs/public_release_manifest.md](docs/public_release_manifest.md)
- [assets/social-preview.png](assets/social-preview.png)

## Repository Tree

```text
packages/schemas/        Schema models, registry, and schema export
server/orchestrator/     Flow controller, events, session state
server/services/         Workflow loading, question repo, replay/report helpers
server/utils/            Logging utilities
configs/                 Synthetic workflow, toy questions, JSON schemas
examples/                Replay transcript and demo runner
docs/                    Architecture and public release notes
tests/                   Minimal behavior checks for the showcase subset
```
