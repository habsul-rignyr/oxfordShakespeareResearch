import logging
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError
from elasticsearch_dsl import Search, Q, A
from flask import current_app
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from datetime import datetime

logger = logging.getLogger(__name__)


class SearchClient:
    def __init__(self, app=None):
        self.es = None
        self._index_lock = threading.Lock()
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the Elasticsearch client with the Flask app"""
        app.config.setdefault('ELASTICSEARCH_URL', 'http://localhost:9200')
        app.config.setdefault('ELASTICSEARCH_INDEX', 'works')
        app.config.setdefault('ELASTICSEARCH_THREAD_POOL_SIZE', 4)

        self.es = Elasticsearch(app.config['ELASTICSEARCH_URL'])
        self.setup_index(app.config['ELASTICSEARCH_INDEX'])

        # Make the client available at the app level
        app.elasticsearch = self

    def setup_index(self, index_name):
        """Create the index with proper mappings for Early Modern English text."""
        if not self.es.indices.exists(index=index_name):
            settings = {
                "settings": {
                    "analysis": {
                        "char_filter": {
                            "early_modern_char": {
                                "type": "mapping",
                                "mappings": [
                                    "ſ => s",
                                    "æ => ae",
                                    "œ => oe",
                                    "ƿ => w",
                                    "þ => th",
                                    "ð => d",
                                    "ȝ => y"
                                ]
                            }
                        },
                        "filter": {
                            "early_modern_synonyms": {
                                "type": "synonym",
                                "synonyms": [
                                    "ye, the",
                                    "thou, you",
                                    "thee, you",
                                    "thy, your",
                                    "thine, your",
                                    "hath, has",
                                    "doth, does",
                                    "wilt, will",
                                    "art, are",
                                    "nay, no",
                                    "ay, yes"
                                ]
                            },
                            "early_modern_stop": {
                                "type": "stop",
                                "stopwords": ["thee", "thou", "ye", "hath", "doth", "thy", "thine"]
                            }
                        },
                        "analyzer": {
                            "early_modern_english": {
                                "type": "custom",
                                "char_filter": ["early_modern_char"],
                                "tokenizer": "standard",
                                "filter": [
                                    "lowercase",
                                    "asciifolding",
                                    "early_modern_stop",
                                    "early_modern_synonyms",
                                    "snowball"
                                ]
                            }
                        }
                    },
                    "index": {
                        "max_ngram_diff": 3
                    }
                },
                "mappings": {
                    "properties": {
                        "title": {
                            "type": "text",
                            "analyzer": "early_modern_english",
                            "fields": {
                                "raw": {"type": "keyword"},
                                "suggest": {
                                    "type": "completion",
                                    "analyzer": "early_modern_english"
                                },
                                "ngram": {
                                    "type": "text",
                                    "analyzer": "early_modern_english"
                                }
                            }
                        },
                        "author": {
                            "type": "text",
                            "analyzer": "early_modern_english",
                            "fields": {
                                "raw": {"type": "keyword"},
                                "suggest": {
                                    "type": "completion",
                                    "analyzer": "early_modern_english"
                                }
                            }
                        },
                        "content": {
                            "type": "text",
                            "analyzer": "early_modern_english",
                            "term_vector": "with_positions_offsets"
                        },
                        "publication_year": {
                            "type": "integer"
                        },
                        "genre": {
                            "type": "keyword"
                        },
                        "collection": {
                            "type": "keyword"
                        },
                        "language": {
                            "type": "keyword"
                        },
                        "tcp_id": {
                            "type": "keyword"
                        },
                        "source_library": {
                            "type": "keyword"
                        },
                        "indexed_date": {
                            "type": "date"
                        }
                    }
                }
            }
            self.es.indices.create(index=index_name, body=settings)
            logger.info(f"Created index {index_name} with Early Modern English settings")

    def build_query(self, query_text, advanced_params=None):
        """Build Elasticsearch query from text and advanced parameters."""
        bool_query = Q('bool')

        if query_text:
            should_queries = [
                Q('multi_match',
                  query=query_text,
                  fields=['title^3', 'author^2', 'content'],
                  fuzziness='AUTO',
                  minimum_should_match='2<70%'),
                Q('multi_match',
                  query=query_text,
                  fields=['title.ngram^2', 'author.ngram', 'content'],
                  type='phrase',
                  slop=2)
            ]
            bool_query = bool_query & Q('bool', should=should_queries)

        if advanced_params:
            if advanced_params.get('must_terms'):
                bool_query = bool_query & Q('bool', must=[
                    Q('match', content={'query': term, 'analyzer': 'early_modern_english'})
                    for term in advanced_params['must_terms']
                ])

            if advanced_params.get('should_terms'):
                bool_query = bool_query & Q('bool', should=[
                    Q('match', content={'query': term, 'analyzer': 'early_modern_english'})
                    for term in advanced_params['should_terms']
                ], minimum_should_match=1)

            if advanced_params.get('must_not_terms'):
                bool_query = bool_query & Q('bool', must_not=[
                    Q('match', content={'query': term, 'analyzer': 'early_modern_english'})
                    for term in advanced_params['must_not_terms']
                ])

            if advanced_params.get('phrase'):
                bool_query = bool_query & Q(
                    'match_phrase',
                    content={
                        'query': advanced_params['phrase'],
                        'analyzer': 'early_modern_english',
                        'slop': 3
                    }
                )

        return bool_query if bool_query.to_dict()['bool'] else Q('match_all')

    def search(self, query=None, filters=None, advanced_params=None, sort='relevance', page=1, per_page=20):
        """Perform a search with filters and pagination."""
        try:
            search_query = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["title^3", "author^2", "content"],
                        "fuzziness": "AUTO"
                    }
                } if query else {"match_all": {}}
            }

            # Add filters if present
            if filters:
                filter_clauses = []
                if 'year' in filters:
                    filter_clauses.append({
                        "range": {
                            "publication_year": filters['year']
                        }
                    })
                if 'collections' in filters:
                    filter_clauses.append({
                        "terms": {
                            "collection": filters['collections']
                        }
                    })
                if 'genres' in filters:
                    filter_clauses.append({
                        "terms": {
                            "genre": filters['genres']
                        }
                    })
                if filter_clauses:
                    search_query["query"] = {
                        "bool": {
                            "must": [search_query["query"]],
                            "filter": filter_clauses
                        }
                    }

            # Add pagination
            from_idx = (page - 1) * per_page
            search_query["from"] = from_idx
            search_query["size"] = per_page

            # Add sorting
            if sort == 'date_asc':
                search_query["sort"] = [{"publication_year": "asc"}]
            elif sort == 'date_desc':
                search_query["sort"] = [{"publication_year": "desc"}]
            elif sort == 'title_asc':
                search_query["sort"] = [{"title.raw": "asc"}]

            # Execute search
            response = self.es.search(
                index=current_app.config['ELASTICSEARCH_INDEX'],
                body=search_query
            )

            # Process results
            results = []
            for hit in response['hits']['hits']:
                result = {
                    'id': hit['_id'],
                    'title': hit['_source'].get('title', ''),
                    'author': hit['_source'].get('author', ''),
                    'publication_year': hit['_source'].get('publication_year'),
                    'collection': hit['_source'].get('collection'),
                    'score': hit['_score']
                }
                results.append(result)

            total_hits = response['hits']['total']['value']
            total_pages = (total_hits + per_page - 1) // per_page

            return {
                'results': results,
                'total': total_hits,
                'pages': total_pages,
                'aggregations': response.get('aggregations', {})
            }

        except Exception as e:
            current_app.logger.error(f"Search error: {str(e)}", exc_info=True)
            return {
                'results': [],
                'total': 0,
                'pages': 0,
                'aggregations': {}
            }

    def index_work(self, work, content):
        """Index a single work with its content."""
        try:
            with self._index_lock:
                doc = {
                    'title': work.title,
                    'author': work.author,
                    'content': content,
                    'publication_year': work.publication_year,
                    'tcp_id': work.tcp_id,
                    'collection': work.collection,
                    'language': work.language,
                    'genre': work.genre,
                    'source_library': work.source_library,
                    'indexed_date': datetime.utcnow()
                }

                self.es.index(
                    index=current_app.config['ELASTICSEARCH_INDEX'],
                    id=str(work.id),
                    document=doc
                )
                logger.info(f"Indexed work {work.id}: {work.title}")
                return True
        except Exception as e:
            logger.error(f"Error indexing work {work.id}: {str(e)}")
            return False

    def reindex_all(self, works, content_extractor):
        """
        Reindex all works using parallel processing.

        Args:
            works: Iterable of work objects
            content_extractor: Function to extract content from a work
        """
        successful = 0
        failed = 0

        with ThreadPoolExecutor(max_workers=current_app.config.get('ELASTICSEARCH_THREAD_POOL_SIZE', 4)) as executor:
            future_to_work = {}
            for work in works:
                try:
                    content = content_extractor(work)
                    if content:
                        future = executor.submit(self.index_work, work, content)
                        future_to_work[future] = work
                except Exception as e:
                    logger.error(f"Error extracting content for work {work.id}: {str(e)}")
                    failed += 1

            for future in as_completed(future_to_work):
                work = future_to_work[future]
                try:
                    if future.result():
                        successful += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f"Error processing work {work.id}: {str(e)}")
                    failed += 1

        return successful, failed

    def suggest(self, text, field='title', limit=5):
        """Get search suggestions for autocomplete."""
        try:
            suggestion = {
                field: {
                    "prefix": text,
                    "completion": {
                        "field": f"{field}.suggest",
                        "size": limit,
                        "fuzzy": {
                            "fuzziness": "AUTO"
                        }
                    }
                }
            }

            response = self.es.search(
                index=current_app.config['ELASTICSEARCH_INDEX'],
                suggest=suggestion
            )

            suggestions = []
            for suggest in response['suggest'][field]:
                for option in suggest['options']:
                    suggestions.append({
                        'text': option['text'],
                        'score': option['_score']
                    })

            return suggestions

        except Exception as e:
            logger.error(f"Suggestion error: {str(e)}")
            return []


# Create the instance
search = SearchClient()