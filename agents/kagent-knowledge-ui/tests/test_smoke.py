from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kagent_knowledge_ui.answerer import GroundedAnswerer
from kagent_knowledge_ui.config import Settings
from kagent_knowledge_ui.pr_service import PullRequestService
from kagent_knowledge_ui.retriever import KnowledgeIndex


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_settings(evidence_dir: Path) -> Settings:
    return Settings(
        kb_repo_url="local",
        kb_repo_ref="main",
        kb_local_path=str(REPO_ROOT),
        kb_clone_dir=Path("/tmp/not-used"),
        ticket_url="https://linear.app/milano2/issue/MIL-128",
        top_k=3,
        min_score=1.2,
        github_repo="davidmarkgardiner/kagent-public",
        github_base_branch="main",
        evidence_dir=evidence_dir,
    )


class KAgentKnowledgeSmokeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.settings = test_settings(Path(self.tmp.name))
        self.index = KnowledgeIndex(REPO_ROOT)
        self.answerer = GroundedAnswerer(self.index, self.settings)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_required_queries_return_grounded_answers(self) -> None:
        queries = [
            "How do I secure my pod?",
            "How do I bring my own domain?",
            "How do I set up a pod disruption budget?",
            "What Kubernetes resources are available on the shared AKS platform?",
        ]
        for query in queries:
            with self.subTest(query=query):
                answer = self.answerer.answer(query)
                self.assertFalse(answer.fallback)
                self.assertGreater(len(answer.answer), 80)
                self.assertGreaterEqual(len(answer.sources), 1)

    def test_unknown_query_uses_ticket_fallback(self) -> None:
        answer = self.answerer.answer("How do I repair a PostgreSQL vacuum freeze issue?")
        self.assertTrue(answer.fallback)
        self.assertIn("Sorry, we couldn't help solve your problem", answer.answer)
        self.assertIn("MIL-128", answer.ticket_url)

    def test_stale_doc_feedback_can_open_simulated_pr(self) -> None:
        service = PullRequestService(REPO_ROOT, self.settings)
        result = service.open_update_pr(
            question="How do I secure my pod?",
            source_path="docs/platform-kb/aks/pod-security.md",
            reason="The PSP guidance is stale.",
            simulate=True,
        )
        self.assertEqual(result.mode, "simulated")
        self.assertIn("/pull/simulated-mil-128", result.pr_url)
        self.assertTrue((self.settings.evidence_dir / "simulated-stale-doc-pr.json").exists())


if __name__ == "__main__":
    unittest.main()
