# Smart Pantry Agent

A conversational agent that helps home cooks discover recipes, track pantry items, and respect user allergies.

<video src="agent_demo.webm" controls autoplay loop>
  Your browser does not support the video tag.
</video>
## Capabilities

The Smart Pantry Agent implements the following capabilities, fully wired to Google Cloud services:

* **Pantry Inventory (Firestore)**: Tracks the user's pantry items.
  * Search pantry items (`search_pantry_items`).
  * Add or update pantry items (respects allergies, quantities, and expiration dates) (`add_or_update_pantry_item`).
* **Cross-Session Memory (Vertex AI Memory Bank)**: Remembers user allergies, dietary restrictions, and personal preferences across conversations.
* **Recipe Discovery**: Searches for real recipes by dish name or main ingredient via TheMealDB API (`search_recipes`).
* **Nutritional Analysis**:
  * Fetches fruit nutritional data via the Fruityvice API (`get_fruit_nutrition_info`).
  * Utilizes an **Agent Sandbox (Code Execution)** to write and run Python code securely to calculate nutrition totals and process data.
* **Media Generation (Cloud Storage)**:
  * Generates high-quality images of dishes using the `gemini-3.1-flash-lite-image` model (`generate_dish_image`).
  * Generates short cinematic videos of dishes using the `gemini-omni-flash-preview` model (`generate_dish_video`).
  * Uploads generated media automatically to a public Cloud Storage bucket.
* **Location Services**:
  * Geocodes addresses using the Google Maps Geocoding API (`geocode_address`).
  * Discovers nearby supermarkets and grocery stores using the Google Maps Places API (`find_nearby_places`).
* **Rich UI (A2UI)**: Returns structured UI responses using Google's A2UI (Agent-to-UI) protocol for rendering rich cards, columns, and embedded images instead of plain text.

*Note: Document grounding/RAG was planned in the project brief but is not yet implemented.*

## Architecture

* **Framework**: Google Agent Development Kit (ADK) / Agent Engine
* **LLM**: Gemini Flash
* **Deployment**: Deployed as an A2A agent to Vertex AI Agent Runtime
* **Frontend**: A custom FastAPI web interface, using the Agent-to-Agent (A2A) protocol to stream responses and natively render A2UI schemas.

## Running Locally

To run the custom frontend UI and connect it to the deployed agent:

1. Open a terminal and navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Export the required environment variables. Replace `<YOUR_RESOURCE_NAME>` with the deployed reasoning engine resource name from your `deployment_metadata.json` file:
   ```bash
   export AGENT_ENGINE_RESOURCE_NAME="<YOUR_RESOURCE_NAME>"
   export AGENT_DIRECTORY="app"
   ```

4. Ensure your Google Cloud application-default credentials are set up so the local proxy can authenticate to Agent Engine:
   ```bash
   gcloud auth application-default login
   ```

5. Start the development server:
   ```bash
   python main.py
   ```

6. Open your browser and navigate to `http://localhost:8080`.
