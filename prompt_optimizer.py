# -*- coding: utf-8 -*-
# 提示词系统：拆分为 搜索 + 优化 两个独立节点
# 依赖：template_utils.py（仅JSON读写，不依赖chromadb/sentence-transformers）

import re, random
from .template_utils import load_templates, add_template, _is_good_prompt, _expand_chinese_query, _ZH_TAG_MAP, _ZH_PATTERN


# ═══════════════════════════════════════════════════════════════
#  节点1：向量库搜索器（加载嵌入模型 + 向量搜索）
# ═══════════════════════════════════════════════════════════════

class TemplateSearcher:
    """🔍 向量库搜索器：LLM理解输入 → 提取英文tag → 向量库搜索 → 输出匹配结果

    接LLM（可选）：有LLM时先用模型提取英文关键词再搜索，中文自然语言也能精准匹配。
    无LLM时直接用原始输入搜索。
    嵌入模型（bge-small-zh-v1.5）自动加载。
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "关键词": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "中文或英文，逗号/空格/换行分隔均可",
                }),
                "模型": (["anima", "sdxl", "animaNSFW", "SDXLNSFW"], {"default": "anima"}),
                "返回数量": ("INT", {"default": 5, "min": 1, "max": 20, "step": 1}),
            },
            "optional": {
                "llama_model": ("LLAMACPPMODEL",),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "INT", "STRING")
    RETURN_NAMES = ("搜索结果", "原始模板", "命中数", "提取关键词")
    FUNCTION = "search"
    CATEGORY = "文本/提示词搜索"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def search(self, 关键词, 模型, 返回数量, llama_model=None):
        if not 关键词 or not 关键词.strip():
            return ("请输入关键词", "", 0, "")

        # ── 第一步：LLM提取英文关键词（有LLM时） ──
        search_query = 关键词.strip()
        extracted = ""
        llm = llama_model

        if llm is None:
            try:
                import importlib
                mod = importlib.import_module("ComfyUI-llama-cpp_vllm.nodes")
                storage = mod.LLAMA_CPP_STORAGE
                if storage.llm is not None:
                    llm = storage.llm
            except Exception:
                pass

        if llm is not None:
            msgs = [
                {
                    "role": "system",
                    "content": (
                        "You are a Danbooru tag extractor. "
                        "Extract 5-15 English tags from the user input that describe the scene, character, and style. "
                        "Output ONLY comma-separated lowercase English tags. "
                        "NO Chinese. NO explanations. NO numbers. NO markdown.\n"
                        "Example: 少女教室看书 -> 1girl, solo, school uniform, classroom, sitting, reading book, book"
                    )
                },
                {"role": "user", "content": [{"type": "text", "text": 关键词.strip()}]}
            ]
            try:
                out = llm.create_chat_completion(
                    messages=msgs, max_tokens=128, temperature=0.2,
                    top_k=30, top_p=0.9, stop=["\n\n"]
                )
                extracted = out['choices'][0]['message']['content'].strip()
                extracted = re.sub(r'[\u4e00-\u9fff\u3400-\u4dbf\uff00-\uffef]', '', extracted)
                extracted = re.sub(r'\s+', ' ', extracted).strip()
                if extracted:
                    search_query = extracted
            except Exception:
                pass

        # ── 第二步：关键词匹配搜索（直接读JSON，不需要嵌入模型） ──
        results = self._keyword_search(模型, search_query, 返回数量)
        if not results:
            return ("未找到匹配模板", "", 0, extracted or search_query)

        # 格式化搜索结果（给LLM看的参考格式）
        formatted_lines = []
        for i, r in enumerate(results):
            cat = r.get("category", "通用")
            tags_preview = ", ".join(r["prompt"].split(",")[:12]).strip()
            formatted_lines.append(f"[{i+1}] {cat}: {tags_preview}")
        formatted = "\n".join(formatted_lines)

        # 原始完整模板（给后续节点拼接用）
        raw_templates = "\n---\n".join(r["prompt"] for r in results)

        return (formatted, raw_templates, len(results), extracted or search_query)

    @staticmethod
    def _keyword_search(model, query, top_n):
        """直接读JSON模板库，按关键词匹配度排序，不需要嵌入模型/ChromaDB"""
        templates = load_templates(model)
        if not templates:
            return []

        # 中文→英文扩展
        expanded_query = _expand_chinese_query(query)

        # 解析查询词为tag列表
        tags = [t.strip().lower() for t in expanded_query.split(",") if t.strip()]
        if not tags:
            tags = [t.strip().lower() for t in expanded_query.split() if t.strip()]
        if not tags:
            return []

        # 按匹配tag数打分
        scored = []
        for t in templates:
            prompt = t.get("prompt", "")
            if not _is_good_prompt(prompt):
                continue
            p_lower = prompt.lower()
            hits = sum(1 for tag in tags if tag in p_lower)
            if hits > 0:
                scored.append((hits, t))

        # 按匹配数降序，取top_n，匹配数相同时随机打乱
        scored.sort(key=lambda x: x[0], reverse=True)
        pool = [t for _, t in scored[:top_n * 3]]
        if len(pool) > top_n:
            return random.sample(pool, top_n)
        return pool


# ═══════════════════════════════════════════════════════════════
#  节点2：质量词选择器（用户勾选质量前缀）
# ═══════════════════════════════════════════════════════════════

class QualityPrefix:
    """🏷️ 质量词选择器：选分级 + 输入自定义质量词，自动合并输出"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "分级": (["safe", "sensitive", "nsfw", "explicit"], {"default": "safe"}),
                "自定义质量词": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "自定义质量词，逗号分隔。与分级选项自动合并输出",
                }),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("质量词",)
    FUNCTION = "build"
    CATEGORY = "文本/质量词"

    def build(self, **kwargs):
        rating = kwargs.get("分级", "safe")
        custom = kwargs.get("自定义质量词", "").strip()
        if custom:
            return (f"{custom}, {rating}",)
        return (rating,)


