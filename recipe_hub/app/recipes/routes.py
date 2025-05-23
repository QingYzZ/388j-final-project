from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from ..forms.recipe_forms import RecipeForm, CommentForm
from ..extensions import mongo
from bson.objectid import ObjectId
import requests
from datetime import datetime
import os
from werkzeug.utils import secure_filename

recipes = Blueprint('recipes', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'jpg', 'jpeg', 'png'}

@recipes.route('/')
def home():
    response = requests.get('https://www.themealdb.com/api/json/v1/1/random.php')
    random_recipe = response.json()['meals'][0] if response.status_code == 200 else None
    return render_template('recipes.html', recipe=random_recipe)

@recipes.route('/add_recipe', methods=['GET', 'POST'])
@login_required
def add_recipe():
    form = RecipeForm()
    if form.validate_on_submit():
        # Handle image upload
        image_url = None
        if form.image.data:
            image = form.image.data
            if allowed_file(image.filename):
                filename = secure_filename(image.filename)
                # Save the file to a folder
                image_path = os.path.join(current_app.root_path, 'static', 'recipe_images', filename)
                image.save(image_path)
                image_url = f'/static/recipe_images/{filename}'
        
        # Parse ingredients
        ingredients_list = []
        for line in form.ingredients.data.split('\n'):
            if line.strip():
                parts = line.split('-', 1)
                if len(parts) == 2:
                    measure, ingredient = parts
                    ingredients_list.append({
                        'measure': measure.strip(),
                        'ingredient': ingredient.strip()
                    })
        
        # Create recipe document
        recipe = {
            'title': form.title.data,
            'category': form.category.data,
            'area': form.area.data,
            'ingredients': ingredients_list,
            'instructions': form.instructions.data,
            'image_url': image_url,
            'user_id': str(current_user.id),
            'username': current_user.username,
            'created_at': datetime.utcnow()
        }
        
        # Save to database
        result = mongo.db.recipes.insert_one(recipe)
        recipe['_id'] = result.inserted_id
        flash('Your recipe has been added!', 'success')
        return redirect(url_for('recipes.recipe_detail', recipe_id=str(recipe['_id'])))
    
    return render_template('add_recipe.html', title='Add Recipe', form=form)

@recipes.route('/recipe/<recipe_id>')
def recipe_detail(recipe_id):
    recipe = None
    source = 'api'

    # Attempt to fetch recipe from TheMealDB API
    try:
        response = requests.get(f'https://www.themealdb.com/api/json/v1/1/lookup.php?i={recipe_id}')
        if response.status_code == 200:
            meals = response.json().get('meals')
            if isinstance(meals, list) and meals:
                meal = meals[0]
                recipe = {
                    'id': meal.get('idMeal'),
                    'name': meal.get('strMeal'),
                    'category': meal.get('strCategory'),
                    'area': meal.get('strArea'),
                    'instructions': meal.get('strInstructions'),
                    'image': meal.get('strMealThumb'),
                    'ingredients': [
                        {
                            'ingredient': meal.get(f'strIngredient{i}'),
                            'measure': meal.get(f'strMeasure{i}')
                        }
                        for i in range(1, 21)
                        if meal.get(f'strIngredient{i}') and meal.get(f'strIngredient{i}').strip()
                    ]
                }
            else:
                raise ValueError("No valid API result")
    except Exception:
        # If API call fails or recipe not found, check local DB
        try:
            db_recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})
            if db_recipe:
                recipe = {
                    'id': str(db_recipe['_id']),
                    'name': db_recipe['title'],
                    'category': db_recipe['category'],
                    'area': db_recipe['area'],
                    'instructions': db_recipe['instructions'],
                    'image': db_recipe.get('image_url', ''),
                    'ingredients': db_recipe.get('ingredients', [])
                }
                source = 'local'
        except Exception:
            pass  # ObjectId conversion or DB lookup failed

    if recipe:
        reviews = list(mongo.db.reviews.find({"recipe_id": recipe_id}))
        form = CommentForm()
        return render_template('recipe_detail.html', recipe=recipe, reviews=reviews, form=form, source=source)

    flash("Recipe not found.", "danger")
    return redirect(url_for('recipes.home'))

@recipes.route('/recipe/<recipe_id>/review', methods=['POST'])
@login_required
def add_review(recipe_id):
    form = CommentForm()
    if form.validate_on_submit():
        review = {
            "recipe_id": recipe_id,
            "user_id": str(current_user.id),
            "username": current_user.username,
            "rating": form.rating.data,
            "comment": form.comment.data,
            "created_at": datetime.utcnow()
        }
        mongo.db.reviews.insert_one(review)
        flash('Your review has been added!', 'success')
    return redirect(url_for('recipes.recipe_detail', recipe_id=recipe_id))

@recipes.route('/search')
def search():
    query = request.args.get('q', '')
    if query:
        # Search in TheMealDB
        response = requests.get(f'https://www.themealdb.com/api/json/v1/1/search.php?s={query}')
        api_recipes = response.json()['meals'] if response.status_code == 200 else []
        
        # Search in our database
        db_recipes = list(mongo.db.recipes.find({"title": {"$regex": query, "$options": "i"}}))
        
        # Combine and format results
        recipes = api_recipes if api_recipes else []
        for recipe in db_recipes:
            formatted_recipe = {
                'idMeal': str(recipe['_id']),
                'strMeal': recipe['title'],
                'strCategory': recipe['category'],
                'strArea': recipe['area'],
                'strMealThumb': recipe.get('image_url', '')
            }
            recipes.append(formatted_recipe)
        
        return render_template('recipes.html', recipes=recipes, query=query)
    return redirect(url_for('recipes.home'))

@recipes.route('/category/<category>')
def by_category(category):
    response = requests.get(f'https://www.themealdb.com/api/json/v1/1/filter.php?c={category}')
    recipes = response.json()['meals'] if response.status_code == 200 else []
    return render_template('recipes.html', recipes=recipes, category=category) 