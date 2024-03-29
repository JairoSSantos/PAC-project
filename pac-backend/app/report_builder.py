from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import base64
from io import BytesIO
from PIL import Image
matplotlib.use('agg')

HERE = Path(__file__).parent
TEMPLATE = Environment(loader=FileSystemLoader(HERE)).get_template('template.html')
IPR = 3

TEMP = HERE/'temp'
TEMP.mkdir(parents=True, exist_ok=True)

def hist(results, area_label):
    plt.clf()
    plt.figure(figsize=(4, 2.75))
    plt.hist(results[area_label])
    plt.xlabel(area_label)
    plt.ylabel('Ocorrências')
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png')
    data = base64.b64encode(buf.getbuffer()).decode("ascii")
    return data

def get_resized_image(base64_image):
    buf = BytesIO()
    Image.open(BytesIO(base64.b64decode(base64_image))).resize((256, 256)).save(buf, format='png')
    return base64.b64encode(buf.getbuffer()).decode("ascii")

def build_report(sample_name, results, area_label, summary, images, comments):
    images = [(index, get_resized_image(strImage)) for index, strImage in images.items()]
    html = TEMPLATE.render(
        sample_name= sample_name,
        datetime= datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        results= results.rename(columns={'Id':''}).to_html(index=False),
        summary= summary.rename(columns={'#':''}).set_index('').T.to_html(),
        hist= hist(results, area_label),
        is_there_comments= len(comments) > 0,
        comments= comments, 
        is_there_images= len(images) > 0,
        images = images

    # with open('report.html', 'w') as f:
    #     f.write(html)
    )

    report = HTML(string=html).write_pdf(
        presentational_hints=True
    )

    return {
        'report': base64.b64encode(report).decode()
    }