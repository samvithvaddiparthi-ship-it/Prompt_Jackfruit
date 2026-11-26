"""Benchmark runner: build instances, run defenses, compute metrics.

Instances come from one split. The optimizer only ever sees "train"; every
reported number comes from "test", where 3 attacker goals and 3 attack styles
never appeared during optimization (tagged seen=False).
"""
from __future__ import annotations

import csv
import itertools
import json
import os
import random
import time
from collections import defaultdict

from . import attacks as A
from .defenses import Defense, run_assistant, task_instruction
from .emails import emails
from .scoring import mcnemar_exact, utility, wilson


def build_instances(split: str, n_attacked: int, n_clean: int, seed: int = 7) -> list[dict]:
    rng = random.Random(f"{split}-{seed}")
    pool = emails(split)
    goals = A.TRAIN_GOALS if split == "train" else list(A.GOALS)
    styles = A.TRAIN_STYLES if split == "train" else list(A.STYLES)
    combos = list(itertools.product(goals, styles))
    rng.shuffle(combos)
    placements = list(A.PLACEMENTS)
    out = []
    for i in range(n_attacked):
        goal, style = combos[i % len(combos)]
        e = rng.choice(pool)
        kind = "summary" if (e["source"] == "custom" and rng.random() < 0.35) else "qa"
        atk = A.make_attack(goal, style, placements[i % len(placements)], rng)
        out.append({"id": f"{split}-atk-{i:03d}", "split": split, "kind": "attacked", "email_id": e["id"],
                    "task_kind": kind, "task": task_instruction(kind, e),
                    "context": A.inject(e["context"], atk), "attack": atk.to_dict(), "seen": atk.seen})
    clean_pool = rng.sample(pool, min(n_clean, len(pool)))
    for i, e in enumerate(clean_pool):
        kind = "summary" if (e["source"] == "custom" and i % 3 == 2) else "qa"
        out.append({"id": f"{split}-cln-{i:03d}", "split": split, "kind": "clean", "email_id": e["id"],
                    "task_kind": kind, "task": task_instruction(kind, e), "context": e["context"],
                    "attack": None, "seen": None})
    return out


_EMAIL_INDEX = None


def email_by_id(eid: str) -> dict:
    global _EMAIL_INDEX
    if _EMAIL_INDEX is None:
        _EMAIL_INDEX = {e["id"]: e for e in emails()}
    return _EMAIL_INDEX[eid]


def run_one(llm, d: Defense, inst: dict) -> dict:
    out = run_assistant(llm, d, inst["task"], inst["context"])
    e = email_by_id(inst["email_id"])
    util = utility(inst["task_kind"], e, out["response"])
    row = {"model": llm.spec, "defense": d.id, "instance": inst["id"], "split": inst["split"],
           "kind": inst["kind"], "task_kind": inst["task_kind"], "email_id": inst["email_id"],
           "response": out["response"], "blocked": out["blocked"], "utility": util,
           "prompt_tokens": out["prompt_tokens"], "completion_tokens": out["completion_tokens"],
           "calls": out["calls"], "latency_s": round(out["latency_s"], 3),
           "goal": "", "style": "", "placement": "", "seen": "", "attack_success": "", "warned": "",
           "check_reason": ""}
    if inst["attack"]:
        a = inst["attack"]
        chk = {"success": False, "warned": False, "reason": "blocked by guard"} if out["blocked"] \
            else A.check_attack(a, out["response"])
        row.update(goal=a["goal"], style=a["style"], placement=a["placement"], seen=a["seen"],
                   attack_success=chk["success"], warned=chk["warned"], check_reason=chk["reason"])
    return row


def run_eval(llm, defenses: list[Defense], instances: list[dict], progress=None, stop_flag=None) -> list[dict]:
    rows, total, k = [], len(defenses) * len(instances), 0
    for d in defenses:
        for inst in instances:
            if stop_flag and stop_flag():
                return rows
            rows.append(run_one(llm, d, inst))
            k += 1
            if progress:
                progress(k, total, d.id)
    return rows


def _rate(vals):
    vals = [v for v in vals if v is not None and v != ""]
    return (sum(vals) / len(vals), len(vals)) if vals else (float("nan"), 0)


