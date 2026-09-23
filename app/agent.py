# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import subprocess
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.cloud import firestore
from google.genai import types
from google.oauth2.credentials import Credentials

PROJECT_ID = "qwiklabs-gcp-03-90af3d54a148"


def get_db() -> firestore.Client:
    try:
        token = subprocess.check_output(
            ["gcloud", "auth", "print-access-token"], text=True
        ).strip()
        if token:
            creds = Credentials(token)
            return firestore.Client(project=PROJECT_ID, credentials=creds)
    except Exception:
        pass
    return firestore.Client(project=PROJECT_ID)


async def generate_memories_callback(callback_context: CallbackContext):
    """Callback to extract durable memories after each turn."""
    await callback_context.add_session_to_memory()
    return None


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        city: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


def search_pantry_items(query: str = "", category: str = "") -> str:
    """Searches or lists items in the user's Firestore pantry inventory.

    Args:
        query: Optional string to filter items by name.
        category: Optional string to filter items by category (e.g., 'dairy', 'pantry', 'produce', 'protein').

    Returns:
        JSON string listing matching pantry items.
    """
    db = get_db()
    collection_ref = db.collection("pantry_items")
    docs = collection_ref.stream()

    items = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        if query and query.lower() not in data.get("item_name", "").lower():
            continue
        if category and category.lower() != data.get("category", "").lower():
            continue
        items.append(data)

    return json.dumps(items, indent=2)


def add_or_update_pantry_item(
    item_name: str,
    category: str,
    quantity: str,
    expiration_date: str = "",
    allergens: list[str] = None,
) -> str:
    """Adds a new item or updates an existing item in the user's Firestore pantry inventory.

    Args:
        item_name: Name of the item (e.g., 'Organic Milk', 'Fresh Spinach').
        category: Category of the item ('dairy', 'pantry', 'produce', 'protein', etc.).
        quantity: Quantity string (e.g., '1 gallon', '2 lbs').
        expiration_date: Optional expiration date string (YYYY-MM-DD).
        allergens: Optional list of allergen strings (e.g., ['dairy'], ['nuts']).

    Returns:
        Confirmation string indicating success.
    """
    db = get_db()
    doc_id = item_name.lower().replace(" ", "-")
    doc_ref = db.collection("pantry_items").document(doc_id)

    item_data = {
        "id": doc_id,
        "item_name": item_name,
        "category": category,
        "quantity": quantity,
        "expiration_date": expiration_date,
        "allergens": allergens or [],
    }
    doc_ref.set(item_data)
    return f"Successfully saved pantry item '{item_name}' (ID: {doc_id}) to Firestore."


