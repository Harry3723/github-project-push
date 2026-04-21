from __future__ import annotations

# Broad productivity-focused search queries.
# Goal: cast a wide net across general tools useful for a PhD researcher's daily life.
# An LLM selector will then pick the 3 most relevant from the collected pool.
SEARCH_QUERIES: list[tuple[str, str]] = [
    # AI assistants & information discovery
    ("ai assistant research productivity stars:>2000", "AI工具"),
    ("llm agent automation productivity stars:>2000", "AI助手"),
    ("information aggregation news feed rss stars:>1000", "信息聚合"),
    ("arxiv paper search semantic scholar stars:>500", "论文发现"),

    # Daily workflow & terminal
    ("terminal shell productivity developer stars:>3000", "终端效率"),
    ("automation workflow python stars:>2000", "自动化"),
    ("developer tools productivity open-source stars:>3000", "开发效率"),

    # Writing & knowledge management
    ("note-taking knowledge-base research stars:>2000", "知识管理"),
    ("writing academic markdown stars:>1000", "写作工具"),

    # Scientific Python & data
    ("scientific computing python visualization stars:>2000", "科学计算"),
    ("data analysis python research stars:>2000", "数据分析"),

    # Broad useful tools
    ("open-source tools useful productivity stars:>5000", "实用工具"),
]

# User profile passed to the LLM selector — update if your focus shifts
USER_PROFILE = """
PhD student in Electrical & Computer Engineering at UT Austin.
Research focus: photonic computing for AI acceleration — specifically photonic tensor cores,
optical neural networks, and on-chip analog photonic computing.
Goal: discover GitHub projects that meaningfully improve day-to-day research productivity,
such as tools for finding and filtering information faster, automating repetitive tasks,
improving writing/note-taking workflow, or broadly useful utilities that save real time.
Hardware/EDA/circuit-specific tools are NOT a priority unless they are exceptional general productivity tools.
"""
