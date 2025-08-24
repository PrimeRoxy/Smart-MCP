import os
import json
import pickle
from openai import OpenAI
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from langchain_community.tools.gmail import GmailSendMessage
from langchain_google_community.gmail.create_draft import GmailCreateDraft
from langchain_google_community.gmail.search import GmailSearch, Resource
from langchain_google_community.gmail.get_message import GmailGetMessage
from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)



# ===================
# Gmail Authentication
# ===================
def authenticate_gmail():
    """Authenticate Gmail and return Gmail API service."""
    SCOPES = ['https://mail.google.com/']
    creds = None

    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            # creds = flow.run_local_server(port=0)
            creds = flow.run_console()
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds)


# Initialize Gmail service + tools
service = authenticate_gmail()
gmail_send_tool = GmailSendMessage(service=service)
gmail_draft_tool = GmailCreateDraft(api_resource=service)
gmail_search_tool = GmailSearch(api_resource=service)
gmail_get_tool = GmailGetMessage(api_resource=service)

# ===================
# Helpers
# ===================

def format_search_results(result_message):
    """
    Format Gmail tool responses into a clean conversational style
    that can be fed into OpenAI chat completion.
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.7,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an AI email assistant. "
                    "When formatting Gmail tool outputs (search, send, draft, etc.), "
                    "present them in a clear, human-like conversational style "
                    "instead of raw JSON. "
                    "Follow these rules:\n"
                    "- For search results: give a neat list (numbered or bulleted) with From, Subject, and Snippet.\n"
                    "- For sending/drafting emails: respond like an assistant confirming the action "
                    "('✅ Email sent to xyz@example.com asking about report.').\n"
                    "- Never output JSON or raw code blocks unless explicitly asked.\n"
                    "- Keep it short, clean, and natural."
                )
            },
            {
                "role": "user",
                "content": result_message
            }
        ],
    )
    return response.choices[0].message.content.strip()