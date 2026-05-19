# database.py
import mysql.connector
from mysql.connector import Error
import hashlib


class Database:
    def __init__(self):
        self.conn = None

    def connect(self, host, user, password, database=None):
        try:
            cfg = dict(host=host, user=user, password=password)
            if database:
                cfg["database"] = database
            self.conn = mysql.connector.connect(**cfg)
            return True, "Connected"
        except Error as e:
            return False, str(e)

    def cursor(self, dictionary=False):
        if self.conn and self.conn.is_connected():
            return self.conn.cursor(dictionary=dictionary)
        raise RuntimeError("Not connected to database.")

    def commit(self):
        self.conn.commit()

    def close(self):
        if self.conn and self.conn.is_connected():
            self.conn.close()

    def setup_database(self):
        """Create the SMS database and all tables."""
        cur = self.cursor()
        cur.execute("CREATE DATABASE IF NOT EXISTS student_management_db")
        cur.execute("USE student_management_db")

        # Users table with soft delete
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id         INT AUTO_INCREMENT PRIMARY KEY,
                username   VARCHAR(50)  NOT NULL UNIQUE,
                password   VARCHAR(255) NOT NULL,
                role       ENUM('admin','teacher','student') DEFAULT 'student',
                full_name  VARCHAR(100) NOT NULL,
                email      VARCHAR(100),
                student_id VARCHAR(20),
                teacher_id INT,
                is_deleted BOOLEAN DEFAULT FALSE,
                deleted_at DATETIME,
                created    DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Teachers table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS teachers (
                id         INT AUTO_INCREMENT PRIMARY KEY,
                teacher_id VARCHAR(20)  NOT NULL UNIQUE,
                full_name  VARCHAR(100) NOT NULL,
                email      VARCHAR(100),
                phone      VARCHAR(20),
                address    TEXT,
                status     ENUM('Active','Inactive') DEFAULT 'Active',
                is_deleted BOOLEAN DEFAULT FALSE,
                deleted_at DATETIME,
                created    DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Classes table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS classes (
                id         INT AUTO_INCREMENT PRIMARY KEY,
                class_name VARCHAR(50)  NOT NULL UNIQUE,
                teacher_id INT,
                room       VARCHAR(20) NOT NULL,
                status     ENUM('Active','Inactive') DEFAULT 'Active',
                is_deleted BOOLEAN DEFAULT FALSE,
                deleted_at DATETIME,
                created    DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE SET NULL
            )
        """)

        # Subjects table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id           INT AUTO_INCREMENT PRIMARY KEY,
                subject_name VARCHAR(100) NOT NULL,
                subject_code VARCHAR(20)  NOT NULL UNIQUE,
                credits      INT NOT NULL DEFAULT 3,
                status       ENUM('Active','Inactive') DEFAULT 'Active',
                is_deleted   BOOLEAN DEFAULT FALSE,
                deleted_at   DATETIME,
                created      DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Class-Subject junction table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS class_subjects (
                class_id   INT NOT NULL,
                subject_id INT NOT NULL,
                PRIMARY KEY (class_id, subject_id),
                FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            )
        """)

        # Students table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id         INT AUTO_INCREMENT PRIMARY KEY,
                student_id VARCHAR(20)  NOT NULL UNIQUE,
                full_name  VARCHAR(100) NOT NULL,
                gender     ENUM('Male','Female','Other') DEFAULT 'Male',
                dob        DATE,
                email      VARCHAR(100),
                phone      VARCHAR(20),
                address    TEXT,
                class_id   INT,
                status     ENUM('Active','Inactive') DEFAULT 'Active',
                is_deleted BOOLEAN DEFAULT FALSE,
                deleted_at DATETIME,
                created    DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE SET NULL
            )
        """)

        # Scores table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                id         INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                subject_id INT NOT NULL,
                midterm    FLOAT DEFAULT 0,
                final      FLOAT DEFAULT 0,
                total      FLOAT GENERATED ALWAYS AS (midterm*0.4 + final*0.6) STORED,
                grade      VARCHAR(2) GENERATED ALWAYS AS (
                               CASE
                                   WHEN midterm*0.4+final*0.6 >= 90 THEN 'A+'
                                   WHEN midterm*0.4+final*0.6 >= 80 THEN 'A'
                                   WHEN midterm*0.4+final*0.6 >= 75 THEN 'B+'
                                   WHEN midterm*0.4+final*0.6 >= 70 THEN 'B'
                                   WHEN midterm*0.4+final*0.6 >= 65 THEN 'C+'
                                   WHEN midterm*0.4+final*0.6 >= 60 THEN 'C'
                                   WHEN midterm*0.4+final*0.6 >= 50 THEN 'D'
                                   ELSE 'F'
                               END
                           ) STORED,
                created    DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
                UNIQUE KEY uq_score (student_id, subject_id)
            )
        """)

        self._seed_data(cur)
        self.commit()
        self.conn.database = "student_management_db"

    def _seed_data(self, cur):
        """Seed initial data for testing."""
        # Seed admin user
        admin_pw = hashlib.sha256("admin123".encode()).hexdigest()
        cur.execute("""
            INSERT IGNORE INTO users (username, password, role, full_name, email, is_deleted)
            VALUES ('admin', %s, 'admin', 'System Administrator', 'admin@school.edu', FALSE)
        """, (admin_pw,))

        # Seed teacher
        teacher_pw = hashlib.sha256("teacher123".encode()).hexdigest()
        cur.execute("""
            INSERT IGNORE INTO teachers (teacher_id, full_name, email, phone, status, is_deleted)
            VALUES ('TCH001', 'Prof. John Smith', 'john.smith@school.edu', '555-0101', 'Active', FALSE)
        """)
        cur.execute("""
            INSERT IGNORE INTO users (username, password, role, full_name, email, teacher_id, is_deleted)
            VALUES ('teacher', %s, 'teacher', 'John Smith', 'john.smith@school.edu', 1, FALSE)
        """, (teacher_pw,))

        # Seed classes
        cur.execute("""
            INSERT IGNORE INTO classes (class_name, teacher_id, room, status, is_deleted)
            VALUES ('Grade 10 - Section A', 1, 'Room 101', 'Active', FALSE)
        """)
        cur.execute("""
            INSERT IGNORE INTO classes (class_name, teacher_id, room, status, is_deleted)
            VALUES ('Grade 11 - Section B', 1, 'Room 102', 'Active', FALSE)
        """)

        # Seed subjects
        cur.execute("""
            INSERT IGNORE INTO subjects (subject_name, subject_code, credits, status, is_deleted)
            VALUES 
                ('Mathematics', 'MATH101', 4, 'Active', FALSE),
                ('Physics', 'PHY101', 4, 'Active', FALSE),
                ('English', 'ENG101', 3, 'Active', FALSE)
        """)
        
        cur.execute("INSERT IGNORE INTO class_subjects (class_id, subject_id) VALUES (1,1), (1,2), (1,3)")
        cur.execute("INSERT IGNORE INTO class_subjects (class_id, subject_id) VALUES (2,1), (2,2)")

        # Seed students
        student_pw = hashlib.sha256("student123".encode()).hexdigest()
        cur.execute("""
            INSERT IGNORE INTO students (student_id, full_name, gender, email, phone, class_id, status, is_deleted)
            VALUES ('STU001', 'Alice Johnson', 'Female', 'alice@student.edu', '555-0201', 1, 'Active', FALSE)
        """)
        cur.execute("""
            INSERT IGNORE INTO users (username, password, role, full_name, email, student_id, is_deleted)
            VALUES ('student', %s, 'student', 'Alice Johnson', 'alice@student.edu', 'STU001', FALSE)
        """, (student_pw,))

        cur.execute("""
            INSERT IGNORE INTO students (student_id, full_name, gender, email, phone, class_id, status, is_deleted)
            VALUES ('STU002', 'Bob Williams', 'Male', 'bob@student.edu', '555-0202', 1, 'Active', FALSE)
        """)
        cur.execute("""
            INSERT IGNORE INTO users (username, password, role, full_name, email, student_id, is_deleted)
            VALUES ('student2', %s, 'student', 'Bob Williams', 'bob@student.edu', 'STU002', FALSE)
        """, (student_pw,))
        
        cur.execute("""
            INSERT IGNORE INTO students (student_id, full_name, gender, email, phone, class_id, status, is_deleted)
            VALUES ('STU003', 'Charlie Brown', 'Male', 'charlie@student.edu', '555-0203', 2, 'Active', FALSE)
        """)
        cur.execute("""
            INSERT IGNORE INTO users (username, password, role, full_name, email, student_id, is_deleted)
            VALUES ('student3', %s, 'student', 'Charlie Brown', 'charlie@student.edu', 'STU003', FALSE)
        """, (student_pw,))
        
db = Database()        