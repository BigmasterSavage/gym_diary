-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    gender VARCHAR(10)
        CHECK (gender IN ('мужской', 'женский') OR gender IS NULL),
    age INTEGER
        CHECK (age > 0 OR age IS NULL),
    weight_kg NUMERIC(5,2)
        CHECK (weight_kg > 0 OR weight_kg IS NULL),
    height_cm INTEGER
        CHECK (height_cm > 0 OR height_cm IS NULL)
);

-- Таблица тренировок
CREATE TABLE IF NOT EXISTS workouts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    title TEXT,
    note TEXT,
    intensity VARCHAR(20)
        CHECK (
            intensity IN ('легкая', 'средняя', 'тяжелая', 'разгрузочная', 'растяжка') OR intensity IS NULL
        ),
    start_time TIMESTAMP DEFAULT NOW(),
    duration_minutes INTEGER
);

-- Таблица упражнений
CREATE TABLE IF NOT EXISTS exercises (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    muscle_group VARCHAR(20)
        CHECK (muscle_group IN ('ноги', 'спина', 'грудные', 'дельты', 'трицепс', 'бицепс', 'кор') OR muscle_group IS NULL),
    is_basic BOOLEAN DEFAULT NULL,
    equipment_type VARCHAR(20)
        CHECK (equipment_type IN ('рычажный', 'блочный', 'свободный вес', 'свой вес') OR equipment_type IS NULL)
);

-- Таблица подходов
CREATE TABLE IF NOT EXISTS sets (
    id SERIAL PRIMARY KEY,
    workout_id INTEGER REFERENCES workouts(id),
    exercise_id INTEGER REFERENCES exercises(id),
    order_num INTEGER,
    weight_kg NUMERIC(5,2),
    reps INTEGER,
    note TEXT,
    execution_type VARCHAR(20)
        CHECK (execution_type IN ('классика', 'дроп-сет', 'суперсет', 'трисет', 'статика', 'пирамида', 'полупирамида'))
        DEFAULT 'классика'
);

-- Добавление пользователя 'admin' при инициализации
INSERT INTO users (username)
VALUES ('admin')
ON CONFLICT (username) DO NOTHING;


-- Добавление упражнений с полной информацией
INSERT INTO exercises (name, muscle_group, is_basic, is_compound, equipment_type) VALUES
('Становая тяга', 'спина', TRUE, TRUE, 'свободный вес'),
('Тяга штанги в наклоне', 'спина', TRUE, TRUE, 'свободный вес'),
('Подтягивания', 'спина', TRUE, TRUE, 'свой вес'),
('Тяга горизонтального блока', 'спина', FALSE, FALSE, 'блочный'),
('Подъем штанги на бицепс', 'бицепс', FALSE, FALSE, 'свободный вес'),
('Подъем гантелей на бицепс', 'бицепс', FALSE, FALSE, 'свободный вес'),
('Молотки', 'бицепс', FALSE, FALSE, 'свободный вес'),
('Гиперэкстензия', 'спина', FALSE, FALSE, 'рычажный'),
('Скручивания', 'кор', FALSE, FALSE, 'свой вес'),
('Подъем ног лежа', 'кор', FALSE, FALSE, 'свой вес'),
('Жим штанги лежа', 'грудные', TRUE, TRUE, 'свободный вес'),
('Жим гантелей лежа', 'грудные', TRUE, TRUE, 'свободный вес'),
('Жим штанги стоя', 'дельты', TRUE, TRUE, 'свободный вес'),
('Отжимания на брусьях с весом', 'грудные', TRUE, TRUE, 'свой вес'),
('Пек-дек', 'грудные', FALSE, FALSE, 'рычажный'),
('Французский жим лёжа', 'трицепс', FALSE, FALSE, 'свободный вес'),
('Отжимания узким хватом', 'трицепс', FALSE, FALSE, 'свой вес'),
('Жим штанги верх обратным хватом', 'дельты', FALSE, FALSE, 'свободный вес'),
('Планка', 'кор', FALSE, FALSE, 'свой вес'),
('Велосипед', 'кор', FALSE, FALSE, 'свой вес'),
('Приседания со штангой', 'ноги', TRUE, TRUE, 'свободный вес'),
('Румынская тяга', 'ноги', TRUE, TRUE, 'свободный вес'),
('Жим ногами', 'ноги', TRUE, TRUE, 'рычажный'),
('Подъемы на носки стоя', 'ноги', FALSE, FALSE, 'свободный вес'),
('Подъемы на носки сидя', 'ноги', FALSE, FALSE, 'рычажный'),
('Махи гантелями в стороны', 'дельты', FALSE, FALSE, 'свободный вес'),
('Махи гантелями вперед', 'дельты', FALSE, FALSE, 'свободный вес'),
('Тяга штанги к подбородку', 'дельты', FALSE, FALSE, 'свободный вес'),
('Планка на локтях', 'кор', FALSE, FALSE, 'свой вес'),
('Вакуум', 'кор', FALSE, FALSE, 'свой вес'),
('Жим гантелей сидя', 'дельты', TRUE, TRUE, 'свободный вес'),
('Разгибание на трицепс - кроссовер (палка)', 'трицепс', FALSE, FALSE, 'блочный'),
('Подъем ног в упоре', 'кор', FALSE, FALSE, 'свой вес'),
('Сгибание ног в тренажере', 'ноги', FALSE, FALSE, 'рычажный'),
('Разгибание ног в тренажере', 'ноги', FALSE, FALSE, 'рычажный'),
('Разведение ног в тренажере', 'ноги', FALSE, FALSE, 'рычажный'),
('Пек-дек', 'грудные', FALSE, FALSE, 'рычажный');

-- Таблица планов тренировок
CREATE TABLE IF NOT EXISTS workout_plans (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    title TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Таблица запланированных тренировок
CREATE TABLE IF NOT EXISTS planned_workouts (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER REFERENCES workout_plans(id),
    title TEXT NOT NULL,
    description TEXT,
    day_of_week INTEGER CHECK (day_of_week BETWEEN 1 AND 7),
    is_completed BOOLEAN DEFAULT FALSE
);