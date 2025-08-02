import requests
from dotenv import load_dotenv  
import os
import json
load_dotenv() 
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
BASE_URL_PLACES = os.getenv("GOOGLE_PLACE_BASE_URL")
DETAILS_URL = os.getenv("GOOGLE_PLACE_DETAILS_URL")

#  Price level mapping
PRICE_LEVEL_MAP = {
    0: "Free",
    1: "Inexpensive",
    2: "Moderate",
    3: "Expensive",
    4: "Very Expensive"
}

# Get detailed information for a place
def get_place_details(place_id):
    # Specify the fields you want to retrieve
    fields = ",".join([
        "name",
        "formatted_address",
        "rating",
        "user_ratings_total",
        "price_level",
        "editorial_summary",
        "website",
        "opening_hours"
    ])
    params = {
        "place_id": place_id,
        "fields": fields,
        "key": GOOGLE_API_KEY
    }
    response = requests.get(DETAILS_URL, params=params)
    info = response.json()
    # Debug print (optional)
    # print(info)
    return info

# Search for places and enrich with details
def search_places(query):
    params = {
        "query": query,
        "key": GOOGLE_API_KEY
    }
    response = requests.get(BASE_URL_PLACES, params=params)
    data = response.json()

    if data.get("status") != "OK":
        return f"Sorry, I couldn't find any matching places. (Status: {data.get('status')})"

    results = data.get("results", [])
    if not results:
        return "I couldn’t find any places matching your request. Want to try a different query?"

    message_lines = ["Here’s what I found ✨:\n"]
    for place in results[:5]:  # Top 5 results only
        place_id = place.get("place_id")
        if not place_id:
            continue

        # Get enriched place details
        detail_data = get_place_details(place_id)
        result = detail_data.get("result", {})

        name = result.get("name", "Unnamed Place")
        address = result.get("formatted_address", "Address not available")
        rating = result.get("rating", "N/A")
        total_reviews = result.get("user_ratings_total", 0)
        # Convert numeric price_level to descriptive string if available
        price_level_num = result.get("price_level")
        if price_level_num is not None and isinstance(price_level_num, int):
            price_level = PRICE_LEVEL_MAP.get(price_level_num, "N/A")
        else:
            price_level = "N/A"
        # Extract editorial_summary overview if available
        summary = result.get("editorial_summary", {}).get("overview", "")
        website = result.get("website", "")
        hours = result.get("opening_hours", {}).get("weekday_text", [])
        # Extract open_now status
        open_now = result.get("opening_hours", {}).get("open_now")
        if open_now is True:
            open_status = "Open Now ✅"
        elif open_now is False:
            open_status = "Closed ❌"
        else:
            open_status = ""

         # Get coordinates for the mobile-friendly URL
        lat = place.get("geometry", {}).get("location", {}).get("lat")
        lng = place.get("geometry", {}).get("location", {}).get("lng")
        
        # Create mobile-friendly Google Maps URL
        maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}&query_place_id={place_id}"

        # Build the output message for this place
        place_info = f"🏬 **{name}**\n"
        if summary:
            place_info += f"📖 {summary}\n"
        place_info += f"⭐ {rating} ({total_reviews} reviews)\n"
        if open_status:
            place_info += f"⏰ {open_status}\n"
        place_info += f"💰 Price Level: {price_level}\n"
        place_info += f"📍 {address}\n"
        if hours:
            place_info += f"🕒 Hours: {' | '.join(hours)}\n"
        if website:
            place_info += f"🌐 [Visit Website]({website})\n"
        place_info += f"[📍 View on Google Maps]({maps_url})\n"

        message_lines.append(place_info)

    return "\n\n".join(message_lines)


def chat_with_places_assistant(user_query, client) -> str:
    places_result = search_places(user_query)
    print(places_result)  # Debug print (optional)

    # If search_places returns dict/list, convert it to a readable string
    if isinstance(places_result, (dict, list)):
        places_text = json.dumps(places_result, indent=2)
    else:
        places_text = str(places_result)

    # Step 2: Send the data to OpenAI for formatting, with clear instructions on map links
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant that formats raw Google Places data into a friendly, easy-to-read response.\n\n"
                    "You are also a knowledgeable and friendly Dubai travel assistant. Your job is to help tourists plan, explore, and enjoy their trip by offering personalized, accurate, and up-to-date recommendations. You should understand the user’s intent and provide concise, helpful, and engaging responses that align with real-world travel experiences in Dubai.\n\n"
                    "Be ready to answer questions about:\n"
                    "- Place Exploration – Suggest popular spots, hidden gems, evening activities, cultural highlights, and personalized itineraries.\n"
                    "- Food & Dining – Recommend restaurants, cafés, dessert places, and cuisine-specific venues by location or mood (e.g., rooftop, budget, local).\n"
                    "- Travel & Transportation – Offer travel time estimates, route suggestions, metro vs taxi advice, and walkability between locations.\n"
                    "- Nearby Recommendations – Suggest attractions, dining spots, and experiences close to landmarks or user-specified areas.\n"
                    "- Timing & Availability – Provide opening/closing times, seasonal info, best visit times, and layover plans.\n\n"
                    "Ensure your responses are:\n"
                    "- Friendly and informative\n"
                    "- Tailored to the user’s context (location, interest, time constraints)\n"
                    "- Clear and practical for real-world travelers\n"
                    "- Strictly don't provide more than 5 places for a day\n\n"
                    "## Itinerary Structure\n"
                    "- **Activities:** Include **2–4 activities per day**.\n"
                    "- **Details per Activity:** Mention **timing, neighborhood/area, and travel method** (taxi, metro, walking).\n"
                    "- **Food Recommendations:** Include **restaurants or cafes** near activity locations.\n"
                    "- **Local Flavor:** Suggest at least one **photo-worthy spot or unique local experience** each day.\n\n"
                    "**IMPORTANT:** When including any Google Maps links in your response, copy the links exactly as they appear in the input. Do not modify, replace, or reformat them in any way.\n\n"
                    "Keep the tone conversational yet confident, as if you're a seasoned local guide."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Format the following search results into a conversational response with the maps link unchanged:\n\n{places_text}"
                )
            }
        ]
    )
    return response.choices[0].message.content

