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

    # Проверяем есть ли активная тренировка
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id FROM workouts 
                WHERE user_id = %s AND duration_minutes IS NULL
                LIMIT 1
            """, (session['user_id'],))
            active_workout = cur.fetchone()

    return render_template('menu.html', active_workout=bool(active_workout))


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        gender = request.form.get('gender')
        age = request.form.get('age')
        weight = request.form.get('weight')
        height = request.form.get('height')

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE users 
                    SET gender = %s, age = %s, weight_kg = %s, height_cm = %s
                    WHERE id = %s
                """, (gender, age, weight, height, session['user_id']))
                conn.commit()

        flash("Данные успешно обновлены")
        return redirect(url_for('profile'))

    # GET запрос - отображаем текущие данные
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
            user_data = cur.fetchone()

    return render_template('profile.html', user=user_data)


@app.route('/exercises', methods=['GET', 'POST'])
def exercises():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            name = request.form.get('name')
            muscle_group = request.form.get('muscle_group') or None
            equipment_type = request.form.get('equipment_type') or None
            exercise_type = request.form.get('exercise_type')

            is_basic = exercise_type == 'basic' if exercise_type else None

            if name:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """INSERT INTO exercises 
                            (name, muscle_group, equipment_type, is_basic) 
                            VALUES (%s, %s, %s, %s)""",
                            (name, muscle_group, equipment_type, is_basic)
                        )
                        conn.commit()
                flash("Упражнение добавлено")
            else:
                flash("Название упражнения обязательно")

        elif action == 'edit':
            exercise_id = request.form.get('exercise_id')
            name = request.form.get('name')
            muscle_group = request.form.get('muscle_group') or None
            equipment_type = request.form.get('equipment_type') or None
            exercise_type = request.form.get('exercise_type')

            is_basic = exercise_type == 'basic' if exercise_type else None

            if name and exercise_id:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """UPDATE exercises 
                            SET name = %s, muscle_group = %s, equipment_type = %s, is_basic = %s
                            WHERE id = %s""",
                            (name, muscle_group, equipment_type, is_basic, exercise_id)
                        )
                        conn.commit()
                flash("Упражнение обновлено")
            else:
                flash("Необходимо указать название упражнения")

        elif action == 'delete':
            exercise_id = request.form.get('exercise_id')
            if exercise_id:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        # Проверяем, используется ли упражнение в подходах
                        cur.execute("SELECT COUNT(*) FROM sets WHERE exercise_id = %s", (exercise_id,))
                        count = cur.fetchone()[0]

                        if count > 0:
                            flash("Нельзя удалить упражнение, так как оно используется в тренировках")
                        else:
                            cur.execute("DELETE FROM exercises WHERE id = %s", (exercise_id,))
                            conn.commit()
                            flash("Упражнение удалено")

        return redirect(url_for('exercises'))

    # GET: отображаем список упражнений
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # Получаем параметры фильтрации
            muscle_group = request.args.get('muscle_group')
            equipment_type = request.args.get('equipment_type')
            exercise_type = request.args.get('exercise_type')

            # Формируем запрос с учетом фильтров
            query = "SELECT * FROM exercises WHERE TRUE"
            params = []

            if muscle_group:
                query += " AND muscle_group = %s"
                params.append(muscle_group)

            if equipment_type:
                query += " AND equipment_type = %s"
                params.append(equipment_type)

            if exercise_type == 'basic':
                query += " AND is_basic = TRUE"
            elif exercise_type == 'isolated':
                query += " AND is_basic = FALSE"

            query += " ORDER BY name"
            cur.execute(query, params)
            exercises_list = cur.fetchall()

    return render_template('exercises.html', exercises=exercises_list)