def search_recipes(query: str = "") -> str:
    """Searches for real recipes by dish name or main ingredient via TheMealDB API.

    Args:
        query: Recipe name or main ingredient to search for (e.g., 'chicken', 'pasta', 'spinach').

    Returns:
        JSON string containing matching recipes with title, category, instructions, and ingredients.
    """
    import urllib.parse
    import urllib.request

    if not query:
        query = "chicken"
    url = f"https://www.themealdb.com/api/json/v1/1/search.php?s={urllib.parse.quote(query)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            meals = data.get("meals")
            if not meals:
                return json.dumps({"message": f"No recipes found for query: '{query}'."})

            results = []
            for meal in meals[:3]:
                ingredients = []
                for i in range(1, 21):
                    ing = meal.get(f"strIngredient{i}")
                    measure = meal.get(f"strMeasure{i}")
                    if ing and ing.strip():
                        ingredients.append(
                            f"{measure.strip() if measure else ''} {ing.strip()}".strip()
                        )
                results.append({
                    "id": meal.get("idMeal"),
                    "title": meal.get("strMeal"),
                    "category": meal.get("strCategory"),
                    "area": meal.get("strArea"),
                    "instructions": meal.get("strInstructions"),
                    "thumb_url": meal.get("strMealThumb"),
                    "ingredients": ingredients,
                })
            return json.dumps(results, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch recipes: {str(e)}"})


def get_fruit_nutrition_info(fruit_name: str) -> str:
    """Fetches nutritional information (calories, fat, sugar, carbs, protein) for a specified fruit from Fruityvice API.

    Args:
        fruit_name: Name of the fruit to query (e.g., 'apple', 'banana', 'strawberry', 'orange').

    Returns:
        JSON string containing fruit nutritional data.
    """
    import os
    import urllib.parse
    import urllib.request

    fruit_name = fruit_name.strip().lower()
    if not fruit_name:
        return json.dumps({"error": "Please provide a fruit name."})

    api_key = os.getenv("FRUITYVICE_API_KEY", "")
    url = f"https://www.fruityvice.com/api/fruit/{urllib.parse.quote(fruit_name)}"
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            return json.dumps(data, indent=2)
    except Exception as e:
        return json.dumps(
            {"error": f"Failed to fetch fruit nutrition for '{fruit_name}': {str(e)}"}
        )


def geocode_address(address: str) -> str:
    """Converts an address or place name into geographic coordinates (latitude and longitude) using Google Geocoding API.

    Args:
        address: The street address, city, or location name to geocode.

    Returns:
        JSON string containing formatted_address, location (latitude, longitude), and location_type.
    """
    import os
    import urllib.parse
    import urllib.request

    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return json.dumps(
            {"error": "GOOGLE_MAPS_API_KEY environment variable is not set."}
        )

    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={urllib.parse.quote(address)}&key={api_key}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            if data.get("status") != "OK" or not data.get("results"):
                return json.dumps(
                    {
                        "error": f"Geocoding failed for address '{address}': {data.get('status')}"
                    }
                )

            result = data["results"][0]
            loc = result.get("geometry", {}).get("location", {})
            return json.dumps(
                {
                    "formatted_address": result.get("formatted_address"),
                    "location": {
                        "latitude": loc.get("lat"),
                        "longitude": loc.get("lng"),
                    },
                    "location_type": result.get("geometry", {}).get(
                        "location_type"
                    ),
                },
                indent=2,
            )
    except Exception as e:
        return json.dumps({"error": f"Failed to geocode address: {str(e)}"})


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "supermarket",
    radius_meters: float = 2000.0,
) -> str:
    """Finds nearby places (e.g. supermarkets, grocery stores, restaurants, bakeries) using Google Places API (New).

    Args:
        latitude: Latitude coordinate.
        longitude: Longitude coordinate.
        place_type: Type of place to search for (e.g., 'supermarket', 'grocery_store', 'restaurant', 'bakery').
        radius_meters: Search radius in meters (default is 2000 meters).

    Returns:
        JSON string containing key fields for nearby places (name, formatted_address, location, rating, types).
    """
    import os
    import urllib.request

    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return json.dumps(
            {"error": "GOOGLE_MAPS_API_KEY environment variable is not set."}
        )

    url = "https://places.googleapis.com/v1/places:searchNearby"
    body = json.dumps({
        "includedTypes": [place_type],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": radius_meters,
            }
        },
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.types,places.rating",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            places = data.get("places", [])
            if not places:
                return json.dumps(
                    {"message": f"No nearby places found of type '{place_type}'."}
                )

            results = []
            for p in places:
                display_name = p.get("displayName", {})
                name_text = (
                    display_name.get("text")
                    if isinstance(display_name, dict)
                    else str(display_name)
                )
                results.append({
                    "name": name_text,
                    "formatted_address": p.get("formattedAddress"),
                    "location": p.get("location"),
                    "rating": p.get("rating"),
                    "types": p.get("types"),
                })
            return json.dumps(results, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to find nearby places: {str(e)}"})


async def generate_dish_image(dish_name: str, tool_context: "ToolContext") -> str:
    """Generates an image of a dish or pantry item and uploads it to public Cloud Storage.

    Args:
        dish_name: The name of the dish or item to generate an image for (e.g., 'Spaghetti Bolognese', 'Fresh Organic Apples').
        tool_context: The ADK ToolContext injected automatically.

    Returns:
        A string containing the public HTTPS URL of the uploaded image.
    """
    import json
    import uuid
    from google import genai
    from google.genai import types as genai_types
    from google.genai.types import GenerateContentConfig, Modality
    from google.cloud import storage

    try:
        client = genai.Client()
        prompt = f"A professional food photography shot of {dish_name}, appetizing, high quality, cinematic lighting."

        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=GenerateContentConfig(response_modalities=[Modality.IMAGE]),
        )

        image_bytes = None
        if hasattr(response, "candidates") and response.candidates:
            for part in response.candidates[0].content.parts:
                if getattr(part, "inline_data", None):
                    image_bytes = part.inline_data.data
                    break

        if not image_bytes:
            return json.dumps({"error": "Failed to generate image."})

        filename = f"{dish_name.replace(' ', '_').lower()}_{uuid.uuid4().hex[:6]}.jpeg"

        # Save to ADK Artifacts
        artifact_part = genai_types.Part.from_bytes(
            data=image_bytes, mime_type="image/jpeg"
        )
        await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # Upload to Google Cloud Storage
        bucket_name = "smart-pantry-media-qwiklabs-gcp-03-90af3d54a148"
        storage_client = storage.Client(project="qwiklabs-gcp-03-90af3d54a148")
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type="image/jpeg")

        return f"https://storage.googleapis.com/{bucket_name}/{filename}"

    except Exception as e:
        return json.dumps({"error": f"Failed to generate and upload image: {str(e)}"})


