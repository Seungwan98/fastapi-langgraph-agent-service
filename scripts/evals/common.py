from __future__ import annotations
import json
import math
import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import cast


ROOT = Path(__file__).resolve().parents[2]


def read_jsonl(path: Path) -> list[dict[str, object]]:
    """JSONL 파일에서 레코드 목록을 읽는다."""
    records: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if isinstance(record, dict):
                records.append(cast(dict[str, object], record))
    return records


def write_jsonl(path: Path, rows: Iterable[dict[str, object]]) -> None:
    """딕셔너리 목록을 JSONL 파일로 저장한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            _ = f.write(json.dumps(row, ensure_ascii=False))
            _ = f.write("\n")


def write_json(path: Path, payload: dict[str, object]) -> None:
    """JSON 데이터를 들여쓰기 형식으로 저장한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def simple_tokenize(text: str) -> list[str]:
    """점수 계산용으로 텍스트를 단순 토큰으로 분리한다."""
    return re.findall(r"[A-Za-z가-힣0-9]+", text.lower())


def lexical_overlap_score(query: str, document: str) -> float:
    """질의와 문서의 토큰 겹침 정도를 점수로 계산한다."""
    q_tokens = simple_tokenize(query)
    d_tokens = simple_tokenize(document)
    if not q_tokens or not d_tokens:
        return 0.0
    q_set = set(q_tokens)
    d_set = set(d_tokens)
    overlap = len(q_set & d_set)
    return overlap / float(len(q_set))


def compute_confusion_matrix(truths: Sequence[str], preds: Sequence[str], labels: Sequence[str]) -> dict[str, dict[str, int]]:
    """정답과 예측 레이블로 다중 분류 혼동 행렬을 만든다."""
    matrix: dict[str, dict[str, int]] = {label: {l: 0 for l in labels} for label in labels}
    for truth, pred in zip(truths, preds):
        if truth not in matrix:
            continue
        if pred not in matrix[truth]:
            continue
        matrix[truth][pred] += 1
    return matrix


def classification_report(confusion: dict[str, dict[str, int]], labels: Sequence[str]) -> dict[str, object]:
    """클래스별 및 전체 분류 지표를 계산한다."""
    per_class: dict[str, dict[str, float | int]] = {}
    total = 0
    correct = 0

    for truth in labels:
        tp = confusion.get(truth, {}).get(truth, 0)
        fp = sum(confusion.get(other, {}).get(truth, 0) for other in labels if other != truth)
        fn = sum(confusion.get(truth, {}).get(other, 0) for other in labels if other != truth)

        precision = tp / (tp + fp) if tp + fp > 0 else 0.0
        recall = tp / (tp + fn) if tp + fn > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if precision + recall > 0 else 0.0

        per_class[truth] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": tp + fn,
        }

    for truth, pred_counts in confusion.items():
        for pred, count in pred_counts.items():
            total += count
            if truth == pred:
                correct += count

    macro_precision = sum(per_class[label]["precision"] for label in labels) / len(labels)
    macro_recall = sum(per_class[label]["recall"] for label in labels) / len(labels)
    macro_f1 = sum(per_class[label]["f1"] for label in labels) / len(labels)
    accuracy = correct / total if total else 0.0

    return {
        "per_class": per_class,
        "macro": {
            "precision": macro_precision,
            "recall": macro_recall,
            "f1": macro_f1,
        },
        "accuracy": accuracy,
        "total": total,
        "correct": correct,
    }


def compute_retrieval_metrics(
    rankings: dict[str, list[str]],
    qrels: dict[str, set[str]],
    ks: Sequence[int] = (1, 3, 5),
) -> dict[str, object]:
    """정렬된 검색 결과의 Recall@k와 MRR을 계산한다."""
    totals = len(qrels)
    recall_hits: dict[int, int] = defaultdict(int)
    reciprocal_ranks: list[float] = []

    for query_id, relevant_ids in qrels.items():
        ranked = rankings.get(query_id, [])
        first_hit = math.inf
        for idx, doc_id in enumerate(ranked, start=1):
            if doc_id in relevant_ids:
                first_hit = min(first_hit, idx)
        if first_hit is not math.inf:
            reciprocal_ranks.append(1.0 / first_hit)
        for k in ks:
            top_k = set(ranked[:k])
            if top_k & relevant_ids:
                recall_hits[k] += 1

    recall = {f"R@{k}": (recall_hits[k] / totals if totals else 0.0) for k in ks}
    mrr = sum(reciprocal_ranks) / totals if totals else 0.0
    return {"recall": recall, "mrr": mrr}


def ensure_dir(path: Path) -> None:
    """필요하면 부모 디렉터리까지 함께 생성한다."""
    path.mkdir(parents=True, exist_ok=True)
