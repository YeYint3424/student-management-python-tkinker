import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
import mysql.connector
from mysql.connector import Error
import hashlib
from datetime import datetime

# Theme / appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Colours
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

# DATABASE 
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

        # Users table with soft delete (no status field)
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

        # Teachers table with status and soft delete
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

        # Classes table with status and soft delete
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

        # Subjects table with status and soft delete (no teacher_id)
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

        # Students table with status and soft delete
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

        # Seed class 1
        cur.execute("""
            INSERT IGNORE INTO classes (class_name, teacher_id, room, status, is_deleted)
            VALUES ('Grade 10 - Section A', 1, 'Room 101', 'Active', FALSE)
        """)
        
        # Seed class 2 for teacher
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

        # Seed student 1 (class 1)
        student_pw = hashlib.sha256("student123".encode()).hexdigest()
        cur.execute("""
            INSERT IGNORE INTO students (student_id, full_name, gender, email, phone, class_id, status, is_deleted)
            VALUES ('STU001', 'Alice Johnson', 'Female', 'alice@student.edu', '555-0201', 1, 'Active', FALSE)
        """)
        cur.execute("""
            INSERT IGNORE INTO users (username, password, role, full_name, email, student_id, is_deleted)
            VALUES ('student', %s, 'student', 'Alice Johnson', 'alice@student.edu', 'STU001', FALSE)
        """, (student_pw,))

        # Seed student 2 (class 1)
        cur.execute("""
            INSERT IGNORE INTO students (student_id, full_name, gender, email, phone, class_id, status, is_deleted)
            VALUES ('STU002', 'Bob Williams', 'Male', 'bob@student.edu', '555-0202', 1, 'Active', FALSE)
        """)
        cur.execute("""
            INSERT IGNORE INTO users (username, password, role, full_name, email, student_id, is_deleted)
            VALUES ('student2', %s, 'student', 'Bob Williams', 'bob@student.edu', 'STU002', FALSE)
        """, (student_pw,))
        
        # Seed student 3 (class 2)
        cur.execute("""
            INSERT IGNORE INTO students (student_id, full_name, gender, email, phone, class_id, status, is_deleted)
            VALUES ('STU003', 'Charlie Brown', 'Male', 'charlie@student.edu', '555-0203', 2, 'Active', FALSE)
        """)
        cur.execute("""
            INSERT IGNORE INTO users (username, password, role, full_name, email, student_id, is_deleted)
            VALUES ('student3', %s, 'student', 'Charlie Brown', 'charlie@student.edu', 'STU003', FALSE)
        """, (student_pw,))


db = Database()


def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


# ========== REUSABLE WIDGETS ==========
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


# ========== SCROLLABLE PAGE ==========
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


