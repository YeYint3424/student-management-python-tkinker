"""
Student Management System with Role-Based Access Control
Built with CustomTkinter + MySQL
Roles: Admin, Teacher, Student
- Admin: Full access to all data
- Teacher: Access only to their assigned class and students
- Student: View-only access to their own data
"""

import customtkinter as ctk
from tkinter import ttk, messagebox
import mysql.connector
from mysql.connector import Error
import hashlib
import re
from datetime import datetime

# ─────────────────────────────────────────────
#  Theme / appearance
# ─────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ─────────────────────────────────────────────
#  Colours
# ─────────────────────────────────────────────
PRIMARY    = "#3B82F6"
PRIMARY_H  = "#2563EB"
SUCCESS    = "#10B981"
WARNING    = "#F59E0B"
DANGER     = "#EF4444"
BG_DARK    = "#0F172A"
CARD       = "#1E293B"
CARD2      = "#334155"
TEXT       = "#F8FAFC"
SUBTEXT    = "#94A3B8"
BORDER     = "#475569"
SIDEBAR_W  = 220


# ══════════════════════════════════════════════
#  DATABASE LAYER
# ══════════════════════════════════════════════
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

        # Users table - includes student_id for student users
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id         INT AUTO_INCREMENT PRIMARY KEY,
                username   VARCHAR(50)  NOT NULL UNIQUE,
                password   VARCHAR(255) NOT NULL,
                role       ENUM('admin','teacher','student') DEFAULT 'student',
                full_name  VARCHAR(100),
                email      VARCHAR(100),
                student_id VARCHAR(20),  -- Link to students table for student users
                teacher_id INT,           -- Link to teachers table (optional)
                created    DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Teachers table with class assignment
        cur.execute("""
            CREATE TABLE IF NOT EXISTS teachers (
                id         INT AUTO_INCREMENT PRIMARY KEY,
                teacher_id VARCHAR(20)  NOT NULL UNIQUE,
                full_name  VARCHAR(100) NOT NULL,
                email      VARCHAR(100),
                phone      VARCHAR(20),
                address    TEXT,
                created    DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS classes (
                id         INT AUTO_INCREMENT PRIMARY KEY,
                class_name VARCHAR(50)  NOT NULL UNIQUE,
                teacher_id INT,          -- Teacher assigned to this class
                room       VARCHAR(20),
                created    DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE SET NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id           INT AUTO_INCREMENT PRIMARY KEY,
                subject_name VARCHAR(100) NOT NULL,
                subject_code VARCHAR(20)  NOT NULL UNIQUE,
                credits      INT DEFAULT 3,
                teacher_id   INT,
                created      DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE SET NULL
            )
        """)

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
                created    DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE SET NULL
            )
        """)

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

        # Sample data seeding
        self._seed_data(cur)

        self.commit()
        self.conn.database = "student_management_db"

    def _seed_data(self, cur):
        """Seed initial data for testing."""
        # Seed admin user
        admin_pw = hashlib.sha256("admin123".encode()).hexdigest()
        cur.execute("""
            INSERT IGNORE INTO users (username, password, role, full_name)
            VALUES ('admin', %s, 'admin', 'System Administrator')
        """, (admin_pw,))

        # Seed teacher
        teacher_pw = hashlib.sha256("teacher123".encode()).hexdigest()
        cur.execute("""
            INSERT IGNORE INTO teachers (teacher_id, full_name, email)
            VALUES ('TCH001', 'Prof. John Smith', 'john.smith@school.edu')
        """)
        cur.execute("""
            INSERT IGNORE INTO users (username, password, role, full_name, teacher_id)
            VALUES ('teacher', %s, 'teacher', 'John Smith', 1)
        """, (teacher_pw,))

        # Seed class
        cur.execute("""
            INSERT IGNORE INTO classes (class_name, teacher_id, room)
            VALUES ('Grade 10 - Section A', 1, 'Room 101')
        """)

        # Seed student
        student_pw = hashlib.sha256("student123".encode()).hexdigest()
        cur.execute("""
            INSERT IGNORE INTO students (student_id, full_name, gender, email, class_id)
            VALUES ('STU001', 'Alice Johnson', 'Female', 'alice@student.edu', 1)
        """)
        cur.execute("""
            INSERT IGNORE INTO users (username, password, role, full_name, student_id)
            VALUES ('student', %s, 'student', 'Alice Johnson', 'STU001')
        """, (student_pw,))

        # Seed another student
        cur.execute("""
            INSERT IGNORE INTO students (student_id, full_name, gender, email, class_id)
            VALUES ('STU002', 'Bob Williams', 'Male', 'bob@student.edu', 1)
        """)
        cur.execute("""
            INSERT IGNORE INTO users (username, password, role, full_name, student_id)
            VALUES ('student2', %s, 'student', 'Bob Williams', 'STU002')
        """, (student_pw,))

        # Seed subjects
        cur.execute("""
            INSERT IGNORE INTO subjects (subject_name, subject_code, credits, teacher_id)
            VALUES 
                ('Mathematics', 'MATH101', 4, 1),
                ('Physics', 'PHY101', 4, 1),
                ('English', 'ENG101', 3, 1)
        """)


db = Database()


def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


# ══════════════════════════════════════════════
#  LOGIN CLASS
# ══════════════════════════════════════════════
class LoginPage(ctk.CTkToplevel):
    def __init__(self, master=None, on_login_success=None):
        super().__init__(master)
        self.title("Student Management System - Login")
        self.geometry("420x520")
        self.resizable(False, False)
        self.configure(fg_color=BG_DARK)
        self.on_login_success = on_login_success
        
        # Center the window
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (420 // 2)
        y = (self.winfo_screenheight() // 2) - (520 // 2)
        self.geometry(f"+{x}+{y}")
        
        self.login_result = None
        self.grab_set()
        self._build()
        
    def _build(self):
        # Main container
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(expand=True, fill="both", padx=40, pady=40)
        
        # Logo / Title
        ctk.CTkLabel(main_frame, text="🎓", font=ctk.CTkFont(size=48)).pack(pady=(0, 10))
        ctk.CTkLabel(main_frame, text="Student Management System",
                     font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=PRIMARY).pack(pady=(0, 5))
        ctk.CTkLabel(main_frame, text="Please login to continue",
                     font=ctk.CTkFont(size=12),
                     text_color=SUBTEXT).pack(pady=(0, 30))
        
        # Login form
        form_frame = ctk.CTkFrame(main_frame, fg_color=CARD, corner_radius=12)
        form_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(form_frame, text="Username",
                     text_color=SUBTEXT, anchor="w").pack(padx=20, pady=(20, 5))
        self.username_entry = StyledEntry(form_frame, placeholder="Enter username")
        self.username_entry.pack(padx=20, pady=(0, 15), fill="x")
        
        ctk.CTkLabel(form_frame, text="Password",
                     text_color=SUBTEXT, anchor="w").pack(padx=20, pady=(0, 5))
        self.password_entry = StyledEntry(form_frame, placeholder="Enter password", show="•")
        self.password_entry.pack(padx=20, pady=(0, 20), fill="x")
        
        # Login button
        StyledButton(form_frame, "Login", color=PRIMARY, hover=PRIMARY_H,
                     command=self._do_login).pack(padx=20, pady=(0, 20), fill="x")
        
        # Info box
        info_frame = ctk.CTkFrame(main_frame, fg_color=CARD2, corner_radius=8)
        info_frame.pack(fill="x", pady=(20, 0))
        
        ctk.CTkLabel(info_frame, text="Demo Credentials:",
                     font=ctk.CTkFont(weight="bold"),
                     text_color=TEXT).pack(pady=(10, 5))
        
        creds = [
            ("👑 Admin", "admin / admin123"),
            ("👨‍🏫 Teacher", "teacher / teacher123"),
            ("👨‍🎓 Student 1", "student / student123"),
            ("👩‍🎓 Student 2", "student2 / student123"),
        ]
        
        for role, cred in creds:
            ctk.CTkLabel(info_frame, text=f"{role}: {cred}",
                         text_color=SUBTEXT, font=ctk.CTkFont(size=11)).pack(pady=2)
        
        # Bind Enter key
        self.bind("<Return>", lambda e: self._do_login())
        
    def _do_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        
        if not username or not password:
            messagebox.showwarning("Login Error", "Please enter both username and password", parent=self)
            return
        
        try:
            cur = db.cursor(dictionary=True)
            cur.execute("""
                SELECT id, username, role, full_name, student_id, teacher_id 
                FROM users WHERE username=%s AND password=%s
            """, (username, hash_pw(password)))
            user = cur.fetchone()
            
            if user:
                self.login_result = user
                self.destroy()
                if self.on_login_success:
                    self.on_login_success(user)
            else:
                messagebox.showerror("Login Failed", "Invalid username or password", parent=self)
        except Exception as e:
            messagebox.showerror("Database Error", str(e), parent=self)


# ══════════════════════════════════════════════
#  SCROLLABLE PAGE BASE
# ══════════════════════════════════════════════
class ScrollablePage(ctk.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)

        self._canvas = ctk.CTkCanvas(self, bg=BG_DARK, highlightthickness=0)
        self._scrollbar = ctk.CTkScrollbar(self, command=self._canvas.yview,
                                           fg_color=CARD, button_color=BORDER,
                                           button_hover_color=PRIMARY)
        self._canvas.configure(yscrollcommand=self._scrollbar.set)

        self._scrollbar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self.inner = ctk.CTkFrame(self._canvas, fg_color="transparent")
        self._window_id = self._canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", self._on_inner_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self._canvas.bind_all("<Button-4>", self._on_mousewheel)
        self._canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _on_inner_configure(self, _event):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self._canvas.itemconfig(self._window_id, width=event.width)

    def _on_mousewheel(self, event):
        if not self.winfo_ismapped():
            return
        if event.num == 4:
            self._canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self._canvas.yview_scroll(1, "units")
        else:
            self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def scroll_to_top(self):
        self._canvas.yview_moveto(0)


# ══════════════════════════════════════════════
#  REUSABLE WIDGETS
# ══════════════════════════════════════════════
class StyledEntry(ctk.CTkEntry):
    def __init__(self, master, placeholder="", show="", **kw):
        super().__init__(master,
                         placeholder_text=placeholder,
                         show=show,
                         fg_color=CARD2,
                         border_color=BORDER,
                         text_color=TEXT,
                         placeholder_text_color=SUBTEXT,
                         height=38,
                         **kw)


class StyledButton(ctk.CTkButton):
    def __init__(self, master, text="", color=PRIMARY, hover=PRIMARY_H, **kw):
        super().__init__(master,
                         text=text,
                         fg_color=color,
                         hover_color=hover,
                         text_color=TEXT,
                         height=38,
                         corner_radius=8,
                         **kw)


class SectionLabel(ctk.CTkLabel):
    def __init__(self, master, text, **kw):
        super().__init__(master, text=text,
                         font=ctk.CTkFont(size=18, weight="bold"),
                         text_color=TEXT, **kw)


def styled_table(parent, columns, col_widths=None):
    style = ttk.Style()
    style.theme_use("default")
    style.configure("SMS.Treeview",
                    background=CARD, foreground=TEXT,
                    fieldbackground=CARD, rowheight=32,
                    borderwidth=0, font=("Segoe UI", 10))
    style.configure("SMS.Treeview.Heading",
                    background=CARD2, foreground=SUBTEXT,
                    font=("Segoe UI", 10, "bold"), relief="flat")
    style.map("SMS.Treeview",
              background=[("selected", PRIMARY)],
              foreground=[("selected", TEXT)])

    tree = ttk.Treeview(parent, columns=columns, show="headings",
                        style="SMS.Treeview")
    for i, col in enumerate(columns):
        w = (col_widths[i] if col_widths else 120)
        tree.heading(col, text=col)
        tree.column(col, width=w, anchor="center")

    sb = ctk.CTkScrollbar(parent, command=tree.yview,
                          fg_color=CARD, button_color=BORDER,
                          button_hover_color=PRIMARY)
    tree.configure(yscrollcommand=sb.set)
    return tree, sb


# ══════════════════════════════════════════════
#  DIALOGS
# ══════════════════════════════════════════════
class StudentDialog(ctk.CTkToplevel):
    def __init__(self, master, title="Student", data=None, on_save=None, teacher_mode=False):
        super().__init__(master)
        self.title(title)
        self.geometry("500x580")
        self.resizable(False, False)
        self.configure(fg_color=BG_DARK)
        self.on_save = on_save
        self.teacher_mode = teacher_mode
        self.grab_set()

        ctk.CTkLabel(self, text=title,
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=TEXT).pack(pady=(20, 10))

        form = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12)
        form.pack(fill="both", expand=True, padx=20, pady=10)
        form.columnconfigure(1, weight=1)

        fields = [
            ("Student ID", "student_id"),
            ("Full Name",  "full_name"),
            ("Email",      "email"),
            ("Phone",      "phone"),
            ("Address",    "address"),
        ]

        self.vars = {}
        row = 0
        for label, key in fields:
            ctk.CTkLabel(form, text=label, text_color=SUBTEXT,
                         anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
            e = StyledEntry(form, placeholder=label, width=280)
            e.grid(row=row, column=1, padx=16, pady=6, sticky="ew")
            if data and data.get(key):
                e.insert(0, str(data[key]))
            self.vars[key] = e
            row += 1

        ctk.CTkLabel(form, text="Gender", text_color=SUBTEXT,
                     anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
        self.gender_var = ctk.StringVar(value=data.get("gender", "Male") if data else "Male")
        ctk.CTkOptionMenu(form, variable=self.gender_var,
                          values=["Male", "Female", "Other"],
                          fg_color=CARD2, button_color=PRIMARY,
                          dropdown_fg_color=CARD).grid(row=row, column=1, padx=16, pady=6, sticky="ew")
        row += 1

        ctk.CTkLabel(form, text="Class", text_color=SUBTEXT,
                     anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
        classes = self._load_classes()
        self.class_map = {v: k for k, v in classes}
        class_names = [v for _, v in classes]
        current_class = data.get("class_name", "") if data else ""
        self.class_var = ctk.StringVar(value=current_class if current_class in class_names else (class_names[0] if class_names else ""))
        ctk.CTkOptionMenu(form, variable=self.class_var,
                          values=class_names or ["(no classes)"],
                          fg_color=CARD2, button_color=PRIMARY,
                          dropdown_fg_color=CARD).grid(row=row, column=1, padx=16, pady=6, sticky="ew")
        row += 1

        ctk.CTkLabel(form, text="Status", text_color=SUBTEXT,
                     anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
        self.status_var = ctk.StringVar(value=data.get("status", "Active") if data else "Active")
        ctk.CTkOptionMenu(form, variable=self.status_var,
                          values=["Active", "Inactive"],
                          fg_color=CARD2, button_color=PRIMARY,
                          dropdown_fg_color=CARD).grid(row=row, column=1, padx=16, pady=6, sticky="ew")

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=16)
        StyledButton(btn_row, "Cancel", color=CARD2, hover=CARD,
                     command=self.destroy).pack(side="left", expand=True, padx=4)
        StyledButton(btn_row, "💾  Save",
                     command=self._save).pack(side="left", expand=True, padx=4)

    def _load_classes(self):
        try:
            cur = db.cursor(dictionary=True)
            cur.execute("SELECT id, class_name FROM classes")
            return [(r["id"], r["class_name"]) for r in cur.fetchall()]
        except Exception:
            return []

    def _save(self):
        vals = {k: e.get().strip() for k, e in self.vars.items()}
        if not vals["student_id"] or not vals["full_name"]:
            messagebox.showwarning("Validation", "Student ID and Full Name are required.", parent=self)
            return
        vals["gender"] = self.gender_var.get()
        vals["status"] = self.status_var.get()
        vals["class_id"] = self.class_map.get(self.class_var.get())
        if self.on_save:
            self.on_save(vals)
        self.destroy()


class ScoreDialog(ctk.CTkToplevel):
    def __init__(self, master, student_id, student_name, on_save=None):
        super().__init__(master)
        self.title(f"Scores – {student_name}")
        self.geometry("480x420")
        self.resizable(False, False)
        self.configure(fg_color=BG_DARK)
        self.on_save = on_save
        self.student_id = student_id
        self.grab_set()

        ctk.CTkLabel(self, text=f"📊  Scores: {student_name}",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=TEXT).pack(pady=(20, 10))

        form = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12)
        form.pack(fill="both", expand=True, padx=20, pady=10)
        form.columnconfigure(1, weight=1)
        form.columnconfigure(2, weight=1)

        subjects = self._load_subjects()
        existing = self._load_existing()

        ctk.CTkLabel(form, text="Subject", text_color=SUBTEXT,
                     font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=12, pady=8)
        ctk.CTkLabel(form, text="Midterm (40%)", text_color=SUBTEXT,
                     font=ctk.CTkFont(weight="bold")).grid(row=0, column=1, padx=12, pady=8)
        ctk.CTkLabel(form, text="Final (60%)", text_color=SUBTEXT,
                     font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, padx=12, pady=8)

        self.score_entries = []
        for i, (sid, sname) in enumerate(subjects, 1):
            ctk.CTkLabel(form, text=sname, text_color=TEXT,
                         anchor="w").grid(row=i, column=0, padx=12, pady=4, sticky="w")
            mid_e = StyledEntry(form, placeholder="0-100", width=100)
            fin_e = StyledEntry(form, placeholder="0-100", width=100)
            mid_e.grid(row=i, column=1, padx=8, pady=4)
            fin_e.grid(row=i, column=2, padx=8, pady=4)
            if sid in existing:
                mid_e.insert(0, str(existing[sid]["midterm"]))
                fin_e.insert(0, str(existing[sid]["final"]))
            self.score_entries.append((sid, mid_e, fin_e))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=16)
        StyledButton(btn_row, "Cancel", color=CARD2, hover=CARD,
                     command=self.destroy).pack(side="left", expand=True, padx=4)
        StyledButton(btn_row, "💾  Save Scores",
                     command=self._save).pack(side="left", expand=True, padx=4)

    def _load_subjects(self):
        try:
            cur = db.cursor(dictionary=True)
            cur.execute("SELECT id, subject_name FROM subjects")
            return [(r["id"], r["subject_name"]) for r in cur.fetchall()]
        except Exception:
            return []

    def _load_existing(self):
        try:
            cur = db.cursor(dictionary=True)
            cur.execute("SELECT subject_id, midterm, final FROM scores WHERE student_id=%s",
                        (self.student_id,))
            return {r["subject_id"]: r for r in cur.fetchall()}
        except Exception:
            return {}

    def _save(self):
        rows = []
        for sid, mid_e, fin_e in self.score_entries:
            try:
                mid = float(mid_e.get() or 0)
                fin = float(fin_e.get() or 0)
                if not (0 <= mid <= 100 and 0 <= fin <= 100):
                    raise ValueError
                rows.append((self.student_id, sid, mid, fin))
            except ValueError:
                messagebox.showwarning("Validation", "Scores must be numbers between 0-100.", parent=self)
                return
        if self.on_save:
            self.on_save(rows)
        self.destroy()


# ══════════════════════════════════════════════
#  SIDEBAR NAV
# ══════════════════════════════════════════════
class SidebarButton(ctk.CTkButton):
    def __init__(self, master, text, icon, command, **kw):
        super().__init__(master,
                         text=f"  {icon}  {text}",
                         fg_color="transparent",
                         hover_color=CARD2,
                         text_color=SUBTEXT,
                         anchor="w",
                         height=44,
                         corner_radius=8,
                         font=ctk.CTkFont(size=13),
                         command=command, **kw)
        self._active = False

    def set_active(self, active):
        self._active = active
        if active:
            self.configure(fg_color=PRIMARY, text_color=TEXT)
        else:
            self.configure(fg_color="transparent", text_color=SUBTEXT)


# ══════════════════════════════════════════════
#  PAGE FRAMES
# ══════════════════════════════════════════════
class DashboardPage(ScrollablePage):
    def __init__(self, master, user_data):
        super().__init__(master)
        self.user_data = user_data
        self._build()

    def _build(self):
        SectionLabel(self.inner, "📊  Dashboard").pack(anchor="w", padx=24, pady=(24, 16))
        
        # Welcome message
        role_display = self.user_data['role'].upper()
        ctk.CTkLabel(self.inner, 
                     text=f"Welcome back, {self.user_data['full_name']} ({role_display})",
                     font=ctk.CTkFont(size=14), text_color=SUBTEXT).pack(anchor="w", padx=24, pady=(0, 20))

        stats_row = ctk.CTkFrame(self.inner, fg_color="transparent")
        stats_row.pack(fill="x", padx=24)
        stats_row.columnconfigure((0, 1, 2, 3), weight=1)

        self.stat_cards = {}
        
        if self.user_data['role'] == 'admin':
            specs = [
                ("Total Students", "👨‍🎓", PRIMARY, "students"),
                ("Active",         "✅",  SUCCESS,   "active"),
                ("Classes",        "🏫",  WARNING,   "classes"),
                ("Subjects",       "📚",  "#A855F7", "subjects"),
            ]
        elif self.user_data['role'] == 'teacher':
            specs = [
                ("My Students",    "👨‍🎓", PRIMARY, "students"),
                ("Active",         "✅",  SUCCESS,   "active"),
                ("My Class",       "🏫",  WARNING,   "class"),
                ("Subjects",       "📚",  "#A855F7", "subjects"),
            ]
        else:  # student
            specs = [
                ("My Scores",      "📊", PRIMARY, "scores_count"),
                ("Average",        "📈", SUCCESS, "average"),
                ("Rank",           "🏆", WARNING, "rank"),
                ("Status",         "✅", "#A855F7", "status"),
            ]
        
        for col, (label, icon, color, key) in enumerate(specs):
            card = ctk.CTkFrame(stats_row, fg_color=CARD, corner_radius=14, height=110)
            card.grid(row=0, column=col, padx=8, sticky="ew")
            card.pack_propagate(False)
            ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(size=28)).pack(pady=(16, 2))
            val = ctk.CTkLabel(card, text="–",
                               font=ctk.CTkFont(size=24, weight="bold"),
                               text_color=color)
            val.pack()
            ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=11),
                         text_color=SUBTEXT).pack(pady=(0, 12))
            self.stat_cards[key] = val

        if self.user_data['role'] != 'student':
            table_frame = ctk.CTkFrame(self.inner, fg_color=CARD, corner_radius=14)
            table_frame.pack(fill="both", expand=True, padx=24, pady=20)
            ctk.CTkLabel(table_frame, text="🕑  Recent Students",
                         font=ctk.CTkFont(size=14, weight="bold"),
                         text_color=TEXT).pack(anchor="w", padx=16, pady=12)

            cols = ["ID", "Name", "Class", "Status", "Added"]
            widths = [80, 200, 120, 90, 140]
            self.tree, sb = styled_table(table_frame, cols, widths)
            self.tree.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=(0, 16))
            sb.pack(side="right", fill="y", pady=(0, 16), padx=(0, 8))
        else:
            # Student score view
            score_frame = ctk.CTkFrame(self.inner, fg_color=CARD, corner_radius=14)
            score_frame.pack(fill="both", expand=True, padx=24, pady=20)
            ctk.CTkLabel(score_frame, text="📖  My Academic Performance",
                         font=ctk.CTkFont(size=14, weight="bold"),
                         text_color=TEXT).pack(anchor="w", padx=16, pady=12)
            
            cols = ["Subject", "Midterm (40%)", "Final (60%)", "Total", "Grade"]
            widths = [200, 120, 120, 100, 80]
            self.tree, sb = styled_table(score_frame, cols, widths)
            self.tree.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=(0, 16))
            sb.pack(side="right", fill="y", pady=(0, 16), padx=(0, 8))

        self.refresh()

    def refresh(self):
        try:
            cur = db.cursor(dictionary=True)
            
            if self.user_data['role'] == 'admin':
                cur.execute("SELECT COUNT(*) AS n FROM students")
                self.stat_cards["students"].configure(text=cur.fetchone()["n"])
                cur.execute("SELECT COUNT(*) AS n FROM students WHERE status='Active'")
                self.stat_cards["active"].configure(text=cur.fetchone()["n"])
                cur.execute("SELECT COUNT(*) AS n FROM classes")
                self.stat_cards["classes"].configure(text=cur.fetchone()["n"])
                cur.execute("SELECT COUNT(*) AS n FROM subjects")
                self.stat_cards["subjects"].configure(text=cur.fetchone()["n"])

                cur.execute("""
                    SELECT s.student_id, s.full_name, c.class_name, s.status,
                           DATE_FORMAT(s.created,'%%Y-%%m-%%d') AS created
                    FROM students s
                    LEFT JOIN classes c ON s.class_id=c.id
                    ORDER BY s.created DESC LIMIT 10
                """)
                self.tree.delete(*self.tree.get_children())
                for r in cur.fetchall():
                    self.tree.insert("", "end",
                                     values=(r["student_id"], r["full_name"],
                                             r["class_name"] or "—", r["status"], r["created"]))
                    
            elif self.user_data['role'] == 'teacher':
                # Get teacher's class
                cur.execute("""
                    SELECT c.id, c.class_name FROM classes c
                    JOIN teachers t ON c.teacher_id = t.id
                    WHERE t.id = %s
                """, (self.user_data['teacher_id'],))
                class_info = cur.fetchone()
                
                if class_info:
                    cur.execute("SELECT COUNT(*) AS n FROM students WHERE class_id=%s", (class_info['id'],))
                    self.stat_cards["students"].configure(text=cur.fetchone()["n"])
                    cur.execute("SELECT COUNT(*) AS n FROM students WHERE class_id=%s AND status='Active'", (class_info['id'],))
                    self.stat_cards["active"].configure(text=cur.fetchone()["n"])
                    self.stat_cards["class"].configure(text=class_info['class_name'][:15])
                    cur.execute("SELECT COUNT(*) AS n FROM subjects")
                    self.stat_cards["subjects"].configure(text=cur.fetchone()["n"])
                    
                    cur.execute("""
                        SELECT s.student_id, s.full_name, c.class_name, s.status,
                               DATE_FORMAT(s.created,'%%Y-%%m-%%d') AS created
                        FROM students s
                        LEFT JOIN classes c ON s.class_id=c.id
                        WHERE s.class_id = %s
                        ORDER BY s.created DESC LIMIT 10
                    """, (class_info['id'],))
                    self.tree.delete(*self.tree.get_children())
                    for r in cur.fetchall():
                        self.tree.insert("", "end",
                                         values=(r["student_id"], r["full_name"],
                                                 r["class_name"] or "—", r["status"], r["created"]))
                else:
                    self.stat_cards["students"].configure(text="0")
                    self.stat_cards["active"].configure(text="0")
                    self.stat_cards["class"].configure(text="No Class")
                    self.stat_cards["subjects"].configure(text="0")
                    
            else:  # student
                cur.execute("""
                    SELECT COUNT(id) AS n FROM scores 
                    WHERE student_id = (SELECT id FROM students WHERE student_id=%s)
                """, (self.user_data['student_id'],))
                self.stat_cards["scores_count"].configure(text=cur.fetchone()["n"] or "0")
                
                cur.execute("""
                    SELECT ROUND(AVG(total),1) AS avg FROM scores 
                    WHERE student_id = (SELECT id FROM students WHERE student_id=%s)
                """, (self.user_data['student_id'],))
                avg = cur.fetchone()["avg"] or 0
                self.stat_cards["average"].configure(text=str(avg))
                
                # Get student status
                cur.execute("SELECT status FROM students WHERE student_id=%s", (self.user_data['student_id'],))
                status = cur.fetchone()
                self.stat_cards["status"].configure(text=status['status'] if status else "Active")
                
                # Load scores
                cur.execute("""
                    SELECT sub.subject_name, sc.midterm, sc.final, sc.total, sc.grade
                    FROM scores sc
                    JOIN subjects sub ON sc.subject_id = sub.id
                    WHERE sc.student_id = (SELECT id FROM students WHERE student_id=%s)
                    ORDER BY sub.subject_name
                """, (self.user_data['student_id'],))
                
                self.tree.delete(*self.tree.get_children())
                for r in cur.fetchall():
                    self.tree.insert("", "end",
                                     values=(r["subject_name"], r["midterm"], r["final"], r["total"], r["grade"]))
        except Exception as e:
            pass


class StudentsPage(ScrollablePage):
    def __init__(self, master, user_data):
        super().__init__(master)
        self.user_data = user_data
        self.selected_db_id = None
        self._build()

    def _build(self):
        top = ctk.CTkFrame(self.inner, fg_color="transparent")
        top.pack(fill="x", padx=24, pady=(24, 0))
        SectionLabel(top, "👨‍🎓  Students").pack(side="left")

        btn_bar = ctk.CTkFrame(top, fg_color="transparent")
        btn_bar.pack(side="right")
        
        if self.user_data['role'] == 'admin':
            StyledButton(btn_bar, "➕ Add", command=self._add).pack(side="left", padx=4)
            StyledButton(btn_bar, "✏️ Edit", color=WARNING, hover="#D97706",
                         command=self._edit).pack(side="left", padx=4)
            StyledButton(btn_bar, "🗑 Delete", color=DANGER, hover="#DC2626",
                         command=self._delete).pack(side="left", padx=4)
        elif self.user_data['role'] == 'teacher':
            StyledButton(btn_bar, "📊 Scores", color=SUCCESS, hover="#059669",
                         command=self._scores).pack(side="left", padx=4)

        search_row = ctk.CTkFrame(self.inner, fg_color="transparent")
        search_row.pack(fill="x", padx=24, pady=10)
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh())
        StyledEntry(search_row, placeholder="🔍  Search by name or ID…",
                    textvariable=self.search_var, width=320).pack(side="left")

        table_frame = ctk.CTkFrame(self.inner, fg_color=CARD, corner_radius=14)
        table_frame.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        cols  = ["ID", "Name", "Gender", "Email", "Phone", "Class", "Status"]
        widths = [90, 200, 80, 180, 110, 110, 80]
        self.tree, sb = styled_table(table_frame, cols, widths)
        self.tree.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=16)
        sb.pack(side="right", fill="y", pady=16, padx=(0, 8))
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        self.refresh()

    def _get_class_filter(self):
        """Get class ID filter for teacher role"""
        if self.user_data['role'] == 'teacher':
            try:
                cur = db.cursor(dictionary=True)
                cur.execute("""
                    SELECT c.id FROM classes c
                    JOIN teachers t ON c.teacher_id = t.id
                    WHERE t.id = %s
                """, (self.user_data['teacher_id'],))
                result = cur.fetchone()
                return result['id'] if result else None
            except:
                return None
        return None

    def refresh(self):
        q = self.search_var.get().strip()
        class_filter = self._get_class_filter()
        
        try:
            cur = db.cursor(dictionary=True)
            sql = """
                SELECT s.id, s.student_id, s.full_name, s.gender,
                       s.email, s.phone, c.class_name, s.status
                FROM students s
                LEFT JOIN classes c ON s.class_id=c.id
            """
            params = []
            conditions = []
            
            if class_filter:
                conditions.append("s.class_id = %s")
                params.append(class_filter)
            
            if q:
                conditions.append("(s.student_id LIKE %s OR s.full_name LIKE %s)")
                like = f"%{q}%"
                params.extend([like, like])
            
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            
            sql += " ORDER BY s.created DESC"
            cur.execute(sql, tuple(params))
            
            self.tree.delete(*self.tree.get_children())
            for r in cur.fetchall():
                self.tree.insert("", "end", iid=r["id"],
                                 values=(r["student_id"], r["full_name"], r["gender"],
                                         r["email"] or "—", r["phone"] or "—",
                                         r["class_name"] or "—", r["status"]))
        except Exception as e:
            pass

    def _on_select(self, _):
        sel = self.tree.selection()
        self.selected_db_id = int(sel[0]) if sel else None

    def _add(self):
        StudentDialog(self, "Add Student", on_save=self._do_add)

    def _do_add(self, vals):
        try:
            cur = db.cursor()
            cur.execute("""
                INSERT INTO students (student_id,full_name,gender,email,phone,address,class_id,status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (vals["student_id"], vals["full_name"], vals["gender"],
                  vals["email"], vals["phone"], vals["address"],
                  vals["class_id"], vals["status"]))
            db.commit()
            self.refresh()
        except Error as e:
            messagebox.showerror("Error", str(e))

    def _edit(self):
        if not self.selected_db_id:
            messagebox.showinfo("Select", "Please select a student first.")
            return
        try:
            cur = db.cursor(dictionary=True)
            cur.execute("""
                SELECT s.*, c.class_name FROM students s
                LEFT JOIN classes c ON s.class_id=c.id
                WHERE s.id=%s
            """, (self.selected_db_id,))
            data = cur.fetchone()
        except Error as e:
            messagebox.showerror("Error", str(e)); return
        StudentDialog(self, "Edit Student", data=data,
                      on_save=lambda v: self._do_edit(v))

    def _do_edit(self, vals):
        try:
            cur = db.cursor()
            cur.execute("""
                UPDATE students SET student_id=%s,full_name=%s,gender=%s,
                email=%s,phone=%s,address=%s,class_id=%s,status=%s
                WHERE id=%s
            """, (vals["student_id"], vals["full_name"], vals["gender"],
                  vals["email"], vals["phone"], vals["address"],
                  vals["class_id"], vals["status"], self.selected_db_id))
            db.commit()
            self.refresh()
        except Error as e:
            messagebox.showerror("Error", str(e))

    def _delete(self):
        if not self.selected_db_id:
            messagebox.showinfo("Select", "Please select a student first.")
            return
        if messagebox.askyesno("Confirm Delete", "Delete this student and all their scores?"):
            try:
                cur = db.cursor()
                cur.execute("DELETE FROM students WHERE id=%s", (self.selected_db_id,))
                db.commit()
                self.selected_db_id = None
                self.refresh()
            except Error as e:
                messagebox.showerror("Error", str(e))

    def _scores(self):
        if not self.selected_db_id:
            messagebox.showinfo("Select", "Please select a student first.")
            return
        sel = self.tree.item(self.selected_db_id)["values"]
        name = sel[1] if sel else "Student"
        ScoreDialog(self, self.selected_db_id, name, on_save=self._do_scores)

    def _do_scores(self, rows):
        try:
            cur = db.cursor()
            for student_id, subject_id, mid, fin in rows:
                cur.execute("""
                    INSERT INTO scores (student_id,subject_id,midterm,final)
                    VALUES (%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE midterm=%s, final=%s
                """, (student_id, subject_id, mid, fin, mid, fin))
            db.commit()
            messagebox.showinfo("Saved", "Scores saved successfully!")
        except Error as e:
            messagebox.showerror("Error", str(e))


