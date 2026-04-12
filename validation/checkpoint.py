# ─── checkpoint.py ───────────────────────────────────────────────────────────
# Lưu và load tiến trình validation để resume khi quota reset

import json
from pathlib import Path
from datetime import datetime


class Checkpoint:
    """
    Cấu trúc checkpoint.json:
    {
      "created_at": "...",
      "updated_at": "...",
      "input_file": "...",
      "total_rows": 8000,
      "t1_t2_done": true,           # T1+T2 đã chạy xong chưa
      "t3_candidates": [0, 1, 5...], # index các row pass T1+T2
      "models": {
        "gemini":   {"status": "done"|"quota"|"running", "last_row_idx": 142},
        "grok":     {"status": "done", "last_row_idx": 7999},
        "qwen":     {"status": "quota", "last_row_idx": 300},
        "deepseek": {"status": "done", "last_row_idx": 7999}
      },
      "aggregated": false   # kết quả cuối đã được aggregate chưa
    }
    """

    def __init__(self, checkpoint_path: str):
        self.path = Path(checkpoint_path)
        self._data: dict = {}

    def exists(self) -> bool:
        return self.path.exists()

    def load(self) -> dict:
        with open(self.path, encoding="utf-8") as f:
            self._data = json.load(f)
        return self._data

    def init(self, input_file: str, total_rows: int, model_names: list[str]):
        self._data = {
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "input_file": input_file,
            "total_rows": total_rows,
            "t1_t2_done": False,
            "t3_candidates": [],
            "models": {m: {"status": "pending", "last_row_idx": -1} for m in model_names},
            "aggregated": False,
        }
        self.save()

    def save(self):
        self._data["updated_at"] = datetime.now().isoformat()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    # ── Accessors ─────────────────────────────────────────────────────────────
    def set_t1t2_done(self, candidate_indices: list[int]):
        self._data["t1_t2_done"] = True
        self._data["t3_candidates"] = candidate_indices
        self.save()

    def set_model_status(self, model: str, status: str, last_row_idx: int):
        """status: 'running' | 'done' | 'quota'"""
        self._data["models"][model]["status"]       = status
        self._data["models"][model]["last_row_idx"] = last_row_idx
        self.save()

    def get_model_resume_idx(self, model: str) -> int:
        """
        Trả về index trong t3_candidates mà model cần bắt đầu (resume).
        -1 nghĩa là chưa chạy gì. last_row_idx là t3_candidate index đã xong.
        """
        return self._data["models"][model]["last_row_idx"] + 1

    def is_model_done(self, model: str) -> bool:
        return self._data["models"][model]["status"] == "done"

    def is_model_quota(self, model: str) -> bool:
        return self._data["models"][model]["status"] == "quota"

    def all_models_finished(self) -> bool:
        """True nếu tất cả model đã done hoặc quota (không còn model nào đang running/pending)."""
        return all(
            self._data["models"][m]["status"] in ("done", "quota")
            for m in self._data["models"]
        )

    def get_pending_models(self) -> list[str]:
        """Models chưa hoàn thành (pending hoặc bị quota ở lần trước)."""
        return [
            m for m, info in self._data["models"].items()
            if info["status"] in ("pending", "quota")
        ]

    @property
    def t3_candidates(self) -> list[int]:
        return self._data["t3_candidates"]

    @property
    def data(self) -> dict:
        return self._data
