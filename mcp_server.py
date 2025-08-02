# server.py
import logging
from mcp.server.fastmcp import FastMCP
from openai import OpenAI
import os
from dotenv import load_dotenv
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
def insight_scope(user_query: str) -> str:
    """
    InsightScope: An intelligent real-time web analysis agent.

    This tool performs dynamic, real-time web research powered by GPT-4o with browsing capabilities.
    It extracts and summarizes the most relevant, up-to-date information from trusted sources,
    including news, websites, documentation, and user reviews.

    Key Features:
    - Context-aware web search tailored to the user's query.
    - Real-time data extraction from authoritative sites.
    - Summarized insights with clickable source links.
    - Useful for market research, trend analysis, product scouting, or verifying recent developments.

    Input:
    - user_query (str): A natural-language query or topic of interest.

    Output:
    - A concise, informative summary with real-time findings and embedded links.

    Example Use Case:
    insight_scope("Latest updates on Apple's Vision Pro release")
    """
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


@mcp.tool()
def perform_general_query(user_query: str) -> str:
    """Perform a general query using a faster model."""
    client = OpenAI() # Assuming client is initialized elsewhere
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # Changed to a faster, general-purpose model
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant. Provide a concise and accurate answer to the user's query."
            },
            {
                "role": "user",
                "content": user_query
            }
        ],
    )
    return response.choices[0].message.content.strip()


@mcp.tool()
def generate_summary(long_text: str):
    """
    Summarizes long paragraphs or content from a text file in a professional, engaging manner,
    preserving the original context and key information.
    """
    # Step 1: Define the summarization prompt
    summary_prompt = [
        {
            "role": "system",
            "content": (
                "You are a professional summarization agent. Your job is to read large blocks of text "
                "and generate concise, clear, and engaging summaries. Preserve all key ideas and context, "
                "but remove redundancy or filler content. The summary should feel natural and insightful to the reader."
            )
        },
        {
            "role": "user",
            "content": (
                f"Summarize the following content:\n\n{long_text}\n\n"
                "Instructions:\n"
                "1. Keep the tone professional and engaging.\n"
                "2. Highlight important points or arguments.\n"
                "3. Avoid unnecessary repetition or verbose phrases.\n"
                "4. Maintain the integrity of the original message.\n"
                "Output the result as a plain text summary (no headings or labels)."
            )
        }
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=summary_prompt,
            temperature=0.3,
            max_tokens=600  # You can increase this if needed
        )

        summary_output = response.choices[0].message.content.strip()
        print("[DEBUG] Generated Summary:\n", summary_output)
        return summary_output

    except Exception as e:
        print("[ERROR] Failed to generate summary:", e)
        return "Summary generation failed. Please try again."



# Run the server for local development or testing
if __name__ == "__main__":
    mcp.run(transport="sse")

