# Verdict Evaluation Metrics Report

**Case**: `state-v-malhotra-2024`  
**Batch Source**: `batch_state-v-malhotra-2024_20261119_154602.jsonl`  
**Persona Mix**: `default`  
**Generated At**: `2026-11-19T15:49:33.180310+00:00`  

---

## 1. Executive Summary & Accuracy

| Metric | Observed Value | 95% Confidence Interval |
|---|---|---|
| **Completion Rate** | 100.0% (20/20) | — |
| **Truth-Match Rate** | **0.0%** (0/20) | **[0.0%, 16.1%]** (Wilson score) |
| **Guilty Verdicts** | 0.0% (0) | — |
| **Not Guilty Verdicts** | 0.0% (0) | — |
| **Hung Jury Rate** | 100.0% (20) | — |

---

## 2. Deliberation & Scoring Diagnostics

- **Mean Statutory Score ($0.5 \times J + 0.5 \times P$)**: `0.744`
- **Mean Juror Conviction Ratio ($J$)**: `0.667`
- **Mean Judicial Guilt Probability ($P$)**: `0.821`
- **Mean Disagreement ($|J - P|$)**: `0.154`

---

## 3. Cost & Performance Metrics

| Metric | Total | Per Trial Mean |
|---|---|---|
| **Cumulative Tokens** | 100,000 (75,000 in / 25,000 out) | 5,000.0 tokens |
| **LLM Calls** | 500 calls | 25.0 calls |
| **Mean Latency** | — | 15.0 ms |
| **Failovers / Errors** | 0 calls | — |

### Provider Distribution
- **fake**: 500 calls (100.0%)

---

## 4. Information Isolation Audit

| Check Description | Audit Classification | Violations Found | Status |
|---|---|---|---|
| **Citations of Struck Turns** | Exact Check | 0 | PASS |
| **Citations of Unretrieved Chunks** | Exact Check | 0 | PASS |
| **Witness Timeline Leakage** | Heuristic Check | 0 | PASS |

> [!NOTE]
> Struck turn and statutory citation checks are **exact mathematical guarantees** verified directly against database foreign keys and clean record tables. Witness knowledge isolation is checked via **heuristic lexical matching** against unwitnessed ground truth events.

---
*Report generated automatically by `scripts/report.py`.*
