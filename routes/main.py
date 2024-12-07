import os
import re
from xml.etree import ElementTree as ET
from flask import render_template, request, abort
from models import db
from models.work import Work
from models.blog import BlogPost
from models.forum import Topic
from normalization import normalize_text
from rapidfuzz.fuzz import partial_ratio, token_set_ratio
import html

def strip_html_tags(text):
    """Remove HTML tags and decode HTML entities from text"""
    if not text:
        return ""
    # First remove HTML tags
    clean_text = re.compile('<.*?>').sub(' ', text)
    # Decode HTML entities like &nbsp; &quot; etc.
    clean_text = html.unescape(clean_text)
    # Replace multiple spaces with single space
    clean_text = ' '.join(clean_text.split())
    return clean_text


def register_routes(app):
    @app.route('/')
    def home():
        # Get the 3 most recent blog posts
        recent_posts = BlogPost.query.filter_by(published=True) \
            .order_by(BlogPost.created_at.desc()) \
            .limit(3).all()

        # Get the 3 most recent forum topics
        recent_topics = Topic.query.order_by(Topic.created_at.desc()) \
            .limit(3).all()

        # Clean the forum content
        for topic in recent_topics:
            topic.clean_content = strip_html_tags(topic.content)
            if len(topic.clean_content) > 150:
                topic.clean_content = topic.clean_content[:150] + "..."

        return render_template("home.html",
                               recent_posts=recent_posts,
                               recent_topics=recent_topics)

    @app.route('/search')
    def search():
        query = request.args.get('query', '').strip()
        results = []

        if query:
            works = Work.query.all()
            matches = []
            normalized_query = normalize_text(query.lower())

            for work in works:
                normalized_title = normalize_text(work.title.lower())

                # Check if query is a substring of title (case insensitive)
                if normalized_query in normalized_title:
                    score = 100
                else:
                    # Fall back to fuzzy matching with higher thresholds
                    partial_score = partial_ratio(normalized_query, normalized_title)
                    token_score = token_set_ratio(normalized_query, normalized_title)
                    score = (partial_score + token_score) / 2

                if score > 80:  # Much higher threshold
                    matches.append((work, score))

            matches.sort(key=lambda x: x[1], reverse=True)
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

            title_element = root.find('.//title')
            if title_element is not None:
                title_parts = []
                for part in title_element.itertext():
                    title_parts.append(part.strip())
                play_title = ' '.join(title_parts)
            else:
                play_title = work.title

            character_mappings = get_character_mappings(root)
            acts = process_acts(root)

            return render_template("play.html",
                                   work=work,
                                   play_title=play_title,
                                   acts=acts,
                                   character_mappings=character_mappings)

        except ET.ParseError:
            abort(500, description="Error parsing the play file")


def get_character_mappings(root):
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


def process_acts(root):
    acts = []

    # Handle prologue
    prologue_act = root.find(".//act[@num='0']")
    if prologue_act is not None:
        prologue_scenes = process_prologue(prologue_act)
        acts.append({
            'act_title': 'Prologue',
            'scenes': prologue_scenes
        })

    # Handle regular acts
    for act in root.findall('act'):
        if act.get('num') == '0':
            continue

        act_title = act.find('acttitle').text if act.find('acttitle') is not None else None
        scenes = process_scenes(act)
        acts.append({
            'act_title': act_title,
            'scenes': scenes
        })

    return acts


def process_prologue(prologue_act):
    prologue_scenes = []
    for prologue in prologue_act.findall('.//prologue'):
        content = process_content(prologue)
        prologue_scenes.append({
            'scene_title': None,
            'content': content
        })
    return prologue_scenes


def process_scenes(act):
    scenes = []
    for scene in act.findall('scene'):
        scene_title = scene.find('scenetitle')
        if scene_title is not None:
            scene_text = ''.join(scene_title.itertext())
            if scene_text != act.find('acttitle').text:
                scene_title = scene_text
            else:
                scene_title = None

        content = process_content(scene)
        scenes.append({
            'scene_title': scene_title,
            'content': content
        })
    return scenes


def process_content(element):
    content = []
    for child in element:
        if child.tag == 'speech':
            content.append(process_speech(child))
        elif child.tag == 'stagedir':
            stage_text = ''.join(child.itertext())
            if stage_text:
                content.append({
                    'type': 'stagedir',
                    'text': stage_text
                })
    return content


def process_speech(speech_element):
    speaker_elem = speech_element.find('speaker')
    speaker = speaker_elem.get(
        'short') or speaker_elem.text or 'Unknown Speaker' if speaker_elem is not None else 'Unknown Speaker'

    lines = []
    for line in speech_element.findall('line'):
        if line.find('dropcap') is not None:
            dropcap = line.find('dropcap').text
            remaining_text = ''.join(part for part in line.itertext() if part != dropcap)
            line_text = f'<span class="dropcap">{dropcap}</span>{remaining_text}'
        else:
            line_text = ''.join(line.itertext())

        if line_text:
            lines.append(line_text)

    return {
        'type': 'speech',
        'speaker': speaker,
        'lines': lines
    }