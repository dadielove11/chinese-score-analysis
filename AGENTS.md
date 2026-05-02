# 项目接手说明

## 项目定位

这是一个面向初中语文教师的离线成绩分析工具，运行形态是本地 Flask Web 应用，可用 PyInstaller 打包成 Windows 离线版。项目不依赖 GPT、云端模型或外部服务；学生成绩、上传图片和导出结果都应保留在本机。

## 常用命令

```powershell
python app.py
python tests\test_defaults_and_export.py
python tests\test_combined_chart.py
python -m compileall app.py student_analysis tests
.\build_release.bat
```

默认访问地址从 `http://127.0.0.1:8765` 开始；如果端口被占用，`app.py` 会自动向后寻找可用端口。

## 代码结构

- `app.py`：程序入口，负责选择端口、启动浏览器和运行 Flask。
- `student_analysis/`：核心业务逻辑，包括导入、分析、图表、存储、OCR 和 Web 路由。
- `templates/`：Jinja2 页面模板。
- `static/`：页面样式。
- `tests/`：轻量测试脚本。
- `tools/create_release_package.py`：发布包与用户说明文档生成脚本。
- `StudentAnalysis.spec`：PyInstaller 打包配置。

## 当前关键流程

- 首页使用统一入口 `/import/files`，根据文件类型分流到 Excel 预览或图片校对。
- `/import/excel` 和 `/import/image` 保留为兼容路由，内部仍复用统一导入后的预览/校对逻辑。
- Excel 模板下载路由是 `/template.xlsx`。
- Excel 和图片导入都必须先进入确认/校对页，不能直接写入成绩数据。
- 删除记录和清空全部数据均有 `confirm()` 二次确认，**不要绕过**。
- 考试顺序通过 ↑↓ 按钮调整（JS 重排 hidden input），后端接收 `order_<exam_name>` 字段。
- 成绩、分数线和考试顺序保存在本地 `data/`。
- 上传临时文件保存在本地 `uploads/`；解析出错时 `_cleanup_paths()` 会清理已落盘文件。

## 编辑边界

- 不要提交真实学生成绩、上传截图、导出 Excel、打包产物或本地运行数据。
- `.gitignore` 应持续排除 `data/`、`uploads/`、`build/`、`dist/`、`release/`。
- 修改用户可见流程时，同步更新 `README.md` 和 `tools/create_release_package.py` 里的发布包说明。
- 前端界面保持教师工作流优先：入口少、确认页清楚、危险操作有二次确认。
- 无成绩数据时首页显示三步新手引导（`.onboarding-panel`），改版时不要删除此逻辑。
