# ─── pipeline.py ─────────────────────────────────────────────────────────────
import csv, sys, time
from pathlib import Path
from tier1_rules    import validate_tier1
from tier2_metadata import validate_tier2
from tier3_orchestrator import run_tier3
from checkpoint import Checkpoint


# ── CSV parser (pipe-delimited, "last 4" strategy) ────────────────────────────
def parse_pipe_row(line: str) -> dict | None:
    parts = line.strip().split("|")
    if len(parts) < 5:
        return None
    return {
        "content":          "|".join(parts[:-4]),
        "label":            parts[-4].strip(),
        "has_url":          parts[-3].strip(),
        "has_phone_number": parts[-2].strip(),
        "sender_type":      parts[-1].strip(),
    }


def load_dataset(filepath: str) -> tuple[list[dict], list[int]]:
    rows, bad_lines = [], []
    with open(filepath, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line: continue
            if i == 1 and "content" in line.lower(): continue   # skip header
            row = parse_pipe_row(line)
            if row is None:
                bad_lines.append(i)
            else:
                row["_orig_idx"] = len(rows)
                rows.append(row)
    return rows, bad_lines


OUTPUT_COLS = [
    "content","label","has_url","has_phone_number","sender_type",
    "validation_status","fail_reason",
    "inferred_category","inferred_level","level_in_range","designed_range",
    "votes_pass","votes_fail","judge_verdicts","quota_models",
]


def run_pipeline(input_path: str, output_path: str,
                 checkpoint_path: str, work_dir: str,
                 skip_tier3: bool = False):

    print(f"\n{'='*62}")
    print(f"  Smishing Dataset Auto Validator — 3-Tier Pipeline")
    print(f"{'='*62}")

    ckpt = Checkpoint(checkpoint_path)

    # ── Load dataset ──────────────────────────────────────────────────────────
    rows, bad_lines = load_dataset(input_path)
    print(f"\n[LOAD] {len(rows):,} rows | {len(bad_lines)} unparseable lines")
    if bad_lines:
        print(f"       Bad lines (first 10): {bad_lines[:10]}")

    n1 = sum(1 for r in rows if str(r.get("label")) == "1")
    n0 = sum(1 for r in rows if str(r.get("label")) == "0")
    print(f"       Label 1 (smishing): {n1:,}  |  Label 0 (clean): {n0:,}\n")

    # ── Init checkpoint nếu chạy lần đầu ────────────────────────────────────
    if not ckpt.exists():
        ckpt.init(input_path, len(rows), ["gemini","grok","qwen","deepseek"])

    ckpt_data = ckpt.load()

    # ── Tầng 1 & 2 (chỉ chạy nếu chưa done) ─────────────────────────────────
    t1_results = [None] * len(rows)
    t2_results = [None] * len(rows)

    if not ckpt_data["t1_t2_done"]:
        t0 = time.time()
        for i, row in enumerate(rows):
            t1_results[i] = validate_tier1(row)
        t1_fail = sum(1 for r in t1_results if not r["pass"])
        print(f"[T1] Rule-based    | Fail: {t1_fail:,} | {time.time()-t0:.2f}s")

        t0 = time.time()
        for i, row in enumerate(rows):
            if t1_results[i]["pass"]:
                t2_results[i] = validate_tier2(row)
        t2_fail = sum(1 for r in t2_results if r and not r["pass"])
        print(f"[T2] Metadata      | Fail: {t2_fail:,} | {time.time()-t0:.2f}s")

        t3_cand_idx = [
            i for i in range(len(rows))
            if t1_results[i]["pass"] and t2_results[i] and t2_results[i]["pass"]
        ]
        ckpt.set_t1t2_done(t3_cand_idx)

        # Persist T1/T2 results để resume
        import json
        Path(work_dir).mkdir(parents=True, exist_ok=True)
        with open(f"{work_dir}/t1t2_results.json","w") as f:
            json.dump({"t1": t1_results, "t2": t2_results}, f)
    else:
        # Resume: load T1/T2 results từ file
        import json
        with open(f"{work_dir}/t1t2_results.json") as f:
            saved = json.load(f)
        t1_results = saved["t1"]
        t2_results = saved["t2"]
        t3_cand_idx = ckpt.t3_candidates
        print(f"[T1/T2] Resumed từ checkpoint — {len(t3_cand_idx):,} T3 candidates")

    # ── Tầng 3 ────────────────────────────────────────────────────────────────
    t3_agg = {}   # orig_idx → result

    if skip_tier3:
        print(f"[T3] SKIPPED (dry-run)")
    else:
        print(f"\n[T3] LLM Judges (parallel) | {len(t3_cand_idx):,} candidates")
        t3_agg = run_tier3(rows, t3_cand_idx, ckpt, work_dir)

        # Summary T3
        statuses = [t3_agg[i]["validation_status"] for i in t3_cand_idx if i in t3_agg]
        from collections import Counter
        stat_cnt = Counter(statuses)
        print(f"\n[T3] Kết quả:")
        for k, v in sorted(stat_cnt.items()):
            print(f"       {k:30s} → {v:,}")

    # ── Ghi output ────────────────────────────────────────────────────────────
    stats = {"pass":0,"flag_T1":0,"flag_T2":0,"flag_T3_fail":0,
             "flag_T3_tie":0,"pending":0,"pass_warn_level":0,"other":0}

    with open(output_path,"w",newline="",encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLS, extrasaction="ignore")
        writer.writeheader()

        for i, row in enumerate(rows):
            out = {k: row.get(k,"") for k in
                   ("content","label","has_url","has_phone_number","sender_type")}
            # Mặc định empty enrichment
            for col in ("inferred_category","inferred_level","level_in_range",
                        "designed_range","votes_pass","votes_fail",
                        "judge_verdicts","quota_models"):
                out[col] = ""

            if not t1_results[i]["pass"]:
                out["validation_status"] = t1_results[i]["fail_code"]
                out["fail_reason"]       = t1_results[i]["fail_reason"]
                stats["flag_T1"] += 1

            elif t2_results[i] and not t2_results[i]["pass"]:
                out["validation_status"] = t2_results[i]["fail_code"]
                out["fail_reason"]       = t2_results[i]["fail_reason"]
                stats["flag_T2"] += 1

            elif i in t3_agg:
                agg = t3_agg[i]
                out.update(agg)
                s = agg["validation_status"]
                if   s == "pass":            stats["pass"] += 1
                elif s == "pass_warn_level": stats["pass_warn_level"] += 1
                elif s == "pending":         stats["pending"] += 1
                elif s == "flag_T3-tie":     stats["flag_T3_tie"] += 1
                elif "fail" in s:            stats["flag_T3_fail"] += 1
                else:                        stats["other"] += 1

            elif skip_tier3:
                out["validation_status"] = "t3_skipped"
                out["fail_reason"] = ""

            writer.writerow(out)

    # ── Final summary ─────────────────────────────────────────────────────────
    print(f"\n{'='*62}")
    print(f"  VALIDATION SUMMARY")
    print(f"{'='*62}")
    print(f"  ✅ pass              : {stats['pass']:,}")
    print(f"  ⚠️  pass_warn_level  : {stats['pass_warn_level']:,}")
    print(f"  ❌ flag_T1 (format)  : {stats['flag_T1']:,}")
    print(f"  ❌ flag_T2 (metadata): {stats['flag_T2']:,}")
    print(f"  ❌ flag_T3 (semantic): {stats['flag_T3_fail']:,}")
    print(f"  🔀 flag_T3 (2-2 tie) : {stats['flag_T3_tie']:,}")
    print(f"  ⏸️  pending (quota)   : {stats['pending']:,}")
    print(f"{'='*62}")
    print(f"  Output: {output_path}")
    if stats["pending"] > 0:
        print(f"\n  ⚠️  Có {stats['pending']:,} rows đang PENDING do quota.")
        print(f"     Khi quota reset, chạy lại lệnh này — pipeline sẽ tự resume.")
    print()
