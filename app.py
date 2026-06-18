APP_TITLE = "InsightFlow Agent"
APP_SUBTITLE = "P0 Agentic SQL Core"


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title=APP_TITLE, page_icon="IF", layout="wide")
    st.title(APP_TITLE)
    st.caption(APP_SUBTITLE)
    st.text_input(
        "业务问题",
        placeholder="最近 30 天销售额最高的 5 个商品是什么？",
        disabled=True,
    )
    st.button("运行", disabled=True)


if __name__ == "__main__":
    main()
