#!/usr/bin/env python3
"""
星渊笔 - 全面自动化测试脚本
"""

import json
import os
import sys
import time
import traceback
from datetime import datetime

import requests

BASE_URL = "http://127.0.0.1:8000"


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.warnings = []
        self.test_details = []

    def add_pass(self, name: str, message: str = ""):
        self.passed += 1
        self.test_details.append(
            {"name": name, "status": "PASS", "message": message, "time": datetime.now().isoformat()}
        )
        print(f"  [PASS] {name}")

    def add_fail(self, name: str, message: str, error: str = ""):
        self.failed += 1
        self.errors.append({"name": name, "message": message, "error": error})
        self.test_details.append(
            {"name": name, "status": "FAIL", "message": message, "error": error, "time": datetime.now().isoformat()}
        )
        print(f"  [FAIL] {name} - {message}")
        if error:
            print(f"      Error: {error[:300]}")

    def add_warn(self, name: str, message: str):
        self.warnings.append({"name": name, "message": message})
        self.test_details.append(
            {"name": name, "status": "WARN", "message": message, "time": datetime.now().isoformat()}
        )
        print(f"  [WARN] {name} - {message}")

    def summary(self) -> dict:
        total = self.passed + self.failed
        pass_rate = (self.passed / total * 100) if total > 0 else 0
        return {
            "total": total,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": pass_rate,
            "errors": self.errors,
            "warnings": self.warnings,
            "details": self.test_details,
        }


def make_request(method: str, endpoint: str, data: dict = None, params: dict = None, expect_status: int = None):
    url = f"{BASE_URL}{endpoint}"
    try:
        if method == "GET":
            resp = requests.get(url, params=params, timeout=10)
        elif method == "POST":
            resp = requests.post(url, json=data, timeout=10)
        elif method == "PUT":
            resp = requests.put(url, json=data, timeout=10)
        elif method == "DELETE":
            resp = requests.delete(url, timeout=10)
        else:
            return False, None, f"Unsupported method: {method}"

        if expect_status and resp.status_code != expect_status:
            if resp.status_code == 200 and expect_status == 201:
                pass
            else:
                error_detail = ""
                try:
                    error_detail = resp.json()
                except Exception:
                    error_detail = resp.text[:500]
                return False, None, f"Expected status {expect_status}, got {resp.status_code}: {error_detail}"

        try:
            return True, resp.json(), ""
        except Exception:
            return True, resp.text, ""

    except requests.exceptions.ConnectionError:
        return False, None, f"Connection failed to {url}"
    except Exception as e:
        return False, None, str(e)


def unwrap_response(data):
    if isinstance(data, dict) and "data" in data and "code" in data:
        return data.get("data")
    return data


def test_health(result: TestResult):
    print("\n" + "=" * 60)
    print("Test Group: Basic Service")
    print("=" * 60)

    success, data, error = make_request("GET", "/health")
    if success and isinstance(data, dict) and data.get("status") == "ok":
        result.add_pass("Health Check", "Service running")
        return True
    else:
        result.add_fail("Health Check", "Service unreachable", error)
        return False


def test_novels(result: TestResult):
    print("\n" + "=" * 60)
    print("Test Group: Novels")
    print("=" * 60)

    novel_id = None

    success, data, error = make_request("GET", "/api/v1/novels")
    if success:
        novels = unwrap_response(data)
        if isinstance(novels, list) and len(novels) > 0:
            novel_id = novels[0].get("id")
            result.add_pass("List Novels", f"Found {len(novels)} novels")
        else:
            result.add_warn("List Novels", f"Return format: {type(novels)}")
    else:
        result.add_fail("List Novels", "Request failed", error)

    if not novel_id:
        success, data, error = make_request(
            "POST",
            "/api/v1/novels",
            {"title": "Test Novel", "premise": "A test novel", "genre": "Test", "target_chapters": 10},
            expect_status=201,
        )
        if success:
            novel_data = unwrap_response(data)
            novel_id = novel_data.get("id") if isinstance(novel_data, dict) else None
            result.add_pass("Create Novel", f"New novel ID: {novel_id}")
        else:
            result.add_fail("Create Novel", "Creation failed", error)

    if novel_id:
        success, data, error = make_request("GET", f"/api/v1/novels/{novel_id}")
        if success:
            novel_data = unwrap_response(data)
            title = novel_data.get("title", "N/A") if isinstance(novel_data, dict) else "N/A"
            result.add_pass("Get Novel", f"Novel: {title}")
        else:
            result.add_fail("Get Novel", "Request failed", error)

        success, data, error = make_request(
            "PUT", f"/api/v1/novels/{novel_id}", {"title": "Test Novel (Updated)", "premise": "Updated premise"}
        )
        if success:
            result.add_pass("Update Novel", "Novel updated")
        else:
            result.add_fail("Update Novel", "Update failed", error)

    return novel_id


