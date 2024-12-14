from xml.etree import ElementTree as ET


class XMLProcessor:
    """Processor for historical texts in XML format, particularly EEBO-TCP and play texts."""

    def __init__(self):
        self.namespaces = {
            'tei': 'http://www.tei-c.org/ns/1.0'
        }

    def process_text_with_marks(self, element):
        """Process text while preserving historical marks and hyphenation"""
        if element is None:
            return ""

        # Collect text and inline elements
        text_parts = []
        for item in element.iter():
            if item.tag == 'g':  # Handle `<g>` elements
                ref = item.get('ref', '')
                if 'EOLhyphen' in ref:  # Join hyphenated words
                    prev_text = item.tail or ''
                    next_elem = item.getnext()
                    if next_elem is not None:
                        next_text = next_elem.text or ''
                        text_parts.append(prev_text.rstrip() + '-' + next_text.lstrip())
                else:
                    continue  # Ignore non-hyphenation `<g>` elements
            elif item.tag == 'gap':  # Handle `<gap>` (illegible text)
                desc = item.find('desc')
                text_parts.append(f"[{desc.text if desc is not None else 'gap'}]")
            else:
                text_parts.append(item.text or '')

        # Normalize whitespace
        return ' '.join(''.join(text_parts).split())

    def process_eebo_content(self, root):
        """Process EEBO-TCP XML content."""
        content = []
        processed_ids = set()

        # Find body with namespace
        body = root.find('.//tei:body', self.namespaces)
        if body is None:
            body = root.find('.//body')
            if body is None:
                return content

        # Process all divs that are chapters or text
        for div in body.findall('.//tei:div[@type="chapter"]', self.namespaces):
            if id(div) not in processed_ids:
                processed_ids.add(id(div))

                # Get chapter heading
                head = div.find('tei:head', self.namespaces) or div.find('head')
                if head is not None:
                    chapter_title = self.process_text_with_marks(head)
                    chapter_content = self.process_prose_div(div)
                    if chapter_content:
                        content.append((chapter_title, chapter_content))

        return content

    def process_poem_div(self, div):
        """Process a poem div, handling lines and maintaining hierarchy."""
        content = []
        processed_ids = set()  # Track processed lines to prevent duplicates

        def process_lines(lines):
            """Helper to process lines, tracking which have been processed"""
            line_content = []
            for line in lines:
                if id(line) not in processed_ids:
                    if line.text and line.text.strip():
                        line_content.append(("line", self.process_text_with_marks(line)))
                    processed_ids.add(id(line))
            return line_content

        # First process lines within line groups
        for lg in div.findall('.//tei:lg', self.namespaces):
            content.extend(process_lines(lg.findall('tei:l', self.namespaces)))

        # Then process standalone lines (not in line groups)
        for line in div.findall('tei:l', self.namespaces):
            if id(line) not in processed_ids and line.text and line.text.strip():
                content.append(("line", self.process_text_with_marks(line)))
                processed_ids.add(id(line))

        return content

    def process_prose_div(self, div):
        """Process a prose div, handling only <p> tags."""
        content = []
        processed_ids = set()

        def process_inline(element):
            """Process inline elements with proper nesting and unique handling."""
            if element is None:
                return ""

            text_parts = []

            # Process the element's own text
            if element.text:
                text_parts.append(element.text)

            # Process child elements
            for child in element:
                # Skip if already processed
                if id(child) in processed_ids:
                    continue

                if child.tag.endswith('hi'):
                    text_parts.append(process_inline(child))
                elif child.tag.endswith('gap'):
                    desc = child.find('desc')
                    if desc is not None and desc.text:
                        text_parts.append(f"[{desc.text}]")
                    else:
                        text_parts.append("[gap]")
                elif child.tag.endswith('g'):
                    ref = child.get('ref', '')
                    if 'EOLhyphen' in ref:
                        text_parts.append('-')

                processed_ids.add(id(child))

                # Add any tail text
                if child.tail:
                    text_parts.append(child.tail)

            return ' '.join(''.join(text_parts).split())

        # Process all paragraphs within the div
        for p in div.findall('.//tei:p', self.namespaces):
            if id(p) not in processed_ids:
                text = process_inline(p)
                if text and text.strip():
                    content.append(('p', text.strip()))
                    processed_ids.add(id(p))

        return content



