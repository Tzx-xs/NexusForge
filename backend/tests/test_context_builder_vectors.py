"""测试上下文构建器向量检索集成（BLOCK-06）。

验证：
- _build_t2_for_content() 在 vector_store 可用时发起语义检索
- 检索结果被映射为 RelevantHistoryChunk 并附加到 T2NearContext
- vector_store.search() 返回空列表时正常处理
- vector_store 不可用时跳过检索
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


from application.engine.context_builder import ContextBuilder

# ========== Mock 组件 ==========

class MockNovelRepo:
    def get_by_id(self, novel_id: str):
        return type("MockNovel", (), {
            "id": novel_id,
            "title": "测试小说",
            "genre": "玄幻",
            "premise": "测试前提",
        })()


class MockChapter:
    def __init__(self, number=1, title="测试章节", outline="", content=""):
        self.id = "ch_test"
        self.novel_id = "novel_test"
        self.number = number
        self.title = title
        self.outline = outline
        self.content = content


class MockChapterRepo:
    def __init__(self, chapters=None):
        self._chapters = chapters or []

    def list_by_novel(self, novel_id: str):
        return sorted(self._chapters, key=lambda c: c.number)

    def get_by_id(self, chapter_id: str):
        for ch in self._chapters:
            if ch.id == chapter_id:
                return ch
        return None


class MockCharacterRepo:
    def list_by_novel(self, novel_id: str):
        return []


class MockSettingRepo:
    def list_by_novel(self, novel_id: str):
        return []


class MockVectorStore:
    """Mock VectorStore 返回模拟检索结果。"""

    def __init__(self, results=None, should_raise=False):
        self._results = results or []
        self._should_raise = should_raise
        self.search_calls = []

    def search(self, novel_id: str, query: str, top_k: int = 3):
        self.search_calls.append({"novel_id": novel_id, "query": query, "top_k": top_k})
        if self._should_raise:
            raise RuntimeError("向量检索模拟异常")
        return self._results


# ========== 测试 _build_t2_for_content 向量检索集成 ==========


def make_builder(vector_store=None, chapter_repo=None):
    """创建最小化 ContextBuilder 用于测试。"""
    return ContextBuilder(
        novel_repo=MockNovelRepo(),
        chapter_repo=chapter_repo or MockChapterRepo(),
        character_repo=MockCharacterRepo(),
        setting_repo=MockSettingRepo(),
        vector_store=vector_store,
    )


def test_build_t2_with_vector_search_results():
    """验证 vector_store.search() 返回3条结果时，T2 包含检索结果。"""
    # Arrange
    chapter = MockChapter(number=2, outline="主角遭遇危机", content="前章内容...")
    previous_chapter = MockChapter(number=1, outline="平静的日常", content="漫长的第一章内容" * 20)
    chapter_repo = MockChapterRepo([previous_chapter, chapter])

    mock_results = [
        {"id": "r1", "text": "关键线索：主角的身世秘密", "chapter_id": "ch_1", "score": 0.92},
        {"id": "r2", "text": "伏笔：神秘黑衣人出现", "chapter_id": "ch_1", "score": 0.85},
        {"id": "r3", "text": "关联事件：宗门大比", "chapter_id": "ch_1", "score": 0.78},
    ]
    vector_store = MockVectorStore(results=mock_results)

    builder = make_builder(vector_store=vector_store, chapter_repo=chapter_repo)

    # Act
    t2 = builder._build_t2_for_content("novel_test", chapter)

    # Assert
    assert len(t2.relevant_history) == 3
    assert t2.relevant_history[0].text == "关键线索：主角的身世秘密"
    assert t2.relevant_history[0].chapter_id == "ch_1"
    assert t2.relevant_history[0].similarity_score == 0.92
    assert t2.relevant_history[0].source == "vector_search"
    assert t2.relevant_history[1].text == "伏笔：神秘黑衣人出现"
    assert t2.relevant_history[2].text == "关联事件：宗门大比"
    # 验证文本被截断到300字
    for h in t2.relevant_history:
        assert len(h.text) <= 300


def test_build_t2_vector_search_truncates_long_text():
    """验证检索结果文本超过300字时被截断。"""
    chapter = MockChapter(number=2, outline="测试")
    previous_chapter = MockChapter(number=1, content="x" * 50)
    chapter_repo = MockChapterRepo([previous_chapter, chapter])

    long_text = "长" * 500  # 500 字
    mock_results = [
        {"id": "r1", "text": long_text, "chapter_id": "ch_1", "score": 0.9},
    ]
    vector_store = MockVectorStore(results=mock_results)

    builder = make_builder(vector_store=vector_store, chapter_repo=chapter_repo)
    t2 = builder._build_t2_for_content("novel_test", chapter)

    assert len(t2.relevant_history) == 1
    assert len(t2.relevant_history[0].text) == 300
    assert t2.relevant_history[0].text == "长" * 300


def test_build_t2_vector_search_empty_results():
    """验证 vector_store.search() 返回空列表时 relevant_history 为空。"""
    chapter = MockChapter(number=2, outline="测试")
    previous_chapter = MockChapter(number=1, content="x" * 50)
    chapter_repo = MockChapterRepo([previous_chapter, chapter])

    vector_store = MockVectorStore(results=[])

    builder = make_builder(vector_store=vector_store, chapter_repo=chapter_repo)
    t2 = builder._build_t2_for_content("novel_test", chapter)

    assert t2.relevant_history == []


def test_build_t2_no_vector_store():
    """验证 vector_store 为 None 时 relevant_history 为空，不报错。"""
    chapter = MockChapter(number=2, outline="测试")
    previous_chapter = MockChapter(number=1, content="x" * 50)
    chapter_repo = MockChapterRepo([previous_chapter, chapter])

    builder = make_builder(vector_store=None, chapter_repo=chapter_repo)
    t2 = builder._build_t2_for_content("novel_test", chapter)

    assert t2.relevant_history == []


def test_build_t2_vector_search_exception_handled():
    """验证 vector_store.search() 抛异常时不影响主流程。"""
    chapter = MockChapter(number=2, outline="测试")
    previous_chapter = MockChapter(number=1, content="x" * 50)
    chapter_repo = MockChapterRepo([previous_chapter, chapter])

    vector_store = MockVectorStore(should_raise=True)

    builder = make_builder(vector_store=vector_store, chapter_repo=chapter_repo)
    t2 = builder._build_t2_for_content("novel_test", chapter)

    # 异常被捕获，relevant_history 为空
    assert t2.relevant_history == []
    # 其他字段正常
    assert t2.chapter_number == 2


def test_build_t2_vector_search_query_construction():
    """验证检索查询由前章摘要+当前章纲构建。"""
    chapter = MockChapter(number=2, outline="主角遭遇神秘袭击，揭开身世之谜")
    previous_chapter = MockChapter(number=1, content="第一章正文内容" * 20)
    chapter_repo = MockChapterRepo([previous_chapter, chapter])

    vector_store = MockVectorStore(results=[])

    builder = make_builder(vector_store=vector_store, chapter_repo=chapter_repo)
    builder._build_t2_for_content("novel_test", chapter)

    assert len(vector_store.search_calls) == 1
    call = vector_store.search_calls[0]
    assert call["novel_id"] == "novel_test"
    assert call["top_k"] == 3
    # query 应包含章纲开头内容
    assert "主角遭遇神秘袭击" in call["query"]


def test_build_t2_no_previous_chapter():
    """验证没有前一章时跳过向量检索。"""
    chapter = MockChapter(number=1, outline="第一章")
    chapter_repo = MockChapterRepo([chapter])

    vector_store = MockVectorStore(results=[])
    builder = make_builder(vector_store=vector_store, chapter_repo=chapter_repo)

    t2 = builder._build_t2_for_content("novel_test", chapter)

    assert t2.relevant_history == []
    assert len(vector_store.search_calls) == 0
