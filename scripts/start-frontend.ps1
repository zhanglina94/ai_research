# 使用 Node 20 启动前端（conda base 自带 Node 26 不兼容 Next.js）
$env:Path = "$PSScriptRoot\..\tools\node20;" + $env:Path
Set-Location "$PSScriptRoot\..\frontend"
npm run dev
