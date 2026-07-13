import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents.agent_engine import WritingAgent
from infrastructure.ai.provider_factory import is_llm_configured
from infrastructure.persistence.conversation_repo import ConversationRepository
from interfaces.dependencies import get_conversation_repo, get_writing_agent
from interfaces.middleware.rate_limit import generation_rate_limit_dependency
from interfaces.utils.response import success_response
from interfaces.utils.sse_utils import sanitize_error

router = APIRouter(prefix="/api/v1", tags=["agent"])


class AgentChatRequest(BaseModel):
    model_config = {"extra": "ignore"}

    conversation_id: str | None = None
    message: str
    novel_id: str | None = None


@router.post("/agent/chat")
async def agent_chat(
    req: AgentChatRequest,
    agent: WritingAgent = Depends(get_writing_agent),
    _rate_limit: None = Depends(generation_rate_limit_dependency),
):
    # P0 修复：在真正调用 LLM 前检测配置，未配置时立即返回可识别的配置错误，
    # 避免默认空 base_url 导致无响应或 obscure 的服务器内部错误。
    if not is_llm_configured(agent.llm_client.provider):
        async def config_error_generator() -> AsyncGenerator[str, None]:
            payload = json.dumps(
                {"code": "E4001", "message": "AI 服务未配置，请先在设置中配置模型"},
                ensure_ascii=False,
            )
            yield f"event: error\ndata: {payload}\n\n"

        return StreamingResponse(
            config_error_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for event_type, data in agent.chat(
                message=req.message,
                conversation_id=req.conversation_id,
                novel_id=req.novel_id,
            ):
                payload = json.dumps(data, ensure_ascii=False, default=str)
                yield f"event: {event_type}\ndata: {payload}\n\n"
        except Exception as e:
            payload = json.dumps({"code": "E5000", "message": sanitize_error(e)}, ensure_ascii=False)
            yield f"event: error\ndata: {payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/agent/conversations")
def list_conversations(
    novel_id: str | None = None,
    repo: ConversationRepository = Depends(get_conversation_repo),
):
    conversations = repo.list_conversations(novel_id)
    return success_response([c.to_dict() for c in conversations])


@router.get("/agent/conversations/{conversation_id}")
def get_conversation(
    conversation_id: str,
    repo: ConversationRepository = Depends(get_conversation_repo),
):
    conv = repo.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = repo.list_messages(conversation_id)
    return success_response(
        {
            "conversation": conv.to_dict(),
            "messages": [m.to_dict() for m in messages],
        }
    )


@router.delete("/agent/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    repo: ConversationRepository = Depends(get_conversation_repo),
):
    deleted = repo.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return success_response({"deleted": True})
