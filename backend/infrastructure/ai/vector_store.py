from abc import ABC, abstractmethod


class BaseVectorStore(ABC):
    """向量存储基类"""

    @abstractmethod
    def add_chunks(self, novel_id: str, chunks: list[dict]) -> int:
        """添加文本片段向量"""
        pass

    @abstractmethod
    def search(self, novel_id: str, query: str, top_k: int = 5) -> list[dict]:
        """语义检索"""
        pass

    @abstractmethod
    def delete_by_chapter(self, novel_id: str, chapter_id: str) -> int:
        """删除章节向量"""
        pass

    @abstractmethod
    def delete_by_novel(self, novel_id: str) -> int:
        """删除小说全部向量"""
        pass

    async def add_document(self, doc_id: str, content: str, metadata: dict | None = None) -> int:
        """添加完整文档（异步接口）"""
        novel_id = metadata.get("novel_id", "") if metadata else ""
        chunk = {"id": doc_id, "text": content, "metadata": metadata or {}}
        return self.add_chunks(novel_id, [chunk])
