from __future__ import annotations

from html import escape
from pathlib import Path
from shutil import copytree, rmtree
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "dist" / "StudentAnalysis"
RELEASE_ROOT = ROOT / "release"
PACKAGE_DIR = RELEASE_ROOT / "初中语文学情分析工具_离线版"
ZIP_PATH = RELEASE_ROOT / "初中语文学情分析工具_离线版.zip"

GUIDE_TEXT = """初中语文学情分析工具（离线版）使用说明

一、使用前
1. 收到压缩包后，先右键“全部解压”或“解压到当前文件夹”。
2. 不要在压缩包里面直接双击运行。
3. 解压后进入文件夹“初中语文学情分析工具_离线版”。
4. 双击 StudentAnalysis.exe。
5. 程序会自动打开浏览器页面；如果没有自动打开，请在浏览器地址栏输入：http://127.0.0.1:8765

二、重要提醒
1. 不能只移动或发送 StudentAnalysis.exe，必须保留整个文件夹。
2. _internal 文件夹不要删除、不要改名。
3. 本工具离线运行，不需要登录，也不需要联网。
4. 成绩数据保存在本文件夹下的 data 目录里。

三、导入成绩
1. 在首页“导入与校对”区域，按文件类型选择“Excel 表格”或“成绩截图”。
2. Excel 支持一次选择一个或多个 .xlsx/.xlsm 文件；如没有固定格式，可先点击“下载 Excel 模板”参考表头。
3. 图片导入适合表格截图，可一次选择一张或多张图片。
4. 为了方便校对，一次导入请只选择同一种类型文件：要么全是 Excel，要么全是图片。
5. Excel 上传后会进入确认页，按文件和工作表显示识别情况；如果没有读出班级或考试名称，可在确认页逐项手动填写。
6. 图片上传后每张图会单独显示一个校对区域，请逐张确认班级、考试名称和识别结果，再统一导入。

四、查看分析
1. 在“班级总览”选择 7班或8班。
2. 在“个人趋势”选择学生，可查看个人几次成绩和班级位次变化。
3. 如果某个学生只有部分考试数据，图中会标出“缺”，下方会显示已录入和缺少的考试。
4. 考试顺序可以在“班级总览”里手动调整。
5. 个人趋势图中红色表示成绩、绿色表示位次；数字标签带同色边框，避免和另一条线混淆。

五、分数线
1. 可以自己设置优秀、良好、及格、低分线。
2. 优秀率、良好率、及格率按“达到对应分数线及以上”统计。
3. 低分率按“低于低分线”统计。

六、数据管理
1. 可以按班级、考试、学生删除数据。
2. “清空全部数据”会删除所有成绩，请谨慎使用。
3. 建议重要数据导出 Excel 后再删除。

七、导出
1. 点击右上角“导出 Excel”。
2. 导出的文件包含成绩明细、班级总览、进退步概览。
3. 在个人趋势区域点击“保存趋势大图 PNG”，会保存当前页面上看到的趋势图。
4. 点击“下载全班趋势图”可以把当前班级所有学生的趋势图打包下载。

八、常见问题
1. 双击没有反应：请确认已经解压，并且 _internal 文件夹还在。
2. 浏览器打不开：手动访问 http://127.0.0.1:8765。
3. Windows 提示未知发布者：这是本地打包程序的常见提示，选择“更多信息”后继续运行即可。
4. 换电脑使用：把整个文件夹复制过去即可；如果也要带已有成绩，请一起复制 data 文件夹。
"""


def main() -> None:
    if not DIST_DIR.exists():
        raise SystemExit(f"打包目录不存在：{DIST_DIR}")

    RELEASE_ROOT.mkdir(exist_ok=True)
    if PACKAGE_DIR.exists():
        rmtree(PACKAGE_DIR)
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    copytree(DIST_DIR, PACKAGE_DIR)
    (PACKAGE_DIR / "data").mkdir(exist_ok=True)
    (PACKAGE_DIR / "uploads").mkdir(exist_ok=True)
    (PACKAGE_DIR / "使用说明.txt").write_text(GUIDE_TEXT, encoding="utf-8")
    (PACKAGE_DIR / "先读我.txt").write_text(
        "请先解压整个压缩包，再双击 StudentAnalysis.exe。不要只发送或只运行单独的 exe 文件。详细步骤见“使用说明.txt”或“使用说明.docx”。\n",
        encoding="utf-8",
    )
    write_docx(PACKAGE_DIR / "使用说明.docx", GUIDE_TEXT)
    write_zip(ZIP_PATH, PACKAGE_DIR)
    print(PACKAGE_DIR)
    print(ZIP_PATH)
    print(f"{ZIP_PATH.stat().st_size / 1024 / 1024:.1f} MB")


def write_docx(path: Path, text: str) -> None:
    body_parts = []
    for line in text.strip().splitlines():
        stripped = line.strip()
        if not stripped:
            body_parts.append("<w:p/>")
            continue
        if stripped.startswith("初中语文"):
            style = '<w:pPr><w:pStyle w:val="Title"/></w:pPr>'
        elif len(stripped) <= 8 and stripped[1:2] == "、":
            style = '<w:pPr><w:pStyle w:val="Heading1"/></w:pPr>'
        else:
            style = ""
        body_parts.append(
            "<w:p>"
            + style
            + '<w:r><w:t xml:space="preserve">'
            + escape(stripped)
            + "</w:t></w:r></w:p>"
        )

    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {"".join(body_parts)}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>
"""
    styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:rFonts w:ascii="Microsoft YaHei" w:eastAsia="Microsoft YaHei"/><w:sz w:val="22"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:rPr><w:b/><w:rFonts w:ascii="Microsoft YaHei" w:eastAsia="Microsoft YaHei"/><w:sz w:val="36"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:rPr><w:b/><w:rFonts w:ascii="Microsoft YaHei" w:eastAsia="Microsoft YaHei"/><w:sz w:val="28"/></w:rPr></w:style>
</w:styles>
"""
    with ZipFile(path, "w", ZIP_DEFLATED) as docx:
        docx.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>""",
        )
        docx.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>""",
        )
        docx.writestr(
            "word/_rels/document.xml.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>""",
        )
        docx.writestr("word/document.xml", document_xml)
        docx.writestr("word/styles.xml", styles_xml)


def write_zip(zip_path: Path, package_dir: Path) -> None:
    with ZipFile(zip_path, "w", ZIP_DEFLATED) as archive:
        for item in package_dir.rglob("*"):
            if item.is_file():
                archive.write(item, item.relative_to(RELEASE_ROOT))
        for empty_dir in [package_dir / "data", package_dir / "uploads"]:
            archive.write(empty_dir, empty_dir.relative_to(RELEASE_ROOT))


if __name__ == "__main__":
    main()
