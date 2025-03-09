from flask import Flask
from flask import Flask, render_template, request, session, redirect, url_for
from flask import Flask, request, jsonify, send_from_directory
from recipe_manager import RecipeBook
from dotenv import load_dotenv
import os
import json
import whisper
import openai

load_dotenv()
client = openai.OpenAI(
    project='proj_EFY0XEao2r1dpkGCiYZEQ562',
    api_key=os.getenv("OPENAI_API_KEY")
)

app = Flask(__name__, static_folder="static")
model = whisper.load_model("base")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["SECRET_KEY"] = "recipe-book"
recipeBook = RecipeBook()

@app.route("/")
def serve_ui():
    return render_template("recipes.html")

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

def recipe_to_html(recipe):
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{recipe.name.title()}</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }}
            h2 {{ color: #d35400; }}
            ul, p {{ margin-left: 20px; }}
            strong {{ color: #2c3e50; }}
        </style>
    </head>
    <body>
        <h2>{recipe.name.title()}</h2>
        <h3>Ingredients:</h3>
        <ul>
    """
    for ingredient, quantity in recipe['ingredients'].items():
        html += f"<li><strong>{ingredient}</strong>: {quantity}</li>\n"

    html += """
        </ul>
        <h3>Instructions:</h3>
        <p>
    """

    html += recipe["instructions"]

    html += "</p>"

    if "time" in recipe:
        html += f'<p><strong>Time:</strong> {recipe["time"]}</p>\n'

    html += """
    </body>
    </html>
    """
    return html


@app.route('/v1/recipes', methods=['GET'])
def view_recipes():
    return jsonify({"recipes": recipeBook.get_recipes()})

@app.route('/v1/add_recipe', methods=['POST'])
def add_recipe_api():
    data = request.json
    print("adding recipe", data)

    recipeBook.add_recipe(data["name"], data["ingredients"], data["instructions"], data["time"])
    return jsonify({"message": "Recipe added successfully"}), 200

@app.route("/v1/get_recipe", methods=["GET"])
def get_recipe():
    print("/v1/get_recipe endpoint triggered")
    query = request.headers["Query"]
    recipe_name = recipeBook.get_best_matching_recipe(query)

    recipe = recipeBook.get_recipe(recipe_name)
    if not recipe:
        return jsonify({"answer": "I couldn't find that recipe."})

    return recipe_to_html(recipe)

@app.route("/v1/delete_recipe", methods=["DELETE"])
def delete_recipe_api():
    print("/v1/delete_recipe endpoint triggered")
    query = request.args.get('name')
    recipe = recipeBook.get_best_matching_recipe(query)
    if recipe:
        success = recipeBook.delete_recipe(recipe["name"])
        if not success:
            return jsonify({"answer": "I couldn't find that recipe."})

        return jsonify({"message": "Recipe deleted successfully"}), 200

    return jsonify({"message": "Could not find recipe"})    

@app.route("/v1/get_recipe_info", methods=["POST"])
def get_recipe_info():
    data = request.get_json()
    query = data.get("query", "").lower() if data else ""

    print("query", query)
    recipe = recipeBook.get_best_matching_recipe(query)
    if not recipe:
        return jsonify({"answer": "I couldn't find that recipe."}), 200

    print("Recipe we're working with", recipe)
    response = get_openai_response(query=query, recipe=recipe)
    if response:
        return jsonify({"answer": response}), 200

    # fallback if OpenAI response is unavailable
    recipe = recipeBook.get_best_matching_recipe(query)
    name = recipe["name"]

    # what ingredients are in <recipe-name>? tell me the ingredients of <recipe-name>.
    if "ingredient" in query or "ingredients" in query:
        return jsonify({"answer": f"The ingredients for {name} are: {json.dumps(recipe['ingredients'])}"}), 200

    # what instructions are in <recipe-name>? tell me the instructions of <recipe-name>.
    if "instructions" in query:
        return jsonify({"answer": f"The instructions for {name} are: {json.dumps(recipe['instructions'])}"}), 200

    # how much <ingredient> should I add to <recipe-name>?
    if "how much" in query or "how many" in query:
        for ingredient, quantity in recipe["ingredients"].items():
            if ingredient in query:
                return jsonify({"answer": f"{name} requires {quantity} of {ingredient}."}), 200

    # how long should I put the <recipe-name> in the oven? what should I preheat oven to?
    if "how long" in query or "oven" in query or "time" in query:
        if "time" in recipe: 
            return jsonify({"answer": f"To make {name} {recipe['time']}"}), 200
        else:
            return jsonify({"answer": f"I'm not sure how long to cook {name}."}), 200

    return jsonify({"answer": "I didn't understand the question."}), 400

def get_openai_response(query, recipe):
    recipe_name = recipe.get("name", "")
    ingredients = "\n".join([f"{ingredient}: {quantity}" for ingredient, quantity in recipe.get("ingredients", {}).items()])
    instructions = "\n".join(recipe.get("instructions", []))
    time = recipe.get("time", "unknown cooking time")

    prompt = f"""
    You are a cooking assistant. Below is the recipe for {recipe_name}:
    
    Ingredients:
    {ingredients}
    
    Instructions:
    {instructions}
    
    Cooking Time: {time}
    
    User Query: {query}
    
    Based on the above recipe, provide a helpful response to the user's query.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=[{
                "role": "user", 
                "content": prompt
            }]
        )
        completion = response.parse()
        print(completion)

        return completion

    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None
