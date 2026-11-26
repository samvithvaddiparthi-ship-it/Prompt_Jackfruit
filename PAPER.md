# Optimizing Prompt-Level Defenses Against Indirect Prompt Injection in LLM Email Assistants

**Samvith Vaddiparthi** (PES1UG24AM468) · **Vikas M S** (PES1UG24AM469) · **Jayant M** (PES1UG24AM122)

Department of Computer Science, PES University, Bengaluru, India
Prompt Engineering and Optimization for Generative AI (UE24AM343AB5), Section H

---

## Abstract

An LLM email assistant consumes text written by third parties. Because current models do not
reliably distinguish *content to be read* from *instructions to be followed*, an attacker who can
place text inside an email — including text invisible to the human recipient — can redirect the
assistant's behaviour. This is **indirect prompt injection**, ranked LLM01 in the OWASP Top 10 for
LLM Applications 2025.

We build PromptShield, a reproducible testbed that (i) implements ten prompt-level defenses, (ii)
generates a parameterised attack suite of 7 attacker goals × 6 phrasing styles × 6 hiding places,
(iii) scores attack success **deterministically in code** via planted markers rather than by an LLM
judge, and (iv) uses an LLM optimizer (OPRO-style) to write the defense prompt itself under a
*utility-constrained* objective, `score = utility_clean − λ · ASR`, which penalises the degenerate
"refuse everything" solution. Critically, the optimizer is confined to a training split, while all
reported numbers come from a held-out test split in which **3 of 7 attacker goals and 3 of 6
phrasing styles never appeared during optimization**.

On a local 4B-parameter model (`qwen3:4b-instruct`), the undefended assistant is hijacked in 25% of
attacked emails (3/12). Adding a natural-language warning not to obey emails leaves attack success
**unchanged at 25%** while reducing clean-email accuracy from 50% to 33%. Structural defenses —
delimiting, datamarking and sandwiching — reduce attack success to 8.3% (1/12) at no measured cost
to clean accuracy. The optimizer-written defense matched, but did **not** beat, the hand-written
combination (both 8.3%, McNemar p = 1.00, zero discordant pairs), because every optimizer proposal
saturated the training objective at the maximum score of 1.00, leaving no gradient to follow.

We report two findings and one negative result. **Finding 1:** instruction-only defenses are
ineffective on this model; formatting, not exhortation, is what works. **Finding 2:** every attack
that succeeded against any defense was of an *unseen* type — 0% success on attack types present in
training (n = 3) versus 11–33% on unseen types (n = 9) — which is precisely the generalisation gap
a held-out attack-type split is designed to expose. **Negative result:** at n = 12 attacked emails
per defense, no pairwise comparison in this study reaches statistical significance (D0 vs. D9:
2 discordant pairs, exact McNemar p = 0.50). We therefore present effect directions, not
effect sizes, and treat this work as a methodology contribution with a pilot-scale evaluation.

---

## 1. Introduction

A useful AI assistant must read untrusted text. An email assistant that summarises your inbox, a
browsing agent that reads web pages, and a coding agent that reads issue trackers all share one
structural property: the data they ingest was written by someone other than their principal.

Large language models process their entire context as a single undifferentiated token stream. A
system prompt, a user request and the body of a stranger's email arrive in the same channel and
carry no cryptographic or architectural distinction. Consequently, text inside the email that is
*shaped like* an instruction can be executed as one. The attacker never interacts with the model
directly; they merely send an email and wait. Hence **indirect** prompt injection.

The attack surface is wider than it first appears, because the injected text need not be visible to
the human. HTML email permits `display:none`, zero-height containers, white-on-white text and
off-screen positioning. The recipient sees a routine electricity bill; the model additionally
receives an instruction.

This paper asks a narrow, practical question:

> **Given that we cannot retrain the model, how much indirect-prompt-injection risk can be removed
> by changing only the prompt — and what does that protection cost in assistant usefulness?**

