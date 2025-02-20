import pandas as pd
import numpy as np
import logging
from datetime import datetime
import asyncio
from typing import List, Dict, Set
from playwright.async_api import async_playwright, TimeoutError
from sqlalchemy.orm import Session
from .database import init_db, RawArticle
import playwright

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("http://google.com")
        print(await page.title())
        await browser.close()

asyncio.run(main())