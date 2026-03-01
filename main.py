from flask import Flask, request, jsonify, render_template
import requests
import os
import random
import time
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"


# -------------------- HOME --------------------
@app.route("/")
def home():
    return render_template("index.html")


# -------------------- GET FREE MODELS --------------------
@app.route("/models", methods=["GET"])
def get_models():
    try:
        response = requests.get(
            f"{BASE_URL}/models",
            headers={"Authorization": f"Bearer {API_KEY}"}
        )

        if response.status_code != 200:
            return jsonify([])

        models = response.json().get("data", [])
        free_models = [m["id"] for m in models if ":free" in m["id"]]

        return jsonify(free_models)

    except:
        return jsonify([])


# -------------------- CHAT --------------------
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    selected_model = data.get("model")
    message = data.get("message")

    if not message:
        return jsonify({"reply": "Message cannot be empty."})

    # Fetch free models dynamically
    try:
        models_response = requests.get(
            f"{BASE_URL}/models",
            headers={"Authorization": f"Bearer {API_KEY}"}
        )

        models_data = models_response.json().get("data", [])
        free_models = [m["id"] for m in models_data if ":free" in m["id"]]

    except:
        return jsonify({"reply": "Failed to fetch models."})

    if not free_models:
        return jsonify({"reply": "No free models available."})

    # Prioritize selected model
    if selected_model in free_models:
        free_models.remove(selected_model)
        free_models.insert(0, selected_model)

    # Shuffle remaining models
    first = free_models[0]
    rest = free_models[1:]
    random.shuffle(rest)
    models_to_try = [first] + rest

    # System prompt for structured output
    system_prompt = """
You are an intelligent assistant.

Follow these rules:

1. If the user asks about a technical term, concept, abbreviation, or definition:
   → Respond in structured format.

2. If the user sends a greeting (hi, hello, hey, etc.):
   → Respond normally in a friendly conversational way.

3. If the user asks a normal question:
   → Answer clearly but do NOT force the structured template.

Structured format (ONLY when explaining a term):

You likely meant **<term>**, which stands for **<full form if applicable>**.

Here's a clear explanation:

### What is <term>?
<definition>

### Key Characteristics:
1. <point>
2. <point>
3. <point>

### Examples:
- <example>
- <example>

### How It Works:
<explanation>

### Limitations:
- <limitation>
- <limitation>
"""

    # Try models one by one
    for model in models_to_try:
        try:
            start = time.time()

            response = requests.post(
                f"{BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message}
                    ],
                    "temperature": 0.3
                },
                timeout=12
            )

            if response.status_code == 200:
                result = response.json()
                reply = result["choices"][0]["message"]["content"]
                response_time = round(time.time() - start, 2)

                return jsonify({
                    "reply": reply,
                    "model_used": model,
                    "response_time": response_time
                })

        except Exception as e:
            print(f"❌ {model} failed:", e)
            continue

    return jsonify({
        "reply": "⚠️ All free models are busy right now. Try again.",
        "model_used": None
    })


if __name__ == "__main__":
    app.run(debug=True)