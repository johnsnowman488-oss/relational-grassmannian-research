# Research Operating Principles

These instructions govern the entire repository and all research stages, not only HLG-M3.

## Governing principle: objective-driven scientific progression

Research progression takes priority over unnecessary investigative completeness. The purpose of engineering, testing, and experimentation is to advance the agreed research objectives, not to become an independent obstacle to them.

1. **Objectives govern progress.** Define the objective, its acceptance criteria, and the evidence required before implementation or experimentation.
2. **Passing means progression.** When the agreed criteria are met, record acceptance and advance to the next objective. Do not add conditions retrospectively or reopen accepted work merely because further investigation is possible.
3. **Investigate demonstrated failures.** When an objective fails, investigate the specific failure and discuss the evidence and proposed remedy before making consequential changes. Do not initiate speculative investigations as a default prerequisite to progress.
4. **Do not require theoretical completeness.** A complete account of every underlying dynamic is not a prerequisite when the implemented model works against the agreed objective. Investigate mechanisms when needed to explain a failure, improve the model, or answer a necessary research question.
5. **Protect accepted foundations.** Reopen an accepted decision or foundational design only when compelling evidence shows a consequential flaw: invalid results, a broken assumption, a serious implementation limitation, or a failure that compromises a subsequent objective.
6. **Prefer the smallest effective correction.** When something fails, repair the failing implementation point first. Restructure code or framework foundations only when the failure demonstrates that a local correction is insufficient.
7. **Keep experiments purposeful.** Every experiment must serve an outstanding objective, resolve a demonstrated failure, or answer a research question necessary for the next decision. Do not create redundant experiments or repeat completed investigations without a specific reason.
8. **Preserve and use progress.** Carry forward accepted results, frozen protocols, validated components, and prior evidence. Do not duplicate completed work or silently discard established progress.
9. **Respect frozen criteria.** Do not change metrics, thresholds, splits, seeds, comparators, or claim boundaries after outcomes are visible. A necessary change requires an explicit reason, versioned decision, and appropriate new campaign.
10. **Report decisions plainly.** State what objective was attempted, what criteria were met, what was accepted, what failed, and what the next objective is. Distinguish implementation execution from the agreed research objective without allowing workflow labels to substitute for the objective's acceptance criteria.

## Execution discipline

- Read the relevant objective, accepted decision, and current implementation before changing code.
- Continue from the current repository state; do not restart or redesign work already completed.
- Use existing validated components and interfaces wherever they satisfy the objective.
- Run the smallest relevant tests for a local correction, then the required acceptance suite for the objective.
- A successful test or workflow is progress when it satisfies a predeclared implementation or research acceptance criterion. Do not dismiss it as merely procedural; equally, do not claim more than the criterion establishes.
- If the objective passes, record it and move forward. If it fails, investigate that failure rather than expanding the scope.
- Keep E-series and M-series evidence separate unless an accepted protocol explicitly connects them.

## Continuity for new contributors and agents

Before acting, inspect this file, `DECISIONS.md`, the relevant frozen protocol/acceptance record, and the latest implementation/results relevant to the active objective. Treat accepted decisions as authoritative unless a consequential flaw is demonstrated. Do not assume that a previous chat's unrecorded discussion overrides repository decisions; record newly accepted decisions here or in the appropriate decision document.

## Parallel implementation and CI execution

- Prefer parallel implementation of independent work packages when their interfaces and shared-file ownership are clear. For the active research objective, split work into genuinely independent components (for example learner representation, context/relation storage, control predictors, campaign integration, and evidence aggregation) and execute them concurrently where practical.
- Before parallelizing, define the shared contracts, input/output schemas, frozen protocol assumptions, and file ownership. Avoid concurrent edits to the same files; integrate through small, explicit interfaces.
- Do not serialize independent work merely for process convenience. Equally, do not parallelize tightly coupled changes before their contracts are agreed. Implement dependency foundations first, then launch dependent packages as soon as their required interfaces are stable.
- Run CI concurrently with implementation when it validates an unchanged or independently changing surface. Trigger focused tests/workflows for completed packages while other independent packages continue. Run the full required acceptance suite after integration.
- Where one CI workflow depends on another workflow's artifacts or outputs, preserve that dependency and wait for the upstream result; do not launch a downstream workflow with missing inputs. Where workflows are independent, run them concurrently.
- Reuse existing successful CI evidence when the relevant commit and inputs are unchanged. Do not rerun successful workflows without a code/input change or a specific acceptance requirement.
- Keep a concise dependency map and report which implementation packages and CI jobs ran in parallel, which required sequencing, and why.
- Parallelism must accelerate the agreed objective, not create redundant experiments, duplicate work, merge conflicts, or extra validation gates.
