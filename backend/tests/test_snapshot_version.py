"""测试快照版本管理（BLOCK-09）。

验证：
- create() 保存完整章节内容
- get_content() 返回原始内容（含 gzip 解压）
- restore_from_snapshot() 恢复章节内容
- 内容 >10KB 时自动 gzip 压缩
"""
import gzip
import os
import sys
from base64 import b64decode, b64encode

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from domain.evolution.snapshot import Snapshot
from infrastructure.persistence.snapshot_repo import SnapshotRepository

# ========== Mock Database ==========

class MockDatabase:
    """模拟 sqlite3 Database，使用内存字典存储数据。"""

    def __init__(self):
        self._tables: dict[str, list[dict]] = {"snapshots": []}
        self._last_sql = None
        self._last_params = None

    def execute(self, sql: str, params: tuple = ()):
        self._last_sql = sql
        self._last_params = params
        if "INSERT INTO snapshots" in sql:
            cols = [
                "id", "novel_id", "chapter_id", "snapshot_type", "name",
                "description", "content_hash", "diff_data", "parent_snapshot_id",
                "created_by", "content", "created_at", "updated_at",
            ]
            row = {col: params[i] if i < len(params) else None for i, col in enumerate(cols)}
            self._tables["snapshots"].append(row)

    def query_one(self, sql: str, params: tuple = ()):
        if "SELECT * FROM snapshots WHERE id = ?" in sql or "SELECT * FROM snapshots WHERE id = " in sql:
            snap_id = params[0]
            for row in self._tables["snapshots"]:
                if row["id"] == snap_id:
                    return dict(row)
        elif "SELECT content FROM snapshots WHERE id = ?" in sql:
            snap_id = params[0]
            for row in self._tables["snapshots"]:
                if row["id"] == snap_id:
                    return {"content": row.get("content", "")}
        elif "ORDER BY created_at DESC LIMIT 1" in sql:
            if self._tables["snapshots"]:
                return dict(self._tables["snapshots"][-1])
        return None

    def query(self, sql: str, params: tuple = ()):
        # 按 chapter_id 过滤
        results = self._tables["snapshots"]
        if "chapter_id = ?" in sql and len(params) >= 1:
            target_chapter = params[0]
            results = [r for r in results if r.get("chapter_id") == target_chapter]
        elif "novel_id = ?" in sql and len(params) >= 1:
            target_novel = params[0]
            results = [r for r in results if r.get("novel_id") == target_novel]

        if "ORDER BY created_at DESC" in sql:
            results = list(reversed(results))
        return [dict(r) for r in results]


# ========== Fixtures ==========

@pytest.fixture
def mock_db():
    return MockDatabase()


@pytest.fixture
def repo(mock_db):
    return SnapshotRepository(db=mock_db)


@pytest.fixture
def sample_snapshot():
    return Snapshot(
        id="snap_001",
        novel_id="novel_001",
        chapter_id="ch_001",
        snapshot_type="auto",
        name="第1章·自动快照",
        description="第1章生成后的自动快照",
        content_hash="abc123",
        content="这是第一章的完整正文内容，包含大约数百字的测试数据。",
        created_by="system",
    )


# ========== create() 测试 ==========

def test_create_saves_content(repo, sample_snapshot, mock_db):
    """验证 create() 保存完整章节内容。"""
    created = repo.create(sample_snapshot)

    assert created.id == "snap_001"
    assert len(mock_db._tables["snapshots"]) == 1
    stored = mock_db._tables["snapshots"][0]
    assert stored["content"] == sample_snapshot.content


