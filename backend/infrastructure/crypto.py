"""加密工具模块 — API Key 的 AES-GCM 加密/解密与脱敏。

- encrypt_api_key: 使用 AES-GCM 加密明文 API Key
- decrypt_api_key: 解密为明文
- mask_api_key: 脱敏显示（如 sk-***xxxx）

加密密钥来源：环境变量 ENCRYPTION_KEY。
如果 ENCRYPTION_KEY 未设置，使用基于机器信息的派生密钥（开发友好）。
"""
import base64
import hashlib
import logging
import os
import secrets
import uuid

# 尝试导入 cryptography，如果不可用则降级为 base64 混淆（开发友好）
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

logger = logging.getLogger(__name__)


def _is_production() -> bool:
    """判断当前是否为生产环境。"""
    return os.getenv("APP_ENV", "production").lower() == "production"


def _get_encryption_key() -> bytes:
    """获取 32 字节的 AES-256 密钥。

    优先级：
    1. 环境变量 ENCRYPTION_KEY（建议 64 字符 hex）
    2. 生产环境必须显式设置 ENCRYPTION_KEY，否则抛 RuntimeError
    3. 开发模式：基于机器 UUID + hostname 的派生密钥（仅开发友好）
    """
    raw = os.getenv("ENCRYPTION_KEY", "")
    if raw:
        # 接受 hex 编码的密钥（64 字符 = 32 字节）
        try:
            key = bytes.fromhex(raw)
            if len(key) == 32:
                return key
        except ValueError:
            pass
        # 否则对任意字符串进行 SHA-256 派生
        return hashlib.sha256(raw.encode("utf-8")).digest()

    # M-07 修复：生产环境必须显式设置 ENCRYPTION_KEY，不再静默降级。
    # 旧实现基于机器信息派生密钥，同一台机器上任何进程都能复现，加密形同虚设。
    # 安全实践：生产环境密钥必须由外部注入（环境变量/KMS），不可派生自机器信息。
    if _is_production():
        raise RuntimeError(
            "生产环境必须设置 ENCRYPTION_KEY 环境变量（64 字符 hex 字符串）。"
            "请运行 python -c \"import secrets; print(secrets.token_hex(32))\" 生成。"
        )

    # 仅开发模式允许机器派生
    logger.warning(
        "ENCRYPTION_KEY 未设置，开发模式下使用机器派生密钥。"
        "生产环境必须显式设置 ENCRYPTION_KEY，否则启动会失败。"
    )
    machine_id = hex(uuid.getnode())
    hostname = os.environ.get("COMPUTERNAME", "localhost")
    derived = hashlib.sha256(f"{machine_id}:{hostname}:xingyuanbi".encode()).digest()
    return derived


def encrypt_api_key(plain: str) -> str:
    """使用 AES-GCM 加密 API Key，返回 base64 编码的密文。

    格式：base64(nonce + ciphertext)，前缀 "ENC:" 标记已加密。
    """
    if not plain:
        return plain

    if not HAS_CRYPTO:
        raise RuntimeError("cryptography 库未安装，生产环境必须使用加密")

    key = _get_encryption_key()
    nonce = secrets.token_bytes(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plain.encode("utf-8"), None)
    combined = nonce + ciphertext
    return "ENC:" + base64.b64encode(combined).decode("ascii")


def decrypt_api_key(encrypted: str) -> str:
    """解密 API Key，返回明文。"""
    if not encrypted:
        return encrypted

    if encrypted.startswith("B64:"):
        # 旧数据使用 base64 降级格式，但 cryptography 现在是必需的
        raise RuntimeError("cryptography 库未安装，无法解密 API Key")

    if not encrypted.startswith("ENC:"):
        # 未加密的旧数据，直接返回
        return encrypted

    if not HAS_CRYPTO:
        # 有 ENC: 前缀但无 cryptography 库，无法解密
        raise RuntimeError("cryptography 库未安装，无法解密 API Key")

    try:
        key = _get_encryption_key()
        combined = base64.b64decode(encrypted[4:].encode("ascii"))
        nonce = combined[:12]
        ciphertext = combined[12:]
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
    except Exception as e:
        # M-08 修复：解密失败时记录日志，便于排查密钥不匹配、数据损坏等问题。
        # 旧实现静默吞掉所有异常返回空字符串，掩盖了配置错误。
        # 安全实践：异常应被审计，而非静默忽略；返回空仅作为兜底降级。
        logger.error(
            "API Key 解密失败，可能是 ENCRYPTION_KEY 变更或数据损坏: %s", e, exc_info=True
        )
        return ""


def mask_api_key(key: str) -> str:
    """脱敏显示 API Key。

    规则：
    - 空值：返回空字符串
    - 已加密值（ENC:/B64: 前缀）：返回 "********"（已设置但不可见）
    - sk-xxx... 格式：sk-***xxxx（保留前缀 + 后 4 位）
    - 其他格式：如果长度 <= 8，显示 ****；否则显示前 4 位 + **** + 后 4 位
    """
    if not key:
        return key

    # 已加密的 key 返回统一占位符
    if key.startswith("ENC:") or key.startswith("B64:"):
        return "********"

    if key.startswith("sk-"):
        if len(key) <= 8:
            return "sk-****"
        return f"sk-***{key[-4:]}"

    if len(key) <= 8:
        return "****"

    return f"{key[:4]}****{key[-4:]}"
