from flask_login import UserMixin
from datetime import datetime
from .extensions import mongo, login_manager
from bson.objectid import ObjectId

@login_manager.user_loader
def load_user(user_id):
    try:
        user_data = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if user_data:
            return User(user_data)
    except Exception:
        pass  # avoid crashing on bad ObjectId
    return None

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data["_id"])
        self.username = user_data["username"]
        self.email = user_data["email"]
        self.password = user_data["password"]

class Review:
    def __init__(self, recipe_id, user_id, rating, comment):
        self.recipe_id = recipe_id
        self.user_id = user_id
        self.rating = rating
        self.comment = comment
        self.created_at = datetime.utcnow() 