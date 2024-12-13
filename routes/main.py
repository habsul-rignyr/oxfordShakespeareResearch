# routes/main.py

from flask import render_template, request, abort, current_app
from models import db
from models.work import Work
from models.blog import BlogPost
from models.forum import Topic
from processors.xml_processor import XMLProcessor
import os
from xml.etree import ElementTree as ET
import re
import html
from urllib.parse import urlencode

def strip_html_tags(text):
    if not text:
        return ""
    clean_text = re.compile('<.*?>').sub(' ', text)
    clean_text = html.unescape(clean_text)
    return ' '.join(clean_text.split())

def update_url(**new_params):
    params = request.args.copy()
    for key, value in new_params.items():
        if value is None and key in params:
            del params[key]
        else:
            params[key] = value
    return f"{request.path}?{urlencode(params, doseq=True)}"

def register_routes(app):
    xml_processor = XMLProcessor()

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
        query = request.args.get('q', '').strip()
        page = int(request.args.get('page', 1))
        sort = request.args.get('sort', 'relevance')
        year_from = request.args.get('year_from', type=int)
        year_to = request.args.get('year_to', type=int)

        try:
            filters = {}
            active_filters = []

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
                active_filters=active_filters
            )

        except Exception as e:
            current_app.logger.error(f"Search error: {str(e)}", exc_info=True)
            return render_template(
                "search.html",
                query=query,
                results=[],
                total_results=0,
                total_pages=0,
                current_page=1,
                sort=sort,
                update_url=update_url,
                active_filters=[]
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
                content = xml_processor.process_eebo_content(root)
                return render_template("eebo_work.html",
                                    work=work,
                                    content=content)
            else:
                play_content = xml_processor.process_play_content(root)
                return render_template("play.html",
                                    work=work,
                                    play_title=play_content['title'],
                                    acts=play_content['acts'],
                                    character_mappings=play_content['character_mappings'])

        except ET.ParseError:
            abort(500, description="Error parsing XML file")

    return app