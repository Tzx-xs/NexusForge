"""Sprint 2.5：管线统一导出。

集中导出 StoryPipeline / AftermathPipeline / PipelineContext 等核心类型，
供调用方按需引用，避免散落在不同子模块路径下。
"""
from engine.pipeline.aftermath import AftermathPipeline, AftermathPipelineStep
from engine.pipeline.base import BaseStoryPipeline, StoryPipeline
from engine.pipeline.context import PipelineContext, PipelineStatus, StepResult

__all__ = [
    "AftermathPipeline",
    "AftermathPipelineStep",
    "BaseStoryPipeline",
    "StoryPipeline",
    "PipelineContext",
    "PipelineStatus",
    "StepResult",
]
