from __future__ import annotations

import math
from typing import Literal

from application.services.bible_service import BibleService
from domain.character import Character
from domain.structure.storyline import StorylineNode
from domain.world_setting import WorldSetting
from infrastructure.persistence.storyline_repo import StorylineRepository

GraphType = Literal["characters", "geography", "rules", "plot"]

_GEOGRAPHY_HINTS = (
    "geography",
    "location",
    "place",
    "city",
    "region",
    "realm",
    "world",
    "地理",
    "地点",
    "地图",
    "城池",
    "秘境",
    "遗迹",
    "势力",
    "主城",
)

_RULE_HINTS = (
    "rule",
    "rules",
    "system",
    "law",
    "restriction",
    "limit",
    "magic",
    "cultivation",
    "culture",
    "规则",
    "体系",
    "法则",
    "限制",
    "核心",
    "进阶",
    "衍生",
)


def _circle_layout(count: int, radius: float = 200.0) -> list[dict[str, float]]:
    positions = []
    for i in range(count):
        angle = (i / count) * math.pi * 2 - math.pi / 2
        positions.append({"x": math.cos(angle) * radius, "y": math.sin(angle) * radius})
    return positions


def _infer_character_type(role: str) -> str:
    r = role.lower()
    if "主角" in role or "主人公" in role or "protagonist" in r or "lead" in r:
        return "protagonist"
    if "敌" in role or "反" in role or "反派" in role or "villain" in r or "enemy" in r or "opponent" in r:
        return "enemy"
    if "友" in role or "盟" in role or "同伴" in role or "ally" in r or "friend" in r or "companion" in r:
        return "ally"
    return "neutral"


def _infer_setting_type(setting_type: str, graph_type: GraphType) -> str:
    t = setting_type.lower()
    if graph_type == "geography":
        if "派" in setting_type or "宗" in setting_type or "盟" in setting_type or "faction" in t or "sect" in t or "clan" in t:
            return "faction"
        return "location"
    return "rule"


def _matches_type(setting_type: str, graph_type: GraphType) -> bool:
    t = setting_type.lower()
    hints = _GEOGRAPHY_HINTS if graph_type == "geography" else _RULE_HINTS
    return any(hint in t for hint in hints)


def _node_dict(
    node_id: str,
    name: str,
    role: str,
    node_type: str,
    identity: str,
    description: str,
    x: float,
    y: float,
    chapters: int = 0,
) -> dict:
    return {
        "id": node_id,
        "name": name,
        "role": role,
        "type": node_type,
        "identity": identity,
        "description": description,
        "connections": 0,
        "chapters": chapters,
        "x": x,
        "y": y,
    }


def _edge_dict(from_id: str, to_id: str, label: str, edge_type: str) -> dict:
    return {
        "from": from_id,
        "to": to_id,
        "label": label,
        "type": edge_type,
    }


class WorldviewService:
    def __init__(self, bible_service: BibleService, storyline_repo: StorylineRepository):
        self._bible = bible_service
        self._storyline_repo = storyline_repo

    def get_graph(self, novel_id: str, graph_type: GraphType) -> dict:
        if not novel_id:
            return {"nodes": [], "edges": []}
        if graph_type == "characters":
            return self._build_characters(novel_id)
        if graph_type == "geography":
            return self._build_settings(novel_id, "geography")
        if graph_type == "rules":
            return self._build_settings(novel_id, "rules")
        if graph_type == "plot":
            return self._build_plot(novel_id)
        return {"nodes": [], "edges": []}

    def _build_characters(self, novel_id: str) -> dict:
        characters = self._bible.list_characters(novel_id)
        if not characters:
            return {"nodes": [], "edges": []}

        typed = [(c, _infer_character_type(c.role)) for c in characters]
        protagonist = next((c for c, t in typed if t == "protagonist"), characters[0])

        positions = _circle_layout(len(characters), 200)
        nodes = []
        for i, (c, t) in enumerate(typed):
            identity = (c.description or c.personality or "")[:60]
            nodes.append(
                _node_dict(
                    node_id=c.id,
                    name=c.name,
                    role=c.role,
                    node_type=t,
                    identity=identity,
                    description=c.description,
                    x=positions[i]["x"],
                    y=positions[i]["y"],
                )
            )

        edges = []
        for c, t in typed:
            if c.id == protagonist.id:
                continue
            if t == "enemy":
                edge_type = "opposite"
                label = "对立"
            elif t == "ally":
                edge_type = "intimate"
                label = "同盟"
            else:
                edge_type = "causal"
                label = "关联"
            edges.append(_edge_dict(protagonist.id, c.id, label, edge_type))

        return self._attach_connections(nodes, edges)

    def _build_settings(self, novel_id: str, graph_type: GraphType) -> dict:
        settings = self._bible.list_settings(novel_id)
        filtered = [s for s in settings if _matches_type(s.setting_type, graph_type)]
        if not filtered:
            return {"nodes": [], "edges": []}

        positions = _circle_layout(len(filtered), 200)
        nodes = []
        for i, s in enumerate(filtered):
            node_type = _infer_setting_type(s.setting_type, graph_type)
            nodes.append(
                _node_dict(
                    node_id=s.id,
                    name=s.name,
                    role=s.setting_type,
                    node_type=node_type,
                    identity=(s.description or "")[:60],
                    description=s.description,
                    x=positions[i]["x"],
                    y=positions[i]["y"],
                )
            )

        node_ids = {n["id"] for n in nodes}
        edges = []
        for i in range(len(filtered) - 1):
            edges.append(
                _edge_dict(
                    filtered[i].id,
                    filtered[i + 1].id,
                    "相邻" if graph_type == "geography" else "派生",
                    "weak" if graph_type == "geography" else "causal",
                )
            )
        for s in filtered:
            if s.parent_id and s.parent_id in node_ids:
                edges.append(
                    _edge_dict(
                        s.parent_id,
                        s.id,
                        "统属" if graph_type == "geography" else "派生",
                        "causal",
                    )
                )

        return self._attach_connections(nodes, edges)

    def _build_plot(self, novel_id: str) -> dict:
        plot_nodes = self._storyline_repo.list_nodes_by_novel(novel_id)
        if not plot_nodes:
            return {"nodes": [], "edges": []}

        nodes = []
        for n in plot_nodes:
            node_type = "plot" if n.node_type == "milestone" else "event"
            nodes.append(
                _node_dict(
                    node_id=n.id,
                    name=n.title,
                    role=n.node_type,
                    node_type=node_type,
                    identity=(n.description or "")[:60],
                    description=n.description,
                    x=n.x or 0,
                    y=n.y or 0,
                    chapters=n.chapter_index or 0,
                )
            )

        edges = []
        for n in plot_nodes:
            for child_id in n.child_ids or []:
                edges.append(_edge_dict(n.id, child_id, "推进", "causal"))

        return self._attach_connections(nodes, edges)

    @staticmethod
    def _attach_connections(nodes: list[dict], edges: list[dict]) -> dict:
        for node in nodes:
            node["connections"] = sum(
                1 for e in edges if e["from"] == node["id"] or e["to"] == node["id"]
            )
        return {"nodes": nodes, "edges": edges}
