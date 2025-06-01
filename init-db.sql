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
    description TEXT,
    is_basic BOOLEAN DEFAULT FALSE
);

-- Таблица подходов
CREATE TABLE IF NOT EXISTS sets (
    id SERIAL PRIMARY KEY,
    workout_id INTEGER REFERENCES workouts(id),
    exercise_id INTEGER REFERENCES exercises(id),
    order_num INTEGER,
    weight_kg NUMERIC(5,2),
    reps INTEGER,
    note TEXT
);


-- Добавление пользователя 'admin' при инициализации
INSERT INTO users (username)
VALUES ('admin')
ON CONFLICT (username) DO NOTHING;


-- Добавление упражнений при инициализации
INSERT INTO exercises (name, description, is_basic) VALUES
('Становая тяга', 'Базовое тяговое упражнение для спины и ног', TRUE),
('Тяга штанги в наклоне', 'Альтернатива становому подъему', TRUE),
('Подтягивания', 'Упражнение на широчайшие мышцы спины', TRUE),
('Тяга горизонтального блока', 'Изолированная тяга для спины', FALSE),
('Подъем штанги на бицепс', 'Классическое упражнение на бицепс', FALSE),
('Подъем гантелей на бицепс', 'Альтернатива штанге', FALSE),
('Молотки', 'Упражнение на длинную головку бицепса', FALSE),
('Гиперэкстензия', 'Упражнение на поясницу и ягодицы', FALSE),
('Скручивания', 'Упражнение на верхний пресс', FALSE),
('Подъем ног лежа', 'Упражнение на нижний пресс', FALSE),
('Жим штанги лежа', 'Базовое упражнение на грудь', TRUE),
('Жим гантелей лежа', 'Альтернатива жиму штанги', TRUE),
('Жим штанги стоя', 'Базовое упражнение на плечи', TRUE),
('Отжимания на брусьях с весом', 'Базовое упражнение на грудь и трицепсы', TRUE),
('Пек-дек машина', 'Изолированное упражнение на внутреннюю часть груди', FALSE),
('Французский жим лёжа', 'Упражнение на трицепс', FALSE),
('Отжимания узким хватом', 'Альтернатива французскому жиму', FALSE),
('Жим штанги верх обратным хватом', 'Упражнение на передние дельты', FALSE),
('Планка', 'Упражнение на кор', FALSE),
('Велосипед', 'Динамическое упражнение на пресс', FALSE),
('Приседания со штангой', 'Базовое упражнение на ноги', TRUE),
('Румынская тяга', 'Базовое упражнение на заднюю цепь', TRUE),
('Жим ногами', 'Базовое упражнение на квадрицепсы', TRUE),
('Подъемы на носки стоя', 'Упражнение на икры', FALSE),
('Подъемы на носки сидя', 'Альтернатива стоя', FALSE),
('Махи гантелями в стороны', 'Упражнение на средние дельты', FALSE),
('Махи гантелями вперед', 'Упражнение на передние дельты', FALSE),
('Тяга штанги к подбородку', 'Упражнение на дельты и трапеции', FALSE),
('Планка на локтях', 'Упражнение на кор', FALSE),
('Вакуум', 'Упражнение на поперечную мышцу живота', FALSE);
