import subprocess
from elasticsearch import Elasticsearch, NotFoundError
from flask import Flask, jsonify, make_response, request, send_from_directory
from urllib.parse import urlparse
import os
from dotenv import load_dotenv
from groq import Groq
from openai import OpenAI

def is_docker():
  try:
    with open("/proc/1/cgroup", "rt") as f:
      return "docker" in f.read()
  except Exception:
    return False

# if not in docker, load from .env file
# otherwise, python will read variables from enviroment
if not is_docker():
  load_dotenv()

app = Flask(__name__)
 
# Connect to Elasticsearch
client_el = Elasticsearch(
    os.environ.get('ELASTICSEARCH_URI'), 
    basic_auth=(
        os.environ.get('ELASTICSEARCH_USER'), 
        os.environ.get('ELASTICSEARCH_PASSWORD')
    )
)

TARGET_WEBSITE = os.environ.get('TARGET_WEBSITE')
parsed_target_url = urlparse(TARGET_WEBSITE).hostname
MODEL = os.environ.get("MODEL")
TARGET_INDEX = f'{parsed_target_url}-vectorized'
 
# Initialize LLM based on available keys
GROQ_API_KEY=os.environ.get("GROQ_API_KEY")
OPENAI_API_KEY=os.environ.get("OPENAI_API_KEY")

if GROQ_API_KEY:
  client_groq = Groq(
    api_key=GROQ_API_KEY,
  )
    
if OPENAI_API_KEY:
  client_openai = OpenAI(
    api_key=OPENAI_API_KEY,
  )
 
def get_completion(prompt, docs):
    # Craft the input for the LLM
    query = f"""
    TOP DOCUMENTS FOR USERS QUESTION: 
     
    {docs}
     
    ORIGINAL USER'S QUESTION: {prompt}
    """
    
    print(f"Token count: {len(query)}")
     
    # Choose the right LLM
    if OPENAI_API_KEY:
        client = client_openai
    elif GROQ_API_KEY:
        client = client_groq
     
    # Send the query to the LLM
    message = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": """You are an agent on website {TARGET_WEBSITE}
                Your objective is to answer the user's question based on the 
                documents retrieved from the prompt (which is based on the website content). 
                 
                If you don't know the answer, CLARIFY it to the user and don't make
                up any inexistent information outside of the documents 
                provided, and don't mention it. 
                 
                There can be multiple answers to the user's question. 
                Don't include [...] on your answers. When title or description 
                can answer the users question direct the user to the URL (with HTML code) 
                of their response to the user on what's written on the documents. 
                ALWAYS include the links in <a> tags if theres a page that can answer the user's question.
                Don't use italics or bold text.
                 
                Only prompt your answer. 
                 
                At the end of your answer, ALWAYS provide the _id(s) from the 
                document(s) that most fits the user's question and your answer 
                AND documents you end up citing in your answer
                (example: "_id:12345", "_id:12345,678891,234567"). 
                 
                PROMPT EXAMPLE:
                 
                TOP DOCUMENTS FOR USERS QUESTION: 
                 
                {
                    "_id": "100090",
                    "_source": {
                       "content_model": "wikitext",
                        "opening_text": "Before Sunset is a 2004 sequel to the 1995 romantic drama film Before Sunrise. Directed by Richard Linklater. Written by Richard Linklater, Ethan Hawke, Julie Delpy, and Kim Krizan. What if you had a second chance with the one that got away? (taglines)",
                        "wiki": "enwikiquote",
                        "auxiliary_text": [
                            "Wikipedia"
                        ], 
                    }
                }
                {
                    "_id": "104240",
                    "_source": {
                        "content_model": "wikitext",
                        "opening_text": "Dedication is a 2007 romantic dramedy about a misogynistic children's book author who is forced to work closely with a female illustrator instead of his long-time collaborator and only friend. Directed by Justin Theroux. Written by David Bromberg. With each moment we write our story.",
                        "wiki": "enwikiquote",
                        "auxiliary_text": [
                            "Wikipedia",
                            "This film article is a stub. You can help out with Wikiquote by expanding it!"
                        ],
                    }
                }
                 
                ORIGINAL USER'S QUESITON: Are there any romantic drama written after 2003?
                 
                YOUR ANSWER:
                 
                There are several romantic dramas that were written or filmed after 2003, including:
                 
                Before Sunrise, a 1995 romantic drama film that Before Sunset is a sequel to, The Mirror Has Two Faces, a 1996 American romantic dramedy film, and Get Real, a 1998 British romantic comedy-drama film about the coming of age of a gay teen.
                 
                The Mirror Has Two Faces is a 1996 American romantic dramedy film written by Richard LaGravenese, based on the 1958 French film Le Miroir à Deux Faces.
                 
                _id:100090,104240
                """ },
            {"role": "user", "content": query}
        ]
    )
     
    return {"message": message.choices[0].message.content, "docs": docs}
 
@app.route("/", methods=['POST', 'GET']) 
def query_view(): 
    if request.method == 'POST': 
        prompt = request.json['prompt'] 
         
        el_resp = client_el.search(index=TARGET_INDEX, source={
            # Excluding certain fields, so we don't exceed the token limit
            "includes": [ "last_crawled_at", "url", "title", "meta_description" ] 
        }, query={
            "sparse_vector": {
              "field": "body_content_embedding",
              "inference_id": "elser-model",
              "query": prompt
            }
        })
         
        response = get_completion(prompt, el_resp["hits"]["hits"]) 
   
        return jsonify({'response': response["message"], "docs": response["docs"]}) 
    return make_response(send_from_directory(".", path="index.html"))
 
if __name__ == "__main__":
  
  # Verify if user has the inference endpoint of the model
  try:
    client_el.inference.get(inference_id='elser-model')
  except NotFoundError:
    print('Inference endpoint not found, creating one for the app...')
    
    client_el.inference.put(
      inference_id='elser-model', 
      task_type='sparse_embedding',
      body={
        "service": "elser",
        "service_settings": {
          "num_allocations": 1,
          "num_threads": 1
        }
      }
    )
    
    print('Inference endpoint "elser-model" created.')

  # Verify if user has the target index with the vectors
  try:
    client_el.indices.get_mapping(index=f'{TARGET_INDEX}')
  except NotFoundError:
    print('Index not found, starting scraping process...')
    
    client_el.ingest.put_pipeline(id=f'{parsed_target_url}-pipeline', body={
      "processors": [
        {
          "inference": {
            "model_id": 'elser-model',
            "input_output": [
              {
                "input_field": "body_content",
                "output_field": "body_content_embedding"
              }
            ]
          }
        }
      ]
    })
    print(f'Created "{parsed_target_url}-pipeline" pipeline.')    
    
    client_el.indices.create(index=TARGET_INDEX, body={
      "settings": {
        "index":{
          "default_pipeline": f"{parsed_target_url}-pipeline" 
        }
      },
      "mappings": {
        "properties": {
          "body_content_embedding": { 
            "type": "sparse_vector"
          },
          "body_content": { 
            "type": "text"
          }
        }
      }
    })
    print(f'Created index "{TARGET_INDEX}" with the ingest pipeline of "{parsed_target_url}-pipeline" by default.')
    
    # license = client_el.license.get()
    
    # if license['license']['type'] == 'enterprise':
    #   TODO: use elastic's scraping system if user has enterprise db since 
    #   it's WAY better than by shit ass python script
    # else:
    
    with open('scrape.py') as file:
      exec(file.read())
  
  # If not, then scrape content
  app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))