from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from fastapi import FastAPI, File, UploadFile

app = FastAPI(title="PaddleOCR Service")
_ocr: Any | None = None
_load_error: str | None = None


def get_ocr():
    global _ocr, _load_error
    if _ocr is not None:
        return _ocr
    try:
        from paddleocr import PaddleOCR

        _ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
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
        result = engine.ocr(tmp_path, cls=True)
        lines = []
        for page in result or []:
            for item in page or []:
                if len(item) < 2:
                    continue
                box = item[0]
                text, score = item[1]
                lines.append({"text": text, "box": box, "confidence": float(score)})
        confidence = sum(line["confidence"] for line in lines) / len(lines) if lines else 0
        return {"code": 200, "message": "识别成功", "data": {"type": type, "lines": lines, "confidence": confidence}}
    except Exception as exc:
        return {"code": 500, "message": "识别失败", "data": {"type": type, "lines": [], "confidence": 0, "error": str(exc)}}
    finally:
        Path(tmp_path).unlink(missing_ok=True)
