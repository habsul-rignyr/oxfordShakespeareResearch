import os
import xml.etree.ElementTree as ET
from models import db
from models.work import Work

# Define the directory containing the XML files
XML_DIR = "/Users/a86136/desktop/plays/PlayShakespeare.com-XML/first_folio_editions"

def parse_play(xml_path):
    """
    Extract minimal metadata from an XML play file.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    title_element = root.find('.//title')
    title = ' '.join(title_element.itertext()).strip() if title_element is not None else f"Unknown Title ({os.path.basename(xml_path)})"

    author_element = root.find('.//playwright')
    author = author_element.text.strip() if author_element is not None else "Unknown Author"

    edition_element = root.find('.//edition')
    edition = edition_element.text.strip() if edition_element is not None else None

    return {
        'title': title,
        'author': author,
        'genre': 'Play',
        'publication_year': 1623,  # You might want to make this more flexible
        'edition': edition,
        'file_path': xml_path,
        'format': 'xml',
        'notes': None
    }

def populate_database():
    """Populate the database with XML file metadata."""
    xml_files = [f for f in os.listdir(XML_DIR) if f.endswith('.xml')]

    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("Tables created successfully!")

        print("Populating database...")
        for xml_file in xml_files:
            try:
                xml_path = os.path.join(XML_DIR, xml_file)
                print(f"Parsing {xml_file}...")
                work_data = parse_play(xml_path)

                work = Work(**work_data)
                db.session.add(work)

            except Exception as e:
                print(f"Error processing {xml_file}: {e}")

        db.session.commit()
        print("Database committed successfully!")

if __name__ == "__main__":
    from app import app
    populate_database()