# dialogs.py
import customtkinter as ctk
from tkinter import messagebox
from config import BG_DARK, CARD, CARD2, SUBTEXT, TEXT, PRIMARY, SUCCESS, WARNING
from widgets import StyledEntry, StyledButton, SectionLabel
from utils import hash_pw
from database import db 

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

        # Username field
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

        # Password fields
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
        
        if not vals["student_id"] or not vals["full_name"]:
            messagebox.showwarning("Validation", "Student ID and Full Name are required.", parent=self)
            return
        
        username = self.username_entry.get().strip()
        if not username:
            messagebox.showwarning("Validation", "Username is required for student accounts.", parent=self)
            return
        
        vals["username"] = username
        
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
        
        if not vals["teacher_id"] or not vals["full_name"]:
            messagebox.showwarning("Validation", "Teacher ID and Full Name are required.", parent=self)
            return
        
        username = self.username_entry.get().strip()
        if not username:
            messagebox.showwarning("Validation", "Username is required for teacher accounts.", parent=self)
            return
        
        vals["username"] = username
        vals["status"] = self.status_var.get()
        
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