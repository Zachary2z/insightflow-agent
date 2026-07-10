# Report and Analysis Layout Refinement Design

Date: 2026-07-10

Status: Approved for implementation

## Context

The 2026-07-10 decision-desk refresh established a consistent product shell, but two detailed result surfaces still carry older layout assumptions:

- Report detail mixes publish, export, download, post-publish links, counts, and warnings across the hero and opening-summary area.
- Analysis results nest a run container, a result container, and several panel cards, producing repeated borders and weak visual hierarchy.

This refinement applies the existing decision-desk visual language to those two surfaces without changing their data or service contracts.

## Goals

- Give report delivery actions a clear primary, secondary, and overflow hierarchy.
- Keep report metadata readable without competing with the report title or opening summary.
- Make the business conclusion the unmistakable first reading target in Analysis Workbench.
- Reduce repeated containers while preserving every chart, evidence, history, follow-up, progress, and technical-detail capability.
- Keep desktop and mobile layouts predictable, accessible, and consistent with the existing product shell.

## Non-Goals

- No backend, API, report schema, analysis result contract, or persistence changes.
- No change to report generation, Feishu publishing, Word export, Markdown download, history restoration, or same-thread follow-up behavior.
- No new dropdown library, design-system dependency, animation framework, or routing state.
- No merging of Analysis Workbench and Report Center.

## Report Detail Design

### Header structure

The report hero becomes a compact header with two regions:

1. Report identity: eyebrow, title, status, generated time, time range, and data sources.
2. Delivery actions: one primary action, one secondary action, and one native disclosure for less frequent actions.

The primary action is state-aware:

- Before a successful publish: `发布到飞书`.
- While publishing: disabled `发布中…`.
- After a successful or warning publish with a safe URL: `打开飞书文档` as an external link.
- After a failed publish or a publish result without a usable URL: return to `发布到飞书` so the user can retry.

`导出 Word` remains the secondary button. `下载 Markdown` and a safe `打开飞书表格` link live under a native `<details>` disclosure labeled `更多操作`. The disclosure avoids a new menu dependency and remains keyboard-operable.

### Delivery status

Feishu and Word outcomes render in a dedicated delivery-status region directly below the header, before the opening summary. It contains:

- A concise state title.
- Safe chart/table counts when present.
- A compact warning summary.
- Detailed warnings inside a collapsed disclosure when multiple warnings exist.
- A Word download link after export succeeds.

The status region never duplicates the primary `打开飞书文档` action. The safe Feishu Sheet link remains available only under `更多操作`.

### Responsive behavior

- Desktop: identity and action toolbar share the header row; the action toolbar stays aligned to the top-right.
- Tablet: actions wrap as a compact horizontal toolbar below the title metadata.
- Mobile: primary and secondary actions form two equal columns; `更多操作` spans the full width.
- Long source names wrap inside the metadata region and never expand the action toolbar.

## Analysis Result Design

### Run container

`AnalysisRunner` keeps the run heading and run id, but the outer `run-shell` becomes a structural section rather than another card. The result itself owns the visible surface.

The optional `查看本次分析详情` link moves into the run heading as a quiet text action so it does not appear as an unrelated button after the entire result.

### Decision summary

`BusinessAnswerCard` becomes a decision-summary surface with four reading levels:

1. Eyebrow, `业务结论`, and confidence.
2. The model-written headline as the primary thesis.
3. The direct answer as a concise lead paragraph.
4. Supporting content in a responsive grid.

Supporting content uses two columns on desktop and one column on mobile:

- `为什么` occupies the wider reasoning area.
- `关键证据` is a compact evidence list.
- `建议动作` and `限制说明` render only when their arrays are non-empty.

The component preserves the exact `business_answer` fields and does not rewrite, summarize, or recalculate model output.

### Result sections

The workbench result is divided into visually named groups:

- `结论与依据`: Business Answer, charts, and evidence.
- `继续追问与分析过程`: Analysis Thread, progress timeline, and technical details.

The second group uses a quieter background and separator treatment. Analysis Thread stays fully functional and visible so clarification and same-thread follow-up forms remain immediately usable. Progress and technical details preserve their current behavior, including default-collapsed technical content.

The result uses one outer surface with internal separators instead of a colored left rail plus several repeated bordered cards.

### Responsive behavior

- Desktop: reasoning and key evidence can form a two-column support grid.
- Mobile: every support block stacks; no action or status chip creates horizontal overflow.
- The run heading stacks cleanly with the run id and detail link.
- Existing chart and evidence table overflow handling remains unchanged.

## Visual Language

The refinement reuses the current decision-desk tokens:

- Canvas: `#eef3f1`.
- Surface: `#fbfcfb` / `#ffffff`.
- Ink: `#14231d`.
- Brand green: `#1e5d4c` / `#173f35`.
- Structural line: `#d7e0dc`.
- Decision blue is retained only for focus and secondary informational accents.

The distinctive element is a restrained editorial decision summary: the business headline uses the existing Songti display face, while operational controls and metadata use the PingFang body face. Decoration is limited to hierarchy, spacing, and separators.

## Accessibility

- All actions remain real buttons or links.
- The overflow control uses native `<details>` and `<summary>` keyboard behavior.
- External links keep `target="_blank"` with `rel="noreferrer"`.
- Publishing/exporting states stay disabled only while their request is active and use an ellipsis.
- Dynamic delivery outcomes use status or alert semantics as appropriate.
- Existing visible focus treatment and reduced-motion behavior remain in force.
- Heading hierarchy remains `h1` page title, `h2` report/run sections, then `h3`/`h4` internal subsections.

## Data Flow and Error Handling

- `ReportViewer` continues to call `publishFeishuReport()` and `exportWorkspaceReportDocx()` unchanged.
- Existing safe warning filtering stays in place.
- A publish error remains retryable and never exposes raw command output or internal paths.
- `RunResult` continues to validate `p16.v1` and passes the existing payload to the existing child components.
- Missing or malformed analysis results preserve the current product-safe error card.

## Test Strategy

Tests must be changed before implementation and must fail for the intended layout contracts.

- Report tests assert a single delivery toolbar, state-aware primary Feishu action, secondary Word action, and `更多操作` containing Markdown/Sheet links.
- Report tests assert successful publish does not duplicate `打开飞书文档` in the status region.
- Analysis tests assert the decision-summary class and named `结论与依据` / `继续追问与分析过程` groups.
- Analysis tests preserve content order and all existing follow-up, history, chart, evidence, and technical-detail assertions.
- Focused Vitest runs precede implementation; full Vitest, Next.js build, focused backend boundaries, `git diff --check`, and desktop/mobile browser QA close the work.

## Acceptance Criteria

- Report actions have one obvious primary action, one secondary action, and one overflow disclosure.
- Post-publish actions do not appear in multiple competing locations.
- The opening summary begins after a compact delivery-status region.
- Analysis results use one cohesive outer surface and a clearly dominant business conclusion.
- Follow-up, history restoration, charts, evidence, progress, technical details, publishing, Word export, and Markdown download still work.
- At 1280px and 390px, neither page has horizontal overflow.
