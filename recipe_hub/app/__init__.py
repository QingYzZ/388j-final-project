from flask import Flask, render_template
from .extensions import mongo, login_manager
from .auth.routes import auth
from .recipes.routes import recipes

def custom_404(e):
    return render_template("404.html"), 404

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_pyfile("../config.py", silent=False)
    
    if test_config is not None:
        app.config.update(test_config)
    
    mongo.init_app(app)
    login_manager.init_app(app)
    
    app.register_blueprint(auth)
    app.register_blueprint(recipes)
    
    app.register_error_handler(404, custom_404)
    login_manager.login_view = "auth.login"
    
    return app 