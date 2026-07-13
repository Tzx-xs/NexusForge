import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def sample_text():
    return """林渊推开吱呀作响的木门，感受着带着咸腥味的海风拂面而来。
今天是他十六岁的生日，也是他成年礼的日子。

在这个被无尽渊海覆盖的世界里，人类只能在漂浮的岛屿上繁衍生息。

"小渊，快过来，今天是你的大日子。" 老渔夫林伯站在不远处招手。

林渊微微点头，迈步走去。他不知道的是，今天之后，他的人生将彻底改变。

突然，海面上传来一声巨响，一道黑影从深渊中一跃而起。
林渊瞳孔骤缩，倒吸一口凉气，手中的渔竿险些掉落。

"血魔老祖...不可能！" 林伯声音颤抖。

林渊眉头微皱，心中暗道：这股气息...好熟悉..."""


@pytest.fixture
def character_names():
    return ["林渊", "林伯", "血魔老祖", "苏清寒"]


@pytest.fixture
def location_names():
    return ["云屿", "渊海", "青云宗"]
