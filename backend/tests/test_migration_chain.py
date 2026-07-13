"""QA Round 2: 验证迁移文件"""
import os
import py_compile
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIGRATIONS_DIR = os.path.join(BACKEND_DIR, "migrations")

MIGRATION_FILES = sorted([
    f for f in os.listdir(MIGRATIONS_DIR)
    if f.endswith('.py') and not f.startswith('_')
])


def test_migrations_directory_exists():
    assert os.path.isdir(MIGRATIONS_DIR), f"migrations/ 目录不存在: {MIGRATIONS_DIR}"


def test_migration_files_present():
    # 当前包含 001-007 共 7 个迁移文件（007 修复 FTS5 触发器兼容性）
    assert len(MIGRATION_FILES) == 7, f"期望7个迁移文件，实际{len(MIGRATION_FILES)}: {MIGRATION_FILES}"


def test_001_initial_schema_syntax():
    path = os.path.join(MIGRATIONS_DIR, "001_initial_schema.py")
    py_compile.compile(path, doraise=True)


def test_002_add_character_gender_age_syntax():
    path = os.path.join(MIGRATIONS_DIR, "002_add_character_gender_age.py")
    py_compile.compile(path, doraise=True)


def test_003_add_snapshot_content_syntax():
    path = os.path.join(MIGRATIONS_DIR, "003_add_snapshot_content.py")
    py_compile.compile(path, doraise=True)


def test_004_fts5_search_syntax():
    path = os.path.join(MIGRATIONS_DIR, "004_fts5_search.py")
    py_compile.compile(path, doraise=True)


def test_005_add_novel_style_tags_perspective_syntax():
    path = os.path.join(MIGRATIONS_DIR, "005_add_novel_style_tags_perspective.py")
    py_compile.compile(path, doraise=True)


def test_006_add_review_tasks_syntax():
    path = os.path.join(MIGRATIONS_DIR, "006_add_review_tasks.py")
    py_compile.compile(path, doraise=True)


def test_007_fix_fts5_triggers_syntax():
    path = os.path.join(MIGRATIONS_DIR, "007_fix_fts5_triggers.py")
    py_compile.compile(path, doraise=True)


def test_all_migrations_have_upgrade():
    for f in MIGRATION_FILES:
        path = os.path.join(MIGRATIONS_DIR, f)
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
        assert "def upgrade" in content, f"{f} 缺少 upgrade() 函数"


def test_all_migrations_have_downgrade():
    for f in MIGRATION_FILES:
        path = os.path.join(MIGRATIONS_DIR, f)
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
        assert "def downgrade" in content, f"{f} 缺少 downgrade() 函数"


def test_all_migrations_have_revision():
    for f in MIGRATION_FILES:
        path = os.path.join(MIGRATIONS_DIR, f)
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
        assert "revision" in content, f"{f} 缺少 revision 变量"


def test_001_includes_bible_characters_tables():
    path = os.path.join(MIGRATIONS_DIR, "001_initial_schema.py")
    with open(path, encoding="utf-8") as fh:
        content = fh.read()
    assert "bible" in content.lower() or "characters" in content.lower() or "CREATE TABLE" in content.upper(), \
        "001应包含建表语句"


def test_002_includes_gender_age_columns():
    path = os.path.join(MIGRATIONS_DIR, "002_add_character_gender_age.py")
    with open(path, encoding="utf-8") as fh:
        content = fh.read()
    assert "gender" in content.lower(), "002应包含 gender 字段"
    assert "age" in content.lower(), "002应包含 age 字段"


def test_003_includes_snapshot_content_column():
    path = os.path.join(MIGRATIONS_DIR, "003_add_snapshot_content.py")
    with open(path, encoding="utf-8") as fh:
        content = fh.read()
    assert "content" in content.lower() or "snapshot" in content.lower(), "003应包含快照内容相关字段"


def test_005_includes_style_tags_and_perspective_columns():
    path = os.path.join(MIGRATIONS_DIR, "005_add_novel_style_tags_perspective.py")
    with open(path, encoding="utf-8") as fh:
        content = fh.read()
    assert "style_tags" in content.lower(), "005应包含 style_tags 字段"
    assert "perspective" in content.lower(), "005应包含 perspective 字段"


def test_006_includes_review_tasks_table():
    path = os.path.join(MIGRATIONS_DIR, "006_add_review_tasks.py")
    with open(path, encoding="utf-8") as fh:
        content = fh.read()
    assert "review_tasks" in content.lower(), "006应包含 review_tasks 表"
