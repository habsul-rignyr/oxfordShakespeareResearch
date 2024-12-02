import os
from lxml import etree
from models import db
from models.work import Work
from app import app

# Path to the folder containing XML files
XML_FOLDER = '/Users/a86136/desktop/plays/PlayShakespeare.com-XML/first_folio_editions'

def parse_xml(file_path):
    """Parse an XML file and extract metadata."""
    with open(file_path, 'r', encoding='utf-8') as file:
        tree = etree.parse(file)
        root = tree.getroot()

        # Extract metadata (adjust based on the XML structure)
        title = root.findtext('.//title') or os.path.basename(file_path)
        author = "William Shakespeare"  # All these plays are attributed to Shakespeare
        genre = "Play"  # Default for this dataset
        publication_year = 1623  # First Folio publication year
        notes = "Downloaded from PlayShakespeare.com"

        return {
            "title": title.strip(),
            "author": author,
            "genre": genre,
            "publication_year": publication_year,
            "file_path": file_path,
            "format": "xml",
            "notes": notes
        }

def add_to_database():
    """Parse XML files and add them to the database."""
    with app.app_context():
        for filename in os.listdir(XML_FOLDER):
            if filename.endswith('.xml'):
                file_path = os.path.join(XML_FOLDER, filename)
                metadata = parse_xml(file_path)

                # Create a new Work entry
                work = Work(
                    title=metadata['title'],
                    author=metadata['author'],
                    genre=metadata['genre'],
                    publication_year=metadata['publication_year'],
                    file_path=metadata['file_path'],
                    format=metadata['format'],
                    notes=metadata['notes']
                )
                db.session.add(work)

        db.session.commit()
        print("XML files added to the database.")

def verify_database():
    """Print all records in the database to verify insertion."""
    with app.app_context():
        works = Work.query.all()
        print(f"Total works in database: {len(works)}")
        for work in works:
            print(f"{work.title} by {work.author} (Format: {work.format})")


if __name__ == "__main__":
    add_to_database()
    verify_database()
