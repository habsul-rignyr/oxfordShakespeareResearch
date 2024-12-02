import os
import xml.etree.ElementTree as ET
from models import db
from models.work import Work
from flask import Flask

# Initialize Flask app
app = Flask(__name__)

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/a86136/PycharmProjects/shakespeare_project/instance/corpus.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db.init_app(app)

# Folder containing XML files
XML_FOLDER = "/Users/a86136/desktop/plays/PlayShakespeare.com-XML/first_folio_editions"


def extract_text_with_linebreaks(element):
    """
    Extracts text from an XML element, handling <lb /> tags by concatenating the text
    with a space between segments.
    """
    if element is None:
        return ""
    # Join all text and tail content with spaces
    return ' '.join(part.strip() for part in element.itertext() if part).strip()


def parse_xml(file_path):
    """
    Parse an XML file and extract metadata, handling titles with <lb /> tags.
    """
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Extract title, including concatenation of text around <lb /> tags
        title_element = root.find("title")
        title = extract_text_with_linebreaks(title_element) if title_element is not None else f"Unknown Title ({os.path.basename(file_path)})"
        author = root.findtext("playwrights/playwright", "Unknown Author").strip()
        genre = root.get("variant", "Play").strip()
        publication_year = 1623  # Default for First Folio
        edition = root.findtext("edition", "First Folio").strip()
        attribution = "PlayShakespeare.com"
        notes = f"File: {os.path.basename(file_path)}"

        return {
            "title": title,
            "author": author,
            "genre": genre,
            "publication_year": publication_year,
            "edition": edition,
            "attribution": attribution,
            "notes": notes
        }
    except Exception as e:
        print(f"Error parsing file {file_path}: {e}")
        return None


def create_database():
    """
    Drop and recreate the database tables.
    """
    with app.app_context():
        print("Creating database tables...")
        db.drop_all()
        db.create_all()
        print("Tables created successfully!")


def add_to_database():
    """
    Parse XML files and add them to the database.
    """
    with app.app_context():
        for filename in os.listdir(XML_FOLDER):
            if filename.endswith('.xml'):
                file_path = os.path.join(XML_FOLDER, filename)
                metadata = parse_xml(file_path)

                if metadata:
                    print(f"Inserting: {metadata['title']} by {metadata['author']}")
                    work = Work(
                        title=metadata['title'],
                        author=metadata['author'],
                        genre=metadata['genre'],
                        publication_year=metadata['publication_year'],
                        edition=metadata['edition'],
                        attribution=metadata['attribution'],
                        file_path=file_path,
                        format='xml',
                        notes=metadata['notes']
                    )
                    db.session.add(work)

        db.session.commit()
        print("Database committed successfully!")


def display_database_contents():
    """
    Display all rows in the database for verification.
    """
    with app.app_context():
        rows = Work.query.all()
        print(f"Number of rows in the database: {len(rows)}")
        for row in rows:
            print(f"Row: {row.id} | {row.title} | {row.author}")


if __name__ == "__main__":
    create_database()  # Create tables
    add_to_database()  # Add XML data to the database
    display_database_contents()  # Display the database contents
