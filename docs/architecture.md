# Architecture

This public repo keeps the engineering skeleton of the SCID research prototype while replacing the private study assets with synthetic configuration and toy transcripts.

## Component View

```mermaid
flowchart LR
    A["Synthetic workflow JSON"] --> B["WorkflowLoader"]
    C["Toy question manifests"] --> D["QuestionRepository"]
    E["JSON schema exports"] --> F["SchemaRegistry"]
    B --> G["FlowController"]
    D --> G
    F --> G
    G --> H["SessionState"]
    G --> I["EventBus"]
    I --> J["Structured logger"]
    K["Synthetic transcript replay"] --> L["TranscriptImporter"]
    L --> H
    H --> M["ReportService"]
```

## Interview Phase Skeleton

```mermaid
flowchart LR
    O["Overview"] --> S["Screening"]
    S --> C["CoreModules"]
    C --> X["ComorbidityAppendix"]
    X --> D["Differential"]
    D --> W["ClinicalSignificance"]
    W --> R["Reporting"]
```

## Public Design Choices

- The flow controller remains deterministic so interviewers can inspect phase progression and retry logic without hidden prompt behavior.
- Schema exports remain in the repo so the structured contracts are visible and testable.
- Replay is file-based and synthetic, which makes trace reconstruction inspectable without exposing real transcripts.
- The question manifests are intentionally small and synthetic; they illustrate orchestration shape, not the full unpublished research inventory.
