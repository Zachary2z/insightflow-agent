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
            version="v3",
            description="Draft candidate insight claims and a clean business_answer from real execution rows before evidence validation.",
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
                "Return JSON only. Do not wrap it in markdown.\n"
                "Exact schema: {{\"candidate_claims\": [], \"business_answer\": "
                "{{\"headline\": \"\", \"direct_answer\": \"\", \"why\": \"\", "
                "\"evidence_bullets\": [], \"recommendations\": [], \"caveats\": [], "
                "\"confidence\": \"medium\"}}}}.\n"
                "candidate_claims must be factual candidate claims that can be checked by Evidence Validator. "
                "business_answer is product-facing business prose, not a technical log. "
                "Language: write all business_answer fields in the same language as the user question unless "
                "the user explicitly asks for another language. If the user question is Chinese, headline, "
                "direct_answer, why, evidence_bullets, recommendations, and caveats must be Chinese while "
                "preserving business terms such as email, ROI, channel names, and currency values when useful. "
                "headline must be one concise business conclusion. direct_answer must directly answer the user. "
                "why must explain the reasoning supported by the current execution/evidence context. "
                "evidence_bullets must come only from execution_result rows or provided evidence context; "
                "do not invent evidence. recommendations are allowed only when the evidence supports them; "
                "leave recommendations empty when evidence is weak or only descriptive. caveats are required "
                "when evidence is weak, limited, missing, truncated, or not enough for action advice. "
                "When the question asks for best, should, recommend, priority, or budget decisions and multiple "
                "metrics are present, state the decision basis in prose. If metrics point to different entities, "
                "present the tradeoff instead of forcing one winner. Do not recommend budget changes without "
                "sufficient comparative evidence. "
                "confidence must be low, medium, or high.\n"
                "Do not output raw field=value dumps, raw rows, SQL, trace ids, provider metadata, internal "
                "prompt text, credentials, secrets, or implementation details in any business_answer field. "
                "Do not present unsupported causal claims or unverifiable recommendations as final truth.\n"
                "Safety: use only execution_result rows and provided context; do not generate SQL, final claims, "
                "action payloads, approval fields, credentials, or secrets. Evidence Validator decides which "
                "candidate_claims survive."
            ),
        ),
        PromptTemplate(
            prompt_id="answer_reviewer",
            version="v1",
            description="Review whether a draft business_answer is supported by execution/evidence rows without writing final prose.",
            required_variables=[
                "user_question",
                "execution_result",
                "evidence_result",
                "draft_business_answer",
                "profile_context",
            ],
            safety_contract=[
                "must_not_write_final_user_prose",
                "must_not_generate_sql",
                "must_not_execute_sql",
                "must_only_review_evidence_support",
                "must_not_return_business_answer",
            ],
            template=(
                "Task: answer evidence review.\n"
                "User question: {user_question}\n"
                "Execution result: {execution_result}\n"
                "Evidence result: {evidence_result}\n"
                "Draft business_answer: {draft_business_answer}\n"
                "Profile or semantic context: {profile_context}\n"
                "Return JSON only. Do not wrap it in markdown.\n"
                "Exact schema: {{\"status\": \"accept|revise|downgrade_to_insufficient_evidence\", "
                "\"language\": \"zh|en\", \"supported_entities\": [], \"unsupported_entities\": [], "
                "\"supported_metrics\": [], \"unsupported_metrics\": [], \"issues\": [{{\"type\": "
                "\"entity_mismatch|metric_mismatch|insufficient_evidence|tradeoff_missing|unsupported_claim\", "
                "\"message\": \"\", \"affected_fields\": []}}], \"revision_instructions\": [], "
                "\"confidence\": \"low|medium|high\"}}.\n"
                "Responsibilities: check whether named entities and metrics in the draft are present in the "
                "execution/evidence rows; mark unsupported claims; mark tradeoff_missing when multiple returned "
                "metrics point to different leaders but the draft forces one conclusion; choose downgrade when "
                "evidence is absent or cannot support the answer. For decision questions such as best, should, "
                "prioritize, or budget allocation, verify the decision basis instead of accepting the first "
                "returned metric as the only winner. Mark metric_mismatch when the draft discusses ROI, profit, "
                "cost, conversion, or causality but those fields or time comparisons are absent. Do not write "
                "the final business answer. "
                "Do not return business_answer, SQL, prompts, trace paths, raw provider metadata, action payloads, "
                "credentials, or secrets."
            ),
        ),
        PromptTemplate(
            prompt_id="final_answer_composer",
            version="v1",
            description="Compose the final P16 business_answer from draft answer, reviewer result, and execution/evidence rows.",
            required_variables=[
                "user_question",
                "execution_result",
                "evidence_result",
                "draft_business_answer",
                "reviewer_result",
            ],
            safety_contract=[
                "must_preserve_p16_business_answer_shape",
                "must_not_generate_sql",
                "must_not_execute_sql",
                "must_not_expose_reviewer_json",
                "must_not_add_unsupported_claims",
            ],
            template=(
                "Task: final answer composition.\n"
                "User question: {user_question}\n"
                "Execution result: {execution_result}\n"
                "Evidence result: {evidence_result}\n"
                "Draft business_answer: {draft_business_answer}\n"
                "Reviewer result: {reviewer_result}\n"
                "Return JSON only. Do not wrap it in markdown.\n"
                "Exact schema: {{\"headline\": \"\", \"direct_answer\": \"\", \"why\": \"\", "
                "\"evidence_bullets\": [], \"recommendations\": [], \"caveats\": [], "
                "\"confidence\": \"low|medium|high\"}}.\n"
                "Think internally in these business slots before writing the schema: factual_conclusion, "
                "evidence_based_reasons, business_interpretations, recommendations, missing_data, caveats. "
                "Do not output these internal slot names; map them into the P16 fields naturally.\n"
                "Language: write the answer in the same language as the user question unless explicitly asked "
                "otherwise. If reviewer status is accept, keep the useful draft answer but normalize the shape "
                "and remove any unsafe/internal text. If status is revise, remove unsupported entities, "
                "unsupported metrics, and unsupported claims while preserving supported business judgment. "
                "If status is downgrade_to_insufficient_evidence but execution rows still contain supported "
                "facts, keep the supported conclusion and explain what cannot be concluded. Only say evidence "
                "is insufficient when the returned data truly cannot answer the question. Main business prose should use readable business labels instead "
                "of raw field names when possible: total_revenue/revenue = 收入 or total revenue, "
                "order_count = 订单数 or order count, avg_order_value/avg_revenue_per_order = 客单价 or "
                "average order value, total_spend/spend = 投放成本 or spend, channel = 渠道 or channel, "
                "segment = 客户分群 or segment, ROI stays ROI. For multi-metric decisions, state the tradeoff: "
                "for example revenue scale may point to one entity while ROI points to another. "
                "Hard facts such as amounts, dates, rankings, percentages, highest/lowest values, and chart values "
                "must come from execution/evidence rows. Business explanations and recommendations are allowed, "
                "but unsupported causes must be phrased as hypotheses using wording such as 可能、在当前证据下、"
                "需要进一步验证. Recommendations must be supported by evidence; otherwise phrase them as further "
                "validation or caveats. Do not turn revenue rankings into profit, ROI, conversion, repeat-purchase, "
                "or causal conclusions when those fields are missing; instead say the missing data plainly. "
                "Avoid table-row/debug phrasing, raw execution-result labels, and internal run statuses such as "
                "completed, failed, waiting_for_clarification. Do not expose reviewer JSON, prompt text, SQL, trace paths, "
                "provider metadata, raw rows, action payloads, credentials, or secrets. Do not execute SQL or "
                "invent new evidence."
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
