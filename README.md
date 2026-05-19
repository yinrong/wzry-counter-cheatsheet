# 王者荣耀 全英雄克制速查 / Honor of Kings Hero Counter Cheatsheet

> 单页手机版 PNG / HTML，覆盖全部 130+ 英雄的克制 (counter) 与被克制 (countered by) 关系。
> 数据用 JSON 维护，渲染用纯 Python (Pillow)，每次提交自动重建图片。

**关键词 / Keywords:** 王者荣耀 · 王者营地 · 克制 · 反制 · cheatsheet · 速查 · honor of kings · arena of valor · hero counter · matchup · wzry · 英雄克制表

---

## 预览 / Preview

![cheatsheet preview](output/cheatsheet_mobile.png)

完整 PNG: [`output/cheatsheet_mobile.png`](output/cheatsheet_mobile.png)
HTML 版: [`output/cheatsheet_mobile.html`](output/cheatsheet_mobile.html)

---

## 这是什么 / What is this

打游戏选英雄前看一眼对面阵容，瞄一下表就知道：
- **「克」**: 你这个英雄能压制谁（你打他容易）
- **「怕」**: 你这个英雄怕谁（被针对就难受）

每个英雄至少给出 3 个克制 + 3 个被克制对象，按拼音 A-Z 分组。

---

## 项目结构 / Layout

```
.
├── data/
│   ├── heroes.json       # 官方英雄列表 (来自 pvp.qq.com)
│   └── counters.json     # 克制关系数据 (人工维护, 见下方贡献流程)
├── src/
│   ├── render_html.py    # 渲染手机版 HTML
│   └── render_png.py     # 渲染手机版 PNG (Pillow, 无浏览器依赖)
├── output/
│   ├── cheatsheet_mobile.png
│   └── cheatsheet_mobile.html
├── .github/workflows/build.yml  # data/src 变更自动重建并 commit
└── requirements.txt
```

---

## 本地构建 / Build locally

```bash
pip install -r requirements.txt
python src/render_html.py
python src/render_png.py
```

需要系统安装中文字体 (Linux: `sudo apt install fonts-noto-cjk`).

---

## 贡献 / Contributing data

克制数据是 `data/counters.json`，结构很简单：

```json
{
  "鲁班七号": {
    "counter": ["程咬金", "廉颇", "白起", "夏侯惇"],
    "countered_by": ["李白", "韩信", "兰陵王", "阿轲"]
  }
}
```

**改一个英雄的克制关系：** 直接编辑 `data/counters.json`，提交 PR/push 到 main，GitHub Actions 自动重新生成 PNG/HTML。

**从哪里抓数据：**
- 王者营地 APP → 数据 → 英雄 → 选英雄 → 克制 → 段位选「巅峰赛/顶端」
- 接口需要登录态，目前没有公开 API
- 抓包工具 (Reqable / HttpCanary / Stream) 可以一次性拉全量

数据每个版本都会变，欢迎按版本号开 PR 更新。

---

## 数据说明 / Data caveat

- **英雄列表**: 来自 `https://pvp.qq.com/web201605/js/herolist.json`，实时官方数据
- **克制关系**: 当前版本基于「通用克制框架 + 历史版本认知」整理，**不是**王者营地实时巅峰赛数据
- 用于把握大方向，具体到分段差异 / 装备 / 阵容请以游戏内为准

---

## 自动化 / Automation

`.github/workflows/build.yml`：
- `data/` 或 `src/` 变更 → 自动跑渲染
- 输出图片 commit 回 `output/` 目录
- 也可手动触发 (`workflow_dispatch`)

---

## License

MIT
