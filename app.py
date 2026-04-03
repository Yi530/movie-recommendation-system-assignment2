from flask import Flask, request, jsonify
from google.cloud import bigquery

app = Flask(__name__)
client = bigquery.Client()


@app.route("/recommend", methods=["GET", "POST"])
def recommend():
    if request.method == "POST":
        data = request.get_json()
        movie_ids = data.get("movie_ids", [])
    else:
        movie_ids = [1, 3, 5, 7]  # 默认测试数据

    if not movie_ids:
        query = """
        SELECT
            m.movieId,
            m.title,
            m.genres,
            AVG(r.rating_im) AS avg_score,
            COUNT(*) AS support
        FROM `movie-database-489322.movies_dataset.ratings_small` r
        JOIN `movie-database-489322.movies_dataset.movies_small` m
            ON r.movieId = m.movieId
        WHERE r.rating_im >= 0.8
        GROUP BY m.movieId, m.title, m.genres
        ORDER BY support DESC, avg_score DESC
        LIMIT 10
        """

        results = client.query(query).result()

        output = []
        for row in results:
            output.append({
                "movieId": row.movieId,
                "title": row.title,
                "genres": row.genres,
                "score": float(row.avg_score),
                "support": int(row.support)
            })

        return jsonify(output)

    movie_union = " UNION ALL ".join([f"SELECT {int(m)} AS movieId" for m in movie_ids])

    query = f"""
    WITH selected_movies AS (
        {movie_union}
    ),
    similar_users AS (
        SELECT
            r.userId,
            COUNT(*) AS common_movies
        FROM `movie-database-489322.movies_dataset.ratings_small` r
        JOIN selected_movies s
            ON r.movieId = s.movieId
        WHERE r.rating_im >= 0.8
        GROUP BY r.userId
    ),
    top_users AS (
        SELECT userId
        FROM similar_users
        ORDER BY common_movies DESC, userId
        LIMIT 5
    ),
    recommended_movies AS (
        SELECT
            r.movieId,
            AVG(r.rating_im) AS avg_score,
            COUNT(*) AS support
        FROM `movie-database-489322.movies_dataset.ratings_small` r
        JOIN top_users u
            ON r.userId = u.userId
        WHERE r.rating_im >= 0.8
          AND r.movieId NOT IN (SELECT movieId FROM selected_movies)
        GROUP BY r.movieId
    )
    SELECT
        m.movieId,
        m.title,
        m.genres,
        rm.avg_score,
        rm.support
    FROM recommended_movies rm
    JOIN `movie-database-489322.movies_dataset.movies_small` m
        ON rm.movieId = m.movieId
    ORDER BY rm.avg_score DESC, rm.support DESC
    LIMIT 10
    """

    results = client.query(query).result()

    output = []
    for row in results:
        output.append({
            "movieId": row.movieId,
            "title": row.title,
            "genres": row.genres,
            "score": float(row.avg_score),
            "support": int(row.support)
        })

    return jsonify(output)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)