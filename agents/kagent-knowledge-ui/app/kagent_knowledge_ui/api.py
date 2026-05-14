from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .answerer import GroundedAnswerer
from .config import Settings, load_settings
from .git_repo import KnowledgeRepo
from .pr_service import PullRequestService
from .retriever import KnowledgeIndex


class QueryRequest(BaseModel):
    question: str


class FeedbackRequest(BaseModel):
    question: str
    source_path: str | None = None
    reason: str = "User marked the answer as wrong or outdated."
    simulate: bool = False


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    static_dir = Path(__file__).resolve().parents[1] / "static"
    app = FastAPI(title="K-Agent Knowledge UI", version="0.1.0")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    state: dict[str, object] = {}

    def rebuild() -> None:
        repo_root = KnowledgeRepo(settings).sync()
        state["repo_root"] = repo_root
        state["index"] = KnowledgeIndex(repo_root)
        state["answerer"] = GroundedAnswerer(state["index"], settings)
        state["pr_service"] = PullRequestService(repo_root, settings)

    @app.on_event("startup")
    def on_startup() -> None:
        rebuild()

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/healthz")
    def healthz() -> dict[str, object]:
        index_obj = state.get("index")
        return {
            "ok": bool(index_obj),
            "chunks": len(index_obj.chunks) if isinstance(index_obj, KnowledgeIndex) else 0,
        }

    @app.post("/api/query")
    def query(request: QueryRequest) -> dict[str, object]:
        answerer = state.get("answerer")
        if not isinstance(answerer, GroundedAnswerer):
            raise HTTPException(status_code=503, detail="knowledge index is not ready")
        return answerer.answer(request.question).to_dict()

    @app.post("/api/refresh")
    def refresh() -> dict[str, object]:
        rebuild()
        index_obj = state["index"]
        return {"ok": True, "chunks": len(index_obj.chunks)}

    @app.post("/api/feedback")
    def feedback(request: FeedbackRequest) -> dict[str, object]:
        service = state.get("pr_service")
        if not isinstance(service, PullRequestService):
            raise HTTPException(status_code=503, detail="PR service is not ready")
        result = service.open_update_pr(
            question=request.question,
            source_path=request.source_path or "",
            reason=request.reason,
            simulate=request.simulate,
        )
        return {
            "mode": result.mode,
            "branch": result.branch,
            "pr_url": result.pr_url,
            "changed_file": result.changed_file,
            "summary": result.summary,
        }

    return app


app = create_app()

