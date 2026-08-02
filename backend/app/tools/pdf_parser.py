"""PDF download and text extraction."""

import logging
from pathlib import Path

import httpx
from pypdf import PdfReader

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _papers_dir() -> Path:
    path = Path(settings.storage_path) / "papers"
    path.mkdir(parents=True, exist_ok=True)
    return path


async def fetch_arxiv_pdf(arxiv_id: str) -> str | None:
    clean_id = arxiv_id.replace("arXiv:", "").strip()
    pdf_url = f"https://arxiv.org/pdf/{clean_id}.pdf"
    dest = _papers_dir() / f"{clean_id.replace('/', '_')}.pdf"

    if dest.exists():
        return str(dest)

    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(pdf_url)
            response.raise_for_status()
            dest.write_bytes(response.content)
            return str(dest)
    except Exception as e:
        logger.error("PDF download failed for %s: %s", arxiv_id, e)
        return None


def extract_text_from_pdf(pdf_path: str, max_pages: int = 20) -> str:
    try:
        reader = PdfReader(pdf_path)
        pages = reader.pages[:max_pages]
        return "\n\n".join(page.extract_text() or "" for page in pages)
    except Exception as e:
        logger.error("PDF extraction failed for %s: %s", pdf_path, e)
        return ""
