from collections import defaultdict

import numpy as np
import pytest
import scipy.sparse as sps
from sklearn.metrics import average_precision_score, ndcg_score

from irspack.evaluator import Evaluator
from irspack.recommenders.base import BaseRecommender


class MockRecommender(BaseRecommender):
    def __init__(self, X_all: sps.csr_matrix, scores: np.ndarray) -> None:
        super().__init__(X_all)
        self.scores = scores

    def get_score(self, user_indices: np.ndarray) -> np.ndarray:
        return self.scores[user_indices]

    def _learn(self) -> None:
        pass


@pytest.mark.parametrize("U, I", [(10, 5), (10, 30)])
def test_metrics(U: int, I: int) -> None:
    rns = np.random.RandomState(42)
    scores = rns.randn(U, I)
    X_gt = (rns.rand(U, I) >= 0.3).astype(np.float64)
    eval = Evaluator(sps.csr_matrix(X_gt), offset=0, cutoff=I, n_thread=4)
    # empty mask
    mock_rec = MockRecommender(sps.csr_matrix(X_gt.shape), scores)
    my_score = eval.get_score(mock_rec)
    sklearn_metrics = defaultdict(list)
    for i in range(scores.shape[0]):
        if X_gt[i].sum() == 0:
            continue
        sklearn_metrics["map"].append(average_precision_score(X_gt[i], scores[i]))
        sklearn_metrics["ndcg"].append(ndcg_score(X_gt[i][None, :], scores[i][None, :]))

    for key in ["map", "ndcg"]:
        assert my_score[key] == pytest.approx(np.mean(sklearn_metrics[key]), abs=1e-8)


@pytest.mark.parametrize("U, I, C", [(10, 5, 5), (10, 30, 29)])
def test_metrics_with_cutoff(U: int, I: int, C: int) -> None:
    rns = np.random.RandomState(42)
    scores = rns.randn(U, I)
    X_gt = (rns.rand(U, I) >= 0.3).astype(np.float64)
    eval = Evaluator(sps.csr_matrix(X_gt), offset=0, cutoff=C, n_thread=2)
    # empty mask
    mock_rec = MockRecommender(sps.csr_matrix(X_gt.shape), scores)
    my_score = eval.get_score(mock_rec)

    ndcg = 0.0
    valid_users = 0
    map = 0.0
    precision = 0.0
    recall = 0.0
    item_appearance_count = np.zeros((I,), dtype=np.float64)
    for i in range(U):
        nzs = set(X_gt[i].nonzero()[0])
        if len(nzs) == 0:
            continue
        valid_users += 1
        ndcg += ndcg_score(X_gt[[i]], scores[[i]], k=C)
        recommended = scores[i].argsort()[::-1][:C]
        recall_denom = min(C, len(nzs))
        ap = 0.0
        current_hit = 0
        for i, rec in enumerate(recommended):
            item_appearance_count[rec] += 1.0
            if rec in nzs:
                current_hit += 1
                ap += current_hit / float(i + 1)
        ap /= recall_denom
        map += ap
        recall += current_hit / recall_denom
        precision += current_hit / C
    entropy = (lambda p: -p.dot(np.log(p)))(
        item_appearance_count / item_appearance_count.sum()
    )
    item_appearance_sorted_normalized = (
        np.sort(item_appearance_count) / item_appearance_count.sum()
    )
    lorentz_curve = np.cumsum(item_appearance_sorted_normalized)

    gini_index = 0
    delta = 1 / I
    for i in range(I):
        f = 2 * (((i + 1) / I) - lorentz_curve[i])
        gini_index += delta * f

    assert my_score["ndcg"] == pytest.approx(ndcg / valid_users)
    assert my_score["map"] == pytest.approx(map / valid_users, abs=1e-8)
    assert my_score["precision"] == pytest.approx(precision / valid_users, abs=1e-8)
    assert my_score["recall"] == pytest.approx(recall / valid_users, abs=1e-8)
    assert my_score["entropy"] == pytest.approx(entropy)
    assert my_score["gini_index"] == pytest.approx(gini_index)
