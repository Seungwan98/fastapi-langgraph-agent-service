from scripts.evals.common import classification_report, compute_confusion_matrix, compute_retrieval_metrics, lexical_overlap_score


def test_confusion_report_precision_recall_f1():
    """혼동 행렬에서 기대한 분류 지표가 계산되는지 확인한다."""
    labels = ["RED", "AMBER", "GREEN"]
    truths = ["RED", "RED", "AMBER", "GREEN", "GREEN"]
    preds = ["RED", "AMBER", "AMBER", "GREEN", "RED"]

    confusion = compute_confusion_matrix(truths, preds, labels)
    report = classification_report(confusion, labels)

    assert report["accuracy"] == 3 / 5
    assert round(report["macro"]["precision"], 3) == round((0.5 + 0.5 + 1.0) / 3, 3)
    assert report["per_class"]["RED"]["recall"] == 0.5
    assert report["per_class"]["AMBER"]["precision"] == 0.5


def test_retrieval_metrics_and_overlap():
    """검색 지표와 어휘 겹침 점수가 기대값과 맞는지 확인한다."""
    rankings = {
        "q1": ["d1", "d2"],
        "q2": ["d3", "d2", "d1"],
    }
    qrels = {"q1": {"d1"}, "q2": {"d2"}}
    metrics = compute_retrieval_metrics(rankings, qrels, ks=(1, 3))

    assert metrics["recall"]["R@1"] == 0.5
    assert metrics["recall"]["R@3"] == 1.0
    assert metrics["mrr"] == (1 + (1 / 2)) / 2

    score = lexical_overlap_score("chest pain shortness of breath", "chest pain and breath difficulty")
    assert 0 < score <= 1
