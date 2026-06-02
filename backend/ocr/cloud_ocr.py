"""
Pluggable cloud OCR providers for handwriting and math.

This is the layer that turns the system into something usable for handwriting:
local OSS engines (Tesseract / EasyOCR) cannot reliably read student handwriting,
let alone notation like A', B-bar, ∑ m(0,1,4). Gradescope-quality recognition
comes from specialised cloud math/handwriting services.

Configure ONE of these via environment variables (no key → provider disabled):

    MATH_OCR_PROVIDER=mathpix
    MATHPIX_APP_ID=...
    MATHPIX_APP_KEY=...

    MATH_OCR_PROVIDER=gcv         # Google Cloud Vision (DOCUMENT_TEXT_DETECTION)
    GOOGLE_VISION_API_KEY=...     # simple API key (not service account)

    MATH_OCR_PROVIDER=azure       # Azure AI Vision Read API
    AZURE_VISION_KEY=...
    AZURE_VISION_ENDPOINT=https://<region>.api.cognitive.microsoft.com

    MATH_OCR_PROVIDER=auto        # pick the first provider whose creds are set

If no provider is configured, OCRProcessor falls back to the local ensemble.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover - requests is normally installed via fastapi extras
    requests = None  # type: ignore


# ── Result type ──────────────────────────────────────────────────────────────


@dataclass
class CloudOCRResult:
    """Output from a cloud OCR provider."""

    text: str
    provider: str
    confidence: Optional[float] = None
    latex: Optional[str] = None  # set by math-aware providers like Mathpix


# ── Tiny on-process LRU keyed by image hash ─────────────────────────────────


class _ResultCache:
    """
    Avoid double-billing and double-latency: same scanned page → same answer.
    Keyed by SHA256 of the raw image bytes plus the provider name.
    """

    def __init__(self, max_entries: int = 256) -> None:
        self._lock = threading.Lock()
        self._data: dict[str, CloudOCRResult] = {}
        self._order: list[str] = []
        self._max = max_entries

    @staticmethod
    def key(image_bytes: bytes, provider: str) -> str:
        h = hashlib.sha256()
        h.update(provider.encode("utf-8"))
        h.update(b"|")
        h.update(image_bytes)
        return h.hexdigest()

    def get(self, key: str) -> Optional[CloudOCRResult]:
        with self._lock:
            return self._data.get(key)

    def put(self, key: str, value: CloudOCRResult) -> None:
        with self._lock:
            if key in self._data:
                self._data[key] = value
                return
            self._data[key] = value
            self._order.append(key)
            while len(self._order) > self._max:
                old = self._order.pop(0)
                self._data.pop(old, None)


_RESULT_CACHE = _ResultCache()


# ── Provider base ───────────────────────────────────────────────────────────


class CloudOCRProvider:
    name: str = "base"

    def available(self) -> bool:  # pragma: no cover - abstract
        return False

    def recognize(self, image_bytes: bytes, mime: str = "image/png") -> Optional[CloudOCRResult]:
        raise NotImplementedError


# ── Mathpix (best for math + handwriting) ───────────────────────────────────


class MathpixProvider(CloudOCRProvider):
    """
    Mathpix is the gold standard for handwritten math.

    Docs: https://docs.mathpix.com/#process-an-image (POST /v3/text)
    Pricing: free trial credits, then per-call billing.
    """

    name = "mathpix"
    endpoint = "https://api.mathpix.com/v3/text"

    @staticmethod
    def _credentials() -> tuple[str, str]:
        return (
            os.getenv("MATHPIX_APP_ID", "").strip(),
            os.getenv("MATHPIX_APP_KEY", "").strip(),
        )

    def available(self) -> bool:
        app_id, app_key = self._credentials()
        return bool(app_id and app_key and requests)

    def recognize(self, image_bytes: bytes, mime: str = "image/png") -> Optional[CloudOCRResult]:
        app_id, app_key = self._credentials()
        if not (app_id and app_key and requests):
            return None
        try:
            b64 = base64.b64encode(image_bytes).decode("ascii")
            payload = {
                "src": f"data:{mime};base64,{b64}",
                "formats": ["text", "data", "html"],
                "data_options": {"include_latex": True},
                "math_inline_delimiters": ["$", "$"],
                "math_display_delimiters": ["$$", "$$"],
                "rm_spaces": False,
                "rm_fonts": True,
            }
            headers = {
                "app_id": app_id,
                "app_key": app_key,
                "Content-Type": "application/json",
            }
            resp = requests.post(  # type: ignore[union-attr]
                self.endpoint, data=json.dumps(payload), headers=headers, timeout=45
            )
            if resp.status_code != 200:
                logger.warning(
                    "Mathpix HTTP %s: %s", resp.status_code, resp.text[:200]
                )
                return None
            data = resp.json()
            text = (data.get("text") or "").strip()
            if not text:
                return None
            confidence = data.get("confidence")
            latex = data.get("latex_styled") or data.get("latex")
            return CloudOCRResult(
                text=text,
                provider=self.name,
                confidence=float(confidence) if confidence is not None else None,
                latex=latex if isinstance(latex, str) else None,
            )
        except Exception as ex:
            logger.warning("Mathpix recognise failed: %s", ex)
            return None


# ── Google Cloud Vision (DOCUMENT_TEXT_DETECTION) ───────────────────────────


class GoogleVisionProvider(CloudOCRProvider):
    """
    Google Cloud Vision document-text detection is excellent at general
    handwriting. Less math-aware than Mathpix, but very strong on English.

    Docs: https://cloud.google.com/vision/docs/handwriting
    """

    name = "gcv"
    endpoint = "https://vision.googleapis.com/v1/images:annotate"

    def __init__(self) -> None:
        self.api_key = os.getenv("GOOGLE_VISION_API_KEY", "").strip()

    def available(self) -> bool:
        return bool(self.api_key and requests)

    def recognize(self, image_bytes: bytes, mime: str = "image/png") -> Optional[CloudOCRResult]:
        if not self.available():
            return None
        try:
            b64 = base64.b64encode(image_bytes).decode("ascii")
            body = {
                "requests": [
                    {
                        "image": {"content": b64},
                        "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
                        "imageContext": {"languageHints": ["en"]},
                    }
                ]
            }
            url = f"{self.endpoint}?key={self.api_key}"
            resp = requests.post(  # type: ignore[union-attr]
                url, data=json.dumps(body), headers={"Content-Type": "application/json"}, timeout=45
            )
            if resp.status_code != 200:
                logger.warning(
                    "GoogleVision HTTP %s: %s", resp.status_code, resp.text[:200]
                )
                return None
            data = resp.json()
            responses = data.get("responses") or []
            if not responses:
                return None
            full = (responses[0].get("fullTextAnnotation") or {}).get("text") or ""
            if not full.strip():
                texts = responses[0].get("textAnnotations") or []
                if texts:
                    full = texts[0].get("description") or ""
            full = full.strip()
            if not full:
                return None
            return CloudOCRResult(text=full, provider=self.name, confidence=None)
        except Exception as ex:
            logger.warning("GoogleVision recognise failed: %s", ex)
            return None


# ── Azure AI Vision Read API ────────────────────────────────────────────────


class AzureReadProvider(CloudOCRProvider):
    """
    Azure Read API also reads handwriting well and is widely available.

    Docs: https://learn.microsoft.com/azure/ai-services/computer-vision/concept-ocr
    The Read API uses a two-step "analyze → poll operation-location" flow.
    """

    name = "azure"

    def __init__(self) -> None:
        self.key = os.getenv("AZURE_VISION_KEY", "").strip()
        self.endpoint = os.getenv("AZURE_VISION_ENDPOINT", "").strip().rstrip("/")

    def available(self) -> bool:
        return bool(self.key and self.endpoint and requests)

    def recognize(self, image_bytes: bytes, mime: str = "image/png") -> Optional[CloudOCRResult]:
        if not self.available():
            return None
        try:
            url = f"{self.endpoint}/vision/v3.2/read/analyze"
            headers = {
                "Ocp-Apim-Subscription-Key": self.key,
                "Content-Type": "application/octet-stream",
            }
            resp = requests.post(url, data=image_bytes, headers=headers, timeout=45)  # type: ignore[union-attr]
            if resp.status_code != 202:
                logger.warning(
                    "AzureRead submit HTTP %s: %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return None
            op_url = resp.headers.get("Operation-Location")
            if not op_url:
                return None
            poll_headers = {"Ocp-Apim-Subscription-Key": self.key}
            for _ in range(20):
                time.sleep(0.6)
                rs = requests.get(op_url, headers=poll_headers, timeout=30)  # type: ignore[union-attr]
                if rs.status_code != 200:
                    continue
                payload = rs.json()
                status = (payload.get("status") or "").lower()
                if status in ("succeeded",):
                    pages = (payload.get("analyzeResult") or {}).get("readResults") or []
                    lines: list[str] = []
                    for page in pages:
                        for ln in page.get("lines") or []:
                            txt = (ln.get("text") or "").strip()
                            if txt:
                                lines.append(txt)
                    text = "\n".join(lines).strip()
                    if not text:
                        return None
                    return CloudOCRResult(text=text, provider=self.name, confidence=None)
                if status in ("failed",):
                    return None
            return None
        except Exception as ex:
            logger.warning("AzureRead recognise failed: %s", ex)
            return None


# ── Manager ─────────────────────────────────────────────────────────────────


def _reload_ocr_env() -> None:
    """Re-read .env so Mathpix keys added while uvicorn is running take effect."""
    try:
        from dotenv import load_dotenv
        from pathlib import Path

        backend = Path(__file__).resolve().parent.parent
        load_dotenv(backend.parent / ".env", override=True)
        load_dotenv(backend / ".env", override=True)
    except Exception:
        pass


class CloudOCRManager:
    """
    Selects the active provider from env. Use `recognize_pil` for callers that
    have a PIL image (e.g. OCRProcessor) — it handles encoding and caching.
    """

    def __init__(self) -> None:
        self._providers: list[CloudOCRProvider] = [
            MathpixProvider(),
            GoogleVisionProvider(),
            AzureReadProvider(),
        ]
        self._chosen: Optional[CloudOCRProvider] = None
        self._refresh_provider()

    def _refresh_provider(self) -> None:
        _reload_ocr_env()
        choice = (os.getenv("MATH_OCR_PROVIDER") or "").strip().lower()
        if choice == "auto" or not choice:
            self._chosen = next((p for p in self._providers if p.available()), None)
        else:
            self._chosen = next(
                (p for p in self._providers if p.name == choice and p.available()),
                None,
            )
        if self._chosen:
            logger.info("Cloud OCR provider active: %s", self._chosen.name)
        elif choice and choice not in ("auto", ""):
            logger.warning(
                "MATH_OCR_PROVIDER=%s but credentials are missing or invalid",
                choice,
            )

    @property
    def active_provider_name(self) -> Optional[str]:
        if self._chosen is None:
            self._refresh_provider()
        return self._chosen.name if self._chosen else None

    def status(self) -> dict:
        self._refresh_provider()
        return {
            "active": self.active_provider_name,
            "available": [p.name for p in self._providers if p.available()],
            "configured": [p.name for p in self._providers],
        }

    def recognize_pil(self, image: Image.Image) -> Optional[CloudOCRResult]:
        if self._chosen is None:
            self._refresh_provider()
        if not self._chosen:
            return None
        image = image.convert("RGB")
        # Mathpix rejects very large PNG payloads — downscale and prefer JPEG for scans.
        max_edge = 2600
        long_side = max(image.width, image.height)
        if long_side > max_edge:
            scale = max_edge / float(long_side)
            image = image.resize(
                (int(image.width * scale), int(image.height * scale)),
                Image.Resampling.LANCZOS,
            )
        buf = io.BytesIO()
        use_jpeg = len(image.tobytes()) > 4_000_000 or max(image.size) > 2200
        if use_jpeg:
            image.save(buf, format="JPEG", quality=88, optimize=True)
            mime = "image/jpeg"
        else:
            image.save(buf, format="PNG", optimize=True)
            mime = "image/png"
        raw = buf.getvalue()
        key = _RESULT_CACHE.key(raw, self._chosen.name)
        cached = _RESULT_CACHE.get(key)
        if cached is not None:
            return cached
        result = self._chosen.recognize(raw, mime=mime)
        if result is not None:
            _RESULT_CACHE.put(key, result)
        return result