# ═══════════════════════════════════════════════════════════════
#  节点3：提示词合并（质量词 + 优化提示词）
# ═══════════════════════════════════════════════════════════════

class MergePrompt:
    """🔗 提示词合并：质量词 + 提示词 → 最终输出

    格式：质量词\n\n提示词（两段之间空两行）
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "质量词": ("STRING", {"multiline": False, "default": ""}),
                "提示词": ("STRING", {"multiline": True, "default": ""}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("最终提示词",)
    FUNCTION = "merge"
    CATEGORY = "文本/质量词"

    def merge(self, 质量词, 提示词):
        q = 质量词.strip()
        p = 提示词.strip()
        if q and p:
            return (f"{q}\n\n{p}",)
        elif q:
            return (q,)
        else:
            return (p,)


# ═══════════════════════════════════════════════════════════════
#  节点4：LLM输出清理器
# ═══════════════════════════════════════════════════════════════

class LLMOutputCleaner:
    """✂️ LLM输出清理器：清理LLM返回的多余内容，只保留干净提示词"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "LLM输出": ("STRING", {"multiline": True, "default": ""}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("优化后提示词",)
    FUNCTION = "clean"
    CATEGORY = "文本/提示词优化"

    def clean(self, LLM输出):
        try:
            if not LLM输出:
                return ("",)
            text = LLM输出.strip()
            # 移除<think>...</think>标签（推理token）
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
            text = re.sub(r"</think>|</think>", "", text)
            text = re.sub(r"```\w*\n?", "", text)
            text = re.sub(r"```", "", text)
            text = re.sub(r"^(优化[后]的?提示词[：:]\s*)", "", text, flags=re.MULTILINE)
            text = re.sub(r"^(here is|optimized|result)[：:]\s*", "", text, flags=re.IGNORECASE | re.MULTILINE)
            text = re.sub(r'^[\'"]|[\'"]\$', "", text.strip())
            text = re.sub(r"\n{3,}", "\n\n", text)
            # 移除末尾rating词（由QualityPrefix节点提供）
            text = re.sub(r",\s*(safe|sensitive|nsfw|explicit)\s*$", "", text.strip(), flags=re.IGNORECASE)
            # 移除开头rating词
            text = re.sub(r"^(safe|sensitive|nsfw|explicit)\s*,\s*", "", text.strip(), flags=re.IGNORECASE)
            text = self._remove_repetition(text)
            return (text.strip(),)
        except Exception as e:
            return (f"[清理失败] {e}",)

    @staticmethod
    def _remove_repetition(text):
        if "," in text and "\n" not in text.strip():
            tags = [t.strip() for t in text.split(",") if t.strip()]
            seen = set()
            deduped = []
            for tag in tags:
                key = tag.lower().strip()
                if key not in seen:
                    seen.add(key)
                    deduped.append(tag)
            if len(deduped) < len(tags) * 0.7:
                return ", ".join(deduped)
        tags = [t.strip() for t in text.split(",") if t.strip()]
        if len(tags) > 10:
            for n in [2, 3, 4]:
                if len(tags) > n * 3:
                    pattern = tags[:n]
                    repeat_count = 0
                    for i in range(n, len(tags), n):
                        if tags[i:i+n] == pattern:
                            repeat_count += 1
                        else:
                            break
                    if repeat_count >= 2:
                        return ", ".join(pattern + tags[n + repeat_count * n:])
        if "\n" in text:
            lines = text.split("\n")
            seen = set()
            deduped = []
            for line in lines:
                key = line.strip().lower()
                if key and key not in seen:
                    seen.add(key)
                    deduped.append(line)
            if len(deduped) < len(lines) * 0.7:
                return "\n".join(deduped)
        return text


