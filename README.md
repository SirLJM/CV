# Personal CV

Bilingual CV (English/Polish) as a static website with PDF export. Multiple CV versions (IT, PM) from a single codebase.

## Features

- Multiple CV versions (IT-focused, PM-focused) with shared structure
- Bilingual support (English/Polish) per version
- Language switcher (no page reload)
- Responsive design with print-optimized layout
- Automated PDF generation via Playwright

## Quick Start

### View in browser
```bash
cd static && python -m http.server 8000
```
Then open:
- `http://localhost:8000/cv_yaml.html?version=it` - IT version
- `http://localhost:8000/cv_yaml.html?version=pm` - PM version

### Generate PDFs
```bash
python generate_pdf.py --version it      # IT version (default)
python generate_pdf.py --version pm      # PM version
python generate_pdf.py --version all     # All versions
```

Options:
- `--version it|pm|all` - CV version (default: it)
- `--language en|pl|both` - language (default: both)
- `--port 8000` - local server port

## Project Structure

```
static/
  content_it.yaml   # IT-focused CV data (en/pl)
  content_pm.yaml   # PM-focused CV data (en/pl)
  cv_yaml.html      # Main HTML with JS rendering
  styles/cv.css     # Styling + print media queries
  images/           # Profile photo
generate_pdf.py     # PDF generator script
```

## Adding New Version

1. Copy `static/content_it.yaml` to `static/content_<version>.yaml`
2. Edit content for new version
3. Add version to `--version` choices in `generate_pdf.py`

## Requirements

- Python 3.10+
- Playwright (auto-installed on first run)

## Technologies

HTML, CSS, JavaScript, YAML, Python, Playwright
