"""星渊笔 API 运行时健康检查脚本。

用法：
    python api_check.py [--host HOST] [--port PORT] [--create-fixtures]

退出码：
    0 - 全部通过
    1 - 存在失败
"""

import argparse
import logging
import sys
import time
from typing import Any

import httpx


class ApiChecker:
    """基于 httpx 的 API 检查客户端。"""

    def __init__(self, host: str, port: int, timeout: float = 10.0):
        self.base_url = f"http://{host}:{port}"
        self.client = httpx.Client(base_url=self.base_url, timeout=timeout)
        self.results: list[tuple[str, bool, str]] = []
        self.novel_id: str | None = None
        self.chapter_id: str | None = None

    def _request(self, method: str, path: str, json_data: dict[str, Any] | None = None) -> tuple[int, Any]:
        try:
            response = self.client.request(method, path, json=json_data)
            try:
                body = response.json()
            except Exception:
                body = response.text
            return response.status_code, body
        except httpx.RequestError as exc:
            return 0, f"request error: {exc}"
        except Exception as exc:
            return 0, f"unexpected error: {exc}"

    def get(self, path: str) -> tuple[int, Any]:
        return self._request("GET", path)

    def post(self, path: str, data: dict[str, Any] | None = None) -> tuple[int, Any]:
        return self._request("POST", path, data)

    def put(self, path: str, data: dict[str, Any] | None = None) -> tuple[int, Any]:
        return self._request("PUT", path, data)

    def delete(self, path: str) -> tuple[int, Any]:
        return self._request("DELETE", path)

    def record(self, name: str, ok: bool, detail: str = "") -> None:
        self.results.append((name, ok, detail))
        status = "PASS" if ok else "FAIL"
        if detail:
            print(f"  {status}: {name} - {detail}")
        else:
            print(f"  {status}: {name}")

    def assert_status(self, name: str, status: int, expected: int = 200) -> bool:
        ok = status == expected
        self.record(name, ok, f"status={status}, expected={expected}" if not ok else "")
        return ok

    def assert_field(self, name: str, data: Any, field: str, expected_type: type | tuple[type, ...]) -> bool:
        if not isinstance(data, dict):
            self.record(name, False, f"response is not dict: {type(data)}")
            return False
        if "data" not in data:
            self.record(name, False, "missing 'data' wrapper")
            return False
        inner = data["data"]
        if not isinstance(inner, dict):
            self.record(name, False, f"data is not dict: {type(inner)}")
            return False
        if field not in inner:
            self.record(name, False, f"missing field '{field}'")
            return False
        if not isinstance(inner[field], expected_type):
            self.record(name, False, f"field '{field}' type mismatch")
            return False
        self.record(name, True)
        return True

    def create_fixtures(self) -> bool:
        print("\n[Creating fixtures]")
        timestamp = int(time.time())
        payload = {
            "title": f"API 检查测试小说 {timestamp}",
            "premise": "仅用于运行时检查",
            "genre": "测试",
            "target_chapters": 3,
        }
        status, body = self.post("/api/v1/novels", payload)
        if status != 200 or not isinstance(body, dict) or body.get("code") != 0:
            self.record("create test novel", False, f"status={status}, body={body}")
            return False
        self.novel_id = body["data"]["id"]
        self.record("create test novel", True, f"novel_id={self.novel_id}")

        chapter_payload = {"title": "测试章节", "number": 1}
        status, body = self.post(f"/api/v1/novels/{self.novel_id}/chapters", chapter_payload)
        if status != 200 or not isinstance(body, dict) or body.get("code") != 0:
            self.record("create test chapter", False, f"status={status}, body={body}")
            return False
        self.chapter_id = body["data"]["id"]
        self.record("create test chapter", True, f"chapter_id={self.chapter_id}")
        return True

    def discover_existing_novel(self) -> bool:
        status, body = self.get("/api/v1/novels")
        if status != 200 or not isinstance(body, dict) or body.get("code") != 0:
            return False
        items = body.get("data", [])
        if items:
            self.novel_id = items[0]["id"]
            return True
        return False

    def cleanup_fixtures(self) -> None:
        if self.chapter_id:
            self.delete(f"/api/v1/chapters/{self.chapter_id}")
        if self.novel_id:
            self.delete(f"/api/v1/novels/{self.novel_id}")

    def run_health_checks(self) -> None:
        print("\n[1. Health]")
        status, body = self.get("/health")
        self.assert_status("GET /health", status)

    def run_novel_checks(self) -> None:
        print("\n[2. Novels]")
        if not self.novel_id:
            print("  SKIP: no novel available")
            return

        status, body = self.get("/api/v1/novels")
        self.assert_status("GET /api/v1/novels", status)

        status, body = self.get(f"/api/v1/novels/{self.novel_id}")
        self.assert_status("GET novel detail", status)
        self.assert_field("novel detail has id", body, "id", str)
        self.assert_field("novel detail has title", body, "title", str)

        status, body = self.get(f"/api/v1/novels/{self.novel_id}/stats")
        self.assert_status("GET novel stats", status)

    def run_chapter_checks(self) -> None:
        print("\n[3. Chapters]")
        if not self.novel_id:
            print("  SKIP: no novel available")
            return

        status, body = self.get(f"/api/v1/novels/{self.novel_id}/chapters")
        self.assert_status("GET chapters list", status)

        if self.chapter_id:
            status, body = self.get(f"/api/v1/chapters/{self.chapter_id}")
            self.assert_status("GET chapter detail", status)
            self.assert_field("chapter detail has id", body, "id", str)
            self.assert_field("chapter detail has novel_id", body, "novel_id", str)

            status, body = self.post(f"/api/v1/chapters/{self.chapter_id}/generate-outline")
            self.assert_status("POST generate-outline", status)

    def run_character_checks(self) -> None:
        print("\n[4. Characters]")
        if not self.novel_id:
            print("  SKIP: no novel available")
            return
        status, body = self.get(f"/api/v1/novels/{self.novel_id}/characters")
        self.assert_status("GET characters", status)

    def run_novel_settings_checks(self) -> None:
        print("\n[5. Novel Settings]")
        if not self.novel_id:
            print("  SKIP: no novel available")
            return
        status, body = self.get(f"/api/v1/novels/{self.novel_id}/settings")
        self.assert_status("GET novel settings", status)

    def run_global_settings_checks(self) -> None:
        print("\n[6. Global Settings]")
        status, body = self.get("/api/v1/settings")
        self.assert_status("GET /api/v1/settings", status)

    def run_foreshadow_checks(self) -> None:
        print("\n[7. Foreshadows]")
        if not self.novel_id:
            print("  SKIP: no novel available")
            return
        status, body = self.get(f"/api/v1/novels/{self.novel_id}/foreshadows")
        self.assert_status("GET foreshadows", status)
        status, body = self.get(f"/api/v1/novels/{self.novel_id}/foreshadows/pending-report")
        self.assert_status("GET foreshadow pending report", status)

    def run_memory_checks(self) -> None:
        print("\n[8. Memory]")
        if not self.novel_id:
            print("  SKIP: no novel available")
            return
        for endpoint in ["facts", "beats", "clues", "iron-lock"]:
            status, body = self.get(f"/api/v1/novels/{self.novel_id}/memory/{endpoint}")
            self.assert_status(f"GET memory {endpoint}", status)

    def run_knowledge_checks(self) -> None:
        print("\n[9. Knowledge]")
        if not self.novel_id:
            print("  SKIP: no novel available")
            return
        status, body = self.get(f"/api/v1/novels/{self.novel_id}/knowledge/summaries")
        self.assert_status("GET knowledge summaries", status)
        status, body = self.get(f"/api/v1/novels/{self.novel_id}/knowledge/triples")
        self.assert_status("GET knowledge triples", status)

    def run_quality_checks(self) -> None:
        print("\n[10. Quality]")
        status, body = self.get("/api/v1/quality/guards")
        self.assert_status("GET quality guards", status)
        status, body = self.post("/api/v1/quality/audit", {"content": "测试文本内容", "context": {}})
        self.assert_status("POST quality audit", status)

    def run_voice_checks(self) -> None:
        print("\n[11. Voice]")
        status, body = self.get("/api/v1/voice/fingerprints")
        self.assert_status("GET voice fingerprints", status)

    def run_export_checks(self) -> None:
        print("\n[12. Export]")
        if not self.novel_id:
            print("  SKIP: no novel available")
            return
        status, body = self.get(f"/api/v1/novels/{self.novel_id}/export/formats")
        self.assert_status("GET export formats", status)
        status, body = self.get(f"/api/v1/novels/{self.novel_id}/export/scopes")
        self.assert_status("GET export scopes", status)
        for fmt in ["txt", "md", "html"]:
            status, body = self.post(f"/api/v1/novels/{self.novel_id}/export", {"format": fmt})
            ok = status == 200
            self.record(f"POST export {fmt}", ok, f"status={status}" if not ok else "")

    def run_storyline_checks(self) -> None:
        print("\n[13. Storylines]")
        if not self.novel_id:
            print("  SKIP: no novel available")
            return
        status, body = self.get(f"/api/v1/novels/{self.novel_id}/storylines")
        self.assert_status("GET storylines", status)

    def run_snapshot_checks(self) -> None:
        print("\n[14. Snapshots]")
        if not self.novel_id:
            print("  SKIP: no novel available")
            return
        status, body = self.get(f"/api/v1/novels/{self.novel_id}/snapshots")
        self.assert_status("GET snapshots", status)

    def run_autonomous_checks(self) -> None:
        print("\n[15. Autonomous]")
        status, body = self.get("/api/v1/autonomous/sessions")
        self.assert_status("GET autonomous sessions", status)

    def run_agent_checks(self) -> None:
        print("\n[16. Agent]")
        # GET /api/v1/agent/conversations - 普通列表端点
        status, body = self.get("/api/v1/agent/conversations")
        self.assert_status("GET agent conversations", status)
        if status == 200 and isinstance(body, dict):
            self.assert_field("agent conversations has list", body, "conversations", list)

        # POST /api/v1/agent/chat - SSE 流式响应，使用 stream 模式只读取首块
        try:
            with self.client.stream(
                "POST",
                "/api/v1/agent/chat",
                json={"message": "你好"},
                timeout=10.0,
            ) as response:
                stream_status = response.status_code
                # 读取首个 chunk 即可，避免阻塞等待整个流
                try:
                    response.iter_text().__next__()
                except StopIteration:
                    pass
                except Exception as e:
                    logging.getLogger(__name__).debug(
                        "SSE 首包读取异常: %s", e
                    )
            ok = stream_status == 200
            self.record(
                "POST agent chat (SSE)",
                ok,
                f"status={stream_status}, expected=200" if not ok else "",
            )
        except httpx.RequestError as exc:
            self.record("POST agent chat (SSE)", False, f"request error: {exc}")
        except Exception as exc:
            self.record("POST agent chat (SSE)", False, f"unexpected error: {exc}")

    def run_all(self, create_fixtures: bool = False) -> bool:
        print("=" * 60)
        print("XingYuanBi API Full Check")
        print(f"Base URL: {self.base_url}")
        print("=" * 60)

        self.run_health_checks()

        if create_fixtures:
            if not self.create_fixtures():
                print("\n[Aborting] fixture creation failed")
                return False
        else:
            if self.discover_existing_novel():
                print(f"  (using existing novel_id: {self.novel_id})")

        self.run_novel_checks()
        self.run_chapter_checks()
        self.run_character_checks()
        self.run_novel_settings_checks()
        self.run_global_settings_checks()
        self.run_foreshadow_checks()
        self.run_memory_checks()
        self.run_knowledge_checks()
        self.run_quality_checks()
        self.run_voice_checks()
        self.run_export_checks()
        self.run_storyline_checks()
        self.run_snapshot_checks()
        self.run_autonomous_checks()
        self.run_agent_checks()

        return self.print_summary()

    def print_summary(self) -> bool:
        passed = sum(1 for _, ok, _ in self.results if ok)
        total = len(self.results)
        print("\n" + "=" * 60)
        print(f"Results: {passed}/{total} passed")
        if passed == total:
            print("ALL PASSED!")
        else:
            print("Some checks failed. See details above.")
        print("=" * 60)
        return passed == total


def main() -> int:
    parser = argparse.ArgumentParser(description="星渊笔 API 运行时健康检查")
    parser.add_argument("--host", default="127.0.0.1", help="后端服务主机地址")
    parser.add_argument("--port", type=int, default=8000, help="后端服务端口")
    parser.add_argument(
        "--create-fixtures",
        action="store_true",
        help="自动创建测试小说与章节（检查结束后会清理）",
    )
    parser.add_argument(
        "--keep-fixtures",
        action="store_true",
        help="检查结束后保留测试数据（默认清理）",
    )
    args = parser.parse_args()

    checker = ApiChecker(args.host, args.port)
    try:
        all_passed = checker.run_all(create_fixtures=args.create_fixtures)
    finally:
        if args.create_fixtures and not args.keep_fixtures:
            print("\n[Cleaning up fixtures]")
            checker.cleanup_fixtures()
        checker.client.close()

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
