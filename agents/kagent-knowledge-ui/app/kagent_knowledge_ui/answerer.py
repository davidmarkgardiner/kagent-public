from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from .config import Settings
from .retriever import KnowledgeIndex, SearchHit, tokenize


SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+-\s+|\n+\d+\.\s+")


@dataclass(frozen=True)
class Source:
    path: str
    heading: str
    url: str
    score: float


@dataclass(frozen=True)
class Answer:
    question: str
    answer: str
    confidence: float
    fallback: bool
    ticket_url: str
    sources: list[Source]

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["sources"] = [asdict(source) for source in self.sources]
        return data


class GroundedAnswerer:
    def __init__(self, index: KnowledgeIndex, settings: Settings):
        self.index = index
        self.settings = settings

    def answer(self, question: str) -> Answer:
        hits = self.index.search(question, top_k=self.settings.top_k)
        if not hits or hits[0].score < self.settings.min_score:
            return Answer(
                question=question,
                answer=(
                    "Sorry, we couldn't help solve your problem. "
                    "Please raise a ticket here."
                ),
                confidence=0.0,
                fallback=True,
                ticket_url=self.settings.ticket_url,
                sources=[],
            )

        steps = build_steps(question, hits)
        sources = [
            Source(
                path=hit.chunk.path,
                heading=hit.chunk.heading,
                url=hit.chunk.url,
                score=hit.score,
            )
            for hit in hits
        ]
        confidence = min(0.98, round(hits[0].score / 7.0, 2))
        answer = "\n".join(steps)
        return Answer(
            question=question,
            answer=answer,
            confidence=confidence,
            fallback=False,
            ticket_url=self.settings.ticket_url,
            sources=sources,
        )


def build_steps(question: str, hits: list[SearchHit]) -> list[str]:
    query_terms = set(tokenize(question))
    lines = [f"Use this documented path for: {question.strip()}"]
    selected: list[tuple[str, str]] = []

    for hit in hits:
        for sentence in candidate_sentences(hit.chunk.text):
            sentence_terms = set(tokenize(sentence))
            if query_terms & sentence_terms or len(selected) < 2:
                cleaned = clean_sentence(sentence)
                if cleaned and (cleaned, hit.chunk.path) not in selected:
                    selected.append((cleaned, hit.chunk.path))
            if len(selected) >= 5:
                break
        if len(selected) >= 5:
            break

    if not selected:
        selected.append((clean_sentence(hits[0].chunk.text[:260]), hits[0].chunk.path))

    for index, (sentence, path) in enumerate(selected[:5], start=1):
        lines.append(f"{index}. {sentence} [{path}]")

    lines.append("Sources:")
    for source in unique_paths(hits):
        lines.append(f"- {source.chunk.path} ({source.chunk.url})")
    return lines


def candidate_sentences(text: str) -> list[str]:
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    lines = text.splitlines()
    if lines and not lines[0].lstrip().startswith("#"):
        text = "\n".join(lines[1:])
    text = re.sub(r"^#+\s+.*$", "", text, flags=re.MULTILINE)
    parts = SENTENCE_RE.split(text)
    return [part.strip(" -\n\t") for part in parts if part.strip()]


def clean_sentence(sentence: str) -> str:
    sentence = re.sub(r"^#+\s*", "", sentence.strip())
    sentence = re.sub(r"\s+", " ", sentence)
    sentence = sentence.replace("`", "")
    if len(sentence) > 230:
        sentence = sentence[:227].rstrip() + "..."
    return sentence


def unique_paths(hits: list[SearchHit]) -> list[SearchHit]:
    seen: set[str] = set()
    unique: list[SearchHit] = []
    for hit in hits:
        if hit.chunk.path not in seen:
            seen.add(hit.chunk.path)
            unique.append(hit)
    return unique
