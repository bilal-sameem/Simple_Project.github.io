-- Reference only: Django creates these tables for you from models.py
-- (python manage.py makemigrations sawanih && python manage.py migrate).
CREATE TABLE sawanih_person (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  full_name        VARCHAR(150) NOT NULL,
  father_name      VARCHAR(150) NOT NULL,
  grandfather_name VARCHAR(150) NOT NULL DEFAULT '',
  date_of_birth    DATE         NOT NULL,
  id_number        VARCHAR(30)  NOT NULL UNIQUE,
  phone            VARCHAR(20)  NOT NULL,
  email            VARCHAR(254) NOT NULL DEFAULT '',
  address          TEXT         NOT NULL DEFAULT '',
  photo            VARCHAR(100) NOT NULL DEFAULT '',
  job_title        VARCHAR(150) NOT NULL DEFAULT '',
  organization     VARCHAR(150) NOT NULL DEFAULT '',
  start_date       DATE         NULL,
  hire_letter_number   VARCHAR(60)  NOT NULL DEFAULT '',   -- مکتوب شمېره
  hire_letter_date     DATE,                          -- stored as a normal date, shown as solar date
  hire_letter_issuer   VARCHAR(150) NOT NULL DEFAULT '',
  notes            TEXT         NOT NULL DEFAULT '',
  created_by_id    INTEGER NULL REFERENCES auth_user(id) ON DELETE SET NULL,
  created_at       DATETIME NOT NULL,
  updated_by_id    INTEGER NULL REFERENCES auth_user(id) ON DELETE SET NULL,
  updated_at       DATETIME NULL
);

-- one person, many degrees (e.g. bachelor + master)
CREATE TABLE sawanih_education (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  person_id       INTEGER NOT NULL REFERENCES sawanih_person(id) ON DELETE CASCADE,
  degree          VARCHAR(100) NOT NULL,
  institution     VARCHAR(150) NOT NULL,
  graduation_year SMALLINT NULL,
  position        SMALLINT NOT NULL DEFAULT 0
);

-- uploaded files; kind = 'id_card' | 'experience' | 'education'
-- (files are saved in private_media/, outside the public MEDIA folder)
CREATE TABLE sawanih_persondocument (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  person_id     INTEGER NOT NULL REFERENCES sawanih_person(id) ON DELETE CASCADE,
  kind          VARCHAR(12)  NOT NULL,
  file          VARCHAR(100) NOT NULL,
  original_name VARCHAR(120) NOT NULL DEFAULT '',
  uploaded_by_id INTEGER NULL REFERENCES auth_user(id) ON DELETE SET NULL,
  uploaded_at   DATETIME NOT NULL
);
