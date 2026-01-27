# Personal CV

Bilingual CV (English/Polish) as a static website with PDF export.

## Features

- Single YAML file for all content in both languages
- Language switcher (no page reload)
- Responsive design with print-optimized layout
- Automated PDF generation via Playwright

## Quick Start

### View in browser
Open `static/cv_yaml.html` in a browser or serve the `static/` folder:
```bash
cd static && python -m http.server 8000
```

### Generate PDFs
```bash
python generate_pdf.py
```

Options:
- `--language en|pl|both` - language version (default: both)
- `--port 8000` - local server port
- `--method playwright|weasyprint` - PDF engine (default: playwright)

## Project Structure

```
static/
  content.yaml      # CV data (en/pl)
  cv_yaml.html      # Main HTML with JS rendering
  styles/cv.css     # Styling + print media queries
  images/           # Profile photo
generate_pdf.py     # PDF generator script
```

## Requirements

- Python 3.10+
- Playwright (auto-installed on first run)

## Technologies

HTML, CSS, JavaScript, YAML, Python, Playwright
