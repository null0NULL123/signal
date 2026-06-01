"""Preferences page - configure topics, view feedback, and recommendations."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from config import load_env
from storage.knowledge import KnowledgeStorage
import workspace as ws

st.set_page_config(page_title="我的偏好 - Sift", page_icon=":material/filter_list:")

DETAIL_LEVELS = ["精简（一句话）", "标准", "详细"]
LANGUAGES = ["中文", "英文", "双语"]


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


def load_preferences(storage: KnowledgeStorage) -> dict:
    raw = storage.get_preference("topics", "[]")
    topics = json.loads(raw) if raw else []
    return {
        "topics": topics,
        "detail_level": storage.get_preference("detail_level", "标准"),
        "language": storage.get_preference("language", "中文"),
        "saved": storage.get_preference("saved", "") == "true",
    }


def save_preferences(storage: KnowledgeStorage, prefs: dict):
    storage.set_preference("topics", json.dumps(prefs["topics"], ensure_ascii=False))
    storage.set_preference("detail_level", prefs["detail_level"])
    storage.set_preference("language", prefs["language"])
    storage.set_preference("saved", "true")


def render_topic_settings(storage: KnowledgeStorage, prefs: dict):
    """Render topic selection and preference settings."""
    st.subheader("关注领域")
    st.write("选择你感兴趣的话题（可多选）：")

    # Get candidate tags from database
    db_tags = storage.get_all_tags(limit=30)
    tag_names = [t["tag"] for t in db_tags]

    # Merge saved prefs that may not be in current DB
    all_tags = list(dict.fromkeys(prefs["topics"] + tag_names))

    if not all_tags:
        st.info("暂无话题数据。添加数据源并运行 pipeline 后，系统会自动提取话题供你选择。")
        return

    selected_topics = []
    cols = st.columns(3)
    for i, topic in enumerate(all_tags):
        with cols[i % 3]:
            count_str = ""
            for t in db_tags:
                if t["tag"] == topic:
                    count_str = f" ({t['count']})"
                    break
            if st.checkbox(f"{topic}{count_str}", value=topic in prefs["topics"], key=f"topic_{topic}"):
                selected_topics.append(topic)

    # Detail level
    st.subheader("摘要详细度")
    detail_level = st.radio(
        "选择摘要的详细程度：",
        DETAIL_LEVELS,
        index=DETAIL_LEVELS.index(prefs["detail_level"]) if prefs["detail_level"] in DETAIL_LEVELS else 1,
        horizontal=True,
    )

    # Language
    st.subheader("语言偏好")
    language = st.radio(
        "周报输出语言：",
        LANGUAGES,
        index=LANGUAGES.index(prefs["language"]) if prefs["language"] in LANGUAGES else 0,
        horizontal=True,
    )

    st.divider()

    if selected_topics:
        st.subheader("偏好预览")
        st.write(f"**关注领域**：{', '.join(selected_topics)}")
        st.write(f"**摘要详细度**：{detail_level}")
        st.write(f"**语言**：{language}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("保存偏好", type="primary", use_container_width=True):
            new_prefs = {
                "topics": selected_topics,
                "detail_level": detail_level,
                "language": language,
                "saved": True,
            }
            save_preferences(storage, new_prefs)
            st.success("偏好已保存")
            st.rerun()

    with col2:
        if st.button("清除偏好", use_container_width=True):
            storage.set_preference("saved", "false")
            storage.set_preference("topics", "[]")
            st.info("偏好已清除。")
            st.rerun()

    if prefs["saved"]:
        st.caption(f"当前已保存偏好：{', '.join(prefs['topics']) or '未选择'} | {prefs['detail_level']} | {prefs['language']}")


def render_feedback_stats(storage: KnowledgeStorage):
    """Render feedback statistics."""
    st.subheader("反馈统计")

    stats = storage.get_feedback_stats()
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("喜欢", stats.get("like", 0))
    with col2:
        st.metric("不喜欢", stats.get("dislike", 0))
    with col3:
        st.metric("收藏", stats.get("bookmark", 0))


def render_preference_analysis(storage: KnowledgeStorage):
    """Render preference analysis based on feedback."""
    st.subheader("偏好分析")

    # Liked sources
    liked_sources = storage.get_liked_sources(5)
    if liked_sources:
        st.write("**偏好来源**：")
        for s in liked_sources:
            st.write(f"- {s['source']}（{s['count']} 篇）")

    # Liked tags
    liked_tags = storage.get_liked_tags(10)
    if liked_tags:
        st.write("**偏好话题**：")
        tags_str = " ".join(f"`{t['tag']}`" for t in liked_tags[:10])
        st.write(tags_str)


def render_article_card_simple(article):
    """Render a simple article card without feedback buttons."""
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
        if article.summary:
            clean = re.sub(r"<[^>]+>", "", article.summary)
            st.write(clean[:200] + ("..." if len(clean) > 200 else ""))


def render_feedback_history(storage: KnowledgeStorage):
    """Render feedback history tabs."""
    st.subheader("反馈历史")

    tab1, tab2, tab3 = st.tabs(["喜欢", "收藏", "不喜欢"])

    with tab1:
        liked = storage.get_feedback_articles("like", limit=20)
        if liked:
            for article in liked:
                render_article_card_simple(article)
        else:
            st.info("还没有喜欢的文章。去文章浏览页面点赞吧！")

    with tab2:
        bookmarked = storage.get_feedback_articles("bookmark", limit=20)
        if bookmarked:
            for article in bookmarked:
                render_article_card_simple(article)
        else:
            st.info("还没有收藏的文章。去文章浏览页面收藏吧！")

    with tab3:
        disliked = storage.get_feedback_articles("dislike", limit=20)
        if disliked:
            for article in disliked:
                render_article_card_simple(article)
        else:
            st.info("还没有不喜欢的文章。")


def render_recommendations(storage: KnowledgeStorage):
    """Render smart recommendations based on feedback."""
    st.subheader("猜你喜欢")

    recommended = storage.get_recommended_articles(limit=10)
    if recommended:
        st.write("基于你喜欢和收藏的文章，为你推荐：")
        for article in recommended:
            render_article_card_simple(article)
    else:
        st.info("点赞或收藏一些文章后，系统会为你推荐相似内容。")


def main():
    init_session()
    render_workspace_selector()

    st.title("我的偏好")
    st.caption(f"工作区：{st.session_state.workspace}")

    storage = get_storage(st.session_state.workspace)
    prefs = load_preferences(storage)

    # Topic and preference settings
    render_topic_settings(storage, prefs)
    st.divider()

    # Feedback stats
    render_feedback_stats(storage)
    st.divider()

    # Preference analysis
    render_preference_analysis(storage)
    st.divider()

    # Feedback history
    render_feedback_history(storage)
    st.divider()

    # Recommendations
    render_recommendations(storage)


if __name__ == "__main__":
    main()
