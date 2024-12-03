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
        from rapidfuzz.process import extract

        normalized_query = normalize_text(query)
        works = Work.query.all()
        title_index = {normalize_text(work.title): work for work in works}
        matches = extract(normalized_query, title_index.keys(), limit=10)

        results = [
            title_index[match[0]]
            for match in matches
            if match[1] >= 70  # Adjust threshold if necessary
        ]

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

        # Get the play title just once at the start
        title_element = root.find('.//title')
        if title_element is not None:
            title_parts = []
            for part in title_element.itertext():
                title_parts.append(part.strip())
            play_title = ' '.join(title_parts)
        else:
            play_title = work.title

        acts = []
        for act in root.findall('act'):
            act_title = act.find('acttitle').text if act.find('acttitle') is not None else 'Unknown Act'
            scenes = []

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
                                line_text = f'<div class="line-with-dropcap"><span class="dropcap">{dropcap}</span><span class="dropcap-text">{remaining_text}</span></div>'
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

        return render_template("play.html", work=work, play_title=play_title, acts=acts)

    except ET.ParseError:
        abort(500, description="Error parsing the play file")


if __name__ == "__main__":
    app.run(debug=True)