class ClassesPage(ScrollablePage):
    def __init__(self, master, user_data):
        super().__init__(master)
        self.user_data = user_data
        self.selected_id = None
        self._build()

    def _build(self):
        top = ctk.CTkFrame(self.inner, fg_color="transparent")
        top.pack(fill="x", padx=24, pady=(24, 0))
        SectionLabel(top, "🏫  Classes").pack(side="left")

        if self.user_data['role'] == 'admin':
            btn_bar = ctk.CTkFrame(top, fg_color="transparent")
            btn_bar.pack(side="right")
            StyledButton(btn_bar, "➕ Add", command=self._add).pack(side="left", padx=4)
            StyledButton(btn_bar, "✏️ Edit", color=WARNING, hover="#D97706",
                         command=self._edit).pack(side="left", padx=4)
            StyledButton(btn_bar, "🗑 Delete", color=DANGER, hover="#DC2626",
                         command=self._delete).pack(side="left", padx=4)

        form = ctk.CTkFrame(self.inner, fg_color=CARD, corner_radius=14)
        form.pack(fill="x", padx=24, pady=16)
        form.columnconfigure((1, 3), weight=1)

        ctk.CTkLabel(form, text="Class Name", text_color=SUBTEXT).grid(row=0, column=0, padx=12, pady=12, sticky="w")
        self.name_e = StyledEntry(form, placeholder="e.g. Grade 10 - Section A", state="readonly" if self.user_data['role'] != 'admin' else "normal")
        self.name_e.grid(row=0, column=1, padx=8, pady=12, sticky="ew")

        ctk.CTkLabel(form, text="Teacher", text_color=SUBTEXT).grid(row=0, column=2, padx=12, pady=12, sticky="w")
        self.teacher_e = StyledEntry(form, placeholder="Teacher name", state="readonly" if self.user_data['role'] != 'admin' else "normal")
        self.teacher_e.grid(row=0, column=3, padx=8, pady=12, sticky="ew")

        ctk.CTkLabel(form, text="Room", text_color=SUBTEXT).grid(row=0, column=4, padx=12, pady=12, sticky="w")
        self.room_e = StyledEntry(form, placeholder="Room number", width=100, state="readonly" if self.user_data['role'] != 'admin' else "normal")
        self.room_e.grid(row=0, column=5, padx=8, pady=12, sticky="ew")

        table_frame = ctk.CTkFrame(self.inner, fg_color=CARD, corner_radius=14)
        table_frame.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        cols  = ["ID", "Class Name", "Teacher", "Room", "Created"]
        widths = [60, 200, 200, 100, 160]
        self.tree, sb = styled_table(table_frame, cols, widths)
        self.tree.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=16)
        sb.pack(side="right", fill="y", pady=16, padx=(0, 8))
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        self.refresh()

    def refresh(self):
        try:
            cur = db.cursor(dictionary=True)
            sql = """
                SELECT c.id, c.class_name, t.full_name as teacher, c.room, 
                       DATE_FORMAT(c.created,'%Y-%m-%d') AS created 
                FROM classes c
                LEFT JOIN teachers t ON c.teacher_id = t.id
            """
            if self.user_data['role'] == 'teacher':
                sql += " WHERE c.teacher_id = %s"
                cur.execute(sql, (self.user_data['teacher_id'],))
            else:
                cur.execute(sql)
                
            self.tree.delete(*self.tree.get_children())
            for r in cur.fetchall():
                self.tree.insert("", "end", iid=r["id"],
                                 values=(r["id"], r["class_name"], r["teacher"] or "—",
                                         r["room"] or "—", r["created"]))
        except Exception:
            pass

    def _on_select(self, _):
        sel = self.tree.selection()
        if sel:
            self.selected_id = int(sel[0])
            vals = self.tree.item(self.selected_id)["values"]
            self.name_e.delete(0, "end"); self.name_e.insert(0, vals[1])
            self.teacher_e.delete(0, "end"); self.teacher_e.insert(0, vals[2] if vals[2] != "—" else "")
            self.room_e.delete(0, "end"); self.room_e.insert(0, vals[3] if vals[3] != "—" else "")

    def _add(self):
        name = self.name_e.get().strip()
        if not name:
            messagebox.showwarning("Validation", "Class name is required."); return
        try:
            cur = db.cursor()
            cur.execute("INSERT INTO classes (class_name, teacher, room) VALUES (%s,%s,%s)",
                        (name, self.teacher_e.get().strip() or None, self.room_e.get().strip() or None))
            db.commit()
            self.refresh()
        except Error as e:
            messagebox.showerror("Error", str(e))

    def _edit(self):
        if not self.selected_id:
            messagebox.showinfo("Select", "Select a class first."); return
        name = self.name_e.get().strip()
        if not name:
            messagebox.showwarning("Validation", "Class name is required."); return
        try:
            cur = db.cursor()
            cur.execute("UPDATE classes SET class_name=%s, teacher=%s, room=%s WHERE id=%s",
                        (name, self.teacher_e.get().strip() or None,
                         self.room_e.get().strip() or None, self.selected_id))
            db.commit()
            self.refresh()
        except Error as e:
            messagebox.showerror("Error", str(e))

    def _delete(self):
        if not self.selected_id:
            messagebox.showinfo("Select", "Select a class first."); return
        if messagebox.askyesno("Confirm", "Delete this class?"):
            try:
                cur = db.cursor()
                cur.execute("DELETE FROM classes WHERE id=%s", (self.selected_id,))
                db.commit()
                self.selected_id = None
                self.refresh()
            except Error as e:
                messagebox.showerror("Error", str(e))


