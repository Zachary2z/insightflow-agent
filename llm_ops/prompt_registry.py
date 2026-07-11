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
        resolved_variables = {**_default_prompt_variables(), **variables}
        missing = [name for name in self.required_variables if name not in resolved_variables]
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

        rendered_variables = {name: _json_text(resolved_variables[name]) for name in self.required_variables}
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


def _default_prompt_variables() -> dict[str, Any]:
    return {
        "question_evidence_ledger": {},
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
            prompt_id="guarded_sql_candidate",
            version="v2",
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
                "For comparison, judgment, reason, recommendation, priority, budget, or optimization questions, "
                "return comparable candidate objects by default, usually LIMIT 3 or LIMIT 5. Do not use LIMIT 1 "
                "unless the user explicitly asks to return only the first item or only one row. Pure factual "
                "\"who is highest/lowest\" questions may use LIMIT 1, but \"why\", \"should\", \"recommend\", "
                "\"priority\", or \"budget\" questions need multi-row comparison evidence.\n"
                "Generate SQLite-compatible SQL only. For recent N-day windows, use SQLite date syntax such as "
                "date((SELECT MAX(order_date) FROM orders), '-90 days') or julianday(); "
                "Do not use INTERVAL, DATE_SUB, NOW(), CURRENT_DATE arithmetic, or non-SQLite date functions.\n"
                "Do not use WITH or CTE clauses; prefer a single SELECT with scalar subqueries over real "
                "workspace tables when you need a max date.\n"
                "Safety: never execute SQL, never bypass validate_sql, never access sensitive fields, "
                "and never use DML or DDL."
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
                "Return JSON only with strategy, intent, analysis_task, missing_slots, clarification_questions, risk_flags, and reason.\n"
                "Allowed strategy values: template, llm_candidate, clarify, reject.\n"
                "Language: this product is Chinese-first. Write reason and clarification_questions in Chinese, "
                "and set analysis_task.output_language to zh even when the user question or raw headers are English.\n"
                "Intent schema: metric, dimension, and operation are strings or null; time_range is an object or null; "
                "filters is a string array; limit is an integer or null; risk_flags is a string array.\n"
                "Analysis task schema: task_type is compare, rank, trend, summary, anomaly, recommendation, report, "
                "or clarification; dimensions and metrics are Chinese business-label string arrays; time_range is an "
                "object or null; filters, missing_slots, and defaults_applied are string arrays; decision_goal is a "
                "string or null; resolved_question is a concise Chinese resolved business question; output_language "
                "must be zh; confidence is low, medium, or high.\n"
                "If multiple metrics are requested, put them in metric as one comma-separated string, not an array. "
                "Requests that explicitly include a time window such as 最近 90 天, a dimension such as 渠道, "
                "and metrics or decision goals such as 收入, 投放成本, ROI, or 加预算 are complete enough for "
                "strategy=llm_candidate; do not ask the user to restate those slots.\n"
                "If Workspace context says a current workspace analysis database is selected, do not ask the user "
                "to specify a data source, table name, or field name before SQL planning.\n"
                "Do ask for clarification when the user asks a broad performance/status question such as "
                "'分析表现' or '看看情况' without an explicit metric, decision objective, or time range. "
                "A dimension like channel is not enough by itself; for '渠道表现' with no metric/time range, "
                "use strategy=clarify with missing_slots including metric and time_range. "
                "Do not infer ROI, budget recommendations, or a date window unless the user explicitly asks for them.\n"
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
                "Schema: requires_clarification is a boolean; missing_slots is a string array; "
                "clarification_questions is a string array; risk_flags is a string array; reason is a short string. "
                "Language: this product is Chinese-first. Write clarification_questions and reason in Chinese. "
                "Use requires_clarification=false with empty missing_slots and clarification_questions if the user "
                "question already supplies a time window, metric or decision objective, and analysis dimension.\n"
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
                "Language: write reason and clarification_questions in the same language as the user question. "
                "If the user question is Chinese, these product-facing strings must be Chinese.\n"
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
            prompt_id="business_answer",
            version="v5",
            description="Generate one guarded Analysis Workbench business_answer from the clean question evidence ledger.",
            required_variables=[
                "user_question",
                "question_evidence_ledger",
            ],
            safety_contract=[
                "must_only_use_question_evidence_ledger",
                "must_not_generate_sql",
                "must_not_execute_sql",
                "must_not_generate_final_claims",
                "must_not_create_action_payloads",
                "must_not_bypass_evidence_validator",
            ],
            template=(
                "Task: Analysis Workbench business answer generation.\n"
                "You are a Chinese business analysis assistant for InsightFlow Agent. "
                "User question: {user_question}\n"
                "Question evidence ledger: {question_evidence_ledger}\n"
                "Return JSON only. Do not wrap it in markdown.\n"
                "Exact schema: {{\"candidate_claims\": [], \"business_answer\": "
                "{{\"headline\": \"\", \"direct_answer\": \"\", \"why\": \"\", "
                "\"evidence_bullets\": [], \"recommendations\": [], \"caveats\": [], "
                "\"confidence\": \"medium\"}}}}.\n"
                "candidate_claims should be strings or objects with claim and category. "
                "Use category hard_fact for evidence numbers, rankings, dates, percentages, amounts, or counts; "
                "business_inference for interpretations; recommendation for suggested actions; "
                "data_limit for caveats about missing or limited evidence. "
                "business_answer is product-facing business prose, not a technical log or fixed section template. "
                "Language: write all business_answer fields in the same language as the user question unless "
                "the user explicitly asks for another language. If the user question is Chinese, headline, "
                "direct_answer, why, evidence_bullets, recommendations, and caveats must be Chinese while "
                "preserving business terms such as email, ROI, channel names, and currency values when useful. "
                "Write naturally, clearly, and directly: first answer the user's core question, then explain key "
                "evidence, then give suggestions and boundaries when useful. Do not output a fixed chapter layout "
                "or report-style section template. headline must be one concise business conclusion. "
                "direct_answer must directly answer the user. why must explain the reasoning supported by the "
                "clean grouped evidence ledger. Use only the Question evidence ledger evidence_groups and "
                "data_limits for hard facts, derived metrics, time policy, and data limits. "
                "For each hard fact, prefer the ledger fact_text, business_object, label, value, and unit fields; "
                "when answering ranking or best/worst questions, name the business object and include the key "
                "supported value instead of saying only 'ranked first' or 'ranked second'. "
                "evidence_bullets must come only from ledger facts/derived_metrics; "
                "do not invent evidence. recommendations are allowed only when the evidence supports them; "
                "leave recommendations empty when evidence is weak or only descriptive. caveats are required "
                "when evidence is weak, limited, missing, truncated, or not enough for action advice. "
                "If evidence is insufficient, explain what is missing instead of pretending the analysis is complete. "
                "Do not invent numbers outside the grouped ledger. "
                "When the question asks for best, should, recommend, priority, or budget decisions and multiple "
                "metrics are present, state the decision basis in prose. If metrics point to different entities, "
                "present the tradeoff instead of forcing one winner. Do not recommend budget changes without "
                "sufficient comparative evidence. "
                "confidence must be low, medium, or high.\n"
                "Do not output raw field=value dumps, raw rows, SQL, internal technical metadata, provider metadata, internal "
                "prompt text, credentials, secrets, or implementation details in any business_answer field. "
                "Do not present unsupported causal claims or unverifiable recommendations as final truth.\n"
                "Safety: use only the clean evidence ledger; do not generate SQL, final claims, "
                "action payloads, approval fields, credentials, or secrets. Evidence Validator decides which "
                "hard_fact candidate_claims survive."
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
                "explanation_basis, and optional unit, value_label, business_annotation. "
                "Allowed chart_type values: ranked_bar, line, grouped_bar, "
                "dual_axis_line, funnel, heatmap, scatter, risk_matrix.\n"
                "required_columns and explanation_basis must be arrays of strings, for example "
                "\"required_columns\": [\"product_name\", \"gmv\"] and "
                "\"explanation_basis\": [\"supported_findings\"].\n"
                "Allowed delivery_tool_id values: local_renderer, excel_exporter.\n"
                "Safety: reference only execution columns; select only a known delivery tool; do not generate "
                "SQL, final claims, final answers, action payloads, approval fields, credentials, secrets, "
                "fabricated rows, or fabricated metrics. The chart explanation basis must come from Evidence "
                "Validator outputs."
            ),
        ),
    ]
)
