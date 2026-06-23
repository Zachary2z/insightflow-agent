from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


def _json_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


@dataclass(frozen=True)
class PromptTemplate:
    prompt_id: str
    version: str
    description: str
    template: str
    required_variables: list[str]
    safety_contract: list[str]

    def render(self, variables: dict[str, Any]) -> dict[str, Any]:
        missing = [name for name in self.required_variables if name not in variables]
        if missing:
            return {
                "success": False,
                "prompt_id": self.prompt_id,
                "prompt_version": self.version,
                "prompt": "",
                "metadata": self.metadata(),
                "missing_variables": missing,
                "error": f"missing required variables: {', '.join(missing)}",
            }

        rendered_variables = {name: _json_text(variables[name]) for name in self.required_variables}
        return {
            "success": True,
            "prompt_id": self.prompt_id,
            "prompt_version": self.version,
            "prompt": self.template.format(**rendered_variables),
            "metadata": self.metadata(),
            "missing_variables": [],
            "error": "",
        }

    def metadata(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "required_variables": list(self.required_variables),
            "safety_contract": list(self.safety_contract),
        }


class PromptRegistry:
    def __init__(self, templates: list[PromptTemplate]):
        self._templates = {template.prompt_id: template for template in templates}

    def get(self, prompt_id: str) -> PromptTemplate | None:
        return self._templates.get(prompt_id)

    def list_prompts(self) -> dict[str, dict[str, Any]]:
        return {
            prompt_id: {
                "prompt_id": template.prompt_id,
                "prompt_version": template.version,
                **template.metadata(),
            }
            for prompt_id, template in sorted(self._templates.items())
        }

    def render(self, prompt_id: str, variables: dict[str, Any]) -> dict[str, Any]:
        template = self.get(prompt_id)
        if template is None:
            return {
                "success": False,
                "prompt_id": prompt_id,
                "prompt_version": "",
                "prompt": "",
                "metadata": {},
                "missing_variables": [],
                "error": f"unknown prompt_id: {prompt_id}",
            }
        return template.render(variables)


