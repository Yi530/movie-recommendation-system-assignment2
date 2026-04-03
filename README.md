## 🎬 Movie Time – Movie Recommendation System 

This project is a Streamlit web application for searching and recommending movies.

### 1.Overview

This project extends Assignment 1 by adding a full recommendation system and system architecture.
In addition to movie search and filtering, the system now supports:
- Personalized movie recommendations using BigQuery ML
- Autocomplete search using Elasticsearch
- Frontend-backend separation using Flask
- Containerized deployment with Docker

### 2.Features

##### 2.1 Explore Mode
- Search movies by title
- Filter by genre, country, language
- Filter by rating and release year
- Sort by rating, title, or release year
- Display movie posters (TMDB API)
- Show movie details (actors, runtime, overview)

##### 2.2 Recommend Mode
- Select favorite movies
- Prevent duplicate selections
- Remove selected movies
- Clear all selections
- Generate personalized recommendations

##### 2.3 Recommendation System
2.3.1 Similarity Computation
The system adopts an item-based collaborative filtering approach using movie co-occurrence in user rating data.
Instead of explicitly computing similarity metrics such as cosine similarity or Pearson correlation, similarity between movies is inferred based on shared user interactions.
For each selected movie, the system:
- Identifies users who have rated the movie
- Retrieves other movies rated by the same users
- Counts how frequently pairs of movies appear together

Two key measures are used:
- Support: the number of users who have rated both movies  
- Score (Confidence): the normalized strength of co-occurrence
Movies that are frequently co-rated by the same users are considered similar.
This approach allows the system to capture implicit relationships between movies based on real user behavior.

2.3.2 Recommendation Generation
Based on the computed co-occurrence relationships, the system generates recommendations by aggregating candidate movies and ranking them according to their relevance.
For a given set of selected movies, the system:
- Collects all co-occurring movies associated with the selected inputs
- Aggregates co-occurrence statistics across multiple selected movies
- Computes a ranking score for each candidate

The ranking is determined using two key factors:

- Score (Confidence): reflects the strength of association between movies  
- Support: reflects how frequently the movies are co-rated by users  

Movies are ranked primarily by score and further refined using support to prioritize more reliable associations.
The top-ranked movies are returned as the final recommendations.
To ensure meaningful results, movies that are already selected by the user are excluded from the recommendation list.

2.3.3 Cold Start Handling

The system addresses the **user cold start problem** by applying a fallback recommendation strategy when no input is provided.
When the user does not select any movies, there is no available preference data to generate personalized recommendations. In this case, the system returns the top 10 most popular movies.
Popularity is determined based on the number of user ratings, ensuring that frequently watched movies are recommended.
This approach guarantees that users always receive meaningful recommendations, even without prior interaction.
However, the system does not explicitly address the **item cold start problem**, as recommendations rely on historical co-occurrence data derived from user ratings.

#### 2.4 Autocomplete
- Implemented using Elasticsearch
- Suggests movie titles dynamically while typing

### 3 System Architecture

#### 3.1 The system follows a modular frontend-backend architecture:
- Frontend: Streamlit (main.py)
- Backend: Flask API (app.py)
- Database: Google BigQuery
- ML Model: BigQuery ML
- Search Engine: Elasticsearch

#### 3.2 Flow:
User → Streamlit UI → Flask API → BigQuery ML → Results → UI


### 4 Running Locally

4.1 Install dependencies
pip install -r requirements.txt

4.2 Start backend (Flask)
python app.py

4.3 Start frontend (Streamlit)
streamlit run main.py

## Open in browser:
http://localhost:8501

### 5 Docker

#### 5.1 Backend (Flask API)
docker build -t movie-api -f Dockerfile.api .
docker run -p 5001:5001 movie-api

#### 5.2 Frontend (Streamlit)
docker build -t movie-ui .
docker run -p 8080:8080 \
  -e API_BASE_URL=http://host.docker.internal:5001 \
  -e ES_BASE_URL=http://host.docker.internal:9200 \
  movie-ui

#### 5.3 Elasticsearch
docker run -p 9200:9200 docker.elastic.co/elasticsearch/elasticsearch:8.13.4


### 6 Data Sources

- Google BigQuery (movie dataset, ratings)
- BigQuery ML (recommendation model)
- TMDB API (posters and metadata)
- Elasticsearch (autocomplete index)

### 7 Deployment

The system is containerized using Docker and can be deployed as:

- Frontend (Streamlit)
- Backend (Flask API)
- Elasticsearch service

Each component runs independently and communicates via API calls.

### Improvements from Assignment 1

- Added recommendation system using BigQuery ML
- Introduced Flask backend (API layer)
- Implemented Elasticsearch autocomplete
- Improved UI with card layout and better interaction
- Added loading indicators and error handling
- Enabled modular Docker-based deployment