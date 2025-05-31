-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Таблица тренировок
CREATE TABLE IF NOT EXISTS workouts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    note TEXT,
    intensity VARCHAR(20)
        CHECK (
            intensity IN ('легкая', 'средняя', 'тяжелая', 'разгрузочная', 'растяжка') OR intensity IS NULL
        ),
    start_time TIMESTAMP,
    duration_minutes INTEGER
);

-- Таблица упражнений
CREATE TABLE IF NOT EXISTS exercises (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_basic BOOLEAN DEFAULT FALSE
);

-- Таблица подходов
CREATE TABLE IF NOT EXISTS sets (
    id SERIAL PRIMARY KEY,
    workout_id INTEGER REFERENCES workouts(id),
    exercise_id INTEGER REFERENCES exercises(id),
    weight_kg NUMERIC(5,2),
    reps INTEGER,
    note TEXT
);

-- Добавление пользователя 'admin' при инициализации
INSERT INTO users (username)
VALUES ('admin')
ON CONFLICT (username) DO NOTHING;
