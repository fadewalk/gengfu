# Super Dev Claude Code Integration

This project uses a pipeline-driven development model.

## Positioning
- Super Dev does not own a model endpoint.
- Claude Code remains the execution host for coding capability.
- Super Dev provides governance: protocol, gates, and audit artifacts.

## Runtime Contract
- Treat Super Dev as the local Python workflow tool plus Claude Code command/rule integration.
- When the user triggers `/super-dev`, `super-dev:`, or `super-dev：`, enter the Super Dev pipeline immediately rather than handling it like casual chat.
- Use Claude Code browse/search for research and Claude Code terminal/editing for implementation.
- Use local `super-dev` commands whenever you need to generate/update docs, spec artifacts, quality reports, and delivery outputs.

## First-Response Contract
- On the first reply after `/super-dev ...`, `super-dev: ...`, or `super-dev：...`, explicitly state that Super Dev pipeline mode is now active rather than normal chat mode.
- Before the first reply, read `.super-dev/WORKFLOW.md` and `output/*-bootstrap.md` when present, and treat them as the explicit bootstrap contract for this repository.
- The first reply must explicitly state that the current phase is `research`, and that you will read `knowledge/` plus `output/knowledge-cache/*-knowledge-bundle.json` first when available before similar-product research.
- The first reply must explicitly state the next sequence: research -> three core documents -> wait for user confirmation -> Spec / tasks -> frontend first with runtime verification -> backend / tests / delivery.
- The first reply must explicitly promise that you will stop after the three core documents and wait for approval before creating Spec or writing code.

## Local Knowledge Contract
- Read relevant files under `knowledge/` before drafting PRD, architecture, and UIUX.
- If `output/knowledge-cache/*-knowledge-bundle.json` exists, read it first and inherit its local knowledge hits into later stages.
- Treat matched local standards, scenario packs, and checklists as hard constraints, not optional hints.

## Before coding
1. If Claude Code browse/search is available, research similar products first and write output/*-research.md as a real repository file
2. Read output/*-prd.md
3. Read output/*-architecture.md
4. Read output/*-uiux.md
5. Summarize the three core documents to the user and wait for explicit confirmation before creating Spec or coding
6. Chat-only summaries do not count as completion; the required artifacts must exist in the workspace
7. Read output/*-execution-plan.md
8. Follow .super-dev/changes/*/tasks.md after confirmation, with frontend-first implementation and runtime verification

9. If the user requests a UI redesign or says the UI is unsatisfactory, first update `output/*-uiux.md`, then redo the frontend, and rerun frontend runtime + UI review before continuing.

## Output Quality
- Keep security/performance constraints from red-team report.
- Ensure quality gate threshold is met before merge.
- UI must follow output/*-uiux.md and avoid AI-looking templates (purple gradient, emoji icons, default-font-only).
- UI implementation must define typography system, tokens, page hierarchy and component states before polishing visuals.
- Prioritize real screenshots, trust modules, proof points and task flows over decorative hero sections.

## Super Dev System Flow Contract
- SUPER_DEV_FLOW_CONTRACT_V1
- PHASE_CHAIN: research>docs>docs_confirm>spec>frontend>preview_confirm>backend>quality>delivery
- DOC_CONFIRM_GATE: required
- PREVIEW_CONFIRM_GATE: required
- HOST_PARITY: required