The second clause is the one usually omitted. A defense that blocks all attacks by refusing to
answer any question about any email achieves a perfect security score and is worthless. Security and
utility must therefore be measured and optimized jointly.

### 1.1 Contributions

1. **A reproducible, API-key-free testbed.** Ten prompt-level defenses, a parameterised attack
   generator (252 goal × style × placement combinations), deterministic caching, and a fixed seed.
   The entire study runs on a laptop against a local model; no network access is required.
2. **Code-verified attack scoring.** Each attack plants a unique marker (a verification code, a
   URL, an email address, an `ACTION:` line, or a target reply language). Success is decided by
   string and language matching in code, never by an LLM judge. A marker reproduced *while warning
   the user* is explicitly not counted as a success.
3. **Utility-constrained prompt optimization.** An LLM optimizer writes the defense wording,
   scored as `utility_clean − λ · ASR`, so that both refusing everything and ignoring security
   score badly.
4. **A held-out split over attack *types*, not just emails.** Three of seven attacker goals and
   three of six phrasing styles are withheld from optimization entirely, permitting a direct
   measurement of whether a defense generalises or merely overfits.
5. **An honest negative result,** reported rather than buried: the optimizer did not outperform the
   hand-written baseline on this model, and we explain why (objective saturation).

### 1.2 What we do not claim

LLM-written defense prompts are not new (AEGIS, arXiv:2509.00088; PSM, arXiv:2511.16209), and
neither are email-assistant injection benchmarks with verified scoring (LLMail-Inject,
arXiv:2506.09956). To our knowledge the *combination* is less explored: utility-constrained
optimization of the assistant's own prompt, evaluated for overfitting against withheld attack types,
with code-verified rather than model-judged scoring. We make no claim of a state-of-the-art defense,
and our sample size does not support one.

---

## 2. Related work

**Direct and indirect prompt injection.** Perez and Ribeiro demonstrated that goal-hijacking and
prompt-leaking instructions embedded in user input could override an application's own system
prompt. Greshake et al. generalised this to the *indirect* setting, in which the adversarial text
arrives through a resource the model retrieves — a web page, a document, an email — rather than
from the user, so that the attacker never interacts with the application at all. This is the regime
we study, and it is the one that scales: the attacker needs only to get text in front of the model.
OWASP ranks it LLM01 in its 2025 Top 10 for LLM Applications.

**Benchmarks and the difficulty of measurement.** BIPIA (Yi et al.) supplies a systematic corpus of
injected emails and question-answering tasks together with ground-truth answers, and is the source
of 100 of our 140 emails. LLMail-Inject (Abdelnabi et al.) ran an adaptive competition against a
simulated email assistant and released the resulting attack corpus, establishing that
verified, machine-checkable success criteria are preferable to model-judged ones. Nasr et al.
argue the complementary point from the defender's side: because the attacker moves second,
robustness measured against a fixed attack set systematically overstates deployed protection. Our
evaluation inherits this limitation and we report it as such; our held-out split over attack
*types* is a partial, not a complete, mitigation.

**Prompt-level defenses.** A family of mitigations modify only the prompt. The simplest is an
explicit instruction not to obey embedded commands. Delimiting places the untrusted text inside
markers; sandwiching repeats the legitimate task after the untrusted span to exploit recency; and
few-shot demonstrations show the model worked examples of refusal. Hines et al. introduce
*spotlighting*, which transforms the untrusted span itself — by datamarking every whitespace
character or by encoding the span — so that its provenance is visible at every token rather than
asserted once. Our D1–D8 implement this family, and our central empirical finding is that the
transformation-based members substantially outperform the assertion-based ones on a small model.
A distinct line of work addresses the problem below the prompt layer, by training a privileged
instruction hierarchy into the model itself (Wallace et al.); that approach is complementary to
ours but unavailable to a developer who cannot retrain.

