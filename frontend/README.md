# Frontend - AI Research OS

Next.js 前端，ChatGPT 风格 UI，支持亮/暗主题切换。

## 功能

- ChatGPT 风格对话界面（欢迎页 + 对话页）
- 亮/暗主题切换（侧边栏底部按钮）
- 侧边栏：新聊天、快捷导航、最近记录
- 快捷操作：研究规划、论文检索、AI Scientist

## 环境要求

- **Node.js 20 LTS**（conda base 的 Node 26 不兼容 Next.js SWC）
- 使用项目内 `tools/node20` 或 `scripts/start-frontend.ps1`

## 开发

```powershell
$env:Path = "..\tools\node20;" + $env:Path
npm install
npm run dev
```

访问 http://localhost:2008

## 主题

- 默认亮色模式（参考 ChatGPT）
- 暗色模式：侧边栏底部 🌙/☀️ 切换
- 偏好保存在 `localStorage.theme`

## 环境变量

| 变量 | 说明 |
|------|------|
| `NEXT_PUBLIC_API_URL` | 后端 API 地址 (默认 http://localhost:8002) |
