import zipfile
import xml.etree.ElementTree as ET

docx_path = r"c:\Users\mrc56\Documents\Proyectos\deck-at-the-plate\referencias\Deck_at_the_Plate_UI_Spec_v1.docx"

try:
    with zipfile.ZipFile(docx_path, 'r') as zip_ref:
        xml_content = zip_ref.read('word/document.xml')
    
    root = ET.fromstring(xml_content)
    
    # Extract text from all paragraphs
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    text_content = []
    
    for paragraph in root.findall('.//w:p', ns):
        para_text = []
        for text_elem in paragraph.findall('.//w:t', ns):
            if text_elem.text:
                para_text.append(text_elem.text)
        if para_text:
            text_content.append(''.join(para_text))
    
    # Print content
    for line in text_content:
        print(line)
        
except Exception as e:
    print(f"Error: {e}")
