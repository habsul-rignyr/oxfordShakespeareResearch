from xml.etree import ElementTree as ET


class XMLProcessor:
    """Processor for historical texts in XML format, particularly EEBO-TCP and play texts.

    Specializes in handling:
    - EEBO-TCP text formatting
    - Early modern English text
    - Special character processing
    - Historical hyphenation
    - Poetry structures
    - Drama structures
    """

    def __init__(self):
        self.namespaces = {
            'tei': 'http://www.tei-c.org/ns/1.0'
        }

    def process_text_with_marks(self, element):
        """Process text while preserving historical marks and hyphenation"""
        if element is None:
            return ""

        # First collect all text parts
        text_parts = []
        for item in element.itertext():
            text_parts.append(item)

        # Join all text first
        text = ''.join(text_parts)

        # Find all g elements and process them in order
        for g_elem in element.findall(".//g"):
            ref = g_elem.get('ref', '')

            # Handle hyphenation
            if 'EOLhyphen' in ref:
                # Get surrounding text
                prev_text = g_elem.tail or ''
                next_elem = g_elem.getnext()
                if next_elem is not None:
                    next_text = next_elem.text or ''
                    # Replace the space between hyphenated parts with a hyphen
                    text = text.replace(prev_text + ' ' + next_text,
                                        prev_text.rstrip() + '-' + next_text.lstrip())

        text = ' '.join(text.split())  # Normalize whitespace
        return text

    def process_eebo_content(self, root):
        """Process EEBO-TCP XML content"""
        content = []

        # Find body with namespace
        body = root.find('.//tei:body', self.namespaces)
        if body is None:
            body = root.find('.//body')  # Try without namespace
            if body is None:
                return content

        # Process each div based on type
        for div in body.findall('.//tei:div', self.namespaces):
            div_type = div.get('type', '')

            if div_type == 'poem':
                poem_content = self.process_poem_div(div)
                if poem_content:
                    head = div.find('.//tei:head', self.namespaces) or div.find('head')
                    title = self.process_text_with_marks(head) if head is not None else 'Poem'
                    content.append((title, poem_content))

            elif div_type in ['text', 'chapter']:
                prose_content = self.process_prose_div(div)
                if prose_content:
                    head = div.find('.//tei:head', self.namespaces) or div.find('head')
                    title = self.process_text_with_marks(head) if head is not None else 'Section'
                    content.append((title, prose_content))

        return content

    def process_poem_div(self, div):
        """Process a poem div and its parts"""
        content = []
        processed_headings = set()

        def add_heading(elem):
            """Add heading if it hasn't been processed yet"""
            if elem is not None:
                text = self.process_text_with_marks(elem)
                if text and text.strip() and text not in processed_headings:
                    processed_headings.add(text)
                    return ('head', text.strip())
            return None

        # Process main poem heading
        main_head = div.find('tei:head', self.namespaces) or div.find('head')
        if main_head is not None:
            heading = add_heading(main_head)
            if heading:
                content.append(heading)

        # Process figures with their lines
        for fig in div.findall('.//figure'):
            for line in fig.findall('l'):
                text = self.process_text_with_marks(line)
                if text and text.strip():
                    content.append(('line', text.strip()))

            # Process figure heading if present
            fig_head = fig.find('head')
            if fig_head is not None:
                heading = add_heading(fig_head)
                if heading:
                    content.append(heading)

        # Process parts
        for part in div.findall('div[@type="part"]'):
            # Process part heading
            part_head = part.find('head')
            if part_head is not None:
                heading = add_heading(part_head)
                if heading:
                    content.append(heading)

            # Process lines in part
            for line in part.findall('l'):
                text = self.process_text_with_marks(line)
                if text and text.strip():
                    content.append(('line', text.strip()))

            # Process line groups in part
            for lg in part.findall('lg'):
                for line in lg.findall('l'):
                    text = self.process_text_with_marks(line)
                    if text and text.strip():
                        content.append(('line', text.strip()))

        return content

    def process_prose_div(self, div):
        """Process a prose div and its parts"""
        content = []

        # Process paragraphs
        for p in div.findall('.//tei:p', self.namespaces):
            text = self.process_text_with_marks(p)
            if text and text.strip():
                content.append(('p', text.strip()))

        # Process headers
        for head in div.findall('.//tei:head', self.namespaces):
            text = self.process_text_with_marks(head)
            if text and text.strip():
                content.append(('head', text.strip()))

        return content

    def process_play_content(self, root):
        """Process dramatic content from play XML"""
        title_element = root.find('.//title')
        if title_element is not None:
            title_parts = []
            for part in title_element.itertext():
                title_parts.append(part.strip())
            play_title = ' '.join(title_parts)
        else:
            play_title = "Untitled Play"

        acts = self.process_acts(root)
        character_mappings = self.get_character_mappings(root)

        return {
            'title': play_title,
            'acts': acts,
            'character_mappings': character_mappings
        }

    def get_character_mappings(self, root):
        """Extract character mappings from play XML"""
        character_list = []
        for character in root.findall('.//persona'):
            character_name = character.find('persname')
            if character_name is not None:
                abbreviated_name = character_name.get('short', '')
                full_name = character_name.text or ''
                if abbreviated_name and full_name:
                    character_list.append({
                        'short': abbreviated_name,
                        'full': full_name
                    })
        return sorted(character_list, key=lambda x: x['short'])

    def process_acts(self, root):
        """Process acts from play XML"""
        acts = []

        # Handle prologue
        prologue = root.find(".//act[@num='0']")
        if prologue is not None:
            prologue_scenes = self.process_prologue(prologue)
            acts.append({
                'act_title': 'Prologue',
                'scenes': prologue_scenes
            })

        # Handle regular acts
        for act in root.findall('act'):
            if act.get('num') == '0':
                continue

            act_title = act.find('acttitle').text if act.find('acttitle') is not None else None
            scenes = self.process_scenes(act)
            acts.append({
                'act_title': act_title,
                'scenes': scenes
            })

        return acts

    def process_prologue(self, prologue_act):
        """Process prologue content"""
        prologue_scenes = []
        for prologue_section in prologue_act.findall('.//prologue'):
            content = self.process_content(prologue_section)
            prologue_scenes.append({
                'scene_title': None,
                'content': content
            })
        return prologue_scenes

    def process_scenes(self, act):
        """Process scenes from an act"""
        scenes = []
        for scene in act.findall('scene'):
            scene_title = scene.find('scenetitle')
            if scene_title is not None:
                scene_text = ''.join(scene_title.itertext())
                if scene_text != act.find('acttitle').text:
                    scene_title = scene_text
                else:
                    scene_title = None

            content = self.process_content(scene)
            scenes.append({
                'scene_title': scene_title,
                'content': content
            })
        return scenes

    def process_content(self, element):
        """Process dramatic content from a scene or prologue"""
        content = []
        for element_type in element:
            if element_type.tag == 'speech':
                content.append(self.process_speech(element_type))
            elif element_type.tag == 'stagedir':
                stage_direction = ''.join(element_type.itertext())
                if stage_direction:
                    content.append({
                        'type': 'stagedir',
                        'text': stage_direction
                    })
        return content

    def process_speech(self, speech_element):
        """Process speech elements from dramatic text"""
        speaker_element = speech_element.find('speaker')
        speaker = speaker_element.get(
            'short') or speaker_element.text or 'Unknown Speaker' if speaker_element is not None else 'Unknown Speaker'

        dialogue_lines = []
        for line in speech_element.findall('line'):
            if line.find('dropcap') is not None:
                initial_letter = line.find('dropcap').text
                remaining_text = ''.join(part for part in line.itertext() if part != initial_letter)
                line_text = f'<span class="dropcap">{initial_letter}</span>{remaining_text}'
            else:
                line_text = ''.join(line.itertext())

            if line_text:
                dialogue_lines.append(line_text)

        return {
            'type': 'speech',
            'speaker': speaker,
            'lines': dialogue_lines
        }