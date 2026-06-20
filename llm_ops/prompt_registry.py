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
            description="Select allowlisted weekly business review sections without generating SQL.",
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
                "Metric context: {metric_context}\n"
                "Business context: {business_context}\n"
                "Current deterministic SQL: {current_deterministic_sql}\n"
                "Return JSON with sql_candidates only.\n"
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
            prompt_id="question_understanding",
            version="v1",
            description="Extract structured BI intent slots without generating SQL.",
            required_variables=["user_question"],
            safety_contract=[
                "must_not_generate_sql",
                "must_not_execute_sql",
                "must_not_select_matched_template",
                "must_preserve_sensitive_or_unsafe_risk_flags",
            ],
            template=(
                "Task: provider-backed question understanding.\n"
                "User question: {user_question}\n"
                "Return JSON only with strategy, intent, missing_slots, clarification_questions, risk_flags, and reason.\n"
                "Allowed strategy values: template, llm_candidate, clarify, reject.\n"
                "Intent schema: metric, dimension, and operation are strings or null; time_range is an object or null; "
                "filters is a string array; limit is an integer or null; risk_flags is a string array.\n"
                "Safety: do not generate SQL, do not execute SQL, do not select matched_template, "
                "and preserve sensitive_field, unsafe_operation, or bulk_export risk flags."
            ),
        ),
    ]
)