class SubjectsPage(ScrollablePage):
    def __init__(self, master, user_data):
        super().__init__(master)
        self.user_data = user_data
        self.selected_id = None
        self._build()

    def _build(self):
        top = ctk.CTkFrame(self.inner, fg_color="transparent")
        top.pack(fill="x", padx=24, pady=(24, 0))
        SectionLabel(top, "📚  Subjects").pack(side="left")

        if self.user_data['role'] == 'admin':
            btn_bar = ctk.CTkFrame(top, fg_color="transparent")
            btn_bar.pack(side="right")
            StyledButton(btn_bar, "➕ Add", command=self._add).pack(side="left", padx=4)
            StyledButton(btn_bar, "✏️ Edit", color=WARNING, hover="#D97706",
                         command=self._edit).pack(side="left", padx=4)
            StyledButton(btn_bar, "🗑 Delete", color=DANGER, hover="#DC2626",
                         command=self._delete).pack(side="left", padx=4)

        form = ctk.CTkFrame(self.inner, fg_color=CARD, corner_radius=14)
        form.pack(fill="x", padx=24, pady=16)
        form.columnconfigure((1, 3, 5), weight=1)

        readonly = self.user_data['role'] != 'admin'
        
        for col, (lbl, attr, ph) in enumerate([
            ("Subject Name", "name_e",    "Mathematics"),
            ("Code",         "code_e",    "MATH101"),
            ("Credits",      "credits_e", "3"),
        ]):
            ctk.CTkLabel(form, text=lbl, text_color=SUBTEXT).grid(row=0, column=col*2, padx=12, pady=12, sticky="w")
            e = StyledEntry(form, placeholder=ph, state="readonly" if readonly else "normal")
            e.grid(row=0, column=col*2+1, padx=8, pady=12, sticky="ew")
            setattr(self, attr, e)

        table_frame = ctk.CTkFrame(self.inner, fg_color=CARD, corner_radius=14)
        table_frame.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        cols  = ["ID", "Subject Name", "Code", "Credits", "Created"]
        widths = [60, 240, 120, 80, 160]
        self.tree, sb = styled_table(table_frame, cols, widths)
        self.tree.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=16)
        sb.pack(side="right", fill="y", pady=16, padx=(0, 8))
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        self.refresh()

    def refresh(self):
        try:
            cur = db.cursor(dictionary=True)
            cur.execute("SELECT id,subject_name,subject_code,credits,DATE_FORMAT(created,'%Y-%m-%d') AS created FROM subjects ORDER BY subject_name")
            self.tree.delete(*self.tree.get_children())
            for r in cur.fetchall():
                self.tree.insert("", "end", iid=r["id"],
                                 values=(r["id"], r["subject_name"], r["subject_code"],
                                         r["credits"], r["created"]))
        except Exception:
            pass

    def _on_select(self, _):
        sel = self.tree.selection()
        if sel:
            self.selected_id = int(sel[0])
            vals = self.tree.item(self.selected_id)["values"]
            for e, v in zip([self.name_e, self.code_e, self.credits_e], [vals[1], vals[2], vals[3]]):
                e.delete(0, "end"); e.insert(0, str(v))

    def _add(self):
        name = self.name_e.get().strip(); code = self.code_e.get().strip()
        if not name or not code:
            messagebox.showwarning("Validation", "Name and Code are required."); return
        try:
            credits = int(self.credits_e.get() or 3)
            cur = db.cursor()
            cur.execute("INSERT INTO subjects (subject_name,subject_code,credits) VALUES (%s,%s,%s)",
                        (name, code, credits))
            db.commit(); self.refresh()
        except Error as e:
            messagebox.showerror("Error", str(e))

    def _edit(self):
        if not self.selected_id:
            messagebox.showinfo("Select", "Select a subject first."); return
        name = self.name_e.get().strip(); code = self.code_e.get().strip()
        if not name or not code:
            messagebox.showwarning("Validation", "Name and Code are required."); return
        try:
            credits = int(self.credits_e.get() or 3)
            cur = db.cursor()
            cur.execute("UPDATE subjects SET subject_name=%s,subject_code=%s,credits=%s WHERE id=%s",
                        (name, code, credits, self.selected_id))
            db.commit(); self.refresh()
        except Error as e:
            messagebox.showerror("Error", str(e))

    def _delete(self):
        if not self.selected_id:
            messagebox.showinfo("Select", "Select a subject first."); return
        if messagebox.askyesno("Confirm", "Delete this subject?"):
            try:
                cur = db.cursor()
                cur.execute("DELETE FROM subjects WHERE id=%s", (self.selected_id,))
                db.commit(); self.selected_id = None; self.refresh()
            except Error as e:
                messagebox.showerror("Error", str(e))


