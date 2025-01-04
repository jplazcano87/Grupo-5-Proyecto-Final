from flask import render_template, request, redirect, url_for
from flask_login import login_user, logout_user, current_user, login_required
from models import User, Message


def register_routes(app, db, bcrypt, open_ia):

    @app.route('/')
    def index():
        return render_template('login.html')

    @app.route('/signup', methods=['GET', 'POST'])
    def signup():
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            repeat_password = request.form.get('repeat_password')
            if password != repeat_password:
                return 'Passwords do not match'

            birthdate = request.form.get('birthdate')

            gender = request.form.get('gender')

            user = User(username=username, email=email, password=bcrypt.generate_password_hash(
                password).decode('utf-8'), birthdate=birthdate, gender=gender)

            message = Message(
                content="Hola! Soy Muby, un recomendador de películas. ¿En qué te puedo ayudar?", author="assistant", user=user)

            db.session.add(user)
            db.session.add(message)
            db.session.commit()

            return redirect(url_for('login'))
        elif request.method == 'GET':
            return render_template('sign_up.html')

        return 'Invalid request method'

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            if request.is_json:
                data = request.get_json()
                email = data.get('email')
                password = data.get('password')

            user = db.session.query(User).filter_by(email=email).first()
            print(f'User: {user}, password: {password}')
            if user and bcrypt.check_password_hash(user.password, password):
                login_user(user)
                print(f'User logged ok: {user}')
                return redirect(url_for('chat'))

            return 'Invalid credentials', 401

        return render_template('login.html')

    @app.route('/chat', methods=['GET', 'POST'])
    @login_required
    def chat():
        if not current_user.is_authenticated:
            return redirect(url_for('login'))

        email = current_user.email
        user = db.session.query(User).filter_by(email=email).first()

        if request.method == 'GET':
            return render_template('chat.html', messages=user.messages,  username=user.username)

        intent = request.form.get('intent')
        intent_random = request.form.get('intent_random')

        intents = {
            'Recomienda algo al azar': 'Recomiéndame una película al azar',
            'Recomieda series de acción': 'Recomiéndame series de acción',
            'Recomieda películas de suspenso': 'Recomiéndame una película de suspenso',
            'Comedia': 'Recomiéndame una película de comedia',
            'Enviar': request.form.get('message')
        }

        if intent in intents:
            user_message = intents[intent]

            # Guardar nuevo mensaje en la BD
            db.session.add(Message(content=user_message,
                           author="user", user=user))
            db.session.commit()

            messages_for_llm = [{
                "role": "system",
                "content": "Eres un chatbot que recomienda películas, te llamas 'Next Moby'. Tu rol es responder recomendaciones de manera breve y concisa. No repitas recomendaciones.",
            }]

            for message in user.messages:
                messages_for_llm.append({
                    "role": message.author,
                    "content": message.content,
                })

            chat_completion = open_ia.chat.completions.create(
                messages=messages_for_llm,
                model="gpt-4o",
                temperature=1
            )

            model_recommendation = chat_completion.choices[0].message.content
            db.session.add(Message(content=model_recommendation,
                                   author="assistant", user=user))
            db.session.commit()

            return render_template('chat.html', messages=user.messages, username=user.username)

    @app.route('/user/<username>')
    def user(username):
        favorite_movies = [
            'The Shawshank Redemption',
            'The Godfather',
            'The Dark Knight',
        ]
        return render_template('user.html', username=username, favorite_movies=favorite_movies)

    @app.post('/recommend')
    def recommend():
        user = db.session.query(User).first()
        data = request.get_json()
        user_message = data['message']
        new_message = Message(content=user_message, author="user", user=user)
        db.session.add(new_message)
        db.session.commit()

        messages_for_llm = [{
            "role": "system",
            "content": "Eres un chatbot que recomienda películas, te llamas 'Next Moby'. Tu rol es responder recomendaciones de manera breve y concisa. No repitas recomendaciones.",
        }]

        for message in user.messages:
            messages_for_llm.append({
                "role": message.author,
                "content": message.content,
            })

        chat_completion = client.chat.completions.create(
            messages=messages_for_llm,
            model="gpt-4o",
        )

        message = chat_completion.choices[0].message.content

        return {
            'recommendation': message,
            'tokens': chat_completion.usage.total_tokens,
        }

    @app.route('/profile')
    @login_required
    def profile():
        if current_user.is_authenticated:
            return render_template('profile.html')
        return redirect(url_for('login'))

    @app.route('/logout', methods=['GET'])
    def logout():
        logout_user()
        return redirect(url_for('login'))
