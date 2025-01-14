import json
from flask import jsonify, render_template, request, redirect, url_for
from flask_login import login_user, logout_user, current_user, login_required
from models import User, Message
from movies import where_to_watch, where_to_watch_movie, get_movie_or_show_trailer, get_current_movies_in_theatres


tools = [
    {
        'type': 'function',
        'function': {
            "name": "where_to_watch",
            "description": "Returns a list of platforms where a specified tv show can be watched. don't use for movies",
            "parameters": {
                "type": "object",
                "required": [
                    "tv_show_name"
                ],
                "properties": {
                    "tv_show_name": {
                        "type": "string",
                        "description": "The name of the tv show to search for"
                    }
                },
                "additionalProperties": False
            }
        },
    },
    {
        'type': 'function',
        'function': {
            "name": "where_to_watch_movie",
            "description": "Returns information about a specified movie. don't use for tv shows",
            "parameters": {
                "type": "object",
                "required": [
                    "movie_name"
                ],
                "properties": {
                    "movie_name": {
                        "type": "string",
                        "movie_name": "The name of the movie show to search for"
                    }
                },
                "additionalProperties": False
            }
        },
    },
    {
        'type': 'function',
        'function': {
            "name": "get_movie_or_show_trailer",
            "description": "Returns a youtube link to the trailer of a specified movie or tv show",
            "parameters": {
                "type": "object",
                "required": [
                    "movie_or_show_name"
                ],
                "properties": {
                    "movie_or_show_name": {
                        "type": "string",
                        "movie_or_show_name": "The name of the movie show or tv show to search for"
                    }
                },
                "additionalProperties": False
            }
        },
    },
    {
        'type': 'function',
        'function': {
            "name": "get_current_movies_in_theatres",
            "description": "Get a list of movies that are currently in theatres."
        },
    }
]


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
                content="Hola! Soy plaIA, un recomendador de películas. ¿En qué te puedo ayudar?", author="assistant", user=user)

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

                if user and bcrypt.check_password_hash(user.password, password):
                    login_user(user)

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

        intents = {
            'Recomienda algo al azar': 'Recomiéndame una película al azar',
            'Recomieda series de acción': 'Recomiéndame series de acción',
            'Recomieda películas de suspenso': 'Recomiéndame una película de suspenso',
            'Enviar': request.form.get('message')
        }

        if intent in intents:
            user_message = intents[intent]
            db.session.add(Message(content=user_message,
                           author="user", user=user))
            db.session.commit()

            messages_for_llm = [{
                "role": "system",
                "content": f"Eres un chatbot que recomienda películas, te llamas 'PlaIA'. Tu rol es responder recomendaciones de manera breve y concisa. No repitas recomendaciones. usa el genéro del usuario {user.gender}  y su  fecha de nacimiento {user.birthdate} para recomendar películas. ",
            }]

            for message in user.messages:
                messages_for_llm.append({
                    "role": message.author,
                    "content": message.content,
                })

            chat_completion = open_ia.chat.completions.create(
                messages=messages_for_llm,
                model="gpt-4o",
                temperature=1,
                tools=tools
            )

            if chat_completion.choices[0].message.tool_calls:
                tool_call = chat_completion.choices[0].message.tool_calls[0]
                if tool_call.function.name == 'where_to_watch':
                    arguments = json.loads(tool_call.function.arguments)
                    name = arguments['tv_show_name']
                    model_recommendation = where_to_watch(name)
                elif tool_call.function.name == 'where_to_watch_movie':
                    arguments = json.loads(
                        tool_call.function.arguments)
                    name = arguments['movie_name']
                    model_recommendation = where_to_watch_movie(name)
                elif tool_call.function.name == 'get_movie_or_show_trailer':
                    arguments = json.loads(
                        tool_call.function.arguments)
                    name = arguments['movie_or_show_name']
                    model_recommendation = get_movie_or_show_trailer(
                        name)
                elif tool_call.function.name == 'get_current_movies_in_theatres':
                    model_recommendation = get_current_movies_in_theatres()
                else:
                    model_recommendation = "No estoy seguro de dónde puedes ver esta película o serie :("
            else:
                model_recommendation = chat_completion.choices[0].message.content

            db.session.add(Message(content=model_recommendation,
                                   author="assistant", user=user))
            db.session.commit()

            return render_template('chat.html', messages=user.messages, username=user.username)

    @app.route('/profile')
    @login_required
    def profile():
        if current_user.is_authenticated:
            return render_template('edit_user.html')
        return redirect(url_for('login'))

    @app.route('/logout', methods=['GET'])
    def logout():
        logout_user()
        return redirect(url_for('login'))

    @app.route('/user_data', methods=['GET'])
    @login_required
    def user_data():
        print(f'Current user: {current_user}')
        data = {
            "username": current_user.username,
            "email": current_user.email,
            "birthdate": current_user.birthdate,
            "gender": current_user.gender
        }
        return jsonify(data)

    @app.route('/update_birthdate_age', methods=['POST'])
    @login_required
    def update_birthdate_age():
        new_birthdate = request.form.get('birthdate')
        new_gender = request.form.get('gender')
        current_user.birthdate = new_birthdate
        current_user.gender = new_gender
        db.session.commit()
        return render_template('edit_user.html', success=True)
