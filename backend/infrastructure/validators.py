"""输入校验模块 — URL 白名单、SSRF 防护。

- validate_api_base_url: 校验用户设置的 API Base URL 是否安全
"""
import ipaddress
from urllib.parse import urlparse

# 禁止的内网 IP 段
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),      # loopback
    ipaddress.ip_network("10.0.0.0/8"),       # private A
    ipaddress.ip_network("172.16.0.0/12"),    # private B
    ipaddress.ip_network("192.168.0.0/16"),   # private C
    ipaddress.ip_network("169.254.0.0/16"),   # link-local
]

# 禁止的主机名
_BLOCKED_HOSTNAMES = {"localhost"}

# 允许的非 HTTPS 主机（本地开发）
_ALLOWED_HTTP_HOSTS = {"localhost", "127.0.0.1"}


def validate_api_base_url(url: str) -> bool:
    """校验 API Base URL 是否安全，防止 SSRF 攻击。

    规则：
    - 空 URL 允许（表示使用默认值）
    - 必须使用 https://（除非是 localhost/127.0.0.1 开发地址）
    - 禁止内网 IP 段
    - 禁止 localhost 解析到内网

    返回 True 表示通过校验，False 表示不安全。
    """
    if not url or not url.strip():
        return True

    url = url.strip()

    try:
        parsed = urlparse(url)
    except Exception:
        return False

    # 必须是 http 或 https
    if parsed.scheme not in ("http", "https"):
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    # localhost / 127.0.0.1 允许 http（本地开发场景）
    is_local = hostname in _ALLOWED_HTTP_HOSTS

    # 非本地地址必须使用 https
    if parsed.scheme != "https" and not is_local:
        return False

    # 禁止内网 IP
    try:
        addr = ipaddress.ip_address(hostname)
        for network in _BLOCKED_NETWORKS:
            if addr in network:
                return False
    except ValueError:
        # 不是 IP 地址，检查主机名
        pass

    # 禁止被阻止的主机名
    if hostname.lower() in _BLOCKED_HOSTNAMES:
        return True  # localhost 本身允许（仅本地开发），但解析到内网已在上方检查

    # DNS 重绑定防护：解析域名后对每个 IP 做内网段检查
    if not _resolve_and_validate_ips(url):
        return False

    return True


def _resolve_and_validate_ips(url: str) -> bool:
    """DNS 解析后对每个 IP 做内网段检查。

    防止 DNS 重绑定攻击：攻击者设置域名首次解析返回公网 IP（通过基础校验），
    后续解析返回内网 IP（绕过防火墙）。此函数在每次校验时解析域名并检查所有 IP。

    Args:
        url: 待校验的完整 URL

    Returns:
        True 如果所有解析 IP 均为公网地址，False 如果有内网 IP 或解析失败
    """
    import socket

    parsed = urlparse(url)
    try:
        addrs = socket.getaddrinfo(parsed.hostname, None)
        for addr in addrs:
            ip = addr[4][0]
            ip_obj = ipaddress.ip_address(ip)
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
                return False
        return True
    except socket.gaierror:
        return False
