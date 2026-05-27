# -*- coding: utf-8 -*-
# 模板管理CLI工具：不启动ComfyUI即可管理提示词模板
# 用法：python manage_templates.py list [模型名]
#        python manage_templates.py add --model anima --category 人物 --prompt "xxx"
#        python manage_templates.py delete --model anima --id 3
#        python manage_templates.py import --model sdxl --file import.json
#        python manage_templates.py stats

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from template_utils import load_templates, add_template, delete_template, save_templates, MODELS


def cmd_list(args):
    models = [args.model] if args.model else MODELS
    for m in models:
        templates = load_templates(m)
        print(f"\n=== {m} ({len(templates)}条) ===")
        for t in templates:
            note = f" | 备注:{t['note']}" if t.get("note") else ""
            print(f"  [{t['id']}] {t['category']} | {t['prompt'][:60]}{note}")


def cmd_add(args):
    entry = add_template(args.model, args.prompt, args.category, args.note or "")
    print(f"✅ 已添加到 {args.model} (ID:{entry['id']})")


def cmd_delete(args):
    templates = load_templates(args.model)
    if not any(t["id"] == args.id for t in templates):
        print(f"❌ 未找到 ID={args.id}")
        return
    delete_template(args.model, args.id)
    print(f"✅ 已删除 {args.model} 中 ID={args.id}")


def cmd_import(args):
    if not os.path.exists(args.file):
        print(f"❌ 文件不存在: {args.file}")
        return
    with open(args.file, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        print("❌ JSON文件格式错误，需要数组")
        return
    existing = load_templates(args.model)
    next_id = max((t["id"] for t in existing), default=0) + 1
    for item in data:
        item["id"] = next_id
        next_id += 1
    existing.extend(data)
    save_templates(args.model, existing)
    print(f"✅ 已导入 {len(data)} 条到 {args.model}")


def cmd_stats(args):
    print("=== 模板库统计 ===")
    total = 0
    for m in MODELS:
        templates = load_templates(m)
        total += len(templates)
        cats = {}
        for t in templates:
            c = t.get("category", "未分类")
            cats[c] = cats.get(c, 0) + 1
        cat_str = ", ".join(f"{k}:{v}" for k, v in cats.items())
        print(f"  {m}: {len(templates)}条 [{cat_str}]")
    print(f"  总计: {total}条")


def main():
    parser = argparse.ArgumentParser(description="提示词模板管理工具")
    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser("list", help="列出模板")
    p_list.add_argument("model", nargs="?", default=None)

    p_add = sub.add_parser("add", help="添加模板")
    p_add.add_argument("--model", required=True)
    p_add.add_argument("--prompt", required=True)
    p_add.add_argument("--category", default="通用")
    p_add.add_argument("--note", default="")

    p_del = sub.add_parser("delete", help="删除模板")
    p_del.add_argument("--model", required=True)
    p_del.add_argument("--id", type=int, required=True)

    p_imp = sub.add_parser("import", help="批量导入")
    p_imp.add_argument("--model", required=True)
    p_imp.add_argument("--file", required=True)

    sub.add_parser("stats", help="统计信息")

    args = parser.parse_args()
    cmds = {"list": cmd_list, "add": cmd_add, "delete": cmd_delete, "import": cmd_import, "stats": cmd_stats}
    if args.command in cmds:
        cmds[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