@app.route('/createtraining', methods=['GET', 'POST'])
def createtraining():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Проверяем есть ли активная тренировка
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id FROM workouts 
                WHERE user_id = %s AND duration_minutes IS NULL
                LIMIT 1
            """, (session['user_id'],))
            active_workout = cur.fetchone()

    if active_workout:
        flash("У вас уже есть активная тренировка. Завершите её перед созданием новой.")
        return redirect(url_for('active_training', workout_id=active_workout[0]))

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


@app.route('/activetraining/<int:workout_id>', methods=['GET'])
def active_training(workout_id):
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


# AJAX endpoint для добавления упражнения
@app.route('/activetraining/<int:workout_id>/add_exercise', methods=['POST'])
def add_exercise_ajax(workout_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    ex_id = data.get('exercise_id')
    execution_type = data.get('execution_type', 'классика')  # Получаем тип выполнения

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # Получаем название упражнения
            cur.execute("SELECT name FROM exercises WHERE id = %s", (ex_id,))
            exercise = cur.fetchone()
            if not exercise:
                return jsonify({'error': 'Exercise not found'}), 404

            # Добавляем подход с указанием типа выполнения
            cur.execute("SELECT COALESCE(MAX(order_num), 0) FROM sets WHERE workout_id = %s", (workout_id,))
            max_order = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO sets (workout_id, exercise_id, order_num, execution_type)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (workout_id, ex_id, max_order + 1, execution_type))
            set_id = cur.fetchone()['id']

            conn.commit()

    return jsonify({
        'success': True,
        'exercise_id': ex_id,
        'exercise_name': exercise['name'],
        'set_id': set_id,
        'execution_type': execution_type
    })


# AJAX endpoint для добавления подхода
@app.route('/activetraining/<int:workout_id>/add_set', methods=['POST'])
def add_set_ajax(workout_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    ex_id = data.get('exercise_id')

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # Получаем текущее количество подходов для этого упражнения
            cur.execute("""
                SELECT COUNT(*) as cnt FROM sets
                WHERE workout_id = %s AND exercise_id = %s
            """, (workout_id, ex_id))
            set_count = cur.fetchone()['cnt'] + 1

            # Добавляем новый подход
            cur.execute("SELECT COALESCE(MAX(order_num), 0) FROM sets WHERE workout_id = %s", (workout_id,))
            max_order = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO sets (workout_id, exercise_id, order_num)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (workout_id, ex_id, max_order + 1))
            set_id = cur.fetchone()['id']

            conn.commit()

    return jsonify({
        'success': True,
        'set_id': set_id,
        'set_number': set_count
    })


# AJAX endpoint для удаления подхода
@app.route('/activetraining/<int:workout_id>/delete_set', methods=['POST'])
def delete_set_ajax(workout_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    set_id = data.get('set_id')

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sets WHERE id = %s AND workout_id = %s", (set_id, workout_id))
            conn.commit()

    return jsonify({'success': True})


# AJAX endpoint для удаления упражнения
@app.route('/activetraining/<int:workout_id>/remove_exercise', methods=['POST'])
def remove_exercise_ajax(workout_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    ex_id = data.get('exercise_id')

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sets WHERE workout_id = %s AND exercise_id = %s", (workout_id, ex_id))
            conn.commit()

    return jsonify({'success': True})


# AJAX endpoint для сохранения упражнения
@app.route('/activetraining/<int:workout_id>/save_exercise', methods=['POST'])
def save_exercise_ajax(workout_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    ex_id = data.get('exercise_id')
    sets_data = data.get('sets', [])

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            for set_data in sets_data:
                weight = float(set_data['weight']) if set_data['weight'] else None
                reps = int(set_data['reps']) if set_data['reps'] else None

                cur.execute("""
                    UPDATE sets SET weight_kg = %s, reps = %s
                    WHERE id = %s AND workout_id = %s
                """, (weight, reps, set_data['set_id'], workout_id))

            conn.commit()

    return jsonify({'success': True})


# AJAX endpoint для завершения тренировки
@app.route('/activetraining/<int:workout_id>/finish', methods=['POST'])
def finish_workout_ajax(workout_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    duration = data.get('duration')

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE workouts SET duration_minutes = %s
                WHERE id = %s AND user_id = %s
            """, (duration, workout_id, session['user_id']))
            conn.commit()

    return jsonify({'success': True})




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


@app.route('/delete_workout/<int:workout_id>', methods=['POST'])
def delete_workout(workout_id):
    if 'user_id' not in session:
        flash("Необходимо авторизоваться")
        return redirect(url_for('login'))

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            try:
                # Сначала проверяем, что тренировка принадлежит пользователю
                cur.execute("SELECT user_id FROM workouts WHERE id = %s", (workout_id,))
                result = cur.fetchone()

                if not result:
                    flash("Тренировка не найдена")
                    return redirect(url_for('my_training'))

                if result[0] != session['user_id']:
                    flash("Нельзя удалить чужую тренировку")
                    return redirect(url_for('my_training'))

                # Удаляем сначала подходы (из-за внешнего ключа)
                cur.execute("DELETE FROM sets WHERE workout_id = %s", (workout_id,))
                # Затем удаляем саму тренировку
                cur.execute("DELETE FROM workouts WHERE id = %s", (workout_id,))
                conn.commit()

                flash("Тренировка успешно удалена", "success")
            except Exception as e:
                conn.rollback()
                flash(f"Ошибка при удалении тренировки: {str(e)}", "error")

    return redirect(url_for('my_training'))


@app.route('/workout_stats/<int:workout_id>')
def workout_stats(workout_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # Получаем информацию о тренировке
            cur.execute("""
                SELECT * FROM workouts
                WHERE id = %s AND user_id = %s
            """, (workout_id, session['user_id']))
            workout = cur.fetchone()

            if not workout:
                flash("Тренировка не найдена")
                return redirect(url_for('my_training'))

            cur.execute("""
                SELECT 
                    e.id AS exercise_id,
                    e.name AS exercise_name,
                    s.id AS set_id,
                    s.weight_kg,
                    s.reps,
                    (s.weight_kg * s.reps) AS tonnage,
                    s.order_num
                FROM sets s
                JOIN exercises e ON s.exercise_id = e.id
                JOIN workouts w ON s.workout_id = w.id
                WHERE s.workout_id = %s AND w.user_id = %s
                ORDER BY s.order_num, s.id
            """, (workout_id, session['user_id']))
            sets = cur.fetchall()

            # Группируем по упражнениям
            exercises = {}
            exercise_order = []
            total_tonnage = 0

            for s in sets:
                if s['exercise_id'] not in exercises:
                    exercises[s['exercise_id']] = {
                        'name': s['exercise_name'],
                        'sets': [],
                        'total_tonnage': 0
                    }
                    exercise_order.append(s['exercise_id'])

                exercises[s['exercise_id']]['sets'].append({
                    'weight': s['weight_kg'],
                    'reps': s['reps'],
                    'tonnage': s['tonnage'],
                    'order_num': s['order_num'],
                    'set_id': s['set_id']
                })
                exercises[s['exercise_id']]['total_tonnage'] += s['tonnage'] or 0
                total_tonnage += s['tonnage'] or 0

    return render_template('workout_stats.html',
                           workout=workout,
                           exercises=exercises,
                           exercise_order=exercise_order,
                           total_tonnage=total_tonnage)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