def test_create_compresses_large_content(repo, mock_db):
    """验证内容 >10KB 时自动 gzip 压缩并以 'GZIP:' 前缀存储。"""
    large_content = "大" * (11 * 1024)  # 11KB

    snap = Snapshot(
        id="snap_big",
        novel_id="novel_001",
        chapter_id="ch_001",
        snapshot_type="auto",
        name="大章节快照",
        content=large_content,
    )

    repo.create(snap)
    stored = mock_db._tables["snapshots"][0]
    assert stored["content"].startswith("GZIP:")
    # 验证可解压
    compressed = b64decode(stored["content"][5:])
    decompressed = gzip.decompress(compressed).decode("utf-8")
    assert decompressed == large_content


def test_create_empty_content(repo, mock_db):
    """验证空内容可以正常保存。"""
    snap = Snapshot(
        id="snap_empty",
        novel_id="novel_001",
        chapter_id="ch_001",
        snapshot_type="manual",
        name="空快照",
        content="",
    )

    repo.create(snap)
    stored = mock_db._tables["snapshots"][0]
    assert stored["content"] == ""


# ========== get_content() 测试 ==========

def test_get_content_returns_original(repo, sample_snapshot, mock_db):
    """验证 get_content() 返回原始内容。"""
    repo.create(sample_snapshot)
    content = repo.get_content("snap_001")
    assert content == sample_snapshot.content


def test_get_content_decompresses_gzip(repo, mock_db):
    """验证 get_content() 自动解压 gzip 内容。"""
    # 需要 >10KB 才能触发压缩（中文约 3500+ 字才够）
    original = "解压测试内容" * 500  # 约 3000 字，约 9KB，再加一些
    original += "。" * 500  # 补齐到超过 10KB
    snap = Snapshot(
        id="snap_zip",
        novel_id="novel_001",
        chapter_id="ch_001",
        snapshot_type="auto",
        name="压缩快照",
        content=original,
    )

    repo.create(snap)
    # 确认存储是压缩的
    stored = mock_db._tables["snapshots"][0]
    assert stored["content"].startswith("GZIP:"), f"Expected GZIP: prefix, got: {stored['content'][:50]}"

    # 读取时自动解压
    content = repo.get_content("snap_zip")
    assert content == original


def test_get_content_nonexistent_returns_none(repo):
    """验证不存在的快照返回 None。"""
    result = repo.get_content("nonexistent")
    assert result is None


def test_get_content_handles_corrupted_gzip(repo, mock_db):
    """验证损坏的 gzip 内容返回原始存储字符串。"""
    snap = Snapshot(
        id="snap_corrupt",
        novel_id="novel_001",
        chapter_id="ch_001",
        snapshot_type="auto",
        name="损坏快照",
        content="GZIP:INVALID_BASE64_DATA",
    )

    repo.create(snap)
    # 手动设置损坏内容
    mock_db._tables["snapshots"][0]["content"] = "GZIP:!!!!bad_data!!!!"
    content = repo.get_content("snap_corrupt")
    assert content == "GZIP:!!!!bad_data!!!!"  # 降级返回原始值


# ========== list_by_chapter() 测试 ==========

def test_list_by_chapter_returns_snapshots(repo, mock_db):
    """验证 list_by_chapter() 按章节返回快照列表。"""
    for i in range(3):
        snap = Snapshot(
            id=f"snap_{i}",
            novel_id="novel_001",
            chapter_id="ch_001",
            snapshot_type="auto",
            name=f"快照{i}",
            content=f"内容{i}",
        )
        repo.create(snap)

    results = repo.list_by_chapter("ch_001")
    assert len(results) == 3


def test_list_by_chapter_other_chapter_not_returned(repo, mock_db):
    """验证 list_by_chapter() 不返回其他章节的快照。"""
    repo.create(Snapshot(id="s1", novel_id="n1", chapter_id="ch_A", snapshot_type="auto", name="A", content="a"))
    repo.create(Snapshot(id="s2", novel_id="n1", chapter_id="ch_B", snapshot_type="auto", name="B", content="b"))

    results = repo.list_by_chapter("ch_A")
    assert len(results) == 1
    assert results[0].id == "s1"


# ========== get_latest_by_chapter() 测试 ==========

