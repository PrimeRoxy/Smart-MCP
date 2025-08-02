from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)


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


def perform_general_query(user_query: str) -> str:
    """Perform a general query using a faster model."""
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


def realtime_web_search(user_query: str) -> str:
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
