# 搏闻 · 交接说明（2026-11-11）

给下一个对话里的 Claude 看：从这里接着做。

## 现在的状态
- 正式版（旧）：https://bo9348699-hub.github.io/ ，根目录 index.html
- 新版 v1 预览：https://bo9348699-hub.github.io/next/ （等用户验收后替换根目录）
  - 首页 7 个 3D 物件：globe=国际 coin=经济 chip=AI bulb=副业 lens=深度 stack=拆解 plane=收件箱
  - 3D：Blender 5.3（pip 包 bpy，需 Python 3.13 虚拟环境）建模 → glTF-Transform 压缩 → three.js r160 单画布分区绘制（next/assets/stage3d.js）
  - 失败时自动回退到 next/assets/*.webp 图片（豆包生成 + rembg 抠图）
  - 功能：分区页、底部详情、多方圆桌、盖章、进度环、速读、动画开关、深浅色、收件箱（只存本机）
- 数据：data/index.json + data/issues/<日期>.json。字段见 data/issues/2026-11-11.json（items/side/deeps/deep/teardowns，item 可带 geo）
- 定时任务「搏闻 早报 + 晚报」：每天 6:40、20:40（上海时间）自动写当天这期并推送到本仓库

## 源文件
- src/blender/build.py：7 个物件的 Blender 建模脚本（`python build.py -- coin` 只做一个）
- src/blender/pack.sh：用 glTF-Transform 压缩到 next/assets/models/
- src/content/extra.py：第 1 期副业 + 拆解内容

## ⚠️ 定时任务的问题（优先处理）
- 2026-11-11 20:40 晚报和 2026-11-12 6:40 早报，定时任务都显示“成功”，但仓库里没有任何新提交（晚报和早报都没推上来）。
- 第 2 期（2026-11-12）是 Claude 在原对话里手动补做、推送的。
- 原因待查：可能是定时任务的新会话里 add_repo 需要确认、没有推送权限，或者推送被拦截。
- 下一步：打开定时任务最近一次运行的会话看报错；修好前，每天检查一次仓库有没有新的一期。

## 还没做 / 下一步
1. 用户验收 /next/，按反馈改；满意后替换根目录
2. 反馈同步：现在“有用/这条有问题/收件箱”只存在用户设备上。计划：GitHub 私有仓库 + 用户自己粘贴的 token
3. 灯泡发光偏弱、纸飞机造型简单、分区页小图标仍是图片
4. AI 外包（省额度）：
   - 已通：通过用户电脑上的内置浏览器 JS 调用免费 API（智谱 key 存在内置浏览器 open.bigmodel.cn 的 localStorage，键名 __bowen_glm_key）
   - 云端工作区连不上这些 API（网络白名单），要用户在 claude.ai 设置 → Capabilities 加域名
   - 结论：智谱 glm-4-flash 只适合机械活（找源，含公众号链接；挑列表）；写作和总结质量差；glm-4.7-flash 高峰被限流
   - 下一步：试更强的免费模型（Gemini，需用户谷歌账号；或硅基流动）
   - 公众号文章在浏览器里会触发人机验证，不能绕过
5. 用户电脑上的 AI：豆包、DeepSeek Harness、Codex（已登录）、Grok Bot（未登录）

## 用户的工作方式（必须遵守）
- 先把需求问清楚，等用户说“确认”，再拆步骤；每步优先用成熟的软件、工具、插件，不要从零手写
- 在确认过的范围内自己决定、直接做，只在需要登录、花钱、不可撤销的操作时停下来
- 每步做完对照目标逐条检查，有差距主动说；降低标准之前先说
- 用大白话，结论先说
