# CadQuery Assistant Starter


本仓库当前提供一个最小可运行的“Planner → Environment → Tools”闭环骨架：
- **env/**：受限执行器 `CQEnv.run(code)`，执行 LLM 生成的 CadQuery 代码，返回几何摘要与渲染图像。  
- **planners/**：基于 OpenAI Chat Completions 的极简 Planner，输出 `plan + action_code`。  
- **runners/**：演示脚本（`text_to_cq_miniloop.py` 等），验证文本→CadQuery→渲染的完整流程。  
- **utils/**：通用函数（日志、保存、渲染调度等）。  
- **result/**：执行产物（代码、图片、summary.json）。
## 当前特性
1. ✅ 文本 → CadQuery 代码生成（调用 LLM Planner）  
2. ✅ `CQEnv` 自动执行并捕获错误  
3. ✅ 自动保存运行日志与渲染结果（时间戳文件夹）  
4. ✅ 支持 `trimesh` 光栅渲染 + 包围盒线框回退  
5. ✅ 独立测试脚本：`render_smoketest.py` 验证离屏渲染是否生效，`opengl_probe.py` 检测 OpenGL/PyOpenGL 上下文。


## 下一步
1. 引入循环机制
2. 实现多模态输入（草图）
3. 增强渲染：替换为真正的三维光照渲染（pyrender / VTK / pythonOCC），输出多视角快照（front / side / iso）。
4. RAG增强