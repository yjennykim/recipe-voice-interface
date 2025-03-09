import json
import os
from rapidfuzz.process import extractOne

RECIPES_FILE = "recipes.json"
BACKUP_FILE = "recipes_backup.json"

class RecipeBook(object):
    def __init__(self):
        self.recipes = self.load_recipes()

    def get_recipes(self):
        return self.recipes
        
    def load_recipes(self):
        """Load recipes from JSON file, creating it if necessary."""
        if not os.path.exists(RECIPES_FILE):
            self.save_recipes({})
        with open(RECIPES_FILE, "r") as file:
            return json.load(file)

    def save_recipes(self, recipes):
        """Save recipes to file with backup."""
        try:
            # Create a backup before overwriting
            if os.path.exists(RECIPES_FILE):
                os.replace(RECIPES_FILE, BACKUP_FILE)
            # Save the new recipes
            with open(RECIPES_FILE, "w") as file:
                json.dump(recipes, file, indent=4)
        except Exception as e:
            print(f"Error saving recipes: {e}")

    def add_recipe(self, name, ingredients, instructions, time):
        """Add a new recipe and save it."""
        self.recipes[name] = {
            "name": name,
            "ingredients": ingredients,
            "instructions": instructions,
            "time": time
        }
        self.save_recipes(self.recipes)

    def delete_recipe(self, name):
        """Delete a recipe and save it."""
        if name in self.recipes:
            print("Deleting recipe")
            del self.recipes[name]
        self.save_recipes(self.recipes)

    def get_best_matching_recipe(self, query):
        best_match = extractOne(query, self.recipes.keys(), score_cutoff=60) 
        print("Best matches", best_match)
        
        if best_match:
            return self.recipes[best_match[0]] # recipe with the highest similarity score
        return None

    def get_recipe(self, recipe_name):
        if recipe_name not in self.recipes:
            return None

        recipe = self.recipes[recipe_name]
        return recipe