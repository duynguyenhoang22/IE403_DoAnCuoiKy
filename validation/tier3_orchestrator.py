# ─── tier3_orchestrator.py ───────────────────────────────────────────────────
# Chạy 4 judges song song, thu thập kết quả, tổng hợp vote

import json
import threading
from pathlib import Path
from tqdm import tqdm

from judges.base import QuotaExceededException
from judges.models import get_all_judges
from checkpoint import Checkpoint
from config import LLM_BATCH_SIZE, SMISHING_OBF_RANGE, CLEAN_FORMALITY_RANGE


# ── Per-model result store ────────────────────────────────────────────────────
# model_results[model_name][candidate_idx] = judge output dict | "error"
_results_lock = threading.Lock()


def _run_one_judge(judge, candidates: list[dict], candidate_indices: list[int],
                   start_idx: int, ckpt: Checkpoint,
                   model_results: dict, pbar_dict: dict):
    """
    Chạy trong thread riêng. Xử lý từng batch, lưu kết quả vào model_results.
    Nếu quota → dừng, cập nhật checkpoint.
    """
    name = judge.name
    total = len(candidate_indices)

    for batch_start in range(start_idx, total, LLM_BATCH_SIZE):
        batch_cand_indices = candidate_indices[batch_start : batch_start + LLM_BATCH_SIZE]
        batch_rows = [candidates[i] for i in batch_cand_indices]

        try:
            results = judge.judge_batch(batch_rows)
        except QuotaExceededException as e:
            # Đánh dấu tất cả row từ đây trở đi là quota
            with _results_lock:
                for ci in batch_cand_indices:
                    model_results[name][ci] = "quota"
                # Mark remaining rows
                for remaining_start in range(batch_start + LLM_BATCH_SIZE, total, LLM_BATCH_SIZE):
                    for ci in candidate_indices[remaining_start : remaining_start + LLM_BATCH_SIZE]:
                        model_results[name][ci] = "quota"
            ckpt.set_model_status(name, "quota", batch_start - 1)
            print(f"\n[T3][{name}] ⚠ Quota exceeded tại batch {batch_start//LLM_BATCH_SIZE}. "
                  f"Đã xử lý {batch_start}/{total} rows.")
            return

        with _results_lock:
            if results is None:
                # Parse/API fail sau retry → đánh error
                for ci in batch_cand_indices:
                    model_results[name][ci] = "error"
            else:
                for j, ci in enumerate(batch_cand_indices):
                    model_results[name][ci] = results[j] if j < len(results) else "error"

            # Cập nhật progress bar
            if name in pbar_dict:
                pbar_dict[name].update(len(batch_cand_indices))

        # Lưu checkpoint sau mỗi batch
        ckpt.set_model_status(name, "running", batch_start + len(batch_cand_indices) - 1)

    ckpt.set_model_status(name, "done", total - 1)
    print(f"\n[T3][{name}] ✓ Hoàn thành {total} rows.")


