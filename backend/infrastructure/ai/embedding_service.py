import hashlib
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseEmbeddingService(ABC):
    """嵌入服务基类"""

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """生成单个文本的嵌入向量"""
        pass

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量生成嵌入向量"""
        pass


class SimpleHashEmbedding(BaseEmbeddingService):
    """简易哈希嵌入（无外部依赖，用于开发测试）

    基于字符级统计生成定长伪向量，仅用于结构验证，不具备语义检索能力
    """

    def __init__(self, dim: int = 128):
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        if not text:
            return vector

        # 基于字符哈希填充
        for i, ch in enumerate(text):
            h = hashlib.md5(ch.encode("utf-8")).digest()
            for j in range(min(8, self.dim)):
                idx = (i * 8 + j) % self.dim
                vector[idx] += h[j] / 255.0

        # 归一化
        norm = sum(v * v for v in vector) ** 0.5
        if norm > 0:
            vector = [v / norm for v in vector]
        return vector

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


class OpenAIEmbeddingService(BaseEmbeddingService):
    """OpenAI 嵌入服务

    通过 OpenAI 兼容的 /embeddings 接口生成语义向量
    """

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        base_url: str = "https://api.openai.com/v1",
    ):
        import httpx

        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=60.0)

    def embed(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        url = f"{self.base_url}/embeddings"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {"model": self.model, "input": texts}
        response = self._client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        items = sorted(data["data"], key=lambda x: x.get("index", 0))
        return [item["embedding"] for item in items]


class EmbeddingService:
    """嵌入服务工厂

    优先使用 OpenAI 嵌入，调用失败降级到本地哈希嵌入。
    提供 as_chromadb_ef() 方法包装为 ChromaDB 兼容的 EmbeddingFunction 接口（M-16）。
    """

    def __init__(
        self,
        provider: str = "simple",
        api_key: str = "",
        model: str = "text-embedding-3-small",
        base_url: str = "https://api.openai.com/v1",
    ):
        self.provider = provider
        self._fallback: BaseEmbeddingService = SimpleHashEmbedding()
        self._service: BaseEmbeddingService = self._fallback

        if provider == "openai" and api_key:
            try:
                self._service = OpenAIEmbeddingService(api_key=api_key, model=model, base_url=base_url)
            except Exception as e:
                logger.warning("OpenAI 嵌入服务初始化失败，降级到 SimpleHashEmbedding: %s", e)
                self._service = self._fallback

    def as_chromadb_ef(self):
        """M-16: 包装为 ChromaDB 兼容的 EmbeddingFunction 接口。

        返回一个 EmbeddingFunction 子类实例，可传入 ChromaDBVectorStore
        以确保向量写入和检索时维度一致。
        """
        try:
            from chromadb.api.types import EmbeddingFunction as ChromaEF

            _service = self

            class _ChromaAdapter(ChromaEF):
                """将项目 EmbeddingService 适配为 ChromaDB EmbeddingFunction。"""

                def __call__(self, input: list[str]) -> list[list[float]]:  # type: ignore[override]
                    return _service.embed_batch(input)

            return _ChromaAdapter()
        except ImportError:
            logger.warning("chromadb 未安装，无法创建 ChromaDB EmbeddingFunction 适配器")
            return None

    def embed(self, text: str) -> list[float]:
        if self._service is self._fallback:
            return self._service.embed(text)
        try:
            return self._service.embed(text)
        except Exception as e:
            logger.warning("OpenAI 嵌入调用失败，降级到 SimpleHashEmbedding: %s", e)
            return self._fallback.embed(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if self._service is self._fallback:
            return self._service.embed_batch(texts)
        try:
            return self._service.embed_batch(texts)
        except Exception as e:
            logger.warning("OpenAI 批量嵌入调用失败，降级到 SimpleHashEmbedding: %s", e)
            return self._fallback.embed_batch(texts)
