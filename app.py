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
        title = request.form.get('title')
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
    print("Request method:", request.method)
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:

            # Получаем тренировку
            cur.execute("SELECT * FROM workouts WHERE id = %s", (workout_id,))
            workout = cur.fetchone()
            if not workout:
                flash("Тренировка не найдена")
                return redirect(url_for('menu'))

            # Обработка POST-запроса
            if request.method == 'POST':
                action = request.form.get('action')

                # Добавление упражнения
                if action == 'add_exercise':
                    ex_id = request.form.get('exercise_id')
                    sets_count = 3
                    if ex_id and sets_count > 0:
                        cur.execute("""
                            SELECT COALESCE(MAX(order_num), 0) FROM sets WHERE workout_id = %s
                        """, (workout_id,))
                        max_order = cur.fetchone()[0]
                        for _ in range(sets_count):
                            cur.execute("""
                                INSERT INTO sets (workout_id, exercise_id, order_num)
                                VALUES (%s, %s, %s)
                            """, (workout_id, ex_id, max_order + 1))
                        conn.commit()
                        return redirect(url_for('active_training', workout_id=workout_id))

                # Добавление подхода
                elif action.startswith('add_set_'):
                    try:
                        # Проверяем, что после add_set_ следует число
                        parts = action.split('_')
                        if len(parts) < 3 or not parts[2].isdigit():
                            raise ValueError("Неверный формат команды")

                        ex_id = int(parts[2])

                        cur.execute("SELECT COALESCE(MAX(order_num), 0) FROM sets WHERE workout_id = %s", (workout_id,))
                        max_order = cur.fetchone()[0]
                        cur.execute("""
                            INSERT INTO sets (workout_id, exercise_id, order_num)
                            VALUES (%s, %s, %s)
                        """, (workout_id, ex_id, max_order + 1))
                        conn.commit()
                        return redirect(url_for('active_training', workout_id=workout_id))
                    except Exception as e:
                        print("Ошибка при добавлении подхода:", str(e))
                        flash("Не удалось добавить подход")
                        conn.rollback()
                        return redirect(url_for('active_training', workout_id=workout_id))
                        
                # Удаление одного подхода по set_id
                elif action.startswith('delete_set_'):
                    try:
                        set_id = int(action.split('_')[2])  # delete_set_123 → 123
                        cur.execute("DELETE FROM sets WHERE id = %s AND workout_id = %s",
                                    (set_id, workout_id))
                        conn.commit()
                        return redirect(url_for('active_training', workout_id=workout_id))
                    except (ValueError, IndexError):
                        flash("Неверный формат запроса на удаление подхода")
                        
                # Сохранение данных подходов для одного упражнения
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
                    return redirect(url_for('active_training', workout_id=workout_id))

                # Удаление всех подходов по упражнению
                elif action.startswith('remove_exercise_'):
                    ex_id = action.split('_')[-1]
                    cur.execute("DELETE FROM sets WHERE workout_id = %s AND exercise_id = %s",
                                (workout_id, ex_id))
                    conn.commit()
                    return redirect(url_for('active_training', workout_id=workout_id))
                
                # Завершение тренировки
                elif action == 'finish':
                    now = datetime.now()
                    duration = max(0, (now - workout['start_time']).total_seconds() // 60 - 600)
                    cur.execute("""
                        UPDATE workouts SET duration_minutes = %s WHERE id = %s
                    """, (duration, workout_id))
                    conn.commit()
                    return redirect(url_for('menu'))

            # Получаем список всех доступных упражнений
            cur.execute("SELECT id, name FROM exercises ORDER BY name")
            exercises = cur.fetchall()

            # Получаем все подходы, связанные с тренировкой
            cur.execute("""
                SELECT sets.*, exercises.name
                FROM sets
                JOIN exercises ON sets.exercise_id = exercises.id
                WHERE workout_id = %s
                ORDER BY sets.order_num
            """, (workout_id,))
            sets = cur.fetchall()

            # Группируем по exercise_id
            grouped_sets = {}
            for s in sets:
                grouped_sets.setdefault(s['exercise_id'], []).append(s)

    return render_template('active_training.html',
                           workout=workout,
                           exercises=exercises,
                           grouped_sets=grouped_sets)
    

@app.route('/finish/<int:workout_id>', methods=['POST'])
def finish_training(workout_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    duration = data.get('duration')

    if duration is None or not isinstance(duration, int):
        return jsonify({'error': 'Invalid duration'}), 400

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE workouts
                SET duration_minutes = %s
                WHERE id = %s AND user_id = %s
            """, (duration, workout_id, session['user_id']))
            conn.commit()

    return jsonify({'status': 'ok'})


@app.route('/mytrainings')
def my_training():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:

            # Статка по активной тренировке
            cur.execute("""
                SELECT * FROM workouts
                WHERE user_id = %s AND duration_minutes IS NULL
                ORDER BY start_time DESC
                LIMIT 1
            """, (user_id,))
            active_workout = cur.fetchone()

            # Статка по завершенным тренировкам
            cur.execute("""
                SELECT * FROM workouts
                WHERE user_id = %s AND duration_minutes IS NOT NULL
                ORDER BY date DESC, start_time DESC
            """, (user_id,))
            completed_workouts = cur.fetchall()

    return render_template('mytrainings.html',
                           active_workout = active_workout,
                           completed_workouts = completed_workouts)


@app.route('/workout_stats/<int:workout_id>')
def workout_stats(workout_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # General info
            cur.execute("""
                SELECT *,
                EXTRACT(EPOCH FROM (start_time + (duration_minutes * INTERVAL '1 minute') - start_time))/60 AS calculated_duration
                FROM workouts
                WHERE id = %s AND user_id = %s
            """, (workout_id, session['user_id']))
            workout=cur.fetchone()

            if not workout_id:
                flash("Тренировка не найдена")
                return redirect(url_for('mytrainings'))

            # Получаем все упражнения и подходы для этой тренировки
            cur.execute("""
                SELECT 
                    e.id AS exercise_id,
                    e.name AS exercise_name,
                    s.id AS set_id,
                    s.weight_kg,
                    s.reps,
                    (s.weight_kg * s.reps) AS tonnage
                FROM sets s
                JOIN exercises e ON s.exercise_id = e.id
                WHERE s.workout_id = %s
                ORDER BY e.name, s.order_num
            """, (workout_id,))
            sets = cur.fetchall()

            # Группируем по упражнениям и считаем общий тоннаж
            exercises = {}
            total_tonnage = 0

            for s in sets:
                if s['exercise_id'] not in exercises:
                    exercises[s['exercise_id']] = {
                        'name': s['exercise_name'],
                        'sets': [],
                        'total_tonnage': 0
                    }

                exercises[s['exercise_id']]['sets'].append({
                    'weight': s['weight_kg'],
                    'reps': s['reps'],
                    'tonnage': s['tonnage']
                })
                exercises[s['exercise_id']]['total_tonnage'] += s['tonnage'] or 0
                total_tonnage += s['tonnage'] or 0

    return render_template('workout_stats.html',
                           workout=workout,
                           sets=sets,
                           exercises=exercises,
                           total_tonnage=total_tonnage)



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