def test_chapters(result: TestResult, novel_id: str):
    print("\n" + "=" * 60)
    print("Test Group: Chapters")
    print("=" * 60)

    chapter_id = None

    if not novel_id:
        result.add_warn("Chapters", "No novel ID, skipping")
        return None

    success, data, error = make_request("GET", f"/api/v1/novels/{novel_id}/chapters")
    if success:
        chapters = unwrap_response(data)
        if isinstance(chapters, list):
            result.add_pass("List Chapters", f"Found {len(chapters)} chapters")
            if len(chapters) > 0:
                chapter_id = chapters[0].get("id")
        else:
            result.add_warn("List Chapters", f"Return format: {type(chapters)}")
    else:
        result.add_fail("List Chapters", "Request failed", error)

    if not chapter_id:
        success, data, error = make_request(
            "POST", f"/api/v1/novels/{novel_id}/chapters", {"title": "Test Chapter", "number": 99}, expect_status=201
        )
        if success:
            chap_data = unwrap_response(data)
            chapter_id = chap_data.get("id") if isinstance(chap_data, dict) else None
            result.add_pass("Create Chapter", f"New chapter ID: {chapter_id}")
        else:
            result.add_fail("Create Chapter", "Creation failed", error)

    if chapter_id:
        success, data, error = make_request("GET", f"/api/v1/chapters/{chapter_id}")
        if success:
            result.add_pass("Get Chapter", "Chapter retrieved")
        else:
            result.add_fail("Get Chapter", "Request failed", error)

        success, data, error = make_request(
            "PUT",
            f"/api/v1/chapters/{chapter_id}",
            {"content": "Test chapter content here.", "title": "Test Chapter (Updated)", "status": "draft"},
        )
        if success:
            result.add_pass("Update Chapter", "Chapter updated")
        else:
            result.add_fail("Update Chapter", "Update failed", error)

    return chapter_id


def test_bible(result: TestResult, novel_id: str):
    print("\n" + "=" * 60)
    print("Test Group: Bible (Characters/Settings)")
    print("=" * 60)

    if not novel_id:
        result.add_warn("Bible", "No novel ID, skipping")
        return

    success, data, error = make_request("GET", f"/api/v1/novels/{novel_id}/characters")
    if success:
        chars = unwrap_response(data)
        if isinstance(chars, list):
            result.add_pass("List Characters", f"Found {len(chars)} characters")
        else:
            result.add_warn("List Characters", f"Return format: {type(chars)}")
    else:
        result.add_fail("List Characters", "Request failed", error)

    success, data, error = make_request(
        "POST",
        f"/api/v1/novels/{novel_id}/characters",
        {
            "name": "Test Character",
            "role": "Supporting",
            "description": "A test character",
            "personality": "Cheerful",
            "appearance": "Tall",
            "background": "Commoner",
        },
        expect_status=201,
    )
    if success:
        result.add_pass("Create Character", "Character created")
    else:
        result.add_fail("Create Character", "Creation failed", error)

    success, data, error = make_request("GET", f"/api/v1/novels/{novel_id}/settings")
    if success:
        settings = unwrap_response(data)
        if isinstance(settings, list):
            result.add_pass("List Settings", f"Found {len(settings)} settings")
        else:
            result.add_warn("List Settings", f"Return format: {type(settings)}")
    else:
        result.add_fail("List Settings", "Request failed", error)

    success, data, error = make_request(
        "POST",
        f"/api/v1/novels/{novel_id}/settings",
        {"name": "Test Location", "setting_type": "geography", "description": "A test location"},
        expect_status=201,
    )
    if success:
        result.add_pass("Create Setting", "Setting created")
    else:
        result.add_fail("Create Setting", "Creation failed", error)


