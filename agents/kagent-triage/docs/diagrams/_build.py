#!/usr/bin/env python3
"""Generate polished landscape Excalidraw diagrams for the K8s Event Triage project.

v3 — landscape layouts that fit a 16:9 slide canvas without scrolling, plus
the same visual polish as v2 (bound arrows, tinted zones, drop shadows,
title/subtitle hierarchy, line-style semantics).
"""

from __future__ import annotations
import json
import os
from dataclasses import dataclass
from typing import Literal, Optional

OUT = os.path.dirname(os.path.abspath(__file__))


# ---- Palette ----------------------------------------------------------------
COLORS = {
    "frontend":   ("#a5d8ff", "#1971c2"),
    "backend":    ("#d0bfff", "#7048e8"),
    "agent":      ("#ffd6a5", "#e8590c"),
    "gateway":    ("#ffa8a8", "#c92a2a"),
    "queue":      ("#fff3bf", "#fab005"),
    "db":         ("#b2f2bb", "#2f9e44"),
    "external":   ("#ffc9c9", "#e03131"),
    "users":      ("#e7f5ff", "#1971c2"),
    "decision":   ("#ffd8a8", "#e8590c"),
    "neutral":    ("#f1f3f5", "#495057"),
    "approve":    ("#b2f2bb", "#2f9e44"),
    "reject":     ("#ffc9c9", "#e03131"),
    "edit":       ("#a5d8ff", "#1971c2"),
    "lgtm":       ("#e599f7", "#9c36b5"),
    "platform":   ("#ffe8cc", "#fd7e14"),
}

ZONE_TINTS = {
    "mgmt":   "#f3f0ff",
    "worker": "#e7f5ff",
    "pod":    "#fff4e6",
}


# ---- Box / arrow data -------------------------------------------------------
@dataclass
class Box:
    id: str
    title: str
    subtitle: str = ""
    x: int = 0
    y: int = 0
    w: int = 240
    h: int = 90
    color: str = "neutral"
    stroke_w: int = 2
    stroke_style: str = "solid"
    shape: Literal["rectangle", "ellipse"] = "rectangle"
    shadow: bool = False


@dataclass
class Group:
    id: str
    label: str
    x: int
    y: int
    w: int
    h: int
    tint: str = "mgmt"


@dataclass
class Arrow:
    id: str
    src: str
    src_edge: Literal["top", "bottom", "left", "right"]
    dst: str
    dst_edge: Literal["top", "bottom", "left", "right"]
    label: Optional[str] = None
    color: str = "#495057"
    style: Literal["solid", "dashed", "dotted"] = "solid"
    src_offset: float = 0.5
    dst_offset: float = 0.5


# ---- JSON building ----------------------------------------------------------
_seed = 0
def _next_seed():
    global _seed
    _seed += 1
    return _seed


def _required_props(seed: int):
    return {
        "angle": 0,
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "seed": seed,
        "version": 1,
        "versionNonce": seed,
        "isDeleted": False,
        "updated": 1,
        "link": None,
        "locked": False,
    }


# Excalidraw fontFamily: 1 = Virgil (the playful default).
FONT_FAMILY = 1


def shape_element(box: Box) -> dict:
    bg, stroke = COLORS[box.color]
    seed = _next_seed()
    bound = [{"type": "text", "id": f"{box.id}-title"}]
    if box.subtitle:
        bound.append({"type": "text", "id": f"{box.id}-sub"})
    elem = {
        "id": box.id,
        "type": box.shape,
        "x": box.x,
        "y": box.y,
        "width": box.w,
        "height": box.h,
        "strokeColor": stroke,
        "backgroundColor": bg,
        "boundElements": bound,
        "roundness": {"type": 3 if box.shape == "rectangle" else 2},
        **_required_props(seed),
    }
    elem["strokeWidth"] = box.stroke_w
    elem["strokeStyle"] = box.stroke_style
    return elem


def shadow_element(box: Box) -> dict:
    seed = _next_seed()
    return {
        "id": f"{box.id}-shadow",
        "type": box.shape,
        "x": box.x + 6,
        "y": box.y + 6,
        "width": box.w,
        "height": box.h,
        "strokeColor": "transparent",
        "backgroundColor": "#000000",
        "boundElements": None,
        "roundness": {"type": 3 if box.shape == "rectangle" else 2},
        **_required_props(seed),
        "opacity": 12,
        "strokeWidth": 0,
    }


def title_text(box: Box) -> dict:
    seed = _next_seed()
    has_sub = bool(box.subtitle)
    text_h = 26
    title_y = box.y + 12 if has_sub else box.y + (box.h - text_h) // 2
    return {
        "id": f"{box.id}-title",
        "type": "text",
        "x": box.x + 5,
        "y": title_y,
        "width": box.w - 10,
        "height": text_h,
        "strokeColor": "#1e1e1e",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "roundness": None,
        "seed": seed,
        "version": 1,
        "versionNonce": seed,
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
        "text": box.title,
        "fontSize": 18,
        "fontFamily": FONT_FAMILY,
        "textAlign": "center",
        "verticalAlign": "middle",
        "baseline": 14,
        "containerId": box.id,
        "originalText": box.title,
        "lineHeight": 1.25,
    }


def subtitle_text(box: Box) -> Optional[dict]:
    if not box.subtitle:
        return None
    seed = _next_seed()
    line_count = box.subtitle.count("\n") + 1
    text_h = 18 * line_count
    sub_y = box.y + box.h - text_h - 10
    return {
        "id": f"{box.id}-sub",
        "type": "text",
        "x": box.x + 5,
        "y": sub_y,
        "width": box.w - 10,
        "height": text_h,
        "strokeColor": "#1e1e1e",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "roundness": None,
        "seed": seed,
        "version": 1,
        "versionNonce": seed,
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
        "text": box.subtitle,
        "fontSize": 13,
        "fontFamily": FONT_FAMILY,
        "textAlign": "center",
        "verticalAlign": "middle",
        "baseline": 11,
        "containerId": box.id,
        "originalText": box.subtitle,
        "lineHeight": 1.3,
    }


def group_elements(g: Group) -> list[dict]:
    bg_seed = _next_seed()
    border_seed = _next_seed()
    label_seed = _next_seed()
    out = [
        {
            "id": f"{g.id}-bg",
            "type": "rectangle",
            "x": g.x,
            "y": g.y,
            "width": g.w,
            "height": g.h,
            "strokeColor": "transparent",
            "backgroundColor": ZONE_TINTS.get(g.tint, "#f8f9fa"),
            "fillStyle": "solid",
            "strokeWidth": 0,
            "strokeStyle": "solid",
            "roughness": 0,
            "opacity": 60,
            "groupIds": [],
            "frameId": None,
            "roundness": {"type": 3},
            "seed": bg_seed,
            "version": 1,
            "versionNonce": bg_seed,
            "isDeleted": False,
            "boundElements": None,
            "updated": 1,
            "link": None,
            "locked": False,
        },
        {
            "id": g.id,
            "type": "rectangle",
            "x": g.x,
            "y": g.y,
            "width": g.w,
            "height": g.h,
            "strokeColor": "#9c36b5",
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "strokeWidth": 2,
            "strokeStyle": "dashed",
            "roughness": 0,
            "opacity": 100,
            "groupIds": [],
            "frameId": None,
            "roundness": {"type": 3},
            "seed": border_seed,
            "version": 1,
            "versionNonce": border_seed,
            "isDeleted": False,
            "boundElements": None,
            "updated": 1,
            "link": None,
            "locked": False,
        },
        {
            "id": f"{g.id}-label",
            "type": "text",
            "x": g.x + 16,
            "y": g.y + 12,
            "width": g.w - 32,
            "height": 26,
            "strokeColor": "#9c36b5",
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "strokeWidth": 1,
            "strokeStyle": "solid",
            "roughness": 1,
            "opacity": 100,
            "groupIds": [],
            "frameId": None,
            "roundness": None,
            "seed": label_seed,
            "version": 1,
            "versionNonce": label_seed,
            "isDeleted": False,
            "boundElements": None,
            "updated": 1,
            "link": None,
            "locked": False,
            "text": g.label,
            "fontSize": 20,
            "fontFamily": FONT_FAMILY,
            "textAlign": "left",
            "verticalAlign": "top",
            "baseline": 16,
            "containerId": None,
            "originalText": g.label,
            "lineHeight": 1.2,
        },
    ]
    return out


