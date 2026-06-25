import markdown
import os
from xhtml2pdf import pisa
import fitz

out_dir = r'C:\Users\NextVivo\AppData\Roaming\Claude\local-agent-mode-sessions\54c4cb55-7338-4617-8790-8e06a25e10cb\e6e926a6-8c05-4e6a-957e-931ebcca9fb9\local_d4a6c91e-75d0-4491-beb6-8c8ae7299bda\outputs'
md1_path = os.path.join(out_dir, 'v14_3_.md')
md2_path = os.path.join(out_dir, 'v14_§8__.md')
v13_pdf = os.path.join(out_dir, '_NGF_v13.pdf')
out_pdf = os.path.join(out_dir, '_NGF_v14_.pdf')

try:
    with open(md1_path, 'r', encoding='utf-8') as f:
        text1 = f.read
    with open(md2_path, 'r', encoding='utf-8') as f:
        text2 = f.read

    md_text = f"# ：V14 3\n\n{text1}\n\n<pdf:nextpage />\n\n# ：V14 §8 \n\n{text2}"
    html_body = markdown.markdown(md_text, extensions=['tables'])

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        @font-face {{
            font-family: 'simhei';
            src: url('C:/Windows/Fonts/simhei.ttf') format('truetype');
        }}
        body {{
            font-family: 'simhei', sans-serif;
            font-size: 14px;
            line-height: 1.6;
            color: #333;
        }}
        h1, h2, h3 {{ color: #222; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
        th, td {{ border: 1px solid #999; padding: 6px; text-align: left; }}
        th {{ background-color: #f5f5f5; font-weight: bold; }}
    </style>
    </head>
    <body>
    {html_body}
    </body>
    </html>
    """

    temp_pdf = os.path.join(out_dir, 'temp_append.pdf')
    with open(temp_pdf, 'wb') as f:
        pisa_status = pisa.CreatePDF(html, dest=f)

    if pisa_status.err:
        print('Error generating PDF with xhtml2pdf')
    else:
        # Merge PDFs
        doc_main = fitz.open(v13_pdf)
        doc_append = fitz.open(temp_pdf)
        doc_main.insert_pdf(doc_append)
        doc_main.save(out_pdf)
        doc_main.close
        doc_append.close
        try:
            os.remove(temp_pdf)
        except:
            pass
        print(f'Successfully generated PDF at: {out_pdf}')
except Exception as e:
    print('Failed:', e)
