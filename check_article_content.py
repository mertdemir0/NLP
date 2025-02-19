"""Script to check IAEA article content structure."""
import requests
from bs4 import BeautifulSoup
import json

def main():
    url = "https://www.iaea.org/newscenter/news/iaea-to-host-international-symposium-on-ai-and-nuclear-energy-in-december"
    
    # Set up headers to simulate a browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://www.iaea.org/news'
    }
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print("Title:")
    print("=" * 80)
    title = soup.find('h1')
    if title:
        print(title.get_text(strip=True))
    else:
        print("No title found")
        
    print("\nContent Areas:")
    print("=" * 80)
    
    # Try different content areas
    content_areas = [
        ('div', 'field--name-body'),
        ('div', 'field--type-text-with-summary'),
        ('div', 'news-story-text'),
        ('div', 'node__content'),
        ('div', 'field--name-field-article-content'),
        ('div', 'field--name-field-press-release-content'),
        ('article', None),
        ('main', None)
    ]
    
    for tag, class_name in content_areas:
        print(f"\nChecking {tag}.{class_name if class_name else ''}")
        print("-" * 40)
        content_div = soup.find(tag, class_=class_name) if class_name else soup.find(tag)
        if content_div:
            print(content_div.prettify())
        else:
            print("Not found")
            
    print("\nJSON Data:")
    print("=" * 80)
    for script in soup.find_all('script', type='application/json'):
        try:
            data = json.loads(script.string)
            print(json.dumps(data, indent=2))
        except:
            continue

if __name__ == "__main__":
    main()
