# CadQuery Assistant Starter


本仓库当前提供一个最小可运行的“Planner → Environment → Tools”闭环骨架：
- **env/**: 受限执行器 `CQEnv.run(code)`，返回几何摘要与图像占位。
- **tools/**: JSON→Sketch 适配、几何识别、约束检查占位。
- **planner/**: 基于 OpenAI Chat Completions 的极简 Planner（输出 plan+action_code）。
- **runners/**: 两个演示脚本，验证执行闭环。


## 下一步
1. 在 `prompts/system_tools.md` 补充论任务与工具清单，确保模型了解接口。
2. 把 `runners/demo_sketch_to_solid.py` 改为 `planner.OpenAIPlannerChain` 驱动的循环：
- 初始 `feedback=None`
- `planner.step(GOAL, feedback)` → 取 `action_code`
- `env.run(action_code)` → 得到 `feedback`
- 根据 `terminate` 字段决定是否停止
3. 增强渲染：用 pythonOCC/VTK 或 trimesh 场景快照生成 PNG 回馈给模型。
4. 完善 `constraint_checker`：施加前后采样关键点，阈值判定漂移。
5. 增补评测：体积/面积/SSIM/Chamfer 等指标，记录每一步日志与图像。