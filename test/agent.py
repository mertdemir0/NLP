from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import Agent
from pydantic import SecretStr
import os
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

# Initialize the model
llm = ChatGoogleGenerativeAI(model='gemini-2.0-flash-exp', api_key=SecretStr(os.getenv('GEMINI_API_KEY')))

# Create agent with the model
agent = Agent(
    task="Your task here",
    llm=llm
)
load_dotenv()

import asyncio

api_key = os.getenv("GEMINI_API_KEY")

llm = ChatGoogleGenerativeAI(model='gemini-2.0-flash-exp', api_key=SecretStr(os.getenv('GEMINI_API_KEY')))

async def main():
    agent = Agent(
        task="save to a database all the title date url and description from google search results site:'bloomberg.com' intitle: nuclear from: to: from to needs to be monthly from 2020 to 2025. if it's multiple pages go to all pages and collect all the data. this is an example query site:'bloomberg.com' intitle:nuclear after:2020-02-01 before:2020-03-01",
        llm=llm,
    )
    result = await agent.run()
    print(result)

asyncio.run(main())