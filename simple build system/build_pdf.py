from weasyprint import HTML, CSS

html = HTML('static/cv.html')
css = CSS('static/styles/cv.css')

html.write_pdf(
    'Lukasz Wisniewski CV.pdf',
    stylesheets=[css],
    optimize_size=()
)