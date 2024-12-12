# update_publication_years.py

import os
import xml.etree.ElementTree as ET
from models import db
from models.work import Work
from flask import current_app
import logging
from datetime import datetime

# Set up logging
log_filename = f"publication_years_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Define the EEBO texts directory
EEBO_DIR = "/Volumes/seagate_portable/eebo-tcp-texts"


def extract_publication_year(header):
    """Extract publication year from multiple possible locations in EEBO-TCP XML."""
    try:
        # Try sourceDesc/biblFull/publicationStmt/date first (most authoritative)
        date_elem = header.find(
            './/{http://www.tei-c.org/ns/1.0}sourceDesc//{http://www.tei-c.org/ns/1.0}biblFull//{http://www.tei-c.org/ns/1.0}publicationStmt//{http://www.tei-c.org/ns/1.0}date')

        # If not found, try editionStmt/edition/date
        if date_elem is None:
            date_elem = header.find(
                './/{http://www.tei-c.org/ns/1.0}editionStmt//{http://www.tei-c.org/ns/1.0}edition//{http://www.tei-c.org/ns/1.0}date')

        if date_elem is not None:
            # Try 'when' attribute first
            year = date_elem.get('when')
            if not year:
                # If no 'when' attribute, try text content
                year = date_elem.text

            # Clean up the year string
            if year:
                # Remove any punctuation
                year = year.strip('.')
                # Extract just the year if it's a longer date
                import re
                year_match = re.search(r'\b(\d{4})\b', year)
                if year_match:
                    return int(year_match.group(1))

                # If it's just a year number
                if year.isdigit() and len(year) == 4:
                    return int(year)

    except (ValueError, AttributeError, TypeError) as e:
        logger.error(f"Error extracting year: {str(e)}")

    return None


def update_work_publication_year(work):
    """Update publication year for a single work."""
    try:
        # Get the relative path from the database and make it absolute
        rel_path = work.file_path
        if rel_path.startswith('/Volumes'):
            abs_path = rel_path  # Already absolute
        else:
            abs_path = os.path.join(EEBO_DIR, os.path.basename(rel_path))

        if not os.path.exists(abs_path):
            logger.error(f"File not found: {abs_path}")
            return False

        tree = ET.parse(abs_path)
        root = tree.getroot()
        header = root.find('.//{http://www.tei-c.org/ns/1.0}teiHeader')

        if header is None:
            logger.error(f"No header found in {abs_path}")
            return False

        pub_year = extract_publication_year(header)
        if pub_year:
            old_year = work.publication_year
            work.publication_year = pub_year
            logger.info(f"Updated work {work.id}: {work.title} - Year changed from {old_year} to {pub_year}")
            return True
        else:
            logger.warning(f"No year found for work {work.id}: {work.title}")
            return False

    except Exception as e:
        logger.error(f"Error processing work {work.id}: {str(e)}")
        return False


def update_all_publication_years():
    """Update publication years for all EEBO-TCP works."""
    logger.info("Starting publication year update process")
    logger.info(f"Using EEBO directory: {EEBO_DIR}")

    if not os.path.exists(EEBO_DIR):
        logger.error(f"EEBO directory not found: {EEBO_DIR}")
        return

    with app.app_context():
        works = Work.query.filter_by(collection='EEBO-TCP').all()
        total_works = len(works)
        logger.info(f"Found {total_works} EEBO-TCP works to process")

        updated = 0
        failed = 0
        no_year = 0

        # Process works in batches to manage memory and allow partial commits
        batch_size = 100
        for i in range(0, total_works, batch_size):
            batch = works[i:i + batch_size]

            for work in batch:
                try:
                    if update_work_publication_year(work):
                        updated += 1
                    else:
                        no_year += 1
                except Exception as e:
                    failed += 1
                    logger.error(f"Failed to update work {work.id}: {str(e)}")

            # Commit each batch
            try:
                db.session.commit()
                logger.info(f"Processed {min(i + batch_size, total_works)}/{total_works} works "
                            f"({(min(i + batch_size, total_works) / total_works) * 100:.1f}%)")
            except Exception as e:
                logger.error(f"Error committing batch: {str(e)}")
                db.session.rollback()
                failed += len(batch)

        logger.info(f"""
Update complete:
- Total works processed: {total_works}
- Successfully updated: {updated}
- No year found: {no_year}
- Failed to process: {failed}
""")


if __name__ == "__main__":
    from app import app

    update_all_publication_years()