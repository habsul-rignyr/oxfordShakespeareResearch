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

# Routes
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
    # Retrieve the play from the database
    work = Work.query.get(work_id)
    if not work:
        abort(404, description="Play not found")

    # Check if the file exists
    if not os.path.exists(work.file_path):
        abort(404, description="Play file not found")

    # Parse the XML file
    try:
        tree = ET.parse(work.file_path)
        root = tree.getroot()
        # Assuming the text is in <play> -> <act> -> <scene> -> <speech>
        acts = []
        for act in root.findall('act'):
            act_title = act.find('acttitle').text if act.find('acttitle') is not None else 'Unknown Act'
            scenes = []
            for scene in act.findall('scene'):
                scene_title = scene.find('scenetitle').text if scene.find('scenetitle') is not None else 'Unknown Scene'
                speeches = []
                for speech in scene.findall('speech'):
                    speaker = speech.find('speaker').text if speech.find('speaker') is not None else 'Unknown Speaker'
                    lines = [line.text for line in speech.findall('line')]
                    speeches.append({'speaker': speaker, 'lines': lines})
                scenes.append({'scene_title': scene_title, 'speeches': speeches})
            acts.append({'act_title': act_title, 'scenes': scenes})

        return render_template("play.html", work=work, acts=acts)
    except ET.ParseError:
        abort(500, description="Error parsing the play file")


# Main block
if __name__ == "__main__":
    app.run(debug=True)
