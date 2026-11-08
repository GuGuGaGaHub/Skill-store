# Skills Store

完整 AI Agent Skills 商店

功能：搜索 / 安装 / 卸载 / 检测本地 / 上传连接 / 命令缓存（减 token）

## 安装

```bash

mkdir -p ~/.skills_store/local~/.skills_store/uploaded

# 把 skills_store.py 放到 ~/.skills_store/

chmod +x ~/.skills_store/skills_store.py

alias skills='python3  ~/.skills_store/skills_store.py'

## 命令:

skills search [关键词]
skills install <路径或名称>
skills uninstall <名称>
skills detect
skills upload <名称或路径>
skills connect
skills list
skills run "任意命令"
skills cache-clear
skills help

目录结构:

~/.skills_store/
├── skills_store.py
├── local/                   # 已安装
│   └── <skill-name>/
│       └── SKILL.md
├── uploaded/                # 已上传
│   └── <skill-name>/
│       └── SKILL.md
├── cmd_cache.json
├── index.json
└── state.json

---

**快速创建命令（复制执行）**

```bash
mkdir -p ~/.skills_store/local/example_skill ~/.skills_store/uploaded
# 然后把上面 skills_store.py 内容写入 ~/.skills_store/skills_store.py
# 把 example SKILL.md 写入 ~/.skills_store/local/example_skill/SKILL.md
echo '{}' > ~/.skills_store/cmd_cache.json
echo '{}' > ~/.skills_store/index.json
echo '{}' > ~/.skills_store/state.json
chmod +x ~/.skills_store/skills_store.py
python3 ~/.skills_store/skills_store.py help