def test_foreshadows(result: TestResult, novel_id: str):
    print("\n" + "=" * 60)
    print("Test Group: Foreshadows")
    print("=" * 60)

    if not novel_id:
        result.add_warn("Foreshadows", "No novel ID, skipping")
        return

    success, data, error = make_request("GET", f"/api/v1/novels/{novel_id}/foreshadows")
    if success:
        items = unwrap_response(data)
        if isinstance(items, list):
            result.add_pass("List Foreshadows", f"Found {len(items)} items")
        else:
            result.add_warn("List Foreshadows", f"Return format: {type(items)}")
    else:
        result.add_fail("List Foreshadows", "Request failed", error)

    success, data, error = make_request(
        "POST",
        f"/api/v1/novels/{novel_id}/foreshadows",
        {"title": "Test Foreshadow", "description": "An important foreshadow", "priority": "P2", "status": "planted"},
        expect_status=201,
    )
    if success:
        result.add_pass("Create Foreshadow", "Foreshadow created")
    else:
        result.add_fail("Create Foreshadow", "Creation failed", error)


def test_storylines(result: TestResult, novel_id: str):
    print("\n" + "=" * 60)
    print("Test Group: Storylines")
    print("=" * 60)

    if not novel_id:
        result.add_warn("Storylines", "No novel ID, skipping")
        return

    success, data, error = make_request("GET", f"/api/v1/novels/{novel_id}/storylines")
    if success:
        items = unwrap_response(data)
        if isinstance(items, list):
            result.add_pass("List Storylines", f"Found {len(items)} storylines")
        else:
            result.add_warn("List Storylines", f"Return format: {type(items)}, data: {str(data)[:200]}")
    else:
        result.add_fail("List Storylines", "Request failed", error)

    success, data, error = make_request(
        "POST",
        f"/api/v1/novels/{novel_id}/storylines",
        {
            "name": "Main Plot",
            "description": "The main story arc",
            "color": "#6366f1",
            "is_active": True,
            "sort_order": 0,
        },
        expect_status=201,
    )
    if success:
        result.add_pass("Create Storyline", "Storyline created")
    else:
        result.add_fail("Create Storyline", "Creation failed", error)


def test_snapshots(result: TestResult, novel_id: str, chapter_id: str):
    print("\n" + "=" * 60)
    print("Test Group: Snapshots")
    print("=" * 60)

    if not novel_id or not chapter_id:
        result.add_warn("Snapshots", "No novel/chapter ID, skipping")
        return

    success, data, error = make_request("GET", f"/api/v1/novels/{novel_id}/snapshots")
    if success:
        items = unwrap_response(data)
        if isinstance(items, list):
            result.add_pass("List Snapshots", f"Found {len(items)} snapshots")
        else:
            result.add_warn("List Snapshots", f"Return format: {type(items)}")
    else:
        result.add_fail("List Snapshots", "Request failed", error)


def test_export(result: TestResult, novel_id: str):
    print("\n" + "=" * 60)
    print("Test Group: Export")
    print("=" * 60)

    if not novel_id:
        result.add_warn("Export", "No novel ID, skipping")
        return

    for fmt in ["txt", "md"]:
        try:
            resp = requests.get(f"{BASE_URL}/api/v1/novels/{novel_id}/export", params={"format": fmt}, timeout=10)
            if resp.status_code == 200:
                result.add_pass(f"Export {fmt.upper()}", f"Size: {len(resp.content)} bytes")
            else:
                result.add_fail(f"Export {fmt.upper()}", f"Status: {resp.status_code}", resp.text[:200])
        except Exception as e:
            result.add_fail(f"Export {fmt.upper()}", "Exception", str(e))

    success, data, error = make_request("GET", f"/api/v1/novels/{novel_id}/export/formats")
    if success:
        result.add_pass("List Export Formats", "Formats retrieved")
    else:
        result.add_warn("List Export Formats", "May need different endpoint", error[:100])


def test_settings(result: TestResult):
    print("\n" + "=" * 60)
    print("Test Group: Settings")
    print("=" * 60)

    success, data, error = make_request("GET", "/api/v1/settings")
    if success:
        s = unwrap_response(data)
        if isinstance(s, (dict, list)):
            result.add_pass("Get Settings", "Settings retrieved")
        else:
            result.add_warn("Get Settings", f"Return format: {type(s)}")
    else:
        result.add_fail("Get Settings", "Request failed", error)


