from flask import Flask
from flask import Flask, render_template, request, session, redirect, url_for
from flask import Flask, request, jsonify, send_from_directory
from recipe_manager import RecipeBook
import os
import json
import whisper


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
    print("\n------ REQUEST DETAILS ------")
    print("Full URL:", request.url)
    print("Request Method:", request.method)
    print("Request Headers:\n", request.headers)
    print("Form Data:", request.form)
    print("JSON Payload:", request.get_json())
    print("--------------------------------\n")

    data = request.get_json()
    query = data.get("query", "").lower() if data else ""

    print("query", query)
    recipe = recipeBook.get_best_matching_recipe(query)
    name = recipe["name"]

    if not recipe.name:
        return jsonify({"answer": "I couldn't find that recipe."}), 200
    
    if "ingredient" in query or "ingredients" in query:
        return jsonify({"answer": f"The ingredients for {name} are: {json.dumps(recipe['ingredients'])}"}), 200
    
    if "instructions" in query:
        return jsonify({"answer": f"The instructions for {name} are: {json.dumps(recipe['instructions'])}"}), 200

    for ingredient, quantity in recipe["ingredients"].items():
        if ingredient in query:
            return jsonify({"answer": f"{name} requires {quantity} of {ingredient}."}), 200
    
    if ("how" in query and "long" in query) or "oven" in query:
        if "time" in recipe: 
            return jsonify({"answer": f"To make {name} {recipe['time']}"}), 200
        else:
            return jsonify({"answer": f"I'm not sure how long to cook {name}."}), 200

    return jsonify({"answer": "I didn't understand the question."}), 400