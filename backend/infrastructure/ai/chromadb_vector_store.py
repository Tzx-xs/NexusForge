import contextlib
import hashlib
import json
import os
from typing import Any

from .vector_store import BaseVectorStore


class SimpleVectorStore(BaseVectorStore):
    """简易向量存储（纯内存 + JSON 持久化，无外部依赖）

    用于开发测试和无 ChromaDB 环境的 fallback
    实际使用关键词 + 文本相似度检索
    """

    def __init__(self, storage_path: str = "./data/vector_store.json"):
        self.storage_path = storage_path
        self._data: dict[str, list[dict]] = {}
        self._load()

    def _load(self):
        try:
            with open(self.storage_path, encoding="utf-8") as f:
                self._data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._data = {}

    def _save(self):
        import os

        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def _hash_text(self, text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _simple_similarity(self, text1: str, text2: str) -> float:
        """简易文本相似度（基于字符级 n-gram 重合度）"""

        def ngrams(text: str, n: int = 2) -> set:
            return {text[i : i + n] for i in range(len(text) - n + 1)}

        g1 = ngrams(text1)
        g2 = ngrams(text2)
        if not g1 or not g2:
            return 0.0
        return len(g1 & g2) / len(g1 | g2)

    def add_chunks(self, novel_id: str, chunks: list[dict]) -> int:
        if novel_id not in self._data:
            self._data[novel_id] = []

        count = 0
        for chunk in chunks:
            chunk_id = chunk.get("id") or self._hash_text(chunk.get("text", ""))
            # 去重
            if not any(c.get("id") == chunk_id for c in self._data[novel_id]):
                self._data[novel_id].append(
                    {
                        "id": chunk_id,
                        "text": chunk.get("text", ""),
                        "chapter_id": chunk.get("chapter_id", ""),
                        "metadata": chunk.get("metadata", {}),
                    }
                )
                count += 1

        self._save()
        return count

    def search(self, novel_id: str, query: str, top_k: int = 5) -> list[dict]:
        if novel_id not in self._data:
            return []

        results = []
        for chunk in self._data[novel_id]:
            score = self._simple_similarity(query, chunk["text"])
            results.append(
                {
                    "id": chunk["id"],
                    "text": chunk["text"],
                    "chapter_id": chunk["chapter_id"],
                    "metadata": chunk["metadata"],
                    "score": score,
                }
            )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def delete_by_chapter(self, novel_id: str, chapter_id: str) -> int:
        if novel_id not in self._data:
            return 0
        original = len(self._data[novel_id])
        self._data[novel_id] = [c for c in self._data[novel_id] if c.get("chapter_id") != chapter_id]
        deleted = original - len(self._data[novel_id])
        self._save()
        return deleted

    def delete_by_novel(self, novel_id: str) -> int:
        if novel_id not in self._data:
            return 0
        count = len(self._data[novel_id])
        del self._data[novel_id]
        self._save()
        return count


class ChromaDBVectorStore(BaseVectorStore):
    """ChromaDB 向量存储（可选，需安装 chromadb）

    当环境中存在 chromadb 时使用，否则自动降级为 SimpleVectorStore。
    支持自定义 embedding_function 以确保向量维度与 EmbeddingService 一致（M-16）。
    """

    def __init__(
        self,
        persist_directory: str = "./data/chroma",
        embedding_function=None,
    ):
        """初始化 ChromaDB 向量存储。

        Args:
            persist_directory: ChromaDB 持久化目录路径（嵌入式模式使用）
            embedding_function: 自定义嵌入函数（ChromaDB EmbeddingFunction 兼容接口）。
                若未提供且 collection 不存在，使用 ChromaDB 默认（all-MiniLM-L6-v2）。
                用于确保检索时维度与 EmbeddingService 一致（M-16）。

        环境变量 CHROMA_HOST + CHROMA_PORT 同时设置时，
        使用 chromadb.HttpClient 连接远程 ChromaDB 服务（生产模式）。
        """
        self._embedding_function = embedding_function
        try:
            import chromadb

            chroma_host = os.getenv("CHROMA_HOST", "")
            chroma_port = os.getenv("CHROMA_PORT", "")
            if chroma_host and chroma_port:
                self._client = chromadb.HttpClient(
                    host=chroma_host, port=int(chroma_port)
                )
            else:
                self._client = chromadb.PersistentClient(path=persist_directory)
            self._available = True
        except ImportError:
            self._available = False
            self._fallback = SimpleVectorStore()

    def _get_collection(self, novel_id: str):
        """获取或创建 collection。

        使用自定义 embedding_function（如果提供），
        并在维度不匹配时重建 collection（M-16）。
        """
        name = f"novel_{novel_id}"
        kwargs: dict[str, Any] = {"name": name}
        if self._embedding_function is not None:
            kwargs["embedding_function"] = self._embedding_function


        try:
            return self._client.get_or_create_collection(**kwargs)
        except Exception:
            # 维度不匹配等错误：删除旧 collection 后重建
            import logging
            logger = logging.getLogger(__name__)
            try:
                self._client.delete_collection(name=name)
                logger.info("ChromaDB collection '%s' 维度不匹配，已重建", name)
            except Exception as e:
                logger.warning("删除旧 collection '%s' 失败: %s", name, e)
            return self._client.create_collection(**kwargs)

    def add_chunks(self, novel_id: str, chunks: list[dict]) -> int:
        if not self._available:
            return self._fallback.add_chunks(novel_id, chunks)

        collection = self._get_collection(novel_id)
        ids = [c.get("id") for c in chunks]
        documents = [c.get("text", "") for c in chunks]
        metadatas = [c.get("metadata", {}) for c in chunks]
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        return len(chunks)

    def search(self, novel_id: str, query: str, top_k: int = 5) -> list[dict]:
        if not self._available:
            return self._fallback.search(novel_id, query, top_k)

        collection = self._get_collection(novel_id)
        results = collection.query(query_texts=[query], n_results=top_k)
        output = []
        for i in range(len(results["ids"][0])):
            output.append(
                {
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "score": 1.0 - results["distances"][0][i] if results["distances"] else 0.0,
                }
            )
        return output

    def delete_by_chapter(self, novel_id: str, chapter_id: str) -> int:
        if not self._available:
            return self._fallback.delete_by_chapter(novel_id, chapter_id)
        # TODO: 按 chapter_id 元数据过滤删除
        return 0

    def delete_by_novel(self, novel_id: str) -> int:
        if not self._available:
            return self._fallback.delete_by_novel(novel_id)
        with contextlib.suppress(Exception):
            self._client.delete_collection(name=f"novel_{novel_id}")
        return 0
