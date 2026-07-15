from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "docs/product/plans/2026-07-15-p39-p44-enterprise-analysis-evolution.md"
TRACKER_PATH = ROOT / "docs/product/plans/2026-07-15-p39-p44-development-tracker.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_p39_p44_roadmap_documents_exist_and_define_the_program_contract():
    plan = _read(PLAN_PATH)
    tracker = _read(TRACKER_PATH)

    assert "Status: Planned; implementation has not started" in plan
    assert "Next planned task: P39-H1" in plan
    assert "## Target Product Chain" in plan
    assert "## Program-Wide Exit Criteria" in plan

    for phase in range(39, 45):
        assert f"## P{phase}:" in plan
        assert f"| P{phase} |" in tracker
        assert f"### P{phase} Task Status" in tracker

    for contract in (
        "ImportContract",
        "DataReadinessReport",
        "SemanticModel",
        "AnalysisSpec",
        "CapabilityGate",
        "ValidatedQuery",
        "EvidenceBundle",
    ):
        assert contract in plan


def test_p39_p44_roadmap_is_current_but_does_not_claim_unimplemented_work():
    readme = _read(ROOT / "README.md")
    development_plan = _read(ROOT / "DEVELOPMENT_PLAN.md")
    development_status = _read(ROOT / "DEVELOPMENT_STATUS.md")
    tracker = _read(TRACKER_PATH)

    for document in (readme, development_plan, development_status):
        assert str(PLAN_PATH.relative_to(ROOT)) in document
        assert str(TRACKER_PATH.relative_to(ROOT)) in document

    assert "P39-H1" in readme
    assert "P39-H1" in development_plan
    assert "| Current phase | P39 planned; implementation has not started |" in development_status
    assert "| Next planned task | P39-H1" in development_status

    for phase in range(39, 45):
        assert f"| P{phase} | `[ ]` Planned |" in development_status
        assert f"| P{phase} | `[ ]` Planned |" in tracker

    for phase in range(39, 45):
        phase_section = tracker.split(f"### P{phase} Task Status", 1)[1]
        if phase < 44:
            phase_section = phase_section.split(f"### P{phase + 1} Task Status", 1)[0]
        else:
            phase_section = phase_section.split("## Release Metrics", 1)[0]
        assert "`[x]` Complete" not in phase_section


def test_tracker_has_update_rules_risks_and_verification_surfaces():
    tracker = _read(TRACKER_PATH)

    for heading in (
        "## Status Legend",
        "## Phase Dependency Order",
        "## Capability Progression",
        "## Risk Register",
        "## Decision Log",
        "## Verification Ledger",
        "## Phase Closeout Template",
        "## Update Protocol",
    ):
        assert heading in tracker

    assert "Do not mark a task complete until its required verification has actually run" in tracker
    assert "P39-H1" in tracker
    assert "P44-H6" in tracker
