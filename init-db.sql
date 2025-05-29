-- init-db.sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE workouts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    note TEXT
);

CREATE TABLE exercises (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT
);

CREATE TABLE sets (
    id SERIAL PRIMARY KEY,
    workout_id INTEGER REFERENCES workouts(id),
    exercise_id INTEGER REFERENCES exercises(id),
    weight_kg NUMERIC(5,2),
    reps INTEGER,
    note TEXT
);

-- Добавление пользователя 'admin' при инициализации БД
INSERT INTO users (username) VALUES ('admin');