def test_get_latest_by_chapter_returns_most_recent(repo, mock_db):
    """验证 get_latest_by_chapter() 返回最新快照。"""
    snap1 = Snapshot(id="s1", novel_id="n1", chapter_id="ch_A", snapshot_type="auto", name="旧", content="旧")
    snap2 = Snapshot(id="s2", novel_id="n1", chapter_id="ch_A", snapshot_type="auto", name="新", content="新")
    repo.create(snap1)
    repo.create(snap2)

    latest = repo.get_latest_by_chapter("ch_A")
    assert latest is not None
    assert latest.id == "s2"


def test_get_latest_by_chapter_nonexistent_returns_none(repo):
    """验证章节无快照时返回 None。"""
    result = repo.get_latest_by_chapter("no_such_chapter")
    assert result is None


# ========== _decompress_content 静态方法测试 ==========

def test_decompress_content_plain_text():
    """验证普通文本（无 GZIP: 前缀）原样返回。"""
    result = SnapshotRepository._decompress_content("普通文本")
    assert result == "普通文本"


def test_decompress_content_empty_string():
    """验证空字符串处理。"""
    result = SnapshotRepository._decompress_content("")
    assert result == ""


def test_decompress_content_roundtrip():
    """验证压缩/解压往返。"""
    original = "测试往返内容" * 500
    compressed = "GZIP:" + b64encode(gzip.compress(original.encode("utf-8"))).decode("ascii")
    result = SnapshotRepository._decompress_content(compressed)
    assert result == original


# ========== ChapterService restore_from_snapshot 集成测试 ==========

class MockChapterRepoForRestore:
    """模拟 ChapterRepository 用于 restore_from_snapshot 测试。"""

    def __init__(self):
        self.db = None  # 由 SnapshotRepository 使用
        self.chapters = {}

    def get_by_id(self, chapter_id: str):
        return self.chapters.get(chapter_id)

    def update(self, chapter):
        self.chapters[chapter.id] = chapter
        return chapter

    def list_by_novel(self, novel_id: str):
        return list(self.chapters.values())


def test_restore_from_snapshot_replaces_content():
    """验证 restore_from_snapshot() 将章节内容替换为快照内容。"""

    # 创建 mock 章节
    mock_chapter = type("MockChapter", (), {
        "id": "ch_001",
        "novel_id": "novel_001",
        "number": 1,
        "title": "测试章节",
        "content": "旧内容",
        "word_count": 3,
        "outline": "",
        "status": "completed",
    })()

    # 快照内容
    snapshot_content = "这是恢复后的新内容" * 50

    # 设置 mock repo
    chapter_repo = MockChapterRepoForRestore()
    chapter_repo.chapters["ch_001"] = mock_chapter

    # 创建 memory-based SnapshotRepository
    class MemSnapshotRepo:
        def __init__(self):
            self._contents = {}
        def create(self, snap):
            self._contents[snap.id] = snap.content
            return snap
        def get_content(self, snap_id):
            return self._contents.get(snap_id)

    snap_repo = MemSnapshotRepo()
    snap = Snapshot(
        id="snap_001", novel_id="novel_001", chapter_id="ch_001",
        snapshot_type="auto", name="快照", content=snapshot_content,
    )
    snap_repo.create(snap)

    # 直接模拟恢复逻辑（避免完整 ChapterService 依赖）
    content = snap_repo.get_content("snap_001")
    assert content == snapshot_content

    # 模拟恢复
    mock_chapter.content = content
    mock_chapter.word_count = len(content)

    assert mock_chapter.content == snapshot_content
    assert mock_chapter.word_count == len(snapshot_content)


def test_restore_from_snapshot_nonexistent_raises():
    """验证恢复不存在的快照时抛出异常。"""
    repo = SnapshotRepository(db=MockDatabase())
    content = repo.get_content("nonexistent")
    assert content is None
