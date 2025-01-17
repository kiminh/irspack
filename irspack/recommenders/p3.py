from typing import Optional

from sklearn.preprocessing import normalize

from ..definitions import InteractionMatrix
from ._knn import P3alphaComputer
from .base import BaseRecommenderWithThreadingSupport, BaseSimilarityRecommender


class P3alphaRecommender(
    BaseSimilarityRecommender, BaseRecommenderWithThreadingSupport
):
    def __init__(
        self,
        X_all: InteractionMatrix,
        alpha: float = 1,
        top_k: Optional[int] = None,
        normalize_weight: bool = False,
        n_thread: Optional[int] = 1,
    ):
        super().__init__(X_all, n_thread=n_thread)
        self.alpha = alpha
        self.top_k = top_k
        self.normalize_weight = normalize_weight

    def _learn(self) -> None:
        computer = P3alphaComputer(
            self.X_all.T,
            alpha=self.alpha,
            n_thread=self.n_thread,
        )
        top_k = self.X_all.shape[1] if self.top_k is None else self.top_k
        self.W_ = computer.compute_W(self.X_all.T, top_k)
        if self.normalize_weight:
            self.W_ = normalize(self.W_, norm="l1", axis=1)
