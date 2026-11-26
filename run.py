"""Command-line runner (same engine as the app).

Examples
  python run.py eval --model gemini:gemma-3-12b-it --defenses D0 D1 D3 D4 D7 D8 D9 --n-attacked 18 --n-clean 6
  python run.py optimize --model gemini:gemma-3-12b-it --optimizer gemini:gemini-2.5-flash-lite --rounds 3 --k 3
"""
from __future__ import annotations

import argparse
import os
import time

from promptshield.defenses import all_defenses
from promptshield.evaluate import build_instances, paired_test, run_eval, save_rows, summarize
from promptshield.llm import LLM, load_dotenv
from promptshield.optimizer import optimize


def main():
    load_dotenv()
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("eval")
    e.add_argument("--model", required=True)
    e.add_argument("--defenses", nargs="+", default=["D0", "D1", "D3", "D4", "D7", "D8", "D9"])
    e.add_argument("--n-attacked", type=int, default=18)
    e.add_argument("--n-clean", type=int, default=6)
    e.add_argument("--rpm", type=float, default=14)
    o = sub.add_parser("optimize")
    o.add_argument("--model", required=True)
    o.add_argument("--optimizer", default=None)
    o.add_argument("--rounds", type=int, default=3)
    o.add_argument("--k", type=int, default=3)
    o.add_argument("--n-attacked", type=int, default=10)
    o.add_argument("--n-clean", type=int, default=5)
    o.add_argument("--lam", type=float, default=1.0)
    o.add_argument("--rpm", type=float, default=14)
    a = ap.parse_args()

    llm = LLM(a.model, rpm=a.rpm)
    prog = lambda k, n, m: print(f"\r{k}/{n} {m}      ", end="", flush=True)  # noqa: E731
    if a.cmd == "eval":
        defs = all_defenses()
        missing = [d for d in a.defenses if d not in defs]
        if missing:
            print(f"Skipping {missing}: not available (run the optimizer first for D9).")
        chosen = [defs[d] for d in a.defenses if d in defs]
        rows = run_eval(llm, chosen, build_instances("test", a.n_attacked, a.n_clean), progress=prog)
        path = os.path.join("results", f"quick_eval_{time.strftime('%Y%m%d_%H%M%S')}.csv")
        save_rows(rows, path, meta={"model": a.model, "mock": llm.is_mock, "defenses": a.defenses,
                                    "n_attacked": a.n_attacked, "n_clean": a.n_clean, "split": "test", "seed": 7})
        print(f"\nSaved {path}\n")
        print(f"{'def':4} {'ASR':>6} {'95% CI':>13} {'unseen':>7} {'clean ok':>9} {'tokens':>7}")
        for s in summarize(rows):
            print(f"{s['defense']:4} {s['asr']:6.0%} {s['asr_lo']:6.0%}-{s['asr_hi']:<6.0%} {s['asr_unseen']:7.0%} "
                  f"{s['utility_clean']:9.0%} {s['prompt_tokens']:7.0f}")
        if "D8" in a.defenses and "D9" in a.defenses and "D9" in defs:
            print("D8 vs D9 McNemar:", paired_test(rows, "D8", "D9"))
    else:
        opt = LLM(a.optimizer, rpm=a.rpm) if a.optimizer else llm
        res = optimize(llm, opt, rounds=a.rounds, k=a.k, n_attacked=a.n_attacked, n_clean=a.n_clean, lam=a.lam,
                       progress=prog)
        print(f"\nBest train score {res['train_score']:.3f} (ASR {res['train_asr']:.0%}, "
              f"correct {res['train_utility']:.0%})\nPOLICY: {res['policy_text']}\nREMINDER: {res['reminder_text']}")


if __name__ == "__main__":
    main()
