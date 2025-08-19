#!/usr/bin/env python3

import asyncio
import subprocess
import sys
import os
import time
import threading
import http.server
import socketserver
from pathlib import Path
from playwright.async_api import async_playwright

# noinspection PyTypeChecker
class CVPDFGenerator:
    def __init__(self, cv_folder="./static", port=8000):
        self.cv_folder = Path(cv_folder).resolve()
        self.port = port
        self.server_process = None
        self.httpd = None

    def start_server(self):
        os.chdir(self.cv_folder)

        class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, param, *args):
                pass  # Suppress server logs

        self.httpd = socketserver.TCPServer(("", self.port), QuietHTTPRequestHandler)
        server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        server_thread.start()
        print(f"✓ Server started at http://localhost:{self.port}")
        time.sleep(2)

    def stop_server(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            print("✓ Server stopped")

    async def generate_pdf_playwright(self, language="en", output_file=None):
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
                margin={
                    'top': '0.5in',
                    'right': '0.5in',
                    'bottom': '0.5in',
                    'left': '0.5in'
                },
                print_background=True,
                prefer_css_page_size=True
            )

            await browser.close()
            print(f"✓ PDF generated: {output_file}")

    async def generate_both_pdfs(self):
        print("Generating English PDF...")
        await self.generate_pdf_playwright("en", "Lukasz Wisniewski CV en.pdf")

        print("Generating Polish PDF...")
        await self.generate_pdf_playwright("pl", "Lukasz Wisniewski CV pl.pdf")

        print("✓ Both PDFs generated successfully!")

    @staticmethod
    def install_requirements():
        try:
            import playwright
        except ImportError:
            print("Installing playwright...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
            subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
            print("✓ Playwright installed")

    async def run(self):
        print("🚀 CV PDF Generator Starting...")

        if not (self.cv_folder / "cv_yaml.html").exists():
            print("❌ Error: cv_yaml.html not found in current directory")
            return

        if not (self.cv_folder / "content.yaml").exists():
            print("❌ Error: content.yaml not found in current directory")
            return

        try:
            self.install_requirements()
            self.start_server()
            await self.generate_both_pdfs()

        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            self.stop_server()

def generate_pdf_weasyprint(language="en", output_file=None):
    try:
        from weasyprint import HTML, CSS
        import yaml
    except ImportError:
        print("Installing weasyprint and pyyaml...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "weasyprint", "pyyaml"])
        from weasyprint import HTML, CSS
        import yaml

    if not output_file:
        output_file = f"Lukasz Wisniewski CV_{language}_weasyprint.pdf"

    with open('content.yaml', 'r', encoding='utf-8') as f:
        cv_data = yaml.safe_load(f)

    with open('cv_yaml.html', 'r', encoding='utf-8') as f:
        html_content = f.read()

    static_html = create_static_html(cv_data[language], html_content)

    HTML(string=static_html, base_url='.').write_pdf(
        output_file,
        stylesheets=[CSS('styles/cv.css')]
    )
    print(f"✓ PDF generated with WeasyPrint: {output_file}")

# TODO add rest of html content to static html
# noinspection PyUnusedLocal
def create_static_html(data, template):
    static_content = f"""
    <!DOCTYPE html>
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
            <!-- Add more sections as needed -->
        </div>
    </body>
    </html>
    """
    return static_content

def main():
    import argparse

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