# ═══════════════════════════════════════════════════════════════
#  节点5：保存提示词模板
# ═══════════════════════════════════════════════════════════════

class SavePromptTemplate:
    """💾 保存提示词模板：一键保存，自动识别模型和分类"""

    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "提示词": ("STRING", {"multiline": True, "default": ""}),
                "模型": (["自动", "anima", "sdxl", "animaNSFW", "SDXLNSFW", "Zimage", "ZimageNSFW"], {"default": "自动"}),
                "分类": ("STRING", {"default": "自动", "tooltip": "自动 或 手动填写（如：人像、风景）"}),
                "备注": ("STRING", {"default": "", "tooltip": "可选"}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("保存状态",)
    FUNCTION = "save"
    CATEGORY = "文本/提示词优化"

    _NSFW_KEYWORDS = {
        "nsfw", "explicit", "nude", "naked", "sex", "anal", "vaginal",
        "blowjob", "fellatio", "handjob", "footjob", "paizuri", "cum",
        "creampie", "orgasm", "penis", "pussy", "vagina", "genital",
        "nipples", "areolae", "masturbation", "fingering", "dildo",
        "bondage", "bdsm", "gangbang", "threesome", "double_penetration",
        "milf", "loli", "shota", "ahegao", "gangbang", "rape",
        "tentacle", "bestiality", "incest", "futanari", "urination",
    }

    _CATEGORY_MAP = {
        "人像": {"1girl", "1boy", "solo", "portrait", "upper_body", "close-up", "face"},
        "风景": {"landscape", "scenery", "nature", "sky", "mountain", "ocean", "forest", "sunset"},
        "室内": {"indoors", "bedroom", "bathroom", "classroom", "office", "room"},
        "群像": {"2girls", "2boys", "3girls", "group", "multiple", "crowd"},
        "抽象": {"abstract", "surreal", "fantasy", "dream", "ethereal", "magical"},
        "赛博朋克": {"cyberpunk", "neon", "futuristic", "sci-fi"},
        "古风": {"ancient", "traditional", "kimono", "chinese", "shrine", "temple"},
        "战斗": {"battle", "fight", "weapon", "sword", "magic", "combat"},
    }

    def save(self, 提示词, 模型, 分类, 备注):
        try:
            if not 提示词 or not 提示词.strip():
                return ("提示词为空，未保存",)
            prompt = 提示词.strip()
            prompt_lower = prompt.lower()
            if 模型 == "自动":
                模型 = self._detect_model(prompt_lower)
            if 分类 == "自动":
                分类 = self._detect_category(prompt_lower)
            entry = add_template(模型, prompt, 分类, 备注)
            return (f"✅ 已保存 → {模型} / {分类} (ID:{entry['id']})",)
        except Exception as e:
            return (f"[保存失败] {e}",)

    def _detect_model(self, prompt_lower):
        has_nsfw = any(kw in prompt_lower for kw in self._NSFW_KEYWORDS)
        has_sdxl = any(kw in prompt_lower for kw in {"sdxl", "score_9", "score_8", "realistic", "photo"})
        if has_nsfw:
            return "SDXLNSFW" if has_sdxl else "animaNSFW"
        return "sdxl" if has_sdxl else "anima"

    def _detect_category(self, prompt_lower):
        best_cat, best_score = "通用", 0
        for cat, keywords in self._CATEGORY_MAP.items():
            score = sum(1 for kw in keywords if kw in prompt_lower)
            if score > best_score:
                best_score = score
                best_cat = cat
        return best_cat
