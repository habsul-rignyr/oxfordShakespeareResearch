import logging
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError
from elasticsearch_dsl import Search, Q
from flask import current_app

logger = logging.getLogger(__name__)


class SearchClient:
    def __init__(self, app=None):
        self.es = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.config.setdefault('ELASTICSEARCH_URL', 'http://localhost:9200')
        app.config.setdefault('ELASTICSEARCH_INDEX', 'works')

        self.es = Elasticsearch(app.config['ELASTICSEARCH_URL'])

        # Create the index if it doesn't exist
        self.setup_index(app.config['ELASTICSEARCH_INDEX'])

    def setup_index(self, index_name):
        """Create the index with proper mappings."""
        if not self.es.indices.exists(index=index_name):
            settings = {
                "settings": {
                    "analysis": {
                        "analyzer": {
                            "eebo_analyzer": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": [
                                    "lowercase",
                                    "asciifolding",
                                    "stop",
                                    "snowball"
                                ]
                            }
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        "title": {
                            "type": "text",
                            "analyzer": "eebo_analyzer",
                            "fields": {
                                "raw": {
                                    "type": "keyword"
                                }
                            }
                        },
                        "author": {
                            "type": "text",
                            "analyzer": "eebo_analyzer",
                            "fields": {
                                "raw": {
                                    "type": "keyword"
                                }
                            }
                        },
                        "content": {
                            "type": "text",
                            "analyzer": "eebo_analyzer"
                        },
                        "publication_year": {
                            "type": "integer"
                        },
                        "tcp_id": {
                            "type": "keyword"
                        },
                        "collection": {
                            "type": "keyword"
                        },
                        "language": {
                            "type": "keyword"
                        }
                    }
                }
            }
            self.es.indices.create(index=index_name, body=settings)

    def index_work(self, work, content):
        """Index a single work with its content."""
        doc = {
            'title': work.title,
            'author': work.author,
            'content': content,
            'publication_year': work.publication_year,
            'tcp_id': work.tcp_id,
            'collection': work.collection,
            'language': work.language
        }

        try:
            self.es.index(
                index=current_app.config['ELASTICSEARCH_INDEX'],
                id=str(work.id),
                document=doc
            )
        except Exception as e:
            logger.error(f"Error indexing work {work.id}: {str(e)}")

    def search(self, query, filters=None, page=1, per_page=10):
        """
        Perform a search with various filters and pagination.

        Args:
            query (str): The search query
            filters (dict): Optional filters like {'year': (1600, 1650), 'collection': 'EEBO-TCP'}
            page (int): Page number
            per_page (int): Results per page
        """
        s = Search(using=self.es, index=current_app.config['ELASTICSEARCH_INDEX'])

        # Base query
        q = Q("multi_match",
              query=query,
              fields=['title^2', 'author^1.5', 'content'],
              fuzziness="AUTO")

        # Apply filters
        if filters:
            if 'year' in filters:
                start_year, end_year = filters['year']
                s = s.filter('range', publication_year={'gte': start_year, 'lte': end_year})

            if 'collection' in filters:
                s = s.filter('term', collection=filters['collection'])

            if 'language' in filters:
                s = s.filter('term', language=filters['language'])

        # Add query to search
        s = s.query(q)

        # Add highlighting
        s = s.highlight('content', fragment_size=150, number_of_fragments=3)
        s = s.highlight('title')

        # Add pagination
        start = (page - 1) * per_page
        s = s[start:start + per_page]

        # Execute search
        response = s.execute()

        # Format results
        results = []
        for hit in response:
            result = {
                'id': hit.meta.id,
                'title': hit.title,
                'author': hit.author if hasattr(hit, 'author') else None,
                'score': hit.meta.score,
                'highlights': []
            }

            # Add highlights
            if hasattr(hit.meta, 'highlight'):
                if hasattr(hit.meta.highlight, 'content'):
                    result['highlights'].extend(hit.meta.highlight.content)
                if hasattr(hit.meta.highlight, 'title'):
                    result['highlights'].extend(hit.meta.highlight.title)

            results.append(result)

        return {
            'results': results,
            'total': response.hits.total.value if hasattr(response.hits.total, 'value')
            else response.hits.total,
            'pages': (response.hits.total.value + per_page - 1) // per_page
            if hasattr(response.hits.total, 'value')
            else (response.hits.total + per_page - 1) // per_page
        }

    def phrase_search(self, phrase, distance=3):
        """Search for exact phrases with optional word distance."""
        s = Search(using=self.es, index=current_app.config['ELASTICSEARCH_INDEX'])

        q = Q("match_phrase", content={
            "query": phrase,
            "slop": distance
        })

        s = s.query(q).highlight('content')
        response = s.execute()

        return response

    def advanced_search(self, must_terms=None, should_terms=None, must_not_terms=None):
        """
        Perform an advanced boolean search.

        Args:
            must_terms (list): Terms that must appear
            should_terms (list): Terms that should appear
            must_not_terms (list): Terms that must not appear
        """
        s = Search(using=self.es, index=current_app.config['ELASTICSEARCH_INDEX'])

        bool_query = Q('bool')

        if must_terms:
            bool_query = bool_query & Q('bool', must=[Q('match', content=term) for term in must_terms])

        if should_terms:
            bool_query = bool_query & Q('bool', should=[Q('match', content=term) for term in should_terms])

        if must_not_terms:
            bool_query = bool_query & Q('bool', must_not=[Q('match', content=term) for term in must_not_terms])

        s = s.query(bool_query).highlight('content')
        response = s.execute()

        return response


# Create the extension
search = SearchClient()