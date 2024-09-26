import requests
import os
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, urldefrag
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Init values
base_url = os.environ.get('TARGET_WEBSITE')
client = Elasticsearch(
    os.environ.get('ELASTICSEARCH_URI'), 
    basic_auth=(
        os.environ.get('ELASTICSEARCH_USER'), 
        os.environ.get('ELASTICSEARCH_PASSWORD')
    )
)

# Necessary in order to bypass moderation
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:55.0) Gecko/20100101 Firefox/55.0',
}

urls = set()

queue = []

data_to_submit = []

def extract_links_and_headings(soup, base_url):
    links = []
    headings = []
    
    for heading_tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        headings += [h.get_text(strip=True) for h in soup.find_all(heading_tag)]
    
    for a in soup.find_all('a', href=True):
        full_url = requests.compat.urljoin(base_url, a['href'])
        links.append(full_url)
    
    return headings, links

def extract_page_metadata(content, url):
    soup = BeautifulSoup(content, 'html.parser')
    
    parsed_url = urlparse(url)
    
    # Extract meta description
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    meta_description = meta_desc['content'] if meta_desc else None
    
    # Extract title
    title = soup.title.string if soup.title else None
    
    # Extract body content
    body_content = soup.get_text(separator=' ', strip=True)
    
    # Extract headings and links
    headings, links = extract_links_and_headings(soup, url)
    
    # Create a data dictionary
    page_info = {
        "last_crawled_at": datetime.now().isoformat(),
        "body_content": body_content,
        "domain": parsed_url.netloc,
        "title": title,
        "url": url,
        "url_scheme": parsed_url.scheme,
        "meta_description": meta_description,
        "headings": headings,
        "links": links,
        "url_port": parsed_url.port,
        "url_host": parsed_url.hostname,
        "url_path": parsed_url.path
    }
    
    #adding to queue
    a_links = soup.find_all('a')
    
    for link in a_links:
        href = link.get('href')  # Use .get() to safely extract the href attribute
        if href:
            # Join the base URL and relative URLs
            full_url = urljoin(base_url, href)
            
            # Remove the fragment (part after #) from the URL
            full_url, _ = urldefrag(full_url)
            
            # Remove trailing slash unless it's the root URL
            if full_url.endswith('/') and full_url != base_url.rstrip('/'):
                full_url = full_url.rstrip('/')
            
            if full_url not in urls:
                print(f'Adding {full_url} in the queue')
                queue.append(full_url)
            urls.add(full_url)  # Add the normalized URL to the set
    
    return page_info

def initial_crawl(base_url):
    response = requests.get(url=base_url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    a_links = soup.find_all('a')
    
    for link in a_links:
        href = link.get('href')  # Use .get() to safely extract the href attribute
        if href:
            # Join the base URL and relative URLs
            full_url = urljoin(base_url, href)
            
            # Remove the fragment (part after #) from the URL
            full_url, _ = urldefrag(full_url)
            
            # Remove trailing slash unless it's the root URL
            if full_url.endswith('/') and full_url != base_url.rstrip('/'):
                full_url = full_url.rstrip('/')
            
            urls.add(full_url)
    
    # Convert the set to a list (optional)
    return list(urls)

def begin_crawl(base_url):
    queue.extend(initial_crawl(base_url))
    
    while True:
        # Once queue ends, end while loop
        if len(queue) == 0:
            break
        
        # Verify if we are going to scrape our own website, otherwise skip
        parsed_url = urlparse(queue[0])
        if parsed_url.hostname != urlparse(base_url).hostname:
            queue.pop(0)
            continue
        
        print(f'Requesting {queue[0]}...')
        
        # Extract content from pages (headings, links, etc)
        response = requests.get(url=queue[0], headers=headers)
        data_to_submit.append(extract_page_metadata(response.content, queue[0]))
        
        print(f'{queue[0]} done!')
        queue.pop(0)
        
    return data_to_submit

# Start crawling
if __name__ == "__main__":
    data = begin_crawl(base_url)
    
    parsed_target_url = urlparse(base_url)
    TARGET_INDEX = f'{parsed_target_url.hostname}-vectorized'
            
    # Upload each doc at a time to our database
    for x in data:
        print(f'Indexing {x["url"]} in f{TARGET_INDEX}')
        client.index(index=TARGET_INDEX, document=x)
        
    print('All done!')