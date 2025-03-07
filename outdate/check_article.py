"""Script to check IAEA article structure."""
import requests
from bs4 import BeautifulSoup

def main():
    url = "https://www.iaea.org/newscenter/news/mozambique-signs-its-third-country-programme-framework-cpf-for-2024-2029"
    
    # Set up headers to simulate a browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Print the HTML structure
    print("HTML Structure:")
    print("=" * 80)
    
    # Find main content area
    main_content = soup.find('main')
    if main_content:
        print(main_content.prettify())
    else:
        print("No main content found")
        
    # Find article content
    article = soup.find('article')
    if article:
        print("\nArticle Content:")
        print("=" * 80)
        print(article.prettify())
    else:
        print("\nNo article tag found")

if __name__ == "__main__":
    main()
