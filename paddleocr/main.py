from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Any
import os

from fastapi import FastAPI, File, UploadFile

app = FastAPI(title="PaddleOCR Service")
_ocr: Any | None = None
_load_error: str | None = None

os.environ.setdefault("FLAGS_use_mkldnn", "false")
os.environ.setdefault("FLAGS_enable_mkldnn", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")


def get_ocr():
    global _ocr, _load_error
    if _ocr is not None:
        return _ocr
    try:
        from paddleocr import PaddleOCR

        _ocr = PaddleOCR(
            use_angle_cls=True,
            lang="ch",
            ocr_version="PP-OCRv3",
            show_log=False,
            use_gpu=False,
            use_mkldnn=False,
            ir_optim=False,
            cpu_threads=1,
        )
        _load_error = None
        return _ocr
    except Exception as exc:  # pragma: no cover - depends on runtime libs
        _load_error = str(exc)
        raise


@app.get("/health")
def health():
    return {"code": 200, "message": "ok", "data": {"status": "ready", "model_loaded": _ocr is not None, "load_error": _load_error}}


@app.post("/api/v1/ocr")
async def ocr(file: UploadFile = File(...), type: str = "contract"):
    suffix = Path(file.filename or "upload.png").suffix or ".png"
    content = await file.read()
    with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        engine = get_ocr()
        lines = _recognize_path(engine, Path(tmp_path))
        confidence = sum(line["confidence"] for line in lines) / len(lines) if lines else 0
        raw_text = "\n".join(line["text"] for line in lines if line.get("text"))
        return {"code": 200, "message": "识别成功", "data": {"type": type, "lines": lines, "raw_text": raw_text, "confidence": confidence}}
    except Exception as exc:
        return {"code": 500, "message": "识别失败", "data": {"type": type, "lines": [], "confidence": 0, "error": str(exc)}}
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _recognize_path(engine: Any, path: Path) -> list[dict]:
    if path.suffix.lower() == ".pdf":
        return _recognize_pdf(engine, path)
    return _parse_result(engine.ocr(str(path), cls=True), 1)


def _recognize_pdf(engine: Any, path: Path) -> list[dict]:
    import fitz

    lines: list[dict] = []
    with fitz.open(str(path)) as document, TemporaryDirectory() as tmp_dir:
        for page_index, page in enumerate(document, start=1):
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image_path = Path(tmp_dir) / f"page_{page_index}.png"
            pixmap.save(str(image_path))
            lines.extend(_parse_result(engine.ocr(str(image_path), cls=True), page_index))
    return lines


def _parse_result(result: Any, page_no: int) -> list[dict]:
    lines = []
    for page in result or []:
        for item in page or []:
            if len(item) < 2:
                continue
            box = item[0]
            text, score = item[1]
            lines.append({"text": text, "box": box, "confidence": float(score), "page": page_no})
    # 按 Y 坐标分组排序改善表格/发票的阅读顺序
    return _sort_by_layout(lines)


def _sort_by_layout(lines: list[dict]) -> list[dict]:
    """按 Y 坐标分组后组内按 X 排序，使表格数据更接近逻辑阅读顺序."""
    if not lines:
        return lines
    # 计算平均行高作为分组阈值
    heights = [max(p["y"] for p in _box_points(line["box"])) - min(p["y"] for p in _box_points(line["box"])) for line in lines]
    avg_height = sum(heights) / len(heights) if heights else 10
    # 按 Y 坐标分组
    y_threshold = avg_height * 0.6
    lines_with_y = []
    for line in lines:
        points = _box_points(line["box"])
        mid_y = sum(p["y"] for p in points) / len(points)
        min_x = min(p["x"] for p in points)
        lines_with_y.append((mid_y, min_x, line))
    # 排序：先 Y 后 X
    lines_with_y.sort(key=lambda item: (round(item[0] / y_threshold), item[1]))
    return [item[2] for item in lines_with_y]


def _box_points(box) -> list[dict]:
    """从检测框提取点坐标列表."""
    points = []
    for pt in box:
        if isinstance(pt, (list, tuple)) and len(pt) >= 2:
            points.append({"x": float(pt[0]), "y": float(pt[1])})
    if not points and len(box) == 4 and all(isinstance(v, (int, float)) for v in box):
        # 平铺格式 [x1, y1, x2, y2]
        points = [{"x": float(box[0]), "y": float(box[1])}, {"x": float(box[2]), "y": float(box[3])}]
    return points
