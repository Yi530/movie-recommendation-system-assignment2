import os
import streamlit as st
from google.cloud import bigquery
import pandas as pd
import requests
from elasticsearch import Elasticsearch
import pycountry


API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:5001")
ES_BASE_URL = os.getenv("ES_BASE_URL", "http://localhost:9200")
ES_API_KEY = os.getenv("ES_API_KEY", "")

if ES_API_KEY:
    es = Elasticsearch(
        ES_BASE_URL,
        api_key=ES_API_KEY
    )
else:
    es = Elasticsearch(ES_BASE_URL)

@st.cache_data(show_spinner=False)
def search_movie_by_title(title):
    if not title.strip():
        return []

    safe_title = title.strip().replace("'", "\\'")

    query = f"""
    SELECT
        movieId,
        title,
        genres
    FROM `movie-database-489322.movies_dataset.movies_small`
    WHERE LOWER(title) LIKE LOWER('%{safe_title}%')
    ORDER BY title
    LIMIT 10
    """

    df = client.query(query).to_dataframe()
    return df.to_dict("records")

# ===== TMDB config =====
TMDB_API_KEY = "3e3684e75ad2ab5a208290a8843a0263"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

# ===== BigQuery config =====
os.environ["GOOGLE_CLOUD_PROJECT"] = "movie-database-489322"

PROJECT_ID = "movie-database-489322"
DATASET_ID = "movies_dataset"
MOVIES_TABLE = f"`{PROJECT_ID}.{DATASET_ID}.movies`"
RATINGS_TABLE = f"`{PROJECT_ID}.{DATASET_ID}.ratings`"

client = bigquery.Client(project=PROJECT_ID)

# ===== Page config =====
st.set_page_config(
    page_title="Movie Recommendation System",
    page_icon="🎬",
    layout="wide"
)

# ===== CSS =====
st.markdown("""
<style>
.block-container {
    max-width: 1200px;
    padding-top: 2rem;
    padding-bottom: 2rem;
}

.movie-card {
    background-color: #ffffff;
    border: 2px solid #e5e7eb;
    border-radius: 14px;
    padding: 18px 20px;
    margin-top: 10px;
    margin-bottom: 16px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.movie-title {
    font-size: 1.18rem;
    font-weight: 700;
    margin-bottom: 0.45rem;
    color: #1f2937;
}

.movie-meta {
    font-size: 0.95rem;
    color: #4b5563;
    margin-bottom: 0.35rem;
    line-height: 1.45;
}
</style>
""", unsafe_allow_html=True)

# ===== Helper functions =====
@st.cache_data
def load_filter_options():
    genre_query = f"""
    WITH split_genres AS (
        SELECT TRIM(genre) AS genre
        FROM {MOVIES_TABLE},
        UNNEST(SPLIT(genres, '|')) AS genre
        WHERE genres IS NOT NULL AND genres != ''
    )
    SELECT DISTINCT genre
    FROM split_genres
    WHERE genre IS NOT NULL
      AND genre != ''
      AND genre != '(no genres listed)'
    ORDER BY genre
    """

    country_query = f"""
    SELECT DISTINCT country
    FROM {MOVIES_TABLE}
    WHERE country IS NOT NULL
      AND country != ''
    ORDER BY country
    """

    language_query = f"""
    SELECT DISTINCT language
    FROM {MOVIES_TABLE}
    WHERE language IS NOT NULL
      AND language != ''
    ORDER BY language
    """

    genres = client.query(genre_query).to_dataframe()["genre"].tolist()
    countries = client.query(country_query).to_dataframe()["country"].tolist()
    languages = client.query(language_query).to_dataframe()["language"].tolist()

    return genres, countries, languages

def get_language_name(code):
    if not code:
        return "Unknown"

    code = str(code).strip().lower()

    try:
        lang = pycountry.languages.get(alpha_2=code)
        if lang and hasattr(lang, "name"):
            return lang.name
    except:
        pass

    return code

def build_stars(rating: float) -> str:
    full_stars = int(round(rating))
    full_stars = max(0, min(full_stars, 5))
    empty_stars = 5 - full_stars
    return "⭐" * full_stars + "☆" * empty_stars


def chunk_dataframe(df, chunk_size=2):
    for i in range(0, len(df), chunk_size):
        yield df.iloc[i:i + chunk_size]