def run_tier3(rows: list[dict], t3_candidate_indices: list[int],
              ckpt: Checkpoint, output_dir: str) -> dict:
    """
    Chạy 4 judges song song trên t3_candidate_indices.
    Trả về dict: {original_row_idx: aggregated_result}
    """
    candidates = [rows[i] for i in t3_candidate_indices]
    # t3_candidate_indices[j] = original row index của candidates[j]
    cand_local = list(range(len(candidates)))   # 0..N-1 index trong candidates[]

    # Khởi tạo model_results
    model_results = {name: {} for name in ["gemini", "grok", "qwen", "deepseek"]}

    judges = get_all_judges()
    pending_models = ckpt.get_pending_models()
    active_judges = [j for j in judges if j.name in pending_models]

    if not active_judges:
        print("[T3] Tất cả models đã hoàn thành — load kết quả từ file.")
    else:
        print(f"[T3] Chạy song song: {[j.name for j in active_judges]}")

        # Load kết quả từ file nếu có (resume)
        for j in judges:
            result_file = Path(output_dir) / f"t3_{j.name}.jsonl"
            if result_file.exists():
                with open(result_file, encoding="utf-8") as f:
                    for line in f:
                        entry = json.loads(line)
                        model_results[j.name][entry["cand_idx"]] = entry["result"]

        # Progress bars
        pbar_dict = {
            j.name: tqdm(total=len(cand_local), desc=f"  {j.name:10}", position=i, leave=True)
            for i, j in enumerate(active_judges)
        }

        # Chạy threads song song
        threads = []
        for j in active_judges:
            start_idx = ckpt.get_model_resume_idx(j.name)
            t = threading.Thread(
                target=_run_one_judge,
                args=(j, candidates, cand_local, start_idx,
                      ckpt, model_results, pbar_dict),
                daemon=True,
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        for pb in pbar_dict.values():
            pb.close()

        # Lưu kết quả từng model ra file (để resume sau)
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        for model_name, results in model_results.items():
            result_file = Path(output_dir) / f"t3_{model_name}.jsonl"
            with open(result_file, "w", encoding="utf-8") as f:
                for ci, res in sorted(results.items()):
                    f.write(json.dumps({"cand_idx": ci, "result": res}, ensure_ascii=False) + "\n")

    # ── Aggregate votes ───────────────────────────────────────────────────────
    aggregated = {}   # original_row_idx → result

    for local_idx, orig_idx in enumerate(t3_candidate_indices):
        votes_pass = 0
        votes_fail = 0
        quota_models = []
        error_models = []
        fail_reasons = []
        judge_verdicts = {}

        cat_votes = {}   # category → count
        level_votes = {} # level → count

        for model_name in ["gemini", "grok", "qwen", "deepseek"]:
            res = model_results[model_name].get(local_idx)

            if res == "quota":
                quota_models.append(model_name)
            elif res in ("error", None):
                error_models.append(model_name)
            elif isinstance(res, dict):
                passed = res.get("overall_pass", False)
                judge_verdicts[model_name] = "pass" if passed else "fail"

                if passed:
                    votes_pass += 1
                else:
                    votes_fail += 1
                    if res.get("fail_reason"):
                        fail_reasons.append(f"[{model_name}] {res['fail_reason']}")

                # Thu thập category và level để lấy consensus
                cat = res.get("inferred_category")
                if cat:
                    cat_votes[cat] = cat_votes.get(cat, 0) + 1

                lvl = res.get("inferred_obf_level") or res.get("inferred_formality_level")
                if lvl is not None:
                    level_votes[lvl] = level_votes.get(lvl, 0) + 1
            else:
                error_models.append(model_name)

        # Nếu có bất kỳ model nào quota → row này pending
        if quota_models:
            status = "pending"
            fail_reason = f"quota_exceeded: {','.join(quota_models)}"
            overall_pass = False
        elif votes_pass + votes_fail == 0:
            status = "flag_T3-no_result"
            fail_reason = f"all_models_error: {','.join(error_models)}"
            overall_pass = False
        elif votes_pass >= 3:       # 3-1 hoặc 4-0
            status = "pass"
            fail_reason = None
            overall_pass = True
        elif votes_fail >= 3:       # 3-1 hoặc 4-0 fail
            status = "flag_T3-fail"
            fail_reason = "; ".join(fail_reasons)
            overall_pass = False
        elif votes_pass == 2 and votes_fail == 2:   # tie
            status = "flag_T3-tie"
            fail_reason = f"2-2 tie: pass=[{','.join(k for k,v in judge_verdicts.items() if v=='pass')}] " \
                          f"fail=[{','.join(k for k,v in judge_verdicts.items() if v=='fail')}]"
            overall_pass = False
        else:
            # 1 model error + 2-1 → vẫn có majority
            if votes_pass > votes_fail:
                status = "pass"
                fail_reason = f"partial_judges(error:{','.join(error_models)})"
                overall_pass = True
            else:
                status = "flag_T3-fail"
                fail_reason = "; ".join(fail_reasons)
                overall_pass = False

        # Consensus category và level
        inferred_category = max(cat_votes, key=cat_votes.get) if cat_votes else None
        inferred_level    = max(level_votes, key=level_votes.get) if level_votes else None

        # Designed range
        label = str(rows[orig_idx]["label"])
        if label == "1" and inferred_category:
            r = SMISHING_OBF_RANGE.get(inferred_category, (None, None))
            designed_range = f"{r[0]}-{r[1]}" if r[0] is not None else "unknown"
            level_in_range = (r[0] is not None and inferred_level is not None
                              and r[0] <= inferred_level <= r[1])
        elif label == "0" and inferred_category:
            r = CLEAN_FORMALITY_RANGE.get(inferred_category, (None, None))
            designed_range = f"{r[0]}-{r[1]}" if r[0] is not None else "unknown"
            level_in_range = (r[0] is not None and inferred_level is not None
                              and r[0] <= inferred_level <= r[1])
        else:
            designed_range = None
            level_in_range = None

        # Level ngoài range → thêm warning vào status (không override pass/fail)
        if overall_pass and inferred_category and level_in_range is False:
            status = "pass_warn_level"
            fail_reason = (f"inferred_level={inferred_level} ngoài designed_range={designed_range} "
                           f"cho '{inferred_category}'")

        aggregated[orig_idx] = {
            "validation_status":    status,
            "fail_reason":          fail_reason,
            "inferred_category":    inferred_category,
            "inferred_level":       inferred_level,
            "level_in_range":       level_in_range,
            "designed_range":       designed_range,
            "votes_pass":           votes_pass,
            "votes_fail":           votes_fail,
            "judge_verdicts":       json.dumps(judge_verdicts, ensure_ascii=False),
            "quota_models":         ",".join(quota_models) if quota_models else None,
        }

    return aggregated
