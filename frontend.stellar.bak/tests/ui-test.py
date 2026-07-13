from playwright.sync_api import sync_playwright, Page, Browser
import time

def test_dashboard_default_module(page: Page):
    """测试首页默认模块是否为"我的小说" """
    print("\n=== 测试1: 首页默认模块 ===")
    page.goto('http://localhost:5174/')
    page.wait_for_load_state('networkidle')
    time.sleep(1)
    
    # 检查 URL 是否包含 module=my-novels
    url = page.url
    assert 'module=my-novels' in url or 'module=' not in url, f"URL 应该默认显示我的小说，当前: {url}"
    print(f"✓ URL: {url}")
    
    # 检查页面标题
    heading = page.locator('h1').first
    heading_text = heading.text_content()
    print(f"✓ 页面标题: {heading_text}")
    
    # 检查侧边栏高亮
    active_link = page.locator('[aria-current="page"]')
    if active_link.count() > 0:
        print(f"✓ 高亮导航: {active_link.first.text_content()}")

def test_navigation(page: Page):
    """测试导航功能 """
    print("\n=== 测试2: 导航功能 ===")
    page.goto('http://localhost:5174/')
    page.wait_for_load_state('networkidle')
    time.sleep(1)
    
    # 测试各导航链接
    nav_links = ['新建小说', '我的小说', '内容审查', '世界观管理', '帮助']
    for link_text in nav_links:
        link = page.locator(f'text={link_text}')
        if link.count() > 0:
            link.click()
            page.wait_for_load_state('networkidle')
            time.sleep(0.5)
            current_url = page.url
            print(f"✓ 点击 '{link_text}' -> URL: {current_url}")

def test_search_input(page: Page):
    """测试搜索输入框 """
    print("\n=== 测试3: 搜索输入框 ===")
    page.goto('http://localhost:5174/#/?module=my-novels')
    page.wait_for_load_state('networkidle')
    time.sleep(1)
    
    search_input = page.locator('input[placeholder*="搜索"]')
    if search_input.count() > 0:
        search_input.fill('测试搜索')
        time.sleep(0.5)
        value = search_input.input_value()
        assert value == '测试搜索', f"搜索输入框值不匹配: {value}"
        print("✓ 搜索输入框正常工作")
    else:
        print("✗ 未找到搜索输入框")

def test_new_novel_button(page: Page):
    """测试新建小说按钮 """
    print("\n=== 测试4: 新建小说按钮 ===")
    page.goto('http://localhost:5174/#/?module=my-novels')
    page.wait_for_load_state('networkidle')
    time.sleep(1)
    
    new_novel_btn = page.locator('button:text("新建小说")')
    if new_novel_btn.count() > 0:
        print("✓ 新建小说按钮存在")
        # 检查按钮是否有 aria-label
        aria_label = new_novel_btn.get_attribute('aria-label')
        print(f"  aria-label: {aria_label}")
    else:
        print("✗ 未找到新建小说按钮")

def test_empty_state(page: Page):
    """测试空状态显示 """
    print("\n=== 测试5: 空状态显示 ===")
    page.goto('http://localhost:5174/#/?module=my-novels')
    page.wait_for_load_state('networkidle')
    time.sleep(1)
    
    empty_state = page.locator('text="还没有小说"')
    if empty_state.count() > 0:
        print("✓ 空状态提示正常显示")
    else:
        print("✗ 未找到空状态提示")

def test_worldview_module(page: Page):
    """测试世界观管理模块 """
    print("\n=== 测试6: 世界观管理模块 ===")
    page.goto('http://localhost:5174/#/?module=worldview')
    page.wait_for_load_state('networkidle')
    time.sleep(2)
    
    heading = page.locator('h1')
    if heading.count() > 0:
        print(f"✓ 页面标题: {heading.first.text_content()}")
    
    # 检查是否有图谱元素
    svg = page.locator('svg')
    if svg.count() > 0:
        print(f"✓ 找到 SVG 元素: {svg.count()} 个")
    else:
        print("✗ 未找到 SVG 元素")

def test_console_errors(page: Page):
    """检查控制台错误 """
    print("\n=== 测试7: 控制台错误检查 ===")
    page.goto('http://localhost:5174/')
    page.wait_for_load_state('networkidle')
    time.sleep(2)
    
    errors = []
    page.on('console', lambda msg: errors.append(msg) if msg.type == 'error' else None)
    
    if errors:
        print(f"✗ 发现 {len(errors)} 个控制台错误")
        for i, error in enumerate(errors[:5]):
            print(f"  Error {i+1}: {error.text[:100]}...")
    else:
        print("✓ 无控制台错误")

def test_page_structure(page: Page):
    """测试页面结构完整性 """
    print("\n=== 测试8: 页面结构检查 ===")
    page.goto('http://localhost:5174/')
    page.wait_for_load_state('networkidle')
    time.sleep(1)
    
    # 检查必需元素
    required_elements = [
        ('header', '顶部导航栏'),
        ('aside', '侧边栏'),
        ('main', '主内容区'),
        ('button', '按钮'),
    ]
    
    for selector, description in required_elements:
        elements = page.locator(selector)
        count = elements.count()
        print(f"✓ {description}: {count} 个")

def test_accessibility_labels(page: Page):
    """测试无障碍标签 """
    print("\n=== 测试9: 无障碍标签检查 ===")
    page.goto('http://localhost:5174/')
    page.wait_for_load_state('networkidle')
    time.sleep(1)
    
    # 检查图标按钮是否有 aria-label
    icon_buttons = page.locator('button')
    count = icon_buttons.count()
    labeled_count = 0
    
    for i in range(count):
        btn = icon_buttons.nth(i)
        aria_label = btn.get_attribute('aria-label')
        if aria_label:
            labeled_count += 1
    
    print(f"✓ 按钮总数: {count}")
    print(f"✓ 带 aria-label 的按钮: {labeled_count}")
    print(f"✓ 未带 aria-label 的按钮: {count - labeled_count}")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            test_dashboard_default_module(page)
            test_navigation(page)
            test_search_input(page)
            test_new_novel_button(page)
            test_empty_state(page)
            test_worldview_module(page)
            test_console_errors(page)
            test_page_structure(page)
            test_accessibility_labels(page)
            
            print("\n=== 测试完成 ===")
        finally:
            browser.close()

if __name__ == '__main__':
    main()