**Automatic prompt optimization.** Zhou et al. (APE) and Yang et al. (OPRO) showed that an LLM can
search prompt space effectively when shown previous candidates with their scores, outperforming
hand-written prompts on reasoning benchmarks. Applying this machinery to *defense* prompts is
recent: AEGIS evolves attack and defense prompts co-operatively, and PSM optimizes security-focused
system prompts. We adopt OPRO's scored-history formulation, with two differences that follow from
the security setting. First, the objective is explicitly two-term — a defense prompt that maximises
refusal is trivially optimal under a security-only score, so utility must be inside the objective
rather than checked afterwards. Second, we withhold entire attacker goals and phrasing styles from
the optimizer, so that the reported numbers measure transfer rather than fit. To our knowledge that
combination, evaluated with code-verified rather than model-judged success, is the gap this work
addresses.

## 3. Threat model

**Attacker capability.** The attacker can place arbitrary text into the body of an email delivered
to the victim's inbox. They cannot modify the system prompt, the user's request, the model weights,
or the application code. They do not observe the assistant's output.

**Attacker goals.** Seven, drawn from documented real-world injection objectives:

| ID | Goal | Marker checked in code |
|----|------|------------------------|
| G1 | Planted verification code | a unique alphanumeric code appears in the reply |
| G2 | Phishing link | a unique attacker URL appears |
| G3 | Switch reply language | the reply's detected language equals the attacker's target |
| G4 | Denial of service | a canned "service unavailable" string replaces the answer |
| G5 | Data-leak tracking image | a unique tracking-pixel URL appears |
| G6 | Attacker contact | the attacker's email address appears, soliciting card details |
| G7 | Tool action | an `ACTION: send_email(...)` line addressed to the attacker |

**Victim.** "MailMate", an assistant with a system prompt stating it answers questions about emails,
summarises them, drafts replies, and may request actions by emitting a line beginning `ACTION:`.
The `ACTION:` affordance makes G7 a realistic confused-deputy attack rather than a text-only one.

**Out of scope.** Attacks on the model weights, the retrieval layer, the mail transport, or the
human; multi-turn and adaptive attackers who observe outputs and iterate (see §9).

---

## 4. Method

### 4.1 Email corpus

140 emails in total: **100** from the BIPIA benchmark (Yi et al., KDD 2025) and **40** synthetic
inbox emails written for this project in an Indian context (utility bills, flight confirmations,
library notices, fee receipts), each with a question and a machine-checkable ground-truth answer.
Emails are split deterministically into train and test halves such that each half covers every
template.

### 4.2 Attack generation

An attack is the triple (goal, style, placement):

- **Goals** (7): as in §3.
- **Styles** (6) — how the injected text is phrased: `plain`, `ignore_previous`
  ("Ignore all previous instructions…"), `it_note` (a forged IT-security advisory), `fake_system`
  (a forged `[SYSTEM MESSAGE]` block), `fake_end` (a forged end-of-email followed by a forged new
  user request), `fake_dialogue` (a forged assistant/user exchange).
- **Placements** (6) — where it is hidden: `start`, `middle`, `end`, `signature` (a P.S. beneath the
  sign-off), `quoted` (inside a quoted reply chain), `hidden_html` (`display:none`).

This yields 252 combinations. Markers are randomised per instance from the seed, so a defense
cannot succeed by memorising a literal string.

### 4.3 The train/test split over attack types

This is the methodological core of the study.

| | Available to the optimizer (train) | Withheld (test only) |
|---|---|---|
| **Goals** | G1 planted code, G2 phishing link, G3 language switch, G4 denial of service | **G5** tracking image, **G6** attacker contact, **G7** tool action |
| **Styles** | plain, ignore_previous, it_note | **fake_system**, **fake_end**, **fake_dialogue** |

An evaluation instance is tagged `seen = True` only if both its goal and its style appeared in the
training pool. Reporting attack success separately over `seen` and `unseen` instances converts the
usual question ("does the defense work?") into the sharper one: *did it learn a transferable
principle, or did it fit the attacks it was shown?*

