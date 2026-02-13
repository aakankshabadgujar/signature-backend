import fitz

def sign_pdf(input_path, output_path):
    doc = fitz.open(input_path)
    page = doc[0]
    page.insert_text((50, 50), "SIGNED", fontsize=18)
    doc.save(output_path)
