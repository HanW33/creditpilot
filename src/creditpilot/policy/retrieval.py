"""Local TF-IDF retrieval over validated synthetic policy sections."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.sparse import spmatrix
from sklearn.feature_extraction.text import TfidfVectorizer

from creditpilot.policy.schemas import PolicyChunk, PolicyEvidenceMatch


@dataclass(slots=True)
class PolicyIndex:
    chunks: tuple[PolicyChunk, ...]
    _vectorizer: TfidfVectorizer = field(init=False, repr=False)
    _matrix: spmatrix = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.chunks:
            raise ValueError("policy index requires at least one chunk")
        self._vectorizer = TfidfVectorizer(lowercase=True, ngram_range=(1, 2))
        self._matrix = self._vectorizer.fit_transform(
            f"{chunk.section_title} {chunk.text}" for chunk in self.chunks
        )

    def search(
        self,
        query: str,
        *,
        top_k: int,
        required_policy_versions: tuple[str, ...] = (),
    ) -> tuple[PolicyEvidenceMatch, ...]:
        if not query.strip():
            raise ValueError("policy query must be non-empty")
        if not 1 <= top_k <= 10:
            raise ValueError("top_k must be between 1 and 10")
        candidate_indices = tuple(
            index
            for index, chunk in enumerate(self.chunks)
            if not required_policy_versions
            or chunk.policy_version in required_policy_versions
        )
        if not candidate_indices:
            raise LookupError("requested policy versions are unavailable")
        query_vector = self._vectorizer.transform([query])
        if query_vector.nnz == 0:
            raise LookupError("query has no searchable synthetic policy terms")
        scores = (self._matrix @ query_vector.T).toarray().ravel()
        ranked = sorted(candidate_indices, key=lambda index: (-scores[index], index))
        return tuple(
            PolicyEvidenceMatch(
                source_document=self.chunks[index].source_document,
                document_title=self.chunks[index].document_title,
                section_or_chunk_reference=(
                    self.chunks[index].section_or_chunk_reference
                ),
                section_title=self.chunks[index].section_title,
                policy_version=self.chunks[index].policy_version,
                effective_date=self.chunks[index].effective_date,
                synthetic_policy_notice=self.chunks[index].synthetic_policy_notice,
                text=self.chunks[index].text,
                retrieval_score=float(np.clip(scores[index], 0.0, 1.0)),
            )
            for index in ranked[: min(top_k, len(ranked))]
        )
