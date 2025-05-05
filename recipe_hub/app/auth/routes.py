from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from ..forms.auth_forms import RegistrationForm, LoginForm
from ..extensions import mongo
from bson.objectid import ObjectId
from ..models import User

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('recipes.home'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = {
            "username": form.username.data,
            "email": form.email.data,
            "password": form.password.data
        }
        mongo.db.users.insert_one(user)
        # Flash with category: required for categorized messages in template
        flash('Your account has been created! You can now log in', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html', title='Register', form=form)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('recipes.home'))

    form = LoginForm()
    if form.validate_on_submit():
        user = mongo.db.users.find_one({"email": form.email.data})
        if user and user['password'] == form.password.data:
            login_user(User(user))
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('recipes.home'))
        else:
            # Flash with category: 'danger' will render a red Bootstrap alert
            flash('Login Unsuccessful. Please check email and password', 'danger')

    return render_template('login.html', title='Login', form=form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('recipes.home'))