@st.cache_data(show_spinner=False)
def get_movie_details_tmdb(tmdb_id):
    try:
        if pd.isna(tmdb_id) or not tmdb_id:
            return None

        detail_url = f"https://api.themoviedb.org/3/movie/{int(tmdb_id)}"
        detail_params = {
            "api_key": TMDB_API_KEY,
            "append_to_response": "credits"
        }

        detail_response = requests.get(detail_url, params=detail_params, timeout=15)
        detail = detail_response.json()

        if detail.get("success") is False:
            return None

        return detail

    except Exception:
        return None

# ===== autocomplete=====
def autocomplete_movie(query):
    if not query:
        return []

    body = {
        "query": {
            "multi_match": {
                "query": query,
                "type": "bool_prefix",
                "fields": [
                    "title_suggest",
                    "title_suggest._2gram",
                    "title_suggest._3gram"
                ]
            }
        },
        "size": 5
    }

    res = es.search(index="movies_autocomplete", body=body)

    results = []
    for hit in res["hits"]["hits"]:
        src = hit["_source"]
        results.append({
            "movieId": src.get("movieId"),
            "title": src.get("title"),
            "genres": src.get("genres", "Unknown")
        })

    return results

# ===== Load filter values =====
genres_list, countries_list, languages_list = load_filter_options()

# ===== Header =====
st.title("🎬 Movie Time")
st.write("Search movies or get recommendations and Enjoy your movie time.")
st.caption(
    f"Available filters: {len(genres_list)} genres, "
    f"{len(countries_list)} countries, {len(languages_list)} languages."
)
st.divider()
st.subheader("Choose mode")
mode = st.radio(
    "",
    ["Explore", "Recommend"],
    horizontal=True,
    label_visibility="collapsed"
)

# ===== Top controls =====

def reset_explore_inputs():
    st.session_state["explore_movie_query"] = ""
    st.session_state["explore_movie_select"] = ""


