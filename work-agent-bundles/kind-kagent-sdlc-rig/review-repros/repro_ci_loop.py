import sys, itertools
sys.path.insert(0, sys.argv[1])
from board_poller import Board
MAIN = "b" * 40
class G:
    def __init__(s):
        s.labels = ["sdlc-rig-poc", "agent:test"]; s.head = "1" * 40; s.n = itertools.count(2); s.t = []
    def child(s, i): return {"iid": 41}
    def issue(s, i): return {"labels": s.labels}
    def transition(s, i, e, d): s.t.append(d); s.labels = ["sdlc-rig-poc", d]; return True
    def post_once(s, *a): pass
    def branch(s, n): return {"commit": {"id": MAIN if n == "main" else s.head}}
    def changed_paths(s, b): return ["README.md"]
    def pipeline(s, b, sha): return {"id": 1, "status": "failed", "sha": sha}
    def pages(s, p): return [{"id": 1, "status": "failed", "sha": s.head}]
    def mr(s, b): return None
    def notes(s, k, i): return []
    def request(s, *a, **k): return {}
g = G(); b = Board(g, "x")
def rework(stage, *a):
    g.head = str(next(g.n) % 10) * 40   # builder always lands a new, still-failing commit
    return "ok"
b.call_pm = rework
for _ in range(30):
    b.process({"iid": 40, "labels": g.labels})
print("30 polls:", len(g.t), "transitions; reached blocked:", "agent:blocked" in g.t, "; last:", g.t[-3:])
