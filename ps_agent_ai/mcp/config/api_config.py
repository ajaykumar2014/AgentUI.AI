import os
from dotenv import load_dotenv

load_dotenv(override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
JIRA_BASE_URL=os.getenv("JIRA_BASE_URL")
JIRA_EMAIL=os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN=os.getenv("JIRA_API_TOKEN")
JIRA_PROJECT_KEY=os.getenv("JIRA_PROJECT_KEY")