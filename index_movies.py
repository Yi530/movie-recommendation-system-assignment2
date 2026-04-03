from google.cloud import bigquery
from elasticsearch import Elasticsearch, helpers

PROJECT_ID = "movie-database-489322"
TABLE_ID = "movie-database-489322.movies_dataset.movies_small"
INDEX_NAME = "movies_autocomplete"

bq_client = bigquery.Client(project=PROJECT_ID)
es = Elasticsearch("http://localhost:9200")

query = f"""
SELECT movieId, title, genres
FROM `{TABLE_ID}`
"""

rows = bq_client.query(query).result()

actions = []

for row in rows:
    action = {
        "_index": INDEX_NAME,
        "_id": row.movieId,
        "_source": {
            "movieId": row.movieId,
            "title": row.title,
            "genres": row.genres,
            "title_suggest": row.title
        }
    }
    actions.append(action)

helpers.bulk(es, actions)

print(f"Indexed {len(actions)} movies into Elasticsearch.")