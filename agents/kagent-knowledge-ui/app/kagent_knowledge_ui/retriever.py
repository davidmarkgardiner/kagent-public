from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9-]{1,}")
HEADING_RE = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
STOPWORDS = {
    "about",
    "after",
    "also",
    "and",
    "are",
    "bring",
    "can",
    "do",
    "for",
    "from",
    "how",
    "into",
    "issue",
    "kubernetes",
    "own",
    "problem",
    "repair",
    "set",
    "that",
    "the",
    "this",
    "what",
    "with",
    "your",
}


@dataclass(frozen=True)
class Chunk:
    path: str
    heading: str
    text: str
    url: str


@dataclass(frozen=True)
class SearchHit:
    chunk: Chunk
    score: float


def tokenize(text: str) -> list[str]:
    return [token for token in TOKEN_RE.findall(text.lower()) if token not in STOPWORDS]


def markdown_title(text: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else fallback


class KnowledgeIndex:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.chunks: list[Chunk] = []
        self.doc_freq: Counter[str] = Counter()
        self.term_freqs: list[Counter[str]] = []
        self.avg_len = 1.0
        self._build()

    def _build(self) -> None:
        search_root = self.repo_root / "docs" / "platform-kb"
        if not search_root.exists():
            search_root = self.repo_root

        candidates = [
            path
            for path in search_root.rglob("*.md")
            if ".git" not in path.parts
            and "node_modules" not in path.parts
            and ".venv" not in path.parts
        ]
        for path in sorted(candidates):
            rel = path.relative_to(self.repo_root).as_posix()
            text = path.read_text(encoding="utf-8", errors="ignore")
            if not text.strip():
                continue
            for chunk in split_markdown(rel, text):
                tokens = tokenize(chunk.text)
                if not tokens:
                    continue
                self.chunks.append(chunk)
                tf = Counter(tokens)
                self.term_freqs.append(tf)
                self.doc_freq.update(tf.keys())

        if self.term_freqs:
            self.avg_len = sum(sum(tf.values()) for tf in self.term_freqs) / len(
                self.term_freqs
            )

    def search(self, query: str, top_k: int = 3) -> list[SearchHit]:
        query_terms = tokenize(query)
        if not query_terms or not self.chunks:
            return []

        scored: list[SearchHit] = []
        total_docs = len(self.chunks)
        for idx, chunk in enumerate(self.chunks):
            tf = self.term_freqs[idx]
            doc_len = sum(tf.values()) or 1
            score = 0.0
            for term in query_terms:
                freq = tf.get(term, 0)
                if not freq:
                    continue
                idf = math.log(
                    1
                    + (total_docs - self.doc_freq[term] + 0.5)
                    / (self.doc_freq[term] + 0.5)
                )
                denom = freq + 1.5 * (1 - 0.75 + 0.75 * doc_len / self.avg_len)
                score += idf * ((freq * 2.5) / denom)

            heading_bonus = sum(
                0.35 for term in query_terms if term in tokenize(chunk.heading)
            )
            path_bonus = sum(0.2 for term in query_terms if term in tokenize(chunk.path))
            score += heading_bonus + path_bonus
            if score > 0:
                scored.append(SearchHit(chunk=chunk, score=round(score, 4)))

        return sorted(scored, key=lambda hit: hit.score, reverse=True)[:top_k]


def split_markdown(path: str, text: str) -> list[Chunk]:
    title = markdown_title(text, Path(path).stem)
    matches = list(HEADING_RE.finditer(text))
    if not matches:
        return [Chunk(path=path, heading=title, text=text.strip(), url=source_url(path))]

    chunks: list[Chunk] = []
    for index, match in enumerate(matches):
        if match.group(1) == "#" and len(matches) > 1:
            continue
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        heading = match.group(2).strip()
        if heading.lower().startswith("related source links"):
            continue
        body = text[start:end].strip()
        if body:
            chunks.append(
                Chunk(
                    path=path,
                    heading=f"{title} - {heading}",
                    text=f"{title}\n{body}",
                    url=source_url(path),
                )
            )
    return chunks


def source_url(path: str) -> str:
    return f"https://github.com/davidmarkgardiner/kagent-public/blob/main/{path}"
