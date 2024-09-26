# Website Vector Search with LLMs

This project provides a Flask-based web app that allows users to search through a website's content using Elasticsearch and vector search with large language models (LLMs). The app crawls a target website, extracts content, stores it in Elasticsearch, and uses LLMs to provide accurate answers based on the website's documents.

## Features
- **Vector search**: Uses Elasticsearch's ELSER model to vectorize and search through website content.
- **LLM integration**: Supports OpenAI and Groq for answering queries based on retrieved documents.
- **Automatic crawling and indexing**: A Python script (`scrape.py`) crawls the target website and stores its data in Elasticsearch.
- **Responsive web interface**: Users can input search queries and view results directly from the provided web interface.

## Requirements
- **Python 3.10**
- **Docker** (optional)
- **Elasticsearch** (with ELSER model support)
- **OpenAI or Groq API keys** (optional, for LLM integration)

## Setup

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/website-vector-search.git
cd website-vector-search
```

### 2. Install dependencies
If not using Docker, install dependencies manually:
```bash
pip install -r requirements.txt
```

### 3. Configure environment variables
Create a `.env` file with the following variables:

```bash
ELASTICSEARCH_URI=<Your Elasticsearch URI>
ELASTICSEARCH_USER=<Elasticsearch username>
ELASTICSEARCH_PASSWORD=<Elasticsearch password>
TARGET_WEBSITE=<URL of the target website>
MODEL=<LLM model (e.g., gpt-3.5-turbo)>
GROQ_API_KEY=<Your Groq API key>
OPENAI_API_KEY=<Your OpenAI API key>
```

### 4. Run the app

#### Using Docker:

1. Build the Docker image:

```bash
docker build -t website-vector-search .
```

2. Run the container:
```
docker run -p 5000:5000 \
-e ELASTICSEARCH_URI=<Your Elasticsearch URI> \
-e ELASTICSEARCH_USER=<Elasticsearch username> \
-e ELASTICSEARCH_PASSWORD=<Elasticsearch password> \
-e TARGET_WEBSITE=<URL of the target website> \
-e MODEL=<LLM model (e.g., gpt-3.5-turbo)> \
-e GROQ_API_KEY=<Your Groq API key> \
-e OPENAI_API_KEY=<Your OpenAI API key> \
website-vector-search
```

#### Without Docker:

Simply run the Flask app:

```bash
python app.py
```

### 5. Access the web interface
Open your browser and navigate to [http://localhost:5000](http://localhost:5000)

## Usage
- **Search Queries**: Enter a search query in the web interface. The app will retrieve relevant documents from the website based on the vectorized content and use LLMs to generate an answer.
- **Crawling**: The app automatically crawls the target website to collect and index its content into Elasticsearch.
- **LLM Integration**: The app can use either OpenAI or Groq APIs to generate responses based on the content of the indexed documents.

## File Structure
- `app.py`: The main Flask app that handles web requests and integrates Elasticsearch and LLMs.
- `scrape.py`: Python script for crawling the target website and indexing the data into Elasticsearch.
- `Dockerfile`: Docker configuration to containerize the app.
- `index.html`: Basic web interface for submitting search queries.