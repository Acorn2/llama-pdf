"""
Agent API路由
基于LangChain的智能Agent接口
"""

import logging
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.schemas.agent_schemas import (
    AgentChatRequest, AgentChatResponse,
    DocumentAnalysisRequest, DocumentAnalysisResponse,
    KnowledgeSearchRequest, KnowledgeSearchResponse,
    SummaryRequest, SummaryResponse,
    ConversationHistoryResponse, AgentStatusResponse
)
from app.schemas import ChatStreamChunk
from app.services.agent_service import AgentService
from app.api.dependencies import get_agent_service_dep, handle_service_exceptions

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent", tags=["Agent"])

@router.post("/chat", response_model=AgentChatResponse, summary="Agent对话")
@handle_service_exceptions
async def agent_chat(
    request: AgentChatRequest,
    agent_service: AgentService = Depends(get_agent_service_dep)
):
    """
    与Agent进行对话
    支持Agent模式和普通对话模式
    """
    result = await agent_service.chat_with_agent(
        kb_id=request.kb_id,
        message=request.message,
        conversation_id=request.conversation_id,
        use_agent=request.use_agent,
        llm_type=request.llm_type
    )
    return result

@router.post("/analyze", response_model=DocumentAnalysisResponse, summary="文档分析")
@handle_service_exceptions
async def analyze_document(
    request: DocumentAnalysisRequest,
    agent_service: AgentService = Depends(get_agent_service_dep)
):
    """
    使用Agent分析文档内容
    """
    result = await agent_service.analyze_document(
        kb_id=request.kb_id,
        query=request.query,
        llm_type=request.llm_type
    )
    return result

@router.post("/search", response_model=KnowledgeSearchResponse, summary="知识搜索")
@handle_service_exceptions
async def search_knowledge(
    request: KnowledgeSearchRequest,
    agent_service: AgentService = Depends(get_agent_service_dep)
):
    """
    在知识库中搜索信息
    """
    result = await agent_service.search_knowledge(
        kb_id=request.kb_id,
        query=request.query,
        max_results=request.max_results,
        llm_type=request.llm_type
    )
    return result

@router.post("/summary", response_model=SummaryResponse, summary="生成摘要")
@handle_service_exceptions
async def generate_summary(
    request: SummaryRequest,
    agent_service: AgentService = Depends(get_agent_service_dep)
):
    """
    生成文档摘要
    """
    result = await agent_service.generate_summary(
        kb_id=request.kb_id,
        llm_type=request.llm_type
    )
    return result

@router.get("/history/{kb_id}", response_model=ConversationHistoryResponse, summary="获取对话历史")
@handle_service_exceptions
async def get_conversation_history(
    kb_id: str, 
    llm_type: str = "qwen",
    agent_service: AgentService = Depends(get_agent_service_dep)
):
    """
    获取Agent对话历史
    """
    result = await agent_service.get_conversation_history(
        kb_id=kb_id,
        llm_type=llm_type
    )
    return result

@router.delete("/memory/{kb_id}", response_model=dict, summary="清除对话记忆")
@handle_service_exceptions
async def clear_agent_memory(
    kb_id: str, 
    llm_type: str = "qwen",
    agent_service: AgentService = Depends(get_agent_service_dep)
):
    """
    清除Agent对话记忆
    """
    result = await agent_service.clear_agent_memory(
        kb_id=kb_id,
        llm_type=llm_type
    )
    return result

@router.delete("/cache", response_model=dict, summary="清除Agent缓存")
@handle_service_exceptions
async def clear_agent_cache(
    agent_service: AgentService = Depends(get_agent_service_dep)
):
    """
    清除所有Agent缓存
    """
    result = agent_service.clear_agent_cache()
    return result

@router.get("/status/{kb_id}", response_model=AgentStatusResponse, summary="获取Agent状态")
@handle_service_exceptions
async def get_agent_status(
    kb_id: str, 
    llm_type: str = "qwen",
    agent_service: AgentService = Depends(get_agent_service_dep)
):
    """
    获取Agent状态信息
    """
    result = agent_service.get_agent_status(
        kb_id=kb_id,
        llm_type=llm_type
    )
    return result

@router.post("/chat/stream", summary="Agent流式对话")
@handle_service_exceptions
async def agent_chat_stream(
    request: AgentChatRequest,
    agent_service: AgentService = Depends(get_agent_service_dep)
):
    """
    Agent流式对话接口
    支持实时流式输出
    """
    import json
    import time
    
    start_time = time.time()
    
    # 这里需要修改AgentService以支持流式输出
    # 目前先返回模拟的流式响应
    async def generate_stream():
        try:
            # 调用非流式Agent服务获取完整回复
            result = await agent_service.chat_with_agent(
                kb_id=request.kb_id,
                message=request.message,
                conversation_id=request.conversation_id,
                use_agent=request.use_agent,
                llm_type=request.llm_type
            )
            
            if result["success"]:
                answer = result["data"]["answer"]
                # 将完整回复分块发送
                chunk_size = 50
                for i in range(0, len(answer), chunk_size):
                    chunk = answer[i:i+chunk_size]
                    chunk_data = ChatStreamChunk(
                        conversation_id=request.conversation_id or "new",
                        content=chunk,
                        is_final=False
                    )
                    yield f"data: {chunk_data.model_dump_json()}\n\n"
                    time.sleep(0.05)  # 模拟流式延迟
                
                # 发送最终块
                final_chunk = ChatStreamChunk(
                    conversation_id=request.conversation_id or "new",
                    content="",
                    is_final=True,
                    processing_time=time.time() - start_time
                )
                yield f"data: {final_chunk.model_dump_json()}\n\n"
            else:
                # 错误情况
                error_chunk = ChatStreamChunk(
                    conversation_id=request.conversation_id or "new",
                    content="抱歉，处理您的请求时发生了错误。",
                    is_final=True,
                    processing_time=time.time() - start_time
                )
                yield f"data: {error_chunk.model_dump_json()}\n\n"
                
        except Exception as e:
            error_chunk = ChatStreamChunk(
                conversation_id=request.conversation_id or "new",
                content=f"处理请求时发生错误: {str(e)}",
                is_final=True,
                processing_time=time.time() - start_time
            )
            yield f"data: {error_chunk.model_dump_json()}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )