"""Reference analysis only reports evidence found in the practice record."""
from __future__ import annotations

import asyncio
import unittest

from utils.ai_analysis import analyze_practice


class ReferenceAnalysisTests(unittest.TestCase):
    def test_sparse_record_requests_missing_evidence(self) -> None:
        result = asyncio.run(analyze_practice("种植观察", "种了豆子", "- 小明（记录）：未记录"))
        self.assertIn("暂无法评价协作", result["analysis"])
        self.assertIn("补充活动步骤", result["analysis"])
        self.assertNotIn("成果显著", result["analysis"])
        self.assertIn("信息有限", result["summary"])

    def test_documented_record_uses_actual_signals(self) -> None:
        result = asyncio.run(analyze_practice(
            "种植观察",
            "首先测量豆苗高度，记录了3厘米。结果发现两天后长高了。下次增加对照组。",
            "- 小明（记录）：测量高度\n- 小红（观察）：记录结果",
        ))
        self.assertIn("过程、数据、结果、反思", result["analysis"])
        self.assertIn("2名成员", result["analysis"])
        self.assertIn("核实数据", result["analysis"])
        self.assertNotIn("可继续完善", result["summary"])


if __name__ == "__main__":
    unittest.main()