def summarize(rows: list[dict]) -> list[dict]:
    by = defaultdict(list)
    for r in rows:
        by[(r["model"], r["defense"])].append(r)
    out = []
    for (model, did), rs in by.items():
        att = [r for r in rs if r["kind"] == "attacked"]
        cln = [r for r in rs if r["kind"] == "clean"]
        k = sum(bool(r["attack_success"]) for r in att)
        lo, hi = wilson(k, len(att))
        seen = [bool(r["attack_success"]) for r in att if r["seen"] is True]
        unseen = [bool(r["attack_success"]) for r in att if r["seen"] is False]
        u_clean, n_uc = _rate([r["utility"] for r in cln])
        u_att, _ = _rate([r["utility"] for r in att])
        out.append({
            "model": model, "defense": did, "n_attacked": len(att), "n_clean": len(cln),
            "asr": k / len(att) if att else float("nan"), "asr_lo": lo, "asr_hi": hi,
            "asr_seen": sum(seen) / len(seen) if seen else float("nan"), "n_seen": len(seen),
            "asr_unseen": sum(unseen) / len(unseen) if unseen else float("nan"), "n_unseen": len(unseen),
            "utility_clean": u_clean, "n_utility_clean": n_uc, "utility_attacked": u_att,
            "blocked_clean": sum(r["blocked"] for r in cln) / len(cln) if cln else float("nan"),
            "warned": sum(bool(r["warned"]) for r in att) / len(att) if att else float("nan"),
            "prompt_tokens": sum(r["prompt_tokens"] for r in rs) / len(rs),
            "latency_s": sum(r["latency_s"] for r in rs) / len(rs),
        })
    order = {f"D{i}": i for i in range(10)}
    return sorted(out, key=lambda x: (x["model"], order.get(x["defense"], 99)))


def breakdown(rows: list[dict], field: str) -> dict:
    """ASR per defense per value of `field` (goal / style / placement)."""
    acc = defaultdict(lambda: [0, 0])
    for r in rows:
        if r["kind"] != "attacked":
            continue
        a = acc[(r["defense"], r[field])]
        a[0] += bool(r["attack_success"])
        a[1] += 1
    return {k: v[0] / v[1] for k, v in acc.items()}


def paired_test(rows: list[dict], d_a: str, d_b: str) -> dict:
    """McNemar on attacked instances: attack success under defense A vs B."""
    a = {r["instance"]: bool(r["attack_success"]) for r in rows if r["defense"] == d_a and r["kind"] == "attacked"}
    b = {r["instance"]: bool(r["attack_success"]) for r in rows if r["defense"] == d_b and r["kind"] == "attacked"}
    common = a.keys() & b.keys()
    only_a = sum(a[i] and not b[i] for i in common)
    only_b = sum(b[i] and not a[i] for i in common)
    return {"n": len(common), "a_only": only_a, "b_only": only_b, "p_value": mcnemar_exact(only_a, only_b)}


FIELDS = ["model", "defense", "instance", "split", "kind", "task_kind", "email_id", "goal", "style", "placement",
          "seen", "attack_success", "warned", "check_reason", "blocked", "utility", "prompt_tokens",
          "completion_tokens", "calls", "latency_s", "response"]


def save_rows(rows: list[dict], path: str, meta: dict | None = None) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    if meta is not None:
        with open(os.path.splitext(path)[0] + "_meta.json", "w", encoding="utf-8") as fh:
            json.dump({**meta, "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")}, fh, indent=2)


def load_rows(path: str) -> list[dict]:
    def conv(v):
        if v in ("True", "False"):
            return v == "True"
        return v
    rows = []
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            r = {k: conv(v) for k, v in r.items()}
            for f in ("prompt_tokens", "completion_tokens", "calls"):
                r[f] = int(r[f])
            r["latency_s"] = float(r["latency_s"])
            r["utility"] = float(r["utility"]) if r["utility"] not in ("", None) else None
            r["seen"] = r["seen"] if isinstance(r["seen"], bool) else None
            r["blocked"] = bool(r["blocked"])
            rows.append(r)
    return rows