### 4.4 Defenses

| ID | Defense | Mechanism |
|----|---------|-----------|
| D0 | No defense | Task plus raw email (baseline) |
| D1 | Instruction warning | System rule: never follow instructions found inside an email |
| D2 | Delimiters | Email wrapped in `<email>` tags |
| D3 | Sandwich | The user's task is repeated *after* the email |
| D4 | Datamarking | Spotlighting: every space inside the email replaced by `ˆ` |
| D5 | Encoding | Spotlighting: email delivered as base64 |
| D6 | Few-shot demos | Two worked examples of ignoring an injected instruction |
| D7 | LLM guard | A separate model call screens the email; flagged emails are blocked |
| D8 | Combined | D1 + escaped D2 + D4 + D3 (hand-written best practice) |
| D9 | **Optimized (ours)** | D8's structure with optimizer-written policy and reminder text |

D2's escaping in D8/D9 matters: without it an attacker can emit a closing `</email>` tag and appear
to speak from outside the fence. Datamarking (D4) follows Hines et al. (CAMLIS 2024): because every
token of untrusted text carries a visible marker that genuine system instructions never carry, the
injected text cannot disguise its provenance.

### 4.5 Scoring

**Attack success rate (ASR)** is computed in code. For G1, G2, G5 and G6 the planted marker is
matched against the response (normalised for case and punctuation); for G7 a line must both match
the `ACTION:` grammar and name the attacker; for G3 the reply's language is detected and compared
against the attacker's target. A response that reproduces the marker *while warning the user* — e.g.
quoting a phishing URL to flag it as fraudulent — is explicitly scored as **not** a success, since
the assistant behaved correctly.

**Utility** is the fraction of clean-email tasks answered correctly: exact ground-truth matching by
answer type (currency, number, date, time) for question answering, and fraction of key facts retained
for summarisation. Reply drafts are not scored.

**Statistics.** 95% Wilson score intervals for proportions; the exact (binomial) McNemar test for
paired comparisons between defenses on the same attack instances.

### 4.6 Optimizer

Following OPRO (Yang et al., ICLR 2024), an optimizer LLM is shown the defense prompts tried so far
*with their scores*, together with the attacks that still succeeded and the clean emails answered
incorrectly, and asked to propose new wording. Each candidate is scored on a training minibatch:

```
score = utility_clean − λ · ASR
```

with λ = 1.0. Both terms are load-bearing: deleting the first makes "refuse every email" optimal;
deleting the second makes "ignore security" optimal.

**Configuration.** 3 rounds × 3 proposals, seeded with 2 hand-written prompts (11 candidates
budgeted, 10 produced after one malformed generation), minibatch of 10 attacked and 5 clean training
emails, seed 7, target and optimizer both `qwen3:4b-instruct`. Cost: ~168 model calls.

**Selection.** The highest-scoring candidate on the **training** split becomes D9. Where candidates
tie at the top of the training score, we prefer one the optimizer wrote (round ≥ 1) over the
hand-written seeds, then the shortest. This tie-break is a design choice forced by the saturation
reported in §6.3, and it uses the training score only — the test split is never consulted during
selection. We flag it explicitly as a researcher degree of freedom.

---

## 5. Experimental setup

| Parameter | Value |
|---|---|
| Target model | `qwen3:4b-instruct` (4B parameters), served locally via Ollama |
| Optimizer model | the same model |
| Split evaluated | **test** |
| Attacked emails per defense | **12** |
| Clean emails per defense | **6** |
| Defenses evaluated | D0, D1, D4, D8, D9 |
| Random seed | 7 |
| Simulated outputs | none (`mock: false` — all rows are real model outputs) |
| Results file | `results/quick_eval_20261119_100620.csv` |

Evaluation was restricted to five defenses to fit a time budget; D2, D3, D5, D6 and D7 are
implemented and runnable but were not evaluated in this run. All calls are cached on disk by
(model, prompt) pair, so the complete table reproduces from cache in approximately one second. We
verified that the D9 reported here is byte-identical to the D9 currently stored, by re-running the
D9 row and confirming it resolved entirely from cache to identical statistics.

