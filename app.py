# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime
import psycopg2
import os
from dotenv import load_dotenv
from psycopg2.extras import DictCursor

load_dotenv()

# Конфиг базы данных
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT', 5433))  # по умолчанию 5432
}

app = Flask(__name__)
app.secret_key = 'fallback-secret-key'  # Для тестирования

def get_db_connection():
    """Создаёт новое соединение с БД"""
    conn = psycopg2.connect(**DB_CONFIG)
    return conn

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')

        if not username:
            flash("Введите имя пользователя")
            return redirect(url_for('login'))

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                # Ищем пользователя в БД
                cur.execute("SELECT * FROM users WHERE username = %s", (username,))
                user = cur.fetchone()

                if not user:
                    flash("Пользователь не найден. Обратитесь к администратору.")
                    return redirect(url_for('login'))

                # Сохраняем в сессию
                session['user_id'] = user['id']
                session['username'] = user['username']

        return redirect(url_for('menu'))

    return render_template('login.html')

@app.route('/menu')
def menu():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('menu.html')

@app.route('/exercises', methods=['GET', 'POST'])
def exercises():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            name = request.form.get('name')
            description = request.form.get('description', '')
            if name:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "INSERT INTO exercises (name, description) VALUES (%s, %s)",
                            (name, description)
                        )
                        conn.commit()
                flash("Упражнение добавлено")
            else:
                flash("Название упражнения обязательно")

        elif action == 'delete':
            exercise_id = request.form.get('exercise_id')
            if exercise_id:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM exercises WHERE id = %s", (exercise_id,))
                        conn.commit()
                flash("Упражнение удалено")

        return redirect(url_for('exercises'))

    # GET: отображаем список упражнений
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT * FROM exercises ORDER BY name")
            exercises_list = cur.fetchall()

    return render_template('exercises.html', exercises=exercises_list)


@app.route('/createtraining', methods=['GET', 'POST'])
def createtraining():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_id = session['user_id']
        date = request.form.get('date')
        title = request.form.get('title')  # <-- новое поле
        note = request.form.get('note', '')
        intensity = request.form.get('intensity') or None

        if not date or not title:
            flash("Укажите дату и название тренировки")
            return redirect(url_for('createtraining'))

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO workouts (user_id, date, title, note, intensity, start_time)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    RETURNING id
                """, (user_id, date, title, note, intensity))
                workout_id = cur.fetchone()[0]

                conn.commit()

        session['workout_id'] = workout_id
        return redirect(url_for('active_training', workout_id=workout_id))

    return render_template('createtraining.html')


@app.route('/activetraining/<int:workout_id>', methods=['GET', 'POST'])
def active_training(workout_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)

    cur.execute("SELECT * FROM workouts WHERE id = %s", (workout_id,))
    workout = cur.fetchone()
    if not workout:
        flash("Тренировка не найдена")
        return redirect(url_for('menu'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add_exercise':
            ex_id = request.form.get('exercise_id')
            sets_count = int(request.form.get('sets_count'))
            for _ in range(sets_count):
                cur.execute("""
                    INSERT INTO sets (workout_id, exercise_id)
                    VALUES (%s, %s)
                """, (workout_id, ex_id))
            conn.commit()

        elif action.startswith('save_exercise_'):
            ex_id = action.split('_')[-1]
            cur.execute("""
                SELECT id FROM sets
                WHERE workout_id = %s AND exercise_id = %s
                ORDER BY id
            """, (workout_id, ex_id))
            sets = cur.fetchall()
            for s in sets:
                weight = request.form.get(f'weight_{s["id"]}') or None
                reps = request.form.get(f'reps_{s["id"]}') or None
                cur.execute("""
                    UPDATE sets SET weight_kg = %s, reps = %s
                    WHERE id = %s
                """, (weight, reps, s["id"]))
            conn.commit()

        elif action.startswith('remove_exercise_'):
            ex_id = action.split('_')[-1]
            cur.execute("DELETE FROM sets WHERE workout_id = %s AND exercise_id = %s", (workout_id, ex_id))
            conn.commit()

        elif action == 'finish':
            now = datetime.now()
            duration = (now - workout['start_time']).seconds // 60
            cur.execute("""
                UPDATE workouts SET duration_minutes = %s WHERE id = %s
            """, (duration, workout_id))
            conn.commit()
            conn.close()
            return redirect(url_for('menu'))

    # Получаем список упражнений
    cur.execute("SELECT id, name FROM exercises ORDER BY name")
    exercises = cur.fetchall()

    # Получаем подходы
    cur.execute("""
        SELECT sets.*, exercises.name
        FROM sets JOIN exercises ON sets.exercise_id = exercises.id
        WHERE workout_id = %s ORDER BY exercise_id, sets.id
    """, (workout_id,))
    sets = cur.fetchall()

    # Группировка по exercise_id
    grouped_sets = {}
    for s in sets:
        grouped_sets.setdefault(s['exercise_id'], []).append(s)

    conn.close()
    return render_template('active_training.html',
                           workout=workout,
                           exercises=exercises,
                           grouped_sets=grouped_sets)



@app.route('/stats', methods=['GET', 'POST'])
def stats():
    if 'username' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    exercise_id = None
    selected_workout_id = None
    tonnage_data = None
    progress_data = None
    exercises_list = []
    workouts_list = []

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT id, name FROM exercises ORDER BY name")
            exercises_list = cur.fetchall()

            cur.execute("SELECT id, date, note FROM workouts WHERE user_id = %s ORDER BY date DESC", (user_id,))
            workouts_list = cur.fetchall()

            if request.method == 'POST':
                exercise_id = request.form.get('exercise_id')
                period = request.form.get('period')
                selected_workout_id = request.form.get('workout_id')

                if not exercise_id:
                    flash("Выберите упражнение")
                else:
                    if selected_workout_id:
                        cur.execute("""
                            SELECT w.date, e.name AS exercise_name,
                                   SUM(s.weight_kg * s.reps) AS total_tonnage
                            FROM sets s
                            JOIN workouts w ON s.workout_id = w.id
                            JOIN exercises e ON s.exercise_id = e.id
                            WHERE s.exercise_id = %s AND s.workout_id = %s
                            GROUP BY w.date, e.name
                        """, (exercise_id, selected_workout_id))
                        tonnage_data = cur.fetchone()

                    query = """
                        SELECT w.date, s.weight_kg, s.reps
                        FROM sets s
                        JOIN workouts w ON s.workout_id = w.id
                        WHERE s.exercise_id = %s AND w.user_id = %s
                    """

                    if period == 'week':
                        query += " AND w.date >= CURRENT_DATE - INTERVAL '7 days'"
                    elif period == 'month':
                        query += " AND w.date >= CURRENT_DATE - INTERVAL '30 days'"
                    elif period == 'all':
                        pass

                    query += " ORDER BY w.date DESC"

                    cur.execute(query, (exercise_id, user_id))
                    progress_data = cur.fetchall()

    return render_template(
        'stats.html',
        exercises=exercises_list,
        workouts=workouts_list,
        selected_exercise=exercise_id,
        selected_workout=selected_workout_id,
        tonnage=tonnage_data,
        progress=progress_data
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