def test_memory(result: TestResult, novel_id: str):
    print("\n" + "=" * 60)
    print("Test Group: Memory Engine")
    print("=" * 60)

    if not novel_id:
        result.add_warn("Memory", "No novel ID, skipping")
        return

    success, data, error = make_request("GET", f"/api/v1/novels/{novel_id}/memory/iron-lock")
    if success:
        result.add_pass("Memory Iron Lock", "Memory state retrieved")
    else:
        result.add_warn("Memory Iron Lock", "Endpoint may need data", error[:100])

    success, data, error = make_request("GET", f"/api/v1/novels/{novel_id}/memory/facts")
    if success:
        facts = unwrap_response(data)
        if isinstance(facts, list):
            result.add_pass("Memory Facts", f"Found {len(facts)} facts")
        else:
            result.add_warn("Memory Facts", f"Return format: {type(facts)}")
    else:
        result.add_warn("Memory Facts", "May need data", error[:100])

    success, data, error = make_request("GET", f"/api/v1/novels/{novel_id}/memory/beats")
    if success:
        result.add_pass("Memory Beats", "Beats retrieved")
    else:
        result.add_warn("Memory Beats", "May need data", error[:100])

    success, data, error = make_request("GET", f"/api/v1/novels/{novel_id}/memory/clues")
    if success:
        result.add_pass("Memory Clues", "Clues retrieved")
    else:
        result.add_warn("Memory Clues", "May need data", error[:100])


def test_knowledge(result: TestResult, novel_id: str):
    print("\n" + "=" * 60)
    print("Test Group: Knowledge Base")
    print("=" * 60)

    if not novel_id:
        result.add_warn("Knowledge", "No novel ID, skipping")
        return

    success, data, error = make_request("GET", f"/api/v1/novels/{novel_id}/knowledge/triples")
    if success:
        triples = unwrap_response(data)
        if isinstance(triples, list):
            result.add_pass("Knowledge Triples", f"Found {len(triples)} triples")
        else:
            result.add_warn("Knowledge Triples", f"Return format: {type(triples)}")
    else:
        result.add_warn("Knowledge Triples", "May need data", error[:100])

    success, data, error = make_request("GET", f"/api/v1/novels/{novel_id}/knowledge/summaries")
    if success:
        result.add_pass("Knowledge Summaries", "Summaries retrieved")
    else:
        result.add_warn("Knowledge Summaries", "May need data", error[:100])


def test_voice(result: TestResult):
    print("\n" + "=" * 60)
    print("Test Group: Voice System")
    print("=" * 60)

    success, data, error = make_request("GET", "/api/v1/voice/fingerprints")
    if success:
        fps = unwrap_response(data)
        if isinstance(fps, list):
            result.add_pass("List Voice Fingerprints", f"Found {len(fps)} fingerprints")
        else:
            result.add_warn("List Voice Fingerprints", f"Return format: {type(fps)}")
    else:
        result.add_warn("List Voice Fingerprints", "May need voice extraction first", error[:100])


def test_review_and_quality(result: TestResult, chapter_id: str):
    print("\n" + "=" * 60)
    print("Test Group: Review & Quality")
    print("=" * 60)

    if not chapter_id:
        result.add_warn("Review", "No chapter ID, skipping")
        return

    success, data, error = make_request("GET", f"/api/v1/chapters/{chapter_id}/review")
    if success:
        result.add_pass("Get Chapter Review", "Review retrieved")
    else:
        result.add_warn("Get Chapter Review", "May need review first", error[:100])


def main():
    print("Starting comprehensive test...")
    print("Time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print()

    result = TestResult()
    start_time = time.time()

    try:
        print("Waiting for service...")
        for _ in range(5):
            try:
                requests.get(f"{BASE_URL}/health", timeout=2)
                break
            except Exception:
                time.sleep(1)

        if not test_health(result):
            print("Service not available!")
            return False

        novel_id = test_novels(result)
        chapter_id = test_chapters(result, novel_id)
        test_bible(result, novel_id)
        test_foreshadows(result, novel_id)
        test_storylines(result, novel_id)
        test_snapshots(result, novel_id, chapter_id)
        test_export(result, novel_id)
        test_settings(result)
        test_memory(result, novel_id)
        test_knowledge(result, novel_id)
        test_voice(result)
        test_review_and_quality(result, chapter_id)

    except Exception:
        result.add_fail("Test Exception", "Unhandled exception", traceback.format_exc())

    elapsed = time.time() - start_time
    summary = result.summary()

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total: {summary['total']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Warnings: {summary['warnings']}")
    print(f"Pass Rate: {summary['pass_rate']:.1f}%")
    print(f"Time: {elapsed:.2f}s")

    if summary["errors"]:
        print("\nFAILURES:")
        for i, err in enumerate(summary["errors"], 1):
            print(f"  {i}. {err['name']}: {err['message']}")

    report_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(report_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(report_dir, f"test_report_{ts}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(
            {"summary": summary, "elapsed_seconds": elapsed, "timestamp": datetime.now().isoformat()},
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\nReport saved to: {report_path}")
    print("=" * 60)

    return summary["failed"] == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