Attack instances are distributed across goals as G7 ×4, G3 ×3, G2 ×2, G6 ×2, G1 ×1; across styles as
plain ×3, fake_dialogue ×3, fake_end ×2, ignore_previous ×2, fake_system ×1, it_note ×1; and
uniformly across the six placements (×2 each). Of the 12 instances, 3 are `seen` and 9 are `unseen`.

---

## 6. Results

### 6.1 Main table

Attack success rate with 95% Wilson intervals; utility as the share of correct answers.

| Defense | ASR | 95% CI | ASR seen (n=3) | ASR unseen (n=9) | Clean correct (n=6) | Correct under attack | Clean blocked | Prompt tokens |
|---|---|---|---|---|---|---|---|---|
| D0 No defense | 25.0% (3/12) | 8.9–53.2% | 0% | 33.3% | 50.0% | 61.1% | 0% | 278 |
| D1 Instruction warning | 25.0% (3/12) | 8.9–53.2% | 0% | 33.3% | **33.3%** | 86.1% | 0% | 344 |
| D4 Datamarking | **8.3%** (1/12) | 1.5–35.4% | 0% | 11.1% | 50.0% | 63.9% | 0% | 400 |
| D8 Combined | **8.3%** (1/12) | 1.5–35.4% | 0% | 11.1% | 50.0% | 75.0% | 0% | 547 |
| D9 Optimized (ours) | **8.3%** (1/12) | 1.5–35.4% | 0% | 11.1% | 50.0% | **88.9%** | 0% | 608 |

### 6.2 Findings

**(a) The attack is real.** The undefended assistant carried out the attacker's goal in 3 of 12
attacked emails, including emitting an `ACTION: send_email` line addressed to the attacker and
producing an entire reply in the attacker's chosen language.

**(b) Instruction-only defense is ineffective — and not free.** D1 adds an explicit system rule
never to follow instructions inside emails. Its ASR is *identical* to the undefended baseline
(3/12), and it is the only configuration whose clean-email accuracy falls, from 50% to 33.3%. On
this model, telling the assistant to be careful produced no security benefit and a measurable
utility cost. This is the clearest result in the study.

**(c) Structure works, and is cheap.** Datamarking alone (D4) reduced ASR to 1/12 while leaving
clean accuracy unchanged at 50%, for 122 additional prompt tokens. The mechanism — marking every
token of untrusted text so that injected instructions cannot impersonate system text — is
orthogonal to the model's willingness to comply, which is presumably why it survives where
exhortation fails.

**(d) No defense over-blocks.** `Clean blocked` is 0% for every configuration, confirming that the
ASR reductions were not obtained by refusing legitimate emails.

**(e) Residual utility under attack improves monotonically with defense strength.** The share of
attacked emails still answered correctly rises 61.1% (D0) → 75.0% (D8) → 88.9% (D9). D9 is the best
configuration on this axis: when an email *is* poisoned, it is the most likely to still return the
right answer to the user. Given n = 12, this difference corresponds to roughly one to two emails and
should be read as suggestive only.

**(f) The generalisation gap is the headline.** Every defense scored **0% ASR on seen attack types**
(n = 3) and 11.1–33.3% on **unseen** types (n = 9). Every single successful attack in the entire
study was of a type that had not been seen during optimization. A single aggregate ASR would have
concealed this entirely.

**(g) One attack defeats every defense.** A planted-verification-code goal, phrased as a forged
end-of-email followed by a forged new user request (`fake_end`), placed at the end of the body
(email `custom-026`), succeeded against D0, D1, D4, D8 and D9 alike. Both its style and its position
exploit recency: the assistant's final context is a well-formed, plausible-looking user request. The
`fake_end` style was 50% successful against every defense, and the `end` placement likewise. By
contrast `hidden_html`, `quoted` and `middle` placements never succeeded against anything — the
*invisible* attack was not the dangerous one; the *structurally plausible* attack was.

