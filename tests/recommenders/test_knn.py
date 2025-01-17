import numpy as np
import pytest
import scipy.sparse as sps

from irspack.recommenders.knn import (
    AsymmetricCosineKNNRecommender,
    CosineKNNRecommender,
    JaccardKNNRecommender,
)
from irspack.recommenders.p3 import P3alphaRecommender
from irspack.recommenders.rp3 import RP3betaRecommender

X_small = sps.csr_matrix(
    np.asfarray([[1, 1, 2, 3, 4], [0, 1, 0, 1, 0], [0, 0, 1, 0, 0], [0, 0, 0, 0, 0]])
)
X_many = np.random.rand(888, 512)
X_many[X_many <= 0.9] = 0
X_many[X_many > 0.9] = 1
X_many = sps.csr_matrix(X_many)
X_many.sort_indices()

X_many_dense = sps.csr_matrix(np.random.rand(133, 245))


@pytest.mark.parametrize(
    "X, normalize", [(X_many, True), (X_small, False), (X_many_dense, True)]
)
def test_cosine(X: sps.csr_matrix, normalize: bool) -> None:
    rec = CosineKNNRecommender(
        X, shrinkage=0, n_thread=5, top_k=X.shape[1], normalize=normalize
    )
    rec.learn()
    sim = rec.W.toarray()
    manual = X.T.toarray()  # I x U
    norm = (manual ** 2).sum(axis=1) ** 0.5
    manual = manual.dot(manual.T)
    if normalize:
        denom = norm[:, None] * norm[None, :] + 1e-6
        manual /= denom
    np.fill_diagonal(manual, 0)
    np.testing.assert_allclose(
        sim,
        manual,
    )


@pytest.mark.parametrize("X", [X_many, X_small, X_many_dense])
def test_jaccard(X: sps.csr_matrix) -> None:
    rec = JaccardKNNRecommender(X, shrinkage=0, top_k=X.shape[1], n_thread=1)
    rec.learn()
    sim = rec.W.toarray()
    X_bin = X.copy()
    X_bin.sort_indices()
    X_bin.data[:] = 1
    manual = X_bin.T.toarray()  # I x U
    norm = manual.sum(axis=1)
    manual = manual.dot(manual.T)
    denom = norm[:, None] + norm[None, :] - manual + 1e-6
    denom[denom <= 1e-10] = 1e-10
    manual = manual / denom
    np.fill_diagonal(manual, 0)
    assert np.all(np.abs(sim - manual) <= 1e-5)


@pytest.mark.parametrize(
    "X, alpha", [(X_many, 0.5), (X_small, 0.7), (X_many_dense, (0.01))]
)
def test_asymmetric_cosine(X: sps.csr_matrix, alpha: float) -> None:
    rec = AsymmetricCosineKNNRecommender(
        X, shrinkage=0, alpha=alpha, n_thread=1, top_k=X.shape[1]
    )
    rec.learn()
    sim = rec.W.toarray()

    manual = X.T.toarray()  # I x U
    norm = (manual ** 2).sum(axis=1)
    norm_alpha = np.power(norm, alpha)
    norm_1malpha = np.power(norm, 1 - alpha)
    manual_sim = manual.dot(manual.T)
    denom = norm_alpha[:, None] * norm_1malpha[None, :] + 1e-6
    manual_sim /= denom
    np.fill_diagonal(manual_sim, 0)
    np.testing.assert_allclose(
        sim,
        manual_sim,
    )


@pytest.mark.parametrize("X", [X_many, X_small])
def test_topk(X: sps.csr_matrix) -> None:
    rec = CosineKNNRecommender(X, shrinkage=0, top_k=30, n_thread=5)
    rec.learn()
    sim = rec.W.toarray()
    assert np.all((sim > 0).sum(axis=1) <= 30)


@pytest.mark.parametrize("X, alpha", [(X_small, 0.001), (X_many_dense, 2), (X_many, 1)])
def test_p3(X: sps.csr_matrix, alpha: float) -> None:
    rec = P3alphaRecommender(X, alpha=alpha, n_thread=4)
    rec.learn()
    W = rec.W.toarray()

    P_ui = np.power(X.toarray(), alpha)
    P_iu = np.power(X.T.toarray(), alpha)

    def zero_or_1(X: np.ndarray) -> np.ndarray:
        X = X.copy()
        X[X == 0] = 1
        return X

    P_ui /= zero_or_1(P_ui.sum(axis=1))[:, None]
    P_iu /= zero_or_1(P_iu.sum(axis=1))[:, None]
    W_man = P_iu.dot(P_ui)
    np.testing.assert_allclose(W, W_man)


@pytest.mark.parametrize(
    "X, alpha, beta", [(X_small, 0.001, 10), (X_many_dense, 2, 10), (X_many, 1, 2)]
)
def test_rp3(X: sps.csr_matrix, alpha: float, beta: float) -> None:
    rec = RP3betaRecommender(X, alpha=alpha, beta=beta, n_thread=4)
    rec.learn()
    W = rec.W.toarray()
    W_sum = W.sum(axis=1)
    W_sum = W_sum[W_sum >= 0]
    np.testing.assert_allclose(W_sum, 1.0)

    popularity = X.sum(axis=0).A1.ravel() ** beta

    def zero_or_1(X: np.ndarray) -> np.ndarray:
        X = X.copy()
        X[X == 0] = 1
        return X

    P_ui = np.power(X.toarray(), alpha) / zero_or_1(popularity)[None, :]
    P_iu = np.power(X.T.toarray(), alpha) / zero_or_1(popularity)[:, None]

    P_ui /= zero_or_1(P_ui.sum(axis=1))[:, None]
    P_iu /= zero_or_1(P_iu.sum(axis=1))[:, None]
    W_man = P_iu.dot(P_ui)
    np.testing.assert_allclose(W, W_man)


def test_raise_shrinkage() -> None:
    with pytest.raises(ValueError):
        _ = P3alphaRecommender(X_many.T, alpha=1.0, n_thread=0)
        _.learn()

    with pytest.raises(ValueError):
        _ = P3alphaRecommender(X_many.T, alpha=-1.0, n_thread=1)
        _.learn()

    with pytest.raises(ValueError):
        rec = AsymmetricCosineKNNRecommender(X_many, 0, alpha=1.5)
        rec.learn()