DEFAULT_PROMPT_REGISTRY = PromptRegistry(
    [
        PromptTemplate(
            prompt_id="report_planner",
            version="v1",
            description="Select allowlisted weekly or monthly business review sections without generating SQL.",
            required_variables=["user_question", "allowed_section_ids"],
            safety_contract=[
                "must_only_select_allowed_section_ids",
                "must_not_generate_sql",
                "must_not_execute_sql",
                "must_not_generate_final_claims",
            ],
            template=(
                "Task: controlled report planning.\n"
                "User question: {user_question}\n"
                "Allowed section ids: {allowed_section_ids}\n"
                "Return JSON with sections, requires_clarification, and clarification_questions.\n"
                "Schema: sections must be an array of objects shaped like "
                "{{\"section_id\": \"one allowed id\", \"rationale\": \"short reason\"}}; "
                "string lists are invalid.\n"
                "The section ids are stable template ids and may contain the word weekly even when the "
                "runtime report is monthly; do not ask whether the user wants weekly or monthly if the "
                "question already says 本周, 周报, 本月, 月报, 月度, monthly, or 最近 30 天.\n"
                "For monthly review requests, choose the relevant allowed ids and let the deterministic "
                "report supervisor adapt labels and SQL date windows.\n"
                "Safety: select only allowed section ids; do not generate SQL; do not execute SQL; "
                "do not generate final evidence-backed claims."
            ),
        ),
        PromptTemplate(
            prompt_id="guarded_sql_candidate",
            version="v1",
            description="Propose SQL candidates that still require validate_sql before execution.",
            required_variables=[
                "user_question",
                "schema_text",
                "workspace_context",
                "metric_context",
                "business_context",
                "current_deterministic_sql",
            ],
            safety_contract=[
                "must_not_execute_sql",
                "must_not_bypass_validate_sql",
                "must_not_access_sensitive_fields",
                "must_not_use_dml_or_ddl",
            ],
            template=(
                "Task: guarded SQL candidate generation.\n"
                "User question: {user_question}\n"
                "Schema: {schema_text}\n"
                "Workspace context: {workspace_context}\n"
                "Metric context: {metric_context}\n"
                "Business context: {business_context}\n"
                "Current deterministic SQL: {current_deterministic_sql}\n"
                "Return ONLY a JSON object with sql_candidates. Do not wrap it in markdown.\n"
                "Exact schema: {{\"sql_candidates\": [{{\"sql\": \"single SELECT statement\", "
                "\"rationale\": \"short reason grounded in schema and metric context\"}}]}}.\n"
                "sql_candidates must be an array of objects, not an array of strings. The SQL key must be sql.\n"
                "When the user asks for a dataset-relative recent window, use the latest available time value "
                "from Workspace context instead of DATE('now').\n"
                "Do not use WITH or CTE clauses; prefer a single SELECT with scalar subqueries over real "
                "workspace tables when you need a max date.\n"
                "Safety: never execute SQL, never bypass validate_sql, never access sensitive fields, "
                "and never use DML or DDL."
            ),
        ),
        PromptTemplate(
            prompt_id="guarded_insight_claims",
            version="v1",
            description="Suggest insight claims that Evidence Validator must verify before use.",
            required_variables=[
                "user_question",
                "execution_result",
                "business_context",
                "metric_context",
                "current_final_answer",
            ],
            safety_contract=[
                "must_not_bypass_evidence_validator",
                "must_not_add_unsupported_claims",
                "must_not_create_final_claims_without_data",
            ],
            template=(
                "Task: guarded insight claim suggestion.\n"
                "User question: {user_question}\n"
                "Execution result: {execution_result}\n"
                "Business context: {business_context}\n"
                "Metric context: {metric_context}\n"
                "Current deterministic answer: {current_final_answer}\n"
                "Return JSON with claims only.\n"
                "Safety: Evidence Validator must verify every claim before it can be used."
            ),
        ),
        PromptTemplate(
            prompt_id="report_writer",
            version="v1",
            description="Polish report prose only from verified evidence, SQL records, chart paths, and trace path.",
            required_variables=[
                "user_question",
                "verified_findings",
                "verified_hypotheses",
                "blocked_unsupported_claims",
                "sql_records",
                "chart_paths",
                "trace_path",
            ],
            safety_contract=[
                "must_not_add_unsupported_claims",
                "must_not_bypass_evidence_validator",
                "must_not_generate_sql",
                "must_not_execute_sql",
            ],
            template=(
                "Task: Evidence-backed report writing and polishing.\n"
                "User question: {user_question}\n"
                "Verified findings from Evidence Validator: {verified_findings}\n"
                "Verified hypotheses from Evidence Validator: {verified_hypotheses}\n"
                "Blocked unsupported claims that must not appear in prose: {blocked_unsupported_claims}\n"
                "SQL records for traceability, not for modification: {sql_records}\n"
                "Chart paths: {chart_paths}\n"
                "Trace path: {trace_path}\n"
                "Return JSON only with executive_summary, business_narrative, next_steps, "
                "used_supported_claims, used_hypotheses, and unsupported_claims.\n"
                "Schema: executive_summary and next_steps are string arrays; business_narrative is a string; "
                "used_supported_claims and used_hypotheses are string arrays copied from verified inputs; "
                "unsupported_claims must be an empty array.\n"
                "Safety: write clearer business prose only from verified findings and hypotheses; "
                "do not add unsupported claims; do not generate SQL; do not execute SQL; "
                "do not replace Evidence Validator."
            ),
        ),
        PromptTemplate(
            prompt_id="insight_claim_typer",
            version="v1",
            description="Classify candidate insight claims before Evidence Validator makes the final evidence decision.",
            required_variables=[
                "user_question",
                "candidate_claims",
                "execution_result",
                "business_context",
                "metric_context",
            ],
            safety_contract=[
                "must_not_generate_sql",
                "must_not_execute_sql",
                "must_not_bypass_evidence_validator",
                "must_not_create_final_claims_without_data",
            ],
            template=(
                "Task: guarded insight claim typing.\n"
                "User question: {user_question}\n"
                "Candidate claims: {candidate_claims}\n"
                "Execution result: {execution_result}\n"
                "Business context: {business_context}\n"
                "Metric context: {metric_context}\n"
                "Return JSON only with typed_claims and risk_flags.\n"
                "Schema: typed_claims is an array of objects with claim, claim_type, and rationale. "
                "Allowed claim_type values: data_supported_finding, hypothesis, unsupported. "
                "risk_flags is a string array.\n"
                "Safety: classify claims only; do not generate SQL; do not execute SQL; "
                "do not bypass Evidence Validator. Evidence Validator still decides which claims can be used."
            ),
        ),
        PromptTemplate(
            prompt_id="action_drafter",
            version="v1",
            description="Draft approval-gated task, metric alert, and email draft payloads from evidence-backed findings.",
            required_variables=[
                "user_question",
                "evidence_findings",
                "evidence_hypotheses",
                "blocked_unsupported_claims",
                "existing_actions",
            ],
            safety_contract=[
                "must_not_execute_actions",
                "must_not_bypass_approval_gate",
                "must_not_send_email",
                "must_not_use_unsupported_claims",
            ],
            template=(
                "Task: provider-backed action and email drafting.\n"
                "User question: {user_question}\n"
                "Evidence-backed findings: {evidence_findings}\n"
                "Evidence-backed hypotheses: {evidence_hypotheses}\n"
                "Blocked unsupported claims that must not appear: {blocked_unsupported_claims}\n"
                "Existing caller-supplied actions, if any: {existing_actions}\n"
                "Return JSON only with actions and risk_flags.\n"
                "Allowed action_type values: create_task, create_metric_alert, create_email_draft.\n"
                "Allowed delivery_tool_id values: local_sqlite, jira_ticket_mock.\n"
                "For create_task include action_id, action_type, title, description, owner, priority, delivery_tool_id, and source_claims.\n"
                "For create_metric_alert include action_id, action_type, metric_name, condition, threshold, description, delivery_tool_id, and source_claims.\n"
                "For create_email_draft include action_id, action_type, recipient, subject, body, delivery_tool_id, and source_claims.\n"
                "Safety: draft only from evidence-backed findings or hypotheses; do not execute actions; "
                "do not bypass approval gate; do not set approval_status, requires_approval, status, record ids, "
                "or audit fields; do not send email; do not use blocked unsupported claims."
            ),
        ),
        PromptTemplate(
            prompt_id="question_understanding",
            version="v1",
            description="Extract structured BI intent slots without generating SQL.",
            required_variables=["user_question", "workspace_context"],
            safety_contract=[
                "must_not_generate_sql",
                "must_not_execute_sql",
                "must_not_select_matched_template",
                "must_preserve_sensitive_or_unsafe_risk_flags",
            ],
            template=(
                "Task: provider-backed question understanding.\n"
                "User question: {user_question}\n"
                "Workspace context: {workspace_context}\n"
                "Return JSON only with strategy, intent, missing_slots, clarification_questions, risk_flags, and reason.\n"
                "Allowed strategy values: template, llm_candidate, clarify, reject.\n"
                "Intent schema: metric, dimension, and operation are strings or null; time_range is an object or null; "
                "filters is a string array; limit is an integer or null; risk_flags is a string array.\n"
                "If Workspace context says a current workspace analysis database is selected, do not ask the user "
                "to specify a data source, table name, or field name before SQL planning.\n"
                "Safety: do not generate SQL, do not execute SQL, do not select matched_template, "
                "and preserve sensitive_field, unsafe_operation, or bulk_export risk flags. "
                "A request for chart/report/export/draft delivery from already analyzed results is not unsafe_operation; "
                "mark unsafe_operation only for data mutation, credential access, approval bypass, "
                "or sending externally without approval."
            ),
        ),
        PromptTemplate(
            prompt_id="clarification_router",
            version="v1",
            description="Generate focused clarification questions for missing BI intent slots without guessing requirements.",
            required_variables=["user_question", "missing_slots", "current_intent", "deterministic_questions"],
            safety_contract=[
                "must_not_generate_sql",
                "must_not_execute_sql",
                "must_not_guess_missing_requirements",
                "must_not_bypass_reject_strategy",
            ],
            template=(
                "Task: provider-backed clarification routing.\n"
                "User question: {user_question}\n"
                "Missing slots: {missing_slots}\n"
                "Current intent: {current_intent}\n"
                "Deterministic clarification questions: {deterministic_questions}\n"
                "Return JSON only with requires_clarification, missing_slots, clarification_questions, risk_flags, and reason.\n"
                "Schema: requires_clarification is true; missing_slots is a string array; "
                "clarification_questions is a string array; risk_flags is a string array; reason is a short string.\n"
                "Safety: do not generate SQL, do not execute SQL, do not guess missing requirements, "
                "and do not override sensitive or unsafe rejection."
            ),
        ),
        PromptTemplate(
            prompt_id="sql_planning_router",
            version="v1",
            description="Choose SQL source strategy without returning executable SQL.",
            required_variables=["user_question", "question_understanding", "deterministic_plan"],
            safety_contract=[
                "must_not_generate_sql",
                "must_not_execute_sql",
                "must_not_bypass_validate_sql",
                "must_not_invent_template_ids",
            ],
            template=(
                "Task: provider-assisted SQL planning.\n"
                "User question: {user_question}\n"
                "Question understanding: {question_understanding}\n"
                "Deterministic SQL plan: {deterministic_plan}\n"
                "Return JSON only with strategy, matched_template, confidence, missing_slots, "
                "clarification_questions, risk_flags, and reason.\n"
                "Allowed strategy values: template, llm_candidate, clarify, reject.\n"
                "Allowed matched_template values: empty string, top_products_gmv, top_categories_gmv, "
                "city_gmv_summary, city_order_count_summary.\n"
                "Use the deterministic SQL plan as the default. Keep llm_candidate for complete non-template "
                "intents; use template only for an allowed matched_template; use clarify or reject only when "
                "required by missing slots or safety risks.\n"
                "Safety: do not generate SQL, do not return sql_candidates, do not execute SQL, "
                "and do not bypass validate_sql."
            ),
        ),
        PromptTemplate(
            prompt_id="analysis_planner",
            version="v1",
            description="Decompose realistic BI scenarios into semantic analysis steps without SQL or final claims.",
            required_variables=[
                "user_question",
                "semantic_context",
                "deterministic_plan",
                "supported_scenario_types",
            ],
            safety_contract=[
                "must_not_generate_sql",
                "must_not_execute_sql",
                "must_not_generate_final_claims",
                "must_not_create_action_payloads",
                "must_use_semantic_metrics_dimensions_and_tables",
            ],
            template=(
                "Task: scenario analysis planning.\n"
                "User question: {user_question}\n"
                "Semantic context: {semantic_context}\n"
                "Deterministic fallback plan: {deterministic_plan}\n"
                "Supported scenario types: {supported_scenario_types}\n"
                "Return JSON only with scenario_type and analysis_steps.\n"
                "Schema: scenario_type must be one supported scenario type. analysis_steps must be an array "
                "of objects with step_id, question, required_metrics, required_dimensions, and candidate_tables. "
                "Use semantic layer metric ids, dimension ids, and table names only.\n"
                "Safety: do not generate SQL, sql_candidates, final claims, final answers, action payloads, "
                "approval fields, or execution instructions. Planning describes what to analyze before the "
                "existing Schema Agent, Metric Agent, SQL Reviewer, validate_sql, run_sql, and Evidence Validator."
            ),
        ),
        PromptTemplate(
            prompt_id="insight_drafter",
            version="v1",
            description="Draft candidate insight claims and concise prose from real execution rows before evidence validation.",
            required_variables=[
                "user_question",
                "execution_result",
                "business_context",
                "metric_context",
            ],
            safety_contract=[
                "must_only_use_execution_result_rows",
                "must_not_generate_sql",
                "must_not_execute_sql",
                "must_not_generate_final_claims",
                "must_not_create_action_payloads",
                "must_not_bypass_evidence_validator",
            ],
            template=(
                "Task: insight drafting.\n"
                "User question: {user_question}\n"
                "Execution result: {execution_result}\n"
                "Business context: {business_context}\n"
                "Metric context: {metric_context}\n"
                "Return JSON only with candidate_claims and draft_summary.\n"
                "candidate_claims must be factual candidate claims that can be checked by Evidence Validator. "
                "draft_summary is concise prose and must not present unsupported causes as final truth.\n"
                "Safety: use only execution_result rows and provided context; do not generate SQL, final claims, "
                "final answers, action payloads, approval fields, credentials, or secrets. Evidence Validator "
                "decides which candidate claims survive."
            ),
        ),
        PromptTemplate(
            prompt_id="visualization_agent",
            version="v1",
            description="Choose a validated chart spec and visualization delivery tool from real execution evidence.",
            required_variables=[
                "user_question",
                "analysis_steps",
                "execution_columns",
                "execution_sample_rows",
                "evidence_result",
                "delivery_tool_catalog",
            ],
            safety_contract=[
                "must_only_reference_execution_columns",
                "must_select_known_delivery_tool",
                "must_not_generate_sql",
                "must_not_execute_sql",
                "must_not_generate_final_claims",
                "must_not_create_action_payloads",
                "must_not_return_credentials_or_secrets",
                "must_not_fabricate_rows_or_metrics",
                "must_not_bypass_evidence_validator",
            ],
            template=(
                "Task: visualization agent decision.\n"
                "User question: {user_question}\n"
                "Analysis steps: {analysis_steps}\n"
                "Execution columns: {execution_columns}\n"
                "Execution sample rows: {execution_sample_rows}\n"
                "Evidence Validator result: {evidence_result}\n"
                "Delivery tool catalog: {delivery_tool_catalog}\n"
                "Return JSON only with chart_spec, delivery_tool_id, and tool_reason.\n"
                "chart_spec schema: chart_type, title, x, y, y_secondary, series, required_columns, "
                "and explanation_basis. Allowed chart_type values: ranked_bar, line, grouped_bar, "
                "dual_axis_line, funnel, heatmap, scatter, risk_matrix.\n"
                "required_columns and explanation_basis must be arrays of strings, for example "
                "\"required_columns\": [\"product_name\", \"gmv\"] and "
                "\"explanation_basis\": [\"supported_findings\"].\n"
                "Allowed delivery_tool_id values: local_renderer, excel_exporter, powerbi_publisher_mock.\n"
                "Safety: reference only execution columns; select only a known delivery tool; do not generate "
                "SQL, final claims, final answers, action payloads, approval fields, credentials, secrets, "
                "fabricated rows, or fabricated metrics. The chart explanation basis must come from Evidence "
                "Validator outputs."
            ),
        ),
    ]
)