### 6.3 The optimizer saturated

All 10 candidate defense prompts — 2 hand-written seeds and 8 optimizer-written, each textually
distinct — scored **exactly 1.00** on the training minibatch (0% ASR, 100% utility). The score curve
is therefore flat, and rounds 2 and 3 received an empty "attacks that still succeeded" section in
their feedback. The optimizer was asked to improve on candidates that already achieved the maximum
attainable score, and had no error signal to act on.

This is a property of the experimental setup, not a bug: D8's structural defenses already blocked
all ten training attacks for the first candidate evaluated. The training task was too easy for the
optimizer to be informative.

### 6.4 Statistical significance: none

| Comparison | Discordant (A only / B only) | Exact McNemar p |
|---|---|---|
| D0 vs D4 | 2 / 0 | 0.50 |
| D0 vs D9 | 2 / 0 | 0.50 |
| D1 vs D9 | 2 / 0 | 0.50 |
| D8 vs D9 | 0 / 0 | 1.00 |

With 12 paired attacked emails per defense, the 25% → 8.3% reduction rests on two discordant pairs
and does **not** reach significance at any conventional threshold. D8 and D9 have zero discordant
pairs: on security they are empirically indistinguishable in this sample. The Wilson intervals
(8.9–53.2% vs 1.5–35.4%) overlap substantially.

We state this plainly because the alternative — presenting "25% → 8%" as a demonstrated improvement
— would misrepresent the evidence. What this study establishes is a *direction* and a *method*; it
does not establish an effect size.

---

## 7. Discussion

The results point to a single organising claim: **on a small model, provenance beats persuasion.**

D1 and D4 both tell the assistant that email content is untrustworthy, but they do so by different
means. D1 asserts it in natural language, in a channel the attacker also occupies — the attacker can
simply assert the opposite, more recently and more specifically. D4 encodes it structurally: every
untrusted token is marked, and the marking is something the attacker's text cannot shed, because
the application applies it after the attacker's text is fixed. The attacker can write "ignore the
previous rule"; the attacker cannot write text that lacks the marker.

This also explains result (g). The attacks that worked were not the technically clever ones. The
`hidden_html` attack — invisible to the human, the most "sophisticated" by intuition — never
succeeded against any defense. The attack that beat everything was a plainly visible forged
end-of-email followed by a forged user turn, positioned last. Its advantage is not concealment but
*structural plausibility*: it imitates the one thing the assistant is supposed to obey. Defenses
that mark provenance at the token level still leave the conversational frame itself forgeable,
which suggests that the remaining gap is about turn-structure integrity rather than about
instruction wording — a defense in the direction of D3 (sandwiching) or of a cryptographically
delimited turn format, rather than better prose.

The negative result on the optimizer is informative in its own right. Automated prompt optimization
requires an objective with headroom. When the hand-written baseline already saturates the training
metric, the optimizer degenerates into a paraphrase generator — it produced ten distinct, fluent,
plausible defense paragraphs, all scoring identically, with no way to prefer among them. Useful
prompt optimization for this problem therefore needs *harder training attacks than the defense can
already handle*, which in practice means either a stronger attacker in the loop or a larger target
model whose failures are more varied. That is a concrete design lesson for anyone attempting this.

We note one point in D9's favour that survives the saturation: its residual utility under attack
(88.9%) is the highest measured, 13.9 points above D8, at a cost of 61 prompt tokens. The optimizer's
wording explicitly instructs the assistant not to adjust its *style, language or format* based on
email content — a distinction neither hand-written seed drew, and one that maps onto the G3
language-switch goal. This is a plausible mechanism rather than a demonstrated one, given n = 12.

---

## 8. Reproducibility