# DIALOGS
class ProfileDialog(ctk.CTkToplevel):
    def __init__(self, master, user_data, on_update=None):
        super().__init__(master)
        self.title("My Profile")
        self.geometry("450x500")
        self.resizable(False, False)
        self.configure(fg_color=BG_DARK)
        self.user_data = user_data
        self.on_update = on_update
        self.grab_set()

        SectionLabel(self, "Profile Settings").pack(pady=(20, 10))

        form = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12)
        form.pack(fill="both", expand=True, padx=20, pady=10)
        form.columnconfigure(1, weight=1)

        fields = [
            ("Full Name", "full_name"),
            ("Email", "email"),
            ("Username", "username"),
        ]
        
        self.vars = {}
        row = 0
        for label, key in fields:
            ctk.CTkLabel(form, text=label, text_color=SUBTEXT,
                         anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
            e = StyledEntry(form, placeholder=label)
            e.grid(row=row, column=1, padx=16, pady=6, sticky="ew")
            if key in user_data and user_data[key]:
                e.insert(0, str(user_data[key]))
            if key == "username":
                e.configure(state="readonly")
            self.vars[key] = e
            row += 1

        ctk.CTkLabel(form, text="Change Password (leave blank to keep current)",
                     text_color=SUBTEXT, font=ctk.CTkFont(size=12)).grid(row=row, column=0, columnspan=2, padx=16, pady=(20, 10), sticky="w")
        row += 1
        
        ctk.CTkLabel(form, text="New Password", text_color=SUBTEXT,
                     anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
        self.new_pw_entry = StyledEntry(form, placeholder="Enter new password", show="*")
        self.new_pw_entry.grid(row=row, column=1, padx=16, pady=6, sticky="ew")
        row += 1
        
        ctk.CTkLabel(form, text="Confirm Password", text_color=SUBTEXT,
                     anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
        self.confirm_pw_entry = StyledEntry(form, placeholder="Confirm new password", show="*")
        self.confirm_pw_entry.grid(row=row, column=1, padx=16, pady=6, sticky="ew")
        row += 1

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=16)
        StyledButton(btn_row, "Cancel", color=CARD2, hover=CARD,
                     command=self.destroy).pack(side="left", expand=True, padx=4)
        StyledButton(btn_row, "Update Profile",
                     command=self._save).pack(side="left", expand=True, padx=4)

    def _save(self):
        vals = {k: e.get().strip() for k, e in self.vars.items()}
        if not vals["full_name"]:
            messagebox.showwarning("Validation", "Full name is required.", parent=self)
            return
        
        new_pw = self.new_pw_entry.get()
        confirm_pw = self.confirm_pw_entry.get()
        
        if new_pw or confirm_pw:
            if new_pw != confirm_pw:
                messagebox.showwarning("Validation", "Passwords do not match.", parent=self)
                return
            if len(new_pw) < 4:
                messagebox.showwarning("Validation", "Password must be at least 4 characters.", parent=self)
                return
            vals["new_password"] = hash_pw(new_pw)
        
        if self.on_update:
            self.on_update(vals)
        self.destroy()


class StudentDialog(ctk.CTkToplevel):
    def __init__(self, master, title="Student", data=None, on_save=None, teacher_mode=False, is_admin=False):
        super().__init__(master)
        self.title(title)
        self.geometry("500x800")
        self.resizable(False, False)
        self.configure(fg_color=BG_DARK)
        self.on_save = on_save
        self.teacher_mode = teacher_mode
        self.is_admin = is_admin
        self.is_edit = data is not None
        self.grab_set()

        SectionLabel(self, title).pack(pady=(20, 10))

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

        # Username field (required for login)
        ctk.CTkLabel(form, text="Username (required for login)", text_color=SUBTEXT,
                     anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
        self.username_entry = StyledEntry(form, placeholder="Enter username", width=280)
        self.username_entry.grid(row=row, column=1, padx=16, pady=6, sticky="ew")
        if data and data.get("username"):
            self.username_entry.insert(0, str(data["username"]))
        row += 1

        ctk.CTkLabel(form, text="Gender", text_color=SUBTEXT,
                     anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
        self.gender_var = ctk.StringVar(value=data.get("gender", "Male") if data else "Male")
        ctk.CTkOptionMenu(form, variable=self.gender_var,
                          values=["Male", "Female", "Other"],
                          fg_color=CARD2, button_color=PRIMARY,
                          dropdown_fg_color=CARD).grid(row=row, column=1, padx=16, pady=6, sticky="ew")
        row += 1
        
        ctk.CTkLabel(form, text="Date of Birth", text_color=SUBTEXT,
                     anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
        self.dob_entry = StyledEntry(form, placeholder="YYYY-MM-DD", width=280)
        self.dob_entry.grid(row=row, column=1, padx=16, pady=6, sticky="ew")
        if data and data.get("dob"):
            self.dob_entry.insert(0, str(data["dob"]))
        row += 1

        ctk.CTkLabel(form, text="Class", text_color=SUBTEXT,
                     anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
        classes = self._load_classes()
        self.class_map = {v: k for k, v in classes}
        class_names = [v for _, v in classes]
        current_class = data.get("class_name", "") if data else ""
        self.class_var = ctk.StringVar(value=current_class if current_class in class_names else (class_names[0] if class_names else ""))
        self.class_menu = ctk.CTkOptionMenu(form, variable=self.class_var,
                                            values=class_names or ["(no classes)"],
                                            fg_color=CARD2, button_color=PRIMARY,
                                            dropdown_fg_color=CARD)
        self.class_menu.grid(row=row, column=1, padx=16, pady=6, sticky="ew")
        row += 1

        # Status field
        ctk.CTkLabel(form, text="Status", text_color=SUBTEXT,
                     anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
        self.status_var = ctk.StringVar(value=data.get("status", "Active") if data else "Active")
        ctk.CTkOptionMenu(form, variable=self.status_var,
                          values=["Active", "Inactive"],
                          fg_color=CARD2, button_color=PRIMARY,
                          dropdown_fg_color=CARD).grid(row=row, column=1, padx=16, pady=6, sticky="ew")
        row += 1

        # Password field (required for new students)
        if not self.is_edit:
            ctk.CTkLabel(form, text="Password (required)", text_color=SUBTEXT,
                         anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
            self.password_entry = StyledEntry(form, placeholder="Enter password", show="*", width=280)
            self.password_entry.grid(row=row, column=1, padx=16, pady=6, sticky="ew")
            row += 1
            
            ctk.CTkLabel(form, text="Confirm Password (required)", text_color=SUBTEXT,
                         anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
            self.confirm_password_entry = StyledEntry(form, placeholder="Confirm password", show="*", width=280)
            self.confirm_password_entry.grid(row=row, column=1, padx=16, pady=6, sticky="ew")
            row += 1
        elif self.is_admin:
            # In edit mode, admin can optionally change password
            ctk.CTkLabel(form, text="New Password (optional)", text_color=SUBTEXT,
                         anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
            self.password_entry = StyledEntry(form, placeholder="Leave blank to keep current", show="*", width=280)
            self.password_entry.grid(row=row, column=1, padx=16, pady=6, sticky="ew")
            row += 1
            
            ctk.CTkLabel(form, text="Confirm Password", text_color=SUBTEXT,
                         anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
            self.confirm_password_entry = StyledEntry(form, placeholder="Confirm new password", show="*", width=280)
            self.confirm_password_entry.grid(row=row, column=1, padx=16, pady=6, sticky="ew")
            row += 1

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=16)
        StyledButton(btn_row, "Cancel", color=CARD2, hover=CARD,
                     command=self.destroy).pack(side="left", expand=True, padx=4)
        StyledButton(btn_row, "Save Student",
                     command=self._save).pack(side="left", expand=True, padx=4)

    def _load_classes(self):
        try:
            cur = db.cursor(dictionary=True)
            cur.execute("SELECT id, class_name FROM classes WHERE is_deleted = FALSE AND status = 'Active'")
            return [(r["id"], r["class_name"]) for r in cur.fetchall()]
        except Exception:
            return []

    def _save(self):
        vals = {k: e.get().strip() for k, e in self.vars.items()}
        
        # Validation
        if not vals["student_id"] or not vals["full_name"]:
            messagebox.showwarning("Validation", "Student ID and Full Name are required.", parent=self)
            return
        
        # Username validation
        username = self.username_entry.get().strip()
        if not username:
            messagebox.showwarning("Validation", "Username is required for student accounts.", parent=self)
            return
        
        vals["username"] = username
        
        # Password validation for new student
        if not self.is_edit:
            password = self.password_entry.get() if hasattr(self, 'password_entry') else ""
            confirm = self.confirm_password_entry.get() if hasattr(self, 'confirm_password_entry') else ""
            
            if not password:
                messagebox.showwarning("Validation", "Password is required for new student accounts.", parent=self)
                return
            if password != confirm:
                messagebox.showwarning("Validation", "Passwords do not match.", parent=self)
                return
            if len(password) < 4:
                messagebox.showwarning("Validation", "Password must be at least 4 characters.", parent=self)
                return
            vals["password"] = hash_pw(password)
        
        # Password validation for edit (admin only)
        elif self.is_admin and hasattr(self, 'password_entry'):
            password = self.password_entry.get()
            confirm = self.confirm_password_entry.get()
            if password or confirm:
                if password != confirm:
                    messagebox.showwarning("Validation", "Passwords do not match.", parent=self)
                    return
                if len(password) < 4:
                    messagebox.showwarning("Validation", "Password must be at least 4 characters.", parent=self)
                    return
                vals["new_password"] = hash_pw(password)
        
        vals["gender"] = self.gender_var.get()
        vals["status"] = self.status_var.get()
        vals["class_id"] = self.class_map.get(self.class_var.get())
        vals["dob"] = self.dob_entry.get().strip() or None
        
        if self.on_save:
            self.on_save(vals)
        self.destroy()

class TeacherDialog(ctk.CTkToplevel):
    def __init__(self, master, title="Teacher", data=None, on_save=None, is_admin=False):
        super().__init__(master)
        self.title(title)
        self.geometry("500x700")
        self.resizable(False, False)
        self.configure(fg_color=BG_DARK)
        self.on_save = on_save
        self.is_admin = is_admin
        self.is_edit = data is not None
        self.grab_set()

        SectionLabel(self, title).pack(pady=(20, 10))

        form = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12)
        form.pack(fill="both", expand=True, padx=20, pady=10)
        form.columnconfigure(1, weight=1)

        fields = [
            ("Teacher ID", "teacher_id"),
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

        ctk.CTkLabel(form, text="Status", text_color=SUBTEXT,
                     anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
        self.status_var = ctk.StringVar(value=data.get("status", "Active") if data else "Active")
        ctk.CTkOptionMenu(form, variable=self.status_var,
                          values=["Active", "Inactive"],
                          fg_color=CARD2, button_color=PRIMARY,
                          dropdown_fg_color=CARD).grid(row=row, column=1, padx=16, pady=6, sticky="ew")
        row += 1

        ctk.CTkLabel(form, text="Username (required for login)", text_color=SUBTEXT,
                     anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
        self.username_entry = StyledEntry(form, placeholder="username", width=280)
        self.username_entry.grid(row=row, column=1, padx=16, pady=6, sticky="ew")
        if data and data.get("username"):
            self.username_entry.insert(0, str(data["username"]))
        row += 1
        
        # Password field
        if not self.is_edit:
            ctk.CTkLabel(form, text="Password (required)", text_color=SUBTEXT,
                         anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
            self.password_entry = StyledEntry(form, placeholder="Enter password", show="*", width=280)
            self.password_entry.grid(row=row, column=1, padx=16, pady=6, sticky="ew")
            row += 1
            
            ctk.CTkLabel(form, text="Confirm Password (required)", text_color=SUBTEXT,
                         anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
            self.confirm_password_entry = StyledEntry(form, placeholder="Confirm password", show="*", width=280)
            self.confirm_password_entry.grid(row=row, column=1, padx=16, pady=6, sticky="ew")
            row += 1
        elif self.is_admin:
            ctk.CTkLabel(form, text="New Password (optional)", text_color=SUBTEXT,
                         anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
            self.password_entry = StyledEntry(form, placeholder="Leave blank to keep current", show="*", width=280)
            self.password_entry.grid(row=row, column=1, padx=16, pady=6, sticky="ew")
            row += 1
            
            ctk.CTkLabel(form, text="Confirm Password", text_color=SUBTEXT,
                         anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
            self.confirm_password_entry = StyledEntry(form, placeholder="Confirm new password", show="*", width=280)
            self.confirm_password_entry.grid(row=row, column=1, padx=16, pady=6, sticky="ew")
            row += 1

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=16)
        StyledButton(btn_row, "Cancel", color=CARD2, hover=CARD,
                     command=self.destroy).pack(side="left", expand=True, padx=4)
        StyledButton(btn_row, "Save Teacher",
                     command=self._save).pack(side="left", expand=True, padx=4)

    def _save(self):
        vals = {k: e.get().strip() for k, e in self.vars.items()}
        
        # Required fields validation
        if not vals["teacher_id"] or not vals["full_name"]:
            messagebox.showwarning("Validation", "Teacher ID and Full Name are required.", parent=self)
            return
        
        # Username validation
        username = self.username_entry.get().strip()
        if not username:
            messagebox.showwarning("Validation", "Username is required for teacher accounts.", parent=self)
            return
        
        vals["username"] = username
        vals["status"] = self.status_var.get()
        
        # Password validation for new teacher
        if not self.is_edit:
            password = self.password_entry.get() if hasattr(self, 'password_entry') else ""
            confirm = self.confirm_password_entry.get() if hasattr(self, 'confirm_password_entry') else ""
            
            if not password:
                messagebox.showwarning("Validation", "Password is required for new teacher accounts.", parent=self)
                return
            if password != confirm:
                messagebox.showwarning("Validation", "Passwords do not match.", parent=self)
                return
            if len(password) < 4:
                messagebox.showwarning("Validation", "Password must be at least 4 characters.", parent=self)
                return
            vals["password"] = hash_pw(password)
        
        # Password validation for edit (admin only)
        elif self.is_admin and hasattr(self, 'password_entry'):
            password = self.password_entry.get()
            confirm = self.confirm_password_entry.get()
            if password or confirm:
                if password != confirm:
                    messagebox.showwarning("Validation", "Passwords do not match.", parent=self)
                    return
                if len(password) < 4:
                    messagebox.showwarning("Validation", "Password must be at least 4 characters.", parent=self)
                    return
                vals["new_password"] = hash_pw(password)
        
        if self.on_save:
            self.on_save(vals)
        self.destroy()


class ClassDialog(ctk.CTkToplevel):
    def __init__(self, master, title="Class", data=None, on_save=None):
        super().__init__(master)
        self.title(title)
        self.geometry("500x650")
        self.resizable(False, False)
        self.configure(fg_color=BG_DARK)
        self.on_save = on_save
        self.data = data
        self.grab_set()

        SectionLabel(self, title).pack(pady=(20, 10))

        form = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12)
        form.pack(fill="both", expand=True, padx=20, pady=10)
        form.columnconfigure(1, weight=1)

        ctk.CTkLabel(form, text="Class Name (required)", text_color=SUBTEXT,
                     anchor="w").grid(row=0, column=0, padx=16, pady=6, sticky="w")
        self.name_entry = StyledEntry(form, placeholder="e.g. Grade 10 - Section A", width=280)
        self.name_entry.grid(row=0, column=1, padx=16, pady=6, sticky="ew")
        if data:
            self.name_entry.insert(0, data.get("class_name", ""))
        
        ctk.CTkLabel(form, text="Room (required)", text_color=SUBTEXT,
                     anchor="w").grid(row=1, column=0, padx=16, pady=6, sticky="w")
        self.room_entry = StyledEntry(form, placeholder="Room number", width=280)
        self.room_entry.grid(row=1, column=1, padx=16, pady=6, sticky="ew")
        if data:
            self.room_entry.insert(0, data.get("room", ""))
        
        ctk.CTkLabel(form, text="Teacher", text_color=SUBTEXT,
                     anchor="w").grid(row=2, column=0, padx=16, pady=6, sticky="w")
        teachers = self._load_teachers()
        self.teacher_map = {v: k for k, v in teachers}
        teacher_names = [v for _, v in teachers]
        current_teacher = data.get("teacher", "") if data else ""
        self.teacher_var = ctk.StringVar(value=current_teacher if current_teacher in teacher_names else (teacher_names[0] if teacher_names else "None"))
        self.teacher_menu = ctk.CTkOptionMenu(form, variable=self.teacher_var,
                                              values=teacher_names or ["None"],
                                              fg_color=CARD2, button_color=PRIMARY,
                                              dropdown_fg_color=CARD)
        self.teacher_menu.grid(row=2, column=1, padx=16, pady=6, sticky="ew")
        
        ctk.CTkLabel(form, text="Subjects (at least one required)", text_color=SUBTEXT,
                     font=ctk.CTkFont(weight="bold")).grid(row=3, column=0, columnspan=2, padx=16, pady=(20, 10), sticky="w")
        
        subjects = self._load_subjects()
        self.subject_vars = {}
        
        subject_frame = ctk.CTkFrame(form, fg_color=CARD2, corner_radius=8)
        subject_frame.grid(row=4, column=0, columnspan=2, padx=16, pady=6, sticky="ew")
        
        existing_subjects = self._get_class_subjects() if data else []
        
        for i, (sid, sname) in enumerate(subjects):
            var = ctk.BooleanVar(value=sid in existing_subjects)
            cb = ctk.CTkCheckBox(subject_frame, text=sname, variable=var,
                                 fg_color=PRIMARY, hover_color=PRIMARY_H,
                                 text_color=TEXT)
            cb.pack(anchor="w", padx=16, pady=4)
            self.subject_vars[sid] = var

        ctk.CTkLabel(form, text="Status", text_color=SUBTEXT,
                     anchor="w").grid(row=5, column=0, padx=16, pady=6, sticky="w")
        self.status_var = ctk.StringVar(value=data.get("status", "Active") if data else "Active")
        ctk.CTkOptionMenu(form, variable=self.status_var,
                          values=["Active", "Inactive"],
                          fg_color=CARD2, button_color=PRIMARY,
                          dropdown_fg_color=CARD).grid(row=5, column=1, padx=16, pady=6, sticky="ew")

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=16)
        StyledButton(btn_row, "Cancel", color=CARD2, hover=CARD,
                     command=self.destroy).pack(side="left", expand=True, padx=4)
        StyledButton(btn_row, "Save Class",
                     command=self._save).pack(side="left", expand=True, padx=4)

    def _load_teachers(self):
        try:
            cur = db.cursor(dictionary=True)
            cur.execute("SELECT id, full_name FROM teachers WHERE is_deleted = FALSE AND status = 'Active'")
            return [("None", "None")] + [(r["id"], r["full_name"]) for r in cur.fetchall()]
        except Exception:
            return [("None", "None")]

    def _load_subjects(self):
        try:
            cur = db.cursor(dictionary=True)
            cur.execute("SELECT id, subject_name FROM subjects WHERE is_deleted = FALSE AND status = 'Active' ORDER BY subject_name")
            return [(r["id"], r["subject_name"]) for r in cur.fetchall()]
        except Exception:
            return []

    def _get_class_subjects(self):
        if not self.data:
            return []
        try:
            cur = db.cursor(dictionary=True)
            cur.execute("SELECT subject_id FROM class_subjects WHERE class_id=%s", (self.data.get("id"),))
            return [r["subject_id"] for r in cur.fetchall()]
        except Exception:
            return []

    def _save(self):
        name = self.name_entry.get().strip()
        room = self.room_entry.get().strip()
        
        if not name:
            messagebox.showwarning("Validation", "Class name is required.", parent=self)
            return
        
        if not room:
            messagebox.showwarning("Validation", "Room number is required.", parent=self)
            return
        
        selected_subjects = [sid for sid, var in self.subject_vars.items() if var.get()]
        
        if not selected_subjects:
            messagebox.showwarning("Validation", "At least one subject is required for the class.", parent=self)
            return
        
        teacher_id = self.teacher_map.get(self.teacher_var.get())
        if teacher_id == "None":
            teacher_id = None
        
        if self.on_save:
            self.on_save({
                "class_name": name,
                "teacher_id": teacher_id,
                "room": room,
                "status": self.status_var.get(),
                "subjects": selected_subjects,
                "class_id": self.data.get("id") if self.data else None
            })
        self.destroy()


class SubjectDialog(ctk.CTkToplevel):
    def __init__(self, master, title="Subject", data=None, on_save=None):
        super().__init__(master)
        self.title(title)
        self.geometry("500x480")
        self.resizable(False, False)
        self.configure(fg_color=BG_DARK)
        self.on_save = on_save
        self.data = data
        self.grab_set()

        SectionLabel(self, title).pack(pady=(20, 10))

        form = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12)
        form.pack(fill="both", expand=True, padx=20, pady=10)
        form.columnconfigure(1, weight=1)

        ctk.CTkLabel(form, text="Subject Name (required)", text_color=SUBTEXT,
                     anchor="w").grid(row=0, column=0, padx=16, pady=6, sticky="w")
        self.name_entry = StyledEntry(form, placeholder="e.g. Mathematics", width=280)
        self.name_entry.grid(row=0, column=1, padx=16, pady=6, sticky="ew")
        if data:
            self.name_entry.insert(0, data.get("subject_name", ""))
        
        ctk.CTkLabel(form, text="Subject Code (required)", text_color=SUBTEXT,
                     anchor="w").grid(row=1, column=0, padx=16, pady=6, sticky="w")
        self.code_entry = StyledEntry(form, placeholder="e.g. MATH101", width=280)
        self.code_entry.grid(row=1, column=1, padx=16, pady=6, sticky="ew")
        if data:
            self.code_entry.insert(0, data.get("subject_code", ""))
        
        ctk.CTkLabel(form, text="Credits (required)", text_color=SUBTEXT,
                     anchor="w").grid(row=2, column=0, padx=16, pady=6, sticky="w")
        self.credits_entry = StyledEntry(form, placeholder="3", width=280)
        self.credits_entry.grid(row=2, column=1, padx=16, pady=6, sticky="ew")
        if data:
            self.credits_entry.insert(0, str(data.get("credits", "3")))
        
        ctk.CTkLabel(form, text="Status", text_color=SUBTEXT,
                     anchor="w").grid(row=3, column=0, padx=16, pady=6, sticky="w")
        self.status_var = ctk.StringVar(value=data.get("status", "Active") if data else "Active")
        ctk.CTkOptionMenu(form, variable=self.status_var,
                          values=["Active", "Inactive"],
                          fg_color=CARD2, button_color=PRIMARY,
                          dropdown_fg_color=CARD).grid(row=3, column=1, padx=16, pady=6, sticky="ew")

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=16)
        StyledButton(btn_row, "Cancel", color=CARD2, hover=CARD,
                     command=self.destroy).pack(side="left", expand=True, padx=4)
        StyledButton(btn_row, "Save Subject",
                     command=self._save).pack(side="left", expand=True, padx=4)

    def _save(self):
        name = self.name_entry.get().strip()
        code = self.code_entry.get().strip()
        credits_str = self.credits_entry.get().strip()
        
        if not name:
            messagebox.showwarning("Validation", "Subject name is required.", parent=self)
            return
        
        if not code:
            messagebox.showwarning("Validation", "Subject code is required.", parent=self)
            return
        
        if not credits_str:
            messagebox.showwarning("Validation", "Credits are required.", parent=self)
            return
        
        try:
            credits = int(credits_str)
            if credits <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Validation", "Credits must be a positive number.", parent=self)
            return
        
        if self.on_save:
            self.on_save({
                "subject_name": name,
                "subject_code": code,
                "credits": credits,
                "status": self.status_var.get(),
                "subject_id": self.data.get("id") if self.data else None
            })
        self.destroy()


class ScoreDialog(ctk.CTkToplevel):
    def __init__(self, master, student_id, student_name, on_save=None):
        super().__init__(master)
        self.title(f"Scores - {student_name}")
        self.geometry("480x420")
        self.resizable(False, False)
        self.configure(fg_color=BG_DARK)
        self.on_save = on_save
        self.student_id = student_id
        self.grab_set()

        SectionLabel(self, f"Scores: {student_name}").pack(pady=(20, 10))

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
        StyledButton(btn_row, "Save Scores",
                     command=self._save).pack(side="left", expand=True, padx=4)

    def _load_subjects(self):
        try:
            cur = db.cursor(dictionary=True)
            cur.execute("""
                SELECT DISTINCT s.id, s.subject_name 
                FROM subjects s
                JOIN class_subjects cs ON s.id = cs.subject_id
                JOIN students st ON st.class_id = cs.class_id
                WHERE st.id = %s AND s.is_deleted = FALSE AND s.status = 'Active'
            """, (self.student_id,))
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


# ========== PAGE FRAMES ==========
class DashboardPage(ScrollablePage):
    def __init__(self, master, user_data):
        super().__init__(master)
        self.user_data = user_data
        self._build()

    def _build(self):
        SectionLabel(self.inner, "Dashboard").pack(anchor="w", padx=24, pady=(24, 16))
        
        ctk.CTkLabel(self.inner, 
                     text=f"Welcome back, {self.user_data['full_name']} ({self.user_data['role'].upper()})",
                     font=ctk.CTkFont(size=14), text_color=SUBTEXT).pack(anchor="w", padx=24, pady=(0, 20))

        stats_row = ctk.CTkFrame(self.inner, fg_color="transparent")
        stats_row.pack(fill="x", padx=24)
        stats_row.columnconfigure((0, 1, 2, 3), weight=1)

        self.stat_cards = {}
        
        if self.user_data['role'] == 'admin':
            specs = [
                ("Total Students", PRIMARY, "students"),
                ("Active Students", SUCCESS, "active"),
                ("Active Teachers", "#A855F7", "teachers"),
                ("Active Subjects", WARNING, "subjects"),
            ]
        elif self.user_data['role'] == 'teacher':
            specs = [
                ("My Students", PRIMARY, "students"),
                ("Active Students", SUCCESS, "active"),
                ("My Classes", WARNING, "class"),
                ("My Subjects", "#A855F7", "subjects"),
            ]
        else:
            specs = [
                ("My Scores", PRIMARY, "scores_count"),
                ("Average", SUCCESS, "average"),
                ("Rank", WARNING, "rank"),
                ("Status", "#A855F7", "status"),
            ]
        
        for col, (label, color, key) in enumerate(specs):
            card = ctk.CTkFrame(stats_row, fg_color=CARD, corner_radius=14, height=110)
            card.grid(row=0, column=col, padx=8, sticky="ew")
            card.pack_propagate(False)
            
            val = ctk.CTkLabel(card, text="-",
                               font=ctk.CTkFont(size=24, weight="bold"),
                               text_color=color)
            val.pack(pady=(20, 2))
            ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=11),
                         text_color=SUBTEXT).pack(pady=(0, 12))
            self.stat_cards[key] = val

        if self.user_data['role'] != 'student':
            table_frame = ctk.CTkFrame(self.inner, fg_color=CARD, corner_radius=14)
            table_frame.pack(fill="both", expand=True, padx=24, pady=20)
            
            ctk.CTkLabel(table_frame, text="Recent Students",
                         font=ctk.CTkFont(size=14, weight="bold"),
                         text_color=TEXT).pack(anchor="w", padx=16, pady=12)

            cols = ["ID", "Name", "Class", "Status", "Added Date"]
            widths = [80, 200, 120, 90, 100]
            self.tree, sb = styled_table(table_frame, cols, widths)
            self.tree.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=(0, 16))
            sb.pack(side="right", fill="y", pady=(0, 16), padx=(0, 8))
        else:
            score_frame = ctk.CTkFrame(self.inner, fg_color=CARD, corner_radius=14)
            score_frame.pack(fill="both", expand=True, padx=24, pady=20)
            
            ctk.CTkLabel(score_frame, text="My Academic Performance",
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
                cur.execute("SELECT COUNT(*) AS n FROM students WHERE is_deleted = FALSE")
                self.stat_cards["students"].configure(text=cur.fetchone()["n"])
                cur.execute("SELECT COUNT(*) AS n FROM students WHERE status='Active' AND is_deleted = FALSE")
                self.stat_cards["active"].configure(text=cur.fetchone()["n"])
                cur.execute("SELECT COUNT(*) AS n FROM teachers WHERE is_deleted = FALSE AND status='Active'")
                self.stat_cards["teachers"].configure(text=cur.fetchone()["n"])
                cur.execute("SELECT COUNT(*) AS n FROM subjects WHERE is_deleted = FALSE AND status='Active'")
                self.stat_cards["subjects"].configure(text=cur.fetchone()["n"])

                cur.execute("""
                    SELECT s.student_id, s.full_name, c.class_name, s.status,
                           DATE(s.created) AS created
                    FROM students s
                    LEFT JOIN classes c ON s.class_id=c.id
                    WHERE s.is_deleted = FALSE
                    ORDER BY s.created DESC LIMIT 10
                """)
                self.tree.delete(*self.tree.get_children())
                for r in cur.fetchall():
                    created_date = str(r["created"]) if r["created"] else "-"
                    self.tree.insert("", "end",
                                     values=(r["student_id"], r["full_name"],
                                             r["class_name"] or "-", r["status"], created_date))
                    
            elif self.user_data['role'] == 'teacher':
                # Get ALL classes for this teacher
                cur.execute("""
                    SELECT c.id, c.class_name, COUNT(s.id) as student_count,
                        SUM(CASE WHEN s.status = 'Active' THEN 1 ELSE 0 END) as active_count
                    FROM classes c
                    JOIN teachers t ON c.teacher_id = t.id
                    LEFT JOIN students s ON s.class_id = c.id AND s.is_deleted = FALSE
                    WHERE t.id = %s AND c.is_deleted = FALSE AND c.status = 'Active'
                    GROUP BY c.id
                """, (self.user_data['teacher_id'],))
                
                teacher_classes = cur.fetchall()
                
                if teacher_classes:
                    # Calculate totals across all classes
                    total_students = sum(c['student_count'] or 0 for c in teacher_classes)
                    total_active = sum(c['active_count'] or 0 for c in teacher_classes)
                    # Show count of classes instead of class names
                    class_count = len(teacher_classes)
                    
                    self.stat_cards["students"].configure(text=str(total_students))
                    self.stat_cards["active"].configure(text=str(total_active))
                    self.stat_cards["class"].configure(text=str(class_count))  # Changed to show number only
                    
                    # Get subject count (distinct subjects across all teacher's classes)
                    cur.execute("""
                        SELECT COUNT(DISTINCT s.id) as n
                        FROM subjects s
                        JOIN class_subjects cs ON s.id = cs.subject_id
                        JOIN classes c ON cs.class_id = c.id
                        WHERE c.teacher_id = %s AND c.is_deleted = FALSE 
                        AND s.is_deleted = FALSE AND s.status = 'Active'
                    """, (self.user_data['teacher_id'],))
                    self.stat_cards["subjects"].configure(text=cur.fetchone()["n"] or "0")
                    
                    # Get recent students from ALL teacher's classes
                    cur.execute("""
                        SELECT s.student_id, s.full_name, c.class_name, s.status,
                            DATE(s.created) AS created
                        FROM students s
                        LEFT JOIN classes c ON s.class_id = c.id
                        WHERE c.teacher_id = %s AND s.is_deleted = FALSE
                        ORDER BY s.created DESC LIMIT 10
                    """, (self.user_data['teacher_id'],))
                    
                    self.tree.delete(*self.tree.get_children())
                    for r in cur.fetchall():
                        created_date = str(r["created"]) if r["created"] else "-"
                        self.tree.insert("", "end",
                                    values=(r["student_id"], r["full_name"],
                                            r["class_name"] or "-", r["status"], created_date))
                else:
                    self.stat_cards["students"].configure(text="0")
                    self.stat_cards["active"].configure(text="0")
                    self.stat_cards["class"].configure(text="0") 
                    self.stat_cards["subjects"].configure(text="0")
                    
            else:
                cur.execute("""
                    SELECT COUNT(id) AS n FROM scores 
                    WHERE student_id = (SELECT id FROM students WHERE student_id=%s AND is_deleted = FALSE)
                """, (self.user_data['student_id'],))
                self.stat_cards["scores_count"].configure(text=cur.fetchone()["n"] or "0")
                
                cur.execute("""
                    SELECT ROUND(AVG(total),1) AS avg FROM scores 
                    WHERE student_id = (SELECT id FROM students WHERE student_id=%s AND is_deleted = FALSE)
                """, (self.user_data['student_id'],))
                avg = cur.fetchone()["avg"] or 0
                self.stat_cards["average"].configure(text=str(avg))
                
                cur.execute("SELECT status FROM students WHERE student_id=%s AND is_deleted = FALSE", (self.user_data['student_id'],))
                status = cur.fetchone()
                self.stat_cards["status"].configure(text=status['status'] if status else "Active")
                
                cur.execute("""
                    SELECT COUNT(*) + 1 as rank FROM (
                        SELECT s.student_id, AVG(sc.total) as avg_score
                        FROM students s
                        JOIN scores sc ON s.id = sc.student_id
                        WHERE s.class_id = (SELECT class_id FROM students WHERE student_id=%s)
                        GROUP BY s.id
                        HAVING avg_score > (
                            SELECT AVG(sc2.total) 
                            FROM scores sc2 
                            WHERE sc2.student_id = (SELECT id FROM students WHERE student_id=%s)
                        )
                    ) as higher_scores
                """, (self.user_data['student_id'], self.user_data['student_id']))
                rank = cur.fetchone()
                self.stat_cards["rank"].configure(text=str(rank['rank']) if rank else "1")
                
                cur.execute("""
                    SELECT sub.subject_name, sc.midterm, sc.final, sc.total, sc.grade
                    FROM scores sc
                    JOIN subjects sub ON sc.subject_id = sub.id
                    WHERE sc.student_id = (SELECT id FROM students WHERE student_id=%s AND is_deleted = FALSE)
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
        SectionLabel(top, "Students").pack(side="left")

        btn_bar = ctk.CTkFrame(top, fg_color="transparent")
        btn_bar.pack(side="right")
        
        if self.user_data['role'] == 'admin':
            StyledButton(btn_bar, "Add", color=SUCCESS, hover="#059669",
                         command=self._add).pack(side="left", padx=4)
            StyledButton(btn_bar, "Edit", color=WARNING, hover="#D97706",
                         command=self._edit).pack(side="left", padx=4)
            StyledButton(btn_bar, "Delete", color=DANGER, hover="#DC2626",
                         command=self._delete).pack(side="left", padx=4)
            StyledButton(btn_bar, "Restore", color=PRIMARY, hover=PRIMARY_H,
                         command=self._restore).pack(side="left", padx=4)
            StyledButton(btn_bar, "Scores", color=PRIMARY, hover=PRIMARY_H,
                         command=self._scores).pack(side="left", padx=4)
        elif self.user_data['role'] == 'teacher':
            StyledButton(btn_bar, "Scores", color=PRIMARY, hover=PRIMARY_H,
                         command=self._scores).pack(side="left", padx=4)
            StyledButton(btn_bar, "View Details", color=PRIMARY,
                         command=self._view).pack(side="left", padx=4)

        search_row = ctk.CTkFrame(self.inner, fg_color="transparent")
        search_row.pack(fill="x", padx=24, pady=10)
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh())
        
        search_entry = StyledEntry(search_row, placeholder="Search by name or ID...",
                                    textvariable=self.search_var, width=320)
        search_entry.pack(side="left")

        # Show deleted checkbox
        self.show_deleted_var = ctk.BooleanVar(value=False)
        show_deleted_cb = ctk.CTkCheckBox(search_row, text="Show Deleted", 
                                          variable=self.show_deleted_var,
                                          command=self.refresh,
                                          fg_color=PRIMARY,
                                          text_color=TEXT)
        show_deleted_cb.pack(side="left", padx=(10, 0))

        table_frame = ctk.CTkFrame(self.inner, fg_color=CARD, corner_radius=14)
        table_frame.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        cols  = ["Student ID", "Name", "Gender", "Email", "Phone", "Class", "Status", "Deleted"]
        widths = [90, 200, 80, 180, 110, 110, 80, 80]
        self.tree, sb = styled_table(table_frame, cols, widths)
        self.tree.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=16)
        sb.pack(side="right", fill="y", pady=16, padx=(0, 8))
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        self.refresh()

    def _get_class_filter(self):
        if self.user_data['role'] == 'teacher':
            try:
                cur = db.cursor(dictionary=True)
                cur.execute("""
                    SELECT GROUP_CONCAT(c.id) as class_ids
                    FROM classes c
                    JOIN teachers t ON c.teacher_id = t.id
                    WHERE t.id = %s AND c.is_deleted = FALSE AND c.status = 'Active'
                """, (self.user_data['teacher_id'],))
                result = cur.fetchone()
                return result['class_ids'] if result and result['class_ids'] else None
            except:
                return None
        return None

    def refresh(self):
        q = self.search_var.get().strip()
        class_filter = self._get_class_filter()
        show_deleted = self.show_deleted_var.get()
        
        try:
            cur = db.cursor(dictionary=True)
            sql = """
                SELECT s.id, s.student_id, s.full_name, s.gender,
                       s.email, s.phone, c.class_name, s.status, 
                       s.dob, s.address, s.is_deleted,
                       DATE(s.deleted_at) as deleted_at
                FROM students s
                LEFT JOIN classes c ON s.class_id=c.id
            """
            params = []
            conditions = []
            
            if class_filter:
                # Handle multiple class IDs with IN clause
                conditions.append(f"s.class_id IN ({class_filter})")
            
            if not show_deleted:
                conditions.append("s.is_deleted = FALSE")
            
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
                deleted_status = "Yes" if r["is_deleted"] else "No"
                self.tree.insert("", "end", iid=r["id"],
                                 values=(r["student_id"], r["full_name"], r["gender"],
                                         r["email"] or "-", r["phone"] or "-",
                                         r["class_name"] or "-", r["status"], deleted_status))
        except Exception as e:
            pass

    def _on_select(self, _):
        sel = self.tree.selection()
        self.selected_db_id = int(sel[0]) if sel else None

    def _get_selected_data(self):
        if not self.selected_db_id:
            return None
        try:
            cur = db.cursor(dictionary=True)
            cur.execute("""
                SELECT s.*, c.class_name, u.username 
                FROM students s
                LEFT JOIN classes c ON s.class_id=c.id
                LEFT JOIN users u ON s.student_id = u.student_id
                WHERE s.id=%s
            """, (self.selected_db_id,))
            return cur.fetchone()
        except Exception:
            return None   
        
    def _add(self):
        StudentDialog(self, "Add Student", on_save=self._do_add, is_admin=(self.user_data['role'] == 'admin'))

    def _do_add(self, vals):
        try:
            cur = db.cursor()
            cur.execute("""
                INSERT INTO students (student_id,full_name,gender,email,phone,address,class_id,status,dob,is_deleted)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,FALSE)
            """, (vals["student_id"], vals["full_name"], vals["gender"],
                vals["email"], vals["phone"], vals["address"],
                vals["class_id"], vals["status"], vals.get("dob")))
            
            # Create user account with username from form
            if "password" in vals and vals.get("username"):
                cur.execute("""
                    INSERT INTO users (username, password, role, full_name, email, student_id, is_deleted)
                    VALUES (%s, %s, 'student', %s, %s, %s, FALSE)
                """, (vals["username"], vals["password"], vals["full_name"], 
                    vals["email"], vals["student_id"]))
            
            db.commit()
            self.refresh()
            messagebox.showinfo("Success", "Student added successfully!")
        except Error as e:
            messagebox.showerror("Error", str(e))
        
    def _edit(self):
        data = self._get_selected_data()
        if not data:
            messagebox.showinfo("Select", "Please select a student first.")
            return
        if data.get("is_deleted"):
            messagebox.showwarning("Cannot Edit", "Deleted students cannot be edited. Restore them first.")
            return
        StudentDialog(self, "Edit Student", data=data,
                      on_save=lambda v: self._do_edit(v), is_admin=(self.user_data['role'] == 'admin'))

    def _view(self):
        data = self._get_selected_data()
        if not data:
            messagebox.showinfo("Select", "Please select a student first.")
            return
        self._show_student_details(data)

    def _show_student_details(self, data):
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Student Details - {data['full_name']}")
        dialog.geometry("450x550")
        dialog.resizable(False, False)
        dialog.configure(fg_color=BG_DARK)
        dialog.grab_set()

        SectionLabel(dialog, "Student Details").pack(pady=(20, 10))

        form = ctk.CTkFrame(dialog, fg_color=CARD, corner_radius=12)
        form.pack(fill="both", expand=True, padx=20, pady=10)

        details = [
            ("Student ID", data.get("student_id", "-")),
            ("Full Name", data.get("full_name", "-")),
            ("Gender", data.get("gender", "-")),
            ("Date of Birth", data.get("dob", "-")),
            ("Email", data.get("email", "-")),
            ("Phone", data.get("phone", "-")),
            ("Class", data.get("class_name", "-")),
            ("Status", data.get("status", "-")),
            ("Deleted", "Yes" if data.get("is_deleted") else "No"),
            ("Address", data.get("address", "-")),
        ]

        for i, (label, value) in enumerate(details):
            ctk.CTkLabel(form, text=f"{label}:", text_color=SUBTEXT,
                         font=ctk.CTkFont(weight="bold")).grid(row=i, column=0, padx=16, pady=6, sticky="w")
            ctk.CTkLabel(form, text=str(value), text_color=TEXT,
                         anchor="w").grid(row=i, column=1, padx=16, pady=6, sticky="w")

        StyledButton(dialog, "Close", color=CARD2, hover=CARD,
                     command=dialog.destroy).pack(pady=20)

    def _do_edit(self, vals):
        try:
            cur = db.cursor()
            cur.execute("""
                UPDATE students SET student_id=%s,full_name=%s,gender=%s,
                email=%s,phone=%s,address=%s,class_id=%s,status=%s,dob=%s
                WHERE id=%s
            """, (vals["student_id"], vals["full_name"], vals["gender"],
                vals["email"], vals["phone"], vals["address"],
                vals["class_id"], vals["status"], vals.get("dob"), self.selected_db_id))
            
            # Update username and password if provided
            if vals.get("username"):
                update_sql = "UPDATE users SET username=%s, full_name=%s, email=%s"
                params = [vals["username"], vals["full_name"], vals["email"]]
                
                if "new_password" in vals:
                    update_sql += ", password=%s"
                    params.append(vals["new_password"])
                
                update_sql += " WHERE student_id=%s"
                params.append(vals["student_id"])
                cur.execute(update_sql, tuple(params))
            
            db.commit()
            self.refresh()
            messagebox.showinfo("Success", "Student updated successfully!")
        except Error as e:
            messagebox.showerror("Error", str(e))
            
    def _can_delete_student(self):
        """Check if student can be deleted (no scores)"""
        try:
            cur = db.cursor()
            cur.execute("SELECT COUNT(*) FROM scores WHERE student_id = %s", (self.selected_db_id,))
            count = cur.fetchone()[0]
            return count == 0
        except:
            return False

    def _delete(self):
        if not self.selected_db_id:
            messagebox.showinfo("Select", "Please select a student first.")
            return
        data = self._get_selected_data()
        if data and data.get("is_deleted"):
            messagebox.showwarning("Already Deleted", "This student is already deleted.")
            return
        
        # Check if student has scores
        if not self._can_delete_student():
            messagebox.showwarning("Cannot Delete", "This student has scores recorded. You cannot delete students with existing scores.\n\nYou can set their status to 'Inactive' instead.")
            return
            
        if messagebox.askyesno("Confirm Delete", "Soft delete this student? They can be restored later."):
            try:
                cur = db.cursor()
                cur.execute("""
                    UPDATE students SET is_deleted = TRUE, deleted_at = NOW() 
                    WHERE id = %s
                """, (self.selected_db_id,))
                cur.execute("""
                    UPDATE users SET is_deleted = TRUE, deleted_at = NOW()
                    WHERE student_id = (SELECT student_id FROM students WHERE id = %s)
                """, (self.selected_db_id,))
                db.commit()
                self.selected_db_id = None
                self.refresh()
                messagebox.showinfo("Success", "Student soft deleted successfully!")
            except Error as e:
                messagebox.showerror("Error", str(e))
    
    def _restore(self):
        if not self.selected_db_id:
            messagebox.showinfo("Select", "Please select a student first.")
            return
        data = self._get_selected_data()
        if data and not data.get("is_deleted"):
            messagebox.showwarning("Not Deleted", "This student is not deleted.")
            return
        if messagebox.askyesno("Confirm Restore", "Restore this student?"):
            try:
                cur = db.cursor()
                cur.execute("""
                    UPDATE students SET is_deleted = FALSE, deleted_at = NULL 
                    WHERE id = %s
                """, (self.selected_db_id,))
                cur.execute("""
                    UPDATE users SET is_deleted = FALSE, deleted_at = NULL
                    WHERE student_id = (SELECT student_id FROM students WHERE id = %s)
                """, (self.selected_db_id,))
                db.commit()
                self.selected_db_id = None
                self.refresh()
                messagebox.showinfo("Success", "Student restored successfully!")
            except Error as e:
                messagebox.showerror("Error", str(e))

    def _scores(self):
        data = self._get_selected_data()
        if not data:
            messagebox.showinfo("Select", "Please select a student first.")
            return
        if data.get("is_deleted"):
            messagebox.showwarning("Cannot Edit Scores", "Deleted students cannot have scores edited.")
            return
        name = data['full_name']
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


class TeachersPage(ScrollablePage):
    def __init__(self, master, user_data):
        super().__init__(master)
        self.user_data = user_data
        self.selected_id = None
        self._build()

    def _build(self):
        top = ctk.CTkFrame(self.inner, fg_color="transparent")
        top.pack(fill="x", padx=24, pady=(24, 0))
        SectionLabel(top, "Teachers").pack(side="left")

        btn_bar = ctk.CTkFrame(top, fg_color="transparent")
        btn_bar.pack(side="right")
        StyledButton(btn_bar, "Add", color=SUCCESS, hover="#059669",
                     command=self._add).pack(side="left", padx=4)
        StyledButton(btn_bar, "Edit", color=WARNING, hover="#D97706",
                     command=self._edit).pack(side="left", padx=4)
        StyledButton(btn_bar, "Delete", color=DANGER, hover="#DC2626",
                     command=self._delete).pack(side="left", padx=4)
        StyledButton(btn_bar, "Restore", color=PRIMARY, hover=PRIMARY_H,
                     command=self._restore).pack(side="left", padx=4)

        search_row = ctk.CTkFrame(self.inner, fg_color="transparent")
        search_row.pack(fill="x", padx=24, pady=10)
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh())
        StyledEntry(search_row, placeholder="Search by name or ID...",
                    textvariable=self.search_var, width=320).pack(side="left")
        
        # Show deleted checkbox
        self.show_deleted_var = ctk.BooleanVar(value=False)
        show_deleted_cb = ctk.CTkCheckBox(search_row, text="Show Deleted", 
                                          variable=self.show_deleted_var,
                                          command=self.refresh,
                                          fg_color=PRIMARY,
                                          text_color=TEXT)
        show_deleted_cb.pack(side="left", padx=(10, 0))

        table_frame = ctk.CTkFrame(self.inner, fg_color=CARD, corner_radius=14)
        table_frame.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        cols = ["ID", "Teacher ID", "Name", "Email", "Phone", "Username", "Status", "Created Date", "Deleted"]
        widths = [60, 100, 200, 180, 100, 120, 80, 100, 80]
        self.tree, sb = styled_table(table_frame, cols, widths)
        self.tree.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=16)
        sb.pack(side="right", fill="y", pady=16, padx=(0, 8))
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        self.refresh()

    def refresh(self):
        q = self.search_var.get().strip()
        show_deleted = self.show_deleted_var.get()
        try:
            cur = db.cursor(dictionary=True)
            sql = """
                SELECT t.id, t.teacher_id, t.full_name, t.email, t.phone, t.status,
                       u.username, DATE(t.created) AS created,
                       t.is_deleted, DATE(t.deleted_at) as deleted_at
                FROM teachers t
                LEFT JOIN users u ON t.id = u.teacher_id
                WHERE 1=1
            """
            params = []
            
            if not show_deleted:
                sql += " AND t.is_deleted = FALSE"
            
            if q:
                sql += " AND (t.teacher_id LIKE %s OR t.full_name LIKE %s)"
                like = f"%{q}%"
                params = [like, like]
            
            sql += " ORDER BY t.created DESC"
            
            cur.execute(sql, tuple(params))
            self.tree.delete(*self.tree.get_children())
            for r in cur.fetchall():
                deleted_status = "Yes" if r["is_deleted"] else "No"
                created_date = str(r["created"]) if r["created"] else "-"
                self.tree.insert("", "end", iid=r["id"],
                                 values=(r["id"], r["teacher_id"], r["full_name"],
                                         r["email"] or "-", r["phone"] or "-",
                                         r["username"] or "-", r["status"], created_date, deleted_status))
        except Exception as e:
            pass

    def _on_select(self, _):
        sel = self.tree.selection()
        self.selected_id = int(sel[0]) if sel else None

    def _get_selected_data(self):
        if not self.selected_id:
            return None
        try:
            cur = db.cursor(dictionary=True)
            cur.execute("""
                SELECT t.*, u.username, u.id as user_id
                FROM teachers t
                LEFT JOIN users u ON t.id = u.teacher_id
                WHERE t.id = %s
            """, (self.selected_id,))
            return cur.fetchone()
        except Exception:
            return None

    def _can_delete_teacher(self):
        """Check if teacher can be deleted (no classes assigned)"""
        try:
            cur = db.cursor()
            cur.execute("SELECT COUNT(*) FROM classes WHERE teacher_id = %s", (self.selected_id,))
            count = cur.fetchone()[0]
            return count == 0
        except:
            return False

    def _add(self):
        TeacherDialog(self, "Add Teacher", on_save=self._do_add, is_admin=(self.user_data['role'] == 'admin'))

    def _do_add(self, vals):
        if not vals["teacher_id"] or not vals["full_name"]:
            messagebox.showwarning("Validation", "Teacher ID and Full Name are required.")
            return
        
        try:
            cur = db.cursor()
            cur.execute("""
                INSERT INTO teachers (teacher_id, full_name, email, phone, address, status, is_deleted)
                VALUES (%s, %s, %s, %s, %s, %s, FALSE)
            """, (vals["teacher_id"], vals["full_name"], vals["email"],
                  vals["phone"], vals["address"], vals["status"]))
            teacher_db_id = cur.lastrowid
            
            # Create user account
            if vals.get("username"):
                password = vals.get("password", hash_pw("password123"))
                cur.execute("""
                    INSERT INTO users (username, password, role, full_name, email, teacher_id, is_deleted)
                    VALUES (%s, %s, 'teacher', %s, %s, %s, FALSE)
                """, (vals["username"], password, vals["full_name"], vals["email"], teacher_db_id))
            
            db.commit()
            self.refresh()
            messagebox.showinfo("Success", "Teacher added successfully!")
        except Error as e:
            messagebox.showerror("Error", str(e))

    def _edit(self):
        data = self._get_selected_data()
        if not data:
            messagebox.showinfo("Select", "Please select a teacher first.")
            return
        if data.get("is_deleted"):
            messagebox.showwarning("Cannot Edit", "Deleted teachers cannot be edited. Restore them first.")
            return
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Edit Teacher")
        dialog.geometry("500x700")
        dialog.resizable(False, False)
        dialog.configure(fg_color=BG_DARK)
        dialog.grab_set()

        SectionLabel(dialog, "Edit Teacher").pack(pady=(20, 10))

        form = ctk.CTkFrame(dialog, fg_color=CARD, corner_radius=12)
        form.pack(fill="both", expand=True, padx=20, pady=10)
        form.columnconfigure(1, weight=1)

        fields = [
            ("Teacher ID", "teacher_id"),
            ("Full Name", "full_name"),
            ("Email", "email"),
            ("Phone", "phone"),
            ("Address", "address"),
        ]

        vars_dict = {}
        row = 0
        for label, key in fields:
            ctk.CTkLabel(form, text=label, text_color=SUBTEXT,
                         anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
            e = StyledEntry(form, placeholder=label, width=280)
            e.grid(row=row, column=1, padx=16, pady=6, sticky="ew")
            if data and data.get(key):
                e.insert(0, str(data[key]))
            vars_dict[key] = e
            row += 1

        ctk.CTkLabel(form, text="Status", text_color=SUBTEXT,
                     anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
        status_var = ctk.StringVar(value=data.get("status", "Active"))
        status_menu = ctk.CTkOptionMenu(form, variable=status_var,
                                        values=["Active", "Inactive"],
                                        fg_color=CARD2, button_color=PRIMARY,
                                        dropdown_fg_color=CARD)
        status_menu.grid(row=row, column=1, padx=16, pady=6, sticky="ew")
        row += 1

        ctk.CTkLabel(form, text="Username", text_color=SUBTEXT,
                     anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
        username_entry = StyledEntry(form, placeholder="username", width=280)
        username_entry.grid(row=row, column=1, padx=16, pady=6, sticky="ew")
        if data and data.get("username"):
            username_entry.insert(0, str(data["username"]))
        row += 1
        
        # Password field for admin
        ctk.CTkLabel(form, text="New Password (optional)", text_color=SUBTEXT,
                     anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
        password_entry = StyledEntry(form, placeholder="Leave blank to keep current", show="*", width=280)
        password_entry.grid(row=row, column=1, padx=16, pady=6, sticky="ew")
        row += 1
        
        ctk.CTkLabel(form, text="Confirm Password", text_color=SUBTEXT,
                     anchor="w").grid(row=row, column=0, padx=16, pady=6, sticky="w")
        confirm_password_entry = StyledEntry(form, placeholder="Confirm new password", show="*", width=280)
        confirm_password_entry.grid(row=row, column=1, padx=16, pady=6, sticky="ew")
        row += 1

        def save_edit():
            new_vals = {k: e.get().strip() for k, e in vars_dict.items()}
            if not new_vals["teacher_id"] or not new_vals["full_name"]:
                messagebox.showwarning("Validation", "Teacher ID and Full Name are required.", parent=dialog)
                return
            
            # Check password
            password = password_entry.get()
            confirm = confirm_password_entry.get()
            if password or confirm:
                if password != confirm:
                    messagebox.showwarning("Validation", "Passwords do not match.", parent=dialog)
                    return
                if len(password) < 4:
                    messagebox.showwarning("Validation", "Password must be at least 4 characters.", parent=dialog)
                    return
                new_password = hash_pw(password)
            else:
                new_password = None
            
            try:
                cur = db.cursor()
                cur.execute("""
                    UPDATE teachers SET teacher_id=%s, full_name=%s, email=%s, phone=%s, address=%s, status=%s
                    WHERE id=%s
                """, (new_vals["teacher_id"], new_vals["full_name"], new_vals["email"],
                      new_vals["phone"], new_vals["address"], status_var.get(), self.selected_id))
                
                new_username = username_entry.get().strip()
                if new_username:
                    if data.get("username"):
                        # Update existing user
                        update_sql = "UPDATE users SET username=%s, full_name=%s, email=%s"
                        params = [new_username, new_vals["full_name"], new_vals["email"]]
                        if new_password:
                            update_sql += ", password=%s"
                            params.append(new_password)
                        update_sql += " WHERE teacher_id=%s"
                        params.append(self.selected_id)
                        cur.execute(update_sql, tuple(params))
                    else:
                        # Create new user account
                        default_pw = new_password if new_password else hash_pw("password123")
                        cur.execute("""
                            INSERT INTO users (username, password, role, full_name, email, teacher_id, is_deleted)
                            VALUES (%s, %s, 'teacher', %s, %s, %s, FALSE)
                        """, (new_username, default_pw, new_vals["full_name"], new_vals["email"], self.selected_id))
                
                db.commit()
                self.refresh()
                messagebox.showinfo("Success", "Teacher updated successfully!", parent=dialog)
                dialog.destroy()
            except Error as e:
                messagebox.showerror("Error", str(e), parent=dialog)

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=16)
        StyledButton(btn_row, "Cancel", color=CARD2, hover=CARD,
                     command=dialog.destroy).pack(side="left", expand=True, padx=4)
        StyledButton(btn_row, "Save",
                     command=save_edit).pack(side="left", expand=True, padx=4)

    def _delete(self):
        if not self.selected_id:
            messagebox.showinfo("Select", "Please select a teacher first.")
            return
        
        data = self._get_selected_data()
        if data and data.get("username") == "admin":
            messagebox.showwarning("Cannot Delete", "Cannot delete the default admin account.")
            return
        if data and data.get("is_deleted"):
            messagebox.showwarning("Already Deleted", "This teacher is already deleted.")
            return
        
        # Check if teacher has classes assigned
        if not self._can_delete_teacher():
            messagebox.showwarning("Cannot Delete", "This teacher is assigned to one or more classes.\n\nYou can set their status to 'Inactive' instead.")
            return
            
        if messagebox.askyesno("Confirm Delete", "Soft delete this teacher? They can be restored later."):
            try:
                cur = db.cursor()
                cur.execute("""
                    UPDATE teachers SET is_deleted = TRUE, deleted_at = NOW() 
                    WHERE id = %s
                """, (self.selected_id,))
                cur.execute("""
                    UPDATE users SET is_deleted = TRUE, deleted_at = NOW()
                    WHERE teacher_id = %s
                """, (self.selected_id,))
                db.commit()
                self.selected_id = None
                self.refresh()
                messagebox.showinfo("Success", "Teacher soft deleted successfully!")
            except Error as e:
                messagebox.showerror("Error", str(e))
    
    def _restore(self):
        if not self.selected_id:
            messagebox.showinfo("Select", "Please select a teacher first.")
            return
        data = self._get_selected_data()
        if data and not data.get("is_deleted"):
            messagebox.showwarning("Not Deleted", "This teacher is not deleted.")
            return
        if messagebox.askyesno("Confirm Restore", "Restore this teacher?"):
            try:
                cur = db.cursor()
                cur.execute("""
                    UPDATE teachers SET is_deleted = FALSE, deleted_at = NULL 
                    WHERE id = %s
                """, (self.selected_id,))
                cur.execute("""
                    UPDATE users SET is_deleted = FALSE, deleted_at = NULL
                    WHERE teacher_id = %s
                """, (self.selected_id,))
                db.commit()
                self.selected_id = None
                self.refresh()
                messagebox.showinfo("Success", "Teacher restored successfully!")
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
        SectionLabel(top, "Classes").pack(side="left")

        if self.user_data['role'] == 'admin':
            btn_bar = ctk.CTkFrame(top, fg_color="transparent")
            btn_bar.pack(side="right")
            StyledButton(btn_bar, "Add", color=SUCCESS, hover="#059669",
                         command=self._add).pack(side="left", padx=4)
            StyledButton(btn_bar, "Edit", color=WARNING, hover="#D97706",
                         command=self._edit).pack(side="left", padx=4)
            StyledButton(btn_bar, "Delete", color=DANGER, hover="#DC2626",
                         command=self._delete).pack(side="left", padx=4)
            StyledButton(btn_bar, "Restore", color=PRIMARY, hover=PRIMARY_H,
                         command=self._restore).pack(side="left", padx=4)

        search_row = ctk.CTkFrame(self.inner, fg_color="transparent")
        search_row.pack(fill="x", padx=24, pady=10)
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh())
        StyledEntry(search_row, placeholder="Search by class name...",
                    textvariable=self.search_var, width=320).pack(side="left")
        
        # Show deleted checkbox
        self.show_deleted_var = ctk.BooleanVar(value=False)
        show_deleted_cb = ctk.CTkCheckBox(search_row, text="Show Deleted", 
                                          variable=self.show_deleted_var,
                                          command=self.refresh,
                                          fg_color=PRIMARY,
                                          text_color=TEXT)
        show_deleted_cb.pack(side="left", padx=(10, 0))

        table_frame = ctk.CTkFrame(self.inner, fg_color=CARD, corner_radius=14)
        table_frame.pack(fill="both", expand=True, padx=24, pady=20)

        cols = ["ID", "Class Name", "Teacher", "Room", "Status", "Subjects", "Created Date", "Deleted"]
        widths = [60, 200, 180, 100, 80, 200, 100, 80]
        self.tree, sb = styled_table(table_frame, cols, widths)
        self.tree.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=16)
        sb.pack(side="right", fill="y", pady=16, padx=(0, 8))
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        self.refresh()

    def refresh(self):
        q = self.search_var.get().strip()
        show_deleted = self.show_deleted_var.get()
        try:
            cur = db.cursor(dictionary=True)
            sql = """
                SELECT c.id, c.class_name, t.full_name as teacher, c.room, c.status,
                       GROUP_CONCAT(s.subject_name SEPARATOR ', ') as subjects,
                       DATE(c.created) AS created,
                       c.is_deleted, DATE(c.deleted_at) as deleted_at
                FROM classes c
                LEFT JOIN teachers t ON c.teacher_id = t.id
                LEFT JOIN class_subjects cs ON c.id = cs.class_id
                LEFT JOIN subjects s ON cs.subject_id = s.id
                WHERE 1=1
            """
            params = []
            
            if not show_deleted:
                sql += " AND c.is_deleted = FALSE"
            
            if q:
                sql += " AND c.class_name LIKE %s"
                params.append(f"%{q}%")
            
            if self.user_data['role'] == 'teacher':
                sql += " AND c.teacher_id = %s"
                params.append(self.user_data['teacher_id'])
            
            sql += " GROUP BY c.id ORDER BY c.created DESC"
            cur.execute(sql, tuple(params))
            
            self.tree.delete(*self.tree.get_children())
            for r in cur.fetchall():
                deleted_status = "Yes" if r["is_deleted"] else "No"
                created_date = str(r["created"]) if r["created"] else "-"
                self.tree.insert("", "end", iid=r["id"],
                                 values=(r["id"], r["class_name"], r["teacher"] or "-",
                                         r["room"] or "-", r["status"], r["subjects"] or "None", created_date, deleted_status))
        except Exception as e:
            pass

    def _on_select(self, _):
        sel = self.tree.selection()
        self.selected_id = int(sel[0]) if sel else None

    def _get_selected_data(self):
        if not self.selected_id:
            return None
        try:
            cur = db.cursor(dictionary=True)
            cur.execute("""
                SELECT c.*, t.full_name as teacher 
                FROM classes c
                LEFT JOIN teachers t ON c.teacher_id = t.id
                WHERE c.id = %s
            """, (self.selected_id,))
            return cur.fetchone()
        except Exception:
            return None

    def _can_delete_class(self):
        """Check if class can be deleted (no students assigned)"""
        try:
            cur = db.cursor()
            cur.execute("SELECT COUNT(*) FROM students WHERE class_id = %s", (self.selected_id,))
            count = cur.fetchone()[0]
            return count == 0
        except:
            return False

    def _add(self):
        ClassDialog(self, "Add Class", on_save=self._do_add)

    def _do_add(self, vals):
        try:
            cur = db.cursor()
            cur.execute("""
                INSERT INTO classes (class_name, teacher_id, room, status, is_deleted)
                VALUES (%s, %s, %s, %s, FALSE)
            """, (vals["class_name"], vals["teacher_id"], vals["room"], vals["status"]))
            class_id = cur.lastrowid
            
            for subject_id in vals["subjects"]:
                cur.execute("INSERT INTO class_subjects (class_id, subject_id) VALUES (%s, %s)",
                           (class_id, subject_id))
            
            db.commit()
            self.refresh()
            messagebox.showinfo("Success", "Class added successfully with subjects!")
        except Error as e:
            messagebox.showerror("Error", str(e))

    def _edit(self):
        data = self._get_selected_data()
        if not data:
            messagebox.showinfo("Select", "Select a class first.")
            return
        if data.get("is_deleted"):
            messagebox.showwarning("Cannot Edit", "Deleted classes cannot be edited. Restore them first.")
            return
        ClassDialog(self, "Edit Class", data=data, on_save=self._do_edit)

    def _do_edit(self, vals):
        try:
            cur = db.cursor()
            cur.execute("""
                UPDATE classes SET class_name=%s, teacher_id=%s, room=%s, status=%s
                WHERE id=%s
            """, (vals["class_name"], vals["teacher_id"], vals["room"], vals["status"], vals["class_id"]))
            
            cur.execute("DELETE FROM class_subjects WHERE class_id=%s", (vals["class_id"],))
            for subject_id in vals["subjects"]:
                cur.execute("INSERT INTO class_subjects (class_id, subject_id) VALUES (%s, %s)",
                           (vals["class_id"], subject_id))
            
            db.commit()
            self.refresh()
            messagebox.showinfo("Success", "Class updated successfully!")
        except Error as e:
            messagebox.showerror("Error", str(e))

    def _delete(self):
        if not self.selected_id:
            messagebox.showinfo("Select", "Select a class first.")
            return
        data = self._get_selected_data()
        if data and data.get("is_deleted"):
            messagebox.showwarning("Already Deleted", "This class is already deleted.")
            return
        
        # Check if class has students
        if not self._can_delete_class():
            messagebox.showwarning("Cannot Delete", "This class has students assigned.\n\nYou can set its status to 'Inactive' instead.")
            return
            
        if messagebox.askyesno("Confirm", "Soft delete this class? It can be restored later."):
            try:
                cur = db.cursor()
                cur.execute("""
                    UPDATE classes SET is_deleted = TRUE, deleted_at = NOW() 
                    WHERE id = %s
                """, (self.selected_id,))
                db.commit()
                self.selected_id = None
                self.refresh()
                messagebox.showinfo("Success", "Class soft deleted successfully!")
            except Error as e:
                messagebox.showerror("Error", str(e))
    
    def _restore(self):
        if not self.selected_id:
            messagebox.showinfo("Select", "Select a class first.")
            return
        data = self._get_selected_data()
        if data and not data.get("is_deleted"):
            messagebox.showwarning("Not Deleted", "This class is not deleted.")
            return
        if messagebox.askyesno("Confirm Restore", "Restore this class?"):
            try:
                cur = db.cursor()
                cur.execute("""
                    UPDATE classes SET is_deleted = FALSE, deleted_at = NULL 
                    WHERE id = %s
                """, (self.selected_id,))
                db.commit()
                self.selected_id = None
                self.refresh()
                messagebox.showinfo("Success", "Class restored successfully!")
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
        SectionLabel(top, "Subjects").pack(side="left")

        if self.user_data['role'] == 'admin':
            btn_bar = ctk.CTkFrame(top, fg_color="transparent")
            btn_bar.pack(side="right")
            StyledButton(btn_bar, "Add", color=SUCCESS, hover="#059669",
                         command=self._add).pack(side="left", padx=4)
            StyledButton(btn_bar, "Edit", color=WARNING, hover="#D97706",
                         command=self._edit).pack(side="left", padx=4)
            StyledButton(btn_bar, "Delete", color=DANGER, hover="#DC2626",
                         command=self._delete).pack(side="left", padx=4)
            StyledButton(btn_bar, "Restore", color=PRIMARY, hover=PRIMARY_H,
                         command=self._restore).pack(side="left", padx=4)

        search_row = ctk.CTkFrame(self.inner, fg_color="transparent")
        search_row.pack(fill="x", padx=24, pady=10)
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh())
        StyledEntry(search_row, placeholder="Search by subject name or code...",
                    textvariable=self.search_var, width=320).pack(side="left")
        
        # Show deleted checkbox
        self.show_deleted_var = ctk.BooleanVar(value=False)
        show_deleted_cb = ctk.CTkCheckBox(search_row, text="Show Deleted", 
                                          variable=self.show_deleted_var,
                                          command=self.refresh,
                                          fg_color=PRIMARY,
                                          text_color=TEXT)
        show_deleted_cb.pack(side="left", padx=(10, 0))

        table_frame = ctk.CTkFrame(self.inner, fg_color=CARD, corner_radius=14)
        table_frame.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        cols  = ["ID", "Subject Name", "Code", "Credits", "Status", "Created Date", "Deleted"]
        widths = [60, 200, 120, 80, 80, 100, 80]
        self.tree, sb = styled_table(table_frame, cols, widths)
        self.tree.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=16)
        sb.pack(side="right", fill="y", pady=16, padx=(0, 8))
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        self.refresh()

    def refresh(self):
        q = self.search_var.get().strip()
        show_deleted = self.show_deleted_var.get()
        try:
            cur = db.cursor(dictionary=True)
            sql = """
                SELECT id, subject_name, subject_code, credits, status,
                       DATE(created) AS created,
                       is_deleted, DATE(deleted_at) as deleted_at
                FROM subjects
                WHERE 1=1
            """
            params = []
            
            if not show_deleted:
                sql += " AND is_deleted = FALSE"
            
            if q:
                sql += " AND (subject_name LIKE %s OR subject_code LIKE %s)"
                like = f"%{q}%"
                params = [like, like]
            
            sql += " ORDER BY subject_name"
            cur.execute(sql, tuple(params))
            
            self.tree.delete(*self.tree.get_children())
            for r in cur.fetchall():
                deleted_status = "Yes" if r["is_deleted"] else "No"
                created_date = str(r["created"]) if r["created"] else "-"
                self.tree.insert("", "end", iid=r["id"],
                                 values=(r["id"], r["subject_name"], r["subject_code"],
                                         r["credits"], r["status"], created_date, deleted_status))
        except Exception:
            pass

    def _on_select(self, _):
        sel = self.tree.selection()
        if sel:
            self.selected_id = int(sel[0])

    def _get_selected_data(self):
        if not self.selected_id:
            return None
        try:
            cur = db.cursor(dictionary=True)
            cur.execute("SELECT * FROM subjects WHERE id = %s", (self.selected_id,))
            return cur.fetchone()
        except Exception:
            return None

    def _can_delete_subject(self):
        """Check if subject can be deleted (no scores and not used in classes)"""
        try:
            cur = db.cursor()
            # Check if subject has scores
            cur.execute("SELECT COUNT(*) FROM scores WHERE subject_id = %s", (self.selected_id,))
            scores_count = cur.fetchone()[0]
            # Check if subject is used in any class
            cur.execute("SELECT COUNT(*) FROM class_subjects WHERE subject_id = %s", (self.selected_id,))
            class_count = cur.fetchone()[0]
            return scores_count == 0 and class_count == 0
        except:
            return False

    def _add(self):
        SubjectDialog(self, "Add Subject", on_save=self._do_add)

    def _do_add(self, vals):
        try:
            cur = db.cursor()
            cur.execute("""
                INSERT INTO subjects (subject_name, subject_code, credits, status, is_deleted)
                VALUES (%s, %s, %s, %s, FALSE)
            """, (vals["subject_name"], vals["subject_code"], vals["credits"], vals["status"]))
            db.commit()
            self.refresh()
            messagebox.showinfo("Success", "Subject added successfully!")
        except Error as e:
            messagebox.showerror("Error", str(e))

    def _edit(self):
        data = self._get_selected_data()
        if not data:
            messagebox.showinfo("Select", "Select a subject first.")
            return
        if data.get("is_deleted"):
            messagebox.showwarning("Cannot Edit", "Deleted subjects cannot be edited. Restore them first.")
            return
        SubjectDialog(self, "Edit Subject", data=data, on_save=self._do_edit)

    def _do_edit(self, vals):
        try:
            cur = db.cursor()
            cur.execute("""
                UPDATE subjects SET subject_name=%s, subject_code=%s, credits=%s, status=%s
                WHERE id=%s
            """, (vals["subject_name"], vals["subject_code"], vals["credits"],
                  vals["status"], vals["subject_id"]))
            db.commit()
            self.refresh()
            messagebox.showinfo("Success", "Subject updated successfully!")
        except Error as e:
            messagebox.showerror("Error", str(e))

    def _delete(self):
        if not self.selected_id:
            messagebox.showinfo("Select", "Select a subject first.")
            return
        data = self._get_selected_data()
        if data and data.get("is_deleted"):
            messagebox.showwarning("Already Deleted", "This subject is already deleted.")
            return
        
        # Check if subject can be deleted
        if not self._can_delete_subject():
            messagebox.showwarning("Cannot Delete", "This subject has scores or is assigned to classes.\n\nYou can set its status to 'Inactive' instead.")
            return
            
        if messagebox.askyesno("Confirm", "Soft delete this subject?"):
            try:
                cur = db.cursor()
                cur.execute("""
                    UPDATE subjects SET is_deleted = TRUE, deleted_at = NOW() 
                    WHERE id = %s
                """, (self.selected_id,))
                db.commit()
                self.selected_id = None
                self.refresh()
                messagebox.showinfo("Success", "Subject soft deleted successfully!")
            except Error as e:
                messagebox.showerror("Error", str(e))
    
    def _restore(self):
        if not self.selected_id:
            messagebox.showinfo("Select", "Select a subject first.")
            return
        data = self._get_selected_data()
        if data and not data.get("is_deleted"):
            messagebox.showwarning("Not Deleted", "This subject is not deleted.")
            return
        if messagebox.askyesno("Confirm Restore", "Restore this subject?"):
            try:
                cur = db.cursor()
                cur.execute("""
                    UPDATE subjects SET is_deleted = FALSE, deleted_at = NULL 
                    WHERE id = %s
                """, (self.selected_id,))
                db.commit()
                self.selected_id = None
                self.refresh()
                messagebox.showinfo("Success", "Subject restored successfully!")
            except Error as e:
                messagebox.showerror("Error", str(e))


class ReportsPage(ScrollablePage):
    def __init__(self, master, user_data):
        super().__init__(master)
        self.user_data = user_data
        self._build()

    def _build(self):
        SectionLabel(self.inner, "Performance Report").pack(anchor="w", padx=24, pady=(24, 16))

        filter_row = ctk.CTkFrame(self.inner, fg_color=CARD, corner_radius=12)
        filter_row.pack(fill="x", padx=24, pady=(0, 12))
        
        if self.user_data['role'] != 'student':
            ctk.CTkLabel(filter_row, text="Filter by Class:",
                         text_color=SUBTEXT).pack(side="left", padx=16, pady=10)
            self.class_var = ctk.StringVar(value="All Classes")
            self.class_menu = ctk.CTkOptionMenu(filter_row, variable=self.class_var,
                                                values=["All Classes"],
                                                fg_color=CARD2, button_color=PRIMARY,
                                                dropdown_fg_color=CARD,
                                                command=lambda _: self.refresh())
            self.class_menu.pack(side="left", padx=8, pady=10)
        
        StyledButton(filter_row, "Refresh", command=self.refresh).pack(side="right", padx=16, pady=10)

        if self.user_data['role'] != 'student':
            StyledButton(filter_row, "Edit Scores", color=SUCCESS, hover="#059669",
                         command=self._edit_scores).pack(side="right", padx=8, pady=10)
            StyledButton(filter_row, "Export", color=WARNING, hover="#D97706",
                         command=self._export).pack(side="right", padx=8, pady=10)

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
            self.tree.bind("<Double-Button-1>", self._on_double_click)

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
                    WHERE t.id = %s AND c.is_deleted = FALSE AND c.status = 'Active'
                """, (self.user_data['teacher_id'],))
                names = [r["class_name"] for r in cur.fetchall()]
                self.class_menu.configure(values=["All Classes"] + names if names else ["No Class"])
                self.class_var.set("All Classes" if names else "No Class")
            else:
                cur.execute("SELECT class_name FROM classes WHERE is_deleted = FALSE AND status = 'Active' ORDER BY class_name")
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
                    WHERE sc.student_id = (SELECT id FROM students WHERE student_id=%s AND is_deleted = FALSE)
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
                    SELECT s.id, s.student_id, s.full_name, c.class_name,
                           COUNT(sc.id) AS subj_count,
                           ROUND(AVG(sc.total),1) AS avg_score
                    FROM students s
                    LEFT JOIN classes c ON s.class_id = c.id
                    LEFT JOIN scores sc ON sc.student_id = s.id
                    WHERE c.teacher_id = %s AND s.is_deleted = FALSE AND s.status = 'Active'
                """
                params = (self.user_data['teacher_id'],)
                if cls != "All Classes" and cls != "No Class":
                    sql += " AND c.class_name = %s"
                    params = (self.user_data['teacher_id'], cls)
                sql += " GROUP BY s.id ORDER BY avg_score DESC"
                cur.execute(sql, params)
            else:
                sql = """
                    SELECT s.id, s.student_id, s.full_name, c.class_name,
                           COUNT(sc.id) AS subj_count,
                           ROUND(AVG(sc.total),1) AS avg_score
                    FROM students s
                    LEFT JOIN classes c ON s.class_id = c.id
                    LEFT JOIN scores sc ON sc.student_id = s.id
                    WHERE s.is_deleted = FALSE AND s.status = 'Active'
                """
                params = ()
                if cls != "All Classes":
                    sql += " AND c.class_name = %s"
                    params = (cls,)
                sql += " GROUP BY s.id ORDER BY avg_score DESC"
                cur.execute(sql, params)
                
            self.students_data = {}
            self.tree.delete(*self.tree.get_children())
            for r in cur.fetchall():
                avg = r["avg_score"] or 0
                grade = ("A+" if avg >= 90 else "A" if avg >= 80 else
                         "B+" if avg >= 75 else "B" if avg >= 70 else
                         "C+" if avg >= 65 else "C" if avg >= 60 else
                         "D" if avg >= 50 else "F")
                result = "Pass" if avg >= 50 else "Fail"
                self.tree.insert("", "end", iid=r["id"],
                                 values=(r["student_id"], r["full_name"],
                                         r["class_name"] or "-", r["subj_count"] or 0,
                                         avg, grade, result))
                self.students_data[r["id"]] = r["student_id"]
        except Exception as e:
            pass

    def _on_double_click(self, event):
        selection = self.tree.selection()
        if selection:
            student_db_id = int(selection[0])
            student_name = self.tree.item(selection[0])['values'][1]
            ScoreDialog(self, student_db_id, student_name, on_save=self._do_scores)

    def _edit_scores(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Select", "Please select a student first.")
            return
        student_db_id = int(selection[0])
        student_name = self.tree.item(selection[0])['values'][1]
        ScoreDialog(self, student_db_id, student_name, on_save=self._do_scores)

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
            self.refresh()
        except Error as e:
            messagebox.showerror("Error", str(e))

    def _export(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Report"
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("Student Performance Report\n")
                    f.write("=" * 60 + "\n\n")
                    items = self.tree.get_children()
                    headers = [self.tree.heading(col)['text'] for col in self.tree['columns']]
                    f.write("\t".join(headers) + "\n")
                    f.write("-" * 60 + "\n")
                    for item in items:
                        values = self.tree.item(item)['values']
                        f.write("\t".join(str(v) for v in values) + "\n")
                messagebox.showinfo("Success", f"Report exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", str(e))


# ========== MAIN APPLICATION ==========
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
        
        self.show_login()
    
    def show_login(self):
        for widget in self.winfo_children():
            widget.destroy()
        
        self.login_frame = ctk.CTkFrame(self, fg_color=BG_DARK)
        self.login_frame.pack(fill="both", expand=True)
        self._create_login_widgets()
    
    def _create_login_widgets(self):
        main_frame = ctk.CTkFrame(self.login_frame, fg_color="transparent")
        main_frame.pack(expand=True, fill="both", padx=40, pady=40)
        
        center_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        center_frame.pack(expand=True)
        
        ctk.CTkLabel(center_frame, text="Student Management System",
                     font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=PRIMARY).pack(pady=(0, 5))
        ctk.CTkLabel(center_frame, text="Please login to continue",
                     font=ctk.CTkFont(size=12),
                     text_color=SUBTEXT).pack(pady=(0, 30))
        
        form_frame = ctk.CTkFrame(center_frame, fg_color=CARD, corner_radius=12)
        form_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(form_frame, text="Username",
                     text_color=SUBTEXT, anchor="w").pack(padx=20, pady=(20, 5))
        self.username_entry = StyledEntry(form_frame, placeholder="Enter username")
        self.username_entry.pack(padx=20, pady=(0, 15), fill="x")
        
        ctk.CTkLabel(form_frame, text="Password",
                     text_color=SUBTEXT, anchor="w").pack(padx=20, pady=(0, 5))
        self.password_entry = StyledEntry(form_frame, placeholder="Enter password", show="*")
        self.password_entry.pack(padx=20, pady=(0, 20), fill="x")
        
        StyledButton(form_frame, "Login", color=PRIMARY, hover=PRIMARY_H,
                     command=self._do_login).pack(padx=20, pady=(0, 20), fill="x")
        
        info_frame = ctk.CTkFrame(center_frame, fg_color=CARD2, corner_radius=8)
        info_frame.pack(fill="x", pady=(20, 0))
        
        ctk.CTkLabel(info_frame, text="Demo Credentials:",
                     font=ctk.CTkFont(weight="bold"),
                     text_color=TEXT).pack(pady=(10, 5))
        
        creds = [
            ("Admin", "admin / admin123"),
            ("Teacher", "teacher / teacher123"),
            ("Student 1", "student / student123"),
            ("Student 2", "student2 / student123"),
            ("Student 3", "student3 / student123"),
        ]
        
        for role, cred in creds:
            ctk.CTkLabel(info_frame, text=f"{role}: {cred}",
                         text_color=SUBTEXT, font=ctk.CTkFont(size=11)).pack(pady=2)
        
        self.bind("<Return>", lambda e: self._do_login())
        self.username_entry.focus()
    
    def _do_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        
        if not username or not password:
            messagebox.showwarning("Login Error", "Please enter both username and password")
            return
        
        try:
            cur = db.cursor(dictionary=True)
            cur.execute("""
                SELECT id, username, role, full_name, student_id, teacher_id, email, is_deleted
                FROM users WHERE username=%s AND password=%s
            """, (username, hash_pw(password)))
            user = cur.fetchone()
            
            if user:
                if user.get("is_deleted"):
                    messagebox.showerror("Login Failed", "Your account has been deactivated. Please contact an administrator.")
                    return
                self.user_data = user
                self._build_main_app()
            else:
                messagebox.showerror("Login Failed", "Invalid username or password")
        except Exception as e:
            messagebox.showerror("Database Error", str(e))
    
    def _build_main_app(self):
        self.login_frame.destroy()
        self._build()
    
    def _update_profile(self, new_data):
        try:
            cur = db.cursor()
            cur.execute("UPDATE users SET full_name=%s, email=%s WHERE id=%s",
                        (new_data["full_name"], new_data["email"], self.user_data["id"]))
            
            if "new_password" in new_data:
                cur.execute("UPDATE users SET password=%s WHERE id=%s",
                            (new_data["new_password"], self.user_data["id"]))
            
            if self.user_data['role'] == 'student' and self.user_data.get('student_id'):
                cur.execute("UPDATE students SET full_name=%s, email=%s WHERE student_id=%s",
                            (new_data["full_name"], new_data["email"], self.user_data['student_id']))
            elif self.user_data['role'] == 'teacher' and self.user_data.get('teacher_id'):
                cur.execute("UPDATE teachers SET full_name=%s, email=%s WHERE id=%s",
                            (new_data["full_name"], new_data["email"], self.user_data['teacher_id']))
            
            db.commit()
            self.user_data["full_name"] = new_data["full_name"]
            self.user_data["email"] = new_data["email"]
            
            messagebox.showinfo("Success", "Profile updated successfully!")
            
            current_page = self.pages.get(self.current_page_name) if hasattr(self, 'current_page_name') else None
            if current_page and hasattr(current_page, "refresh"):
                current_page.refresh()
                
        except Error as e:
            messagebox.showerror("Error", str(e))
    
    def _build(self):
        sidebar = ctk.CTkFrame(self, width=SIDEBAR_W, fg_color=CARD, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        logo_frame = ctk.CTkFrame(sidebar, fg_color=PRIMARY, height=64, corner_radius=0)
        logo_frame.pack(fill="x")
        logo_frame.pack_propagate(False)
        
        ctk.CTkLabel(logo_frame, text="SMS",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=TEXT).pack(expand=True)

        if self.user_data['role'] == 'admin':
            nav_items = [
                ("Dashboard", self._show_dashboard),
                ("Students", self._show_students),
                ("Teachers", self._show_teachers),
                ("Classes", self._show_classes),
                ("Subjects", self._show_subjects),
                ("Reports", self._show_reports),
            ]
        elif self.user_data['role'] == 'teacher':
            nav_items = [
                ("Dashboard", self._show_dashboard),
                ("Students", self._show_students),
                ("Classes", self._show_classes),
                ("Reports", self._show_reports),
            ]
        else:
            nav_items = [
                ("Dashboard", self._show_dashboard),
                ("Reports", self._show_reports),
            ]

        nav_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav_frame.pack(fill="x", padx=8, pady=16)

        self.nav_buttons = {}
        for name, cmd in nav_items:
            btn = ctk.CTkButton(nav_frame, text=name,
                               fg_color="transparent",
                               hover_color=CARD2,
                               text_color=SUBTEXT,
                               anchor="w",
                               height=44,
                               corner_radius=8,
                               font=ctk.CTkFont(size=13),
                               command=cmd)
            btn.pack(fill="x", pady=2)
            self.nav_buttons[name] = btn

        user_frame = ctk.CTkFrame(sidebar, fg_color=CARD2, corner_radius=10)
        user_frame.pack(side="bottom", fill="x", padx=8, pady=12)
        
        ctk.CTkLabel(user_frame, text=self.user_data['username'],
                     text_color=TEXT, font=ctk.CTkFont(weight="bold")).pack(pady=(10, 2))
        ctk.CTkLabel(user_frame, text=f"Role: {self.user_data['role'].title()}",
                     text_color=SUBTEXT, font=ctk.CTkFont(size=11)).pack(pady=(0, 5))
        
        StyledButton(user_frame, "Profile", color=PRIMARY, hover=PRIMARY_H,
                     command=self._show_profile).pack(pady=(4, 4), padx=12, fill="x")
        
        StyledButton(user_frame, "Logout", color=DANGER, hover="#DC2626",
                     command=self._logout).pack(pady=(4, 10), padx=12, fill="x")

        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(side="left", fill="both", expand=True)

        self.pages = {}
        
        if self.user_data['role'] == 'admin':
            self.pages = {
                "Dashboard": DashboardPage(self.content, self.user_data),
                "Students": StudentsPage(self.content, self.user_data),
                "Teachers": TeachersPage(self.content, self.user_data),
                "Classes": ClassesPage(self.content, self.user_data),
                "Subjects": SubjectsPage(self.content, self.user_data),
                "Reports": ReportsPage(self.content, self.user_data),
            }
        elif self.user_data['role'] == 'teacher':
            self.pages = {
                "Dashboard": DashboardPage(self.content, self.user_data),
                "Students": StudentsPage(self.content, self.user_data),
                "Classes": ClassesPage(self.content, self.user_data),
                "Reports": ReportsPage(self.content, self.user_data),
            }
        else:
            self.pages = {
                "Dashboard": DashboardPage(self.content, self.user_data),
                "Reports": ReportsPage(self.content, self.user_data),
            }

        self._show_dashboard()

    def _show_profile(self):
        ProfileDialog(self, self.user_data, on_update=self._update_profile)
    
    def _show_page(self, name):
        for p in self.pages.values():
            p.pack_forget()
        for n, b in self.nav_buttons.items():
            if n == name:
                b.configure(fg_color=PRIMARY, text_color=TEXT)
            else:
                b.configure(fg_color="transparent", text_color=SUBTEXT)
        page = self.pages[name]
        if hasattr(page, "refresh"):
            page.refresh()
        if hasattr(page, "scroll_to_top"):
            page.scroll_to_top()
        page.pack(fill="both", expand=True)
        self.current_page_name = name

    def _show_dashboard(self): self._show_page("Dashboard")
    def _show_students(self): self._show_page("Students")
    def _show_teachers(self): self._show_page("Teachers")
    def _show_classes(self): self._show_page("Classes")
    def _show_subjects(self): self._show_page("Subjects")
    def _show_reports(self): self._show_page("Reports")

    def _logout(self):
        self.user_data = None
        self.pages = {}
        self.nav_buttons = {}
        
        for widget in self.winfo_children():
            widget.destroy()
        
        self.show_login()


if __name__ == "__main__":
    DB_HOST = "localhost"
    DB_USER = "root"
    DB_PASSWORD = "root"
    
    ok, msg = db.connect(DB_HOST, DB_USER, DB_PASSWORD)
    if not ok:
        root = ctk.CTk()
        root.withdraw()
        messagebox.showerror(
            "Database Error",
            f"Cannot connect to MySQL with {DB_USER}/{DB_PASSWORD}:\n\n{msg}\n\n"
            "Please check that MySQL is running and your credentials are correct."
        )
        root.destroy()
    else:
        try:
            db.setup_database()
        except Exception as e:
            root = ctk.CTk()
            root.withdraw()
            messagebox.showerror("Setup Error", str(e))
            root.destroy()
        else:
            app = MainApp()
            app.mainloop()