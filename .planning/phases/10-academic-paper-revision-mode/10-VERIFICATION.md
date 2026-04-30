# Verification: Phase 10 Academic Paper Revision Mode

## Goal-Backward Check

Phase 10 promised a real academic paper revision mode. The implementation now delivers a concrete flow from request input to persisted, inspectable stage results:

- `paper-revision` resolves through the normal preset and rule-template system.
- Academic context can be collected from journal guideline and reference paper URLs.
- The orchestration trace contains standards analysis, revision draft, style review, content review, revision iteration, and final re-review.
- The frontend exposes academic inputs and an Academic Context result tab.
- The Ark/Doubao model path is available through `OPENHANDS_MODE=model-api` and `ARK_API_KEY`.

## Validation Matrix

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Paper agents are instantiated | Pass | `SerialOrchestrationService` uses a six-stage paper flow |
| Journal/reference context is available | Pass | `AcademicContextService` and task metadata include summaries |
| Review-revise-re-review loop exists | Pass | stage order includes style/content review, iterate, and final re-review |
| Rule templates assign paper role models | Pass | `paper-revision-journal` maps paper roles to model IDs |
| Frontend can submit and inspect paper context | Pass | journal/reference fields and `academic` tab |
| Real model API path exists | Pass | `model-api` adapter posts OpenAI-compatible chat completions |

## Test Commands

```powershell
python -m pytest -q
cd frontend
npm run test
npm run build
cd ..
python -m compileall app
```

## Actual Results

- `python -m pytest -q`: 54 passed.
- `frontend npm run test`: 3 passed.
- `frontend npm run build`: passed.
- `python -m compileall app`: passed.
- Ark smoke test: `model-api:volces-ark` completed with `doubao-seed-2.0-lite`.

## Residual Risks

- Academic URL fetching is deliberately shallow and should not be treated as a full literature crawler.
- Journal pages with heavy JavaScript or paywalls may return limited excerpts.
- The live model API smoke test depends on a valid external API key and network access.
