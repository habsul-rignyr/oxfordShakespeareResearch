# processors/xml_processor.py

from xml.etree import ElementTree as ET


class XMLProcessor:
    """Processor for historical texts in XML format, particularly EEBO-TCP and play texts.

    Specializes in handling early modern English texts including:
    - Special character processing
    - Historical hyphenation
    - Drama and play structures
    - EEBO-TCP specific formatting
    """

    def __init__(self):
        self.namespaces = {
            'tei': 'http://www.tei-c.org/ns/1.0'
        }

    def process_text_with_marks(self, element):
        """Process text while preserving historical marks and hyphenation"""
        text_parts = []
        for item in element.itertext():
            text_parts.append(item)

        # Join all text first
        text = ''.join(text_parts)

        # Handle special characters
        for historical_mark in element.findall(".//g"):
            mark_type = historical_mark.get('ref', '')
            if 'EOLhyphen' in mark_type:
                previous_text = historical_mark.tail or ''
                following_text = historical_mark.getnext().text if historical_mark.getnext() is not None else ''
                text = text.replace(previous_text + ' ' + following_text,
                                    previous_text.rstrip() + '-' + following_text.lstrip())
            elif 'cmbAbbrStroke' in mark_type:
                text = text.replace(historical_mark.tail or '', '̄' + (historical_mark.tail or ''))

        return text

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

    def process_eebo_content(self, root):
        """Process EEBO-TCP XML content"""
        content = []

        # Get all major sections
        front = root.find('.//tei:front', self.namespaces)
        body = root.find('.//tei:body', self.namespaces)

        # Process front matter if it exists
        if front is not None:
            front_content = self.process_eebo_section(front)
            if front_content:
                content.append(('Front Matter', front_content))

        # Process main text if it exists
        if body is not None:
            # Process each div in the body
            for div in body.findall('.//tei:div', self.namespaces):
                div_content = self.process_eebo_section(div)
                if div_content:
                    # Get the chapter heading if it exists
                    head = div.find('tei:head', self.namespaces)
                    section_title = self.process_text_with_marks(head) if head is not None else 'Main Text'
                    content.append((section_title, div_content))

        return content

    def process_eebo_section(self, section):
        """Process a section of EEBO-TCP XML"""
        content = []
        processed_headings = set()  # Keep track of headings we've seen

        print("\nProcessing XML section...")  # Debug

        for elem in section.iter():
            tag = elem.tag.split('}')[-1]  # Remove namespace
            print(f"Found element: {tag}")  # Debug

            if tag == 'p':  # Paragraph content
                text = self.process_text_with_marks(elem)
                if text and text.strip():
                    print(f"Adding paragraph: {text[:50]}...")  # Debug
                    content.append(('p', text.strip()))

            elif tag == 'head':  # Heading
                text = self.process_text_with_marks(elem)
                if text and text.strip():
                    # Only add heading if we haven't seen it before
                    if text not in processed_headings:
                        processed_headings.add(text)
                        print(f"Adding heading: {text[:50]}...")  # Debug
                        content.append(('head', text.strip()))

        print(f"Total content items: {len(content)}")  # Debug
        for i, (type, text) in enumerate(content):
            print(f"{i + 1}. Type: {type}, Text: {text[:50]}...")  # Debug

        return content
