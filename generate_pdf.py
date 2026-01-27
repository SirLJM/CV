#!/usr/bin/env python3

from __future__ import annotations

import argparse
import asyncio
import http.server
import socket
import socketserver
import subprocess
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

PDF_MARGIN = '0.5in'

def is_port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("", port))
            return True
        except OSError:
            return False

def wait_for_server(port: int, timeout: float = 5.0) -> bool:
    import time
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("localhost", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False

def create_directory_handler(directory: Path) -> type[http.server.SimpleHTTPRequestHandler]:
    class DirectoryHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(directory), **kwargs)

        def log_message(self, _fmt: str, *_args: Any) -> None:
            return
    return DirectoryHTTPRequestHandler


class CVPDFGenerator:
    def __init__(self, cv_folder: str = "./static", port: int = 8000) -> None:
        self.cv_folder = Path(cv_folder).resolve()
        self.port = port
        self.httpd: socketserver.TCPServer | None = None

    def start_server(self) -> None:
        if not is_port_available(self.port):
            raise RuntimeError(f"Port {self.port} is already in use. Try --port with a different number.")

        handler = create_directory_handler(self.cv_folder)
        self.httpd = socketserver.TCPServer(("", self.port), handler)  # type: ignore[arg-type]
        server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        server_thread.start()

        if not wait_for_server(self.port):
            raise RuntimeError(f"Server failed to start on port {self.port}")

        print(f"✓ Server started at http://localhost:{self.port}")

    def stop_server(self) -> None:
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            print("✓ Server stopped")

    async def generate_pdf_playwright(self, language: str = "en", output_file: str | None = None) -> None:
        from playwright.async_api import async_playwright

        if not output_file:
            output_file = f"Lukasz Wisniewski CV {language}.pdf"

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            url = f"http://localhost:{self.port}/cv_yaml.html"
            await page.goto(url)
            await page.wait_for_selector("#cv")

            if language == "pl":
                await page.click("button:has-text('Polski')")
                await page.wait_for_timeout(1000)

            await page.pdf(
                path=output_file,
                format='A4',
                margin={  # type: ignore[arg-type]
                    'top': PDF_MARGIN,
                    'right': PDF_MARGIN,
                    'bottom': PDF_MARGIN,
                    'left': PDF_MARGIN
                },
                print_background=True,
                prefer_css_page_size=True
            )

            await browser.close()
            print(f"✓ PDF generated: {output_file}")

    async def generate_both_pdfs(self) -> None:
        print("Generating English PDF...")
        await self.generate_pdf_playwright("en", "Lukasz Wisniewski CV en.pdf")

        print("Generating Polish PDF...")
        await self.generate_pdf_playwright("pl", "Lukasz Wisniewski CV pl.pdf")

        print("✓ Both PDFs generated successfully!")

    @staticmethod
    def install_requirements() -> None:
        try:
            import playwright
        except ImportError:
            print("Installing playwright...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
            subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
            print("✓ Playwright installed")

    async def run(self) -> None:
        print("🚀 CV PDF Generator Starting...")

        if not (self.cv_folder / "cv_yaml.html").exists():
            print(f"❌ Error: cv_yaml.html not found in {self.cv_folder}")
            return

        if not (self.cv_folder / "content.yaml").exists():
            print(f"❌ Error: content.yaml not found in {self.cv_folder}")
            return

        try:
            self.install_requirements()
            self.start_server()
            await self.generate_both_pdfs()
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            self.stop_server()


def generate_pdf_weasyprint(language: str = "en", output_file: str | None = None, base_path: Path | None = None) -> None:
    try:
        from weasyprint import HTML, CSS
        import yaml
    except ImportError:
        print("Installing weasyprint and pyyaml...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "weasyprint", "pyyaml"])
        from weasyprint import HTML, CSS
        import yaml

    if base_path is None:
        base_path = Path("./static")

    if not output_file:
        output_file = f"Lukasz Wisniewski CV_{language}_weasyprint.pdf"

    with open(base_path / 'content.yaml', 'r', encoding='utf-8') as f:
        cv_data = yaml.safe_load(f)

    static_html = create_static_html(cv_data[language], cv_data[language].get('labels', {}))

    HTML(string=static_html, base_url=str(base_path)).write_pdf(
        output_file,
        stylesheets=[CSS(base_path / 'styles/cv.css')]
    )
    print(f"✓ PDF generated with WeasyPrint: {output_file}")


def render_experience(experiences: list[dict]) -> str:
    items = []
    for exp in experiences:
        details = exp['details']
        if len(details) == 1 and '•' not in details[0]:
            details_html = details[0]
        else:
            details_html = "<ul>" + "".join(f"<li>{d}</li>" for d in details) + "</ul>"

        company_html = f"<span class=\"experience-company\">{exp['company']}</span><br/>" if exp.get('company') else ""

        items.append(
            f'<div class="experience-year">{exp["years"]}</div>'
            f'<div>'
            f'<span class="experience-position">{exp["position"]}</span><br/>'
            f'{company_html}'
            f'{details_html}'
            f'</div>'
        )
    return "".join(items)


def render_skills(skills: list[dict]) -> str:
    return "".join(
        f'<span class="technology-name">{s["name"]}</span><span class="technology-description">{s["description"]}</span>'
        for s in skills
    )


def render_education(education: list[dict]) -> str:
    return "".join(
        f'''<div class="education-year">{e['year']}</div>
            <div><span class="education-detail">{e['detail']}</span><br/><span class="education-org">{e['org']}</span></div>'''
        for e in education
    )


def render_languages(languages: list[dict]) -> str:
    return "".join(
        f'<span class="language-name">{l["name"]}</span><span>{l["level"]}</span>'
        for l in languages
    )


def render_disabilities(disabilities: list[dict]) -> str:
    return "".join(
        f'<span class="disability-name">{d["name"]}</span><span>{d["level"]}</span>'
        for d in disabilities
    )


def render_projects(projects: list[dict], labels: dict) -> str:
    items = []
    for p in projects:
        items.append(f'''
            <h2 class="workproject-heading">{p['years']} {p['title']}</h2>
            <div class="workproject-intro">{p['intro']}</div>
            <div class="workproject-details">
                <strong>{labels.get('position', 'Position')}</strong><div>{p['position']}</div>
                <strong>{labels.get('technology', 'Technology')}</strong><div>{p['technology']}</div>
                <strong>{labels.get('role', 'Role')}</strong><div>{p['role']}</div>
            </div>
        ''')
    return "".join(items)


def create_static_html(data: dict, labels: dict) -> str:
    return f'''<!DOCTYPE html>
<html>
<head>
    <title>{data['name']}</title>
    <link rel="stylesheet" href="styles/cv.css">
    <meta charset="utf-8">
</head>
<body>
    <div id="cv">
        <section id="header">
            <div id="name-container">
                <img id="profile-picture" src="images/CV_1024x1024.png" alt="profile-picture"/>
                <span id="name">{data['name']}</span>
            </div>
            <div id="intro">
                <span>{data['intro']}</span>
            </div>
        </section>

        <section id="contact">
            <a class="phoneNumber" href="tel:{data['contact']['phone']}">
                <span class="fas fa-phone icon"></span><span>{data['contact']['phone']}</span>
            </a>
            <a href="mailto:{data['contact']['email']}">
                <span class="fas fa-envelope icon"></span><span>{data['contact']['email']}</span>
            </a>
            <a href="{data['contact']['linkedin']}">
                <span class="fab fa-linkedin icon"></span><span>linkedin.com/in/lukasz0wisniewski</span>
            </a>
        </section>

        <h1>{labels.get('experience', 'Experience')}</h1>
        <section id="experience" class="section-experience">
            {render_experience(data['experience'])}
        </section>

        <h1>{labels.get('skills', 'Skills and Technology')}</h1>
        <div class="section-large" id="technology-list">
            {render_skills(data['skills'])}
        </div>
        <div id="technology-other">
            {data.get('skills_other', '')}
        </div>

        <section id="education" class="two-sections">
            <div>
                <h1>{labels.get('education', 'Education')}</h1>
                <section class="section-small">
                    {render_education(data['education'])}
                </section>
            </div>
            <div>
                <h1>{labels.get('language', 'Language')}</h1>
                <section class="section-small">
                    {render_languages(data['languages'])}
                </section>
                <h1>{labels.get('disability', 'Certificate of Disability')}</h1>
                <section class="section-small">
                    {render_disabilities(data.get('disabilities', []))}
                </section>
            </div>
        </section>

        <h1 id="work-projects">{labels.get('projects', 'Project highlights')}</h1>
        {render_projects(data['projects'], labels)}
    </div>
</body>
</html>'''


def main() -> None:
    parser = argparse.ArgumentParser(description='Generate PDF from CV HTML')
    parser.add_argument('--method', choices=['playwright', 'weasyprint'],
                        default='playwright', help='PDF generation method')
    parser.add_argument('--language', choices=['en', 'pl', 'both'],
                        default='both', help='Language version to generate')
    parser.add_argument('--port', type=int, default=8000,
                        help='Local server port')

    args = parser.parse_args()

    if args.method == 'playwright':
        generator = CVPDFGenerator(port=args.port)
        if args.language == 'both':
            asyncio.run(generator.run())
        else:
            generator.install_requirements()
            generator.start_server()
            try:
                asyncio.run(generator.generate_pdf_playwright(args.language))
            finally:
                generator.stop_server()
    else:
        if args.language in ['en', 'pl']:
            generate_pdf_weasyprint(args.language)
        else:
            generate_pdf_weasyprint('en')
            generate_pdf_weasyprint('pl')


if __name__ == "__main__":
    main()
