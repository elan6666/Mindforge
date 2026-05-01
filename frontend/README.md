# Mindforge 前端

该目录是 Mindforge 的 Web App 前端，使用 React、TypeScript 和 Vite 构建。

## 职责

- 提供类似 Codex 的工作台界面。
- 让用户提交任务、选择 Preset、查看结果和历史。
- 展示多 Agent 阶段输出、任务 metadata、审批状态和 GitHub/论文上下文。
- 提供模型控制中心和 Provider/API 管理中心。

## 本地开发

```powershell
cd frontend
npm install
npm run dev
```

默认后端地址：

- `http://127.0.0.1:8000/api`

如需覆盖：

```powershell
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000/api"
```

## 验证

```powershell
npm run test
npm run build
```
