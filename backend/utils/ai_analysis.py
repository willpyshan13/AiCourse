"""Evidence-based reference feedback for classroom practice records."""
from __future__ import annotations


async def analyze_practice(title: str, content: str, member_text: str) -> dict[str, str]:
    """Generate reference feedback from the fields that were actually recorded."""
    return _analyze_local(title, content, member_text)


def _analyze_local(title: str, content: str, member_text: str) -> dict[str, str]:
    title = title.strip()
    content = content.strip()
    members = [line.strip() for line in member_text.splitlines() if line.strip()]
    documented = [
        line
        for line in members
        if not any(
            marker in line for marker in ("：未记录", ":未记录", "：未填写", ":未填写")
        )
    ]

    signals = {
        "过程": ("步骤", "过程", "首先", "然后", "制作", "操作", "开展", "实施"),
        "数据": ("数据", "测量", "记录了", "统计", "厘米", "千克", "分钟", "%", "％"),
        "结果": ("结果", "发现", "观察到", "完成", "得到", "变化", "结论"),
        "反思": ("反思", "改进", "不足", "下次", "问题", "原因", "建议"),
    }
    present = [name for name, terms in signals.items() if any(term in content for term in terms)]
    missing = [name for name in signals if name not in present]
    observations = []
    if content:
        if present:
            observations.append(f"活动记录涉及{'、'.join(present)}。")
        else:
            observations.append("已填写活动内容，但暂未明确写出过程、数据、结果或反思。")
    else:
        observations.append("尚未填写活动内容，无法根据记录判断实践过程和成果。")
    if documented:
        observations.append(f"已记录{len(documented)}名成员的具体工作，可据此核对分工。")
    else:
        observations.append("尚未记录成员的具体工作，暂无法评价协作情况。")

    suggestions = {
        "过程": "补充活动步骤和所用方法",
        "数据": "补充观察或测量数据",
        "结果": "写明实际结果和发现",
        "反思": "记录遇到的问题及改进想法",
    }
    if missing:
        observations.append("建议" + "，并".join(suggestions[name] for name in missing[:2]) + "。")
    else:
        observations.append("建议对照原始记录核实数据，并说明结论如何得出。")
    if not documented and members:
        observations.append("可为每位成员补充具体贡献。")

    if present and missing:
        summary = f"《{title}》已记录{'、'.join(present)}；可继续完善{'、'.join(missing[:2])}。"
    elif present:
        summary = f"《{title}》已记录过程、数据、结果和反思；请结合原始记录核对结论。"
    else:
        summary = f"《{title}》目前信息有限，建议补充过程和实际发现。"
    return {"analysis": "".join(observations), "summary": summary}