def edge_point(box: Box, edge: str, offset: float = 0.5) -> tuple[int, int]:
    if edge == "top":
        return (box.x + int(box.w * offset), box.y)
    if edge == "bottom":
        return (box.x + int(box.w * offset), box.y + box.h)
    if edge == "left":
        return (box.x, box.y + int(box.h * offset))
    if edge == "right":
        return (box.x + box.w, box.y + int(box.h * offset))
    raise ValueError(edge)


def _focus(offset: float) -> float:
    return (offset - 0.5) * 2


def arrow_element(arrow: Arrow, boxes: dict[str, Box]) -> list[dict]:
    src = boxes[arrow.src]
    dst = boxes[arrow.dst]
    sx, sy = edge_point(src, arrow.src_edge, arrow.src_offset)
    dx, dy = edge_point(dst, arrow.dst_edge, arrow.dst_offset)

    if arrow.src_edge in ("top", "bottom") and arrow.dst_edge in ("top", "bottom"):
        mid_y = (sy + dy) // 2
        points = [(0, 0), (0, mid_y - sy), (dx - sx, mid_y - sy), (dx - sx, dy - sy)]
    elif arrow.src_edge in ("left", "right") and arrow.dst_edge in ("left", "right"):
        mid_x = (sx + dx) // 2
        points = [(0, 0), (mid_x - sx, 0), (mid_x - sx, dy - sy), (dx - sx, dy - sy)]
    else:
        if arrow.src_edge in ("left", "right"):
            points = [(0, 0), (dx - sx, 0), (dx - sx, dy - sy)]
        else:
            points = [(0, 0), (0, dy - sy), (dx - sx, dy - sy)]

    seed = _next_seed()
    arr = {
        "id": arrow.id,
        "type": "arrow",
        "x": sx,
        "y": sy,
        "width": max(abs(p[0]) for p in points) or 1,
        "height": max(abs(p[1]) for p in points) or 1,
        "strokeColor": arrow.color,
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": arrow.style,
        "roughness": 0,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "roundness": None,
        "seed": seed,
        "version": 1,
        "versionNonce": seed,
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
        "points": [list(p) for p in points],
        "lastCommittedPoint": None,
        "startBinding": {
            "elementId": arrow.src,
            "focus": _focus(arrow.src_offset),
            "gap": 6,
        },
        "endBinding": {
            "elementId": arrow.dst,
            "focus": _focus(arrow.dst_offset),
            "gap": 6,
        },
        "startArrowhead": None,
        "endArrowhead": "arrow",
        "elbowed": True,
        "angle": 0,
    }

    out = [arr]

    for bid in (arrow.src, arrow.dst):
        b = boxes[bid]
        b.__dict__.setdefault("_extra_bound", []).append(
            {"type": "arrow", "id": arrow.id})

    if arrow.label:
        mid_idx = max(0, len(points) // 2 - 1)
        midx, midy = points[mid_idx]
        nextx, nexty = points[min(mid_idx + 1, len(points) - 1)]
        lx = sx + (midx + nextx) // 2 + 8
        ly = sy + (midy + nexty) // 2 - 22
        label_seed = _next_seed()
        line_count = arrow.label.count("\n") + 1
        out.append({
            "id": f"{arrow.id}-label",
            "type": "text",
            "x": lx,
            "y": ly,
            "width": max(60, max(len(L) for L in arrow.label.split("\n")) * 7),
            "height": 18 * line_count,
            "strokeColor": arrow.color,
            "backgroundColor": "#ffffff",
            "fillStyle": "solid",
            "strokeWidth": 1,
            "strokeStyle": "solid",
            "roughness": 1,
            "opacity": 100,
            "groupIds": [],
            "frameId": None,
            "roundness": None,
            "seed": label_seed,
            "version": 1,
            "versionNonce": label_seed,
            "isDeleted": False,
            "boundElements": None,
            "updated": 1,
            "link": None,
            "locked": False,
            "text": arrow.label,
            "fontSize": 12,
            "fontFamily": FONT_FAMILY,
            "textAlign": "left",
            "verticalAlign": "top",
            "baseline": 11,
            "containerId": None,
            "originalText": arrow.label,
            "lineHeight": 1.25,
        })
    return out


def build(boxes: list[Box], arrows: list[Arrow], groups: list[Group] | None = None) -> dict:
    elements = []
    if groups:
        for g in groups:
            elements.extend(group_elements(g))

    for b in boxes:
        if b.shadow:
            elements.append(shadow_element(b))

    for b in boxes:
        b.__dict__["_extra_bound"] = []

    box_map = {b.id: b for b in boxes}

    arrow_elems = []
    for a in arrows:
        arrow_elems.extend(arrow_element(a, box_map))

    for b in boxes:
        rect = shape_element(b)
        rect["boundElements"] = (rect.get("boundElements") or []) + b._extra_bound
        elements.append(rect)
        elements.append(title_text(b))
        sub = subtitle_text(b)
        if sub:
            elements.append(sub)

    elements.extend(arrow_elems)

    return {
        "type": "excalidraw",
        "version": 2,
        "source": "claude-code-excalidraw-skill",
        "elements": elements,
        "appState": {
            "gridSize": 20,
            "viewBackgroundColor": "#ffffff",
        },
        "files": {},
    }


def write_diagram(name: str, doc: dict):
    path = os.path.join(OUT, name)
    with open(path, "w") as f:
        json.dump(doc, f, indent=2)
    print(f"wrote {path}  ({len(doc['elements'])} elements)")


# =============================================================================
# DIAGRAM 1 — Management cluster + worker clusters topology (LANDSCAPE)
#
# Layout: two clusters side-by-side, each compacted into 2 internal columns.
# Total canvas ~ 1900 × 760  (approx 16:9 once SVG export adds padding).
# =============================================================================
def diagram_1():
    global _seed
    _seed = 0

    boxes = [
        # ── MGMT cluster — left column (col A) ──
        Box("argo-events", "Argo Events", "EventBus · EventSource\nSensors per tier",
            80, 110, 280, 100, "backend", shadow=True),
        Box("argo-wf", "Argo Workflows", "k8s-triage-critical\nwarnings · infra",
            80, 240, 280, 100, "backend", shadow=True),
        Box("kagent-mgmt", "kagent system agents", "infra · network · cost\nobservability · incident · compliance",
            80, 370, 280, 100, "agent", shadow=True),
        Box("gitops-rem", "gitops-remediation-agent", "(future)",
            80, 500, 280, 75, "agent", stroke_style="dashed"),

        # ── MGMT cluster — right column (col B) ──
        Box("agentgw", "agentgateway", "LLM proxy · MCP & A2A gateway\nUAMI · OTel · guardrails",
            390, 240, 300, 100, "gateway", shadow=True),
        Box("aks-mcp", "AKS-MCP", "UAMI cross-cluster kubectl",
            390, 370, 300, 100, "platform"),
        Box("azure-openai", "Azure OpenAI", "via UAMI / workload identity",
            390, 500, 300, 75, "external"),

        # ── Middle bridge — Event Hub ──
        Box("eh", "Azure Event Hub", "topics:\nk8s-events  ·  alerts",
            760, 260, 240, 130, "queue", shadow=True),

        # ── WORKER cluster — left column ──
        Box("worker-alloy", "Alloy", "events · logs · metrics · traces",
            1080, 110, 320, 100, "frontend", shadow=True),
        Box("worker-kagent", "Worker-local kagent\nspecialists", "cert-manager · kyverno · kro\nexternal-secrets · monitoring",
            1080, 240, 320, 100, "agent", shadow=True),
        Box("worker-ns", "App + system namespaces", "generates K8s warning events",
            1080, 370, 320, 100, "neutral"),
        Box("worker-k8s", "Worker K8s API server", "",
            1080, 500, 320, 75, "neutral"),

        # ── WORKER cluster — right column ──
        Box("lgtm", "Managed LGTM", "Mimir · Loki · Tempo",
            1430, 240, 280, 130, "lgtm", shape="ellipse", shadow=True),
    ]

    groups = [
        Group("g-mgmt", "MANAGEMENT  CLUSTER", 40, 70, 670, 535, tint="mgmt"),
        Group("g-worker", "WORKER  CLUSTERS  (1..N)", 1040, 70, 720, 535, tint="worker"),
    ]

    arrows = [
        Arrow("a1", "worker-alloy", "left", "eh", "right", "Kafka/TLS\nSAS Send", "#fab005",
              src_offset=0.5, dst_offset=0.3),
        Arrow("a2", "eh", "left", "argo-events", "right", "Kafka/TLS\nSAS Listen", "#fab005",
              src_offset=0.5, dst_offset=0.5),
        Arrow("a3", "argo-events", "bottom", "argo-wf", "top", color="#7048e8"),
        Arrow("a4", "argo-wf", "bottom", "kagent-mgmt", "top", "A2A JSON-RPC", "#7048e8"),
        Arrow("a5", "kagent-mgmt", "right", "agentgw", "left", color="#e8590c"),
        Arrow("a6", "agentgw", "bottom", "aks-mcp", "top", color="#c92a2a", style="dashed"),
        Arrow("a7", "aks-mcp", "right", "worker-k8s", "left", "UAMI · workload identity", "#fd7e14",
              src_offset=0.5, dst_offset=0.4),
        Arrow("a8", "agentgw", "right", "azure-openai", "right", "UAMI", "#c92a2a",
              src_offset=0.95, dst_offset=0.5),
        Arrow("a9", "kagent-mgmt", "bottom", "gitops-rem", "top", color="#e8590c", style="dotted"),
        Arrow("a10", "worker-alloy", "right", "lgtm", "top", "remote_write\nloki.write · OTLP", "#9c36b5",
              src_offset=0.5, dst_offset=0.4),
    ]
    return build(boxes, arrows, groups)


# =============================================================================
# DIAGRAM 2 — Triage flow (LANDSCAPE — 3 horizontal rows)
# =============================================================================
def diagram_2():
    global _seed
    _seed = 0

    boxes = [
        # ── Row 1: pipeline ingest (top) ──
        Box("evt", "K8s Warning Event", "type=Warning",
            60, 80, 200, 80, "external", shadow=True),
        Box("alloy", "Alloy", "kubernetes_events",
            290, 80, 200, 80, "frontend"),
        Box("eh", "Azure Event Hub", "topic: k8s-events",
            520, 80, 200, 80, "queue"),
        Box("es", "EventSource", "Kafka consumer",
            750, 80, 180, 80, "backend"),
        Box("sn", "Sensor", "rate-limited",
            960, 80, 160, 80, "backend"),
        Box("parse", "parse-otlp", "extract ns + reason",
            1150, 80, 200, 80, "backend"),
        Box("router", "Router", "namespace · reason\nelse default",
            1380, 80, 220, 90, "decision", stroke_style="dashed"),

        # Routing CMs above the router
        Box("ns-cm", "namespace-routes", "ConfigMap",
            1380, 0, 200, 60, "db"),
        Box("rn-cm", "reason-routes", "ConfigMap",
            1600, 0, 200, 60, "db"),

        # ── Row 2: kagent agent pod (middle, horizontal) ──
        Box("a2a", "A2A POST", "/api/a2a/kagent/<agent>/",
            60, 280, 220, 100, "agent", shadow=True),
        Box("ag-prompt", "System prompt + skills", "/skills mounted",
            340, 290, 240, 90, "agent"),
        Box("ag-mem", "load_memory", "→ pgvector",
            620, 290, 200, 90, "db"),
        Box("ag-tools", "MCP tools", "kagent-tool-server\nAKS-MCP",
            860, 290, 220, 90, "platform"),
        Box("ag-llm", "LLM call", "→ agentgateway\n→ Azure OpenAI",
            1130, 290, 240, 90, "gateway"),
        Box("diag", "Diagnosis JSON", "Issue · Cause · Fix · Risk",
            1420, 280, 240, 100, "backend", shadow=True),

        # ── Row 3: severity + outputs (bottom) ──
        Box("sev", "Severity router", "critical → HITL\nwarnings → direct",
            60, 480, 240, 100, "decision", stroke_style="dashed"),
        Box("save", "save_memory", "incident summary",
            340, 490, 200, 90, "db"),
        Box("hitl", "HITL gate", "writes / remediation",
            580, 490, 220, 90, "gateway"),
        Box("direct", "Direct ticket", "read-only triage",
            840, 490, 220, 90, "backend"),
        Box("gitlab", "GitLab issue", "round-robin assigned",
            1100, 490, 200, 90, "users"),
        Box("teams", "Teams card", "Adaptive Card",
            1330, 490, 240, 90, "users"),
    ]

    groups = [
        Group("g-pod", "kagent  agent  pod  (per-request)",
              330, 270, 1050, 130, tint="pod"),
    ]

    arrows = [
        # row 1
        Arrow("d2-1", "evt", "right", "alloy", "left"),
        Arrow("d2-2", "alloy", "right", "eh", "left"),
        Arrow("d2-3", "eh", "right", "es", "left"),
        Arrow("d2-4", "es", "right", "sn", "left"),
        Arrow("d2-5", "sn", "right", "parse", "left"),
        Arrow("d2-6", "parse", "right", "router", "left"),
        Arrow("d2-7", "ns-cm", "bottom", "router", "top",
              color="#2f9e44", src_offset=0.5, dst_offset=0.3),
        Arrow("d2-8", "rn-cm", "bottom", "router", "top",
              color="#2f9e44", src_offset=0.5, dst_offset=0.7),
        # router → agent pod
        Arrow("d2-9", "router", "bottom", "a2a", "top", color="#e8590c",
              src_offset=0.5, dst_offset=0.5),
        # row 2 (inside pod)
        Arrow("d2-10", "a2a", "right", "ag-prompt", "left"),
        Arrow("d2-pod1", "ag-prompt", "right", "ag-mem", "left"),
        Arrow("d2-pod2", "ag-mem", "right", "ag-tools", "left"),
        Arrow("d2-pod3", "ag-tools", "right", "ag-llm", "left"),
        Arrow("d2-pod4", "ag-llm", "right", "diag", "left"),
        # row 2 → row 3
        Arrow("d2-11", "diag", "bottom", "sev", "top",
              src_offset=0.5, dst_offset=0.5),
        Arrow("d2-12", "diag", "bottom", "save", "top",
              color="#2f9e44", src_offset=0.2, dst_offset=0.5, style="dashed"),
        # severity branches
        Arrow("d2-13a", "sev", "right", "hitl", "left", color="#c92a2a"),
        Arrow("d2-13b", "hitl", "right", "direct", "left", color="#7048e8", style="dashed"),
        Arrow("d2-14a", "hitl", "right", "gitlab", "left", color="#c92a2a",
              src_offset=0.95, dst_offset=0.5),
        Arrow("d2-14b", "direct", "right", "teams", "left",
              src_offset=0.95, dst_offset=0.5),
    ]
    return build(boxes, arrows, groups)


# =============================================================================
# DIAGRAM 3 — HITL approval flow (LANDSCAPE — main flow horizontal)
# =============================================================================
def diagram_3():
    global _seed
    _seed = 0

    boxes = [
        # Top row — initial flow
        Box("triage", "Triage agent", "diagnosis + suggested fix",
            60, 80, 280, 100, "agent", shadow=True),
        Box("suspend", "Workflow Suspend", "paused · awaits callback",
            390, 80, 280, 100, "decision", stroke_w=3, stroke_style="dashed", shadow=True),
        Box("teams", "Teams Adaptive Card", "via Logic App webhook",
            720, 80, 280, 100, "users", shadow=True),

        # Middle row — three branches
        Box("approve", "Approve", "",
            60, 240, 200, 70, "approve", shadow=True),
        Box("reject", "Reject", "",
            290, 240, 200, 70, "reject", shadow=True),
        Box("edit", "Edit", "",
            520, 240, 200, 70, "edit", shadow=True),

        # Branch detail row
        Box("hmac", "HMAC callback", "POST + workflow token",
            60, 350, 200, 80, "platform"),
        Box("rej-act", "Resume", "approved=false",
            290, 350, 200, 80, "neutral"),
        Box("edit-act", "Re-prompt agent", "human-modified text",
            520, 350, 200, 80, "neutral"),

        # Approve-path horizontal flow (right side)
        Box("istio", "Istio VS + AuthZ", "HMAC verify",
            290, 470, 200, 90, "platform"),
        Box("callback", "Argo Events webhook", "EventSource on resume",
            520, 470, 220, 90, "backend"),
        Box("resume", "Sensor resumes", "approved=true",
            770, 470, 200, 90, "backend"),
        Box("remed", "Remediation agent", "controlled patch / scale",
            1000, 470, 280, 90, "agent", shadow=True),
        Box("verify", "Verify", "resource recovered",
            1310, 470, 200, 90, "backend"),

        # Reject convergence
        Box("ticket-only", "Ticket only", "no remediation",
            290, 620, 280, 80, "users"),

        # Final close (right end, big)
        Box("close", "GitLab issue updated", "with outcome + resolution",
            1120, 620, 390, 100, "users", shadow=True),
    ]

    arrows = [
        # Top row
        Arrow("h-1", "triage", "right", "suspend", "left"),
        Arrow("h-2", "suspend", "right", "teams", "left"),
        # Branches
        Arrow("h-3a", "teams", "bottom", "approve", "top", color="#2f9e44",
              src_offset=0.2, dst_offset=0.5),
        Arrow("h-3b", "teams", "bottom", "reject", "top", color="#e03131",
              src_offset=0.5, dst_offset=0.5),
        Arrow("h-3c", "teams", "bottom", "edit", "top", color="#1971c2",
              src_offset=0.8, dst_offset=0.5),
        # Branch detail
        Arrow("h-4a", "approve", "bottom", "hmac", "top", color="#2f9e44"),
        Arrow("h-4b", "reject", "bottom", "rej-act", "top", color="#e03131"),
        Arrow("h-4c", "edit", "bottom", "edit-act", "top", color="#1971c2"),
        # Edit loop back to triage
        Arrow("h-5c", "edit-act", "left", "triage", "right", "back to triage",
              "#1971c2", style="dashed", src_offset=0.5, dst_offset=0.7),
        # Approve path (horizontal across the bottom)
        Arrow("h-6", "hmac", "right", "istio", "left", color="#2f9e44"),
        Arrow("h-7", "istio", "right", "callback", "left", color="#2f9e44"),
        Arrow("h-8", "callback", "right", "resume", "left", color="#2f9e44"),
        Arrow("h-9", "resume", "right", "remed", "left", color="#2f9e44"),
        Arrow("h-10", "remed", "right", "verify", "left", color="#2f9e44"),
        Arrow("h-11", "verify", "bottom", "close", "top", color="#2f9e44",
              src_offset=0.5, dst_offset=0.5),
        # Reject path → ticket-only → close
        Arrow("h-12", "rej-act", "bottom", "ticket-only", "top", color="#e03131"),
        Arrow("h-13", "ticket-only", "right", "close", "left", color="#e03131",
              style="dashed", src_offset=0.5, dst_offset=0.5),
    ]
    return build(boxes, arrows)


# =============================================================================
# DIAGRAM 4 — "What good looks like" end-to-end journey + mind-map of inputs
#
# Mind-map style: a horizontal journey spine across the middle, with
# fan-outs below showing what each phase USES (skills, tools, memory, LLM, A2A,
# HITL inputs, callback chain, downstream agents) and fan-outs above showing
# what GOOD looks like at close (tickets resolved, memory updated, LGTM clean).
#
# Total canvas: ~2400 × 1100. Lands on a single landscape slide.
# =============================================================================
def diagram_4():
    global _seed
    _seed = 0

    Y_SPINE = 520

    boxes = [
        # ───── Main journey spine (left to right) ─────
        Box("evt", "1 · Event", "K8s Warning · CronWorkflow\nor manual trigger",
            60, Y_SPINE, 220, 110, "external", shadow=True),
        Box("agent", "2 · Triage Agent", "selectors decide\nwhich specialist picks it up",
            340, Y_SPINE, 280, 110, "agent", shadow=True),
        Box("decide", "3 · Can fix?", "diagnose → recommend\nremediation",
            680, Y_SPINE, 220, 110, "decision", stroke_w=3, stroke_style="dashed", shadow=True),
        Box("hitl", "4 · HITL Gate", "Teams Adaptive Card\nApprove · Reject · Edit",
            960, Y_SPINE, 280, 110, "users", shadow=True),
        Box("callback", "5 · Callback", "press-gang return\nIstio HMAC verify",
            1300, Y_SPINE, 220, 110, "platform", shadow=True),
        Box("dispatch", "6 · Dispatch", "incident-agent routes\nto the right specialist",
            1580, Y_SPINE, 260, 110, "agent", shadow=True),
        Box("lgtm", "7 · LGTM Close", "everything green\nincident closed",
            1900, Y_SPINE, 280, 110, "approve", shadow=True),

        # ───── Phase 2 — What the Triage Agent uses (BELOW) ─────
        Box("p2-skills", "Skills", "/skills mounted\nvia skills-init",
            60, 720, 200, 80, "agent"),
        Box("p2-tools", "Tools (MCP)", "kagent-tool-server\nAKS-MCP cross-cluster",
            280, 720, 200, 80, "platform"),
        Box("p2-memory", "Memory", "load_memory\n→ pgvector",
            500, 720, 200, 80, "db"),
        Box("p2-llm", "LLM call", "→ agentgateway\n→ Azure OpenAI (UAMI)",
            720, 720, 240, 80, "gateway"),
        Box("p2-a2a", "A2A comms", "agent-as-tool\ncall other agents",
            980, 720, 220, 80, "backend"),
        Box("p2-prompt", "System prompt", "+ ConfigMap context\n+ namespace anchor",
            1220, 720, 220, 80, "neutral"),

        # ───── Phase 4 — HITL details (BELOW) ─────
        Box("p4-approve", "Approve", "remediation runs",
            960, 850, 90, 70, "approve"),
        Box("p4-reject", "Reject", "ticket only",
            1060, 850, 90, 70, "reject"),
        Box("p4-edit", "Edit", "re-prompt agent",
            1160, 850, 90, 70, "edit"),

        # ───── Phase 5 — Callback chain (BELOW) ─────
        Box("p5-istio", "Istio AuthZ", "verify HMAC token",
            1300, 850, 220, 70, "platform"),

        # ───── Phase 6 — Dispatch fans to 3 downstream agents (BELOW) ─────
        Box("p6-remed", "Remediation agent", "patch · scale · restart",
            1480, 980, 220, 80, "agent"),
        Box("p6-gitops", "GitOps agent", "branch + MR\nFlux applies",
            1720, 980, 220, 80, "agent"),
        Box("p6-incident", "Incident MCP", "ServiceNow · ADO\nGitLab issue",
            1960, 980, 220, 80, "users"),

        # ───── Phase 7 — What GOOD looks like (ABOVE LGTM) ─────
        Box("good-1", "✓ Incident closed", "ticket resolved",
            60, 60, 220, 70, "approve"),
        Box("good-2", "✓ GitLab issue", "marked resolved",
            300, 60, 220, 70, "approve"),
        Box("good-3", "✓ Memory updated", "save_memory(...)",
            540, 60, 220, 70, "approve"),
        Box("good-4", "✓ Teams notified", "Adaptive Card update",
            780, 60, 220, 70, "approve"),
        Box("good-5", "✓ LGTM observability", "no anomaly alerts",
            1020, 60, 220, 70, "approve"),
        Box("good-6", "✓ No rogue agent", "no unauthorised access",
            1260, 60, 220, 70, "approve"),
        Box("good-summary", "WHAT GOOD LOOKS LIKE", "humans informed · cluster healthy\nlearning loop closed",
            1900, 200, 280, 110, "lgtm", shadow=True),
    ]

    groups = [
        Group("g-uses", "WHAT  THE  AGENT  USES",
              40, 690, 1420, 140, tint="pod"),
        Group("g-good", "WHAT  GOOD  LOOKS  LIKE  (LGTM)",
              40, 30, 1500, 120, tint="worker"),
    ]

    arrows = [
        # Main journey spine
        Arrow("j-1", "evt", "right", "agent", "left"),
        Arrow("j-2", "agent", "right", "decide", "left"),
        Arrow("j-3", "decide", "right", "hitl", "left"),
        Arrow("j-4", "hitl", "right", "callback", "left", color="#2f9e44"),
        Arrow("j-5", "callback", "right", "dispatch", "left", color="#2f9e44"),
        Arrow("j-6", "dispatch", "right", "lgtm", "left", color="#2f9e44"),

        # Agent → uses (fan down)
        Arrow("u-1", "agent", "bottom", "p2-skills", "top",
              color="#e8590c", style="dashed", src_offset=0.1, dst_offset=0.5),
        Arrow("u-2", "agent", "bottom", "p2-tools", "top",
              color="#fd7e14", style="dashed", src_offset=0.3, dst_offset=0.5),
        Arrow("u-3", "agent", "bottom", "p2-memory", "top",
              color="#2f9e44", style="dashed", src_offset=0.5, dst_offset=0.5),
        Arrow("u-4", "agent", "bottom", "p2-llm", "top",
              color="#c92a2a", style="dashed", src_offset=0.7, dst_offset=0.5),
        Arrow("u-5", "agent", "bottom", "p2-a2a", "top",
              color="#7048e8", style="dashed", src_offset=0.9, dst_offset=0.5),
        Arrow("u-6", "decide", "bottom", "p2-prompt", "top",
              color="#495057", style="dashed", src_offset=0.5, dst_offset=0.5),

        # HITL → 3 buttons
        Arrow("h-a", "hitl", "bottom", "p4-approve", "top",
              color="#2f9e44", src_offset=0.2, dst_offset=0.5),
        Arrow("h-r", "hitl", "bottom", "p4-reject", "top",
              color="#e03131", src_offset=0.5, dst_offset=0.5),
        Arrow("h-e", "hitl", "bottom", "p4-edit", "top",
              color="#1971c2", src_offset=0.8, dst_offset=0.5),
        Arrow("h-back", "p4-edit", "left", "agent", "bottom",
              "back to triage", "#1971c2", style="dashed",
              src_offset=0.5, dst_offset=0.85),

        # Callback chain
        Arrow("cb-1", "callback", "bottom", "p5-istio", "top", color="#2f9e44",
              src_offset=0.5, dst_offset=0.5),

        # Dispatch fans to 3 downstream agents
        Arrow("d-r", "dispatch", "bottom", "p6-remed", "top",
              color="#e8590c", src_offset=0.2, dst_offset=0.5),
        Arrow("d-g", "dispatch", "bottom", "p6-gitops", "top",
              color="#7048e8", src_offset=0.5, dst_offset=0.5),
        Arrow("d-i", "dispatch", "bottom", "p6-incident", "top",
              color="#1971c2", src_offset=0.8, dst_offset=0.5),

        # Downstream agents → LGTM close
        Arrow("close-r", "p6-remed", "right", "lgtm", "bottom",
              color="#2f9e44", src_offset=0.5, dst_offset=0.2),
        Arrow("close-g", "p6-gitops", "right", "lgtm", "bottom",
              color="#2f9e44", src_offset=0.5, dst_offset=0.5),
        Arrow("close-i", "p6-incident", "top", "lgtm", "bottom",
              color="#2f9e44", src_offset=0.5, dst_offset=0.8),

        # LGTM → goods (fan up)
        Arrow("g-1", "lgtm", "top", "good-1", "bottom",
              color="#2f9e44", src_offset=0.05, dst_offset=0.5),
        Arrow("g-2", "lgtm", "top", "good-2", "bottom",
              color="#2f9e44", src_offset=0.2, dst_offset=0.5),
        Arrow("g-3", "lgtm", "top", "good-3", "bottom",
              color="#2f9e44", src_offset=0.4, dst_offset=0.5),
        Arrow("g-4", "lgtm", "top", "good-4", "bottom",
              color="#2f9e44", src_offset=0.6, dst_offset=0.5),
        Arrow("g-5", "lgtm", "top", "good-5", "bottom",
              color="#2f9e44", src_offset=0.8, dst_offset=0.5),
        Arrow("g-6", "lgtm", "top", "good-6", "bottom",
              color="#2f9e44", src_offset=0.95, dst_offset=0.5),

        # Summary
        Arrow("g-sum", "lgtm", "right", "good-summary", "left", color="#9c36b5"),

        # Learning loop — memory feeds back to next event
        Arrow("loop", "p2-memory", "left", "evt", "bottom",
              "learning loop · next event\nstarts smarter",
              "#9c36b5", style="dashed", src_offset=0.5, dst_offset=0.3),
    ]
    return build(boxes, arrows, groups)


# =============================================================================
# DIAGRAM 5 — "Pod crashes in production" — stakeholder architecture journey
#
# Combines the END-TO-END journey with the COMPONENT MAP showing:
#   • The kagent runtime as a central zone with multiple agents inside
#   • Tools/skills/memory/model loading explicitly shown
#   • A2A communications between specific agents
#   • External APIs called BY the agents:  AKS-MCP, Teams (HITL), ServiceNow,
#     GitLab — drawn outside the kagent boundary
#   • Argo Workflow orchestrating the whole thing
#
# Reads top-to-bottom-then-right with a clear narrative numbering 1..10.
# =============================================================================
def diagram_5():
    global _seed
    _seed = 0

    # Layout — 4 horizontal rows, single left-to-right reading order:
    #   Row 0 (y=20-160):   "What the Triage Agent loads" mind-map
    #   Row 1 (y=200-380):  KAGENT RUNTIME — main agent journey spine
    #   Row 2 (y=520-660):  External APIs reached over the network
    #   Row 3 (y=720-820):  External targets behind the APIs
    # Canvas: ~3000 wide × 880 tall (fits in a wide landscape slide).

    Y_LOADS = 60
    Y_AGENTS = 260
    Y_API = 540
    Y_TARGET = 740

    boxes = [
        # ═════════ ROW 0 — what the triage agent loads ═════════
        Box("u-skills", "Skills", "git-mounted\n/skills bundle",
            760, Y_LOADS, 180, 100, "agent"),
        Box("u-tools", "Tools (MCP)", "k8s reads · logs\ndescribe · events",
            960, Y_LOADS, 180, 100, "platform"),
        Box("u-memory", "Memory", "load_memory\n→ pgvector",
            1160, Y_LOADS, 180, 100, "db"),
        Box("u-model", "Model", "picked per task\nvia agentgateway",
            1360, Y_LOADS, 200, 100, "gateway"),

        # ═════════ ROW 1 — main agent journey (kagent runtime spine) ═════════
        Box("evt", "1 · Pod crashes", "CrashLoopBackOff",
            60, Y_AGENTS, 200, 120, "external", shadow=True),
        Box("argo", "2 · Argo Workflow", "event triggers\ntriage pipeline",
            280, Y_AGENTS, 200, 120, "backend", shadow=True),
        Box("ticket-agent", "3 · Ticket agent", "opens GitLab ticket\n+ ServiceNow incident",
            500, Y_AGENTS, 220, 120, "agent", shadow=True),
        Box("triage", "4 · Triage agent", "assigned · runs analysis\n(loads ↑)",
            740, Y_AGENTS, 240, 120, "agent", shadow=True),
        Box("analysis", "5 · Decide", "engage agents\nengage human",
            1000, Y_AGENTS, 200, 120, "decision",
            stroke_w=3, stroke_style="dashed", shadow=True),
        Box("specialists", "Other specialist agents (A2A)", "cert-manager · network · storage · security · …",
            740, Y_AGENTS + 160, 460, 70, "agent"),
        Box("hitl", "6 · HITL approval", "Approve · Reject · Edit\n(Teams Adaptive Card)",
            1220, Y_AGENTS, 240, 120, "users",
            stroke_w=3, stroke_style="dashed", shadow=True),
        Box("gitops-up", "7a · GitOps agent", "branches Git\nopens MR",
            1480, Y_AGENTS - 60, 220, 100, "agent", shadow=True),
        Box("fix-agent", "7b · Fix agent", "patches · scales\nrestarts",
            1480, Y_AGENTS + 60, 220, 100, "agent", shadow=True),
        Box("testing", "8 · Testing agent", "verifies\nrecovery",
            1720, Y_AGENTS, 200, 120, "backend", shadow=True),
        Box("close-agent", "9 · Closure agents", "GitLab close + ServiceNow close",
            1940, Y_AGENTS - 60, 280, 100, "agent", shadow=True),
        Box("notify", "10 · Notification agent", "posts to Teams channel",
            1940, Y_AGENTS + 60, 280, 100, "agent", shadow=True),
        Box("done", "ALL CLEAR  ✓", "tickets closed\ncluster healthy · LGTM green",
            2240, Y_AGENTS, 280, 160, "approve", shadow=True),

        # ═════════ ROW 2 — external APIs reached from kagent ═════════
        Box("aks-mcp", "AKS-MCP", "cross-cluster kubectl\nUAMI / workload identity",
            60, Y_API, 240, 120, "platform", shadow=True),
        Box("teams-svc", "Teams Logic App", "Adaptive Card webhook\nposts updates",
            340, Y_API, 240, 120, "users", shadow=True),
        Box("snow-api", "ServiceNow API", "incident open / update / close",
            620, Y_API, 240, 120, "users", shadow=True),
        Box("gitlab-api", "GitLab API", "issues + merge requests",
            900, Y_API, 240, 120, "users", shadow=True),
        Box("git-api", "Git repo (GitOps)", "branch · commit · MR\nFlux applies later",
            1180, Y_API, 240, 120, "platform", shadow=True),

        # ═════════ ROW 3 — what's reached behind the APIs ═════════
        Box("workers", "Worker clusters", "1..N production AKS",
            60, Y_TARGET, 240, 80, "neutral"),
        Box("human", "Human approver", "in Teams channel",
            340, Y_TARGET, 240, 80, "users"),
        Box("snow-tenant", "ServiceNow tenant", "incident records",
            620, Y_TARGET, 240, 80, "neutral"),
        Box("gitlab-prj", "GitLab project", "tickets · MRs",
            900, Y_TARGET, 240, 80, "neutral"),
        Box("flux", "Flux + cluster", "applies the fix",
            1180, Y_TARGET, 240, 80, "neutral"),
    ]

    groups = [
        Group("g-loads", "WHAT  THE  TRIAGE  AGENT  LOADS",
              740, 30, 840, 130, tint="pod"),
        Group("g-kagent",
              "KAGENT  RUNTIME  —  agents collaborate via A2A; orchestrated by Argo Workflows",
              40, 230, 2500, 270, tint="mgmt"),
        Group("g-ext",
              "EXTERNAL  APIs  +  TARGETS  —  reached from kagent over the network",
              40, 510, 1400, 320, tint="worker"),
    ]

    arrows = [
        # ── Triage loads (down-arrows from row 0 into triage) ──
        Arrow("l-skills", "u-skills", "bottom", "triage", "top",
              color="#e8590c", style="dashed", src_offset=0.5, dst_offset=0.15),
        Arrow("l-tools", "u-tools", "bottom", "triage", "top",
              color="#fd7e14", style="dashed", src_offset=0.5, dst_offset=0.4),
        Arrow("l-memory", "u-memory", "bottom", "triage", "top",
              color="#2f9e44", style="dashed", src_offset=0.5, dst_offset=0.65),
        Arrow("l-model", "u-model", "bottom", "triage", "top",
              color="#c92a2a", style="dashed", src_offset=0.5, dst_offset=0.85),

        # ── Main row spine ──
        Arrow("s-1", "evt", "right", "argo", "left"),
        Arrow("s-2", "argo", "right", "ticket-agent", "left"),
        Arrow("s-3", "ticket-agent", "right", "triage", "left"),
        Arrow("s-4", "triage", "right", "analysis", "left"),
        Arrow("s-5", "analysis", "right", "hitl", "left"),
        Arrow("s-6a", "hitl", "right", "gitops-up", "left", "approved",
              "#2f9e44", src_offset=0.5, dst_offset=0.5),
        Arrow("s-6b", "hitl", "right", "fix-agent", "left", "approved",
              "#2f9e44", src_offset=0.5, dst_offset=0.5),
        Arrow("s-7a", "gitops-up", "right", "testing", "left",
              color="#7048e8", src_offset=0.5, dst_offset=0.3),
        Arrow("s-7b", "fix-agent", "right", "testing", "left",
              color="#e8590c", src_offset=0.5, dst_offset=0.7),
        Arrow("s-8a", "testing", "right", "close-agent", "left",
              color="#2f9e44", src_offset=0.5, dst_offset=0.5),
        Arrow("s-8b", "testing", "right", "notify", "left",
              color="#1971c2", src_offset=0.5, dst_offset=0.5),
        Arrow("s-9a", "close-agent", "right", "done", "left",
              color="#2f9e44", src_offset=0.5, dst_offset=0.3),
        Arrow("s-9b", "notify", "right", "done", "left",
              color="#2f9e44", src_offset=0.5, dst_offset=0.7),

        # ── A2A — triage to specialists, decision back into specialists ──
        Arrow("a2a-1", "triage", "bottom", "specialists", "top",
              "A2A", "#7048e8", src_offset=0.5, dst_offset=0.3),
        Arrow("a2a-2", "specialists", "right", "analysis", "bottom",
              color="#7048e8", style="dashed",
              src_offset=0.95, dst_offset=0.3),

        # ── External API calls FROM the kagent runtime ──
        Arrow("e-snow", "ticket-agent", "bottom", "snow-api", "top",
              "create incident", "#1971c2",
              src_offset=0.6, dst_offset=0.5),
        Arrow("e-gitlab", "ticket-agent", "bottom", "gitlab-api", "top",
              "open ticket", "#1971c2",
              src_offset=0.95, dst_offset=0.3),
        Arrow("e-mcp-spec", "specialists", "bottom", "aks-mcp", "top",
              "kubectl reads", "#fd7e14",
              src_offset=0.1, dst_offset=0.7),
        Arrow("e-teams-hitl", "hitl", "bottom", "teams-svc", "top",
              "Adaptive Card", "#1971c2",
              src_offset=0.3, dst_offset=0.7),
        Arrow("e-git", "gitops-up", "bottom", "git-api", "top",
              "branch + MR", "#7048e8",
              src_offset=0.5, dst_offset=0.7),
        Arrow("e-mcp-fix", "fix-agent", "bottom", "aks-mcp", "top",
              "patch · scale", "#e8590c",
              src_offset=0.05, dst_offset=0.3),
        Arrow("e-snow-close", "close-agent", "bottom", "snow-api", "top",
              "close", "#2f9e44",
              src_offset=0.05, dst_offset=0.7),
        Arrow("e-gitlab-close", "close-agent", "bottom", "gitlab-api", "top",
              "close", "#2f9e44",
              src_offset=0.5, dst_offset=0.7),
        Arrow("e-teams-notify", "notify", "bottom", "teams-svc", "top",
              "post outcome", "#1971c2",
              src_offset=0.05, dst_offset=0.3),

        # ── External APIs → real targets ──
        Arrow("t-mcp", "aks-mcp", "bottom", "workers", "top", color="#fd7e14"),
        Arrow("t-teams", "teams-svc", "bottom", "human", "top", color="#1971c2"),
        Arrow("t-snow", "snow-api", "bottom", "snow-tenant", "top", color="#1971c2"),
        Arrow("t-gitlab", "gitlab-api", "bottom", "gitlab-prj", "top", color="#1971c2"),
        Arrow("t-flux", "git-api", "bottom", "flux", "top", color="#7048e8"),
    ]
    return build(boxes, arrows, groups)


# =============================================================================
# Helpers for diagram 6 — annotated emoji story
# =============================================================================
def comic_phase(id_prefix: str, x: int, y: int, emoji: str, num: str,
                title: str, annotation: str, color: str = "neutral") -> list:
    """Build a 'comic-strip' phase: emoji + step number + title + annotation.

    Returns a list of elements to add directly to the elements list.
    Bypasses the standard Box renderer because we want a bigger emoji
    and a separate sticky-note-style annotation below.
    """
    bg, stroke = COLORS[color]
    out = []

    # Card container
    seed = _next_seed()
    out.append({
        "id": f"{id_prefix}-card",
        "type": "rectangle",
        "x": x, "y": y, "width": 220, "height": 220,
        "strokeColor": stroke, "backgroundColor": bg,
        "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
        "roughness": 1, "opacity": 100,
        "groupIds": [], "frameId": None,
        "roundness": {"type": 3},
        "seed": seed, "version": 1, "versionNonce": seed, "isDeleted": False,
        "boundElements": None, "updated": 1, "link": None, "locked": False,
    })

    # Drop shadow (offset behind card)
    sh_seed = _next_seed()
    out.insert(0, {
        "id": f"{id_prefix}-sh",
        "type": "rectangle",
        "x": x + 6, "y": y + 6, "width": 220, "height": 220,
        "strokeColor": "transparent", "backgroundColor": "#000000",
        "fillStyle": "solid", "strokeWidth": 0, "strokeStyle": "solid",
        "roughness": 0, "opacity": 12,
        "groupIds": [], "frameId": None,
        "roundness": {"type": 3},
        "seed": sh_seed, "version": 1, "versionNonce": sh_seed, "isDeleted": False,
        "boundElements": None, "updated": 1, "link": None, "locked": False,
    })

    # Big emoji (at the top of the card)
    emoji_seed = _next_seed()
    out.append({
        "id": f"{id_prefix}-emoji",
        "type": "text",
        "x": x + 5, "y": y + 14, "width": 210, "height": 48,
        "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
        "roughness": 0, "opacity": 100,
        "groupIds": [], "frameId": None, "roundness": None,
        "seed": emoji_seed, "version": 1, "versionNonce": emoji_seed,
        "isDeleted": False, "boundElements": None, "updated": 1,
        "link": None, "locked": False,
        "text": emoji,
        "fontSize": 40, "fontFamily": FONT_FAMILY,
        "textAlign": "center", "verticalAlign": "middle",
        "baseline": 32,
        "containerId": None, "originalText": emoji, "lineHeight": 1.2,
    })

    # Step number badge
    num_seed = _next_seed()
    out.append({
        "id": f"{id_prefix}-num",
        "type": "text",
        "x": x + 5, "y": y + 78, "width": 210, "height": 22,
        "strokeColor": "#ff6b1a", "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
        "roughness": 0, "opacity": 100,
        "groupIds": [], "frameId": None, "roundness": None,
        "seed": num_seed, "version": 1, "versionNonce": num_seed,
        "isDeleted": False, "boundElements": None, "updated": 1,
        "link": None, "locked": False,
        "text": f"STEP  {num}",
        "fontSize": 14, "fontFamily": FONT_FAMILY,
        "textAlign": "center", "verticalAlign": "middle",
        "baseline": 12,
        "containerId": None, "originalText": f"STEP  {num}", "lineHeight": 1.2,
    })

    # Title
    title_seed = _next_seed()
    out.append({
        "id": f"{id_prefix}-title",
        "type": "text",
        "x": x + 8, "y": y + 105, "width": 204, "height": 30,
        "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
        "roughness": 1, "opacity": 100,
        "groupIds": [], "frameId": None, "roundness": None,
        "seed": title_seed, "version": 1, "versionNonce": title_seed,
        "isDeleted": False, "boundElements": None, "updated": 1,
        "link": None, "locked": False,
        "text": title,
        "fontSize": 18, "fontFamily": FONT_FAMILY,
        "textAlign": "center", "verticalAlign": "middle",
        "baseline": 14,
        "containerId": None, "originalText": title, "lineHeight": 1.25,
    })

    # Annotation
    line_count = annotation.count("\n") + 1
    ann_h = 18 * line_count
    ann_seed = _next_seed()
    out.append({
        "id": f"{id_prefix}-ann",
        "type": "text",
        "x": x + 10, "y": y + 220 - ann_h - 14, "width": 200, "height": ann_h,
        "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
        "roughness": 1, "opacity": 100,
        "groupIds": [], "frameId": None, "roundness": None,
        "seed": ann_seed, "version": 1, "versionNonce": ann_seed,
        "isDeleted": False, "boundElements": None, "updated": 1,
        "link": None, "locked": False,
        "text": annotation,
        "fontSize": 13, "fontFamily": FONT_FAMILY,
        "textAlign": "center", "verticalAlign": "middle",
        "baseline": 11,
        "containerId": None, "originalText": annotation, "lineHeight": 1.3,
    })

    return out


def sticky_note(id_prefix: str, x: int, y: int, w: int, h: int,
                text: str, color: str = "#fff4e6") -> list:
    """Yellow sticky-note style annotation that hangs off the diagram."""
    note_seed = _next_seed()
    text_seed = _next_seed()
    return [
        {
            "id": f"{id_prefix}-note",
            "type": "rectangle",
            "x": x, "y": y, "width": w, "height": h,
            "strokeColor": "#fab005", "backgroundColor": color,
            "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
            "roughness": 2, "opacity": 100,
            "groupIds": [], "frameId": None,
            "roundness": None,
            "seed": note_seed, "version": 1, "versionNonce": note_seed,
            "isDeleted": False, "boundElements": None, "updated": 1,
            "link": None, "locked": False,
            "angle": -0.05,
        },
        {
            "id": f"{id_prefix}-note-text",
            "type": "text",
            "x": x + 8, "y": y + 8, "width": w - 16, "height": h - 16,
            "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
            "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
            "roughness": 1, "opacity": 100,
            "groupIds": [], "frameId": None, "roundness": None,
            "seed": text_seed, "version": 1, "versionNonce": text_seed,
            "isDeleted": False, "boundElements": None, "updated": 1,
            "link": None, "locked": False,
            "text": text,
            "fontSize": 13, "fontFamily": FONT_FAMILY,
            "textAlign": "left", "verticalAlign": "top",
            "baseline": 11,
            "containerId": None, "originalText": text, "lineHeight": 1.3,
            "angle": -0.05,
        },
    ]


# =============================================================================
# DIAGRAM 6 — Annotated emoji story · "fun" version of the journey
# =============================================================================
def diagram_6():
    global _seed
    _seed = 0

    # 12 phases · 2 rows of 6 · each card 220×220 · gap 60
    GAP = 60
    CARD = 220
    Y_TOP = 120
    Y_BOT = 480

    # Row 1 phases (left → right)
    phases_top = [
        ("p1",  "💥", "1",  "Pod crashes",       "production cluster\nCrashLoopBackOff",       "external"),
        ("p2",  "⚡", "2",  "Event triggers",    "kubelet → K8s API\nWarning event fires",     "queue"),
        ("p3",  "🔄", "3",  "Argo picks it up",  "EventSource → Sensor\nWorkflow starts",      "backend"),
        ("p4",  "🎫", "4",  "Tickets opened",    "GitLab issue\n+ ServiceNow incident",         "users"),
        ("p5",  "🧠", "5",  "Triage agent",      "loads skills · tools\nmemory · model",        "agent"),
        ("p6",  "🤔", "6",  "Analysis",          "diagnoses root cause\ndecides next step",     "decision"),
    ]
    # Row 2 phases (left → right)
    phases_bot = [
        ("p7",  "🤝", "7",  "Human approval",    "Teams Adaptive Card\nApprove · Reject · Edit","users"),
        ("p8",  "🛠️", "8",  "Fix is applied",    "GitOps MR + cluster\npatch · scale",          "agent"),
        ("p9",  "🧪", "9",  "Tests verify",      "Testing agent confirms\nrecovery",            "backend"),
        ("p10", "✅", "10", "Tickets closed",    "GitLab + ServiceNow\nresolved",               "approve"),
        ("p11", "📢", "11", "Teams notified",    "channel updated\noutcome posted",             "users"),
        ("p12", "🎉", "12", "ALL CLEAR",         "cluster healthy\nLGTM green · sleep tight",   "approve"),
    ]

    elements = []

    # Title row
    title_seed = _next_seed()
    elements.append({
        "id": "doc-title", "type": "text",
        "x": 60, "y": 30, "width": 1700, "height": 50,
        "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
        "roughness": 1, "opacity": 100,
        "groupIds": [], "frameId": None, "roundness": None,
        "seed": title_seed, "version": 1, "versionNonce": title_seed,
        "isDeleted": False, "boundElements": None, "updated": 1,
        "link": None, "locked": False,
        "text": "Pod crashes in production · the 12-step happy path · with mechanics",
        "fontSize": 32, "fontFamily": FONT_FAMILY,
        "textAlign": "left", "verticalAlign": "top",
        "baseline": 26,
        "containerId": None,
        "originalText": "Pod crashes in production · the 12-step happy path · with mechanics",
        "lineHeight": 1.2, "angle": 0,
    })

    # Build rows
    for i, (pid, emoji, num, title, ann, color) in enumerate(phases_top):
        x = 60 + i * (CARD + GAP)
        elements.extend(comic_phase(pid, x, Y_TOP, emoji, num, title, ann, color))
    for i, (pid, emoji, num, title, ann, color) in enumerate(phases_bot):
        # Reverse the bottom row so the snake reads naturally:
        # we go right→left on the bottom row, ending at "ALL CLEAR" on the left.
        # Actually, easier reading: keep left→right but draw a curving wrap arrow
        # from p6 (top-right) down to p7 (bottom-left).
        x = 60 + i * (CARD + GAP)
        elements.extend(comic_phase(pid, x, Y_BOT, emoji, num, title, ann, color))

    # ───── TOOLS / MCP row at the bottom ─────
    Y_TOOLS = 800
    tools = [
        ("aks-mcp",   "☸",  "AKS-MCP",        "login · get logs · get events\nexec commands on cluster",  "platform"),
        ("teams-mcp", "💬",  "Teams Logic App", "Adaptive Card webhook\nhuman approve · reject",            "users"),
        ("gitlab-mcp","🐙",  "GitLab MCP",      "open · update · close\ntickets · MRs",                     "users"),
        ("snow-mcp",  "📋",  "ServiceNow MCP",  "open · update · close\nincidents",                          "users"),
        ("git-mcp",   "📦",  "Git MCP",         "branch · commit · MR\nFlux applies later",                  "platform"),
    ]
    for i, (tid, emoji, title, ann, color) in enumerate(tools):
        x = 60 + i * (CARD + GAP)
        elements.extend(comic_phase(tid, x, Y_TOOLS, emoji, "MCP", title, ann, color))

    # Sticky-note annotations to call out the special bits
    elements.extend(sticky_note(
        "note-loads", 1370, 60, 240, 80,
        "💡 The triage agent is\nspecialised — different\nagents pick up cert-mgr,\nstorage, network, etc.",
    ))
    elements.extend(sticky_note(
        "note-iterate", 1100, 380, 280, 80,
        "💬 Iterate: agent uses AKS-MCP\nto fetch logs, describe pods,\nbuild picture · updates ticket\nas it goes.",
    ))
    elements.extend(sticky_note(
        "note-ask", 1370, 380, 280, 80,
        '🔒 "I think I can fix it but I\nneed to run a command that\'s\nnot on my allow-list — can you\napprove?"',
    ))
    elements.extend(sticky_note(
        "note-hitl", 70, 380, 220, 80,
        "🔒 No write hits the\ncluster without a human\nclick. HITL is the gate.",
    ))
    elements.extend(sticky_note(
        "note-run", 360, 720, 240, 80,
        '🔧 Approved → remediation\nagent calls AKS-MCP again:\n"run THIS command on\nthat cluster".',
    ))
    elements.extend(sticky_note(
        "note-verify", 660, 720, 240, 80,
        "🔍 Verify: agent re-checks\nlogs via AKS-MCP — confirms\nthe fix actually worked\nbefore moving on.",
    ))
    elements.extend(sticky_note(
        "note-gitops", 700, 1040, 240, 80,
        "📦 Fix can also be committed\nto Git FIRST via Git MCP →\nFlux applies. Classic GitOps.",
    ))
    elements.extend(sticky_note(
        "note-good", 1370, 1040, 280, 100,
        "🎯 GOOD looks like:\nincident closed · tickets resolved\nteams informed · LGTM observability\nclean · no rogue agents.",
    ))

    # Spine arrows (curved between cards)
    arrow_color = "#7048e8"
    arrows = []

    def make_arrow(arr_id, src_x, src_y, dx, dy, color="#495057",
                   style="solid", points=None, label=None):
        seed = _next_seed()
        if points is None:
            points = [[0, 0], [dx, dy]]
        arr = {
            "id": arr_id, "type": "arrow",
            "x": src_x, "y": src_y,
            "width": max(abs(p[0]) for p in points) or 1,
            "height": max(abs(p[1]) for p in points) or 1,
            "strokeColor": color, "backgroundColor": "transparent",
            "fillStyle": "solid", "strokeWidth": 3, "strokeStyle": style,
            "roughness": 0, "opacity": 100,
            "groupIds": [], "frameId": None, "roundness": None,
            "seed": seed, "version": 1, "versionNonce": seed,
            "isDeleted": False, "boundElements": None, "updated": 1,
            "link": None, "locked": False,
            "points": points, "lastCommittedPoint": None,
            "startBinding": None, "endBinding": None,
            "startArrowhead": None, "endArrowhead": "arrow",
            "elbowed": False, "angle": 0,
        }
        out = [arr]
        if label:
            label_seed = _next_seed()
            mx = src_x + (points[-1][0]) // 2
            my = src_y + (points[-1][1]) // 2
            out.append({
                "id": f"{arr_id}-label", "type": "text",
                "x": mx + 8, "y": my - 22,
                "width": max(80, len(label) * 8), "height": 18,
                "strokeColor": color, "backgroundColor": "#ffffff",
                "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
                "roughness": 1, "opacity": 100,
                "groupIds": [], "frameId": None, "roundness": None,
                "seed": label_seed, "version": 1, "versionNonce": label_seed,
                "isDeleted": False, "boundElements": None, "updated": 1,
                "link": None, "locked": False,
                "text": label, "fontSize": 12, "fontFamily": FONT_FAMILY,
                "textAlign": "left", "verticalAlign": "top", "baseline": 11,
                "containerId": None, "originalText": label, "lineHeight": 1.25,
                "angle": 0,
            })
        return out

    # Top row arrows (left → right), going between cards horizontally
    for i in range(5):
        x_src = 60 + (i + 1) * CARD + i * GAP
        x_dst_offset = GAP
        arrows.extend(make_arrow(
            f"top-{i}", x_src, Y_TOP + 110, x_dst_offset, 0,
            color=arrow_color))

    # Wrap arrow: from p6 (top, far right) curving DOWN through the gap
    # between rows, then LEFT, then DOWN to land on p7's top edge.
    p6_x = 60 + 5 * (CARD + GAP) + CARD     # right edge of p6 = 1680
    p7_x = 60                                # left edge of p7 = 60
    p7_top_mid = p7_x + CARD // 2            # 170 — where the arrow lands
    delta_x = p7_top_mid - p6_x              # negative — going left
    # Mid-gap between rows: Y_TOP+CARD=340; Y_BOT=480; gap-mid = 410.
    # Arrow path (relative to start at (p6_x, Y_TOP+110)=(1680, 230)):
    arrows.extend(make_arrow(
        "wrap", p6_x, Y_TOP + 110,
        0, 0,  # ignored — using points
        color="#9c36b5", style="dashed",
        points=[
            [0, 0],            # start at right edge of p6, mid-card
            [60, 0],           # right 60
            [60, 180],         # down 180 → mid-gap (y=410)
            [delta_x, 180],    # back left to p7 top-mid x
            [delta_x, 250],    # down 70 → p7's top edge
        ],
        label="next phase ↓"
    ))

    # Bottom row arrows (left → right)
    for i in range(5):
        x_src = 60 + (i + 1) * CARD + i * GAP
        arrows.extend(make_arrow(
            f"bot-{i}", x_src, Y_BOT + 110, GAP, 0,
            color="#2f9e44"))

    # ── Tool / MCP usage arrows — from each bottom-row phase down to the
    # tool layer it calls. Dashed purple to distinguish from the journey spine.
    Y_PHASE_BOT = Y_BOT + CARD     # 700
    TOOL_TOP = 800                  # tools row top
    TOOL_X = {                       # top-mid x of each tool card
        "aks":    170,
        "teams":  450,
        "gitlab": 730,
        "snow":  1010,
        "git":   1290,
    }
    PHASE_BOT_X = {                  # bottom-mid x of each bottom-row phase
        "p7":   170, "p8":  450, "p9":  730, "p10": 1010, "p11": 1290, "p12": 1570,
    }
    tool_links = [
        ("tl-7-teams",   "p7",  "teams",  "Adaptive Card"),
        ("tl-8-aks",     "p8",  "aks",    "exec: run command"),
        ("tl-8-git",     "p8",  "git",    "commit · MR"),
        ("tl-9-aks",     "p9",  "aks",    "verify: get logs"),
        ("tl-10-gitlab", "p10", "gitlab", "close ticket"),
        ("tl-10-snow",   "p10", "snow",   "close incident"),
        ("tl-11-teams",  "p11", "teams",  "post outcome"),
    ]
    for tid, phase, tool, label in tool_links:
        src_x = PHASE_BOT_X[phase]
        dst_x = TOOL_X[tool]
        dy = TOOL_TOP - Y_PHASE_BOT  # 100
        dx = dst_x - src_x
        arrows.extend(make_arrow(
            tid, src_x, Y_PHASE_BOT,
            0, 0,
            color="#7048e8", style="dashed",
            points=[[0, 0], [0, dy // 2], [dx, dy // 2], [dx, dy]],
            label=label,
        ))

    # ── Iteration arrow: triage agent (p5, top row) ↔ AKS-MCP (tool row)
    # Routes around the LEFT side of the bottom row to avoid cutting through
    # any phase card. Shows the back-and-forth conversation with the cluster.
    p5_bot_x = 60 + 4 * (CARD + GAP) + CARD // 2  # 1290 (x mid of p5)
    arrows.extend(make_arrow(
        "iter-aks", p5_bot_x, Y_TOP + CARD,    # start at p5 bottom-mid
        0, 0,
        color="#9c36b5", style="dashed",
        points=[
            [0, 0],
            [0, 70],                            # down into row-gap (y=410)
            [-(p5_bot_x - 40), 70],             # left to x=40 (left of all phases)
            [-(p5_bot_x - 40), 460],            # down to y=800 (tool row top)
            [-(p5_bot_x - TOOL_X["aks"]), 460], # right to AKS-MCP top-mid
        ],
        label="AKS-MCP · login + iterate"
    ))

    elements.extend(arrows)

    return {
        "type": "excalidraw",
        "version": 2,
        "source": "claude-code-excalidraw-skill",
        "elements": elements,
        "appState": {
            "gridSize": 20,
            "viewBackgroundColor": "#ffffff",
        },
        "files": {},
    }


# =============================================================================
if __name__ == "__main__":
    write_diagram("01-mgmt-worker-topology.excalidraw", diagram_1())
    write_diagram("02-triage-flow.excalidraw", diagram_2())
    write_diagram("03-hitl-approval-flow.excalidraw", diagram_3())
    write_diagram("04-good-journey.excalidraw", diagram_4())
    write_diagram("05-pod-crash-stakeholder.excalidraw", diagram_5())
    write_diagram("06-pod-crash-annotated-story.excalidraw", diagram_6())
