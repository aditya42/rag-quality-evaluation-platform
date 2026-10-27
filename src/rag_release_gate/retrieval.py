"""Small real BM25 retriever, deliberately independent of test references."""

import math
import re
from collections import Counter

from .models import Document, Profile

STOPWORDS = set(
    "a an and are as at be by can do does for from how i in is it its me my of on or our please the their this to what when where which who why will with would you your tell about much many".split()
)


def tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOPWORDS]


class BM25:
    def __init__(self, documents: list[Document]):
        self.documents = documents
        self.counts = [Counter(tokens(d.title + " " + d.text)) for d in documents]
        self.lengths = [sum(c.values()) for c in self.counts]
        self.average = sum(self.lengths) / max(1, len(self.lengths))
        self.df = Counter(t for counts in self.counts for t in counts)

    def search(self, question: str, profile: Profile) -> list[Document]:
        if profile.fault == "drop_context":
            return []
        ranked = []
        query = set(tokens(question))
        for doc, counts, length in zip(self.documents, self.counts, self.lengths, strict=True):
            if profile.active_only and doc.status != "active":
                continue
            if profile.trusted_only and not doc.trusted:
                continue
            score = 0.0
            for term in query:
                freq = counts[term]
                idf = math.log(
                    1 + (len(self.documents) - self.df[term] + 0.5) / (self.df[term] + 0.5)
                )
                denom = freq + 1.5 * (0.25 + 0.75 * length / max(self.average, 1))
                score += idf * freq * 2.5 / denom
            if score > 0:
                ranked.append((score, doc.id, doc))
        ranked.sort(key=lambda row: (-row[0], row[1]))
        return [row[2] for row in ranked[: profile.top_k]]
