import io
import os
import sys
import zipfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from application.services.export_service import ExportFormat, ExportOptions, ExportScope, ExportService


class MockNovelRepo:
    def get_by_id(self, novel_id):
        return type(
            "MockNovel",
            (),
            {
                "id": novel_id,
                "title": "星渊传说",
                "premise": "一个关于少年守护世界的故事",
                "author": "测试作者",
            },
        )()


class MockChapterRepo:
    def list_by_novel(self, novel_id):
        return [
            type(
                "MockChapter",
                (),
                {
                    "id": "ch_1",
                    "number": 1,
                    "title": "第一章 命运的开端",
                    "content": "云泽站在星渊崖边，望着下方无尽的深渊。\n今天是他十六岁的生日。",
                    "word_count": 500,
                    "status": "completed",
                },
            )(),
            type(
                "MockChapter",
                (),
                {
                    "id": "ch_2",
                    "number": 2,
                    "title": "第二章 初入宗门",
                    "content": "第二天，云泽踏上了前往青云宗的路。\n师叔在路口等他。",
                    "word_count": 600,
                    "status": "completed",
                },
            )(),
        ]


@pytest.fixture
def export_service():
    return ExportService(
        novel_repo=MockNovelRepo(),
        chapter_repo=MockChapterRepo(),
    )


def test_export_txt(export_service):
    options = ExportOptions(format=ExportFormat.TXT)
    result = export_service.export_novel("novel_1", options)

    assert result is not None
    assert len(result) > 0
    assert isinstance(result, bytes)

    text = result.decode("utf-8")
    assert "星渊传说" in text
    assert "第一章 命运的开端" in text
    assert "第二章 初入宗门" in text


def test_export_markdown(export_service):
    options = ExportOptions(format=ExportFormat.MARKDOWN)
    result = export_service.export_novel("novel_1", options)

    assert result is not None
    assert len(result) > 0
    assert isinstance(result, bytes)

    text = result.decode("utf-8")
    assert "# 星渊传说" in text
    assert "第一章 命运的开端" in text
    assert "第二章 初入宗门" in text


def test_export_html(export_service):
    options = ExportOptions(format=ExportFormat.HTML)
    result = export_service.export_novel("novel_1", options)

    assert result is not None
    assert len(result) > 0
    assert isinstance(result, bytes)

    text = result.decode("utf-8")
    assert "<html" in text.lower()
    assert "<body" in text.lower()
    assert "星渊传说" in text
    assert "第一章 命运的开端" in text


def test_export_docx(export_service):
    options = ExportOptions(format=ExportFormat.DOCX)
    result = export_service.export_novel("novel_1", options)

    assert result is not None
    assert len(result) > 0
    assert isinstance(result, bytes)


def test_export_epub(export_service):
    options = ExportOptions(format=ExportFormat.EPUB)
    result = export_service.export_novel("novel_1", options)

    assert result is not None
    assert len(result) > 0
    assert isinstance(result, bytes)


def test_export_with_custom_title(export_service):
    options = ExportOptions(format=ExportFormat.TXT, title="自定义标题")
    result = export_service.export_novel("novel_1", options)

    text = result.decode("utf-8")
    assert "自定义标题" in text


def test_export_with_include_title_page(export_service):
    options = ExportOptions(format=ExportFormat.TXT, include_title_page=True, author="测试作者")
    result = export_service.export_novel("novel_1", options)

    text = result.decode("utf-8")
    assert "星渊传说" in text
    assert "测试作者" in text


def test_export_with_chapter_range(export_service):
    options = ExportOptions(
        format=ExportFormat.TXT,
        scope=ExportScope.CHAPTER_RANGE,
        start_chapter=1,
        end_chapter=1,
    )
    result = export_service.export_novel("novel_1", options)

    text = result.decode("utf-8")
    assert "第一章 命运的开端" in text
    assert "第二章 初入宗门" not in text


def test_export_options_defaults():
    options = ExportOptions()

    assert options.format == ExportFormat.TXT
    assert options.scope == ExportScope.FULL
    assert options.include_title_page is True
    assert options.include_chapter_numbers is True
    assert options.include_toc is True
    assert options.font_size == 14
    assert options.line_spacing == 1.5
    assert options.start_chapter is None
    assert options.end_chapter is None


def test_export_unsupported_format(export_service):
    options = ExportOptions(format="unsupported_format")
    result = export_service.export_novel("novel_1", options)

    assert result is not None
    assert isinstance(result, bytes)
    text = result.decode("utf-8")
    assert "星渊传说" in text


def test_txt_export_content_order(export_service):
    options = ExportOptions(format=ExportFormat.TXT)
    result = export_service.export_novel("novel_1", options)

    text = result.decode("utf-8")
    pos1 = text.find("第一章 命运的开端")
    pos2 = text.find("第二章 初入宗门")

    assert pos1 < pos2


def test_export_format_enum():
    assert ExportFormat.TXT == "txt"
    assert ExportFormat.MARKDOWN == "md"
    assert ExportFormat.EPUB == "epub"
    assert ExportFormat.DOCX == "docx"
    assert ExportFormat.HTML == "html"


def test_export_scope_enum():
    assert ExportScope.FULL == "full"
    assert ExportScope.CHAPTER_RANGE == "chapter_range"
    assert ExportScope.SINGLE_CHAPTER == "single_chapter"
    assert ExportScope.OUTLINE_ONLY == "outline_only"


def test_export_single_chapter(export_service):
    options = ExportOptions(
        format=ExportFormat.TXT,
        scope=ExportScope.SINGLE_CHAPTER,
        start_chapter=2,
    )
    result = export_service.export_novel("novel_1", options)

    text = result.decode("utf-8")
    assert "第二章 初入宗门" in text
    assert "第一章 命运的开端" not in text


def test_export_outline_only(export_service):
    options = ExportOptions(
        format=ExportFormat.TXT,
        scope=ExportScope.OUTLINE_ONLY,
    )
    result = export_service.export_novel("novel_1", options)

    assert result is not None
    assert isinstance(result, bytes)


def test_export_epub_escapes_html_entities():
    """EPUB 导出应对标题和正文中的 HTML/XML 特殊字符做转义，防止破坏 XHTML 结构。"""

    class EscapingChapterRepo:
        def list_by_novel(self, novel_id):
            return [
                type(
                    "MockChapter",
                    (),
                    {
                        "id": "ch_escape",
                        "number": 1,
                        "title": "第一章 <测试> & \"标题\"",
                        "content": "正文包含 <b>标签</b> 与 & 符号。\n第二段 \"引号\" 测试。",
                        "word_count": 100,
                        "status": "completed",
                    },
                )()
            ]

    service = ExportService(
        novel_repo=MockNovelRepo(),
        chapter_repo=EscapingChapterRepo(),
    )
    options = ExportOptions(format=ExportFormat.EPUB)
    result = service.export_novel("novel_1", options)

    assert result is not None
    assert isinstance(result, bytes)

    with zipfile.ZipFile(io.BytesIO(result)) as zf:
        names = zf.namelist()
        chapter_name = next((n for n in names if n.endswith("chapter_1.xhtml")), None)
        assert chapter_name is not None
        chapter_html = zf.read(chapter_name).decode("utf-8")

    assert "<b>标签</b>" not in chapter_html
    assert "&lt;b&gt;标签&lt;/b&gt;" in chapter_html
    assert "&lt;测试&gt;" in chapter_html
    assert "&amp;" in chapter_html
    assert "&quot;标题&quot;" in chapter_html or '"标题"' in chapter_html
    assert "&quot;引号&quot;" in chapter_html or '"引号"' in chapter_html
