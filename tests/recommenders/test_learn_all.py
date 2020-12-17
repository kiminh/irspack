import pytest
from typing import Type, List
import numpy as np
import scipy.sparse as sps
from irspack.recommenders import (
    BaseRecommender,
    TopPopRecommender,
    CosineKNNRecommender,
    AsymmetricCosineKNNRecommender,
    TverskyIndexKNNRecommender,
    JaccardKNNRecommender,
    P3alphaRecommender,
    RP3betaRecommender,
    TruncatedSVDRecommender,
    RandomWalkWithRestartRecommender,
    IALSRecommender,
    DenseSLIMRecommender,
    SLIMRecommender,
)

X_train = sps.csr_matrix(
    np.asfarray(
        [[1, 1, 2, 0, 0], [0, 1, 0, 1, 0], [0, 0, 1, 0, 0], [0, 0, 0, 0, 0]]
    )
)

X_test = sps.csr_matrix(
    np.asfarray(
        [[0, 0, 0, 1, 1], [1, 0, 0, 0, 0], [0, 0, 0, 0, 0], [1, 0, 0, 0, 0]]
    )
)

rec_classes: List[Type[BaseRecommender]] = [
    TopPopRecommender,
    CosineKNNRecommender,
    AsymmetricCosineKNNRecommender,
    TverskyIndexKNNRecommender,
    JaccardKNNRecommender,
    P3alphaRecommender,
    RP3betaRecommender,
    TruncatedSVDRecommender,
    RandomWalkWithRestartRecommender,
    IALSRecommender,
    DenseSLIMRecommender,
    SLIMRecommender,
]


@pytest.mark.parametrize("RecommenderClass", rec_classes)
def test_recs(RecommenderClass):
    rec = RecommenderClass(X_train)
    rec.learn()
    scores = rec.get_score(np.arange(X_train.shape[0]))
    assert np.all(np.isfinite(scores))
    assert np.all(~np.isnan(scores))
