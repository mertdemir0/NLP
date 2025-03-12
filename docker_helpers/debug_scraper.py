#!/usr/bin/env python
"""
Debug script to diagnose scraping issues
"""
import os
import sys
import logging
import json
import base64
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Add project directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from docker_config import get_env, get_db_path

# Initialize connections
def save_debug_data(date, html_content, screenshot_data=None):
    """Save debug data to files for inspection"""
    debug_dir = os.path.join(os.environ.get('DATA_DIR', 'data'), 'debug')
    os.makedirs(debug_dir, exist_ok=True)
    
    # Save HTML content
    html_file = os.path.join(debug_dir, f"google_search_{date}.html")
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # Save screenshot if available
    if screenshot_data:
        try:
            screenshot_file = os.path.join(debug_dir, f"google_search_{date}.png")
            with open(screenshot_file, 'wb') as f:
                f.write(base64.b64decode(screenshot_data))
        except Exception as e:
            logging.error(f"Error saving screenshot: {str(e)}")
    
    logging.info(f"Debug data for {date} saved to {debug_dir}")
    return html_file

def check_google_access():
    """Test direct access to Google to check if we can connect"""
    import requests
    
    try:
        response = requests.get('https://www.google.com', timeout=10)
        if response.status_code == 200:
            logging.info("Direct access to Google successful")
            return True
        else:
            logging.error(f"Direct access to Google failed with status code: {response.status_code}")
            return False
    except Exception as e:
        logging.error(f"Direct access to Google failed with error: {str(e)}")
        return False

def test_splash_with_google(date="2022-01-01"):
    """Test if Splash can access Google and what response we're getting"""
    import requests
    import json
    
    splash_url = get_env('SPLASH_URL', 'http://splash:8050')
    logging.info(f"Testing Splash connection at {splash_url}")
    
    # Custom Lua script for Google
    lua_script = """
    function main(splash, args)
        -- Set user agent to a normal browser
        splash:set_user_agent("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        
        -- Configure viewport like a desktop
        splash:set_viewport_size(1920, 1080)
        
        -- Set normal browser headers
        splash:set_custom_headers({
            ["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            ["Accept-Language"] = "en-US,en;q=0.9",
            ["Accept-Encoding"] = "gzip, deflate, br",
            ["Connection"] = "keep-alive",
            ["Cache-Control"] = "max-age=0",
            ["Sec-Ch-Ua"] = '"Chromium";v="122", "Google Chrome";v="122", "Not:A-Brand";v="99"',
            ["Sec-Ch-Ua-Mobile"] = "?0",
            ["Sec-Ch-Ua-Platform"] = '"macOS"',
            ["Sec-Fetch-Dest"] = "document",
            ["Sec-Fetch-Mode"] = "navigate",
            ["Sec-Fetch-Site"] = "none",
            ["Sec-Fetch-User"] = "?1",
            ["Upgrade-Insecure-Requests"] = "1"
        })
        
        -- Enable JS
        splash.js_enabled = true
        
        -- Private mode to avoid cookies
        splash.private_mode_enabled = true
        
        -- Extra options
        splash.resource_timeout = 20
        splash.images_enabled = true
        
        -- Initial load with 10s wait
        splash:go(args.url)
        splash:wait(5)
        
        -- Scroll down slowly
        for i = 1, 10 do
            splash:evaljs("window.scrollBy(0, 300)")
            splash:wait(0.3)
        end
        
        -- Wait a bit more
        splash:wait(2)
        
        -- Check for captcha or unusual traffic message
        local has_captcha = splash:evaljs([[
            (document.body.innerText.indexOf('captcha') > -1) || 
            (document.body.innerText.indexOf('unusual traffic') > -1) ||
            (document.body.innerText.indexOf('sorry') > -1)
        ]])
        
        local search_results = splash:evaljs([[
            document.querySelectorAll('a[href*="bloomberg.com"]').length
        ]])
        
        -- Return complete response
        return {
            html = splash:html(),
            png = splash:png(),
            url = splash:url(),
            has_captcha = has_captcha,
            search_results = search_results
        }
    end
    """
    
    # Prepare Google search URL
    query = f'site:bloomberg.com intitle:nuclear "{date}"'
    url = f"https://www.google.com/search?q={query}&num=20"
    
    try:
        # Connect to Splash and run the script
        response = requests.post(
            f"{splash_url}/execute",
            json={
                'lua_source': lua_script,
                'url': url,
                'timeout': 60
            },
            timeout=70  # Higher timeout for the request
        )
        
        if response.status_code == 200:
            try:
                result = response.json()
                logging.info(f"Splash response received for {date}: Size: {len(result.get('html', ''))}")
                logging.info(f"Page URL: {result.get('url', 'Unknown')}")
                logging.info(f"Has CAPTCHA: {result.get('has_captcha', 'Unknown')}")
                logging.info(f"Bloomberg links found: {result.get('search_results', 'Unknown')}")
                
                # Save the debug data
                html_file = save_debug_data(date, result.get('html', ''), result.get('png'))
                
                # Print first 500 characters of HTML to help debug
                html_preview = result.get('html', '')[:500] + "..." if len(result.get('html', '')) > 500 else result.get('html', '')
                logging.info(f"HTML Preview: {html_preview}")
                
                return result
                
            except json.JSONDecodeError:
                logging.error("Invalid JSON response from Splash")
                return None
        else:
            logging.error(f"Splash request failed with status code: {response.status_code}")
            logging.error(f"Response: {response.text}")
            return None
            
    except Exception as e:
        logging.error(f"Splash request failed with error: {str(e)}")
        return None

def main():
    """Main function to run tests"""
    logging.info("Starting debug checks for Google scraper")
    
    # Check if direct access to Google works
    check_google_access()
    
    # Test Splash with Google for a few dates
    dates_to_test = ["2022-01-01", "2023-01-01", "2024-01-01"]
    for date in dates_to_test:
        logging.info(f"Testing Google search for date: {date}")
        result = test_splash_with_google(date)
        
        if result:
            if result.get('has_captcha', False):
                logging.warning(f"CAPTCHA detected for date {date}!")
            elif result.get('search_results', 0) > 0:
                logging.info(f"Found {result.get('search_results')} Bloomberg links for {date}")
            else:
                logging.warning(f"No search results found for {date}")

if __name__ == "__main__":
    main()
