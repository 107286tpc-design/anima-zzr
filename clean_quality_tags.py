# -*- coding: utf-8 -*-
"""
一次性脚本：清理 templates/ 下所有 JSON 文件中的质量词
用法：python clean_quality_tags.py
备份：自动创建 .bak 文件
"""
import os, json, re, shutil

# ── 从 template_utils.py 复制的质量词定义 ──
_QUALITY_KEYWORDS = [
    "masterpiece", "best quality", "amazing quality", "very aesthetic",
    "extremely detailed", "very detailed", "absurdres", "highres", "newest",
    "score_9", "score_8", "score_7", "safe",
    "cinematic lighting", "real background", "smooth shading",
    "glossy surfaces", "colorful depth", "soft lighting", "rim lighting",
    "masterful shading", "shallow depth of field", "foreshortening",
    "from above", "from below", "from side", "from behind",
    "dramatic angles", "dynamic angle", "low angle", "high angle",
    "vanishing point", "wide shot", "medium shot", "close-up",
    "depth of field", "bokeh", "sharp focus", "soft focus",
    "dramatic lighting", "volumetric lighting", "backlighting",
    "high contrast", "huge filesize", "very aesthetic",
    "subtle", "sketch",
    "pale_skin", "fair_skin",
    # year tags
    "year 2023", "year 2024", "year 2025",
]
_QUALITY_PATTERNS = [
    r'^@\w+(?:\.\d+)?\)?',            # @sw33t, @artist.weight
    r'^Clean\s+elegant\s+anime',       # Clean elegant anime linework
    r'^visible\s+construction',         # visible construction sketch lines
    r'^broken\s+line',                  # broken line edges
    r'^uneven\s+ink',                   # uneven ink detailing
    r'^visual-development',             # visual-development artwork quality
    r'^strong\s+silhouette',            # strong silhouette readability
]
_SKIP_COMPILED = [re.compile(p, re.IGNORECASE) for p in _QUALITY_PATTERNS]


def _is_quality_tag(tag):
    """判断一个tag是否为通用质量/光线/画质词"""
    tag_clean = tag.strip().strip("()").strip()
    if not tag_clean:
        return True
    tag_lower = tag_clean.lower()
    # 检查关键词列表
    for kw in _QUALITY_KEYWORDS:
        if kw in tag_lower:
            return True
    # 检查正则模式
    for p in _SKIP_COMPILED:
        if p.match(tag_clean):
            return True
    return False


def clean_template_prompt(prompt):
    """清理单条prompt中的质量词"""
    if not prompt:
        return prompt, 0
    tags = re.split(r',\s*', prompt)
    kept_tags = []
    removed_count = 0
    for tag in tags:
        if _is_quality_tag(tag):
            removed_count += 1
        else:
            kept_tags.append(tag)
    return ", ".join(kept_tags), removed_count


def main():
    PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
    TEMPLATES_DIR = os.path.join(PLUGIN_DIR, "templates")

    json_files = [
        "anima.json", "animaNSFW.json", "sdxl.json",
        "SDXLNSFW.json", "Zimage.json", "ZimageNSFW.json"
    ]

    total_removed = 0
    total_entries = 0

    for fname in json_files:
        fpath = os.path.join(TEMPLATES_DIR, fname)
        if not os.path.exists(fpath):
            print(f"⚠️  {fname}: 文件不存在，跳过")
            continue

        # 备份
        bak_path = fpath + ".bak"
        shutil.copy2(fpath, bak_path)

        # 加载
        with open(fpath, "r", encoding="utf-8") as f:
            templates = json.load(f)

        file_removed = 0
        file_entries = len(templates)

        for t in templates:
            prompt = t.get("prompt", "")
            cleaned, removed = clean_template_prompt(prompt)
            t["prompt"] = cleaned
            file_removed += removed

        # 保存
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(templates, f, ensure_ascii=False, indent=2)

        total_removed += file_removed
        total_entries += file_entries
        print(f"✅  {fname}: {file_entries} 条模板，移除 {file_removed} 个质量词")

    print(f"\n{'='*50}")
    print(f"总计：{total_entries} 条模板，移除 {total_removed} 个质量词")
    print(f"备份文件：*.bak（与原文件同在 templates/ 目录下）")


if __name__ == "__main__":
    main()
