from weasyprint import HTML, CSS
from jinja2 import Environment, FileSystemLoader
import yaml, sys

with open('static/content.yaml', "r", encoding="utf-8") as f:
    data = yaml.safe_load(f)

env = Environment(loader=FileSystemLoader('.'))
template = env.get_template('static/cv_template.html')

html_toggle = template.render(content=data)
open('static/cv_toggle.html', 'w', encoding="utf-8").write(html_toggle)

html_en=template.render(content={"en": data["en"]})
HTML(string=html_en, base_url=".").write_pdf("CV_en.pdf", stylesheets=[CSS('static/styles/cv.css')])

# html = HTML('static/cv.html')
# css = CSS('static/styles/cv.css')
#
# html.write_pdf(
#     'Lukasz Wisniewski CV.pdf',
#     stylesheets=[css],
#     optimize_size=()
# )