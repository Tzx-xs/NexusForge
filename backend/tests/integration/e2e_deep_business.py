#!/usr/bin/env python3
"""
深度业务链路测试 - 验证完整业务流程
"""

import sys

import requests

BASE_URL = "http://127.0.0.1:8000"


def unwrap(data):
    if isinstance(data, dict) and "data" in data and "code" in data:
        return data["data"]
    return data


passed = 0
failed = 0
errors = []


def check(name, condition, msg=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        errors.append((name, msg))
        print(f"  [FAIL] {name}: {msg}")


def main():
    global passed, failed, errors
    print("=" * 60)
    print("深度业务链路测试")
    print("=" * 60)

    # 1. 完整小说CRUD链路
    print("\n--- 小说完整生命周期 ---")
    resp = requests.post(
        f"{BASE_URL}/api/v1/novels",
        json={"title": "业务测试小说", "premise": "测试完整业务流程", "genre": "测试", "target_chapters": 5},
    )
    check("创建小说", resp.status_code in [200, 201])
    novel = unwrap(resp.json())
    novel_id = novel.get("id")
    check("小说ID存在", novel_id is not None, f"novel={novel}")

    if novel_id:
        # 2. 章节完整链路
        print("\n--- 章节完整生命周期 ---")
        chapters = []
        for i in range(1, 4):
            resp = requests.post(
                f"{BASE_URL}/api/v1/novels/{novel_id}/chapters", json={"title": f"第{i}章", "number": i}
            )
            check(f"创建章节{i}", resp.status_code in [200, 201])
            ch = unwrap(resp.json())
            chapters.append(ch)

        if chapters:
            ch1_id = chapters[0].get("id")
            # 更新章节内容
            content = "第一章的内容。\n\n故事开始了..."
            resp = requests.put(
                f"{BASE_URL}/api/v1/chapters/{ch1_id}", json={"content": content, "status": "generated"}
            )
            check("更新章节内容", resp.status_code == 200)

            # 获取章节详情
            resp = requests.get(f"{BASE_URL}/api/v1/chapters/{ch1_id}")
            ch_data = unwrap(resp.json())
            check("章节内容正确", ch_data.get("content") == content, f"got: {ch_data.get('content', '')[:50]}")

        # 3. 人物设定链路
        print("\n--- 人物设定链路 ---")
        characters = [
            {"name": "主角A", "role": "主角", "description": "故事主角"},
            {"name": "反派B", "role": "反派", "description": "故事反派"},
        ]
        for c in characters:
            resp = requests.post(f"{BASE_URL}/api/v1/novels/{novel_id}/characters", json=c)
            check(f"创建人物{c['name']}", resp.status_code in [200, 201])

        resp = requests.get(f"{BASE_URL}/api/v1/novels/{novel_id}/characters")
        char_list = unwrap(resp.json())
        check("人物列表包含新增", len(char_list) >= 2, f"count={len(char_list)}")

        # 4. 世界观设定链路
        print("\n--- 世界观设定链路 ---")
        resp = requests.post(
            f"{BASE_URL}/api/v1/novels/{novel_id}/settings",
            json={"name": "测试世界", "setting_type": "geography", "description": "一个测试用的世界"},
        )
        check("创建世界观", resp.status_code in [200, 201])

        # 5. 伏笔链路
        print("\n--- 伏笔链路 ---")
        resp = requests.post(
            f"{BASE_URL}/api/v1/novels/{novel_id}/foreshadows",
            json={"title": "神秘玉佩", "description": "主角佩戴的神秘玉佩", "priority": "P1", "status": "planted"},
        )
        check("创建伏笔", resp.status_code in [200, 201])

        resp = requests.get(f"{BASE_URL}/api/v1/novels/{novel_id}/foreshadows")
        fores = unwrap(resp.json())
        check("伏笔列表可获取", isinstance(fores, list))

        # 6. 故事线链路
        print("\n--- 故事线链路 ---")
        resp = requests.post(
            f"{BASE_URL}/api/v1/novels/{novel_id}/storylines",
            json={"name": "主线", "description": "主要故事线", "is_active": True},
        )
        check("创建故事线", resp.status_code in [200, 201])

        resp = requests.get(f"{BASE_URL}/api/v1/novels/{novel_id}/storylines")
        sls = unwrap(resp.json())
        check("故事线列表可获取", isinstance(sls, list), f"type={type(sls)}")

        # 7. 导出链路 - 实际验证导出内容
        print("\n--- 导出功能深度验证 ---")
        for fmt in ["txt", "md"]:
            resp = requests.get(f"{BASE_URL}/api/v1/novels/{novel_id}/export", params={"format": fmt})
            check(f"导出{fmt}成功", resp.status_code == 200, f"status={resp.status_code}")
            if resp.status_code == 200:
                text = resp.content.decode("utf-8", errors="replace")
                check(f"{fmt}包含小说标题", "业务测试小说" in text, f"len={len(text)}")
                check(f"{fmt}非空内容", len(text) > 50, f"len={len(text)}")

        # 8. 记忆引擎链路
        print("\n--- 记忆引擎链路 ---")
        resp = requests.get(f"{BASE_URL}/api/v1/novels/{novel_id}/memory/facts")
        check("记忆事实可获取", resp.status_code == 200)

        resp = requests.get(f"{BASE_URL}/api/v1/novels/{novel_id}/memory/iron-lock")
        check("记忆锁可获取", resp.status_code == 200)

        # 9. 知识库链路
        print("\n--- 知识库链路 ---")
        resp = requests.get(f"{BASE_URL}/api/v1/novels/{novel_id}/knowledge/triples")
        check("知识三元组可获取", resp.status_code == 200)

        resp = requests.get(f"{BASE_URL}/api/v1/novels/{novel_id}/knowledge/summaries")
        check("章节摘要可获取", resp.status_code == 200)

        # 10. 系统设置
        print("\n--- 系统设置 ---")
        resp = requests.get(f"{BASE_URL}/api/v1/settings")
        check("系统设置可获取", resp.status_code == 200)
        settings_data = unwrap(resp.json())
        check("设置数据有效", isinstance(settings_data, (dict, list)))

    # 11. 验证原有样例数据完整性
    print("\n--- 样例数据完整性 ---")
    resp = requests.get(f"{BASE_URL}/api/v1/novels")
    novels = unwrap(resp.json())
    check("小说列表非空", len(novels) >= 1, f"count={len(novels)}")

    if novels:
        sample_id = novels[0].get("id")
        resp = requests.get(f"{BASE_URL}/api/v1/novels/{sample_id}/chapters")
        chs = unwrap(resp.json())
        check("样例小说章节存在", len(chs) >= 1, f"count={len(chs)}")

    # 汇总
    print("\n" + "=" * 60)
    print("深度测试汇总")
    print("=" * 60)
    total = passed + failed
    print(f"总计: {total}")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"通过率: {passed / total * 100:.1f}%" if total > 0 else "N/A")

    if errors:
        print("\n失败项:")
        for name, msg in errors:
            print(f"  - {name}: {msg}")

    return failed == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
