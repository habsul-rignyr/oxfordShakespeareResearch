import os
import xml.etree.ElementTree as ET
from flask import current_app
from models import db
from models.work import Work
from search import search
import logging
from datetime import datetime
import concurrent.futures
import functools

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'indexing_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def extract_text_from_xml(xml_path):
    """Extract full text content from XML file."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Handle different XML formats
        if 'tei-c.org' in str(root.tag):  # EEBO-TCP format
            # Extract text from body
            body = root.find('.//{http://www.tei-c.org/ns/1.0}body')
            if body is None:
                return ""

            # Join all text elements, preserving some structure
            text_parts = []
            for elem in body.iter():
                if elem.text and elem.text.strip():
                    text_parts.append(elem.text.strip())

            return " ".join(text_parts)
        else:  # Shakespeare play format
            text_parts = []

            # Extract speeches
            for speech in root.findall('.//speech'):
                speaker = speech.find('speaker')
                if speaker is not None:
                    text_parts.append(speaker.text)

                for line in speech.findall('line'):
                    text_parts.append(''.join(line.itertext()))

            # Extract stage directions
            for stagedir in root.findall('.//stagedir'):
                text_parts.append(stagedir.text)

            return " ".join(text_parts)

    except Exception as e:
        logger.error(f"Error processing {xml_path}: {str(e)}")
        return ""


def index_work_with_context(app, work):
    """Index a single work into Elasticsearch with app context."""
    with app.app_context():
        try:
            if not os.path.exists(work.file_path):
                logger.error(f"File not found: {work.file_path}")
                return False

            # Extract text content
            content = extract_text_from_xml(work.file_path)
            if not content:
                logger.error(f"No content extracted from {work.file_path}")
                return False

            # Index the work
            success = search.index_work(work, content)
            if success:
                logger.info(f"Successfully indexed work {work.id}: {work.title}")
            return success

        except Exception as e:
            logger.error(f"Error indexing work {work.id}: {str(e)}")
            return False


def index_all_works(app):
    """Index all works in the database into Elasticsearch."""
    with app.app_context():
        # Get total count
        total_works = Work.query.count()
        logger.info(f"Starting indexing of {total_works} works")

        # Process works in batches to manage memory
        batch_size = 100
        successful = 0
        failed = 0

        # Create a partial function with the app argument
        index_work_partial = functools.partial(index_work_with_context, app)

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            for offset in range(0, total_works, batch_size):
                works = Work.query.offset(offset).limit(batch_size).all()

                # Submit batch of works for indexing
                future_to_work = {executor.submit(index_work_partial, work): work for work in works}

                # Process completed tasks
                for future in concurrent.futures.as_completed(future_to_work):
                    work = future_to_work[future]
                    try:
                        if future.result():
                            successful += 1
                        else:
                            failed += 1
                    except Exception as e:
                        logger.error(f"Error processing work {work.id}: {str(e)}")
                        failed += 1

                # Log progress
                progress = (offset + len(works)) / total_works * 100
                logger.info(f"Progress: {progress:.1f}% ({successful} succeeded, {failed} failed)")

        logger.info(f"Indexing complete. {successful} works indexed successfully, {failed} failed")


if __name__ == "__main__":
    from app import app
    logger.info("Starting indexing process")
    index_all_works(app)
    logger.info("Indexing process finished")