import os
import xml.etree.ElementTree as ET
from models import db
from models.work import Work
from flask import current_app
import concurrent.futures
import logging
from datetime import datetime

# Set up logging
log_filename = f"eebo_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def parse_eebo_metadata(xml_path):
    """Extract metadata from an EEBO-TCP XML file."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Find the teiHeader element
        header = root.find('.//{http://www.tei-c.org/ns/1.0}teiHeader')
        if header is None:
            return None

        # Extract basic metadata
        title_elem = header.find('.//{http://www.tei-c.org/ns/1.0}title')
        title = ' '.join(title_elem.itertext()).strip() if title_elem is not None else "Unknown Title"

        author_elem = header.find('.//{http://www.tei-c.org/ns/1.0}author')
        author = ' '.join(author_elem.itertext()).strip() if author_elem is not None else None

        # Extract TCP ID from filename
        tcp_id = os.path.splitext(os.path.basename(xml_path))[0]

        # Find publication date
        date_elem = header.find('.//{http://www.tei-c.org/ns/1.0}date')
        try:
            pub_year = int(date_elem.get('when')) if date_elem is not None else None
        except (ValueError, TypeError):
            pub_year = None

        return {
            'title': title[:500],  # Truncate to match model field length
            'author': author[:200] if author else None,
            'publication_year': pub_year,
            'tcp_id': tcp_id,
            'file_path': xml_path,
            'format': 'xml',
            'collection': 'EEBO-TCP',
            'language': 'eng'  # Default to English, could be extracted from metadata
        }
    except Exception as e:
        logger.error(f"Error parsing {xml_path}: {str(e)}")
        return None


def process_directory(directory):
    """Process all XML files in a directory and its subdirectories."""
    logger.info(f"Starting to process directory: {directory}")
    processed = 0
    errors = 0

    # Get list of all XML files
    xml_files = []
    for root, _, files in os.walk(directory):
        xml_files.extend([os.path.join(root, f) for f in files if f.endswith('.xml')])

    total_files = len(xml_files)
    logger.info(f"Found {total_files} XML files to process")

    # Process files in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_to_file = {executor.submit(parse_eebo_metadata, xml_file): xml_file
                          for xml_file in xml_files}

        for future in concurrent.futures.as_completed(future_to_file):
            xml_file = future_to_file[future]
            try:
                metadata = future.result()
                if metadata:
                    # Check if work already exists
                    existing_work = Work.query.filter_by(tcp_id=metadata['tcp_id']).first()
                    if not existing_work:
                        work = Work(**metadata)
                        db.session.add(work)
                        processed += 1
                        # Commit every 100 records
                        if processed % 100 == 0:
                            db.session.commit()
                            logger.info(
                                f"Processed {processed}/{total_files} files ({(processed / total_files) * 100:.1f}%)")
                else:
                    errors += 1
            except Exception as e:
                logger.error(f"Error processing {xml_file}: {str(e)}")
                errors += 1

    # Final commit
    try:
        db.session.commit()
    except Exception as e:
        logger.error(f"Error in final commit: {str(e)}")
        db.session.rollback()

    logger.info(f"Processing complete. Processed {processed} files with {errors} errors.")
    return processed, errors


if __name__ == "__main__":
    from app import app

    EEBO_DIR = "/Volumes/seagate_portable/eebo-tcp-texts/tcp"

    if not os.path.exists(EEBO_DIR):
        logger.error(f"Directory not found: {EEBO_DIR}")
        exit(1)

    logger.info("Starting EEBO-TCP import process")
    with app.app_context():
        process_directory(EEBO_DIR)
    logger.info("Import process completed")