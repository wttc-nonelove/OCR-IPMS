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
    return lines
