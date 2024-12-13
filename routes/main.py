import os
import re
import html
from xml.etree import ElementTree as ET
from flask import render_template, request, abort, url_for, flash, current_app
from models import db
from models.work import Work
from models.blog import BlogPost
from models.forum import Topic
from normalization import normalize_text
from urllib.parse import urlencode
from elasticsearch_dsl import Q


def strip_html_tags(text):
    """Remove HTML tags and decode HTML entities from text"""
    if not text:
        return ""
    clean_text = re.compile('<.*?>').sub(' ', text)
    clean_text = html.unescape(clean_text)
    clean_text = ' '.join(clean_text.split())
    return clean_text


def update_url(**new_params):
    """Update URL parameters while maintaining existing ones"""
    params = request.args.copy()
    for key, value in new_params.items():
        if value is None and key in params:
            del params[key]
        else:
            params[key] = value
    return f"{request.path}?{urlencode(params, doseq=True)}"


def get_character_mappings(root):
    """Extract character mappings from XML"""
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
    """Process acts from XML"""
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
    """Process prologue content"""
    prologue_scenes = []
    for prologue in prologue_act.findall('.//prologue'):
        content = process_content(prologue)
        prologue_scenes.append({
            'scene_title': None,
            'content': content
        })
    return prologue_scenes


def process_scenes(act):
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

        content = process_content(scene)
        scenes.append({
            'scene_title': scene_title,
            'content': content
        })
    return scenes


def process_content(element):
    """Process content of a scene or prologue"""
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
    """Process speech content"""
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


def process_eebo_content(root):
    """Process EEBO-TCP XML content into displayable sections"""
    content = []

    # Find the text element with namespace
    text_elem = root.find('.//{http://www.tei-c.org/ns/1.0}text')
    if text_elem is None:
        return content

    # Process front matter
    front = text_elem.find('.//{http://www.tei-c.org/ns/1.0}front')
    if front is not None:
        front_content = process_eebo_section(front)
        if front_content:
            content.append(('Front Matter', front_content))

    # Process main body
    body = text_elem.find('.//{http://www.tei-c.org/ns/1.0}body')
    if body is not None:
        body_content = process_eebo_section(body)
        if body_content:
            content.append(('Main Text', body_content))

    # Process back matter
    back = text_elem.find('.//{http://www.tei-c.org/ns/1.0}back')
    if back is not None:
        back_content = process_eebo_section(back)
        if back_content:
            content.append(('Back Matter', back_content))

    return content


def process_eebo_section(section):
    """Process a section of EEBO-TCP XML into formatted text"""
    content = []

    def process_text_with_marks(element):
        """Process text while handling special characters and hyphenation"""
        text_parts = []
        last_was_hyphen = False

        for item in element.iter():
            # Handle g elements (special characters)
            if item.tag.endswith('}g'):
                ref = item.get('ref', '')
                if 'EOLhyphen' in ref:
                    last_was_hyphen = True
                    continue
                # Handle other special characters
                if 'cmbAbbrStroke' in ref:
                    text_parts.append('̄')  # Unicode combining macron
                continue

            # Get text content
            text = item.text or ''
            tail = item.tail or ''

            # Handle text based on previous hyphen
            if last_was_hyphen:
                text = text.lstrip()  # Remove leading space after hyphen
                last_was_hyphen = False

            if text:
                text_parts.append(text)
            if tail:
                text_parts.append(tail)

        return ''.join(text_parts)

    for elem in section.iter():
        tag = elem.tag.split('}')[-1]  # Remove namespace

        if tag == 'p':  # Paragraph
            text = process_text_with_marks(elem)
            if text.strip():
                content.append(('paragraph', text))
        elif tag == 'head':  # Heading
            text = process_text_with_marks(elem)
            if text.strip():
                content.append(('heading', text))
        elif tag == 'lb':  # Line break
            content.append(('linebreak', None))
        elif tag == 'note':  # Notes
            text = process_text_with_marks(elem)
            if text.strip():
                content.append(('note', text))
        elif tag == 'hi':  # Highlighted text
            text = process_text_with_marks(elem)
            if text.strip():
                content.append(('highlight', text))

    return content


