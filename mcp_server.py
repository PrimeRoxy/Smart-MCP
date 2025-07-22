# server.py
import logging
from mcp.server.fastmcp import FastMCP
from openai import OpenAI
import os
from dotenv import load_dotenv
import requests
import json

# Load environment variables from .env file
load_dotenv()

# Create an MCP server instance named "Demo"
# Provide host and port during instantiation
mcp = FastMCP("Demo", host="0.0.0.0", port=8000)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)



# Web search tool using GPT-4o search preview
@mcp.tool()
def perform_search(user_query: str) -> str:
    """Perform real-time web search using OpenAI GPT-4o with web browsing"""
    response = client.chat.completions.create(
        model="gpt-4o-search-preview",
        web_search_options={"search_context_size": "low"},
        messages=[
            {
                "role": "system",
                "content": "Answer the user's query to the point using real-time web results. Do not include any extra information or commentary."
            },
            {
                "role": "user",
                "content": user_query
            }
        ],
    )
    return response.choices[0].message.content.strip()

# Example static tool for testing
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@mcp.tool()
def generate_search_queries(flattened_message: str):
    """
    Accepts a flattened message that contains the full system prompt, conversation context, and user's question.
    Uses OpenAI to extract a clean search query and generate a semantic search query.
    """
    # Step 1: Ask OpenAI to extract final query and summarize the conversation
    extraction_prompt = [
        {
            "role": "system",
            "content": (
                "You are a backend assistant that receives a single message containing instructions, "
                "conversation history, and the user's final question. Extract clean components needed for vector search."
            )
        },
        {
            "role": "user",
            "content": (
                f"Here is the message:\n{flattened_message}\n\n"
                "1. Extract only the user's final question (no labeling).\n"
                "2. Extract a very short summary (1–3 lines) of the conversation context relevant to the question.\n\n"
                "Respond in text format with keys: 'query' and 'summary'."
            )
        }
    ]

    extraction_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=extraction_prompt,
        temperature=0.2,
        max_tokens=250
    )
    print("[DEBUG] Extraction Response from LLM:", extraction_response.choices[0].message.content)
    try:
        parsed = json.loads(extraction_response.choices[0].message.content)
        user_query = parsed.get("query", "").strip()
        summary = parsed.get("summary", "").strip()
    except Exception as e:
        print("[ERROR] Failed to parse JSON from LLM response:", e)
        return []

    print("[DEBUG] Extracted Query:", user_query)
    print("[DEBUG] Extracted Summary:", summary)

    # Step 2: Generate semantic search queries from the clean query and summary
    query_gen_prompt = [
        {
            "role": "system",
            "content": (
                "You are an AI assistant that generates short, high-quality search queries. "
                "Always ensure the generated search query preserves the main context and intent of the user's original question. "
                "Use the conversation summary only if it helps clarify the user's intent, but do not let it override or dilute the user's main question."
            )
        },
        {
            "role": "user",
            "content": (
                f"Conversation Summary:\n{summary}\n\n"
                f"User Query:\n{user_query}\n\n"
                "Generate 1 precise search query that matches the user's main question and preserves its core context."
            )
        }
    ]

    response_queries = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=query_gen_prompt,
        temperature=0.2,
        max_tokens=150
    )

    proposed_queries_text = response_queries.choices[0].message.content
    print("[DEBUG] Proposed Search Queries from LLM:\n", proposed_queries_text)

    # Step 3: Parse search queries from LLM output
    queries = []
    for line in proposed_queries_text.splitlines():
        line = line.strip("-•*\"•.\t ").strip()
        if line:
            queries.append(line)

    if not queries and proposed_queries_text:
        queries = [q.strip() for q in proposed_queries_text.split(".") if q.strip()]

    queries = queries[:4]
    print("[DEBUG] Final Parsed Queries:", queries)

    return queries


# Run the server for local development or testing
if __name__ == "__main__":
    mcp.run(transport="sse")