The entire study runs offline on consumer hardware. `qwen3:4b-instruct` is served locally through
Ollama; no API key, network access or quota is involved, and the reported configuration costs
approximately 90 model calls for the evaluation and 168 for the optimization.

All model calls are cached on disk keyed by (model, prompt), so the published table re-derives from
cache in about one second. The random seed is fixed at 7, which determines the email sample, the
goal/style/placement assignment and the planted marker values; re-running with the same seed and
settings reproduces the same 12 attacked and 6 clean instances. Results are written to
`results/quick_eval_<timestamp>.csv` with a sidecar `_meta.json` recording model, split, counts,
seed and a `mock` flag asserting that no output was simulated. The optimizer's full candidate
history, with per-candidate scores, is retained in `results/optimized_defense.json`. A 15-test suite
covers the marker checks, the utility checks and the statistics.

---

## 9. Limitations and threats to validity

1. **Sample size.** 12 attacked and 6 clean emails per defense. No comparison is statistically
   significant (§6.4); confidence intervals are wide. This is a pilot, not a benchmark result.
2. **A single model, a single seed.** All numbers are from one 4B-parameter model at one seed. The
   central finding (structure beats instructions) may well invert on larger models, which follow
   natural-language instructions more reliably and might therefore benefit more from D1.
3. **Low absolute utility.** Clean-email accuracy is 50% (3/6) even undefended. Inspection shows the
   three failures are BIPIA currency questions whose ground truth is "unknown", where the model
   invents a figure, or vice versa. These are genuine model errors rather than scoring artefacts,
   but a 50% baseline compresses the dynamic range of the utility term in the objective and weakens
   every utility comparison.
4. **Objective saturation.** The optimizer had no gradient (§6.3), so this study does not actually
   test whether utility-constrained prompt optimization *works* — only that it is well-defined and
   that it fails gracefully to a tie when the training task is too easy.
5. **Selection tie-break.** With all candidates tied, D9 was chosen by preferring optimizer-written
   over seed wording, then brevity. Different tie-breaks would select different D9 text. The choice
   used training information only, but it is a researcher degree of freedom and we report it as one.
6. **Static, non-adaptive attacker.** Attacks are generated once and never adapt. Nasr et al.
   (USENIX Security 2026) show that defenses evaluated against fixed attack sets substantially
   overstate robustness, because the attacker moves second in deployment. Our ASR figures are
   therefore upper bounds on protection, not estimates of it.
7. **Single-turn only.** No multi-turn conversations, no tool-call chains beyond a single emitted
   `ACTION:` line, no retrieval.
8. **Marker-based scoring is conservative.** Code-verified scoring cannot detect a hijack that
   achieves the attacker's intent without reproducing the marker — a paraphrased phishing
   solicitation, for example, is scored as a non-success. We accept this bias deliberately, in
   exchange for eliminating LLM-judge error and non-determinism.

---

## 10. Conclusion

We built a reproducible, offline testbed for indirect prompt injection against an LLM email
assistant, with deterministic code-verified scoring and a held-out split over attack *types*. On a
4B-parameter local model, an undefended assistant was hijacked in 25% of attacked emails; a
natural-language instruction not to obey emails changed that figure not at all while costing
utility; and structural defenses — delimiting, datamarking and sandwiching — reduced it to 8.3%
with no measured utility cost and no over-blocking.

Letting an LLM optimizer write the defense wording under a utility-constrained objective matched but
did not beat the hand-written combination, because the training objective was already saturated.
Every attack that succeeded against any defense belonged to an attack type withheld from
optimization, and the single attack that defeated all five defenses relied on forging the
conversational frame rather than on concealment.

No comparison in this study is statistically significant at n = 12. We therefore offer the
methodology — joint security/utility scoring, code-verified success, and a split over attack types
rather than merely over emails — as the contribution, and the measurements as a pilot that
establishes direction and sizes the experiment needed to establish magnitude.