def register_routes(app):
    @app.route('/')
    def home():
        recent_posts = BlogPost.query.filter_by(published=True) \
            .order_by(BlogPost.created_at.desc()) \
            .limit(3).all()

        recent_topics = Topic.query.order_by(Topic.created_at.desc()) \
            .limit(3).all()

        for topic in recent_topics:
            topic.clean_content = strip_html_tags(topic.content)
            if len(topic.clean_content) > 150:
                topic.clean_content = topic.clean_content[:150] + "..."

        return render_template("home.html",
                               recent_posts=recent_posts,
                               recent_topics=recent_topics)

    @app.route('/search')
    def search():
        # Get search parameters
        query = request.args.get('q', '').strip()
        page = int(request.args.get('page', 1))
        sort = request.args.get('sort', 'relevance')
        year_from = request.args.get('year_from', type=int)
        year_to = request.args.get('year_to', type=int)

        current_app.logger.debug(f"Search route called with parameters: query={query}, "
                                 f"year_from={year_from}, year_to={year_to}")

        try:
            # Build filters
            filters = {}
            active_filters = []  # List to store active filters for display

            if year_from or year_to:
                year_range = {}
                if year_from:
                    year_range['gte'] = year_from
                    active_filters.append({
                        'label': 'From Year',
                        'value': year_from,
                        'remove_url': update_url(year_from=None)
                    })
                if year_to:
                    year_range['lte'] = year_to
                    active_filters.append({
                        'label': 'To Year',
                        'value': year_to,
                        'remove_url': update_url(year_to=None)
                    })
                filters['year'] = year_range

            current_app.logger.debug(f"Built year range filter: {filters}")

            # Perform search
            search_results = current_app.elasticsearch.search(
                query=query,
                filters=filters,
                sort=sort,
                page=page,
                per_page=20
            )

            return render_template(
                "search.html",
                query=query,
                results=search_results['results'],
                total_results=search_results['total'],
                total_pages=search_results['pages'],
                current_page=page,
                sort=sort,
                update_url=update_url,
                active_filters=active_filters  # Pass the list of filter objects
            )

        except Exception as e:
            current_app.logger.error(f"Search route error: {str(e)}", exc_info=True)
            return render_template(
                "search.html",
                query=query,
                results=[],
                total_results=0,
                total_pages=0,
                current_page=1,
                sort=sort,
                update_url=update_url,
                active_filters=[]  # Empty list for error case
            )

    @app.route('/work/<int:work_id>')
    def render_work(work_id):
        work = Work.query.get_or_404(work_id)
        if not os.path.exists(work.file_path):
            abort(404, description="File not found")

        try:
            tree = ET.parse(work.file_path)
            root = tree.getroot()

            if work.collection == 'EEBO-TCP':
                content = process_eebo_content(root)
                return render_template("eebo_work.html",
                                       work=work,
                                       content=content)
            else:
                # Original play processing logic
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
            abort(500, description="Error parsing XML file")

    @app.route('/test_search')
    def test_search():
        """Temporary route to test Elasticsearch directly"""
        try:
            # Test basic search
            test_query = {
                "query": {
                    "multi_match": {
                        "query": "shakespeare",
                        "fields": ["title^3", "author^2", "content"]
                    }
                }
            }

            result = current_app.elasticsearch.es.search(
                index=current_app.config['ELASTICSEARCH_INDEX'],
                body=test_query
            )

            return {
                "total_hits": result['hits']['total']['value'],
                "first_few_hits": [
                    {
                        "title": hit['_source'].get('title'),
                        "author": hit['_source'].get('author'),
                        "score": hit['_score']
                    }
                    for hit in result['hits']['hits'][:5]
                ],
                "query_used": test_query
            }

        except Exception as e:
            return {"error": str(e)}

    return app