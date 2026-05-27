# -*- coding: utf-8 -*-
import os
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from .prompt_optimizer import TemplateSearcher, QualityPrefix, MergePrompt, LLMOutputCleaner, SavePromptTemplate

NODE_CLASS_MAPPINGS = {
    "TemplateSearcher": TemplateSearcher,
    "QualityPrefix": QualityPrefix,
    "MergePrompt": MergePrompt,
    "LLMOutputCleaner": LLMOutputCleaner,
    "SavePromptTemplate": SavePromptTemplate,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "TemplateSearcher": "🔍 向量库搜索器 (zzr)",
    "QualityPrefix": "🏷️ 质量词输入 (zzr)",
    "MergePrompt": "🔗 提示词合并 (zzr)",
    "LLMOutputCleaner": "✂️ LLM输出清理器 (zzr)",
    "SavePromptTemplate": "💾 保存提示词模板 (zzr)",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