if mode == "Explore":

    # ===== Top controls =====
    top_col1, top_col2 = st.columns([2, 1])

    with top_col1:
        explore_query = st.text_input(
            "Movie name",
            placeholder="Type a movie name for autocomplete",
            key="explore_movie_query"
        )

        if explore_query.strip():
            explore_matches = autocomplete_movie(explore_query)
        else:
            explore_matches = []

        explore_option_map = {
            f"{movie['title']} ({movie['genres']})": movie["title"]
            for movie in explore_matches
        }

        select_col, reset_col = st.columns([5, 1])

        with select_col:
            selected_explore_option = st.selectbox(
                "Choose a movie",
                options=[""] + list(explore_option_map.keys()),
                index=0,
                key="explore_movie_select"
            )

        with reset_col:
            st.write("")
            st.write("")
            st.button(
                "Reset",
                key="reset_explore_movie",
                on_click=reset_explore_inputs
            )

        if selected_explore_option:
            movie_name = explore_option_map[selected_explore_option]
        else:
            movie_name = explore_query

    with top_col2:
        sort_option = st.selectbox(
            "Sort results by",
            ["Rating", "Title", "Release Year"]
        )
    # ===== Filters =====
    with st.expander("Filters", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            selected_genre = st.selectbox("Genre", ["All"] + genres_list)

        with col2:
            selected_country = st.selectbox("Country", ["All"] + countries_list)

        with col3:
            language_query = f"""
            SELECT DISTINCT language
            FROM {MOVIES_TABLE}
            WHERE language IS NOT NULL
              AND language != ''
            ORDER BY language
            """
            language_df = client.query(language_query).to_dataframe()
            raw_languages = language_df["language"].dropna().tolist()

            language_options = {"All": "All"}
            for code in raw_languages:
                language_options[get_language_name(code)] = code

            selected_language_label = st.selectbox(
                "Language",
                list(language_options.keys())
            )

            selected_language = language_options[selected_language_label]
        col4, col5 = st.columns(2)
        with col4:
            min_rating = st.slider(
                "Minimum average rating",
                min_value=0.0,
                max_value=5.0,
                value=3.0,
                step=0.1
            )

        with col5:
            year_after = st.number_input(
                "Release year after",
                min_value=1900,
                max_value=2025,
                value=2000
            )

    # ===== Query setup =====
    if sort_option == "Rating":
        order_by = "avg_rating DESC"
    elif sort_option == "Release Year":
        order_by = "m.release_year DESC"
    else:
        order_by = "m.title ASC"

    where_clauses = [
        f"m.release_year >= {year_after}"
    ]

    if movie_name.strip():
        safe_movie_name = movie_name.strip().replace("'", "\\'")
        where_clauses.append(f"LOWER(m.title) LIKE LOWER('%{safe_movie_name}%')")

    if selected_genre != "All":
        safe_genre = selected_genre.replace("'", "\\'")
        where_clauses.append(f"LOWER(m.genres) LIKE LOWER('%{safe_genre}%')")

    if selected_country != "All":
        safe_country = selected_country.replace("'", "\\'")
        where_clauses.append(f"m.country = '{safe_country}'")

    if selected_language != "All":
        safe_language = selected_language.replace("'", "\\'")
        where_clauses.append(f"m.language = '{safe_language}'")

    where_sql = " AND ".join(where_clauses)

    query = f"""
    SELECT
        m.movieId,
        m.tmdbId,
        m.title,
        m.genres,
        m.country,
        m.language,
        m.release_year,
        AVG(r.rating) AS avg_rating,
        COUNT(r.rating) AS rating_count
    FROM {MOVIES_TABLE} m
    JOIN {RATINGS_TABLE} r
        ON m.movieId = r.movieId
    WHERE
        {where_sql}
    GROUP BY
        m.movieId, m.tmdbId, m.title, m.genres, m.country, m.language, m.release_year
    HAVING
        avg_rating >= {min_rating}
    ORDER BY
        {order_by}
    LIMIT 10
    """
    print("Executing SQL query:")
    print(query)

    df = client.query(query).to_dataframe()

    # ===== Results =====
    if movie_name.strip():
        st.subheader("Search Results")
    else:
        st.subheader("Top 10 Trending Movies")

    st.success(f"Found {len(df)} movies")

    if df.empty:
        st.warning("No movies found. Try changing the filters.")
    else:
        for chunk in chunk_dataframe(df, 2):
            cols = st.columns(2)

            for idx, (_, row) in enumerate(chunk.iterrows()):
                with cols[idx]:
                    movie_id = int(row["movieId"])
                    tmdb_id = row["tmdbId"]
                    title = row["title"]
                    genres = row["genres"] if pd.notna(row["genres"]) else "Unknown"
                    country = row["country"] if pd.notna(row["country"]) else "Unknown"
                    language = row["language"] if pd.notna(row["language"]) else "Unknown"
                    release_year = int(row["release_year"]) if pd.notna(row["release_year"]) else "Unknown"
                    rating = round(row["avg_rating"], 1)
                    rating_count = int(row["rating_count"]) if pd.notna(row["rating_count"]) else 0
                    stars = build_stars(rating)

                    detail = get_movie_details_tmdb(tmdb_id)

                    poster = None
                    actors = "No actor information"
                    runtime = "N/A"
                    overview = "No overview available."

                    if detail is not None:
                        poster_path = detail.get("poster_path")
                        if poster_path:
                            poster = TMDB_IMAGE_BASE + poster_path

                        runtime = detail.get("runtime", "N/A")
                        overview = detail.get("overview", "No overview available.")

                        credits = detail.get("credits", {})
                        cast_list = credits.get("cast", [])
                        if cast_list:
                            actors = ", ".join([c["name"] for c in cast_list[:5]])

                    with st.container(border=True):
                        left, right = st.columns([3, 1])

                        with left:
                            st.markdown(f'<div class="movie-title">{title}</div>', unsafe_allow_html=True)
                            st.markdown(
                                f'<div class="movie-meta"><b>Average Rating:</b> {rating} &nbsp;&nbsp; {stars}</div>',
                                unsafe_allow_html=True)
                            st.markdown(f'<div class="movie-meta"><b>Rating Count:</b> {rating_count}</div>',
                                        unsafe_allow_html=True)
                            st.markdown(f'<div class="movie-meta"><b>Release Year:</b> {release_year}</div>',
                                        unsafe_allow_html=True)
                            st.markdown(f'<div class="movie-meta"><b>Genre:</b> {genres}</div>', unsafe_allow_html=True)
                            st.markdown(f'<div class="movie-meta"><b>Country:</b> {country}</div>', unsafe_allow_html=True)
                            st.markdown(f'<div class="movie-meta"><b>Language:</b> {language}</div>',
                                        unsafe_allow_html=True)

                    with right:
                        if poster:
                            st.image(poster, width=140)

                    st.markdown("</div>", unsafe_allow_html=True)

                    with st.expander("🎬 View details"):
                        st.write(f"**Actors:** {actors}")
                        if runtime != "N/A":
                            st.write(f"**Runtime:** {runtime} minutes")
                        else:
                            st.write("**Runtime:** N/A")
                        st.write("**Overview:**")
                        st.write(overview)

    st.caption("Movie posters and additional metadata are provided by TMDB.")

elif mode == "Recommend":

    st.subheader("🎬 Select Movies You Like")

    movie_input = st.text_input(
        "Enter movie name",
        placeholder="Type a movie name for autocomplete (e.g. Toy Story)"
    )

    matches = autocomplete_movie(movie_input)

    if movie_input.strip():
        st.write("### Matching movies:")

        option_map = {
            f"{movie['title']} ({movie['genres']})": movie
            for movie in matches
        }

        selected_option = st.selectbox(
            "Choose a movie",
            options=[""] + list(option_map.keys()),
            index=0
        )

        if selected_option:
            chosen_movie = option_map[selected_option]

            if st.button("Add selected movie", use_container_width=True):
                already_selected = any(
                    m["movieId"] == chosen_movie["movieId"]
                    for m in st.session_state.selected_movies
                )

                if not already_selected:
                    st.session_state.selected_movies.append(chosen_movie)
                    st.rerun()
                else:
                    st.info(f"{chosen_movie['title']} is already selected.")

    if "selected_movies" not in st.session_state:
        st.session_state.selected_movies = []

    st.write("### Selected movies:")

    for idx, m in enumerate(st.session_state.selected_movies):
        with st.container(border=True):
            col1, col2 = st.columns([8, 1])

            with col1:
                st.markdown(
                    f"""
                    <div style="padding: 4px 2px;">
                        <div class="movie-title" style="font-size:1.05rem; margin-bottom:0.2rem;">
                            {m['title']}
                        </div>
                        <div class="movie-meta" style="margin-bottom:0;">
                            <b>Genre:</b> {m['genres']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with col2:
                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
                if st.button("✕", key=f"remove_{idx}", help="Remove this movie"):
                    st.session_state.selected_movies.pop(idx)
                    st.rerun()



    action_col1, action_col2 = st.columns([2, 1])

    with action_col1:
        get_recommend = st.button(
            "Get Recommendations",
            use_container_width=True,
            disabled=(len(st.session_state.selected_movies) == 0)
        )

    with action_col2:
        if st.button("Clear All", use_container_width=True):
            st.session_state.selected_movies = []
            st.rerun()

    if get_recommend:
        movie_ids = [m["movieId"] for m in st.session_state.selected_movies]

        if not movie_ids:
            st.info("No movie selected. Showing the 10 most popular movies instead.")

        with st.spinner("Generating recommendations..."):
            try:
                response = requests.post(
                    f"{API_BASE_URL}/recommend",
                    json={"movie_ids": movie_ids}
                )

                if response.status_code == 200:
                    recommendations = response.json()

                    st.write("### Recommended movies:")

                    if not recommendations:
                        st.warning(
                            "No personalized recommendations were found for your selection. Try different movies.")
                    else:
                        for i in range(0, len(recommendations), 2):
                            row_movies = recommendations[i:i + 2]
                            cols = st.columns(2)

                            for idx, movie in enumerate(row_movies):
                                with cols[idx]:
                                    tmdb_match = client.query(f"""
                                        SELECT tmdbId
                                        FROM `movie-database-489322.movies_dataset.links_small`
                                        WHERE movieId = {movie['movieId']}
                                        LIMIT 1
                                    """).to_dataframe()

                                    poster = None
                                    if not tmdb_match.empty and pd.notna(tmdb_match.iloc[0]["tmdbId"]):
                                        detail = get_movie_details_tmdb(tmdb_match.iloc[0]["tmdbId"])
                                        if detail is not None:
                                            poster_path = detail.get("poster_path")
                                            if poster_path:
                                                poster = TMDB_IMAGE_BASE + poster_path

                                    with st.container(border=True):
                                        left, right = st.columns([4, 1])

                                        with left:
                                            st.markdown(f"""
                                            <div class="movie-title">{movie['title']}</div>
                                            <div class="movie-meta"><b>Genre:</b> {movie['genres']}</div>
                                            <div class="movie-meta"><b>Score:</b> {round(movie['score'], 3)}</div>
                                            <div class="movie-meta"><b>Support:</b> {movie['support']}</div>
                                            """, unsafe_allow_html=True)

                                        with right:
                                            if poster:
                                                st.image(poster, width=120)
                else:
                    st.error("API error")

            except Exception as e:
                st.error(f"Connection failed: {e}")