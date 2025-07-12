from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from .models import db, User, Question, Answer, Notification, Vote
import os
from flask import jsonify

main = Blueprint('main', __name__)


@main.route('/')
def root():
    return redirect(url_for('main.login'))


@main.route('/home')
@login_required
def home():
    questions = Question.query.order_by(Question.created_at.desc()).all()

    # Unread notification count and recent notifications
    unread_count = len([n for n in current_user.notifications if not n.is_read])
    recent_notifications = sorted(current_user.notifications, key=lambda n: n.timestamp, reverse=True)[:10]

    return render_template('home.html',
                           questions=questions,
                           unread_count=unread_count,
                           notifications=recent_notifications)


@main.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        new_name = request.form.get('name')
        new_pic = request.files.get('profile_pic')

        if new_name:
            current_user.username = new_name

        if new_pic:
            filename = secure_filename(new_pic.filename)
            path = os.path.join(current_app.static_folder, 'profile_pics', filename)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            new_pic.save(path)
            current_user.profile_pic = f'/static/profile_pics/{filename}'

        db.session.commit()
        flash("Profile updated successfully!")
        return redirect(url_for('main.profile'))

    user_questions = Question.query.filter_by(user_id=current_user.id).all()
    user_answers = Answer.query.filter_by(user_id=current_user.id).all()
    return render_template('profile.html', questions=user_questions, answers=user_answers)


@main.route('/question/<int:id>', methods=['GET', 'POST'])
def view_question(id):
    question = Question.query.get_or_404(id)

    # Increment views
    question.views = (question.views or 0) + 1
    db.session.commit()

    # Handle new answer submission
    if request.method == 'POST':
        if not current_user.is_authenticated:
            flash("You must be logged in to post an answer.")
            return redirect(url_for('main.login'))

        content = request.form.get('answer')
        if not content:
            flash("Answer cannot be empty.")
            return redirect(url_for('main.view_question', id=id))

        answer = Answer(content=content, user_id=current_user.id, question_id=id)
        db.session.add(answer)

        if question.user_id != current_user.id:
            notification = Notification(
                recipient_id=question.user_id,
                message=f"{current_user.username} answered your question: '{question.title}'"
            )
            db.session.add(notification)

        db.session.commit()
        return redirect(url_for('main.view_question', id=id))

    return render_template('question.html', question=question)


@main.route('/upvote/<int:question_id>', methods=['POST'])
@login_required
def upvote_question(question_id):
    question = Question.query.get_or_404(question_id)

    if current_user in question.voters:
        return jsonify({'error': 'Already upvoted'}), 400

    question.voters.append(current_user)
    question.likes += 1
    db.session.commit()
    return jsonify({'likes': question.likes})


@main.route('/ask', methods=['GET', 'POST'])
@login_required
def ask():
    if request.method == 'POST':
        title = request.form.get('title')
        body = request.form.get('body')
        tags = request.form.get('tags')
        image = request.files.get('image')

        image_url = None
        if image:
            filename = secure_filename(image.filename)
            filepath = os.path.join(current_app.static_folder, 'uploads', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            image.save(filepath)
            image_url = f'/static/uploads/{filename}'

        q = Question(title=title, body=body, user_id=current_user.id, tags=tags, image=image_url)
        db.session.add(q)
        db.session.commit()

        return redirect(url_for('main.success'))

    return render_template('ask-question.html')


@main.route('/success')
def success():
    return render_template('success.html')


@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        username = request.form.get('username')  # Full email
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('main.home'))

        flash("Invalid credentials")

    return render_template('login.html')


@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('username')
        password = generate_password_hash(request.form.get('password'))

        if User.query.filter_by(username=email).first():
            flash("User already exists")
        else:
            user = User(username=email, password=password)
            db.session.add(user)
            db.session.commit()
            return redirect(url_for('main.login'))

    return render_template('register.html')


@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))
