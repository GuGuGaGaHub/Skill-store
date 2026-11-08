#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""skills_store.py - 完整 AI Agent Skills 商店
搜索/安装/卸载/检测本地/连接上传
命令级缓存（减token，不重复执行）
每步只报步骤号+核心结果，零解释
"""

import os
import sys
import json
import hashlib
import shutil
import subprocess
import time
import argparse
from pathlib import Path
from typing import Dict, List, Tuple

HOME = Path.home()
ROOT = HOME / ".skills_store"
LOCAL = ROOT / "local"
UPLOADED = ROOT / "uploaded"
CACHE_FILE = ROOT / "cmd_cache.json"
STATE_FILE = ROOT / "state.json"
INDEX_FILE = ROOT / "index.json"

for d in (LOCAL, UPLOADED):
    d.mkdir(parents=True, exist_ok=True)

def load_json(path: Path, default=None):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default if default is not None else {}

def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def cmd_hash(cmd: str) -> str:
    return hashlib.sha256(cmd.strip().encode()).hexdigest()[:16]

def progress(step: int, core: str):
    print(f"步骤{step}：{core}")

def run_once(cmd: str, timeout: int = 90) -> Tuple[str, bool]:
    cache = load_json(CACHE_FILE, {})
    h = cmd_hash(cmd)
    if h in cache:
        return cache[h]["out"], True
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace"
        )
        out = (r.stdout + r.stderr).strip()
        cache[h] = {"out": out, "ts": time.time(), "cmd": cmd[:200]}
        save_json(CACHE_FILE, cache)
        return out, False
    except Exception as e:
        return str(e), False

def skill_meta(skill_dir: Path) -> Dict:
    md = skill_dir / "SKILL.md"
    name = skill_dir.name
    desc = ""
    if md.exists():
        text = md.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()
        for line in lines[:30]:
            if line.startswith("# "):
                name = line[2:].strip()
            low = line.lower()
            if low.startswith("description:") or low.startswith("## description"):
                desc = line.split(":", 1)[-1].strip()
        if not desc:
            for line in lines:
                if line.strip() and not line.startswith("#") and not line.startswith("---"):
                    desc = line.strip()[:120]
                    break
    return {
        "name": name,
        "id": skill_dir.name,
        "path": str(skill_dir),
        "desc": desc,
        "has_skill_md": md.exists()
    }

def detect_local() -> List[Dict]:
    results = []
    for p in LOCAL.iterdir():
        if p.is_dir() and (p / "SKILL.md").exists():
            meta = skill_meta(p)
            meta["uploaded"] = (UPLOADED / p.name).exists()
            results.append(meta)
    return results

def search(query: str = "") -> List[Dict]:
    q = query.lower().strip()
    hits = []
    seen = set()
    for item in detect_local():
        key = item["id"]
        if key in seen:
            continue
        text = (item["name"] + " " + item["desc"] + " " + item["id"]).lower()
        if not q or q in text:
            hits.append(item)
            seen.add(key)
    for p in UPLOADED.iterdir():
        if p.is_dir() and (p / "SKILL.md").exists() and p.name not in seen:
            meta = skill_meta(p)
            meta["uploaded"] = True
            meta["path"] = str(p)
            text = (meta["name"] + " " + meta["desc"] + " " + meta["id"]).lower()
            if not q or q in text:
                hits.append(meta)
                seen.add(p.name)
    return hits

def install(src: str) -> str:
    src_path = Path(src).expanduser().resolve()
    if not src_path.exists():
        up = UPLOADED / src
        if up.exists():
            src_path = up
        else:
            return f"未找到: {src}"
    name = src_path.name if src_path.is_dir() else src_path.stem
    dst = LOCAL / name
    if dst.exists():
        return f"已存在: {dst}"
    if src_path.is_dir():
        shutil.copytree(src_path, dst)
    else:
        dst.mkdir(parents=True)
        if src_path.suffix.lower() in {".md", ".txt"}:
            shutil.copy2(src_path, dst / "SKILL.md")
        else:
            shutil.copy2(src_path, dst / src_path.name)
            (dst / "SKILL.md").write_text(f"# {name}\n\nInstalled from {src_path}\n", encoding="utf-8")
    idx = load_json(INDEX_FILE, {})
    idx[name] = skill_meta(dst)
    save_json(INDEX_FILE, idx)
    return f"已安装 → {dst}"

def uninstall(name: str) -> str:
    target = LOCAL / name
    if not target.exists():
        return f"未安装: {name}"
    shutil.rmtree(target)
    idx = load_json(INDEX_FILE, {})
    idx.pop(name, None)
    save_json(INDEX_FILE, idx)
    return f"已卸载: {name}"

def upload(name_or_path: str) -> str:
    src = Path(name_or_path).expanduser()
    if not src.exists():
        src = LOCAL / name_or_path
    if not src.exists() or not src.is_dir():
        return f"未找到可上传 skill: {name_or_path}"
    name = src.name
    dst = UPLOADED / name
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return f"已上传 → {dst}"

def connect_uploaded() -> List[str]:
    linked = []
    for p in UPLOADED.iterdir():
        if p.is_dir() and (p / "SKILL.md").exists():
            link = LOCAL / p.name
            if link.exists():
                continue
            try:
                link.symlink_to(p)
                linked.append(p.name)
            except Exception:
                shutil.copytree(p, link)
                linked.append(p.name)
    return linked

def list_all() -> None:
    items = detect_local()
    if not items:
        print("（空）")
        return
    for i in items:
        flag = "✓上传" if i["uploaded"] else "本地"
        print(f"{i['id']:<30} [{flag}]  {i['desc'][:60]}")

def clear_cache() -> str:
    if CACHE_FILE.exists():
        CACHE_FILE.unlink()
    return "缓存已清空"

def main():
    parser = argparse.ArgumentParser(description="Skills 商店", add_help=False)
    parser.add_argument("action", nargs="?", default="help")
    parser.add_argument("args", nargs="*", default=[])
    parser.add_argument("-q", "--query", default="")
    args = parser.parse_args()
    act = args.action.lower()
    rest = args.args

    if act in ("help", "-h", "--help"):
        progress(0, "search | install | uninstall | detect | upload | connect | list | run | cache-clear")
        return

    if act == "search":
        q = " ".join(rest) or args.query
        progress(1, f"搜索「{q}」")
        hits = search(q)
        progress(2, f"命中 {len(hits)} 个")
        for h in hits:
            flag = "上传" if h.get("uploaded") else "本地"
            print(f"{h['id']:<28} [{flag}] {h['desc'][:70]}")
        return

    if act == "install":
        if not rest:
            progress(0, "需要路径或名称")
            return
        progress(1, "安装中")
        msg = install(rest[0])
        progress(2, msg)
        return

    if act == "uninstall":
        if not rest:
            progress(0, "需要名称")
            return
        progress(1, "卸载中")
        msg = uninstall(rest[0])
        progress(2, msg)
        return

    if act == "detect":
        progress(1, "检测本地插件")
        items = detect_local()
        for i in items:
            print(f"{i['id']:<30} uploaded={i['uploaded']}")
        progress(2, f"共 {len(items)} 个")
        return

    if act == "upload":
        if not rest:
            progress(0, "需要名称或路径")
            return
        progress(1, "上传中")
        msg = upload(rest[0])
        progress(2, msg)
        return

    if act == "connect":
        progress(1, "连接已上传插件")
        linked = connect_uploaded()
        progress(2, f"已连接 {len(linked)} 个 → {linked}")
        return

    if act == "list":
        progress(1, "列出已安装")
        list_all()
        progress(2, "完成")
        return

    if act == "run":
        if not rest:
            progress(0, "需要命令")
            return
        cmd = " ".join(rest)
        progress(1, f"执行(去重) {cmd[:50]}")
        out, cached = run_once(cmd)
        progress(2, "缓存命中" if cached else "新执行")
        print(out)
        return

    if act == "cache-clear":
        progress(1, "清空命令缓存")
        msg = clear_cache()
        progress(2, msg)
        return

    progress(0, f"未知指令: {act}")

if __name__ == "__main__":
    main()
