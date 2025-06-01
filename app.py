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
        note = request.form.get('note', '')

        exercise_ids = request.form.getlist('exercise_id')
        weights = request.form.getlist('weight_kg')
        reps = request.form.getlist('reps')
        set_notes = request.form.getlist('set_note')

        if not date:
            flash("Выберите дату тренировки")
            return redirect(url_for('createtraining'))

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO workouts (user_id, date, note)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (user_id, date, note))
                workout_id = cur.fetchone()[0]

                for i in range(len(exercise_ids)):
                    eid = exercise_ids[i]
                    weight = weights[i] or None
                    rep = reps[i] or None
                    set_note = set_notes[i] or ''

                    if eid and rep:
                        cur.execute("""
                            INSERT INTO sets (workout_id, exercise_id, weight_kg, reps, note)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (workout_id, eid, weight, rep, set_note))

                conn.commit()

        # 👇 Исправленный переход
        session['workout_id'] = workout_id
        return redirect(url_for('activetraining'))

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT id, name FROM exercises ORDER BY name")
            exercises_list = cur.fetchall()

    return render_template('createtraining.html', exercises=exercises_list)


@app.route('/active_training/<int:workout_id>', methods=['GET'])
def active_training(workout_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # Получение тренировки
            cur.execute("SELECT * FROM workouts WHERE id = %s AND user_id = %s", (workout_id, user_id))
            workout = cur.fetchone()

            if not workout:
                flash("Тренировка не найдена.")
                return redirect(url_for('menu'))

            # Установка времени начала при первом входе
            if not workout['start_time']:
                now = datetime.now()
                cur.execute("UPDATE workouts SET start_time = %s WHERE id = %s", (now, workout_id))
                conn.commit()
                workout['start_time'] = now

            # Получение всех подходов
            cur.execute("""
                SELECT s.id, s.exercise_id, e.name AS exercise_name, s.weight_kg, s.reps, s.note
                FROM sets s
                LEFT JOIN exercises e ON s.exercise_id = e.id
                WHERE s.workout_id = %s
                ORDER BY s.id
            """, (workout_id,))
            sets = cur.fetchall()

            # Получение всех упражнений
            cur.execute("SELECT id, name FROM exercises ORDER BY name")
            exercises = cur.fetchall()

    return render_template(
        'active_training.html',
        workout=workout,
        sets=sets,
        exercises=exercises
    )


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
