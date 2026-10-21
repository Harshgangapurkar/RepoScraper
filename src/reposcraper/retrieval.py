from __future__ import annotations

import math
import re
from collections import Counter
from .chunking import CodeChunk

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{1,}|[A-Za-z0-9]+")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


class BM25Retriever:
    """Small dependency-free BM25 retriever suitable for bounded code repositories."""

    def __init__(self, chunks: list[CodeChunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.tokens = [tokenize(f"{chunk.path} {chunk.text}") for chunk in chunks]
        self.term_freqs = [Counter(doc) for doc in self.tokens]
        self.doc_lengths = [len(doc) for doc in self.tokens]
        self.avgdl = sum(self.doc_lengths) / max(len(self.doc_lengths), 1)
        df = Counter()
        for doc in self.tokens:
            df.update(set(doc))
        self.idf = {
            term: math.log(1 + (len(chunks) - freq + 0.5) / (freq + 0.5))
            for term, freq in df.items()
        }

    def search(self, query: str, top_k: int = 6) -> list[tuple[CodeChunk, float]]:
        terms = tokenize(query)
        if not terms or not self.chunks:
            return []
        scored = []
        for index, chunk in enumerate(self.chunks):
            score = 0.0
            length = self.doc_lengths[index]
            for term in terms:
                tf = self.term_freqs[index].get(term, 0)
                if not tf:
                    continue
                denom = tf + self.k1 * (1 - self.b + self.b * length / max(self.avgdl, 1))
                score += self.idf.get(term, 0.0) * tf * (self.k1 + 1) / denom
            # Slight boost for exact filename/function-name query matches.
            if any(term in chunk.path.lower() for term in terms):
                score *= 1.2
            if score > 0:
                scored.append((chunk, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:max(1, top_k)]
