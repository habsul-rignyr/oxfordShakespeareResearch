from flask import Flask, render_template, request, abort
from models import db
from models.work import Work
from xml.etree import ElementTree as ET
import os

app = Flask(__name__)

# Configure the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/a86136/PycharmProjects/shakespeare_project/instance/corpus.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db.init_app(app)


@app.route('/')
def home():
    return render_template("home.html")


@app.route('/search')
def search():
    query = request.args.get('query', '').strip()
    results = []

    if query:
        from normalization import normalize_text
        from rapidfuzz.fuzz import partial_ratio, token_set_ratio

        works = Work.query.all()
        matches = []

        # Normalize query once
        normalized_query = normalize_text(query.lower())

        for work in works:
            normalized_title = normalize_text(work.title.lower())

            # Use both partial_ratio for substring matches and token_set_ratio for word matching
            partial_score = partial_ratio(normalized_query, normalized_title)
            token_score = token_set_ratio(normalized_query, normalized_title)

            # Calculate final score with more weight on token matching
            final_score = (partial_score + 2 * token_score) / 3

            # For "henry" query, boost scores of titles that actually contain henry
            if normalized_query == "henry":
                if "henry" in normalized_title.split():
                    final_score = final_score * 1.2  # Boost relevant results

            if final_score > 70:  # Adjusted threshold
                matches.append((work, final_score))

        # Sort by score descending
        matches.sort(key=lambda x: x[1], reverse=True)

        # Get just the works, discard scores
        results = [match[0] for match in matches]

    return render_template("search.html", query=query, results=results)


@app.route('/play/<int:work_id>')
def render_play(work_id):
    work = Work.query.get(work_id)
    if not work:
        abort(404, description="Play not found")

    if not os.path.exists(work.file_path):
        abort(404, description="Play file not found")

    try:
        tree = ET.parse(work.file_path)
        root = tree.getroot()

        # Debug print
        print("Found acts:", [act.get('num') for act in root.findall('act')])

        # Get the play title just once at the start
        title_element = root.find('.//title')
        if title_element is not None:
            title_parts = []
            for part in title_element.itertext():
                title_parts.append(part.strip())
            play_title = ' '.join(title_parts)
        else:
            play_title = work.title

        character_mappings = get_character_mappings(root)

        acts = []

        # Handle prologue if it exists
        prologue_act = root.find(".//act[@num='0']")
        if prologue_act is not None:
            prologue_scenes = []
            for prologue in prologue_act.findall('.//prologue'):
                content = []

                for child in prologue:
                    if child.tag == 'speech':
                        speaker_elem = child.find('speaker')
                        if speaker_elem is not None:
                            speaker = speaker_elem.get('short') or speaker_elem.text or 'Prologue'
                        else:
                            speaker = 'Prologue'
                        lines = []

                        for line in child.findall('line'):
                            if line.find('dropcap') is not None:
                                dropcap = line.find('dropcap').text
                                remaining_text = ''.join(part for part in line.itertext() if part != dropcap)
                                line_text = f'<span class="dropcap">{dropcap}</span>{remaining_text}'
                            else:
                                line_text = ''.join(line.itertext())

                            if line_text:
                                lines.append(line_text)

                        content.append({
                            'type': 'speech',
                            'speaker': speaker,
                            'lines': lines
                        })

                    elif child.tag == 'stagedir':
                        stage_text = ''.join(child.itertext())
                        if stage_text:
                            content.append({
                                'type': 'stagedir',
                                'text': stage_text
                            })

                prologue_scenes.append({
                    'scene_title': None,  # Remove scene_title for prologue
                    'content': content
                })

            acts.append({
                'act_title': 'Prologue',
                'scenes': prologue_scenes
            })

        # Handle regular acts
        for act in root.findall('act'):
            # Debug print
            print(f"Processing act {act.get('num')}")

            if act.get('num') == '0':
                continue

            act_title = act.find('acttitle').text if act.find('acttitle') is not None else None
            scenes = []

            # Debug print
            print(f"Act {act.get('num')} title: {act_title}")
            print(f"Found scenes: {len(act.findall('scene'))}")

            for scene in act.findall('scene'):
                scene_title = scene.find('scenetitle')
                # Only use scene_title if it's different from act_title
                if scene_title is not None:
                    scene_text = ''.join(scene_title.itertext())
                    if scene_text != act_title:
                        scene_title = scene_text
                    else:
                        scene_title = None

                content = []  # Will hold both speeches and stage directions

                # Process each child of the scene in order
                for child in scene:
                    if child.tag == 'speech':
                        speaker_elem = child.find('speaker')
                        if speaker_elem is not None:
                            # Use the short attribute if available, otherwise use the text content
                            speaker = speaker_elem.get('short') or speaker_elem.text or 'Unknown Speaker'
                        else:
                            speaker = 'Unknown Speaker'
                        lines = []

                        for line in child.findall('line'):
                            # Keep the special handling for dropcaps but preserve all other characters
                            if line.find('dropcap') is not None:
                                dropcap = line.find('dropcap').text
                                remaining_text = ''.join(part for part in line.itertext() if part != dropcap)
                                line_text = f'<span class="dropcap">{dropcap}</span>{remaining_text}'
                            else:
                                line_text = ''.join(line.itertext())

                            if line_text:
                                lines.append(line_text)

                        content.append({
                            'type': 'speech',
                            'speaker': speaker,
                            'lines': lines
                        })

                    elif child.tag == 'stagedir':
                        stage_text = ''.join(child.itertext())
                        if stage_text:
                            content.append({
                                'type': 'stagedir',
                                'text': stage_text
                            })

                scenes.append({
                    'scene_title': scene_title,
                    'content': content
                })

            acts.append({
                'act_title': act_title,
                'scenes': scenes
            })

        return render_template("play.html",
                               work=work,
                               play_title=play_title,
                               acts=acts,
                               character_mappings=character_mappings)

    except ET.ParseError:
        abort(500, description="Error parsing the play file")

def get_character_mappings(root):
    """Extract character name mappings from the personae section"""
    mappings = []
    for persona in root.findall('.//persona'):
        persname = persona.find('persname')
        if persname is not None:
            short_name = persname.get('short', '')
            full_name = persname.text or ''
            if short_name and full_name:
                mappings.append({
                    'short': short_name,
                    'full': full_name
                })
    return sorted(mappings, key=lambda x: x['short'])

if __name__ == "__main__":
    app.run(debug=True)