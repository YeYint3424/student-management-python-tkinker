# main.py
import customtkinter as ctk
from tkinter import messagebox
from config import BG_DARK, CARD, CARD2, SUBTEXT, TEXT, PRIMARY, DANGER, SIDEBAR_W
from widgets import StyledButton, StyledEntry
from dialogs import ProfileDialog
from pages import DashboardPage, StudentsPage, TeachersPage, ClassesPage, SubjectsPage, ReportsPage
from database import db 
from utils import hash_pw

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
                
        except Exception as e:
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
    from config import DB_HOST, DB_USER, DB_PASSWORD
    
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