class ReportsPage(ScrollablePage):
    def __init__(self, master, user_data):
        super().__init__(master)
        self.user_data = user_data
        self._build()

    def _build(self):
        SectionLabel(self.inner, "📈  Performance Report").pack(anchor="w", padx=24, pady=(24, 16))

        filter_row = ctk.CTkFrame(self.inner, fg_color=CARD, corner_radius=12)
        filter_row.pack(fill="x", padx=24, pady=(0, 12))
        
        if self.user_data['role'] != 'student':
            ctk.CTkLabel(filter_row, text="Filter by Class:", text_color=SUBTEXT).pack(side="left", padx=16, pady=10)
            self.class_var = ctk.StringVar(value="All Classes")
            self.class_menu = ctk.CTkOptionMenu(filter_row, variable=self.class_var,
                                                values=["All Classes"],
                                                fg_color=CARD2, button_color=PRIMARY,
                                                dropdown_fg_color=CARD,
                                                command=lambda _: self.refresh())
            self.class_menu.pack(side="left", padx=8, pady=10)
        
        StyledButton(filter_row, "🔄 Refresh", command=self.refresh).pack(side="right", padx=16, pady=10)

        table_frame = ctk.CTkFrame(self.inner, fg_color=CARD, corner_radius=14)
        table_frame.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        if self.user_data['role'] == 'student':
            cols = ["Subject", "Midterm (40%)", "Final (60%)", "Total", "Grade"]
            widths = [200, 120, 120, 100, 80]
        else:
            cols = ["Student ID", "Name", "Class", "Subjects", "Avg Score", "Grade", "Result"]
            widths = [100, 200, 110, 80, 100, 70, 80]
            
        self.tree, sb = styled_table(table_frame, cols, widths)
        self.tree.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=16)
        sb.pack(side="right", fill="y", pady=16, padx=(0, 8))

        if self.user_data['role'] != 'student':
            self._load_classes()
        self.refresh()

    def _load_classes(self):
        try:
            cur = db.cursor(dictionary=True)
            if self.user_data['role'] == 'teacher':
                cur.execute("""
                    SELECT c.class_name FROM classes c
                    JOIN teachers t ON c.teacher_id = t.id
                    WHERE t.id = %s
                """, (self.user_data['teacher_id'],))
                names = [r["class_name"] for r in cur.fetchall()]
                self.class_menu.configure(values=names if names else ["No Class"])
                self.class_var.set(names[0] if names else "No Class")
            else:
                cur.execute("SELECT class_name FROM classes ORDER BY class_name")
                names = ["All Classes"] + [r["class_name"] for r in cur.fetchall()]
                self.class_menu.configure(values=names)
        except Exception:
            pass

    def refresh(self):
        if self.user_data['role'] == 'student':
            try:
                cur = db.cursor(dictionary=True)
                cur.execute("""
                    SELECT sub.subject_name, sc.midterm, sc.final, sc.total, sc.grade
                    FROM scores sc
                    JOIN subjects sub ON sc.subject_id = sub.id
                    WHERE sc.student_id = (SELECT id FROM students WHERE student_id=%s)
                    ORDER BY sub.subject_name
                """, (self.user_data['student_id'],))
                
                self.tree.delete(*self.tree.get_children())
                for r in cur.fetchall():
                    self.tree.insert("", "end",
                                     values=(r["subject_name"], r["midterm"], r["final"], r["total"], r["grade"]))
            except Exception:
                pass
            return
            
        cls = self.class_var.get()
        try:
            cur = db.cursor(dictionary=True)
            
            if self.user_data['role'] == 'teacher':
                sql = """
                    SELECT s.student_id, s.full_name, c.class_name,
                           COUNT(sc.id) AS subj_count,
                           ROUND(AVG(sc.total),1) AS avg_score
                    FROM students s
                    LEFT JOIN classes c ON s.class_id = c.id
                    LEFT JOIN scores sc ON sc.student_id = s.id
                    WHERE c.teacher_id = %s
                """
                params = (self.user_data['teacher_id'],)
                if cls != "All Classes" and cls != "No Class":
                    sql += " AND c.class_name = %s"
                    params = (self.user_data['teacher_id'], cls)
                sql += " GROUP BY s.id ORDER BY avg_score DESC"
                cur.execute(sql, params)
            else:
                sql = """
                    SELECT s.student_id, s.full_name, c.class_name,
                           COUNT(sc.id) AS subj_count,
                           ROUND(AVG(sc.total),1) AS avg_score
                    FROM students s
                    LEFT JOIN classes c ON s.class_id = c.id
                    LEFT JOIN scores sc ON sc.student_id = s.id
                """
                params = ()
                if cls != "All Classes":
                    sql += " WHERE c.class_name = %s"
                    params = (cls,)
                sql += " GROUP BY s.id ORDER BY avg_score DESC"
                cur.execute(sql, params)
                
            self.tree.delete(*self.tree.get_children())
            for r in cur.fetchall():
                avg = r["avg_score"] or 0
                grade = ("A+" if avg >= 90 else "A" if avg >= 80 else
                         "B+" if avg >= 75 else "B" if avg >= 70 else
                         "C+" if avg >= 65 else "C" if avg >= 60 else
                         "D" if avg >= 50 else "F")
                result = "✅ Pass" if avg >= 50 else "❌ Fail"
                self.tree.insert("", "end",
                                 values=(r["student_id"], r["full_name"],
                                         r["class_name"] or "—", r["subj_count"] or 0,
                                         avg, grade, result))
        except Exception as e:
            pass