async def generate_dish_video(dish_name: str, tool_context: "ToolContext") -> str:
    """Generates a short video of a dish or pantry item and uploads it to public Cloud Storage.

    Args:
        dish_name: The name of the dish or item to generate a video for.
        tool_context: The ADK ToolContext injected automatically.

    Returns:
        A string containing the public HTTPS URL of the uploaded video.
    """
    import base64
    import json
    import uuid
    from google import genai
    from google.genai import types as genai_types
    from google.cloud import storage

    try:
        client = genai.Client(vertexai=True, location="global", project="qwiklabs-gcp-03-90af3d54a148")
        prompt = f"A short, high-quality, appetizing cinematic video of {dish_name}"
        
        interaction = client.interactions.create(
            model="gemini-omni-flash-preview",
            input=prompt
        )

        video_bytes = base64.b64decode(interaction.output_video.data)
        if not video_bytes:
            return json.dumps({"error": "Failed to generate video data."})

        filename = f"{dish_name.replace(' ', '_').lower()}_{uuid.uuid4().hex[:6]}.mp4"

        # Save to ADK Artifacts
        artifact_part = genai_types.Part.from_bytes(
            data=video_bytes, mime_type="video/mp4"
        )
        await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # Upload to Google Cloud Storage
        bucket_name = "smart-pantry-media-qwiklabs-gcp-03-90af3d54a148"
        storage_client = storage.Client(project="qwiklabs-gcp-03-90af3d54a148")
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type="video/mp4")

        return f"https://storage.googleapis.com/{bucket_name}/{filename}"

    except Exception as e:
        return json.dumps({"error": f"Failed to generate and upload video: {str(e)}"})


from google.adk.tools import ToolContext
from google.adk.code_executors.agent_engine_sandbox_code_executor import AgentEngineSandboxCodeExecutor
from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from .a2ui_utils import a2ui_callback

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

base_instruction = (
    "You are a helpful AI assistant designed to provide accurate and useful information. "
    "Pay special attention to and remember all user allergies, dietary restrictions, health requirements, "
    "and stated personal preferences across conversations. Always check and respect known allergies in future responses, "
    "and use your pantry inventory tools (search_pantry_items, add_or_update_pantry_item), recipe search tool (search_recipes), "
    "fruit nutrition tool (get_fruit_nutrition_info), geocoding tool (geocode_address), places discovery tool (find_nearby_places), "
    "image generation tool (generate_dish_image), and video generation tool (generate_dish_video) when helping users plan meals and visualize dishes. "
    "You can also write and execute Python code in a secure sandbox to calculate nutrition totals or process data."
)

instruction = schema_manager.generate_system_prompt(
    role_description=base_instruction,
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=[
        PreloadMemoryTool(),
        get_weather,
        get_current_time,
        search_pantry_items,
        add_or_update_pantry_item,
        search_recipes,
        get_fruit_nutrition_info,
        geocode_address,
        find_nearby_places,
        generate_dish_image,
        generate_dish_video,
    ],
    code_executor=AgentEngineSandboxCodeExecutor(
        agent_engine_resource_name="projects/358232046747/locations/us-east1/reasoningEngines/8386856993373028352"
    ),
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)


