"""Articles page - browse, search, and filter articles."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from config import load_env
from storage.knowledge import KnowledgeStorage
import workspace as ws

st.set_page_config(page_title="文章 - Sift", page_icon=":material/filter_list:")


def init_session():
    if "workspace" not in st.session_state:
        st.session_state.workspace = ws.DEFAULT_WORKSPACE


@st.cache_resource
def get_storage(workspace: str):
    load_env()
    db_path = ws.get_db_path(workspace)
    storage = KnowledgeStorage(db_path=db_path)
    storage.initialize()
    return storage


def render_workspace_selector():
    workspaces = ws.list_workspaces()
    with st.sidebar:
        st.header("工作区")
        current_idx = workspaces.index(st.session_state.workspace) if st.session_state.workspace in workspaces else 0
        selected = st.selectbox("选择工作区", workspaces, index=current_idx, label_visibility="collapsed")
        if selected != st.session_state.workspace:
            st.session_state.workspace = selected
            st.rerun()


def render_article_card(article, storage: KnowledgeStorage):
    with st.container(border=True):
        st.markdown(f"**[{article.title}]({article.link})**")
        meta_parts = []
        if article.source:
            meta_parts.append(article.source)
        if article.week:
            meta_parts.append(article.week)
        if article.published:
            meta_parts.append(article.published[:10])
        if meta_parts:
            st.caption(" | ".join(meta_parts))
        # Show LLM summary if available, otherwise show original summary
        summary_text = article.llm_summary or article.summary
        if summary_text:
            clean = re.sub(r"<[^>]+>", "", summary_text)
            st.write(clean[:300] + ("..." if len(clean) > 300 else ""))
        if article.llm_summary:
            st.caption("AI 摘要")
        if article.tags:
            st.write(" ".join(f"`{t}`" for t in article.tags))

        # Feedback buttons
        feedback_types = storage.get_article_feedback(article.id)
        col1, col2, col3, _ = st.columns([1, 1, 1, 5])

        with col1:
            like_active = "like" in feedback_types
            if st.button(
                "Like" if like_active else "Like",
                key=f"like_{article.id}",
                type="primary" if like_active else "secondary",
                use_container_width=True,
            ):
                storage.toggle_feedback(article.id, "like")
                st.rerun()

        with col2:
            dislike_active = "dislike" in feedback_types
            if st.button(
                "Dislike" if dislike_active else "Dislike",
                key=f"dislike_{article.id}",
                type="primary" if dislike_active else "secondary",
                use_container_width=True,
            ):
                storage.toggle_feedback(article.id, "dislike")
                st.rerun()

        with col3:
            bookmark_active = "bookmark" in feedback_types
            if st.button(
                "Save" if bookmark_active else "Save",
                key=f"bookmark_{article.id}",
                type="primary" if bookmark_active else "secondary",
                use_container_width=True,
            ):
                storage.toggle_feedback(article.id, "bookmark")
                st.rerun()


def main():
    init_session()
    render_workspace_selector()

    st.title("文章浏览")
    st.caption(f"工作区：{st.session_state.workspace}")

    storage = get_storage(st.session_state.workspace)

    # Sidebar filters
    with st.sidebar:
        st.divider()
        st.header("筛选")
        weeks = st.slider("回溯周数", 1, 24, 4)
        keyword = st.text_input("关键词搜索")

        st.divider()
        st.header("显示模式")
        view_mode = st.radio(
            "文章类型",
            ["全部", "精选"],
            index=0,
            label_visibility="collapsed",
        )

        st.divider()
        st.header("反馈筛选")
        feedback_filter = st.radio(
            "显示文章",
            ["全部", "喜欢", "不喜欢", "收藏"],
            index=0,
        )

    # Get articles based on filter
    if view_mode == "精选":
        articles = storage.get_selected_articles(weeks=weeks)
    elif feedback_filter == "全部":
        articles = storage.get_articles(weeks=weeks)
    elif feedback_filter == "喜欢":
        articles = storage.get_feedback_articles("like")
    elif feedback_filter == "不喜欢":
        articles = storage.get_feedback_articles("dislike")
    else:  # 收藏
        articles = storage.get_feedback_articles("bookmark")

    # Apply keyword filter
    if keyword:
        kw = keyword.lower()
        articles = [a for a in articles if kw in a.title.lower() or kw in (a.summary or "").lower()]

    # Stats
    st.caption(f"共 {len(articles)} 篇文章")

    if not articles:
        st.info("没有找到匹配的文章。试试扩大回溯周数或换个关键词。")
        return

    # Source filter
    sources = sorted({a.source for a in articles if a.source})
    if sources:
        selected_sources = st.multiselect("按来源筛选", sources, default=sources)
        articles = [a for a in articles if a.source in selected_sources]

    # Display
    for article in articles[:50]:
        render_article_card(article, storage)

    if len(articles) > 50:
        st.caption(f"仅显示前 50 篇，共 {len(articles)} 篇")


if __name__ == "__main__":
    main()