# ══════════════════════════════════════════════
#  MAIN APPLICATION
# ══════════════════════════════════════════════
class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Student Management System")
        self.geometry("1100x700")
        self.minsize(900, 600)
        self.configure(fg_color=BG_DARK)
        self.user_data = None
        self.pages = {}
        self.nav_buttons = {}
        
        # Show login first
        self.show_login()
    
    def show_login(self):
        """Show the login screen"""
        # Clear any existing content
        for widget in self.winfo_children():
            widget.destroy()
        
        # Create login frame
        self.login_frame = ctk.CTkFrame(self, fg_color=BG_DARK)
        self.login_frame.pack(fill="both", expand=True)
        
        # Create login dialog within the frame
        self._create_login_widgets()
    
    def _create_login_widgets(self):
        """Create login widgets in the main window"""
        # Main container
        main_frame = ctk.CTkFrame(self.login_frame, fg_color="transparent")
        main_frame.pack(expand=True, fill="both", padx=40, pady=40)
        
        # Center the content
        center_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        center_frame.pack(expand=True)
        
        # Logo / Title
        ctk.CTkLabel(center_frame, text="🎓", font=ctk.CTkFont(size=48)).pack(pady=(0, 10))
        ctk.CTkLabel(center_frame, text="Student Management System",
                     font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=PRIMARY).pack(pady=(0, 5))
        ctk.CTkLabel(center_frame, text="Please login to continue",
                     font=ctk.CTkFont(size=12),
                     text_color=SUBTEXT).pack(pady=(0, 30))
        
        # Login form
        form_frame = ctk.CTkFrame(center_frame, fg_color=CARD, corner_radius=12)
        form_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(form_frame, text="Username",
                     text_color=SUBTEXT, anchor="w").pack(padx=20, pady=(20, 5))
        self.username_entry = StyledEntry(form_frame, placeholder="Enter username")
        self.username_entry.pack(padx=20, pady=(0, 15), fill="x")
        
        ctk.CTkLabel(form_frame, text="Password",
                     text_color=SUBTEXT, anchor="w").pack(padx=20, pady=(0, 5))
        self.password_entry = StyledEntry(form_frame, placeholder="Enter password", show="•")
        self.password_entry.pack(padx=20, pady=(0, 20), fill="x")
        
        # Login button
        StyledButton(form_frame, "Login", color=PRIMARY, hover=PRIMARY_H,
                     command=self._do_login).pack(padx=20, pady=(0, 20), fill="x")
        
        # Info box
        info_frame = ctk.CTkFrame(center_frame, fg_color=CARD2, corner_radius=8)
        info_frame.pack(fill="x", pady=(20, 0))
        
        ctk.CTkLabel(info_frame, text="Demo Credentials:",
                     font=ctk.CTkFont(weight="bold"),
                     text_color=TEXT).pack(pady=(10, 5))
        
        creds = [
            ("👑 Admin", "admin / admin123"),
            ("👨‍🏫 Teacher", "teacher / teacher123"),
            ("👨‍🎓 Student 1", "student / student123"),
            ("👩‍🎓 Student 2", "student2 / student123"),
        ]
        
        for role, cred in creds:
            ctk.CTkLabel(info_frame, text=f"{role}: {cred}",
                         text_color=SUBTEXT, font=ctk.CTkFont(size=11)).pack(pady=2)
        
        # Bind Enter key
        self.bind("<Return>", lambda e: self._do_login())
        
        # Set focus to username entry
        self.username_entry.focus()
    
    def _do_login(self):
        """Handle login attempt"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        
        if not username or not password:
            messagebox.showwarning("Login Error", "Please enter both username and password")
            return
        
        try:
            cur = db.cursor(dictionary=True)
            cur.execute("""
                SELECT id, username, role, full_name, student_id, teacher_id 
                FROM users WHERE username=%s AND password=%s
            """, (username, hash_pw(password)))
            user = cur.fetchone()
            
            if user:
                self.user_data = user
                self._build_main_app()
            else:
                messagebox.showerror("Login Failed", "Invalid username or password")
        except Exception as e:
            messagebox.showerror("Database Error", str(e))
    
    def _build_main_app(self):
        """Build the main application after successful login"""
        # Clear login frame
        self.login_frame.destroy()
        
        # Build main app UI
        self._build()
    
    def _build(self):
        """Build the main application UI"""
        # ── Sidebar ──────────────────────────────
        sidebar = ctk.CTkFrame(self, width=SIDEBAR_W, fg_color=CARD, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        logo_frame = ctk.CTkFrame(sidebar, fg_color=PRIMARY, height=64, corner_radius=0)
        logo_frame.pack(fill="x")
        logo_frame.pack_propagate(False)
        ctk.CTkLabel(logo_frame, text="🎓  SMS",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=TEXT).pack(expand=True)

        # Navigation items based on role
        if self.user_data['role'] == 'admin':
            nav_items = [
                ("Dashboard", "📊", self._show_dashboard),
                ("Students",  "👨‍🎓", self._show_students),
                ("Classes",   "🏫", self._show_classes),
                ("Subjects",  "📚", self._show_subjects),
                ("Reports",   "📈", self._show_reports),
            ]
        elif self.user_data['role'] == 'teacher':
            nav_items = [
                ("Dashboard", "📊", self._show_dashboard),
                ("Students",  "👨‍🎓", self._show_students),
                ("Classes",   "🏫", self._show_classes),
                ("Reports",   "📈", self._show_reports),
            ]
        else:  # student
            nav_items = [
                ("Dashboard", "📊", self._show_dashboard),
                ("Reports",   "📈", self._show_reports),
            ]

        nav_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav_frame.pack(fill="x", padx=8, pady=16)

        self.nav_buttons = {}
        for name, icon, cmd in nav_items:
            btn = SidebarButton(nav_frame, name, icon, command=cmd)
            btn.pack(fill="x", pady=2)
            self.nav_buttons[name] = btn

        user_frame = ctk.CTkFrame(sidebar, fg_color=CARD2, corner_radius=10)
        user_frame.pack(side="bottom", fill="x", padx=8, pady=12)
        
        role_icon = "👑" if self.user_data['role'] == 'admin' else "👨‍🏫" if self.user_data['role'] == 'teacher' else "👨‍🎓"
        ctk.CTkLabel(user_frame, text=f"{role_icon}  {self.user_data['username']}",
                     text_color=TEXT, font=ctk.CTkFont(weight="bold")).pack(pady=(10, 2))
        ctk.CTkLabel(user_frame, text=f"Role: {self.user_data['role'].title()}",
                     text_color=SUBTEXT, font=ctk.CTkFont(size=11)).pack(pady=(0, 5))
        StyledButton(user_frame, "Logout", color=DANGER, hover="#DC2626",
                     command=self._logout).pack(pady=(4, 10), padx=12, fill="x")

        # ── Content area ─────────────────────────
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(side="left", fill="both", expand=True)

        self.pages = {}
        
        if self.user_data['role'] == 'admin':
            self.pages = {
                "Dashboard": DashboardPage(self.content, self.user_data),
                "Students":  StudentsPage(self.content, self.user_data),
                "Classes":   ClassesPage(self.content, self.user_data),
                "Subjects":  SubjectsPage(self.content, self.user_data),
                "Reports":   ReportsPage(self.content, self.user_data),
            }
        elif self.user_data['role'] == 'teacher':
            self.pages = {
                "Dashboard": DashboardPage(self.content, self.user_data),
                "Students":  StudentsPage(self.content, self.user_data),
                "Classes":   ClassesPage(self.content, self.user_data),
                "Reports":   ReportsPage(self.content, self.user_data),
            }
        else:
            self.pages = {
                "Dashboard": DashboardPage(self.content, self.user_data),
                "Reports":   ReportsPage(self.content, self.user_data),
            }

        self._show_dashboard()

    def _show_page(self, name):
        for p in self.pages.values():
            p.pack_forget()
        for n, b in self.nav_buttons.items():
            b.set_active(n == name)
        page = self.pages[name]
        if hasattr(page, "refresh"):
            page.refresh()
        if hasattr(page, "scroll_to_top"):
            page.scroll_to_top()
        page.pack(fill="both", expand=True)

    def _show_dashboard(self): self._show_page("Dashboard")
    def _show_students(self):  self._show_page("Students")
    def _show_classes(self):   self._show_page("Classes")
    def _show_subjects(self):  self._show_page("Subjects")
    def _show_reports(self):   self._show_page("Reports")

    def _logout(self):
        """Handle logout - clear user data and show login screen"""
        # Clear user data
        self.user_data = None
        self.pages = {}
        self.nav_buttons = {}
        
        # Clear all widgets
        for widget in self.winfo_children():
            widget.destroy()
        
        # Show login screen again
        self.show_login()


if __name__ == "__main__":
    # Connect to database
    ok, msg = db.connect("localhost", "root", "root")
    if not ok:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Database Error",
            f"Cannot connect to MySQL with root/root:\n\n{msg}\n\n"
            "Please check that MySQL is running and your credentials are correct."
        )
        root.destroy()
    else:
        try:
            db.setup_database()
        except Exception as e:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Setup Error", str(e))
            root.destroy()
        else:
            # Create and run the main app (which shows login first)
            app = MainApp()
            app.mainloop()