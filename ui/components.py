from __future__ import annotations

from typing import Any


def render_metric_strip(st: Any, metrics: dict[str, Any]) -> None:
    columns = st.columns(max(len(metrics), 1))
    for column, (label, value) in zip(columns, metrics.items(), strict=False):
        column.metric(label, value)


def render_source_cards(st: Any, source_cards: list[dict[str, Any]]) -> None:
    if not source_cards:
        st.write("No source metadata available.")
        return
    st.dataframe(source_cards, use_container_width=True, hide_index=True)


def render_trace_timeline(st: Any, timeline: list[dict[str, Any]]) -> None:
    if not timeline:
        st.write("No trace events yet.")
        return
    st.dataframe(timeline, use_container_width=True, hide_index=True)


def render_agent_pipeline(st: Any, pipeline: list[dict[str, Any]]) -> None:
    if not pipeline:
        st.write("No agent pipeline events yet.")
        return
    st.dataframe(pipeline, use_container_width=True, hide_index=True)


def render_tool_call_cards(st: Any, tool_calls: list[dict[str, Any]]) -> None:
    if not tool_calls:
        st.write("No tool calls yet.")
        return
    st.dataframe(tool_calls, use_container_width=True, hide_index=True)


def render_validator_gates(st: Any, gates: list[dict[str, Any]]) -> None:
    if not gates:
        st.write("No validator gates available.")
        return
    st.dataframe(gates, use_container_width=True, hide_index=True)


def render_artifact_panel(st: Any, artifacts: list[dict[str, Any]]) -> None:
    if not artifacts:
        st.write("No artifacts yet.")
        return
    st.dataframe(artifacts, use_container_width=True, hide_index=True)


def render_capability_catalog(st: Any, capabilities: list[dict[str, Any]]) -> None:
    st.dataframe(capabilities, use_container_width=True, hide_index=True)


def render_json_expander(st: Any, label: str, payload: Any, expanded: bool = False) -> None:
    with st.expander(label, expanded=expanded):
        st.json(payload, expanded=False)
