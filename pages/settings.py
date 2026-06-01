"""Settings page - edit .env configuration and feeds."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from config import DEFAULT_ENV_PATH
import workspace as ws

st.set_page_config(page_title="设置 - Sift", page_icon=":material/settings:")


def load_env_file() -> dict[str, str]:
    """Load .env file into a dict."""
    env_path = Path(DEFAULT_ENV_PATH)
    if not env_path.exists():
        return {}

    result = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip()
    return result


def save_env_file(env: dict[str, str]) -> None:
    """Save dict back to .env file, preserving comments and order."""
    env_path = Path(DEFAULT_ENV_PATH)
    if not env_path.exists():
        # Create new file
        lines = [f"{k}={v}" for k, v in env.items()]
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    # Read existing file to preserve structure
    original = env_path.read_text(encoding="utf-8")
    lines = original.splitlines()
    new_lines = []
    written_keys: set[str] = set()

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue

        if "=" in stripped:
            key, _, _ = stripped.partition("=")
            key = key.strip()
            if key in env:
                new_lines.append(f"{key}={env[key]}")
                written_keys.add(key)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    # Append new keys that weren't in the original file
    for key, value in env.items():
        if key not in written_keys:
            new_lines.append(f"{key}={value}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def render_section(title: str, fields: list[tuple[str, str, str, str, bool, str | None]]):
    """Render a section of settings fields.

    Each field: (key, label, help_text, default, is_password, field_type)
    field_type: None = text_input, "select" = selectbox, "number" = number_input
    Returns dict of values.
    """
    st.subheader(title)
    values = {}
    for key, label, help_text, default, is_password, field_type in fields:
        current = st.session_state.env.get(key, default)
        if field_type == "select":
            # Parse options from default: "option1,option2,option3"
            options = [o.strip() for o in default.split(",")]
            idx = options.index(current) if current in options else 0
            values[key] = st.selectbox(label, options, index=idx, help=help_text, key=f"env_{key}")
        elif field_type == "number":
            values[key] = st.number_input(label, value=int(current) if current else 0, help=help_text, key=f"env_{key}")
        else:
            input_type = "password" if is_password else "default"
            values[key] = st.text_input(
                label,
                value=current,
                help=help_text,
                key=f"env_{key}",
                type=input_type,
            )
    return values


def init_session():
    if "workspace" not in st.session_state:
        st.session_state.workspace = ws.DEFAULT_WORKSPACE


def load_feeds(workspace: str) -> list[dict]:
    """Load feeds.json for a workspace."""
    feeds_path = ws.get_feeds_path(workspace)
    if not feeds_path.exists():
        return []
    return json.loads(feeds_path.read_text(encoding="utf-8"))


def save_feeds(workspace: str, feeds: list[dict]) -> None:
    """Save feeds.json for a workspace."""
    feeds_path = ws.get_feeds_path(workspace)
    feeds_path.write_text(json.dumps(feeds, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    init_session()
    st.title("设置")

    workspace = st.session_state.workspace
    st.caption(f"工作区：{workspace}")

    # Initialize session state
    if "env" not in st.session_state:
        st.session_state.env = load_env_file()

    env = st.session_state.env

    # Feeds management
    st.subheader("订阅源")
    feeds = load_feeds(workspace)

    if feeds:
        for i, feed in enumerate(feeds):
            with st.expander(feed.get("name", "")):
                edit_name = st.text_input("名称", value=feed.get("name", ""), key=f"edit_name_{i}")
                edit_url = st.text_input("URL", value=feed.get("url", ""), key=f"edit_url_{i}")
                type_options = ["rss", "web"]
                edit_type = st.selectbox(
                    "类型", type_options,
                    index=type_options.index(feed.get("source_type", "rss")),
                    key=f"edit_type_{i}",
                )

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("删除", key=f"del_feed_{i}", use_container_width=True):
                        feeds.pop(i)
                        save_feeds(workspace, feeds)
                        st.rerun()
                with col2:
                    if st.button("保存", key=f"save_feed_{i}", type="primary", use_container_width=True):
                        feeds[i] = {
                            "name": edit_name,
                            "url": edit_url,
                            "source_type": edit_type,
                        }
                        save_feeds(workspace, feeds)
                        st.rerun()
    else:
        st.info("暂无订阅源")

    # Add new feed
    with st.expander("添加订阅源"):
        new_name = st.text_input("名称", key="new_feed_name", placeholder="如 Cloudflare Blog")
        new_url = st.text_input("URL", key="new_feed_url", placeholder="RSS 地址或网页 URL")
        new_type = st.selectbox("类型", ["rss", "web"], key="new_feed_type")
        if st.button("添加", use_container_width=True) and new_name and new_url:
            feeds.append({
                "name": new_name,
                "url": new_url,
                "source_type": new_type,
            })
            save_feeds(workspace, feeds)
            st.rerun()

    st.divider()

    # LLM API
    llm_values = render_section("LLM API", [
        ("API_BASE_URL", "API 地址", "OpenAI 兼容格式，支持 DeepSeek / 通义千问 / Kimi 等", "https://api.deepseek.com/v1", False, None),
        ("API_KEY", "API Key", "", "", True, None),
        ("MODEL_NAME", "模型名称", "", "deepseek-chat", False, None),
    ])

    st.divider()

    # Embedding API
    embedding_values = render_section("Embedding API", [
        ("EMBEDDING_API_BASE_URL", "Embedding API 地址", "用于知识库语义搜索", "https://api.siliconflow.cn/v1", False, None),
        ("EMBEDDING_API_KEY", "Embedding API Key", "", "", True, None),
        ("EMBEDDING_MODEL", "Embedding 模型", "", "Qwen/Qwen3-Embedding-4B", False, None),
        ("EMBEDDING_DIM", "向量维度", "需与模型匹配（默认 2560）", "2560", False, "number"),
    ])

    st.divider()

    # SMTP Email
    smtp_values = render_section("SMTP 邮件（可选）", [
        ("SMTP_SERVER", "SMTP 服务器", "如 smtp.qq.com", "", False, None),
        ("SMTP_PORT", "SMTP 端口", "如 587", "587", False, "number"),
        ("SMTP_SENDER", "发件人邮箱", "", "", False, None),
        ("SMTP_AUTH_CODE", "邮箱授权码", "QQ 邮箱需开启 POP3/SMTP 并生成授权码", "", True, None),
        ("SMTP_RECEIVER", "收件人邮箱", "", "", False, None),
    ])

    st.divider()

    # Summary settings
    summary_values = render_section("摘要设置", [
        ("SUMMARY_DAYS", "回溯天数", "默认 7 天", "7", False, "number"),
        ("SUMMARY_LANGUAGE", "输出语言", "", "zh-CN,en", False, "select"),
        ("PROMPT_NAME", "提示词模板", "", "tech-weekly,finance-weekly,papers-weekly", False, "select"),
    ])

    st.divider()

    # LLM parameters
    llm_params = render_section("LLM 参数（可选）", [
        ("LLM_TEMPERATURE", "生成温度", "0-2，默认 0.3", "0.3", False, None),
        ("LLM_MAX_TOKENS", "最大输出 token", "默认 4096", "4096", False, "number"),
    ])

    st.divider()

    # Other
    other_values = render_section("其他", [
        ("GITHUB_REPO_URL", "GitHub 仓库地址", "用于 GitHub Pages 页面链接", "", False, None),
        ("FETCH_MAX_WORKERS", "并发抓取线程数", "默认 8", "8", False, "number"),
    ])

    st.divider()

    # Save button
    col1, col2 = st.columns(2)
    with col1:
        if st.button("保存配置", type="primary", use_container_width=True):
            # Merge all values
            all_values = {}
            for d in [llm_values, embedding_values, smtp_values, summary_values, llm_params, other_values]:
                for k, v in d.items():
                    if v:  # Only save non-empty values
                        all_values[k] = v

            save_env_file(all_values)
            st.session_state.env = load_env_file()
            st.success("配置已保存到 .env")

    with col2:
        if st.button("重新加载", use_container_width=True):
            st.session_state.env = load_env_file()
            st.rerun()

    # Show raw .env
    with st.expander("查看原始 .env 文件"):
        env_path = Path(DEFAULT_ENV_PATH)
        if env_path.exists():
            st.code(env_path.read_text(encoding="utf-8"), language="bash")
        else:
            st.info(".env 文件不存在")


if __name__ == "__main__":
    main()