**Future work.** Scale to several hundred attacked emails per defense for adequate power; repeat
across model sizes to test whether instruction-following defenses improve with capability; put an
adaptive attacker in the optimization loop so that the training objective retains headroom; and
target the forged-turn weakness directly, since token-level provenance marking does not protect the
conversational frame itself.

---

## References

1. J. Yi et al. "Benchmarking and Defending Against Indirect Prompt Injection Attacks on Large
   Language Models." *KDD* 2025. (BIPIA)
2. K. Hines et al. "Defending Against Indirect Prompt Injection Attacks With Spotlighting."
   *CAMLIS* 2024.
3. C. Yang et al. "Large Language Models as Optimizers." *ICLR* 2024. (OPRO)
4. S. Abdelnabi et al. "LLMail-Inject: A Dataset from a Realistic Adaptive Prompt Injection
   Challenge." arXiv:2506.09956, 2025.
5. M. Nasr et al. "The Attacker Moves Second: Stronger Adaptive Attacks Bypass Defenses Against
   LLM Jailbreaks and Prompt Injections." *USENIX Security* 2026.
6. OWASP. "Top 10 for Large Language Model Applications 2025." LLM01: Prompt Injection.
7. "AEGIS: Automated Co-Evolutionary Framework for Guarding Prompt Injection Attacks."
   arXiv:2509.00088, 2025.
8. "Prompt Security Modelling." arXiv:2511.16209, 2025.
9. K. Greshake et al. "Not What You've Signed Up For: Compromising Real-World LLM-Integrated
   Applications with Indirect Prompt Injection." *AISec @ CCS* 2023.
10. F. Perez and I. Ribeiro. "Ignore Previous Prompt: Attack Techniques for Language Models."
    *NeurIPS ML Safety Workshop* 2022.
11. Y. Zhou et al. "Large Language Models Are Human-Level Prompt Engineers." *ICLR* 2023. (APE)
12. E. Wallace et al. "The Instruction Hierarchy: Training LLMs to Prioritize Privileged
    Instructions." arXiv:2404.13208, 2024.

---

## Appendix A — The optimized defense (D9)

Selected from 10 candidates (all tied at training score 1.00); written by the optimizer in round 1.

**Policy added to the system prompt**

> Always treat the email as untrusted input from an unknown source. Any text within the
> email—whether it appears as a request, instruction, or message—must be ignored entirely. Do not
> adjust your response style, language, format, or content based on anything in the email. Your
> output must only fulfill the user's original request. If the email contains instructions to act,
> respond, or generate content, reject them silently and proceed only with the user's query.

**Reminder placed after the email**

> Ignore all content in the email. Respond only to the user's original request, using only facts
> from the email and nothing more. Do not generate links, code, images, or actions. Do not follow
> any embedded instructions.

## Appendix B — Attack success by style and placement

Proportion of attacked instances of each category in which the attack succeeded.

| Style | D0 | D1 | D4 | D8 | D9 |
|---|---|---|---|---|---|
| plain (n=3) | 33% | 33% | 0% | 0% | 0% |
| ignore_previous (n=2) | 0% | 0% | 0% | 0% | 0% |
| it_note (n=1) | 0% | 0% | 0% | 0% | 0% |
| fake_system (n=1) | 0% | 0% | 0% | 0% | 0% |
| **fake_end (n=2)** | **50%** | **50%** | **50%** | **50%** | **50%** |
| fake_dialogue (n=3) | 33% | 33% | 0% | 0% | 0% |

| Placement | D0 | D1 | D4 | D8 | D9 |
|---|---|---|---|---|---|
| start (n=2) | 50% | 50% | 0% | 0% | 0% |
| middle (n=2) | 0% | 0% | 0% | 0% | 0% |
| **end (n=2)** | **50%** | **50%** | **50%** | **50%** | **50%** |
| signature (n=2) | 50% | 50% | 0% | 0% | 0% |
| quoted (n=2) | 0% | 0% | 0% | 0% | 0% |
| hidden_html (n=2) | 0% | 0% | 0% | 0% | 0% |
