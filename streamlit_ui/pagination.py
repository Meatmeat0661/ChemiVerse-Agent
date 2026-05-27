"""Streamlit 表格分页（每页固定行数）."""

from __future__ import annotations

import math

import streamlit as st


def reset_table_page(table_key: str) -> None:
    st.session_state[f"table_page__{table_key}"] = 1


def paginated_dataframe(
    rows: list[dict],
    *,
    table_key: str,
    page_size: int = 50,
    caption: str | None = None,
) -> None:
    """展示可翻页的数据表。table_key 需在页面内唯一（用于 session_state）。"""
    if not rows:
        st.info("无记录")
        return

    total = len(rows)
    total_pages = max(1, math.ceil(total / page_size))
    page_state_key = f"table_page__{table_key}"

    if page_state_key not in st.session_state:
        st.session_state[page_state_key] = 1
    st.session_state[page_state_key] = max(1, min(int(st.session_state[page_state_key]), total_pages))

    if caption:
        st.caption(caption)

    nav1, nav2, nav3 = st.columns([1, 3, 1])
    with nav1:
        if st.button("上一页", key=f"{table_key}_prev", disabled=st.session_state[page_state_key] <= 1):
            st.session_state[page_state_key] -= 1
            st.rerun()
    with nav2:
        st.number_input(
            "页码",
            min_value=1,
            max_value=total_pages,
            value=st.session_state[page_state_key],
            step=1,
            key=page_state_key,
            label_visibility="collapsed",
        )
        current_page = int(st.session_state[page_state_key])
        st.caption(f"共 {total} 行 · 第 {current_page}/{total_pages} 页（每页 {page_size} 行）")
    with nav3:
        if st.button(
            "下一页",
            key=f"{table_key}_next",
            disabled=st.session_state[page_state_key] >= total_pages,
        ):
            st.session_state[page_state_key] += 1
            st.rerun()

    current_page = int(st.session_state[page_state_key])
    start = (current_page - 1) * page_size
    end = start + page_size
    st.dataframe(rows[start:end], use_container_width=True)
