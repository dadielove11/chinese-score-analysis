from __future__ import annotations

from pathlib import Path


def image_to_text(path: Path) -> tuple[str, str | None]:
    rapid_text, rapid_error = rapidocr_image_to_table(path)
    if rapid_text:
        return rapid_text, None

    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return "", rapid_error or "当前程序缺少图片识别组件。图片已上传，但需要手动录入或粘贴表格内容。"

    try:
        text = pytesseract.image_to_string(Image.open(path), lang="chi_sim+eng")
    except Exception as exc:  # OCR depends on a native executable that may not be bundled yet.
        message = str(exc)
        if "tesseract is not installed" in message or "not in your PATH" in message:
            return "", "当前电脑没有安装离线 OCR 引擎，暂时不能自动识别图片。请先手动录入或粘贴表格内容；后续可把 Tesseract 中文 OCR 一起打包进 exe。"
        return "", f"图片自动识别失败：{exc}"
    return text, None


def rapidocr_image_to_table(path: Path) -> tuple[str, str | None]:
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:
        return "", f"当前程序缺少离线 OCR 组件：{exc}。图片已上传，但需要手动录入或粘贴表格内容。"

    try:
        result, _ = RapidOCR()(str(path))
    except Exception as exc:
        return "", f"图片自动识别失败：{exc}"
    if not result:
        return "", "图片中没有识别到文字，请手动录入或换一张更清晰的截图。"

    cells = []
    for box, text, _score in result:
        xs = [point[0] for point in box]
        ys = [point[1] for point in box]
        cells.append(
            {
                "x": sum(xs) / len(xs),
                "y": sum(ys) / len(ys),
                "h": max(ys) - min(ys),
                "text": str(text).strip(),
            }
        )
    rows = group_cells_into_rows(cells)
    lines = ["\t".join(cell["text"] for cell in row) for row in rows if row]
    return "\n".join(lines), None


def group_cells_into_rows(cells: list[dict[str, object]]) -> list[list[dict[str, object]]]:
    if not cells:
        return []
    ordered = sorted(cells, key=lambda cell: (float(cell["y"]), float(cell["x"])))
    avg_height = sum(float(cell["h"]) for cell in ordered) / len(ordered)
    threshold = max(10.0, avg_height * 0.65)
    rows: list[list[dict[str, object]]] = []
    row_centers: list[float] = []

    for cell in ordered:
        y = float(cell["y"])
        target = None
        for index, center in enumerate(row_centers):
            if abs(y - center) <= threshold:
                target = index
                break
        if target is None:
            rows.append([cell])
            row_centers.append(y)
            continue
        rows[target].append(cell)
        row_centers[target] = (row_centers[target] * (len(rows[target]) - 1) + y) / len(rows[target])

    return [sorted(row, key=lambda cell: float(cell["x"])) for row in rows]
