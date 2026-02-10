from __future__ import annotations

import asyncio
import http.server
import socketserver
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

PDF_MARGIN = "0.4in"
STATIC_DIR = Path("./static").resolve()
STATIC_PORT = 8001
MAX_CONCURRENT_PDFS = 5


class GenerateRequest(BaseModel):
    language: str = "en"
    data: dict[str, Any]


def create_directory_handler(directory: Path) -> type[http.server.SimpleHTTPRequestHandler]:
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(directory), **kwargs)

        def log_message(self, _fmt: str, *_args: Any) -> None:
            return

    return Handler


class PDFService:
    def __init__(self) -> None:
        self.browser = None
        self.playwright = None
        self.httpd: socketserver.TCPServer | None = None
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_PDFS)

    async def start(self) -> None:
        handler = create_directory_handler(STATIC_DIR)
        self.httpd = socketserver.TCPServer(("", STATIC_PORT), handler)  # type: ignore[arg-type]
        thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        thread.start()

        from playwright.async_api import async_playwright

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()

    async def stop(self) -> None:
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()

    async def generate_pdf(self, data: dict[str, Any], language: str) -> bytes:
        if language not in data:
            raise HTTPException(
                status_code=400,
                detail=f"Language '{language}' not found in data. Available: {list(data.keys())}",
            )

        async with self.semaphore:
            page = await self.browser.new_page()
            try:
                await page.goto(f"http://localhost:{STATIC_PORT}/cv_yaml.html")
                await page.wait_for_selector("#cv-container")

                await page.evaluate(
                    """([data, lang]) => {
                        cvData = data;
                        currentLang = lang;
                        renderCV();
                    }""",
                    [data, language],
                )

                await page.wait_for_selector("#cv")

                pdf_bytes = await page.pdf(
                    format="A4",
                    margin={
                        "top": PDF_MARGIN,
                        "right": PDF_MARGIN,
                        "bottom": PDF_MARGIN,
                        "left": PDF_MARGIN,
                    },
                    print_background=True,
                    prefer_css_page_size=True,
                )
                return pdf_bytes
            finally:
                await page.close()


pdf_service = PDFService()


@asynccontextmanager
async def lifespan():
    await pdf_service.start()
    yield
    await pdf_service.stop()


app = FastAPI(title="CV PDF Generator API")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/generate")
async def generate_pdf(request: GenerateRequest):
    pdf_bytes = await pdf_service.generate_pdf(request.data, request.language)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=cv.pdf"},
    )
