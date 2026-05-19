# pages/teachers.py
import customtkinter as ctk
from tkinter import messagebox
from config import CARD, SUCCESS, WARNING, DANGER, PRIMARY, BG_DARK, SUBTEXT, TEXT, CARD2
from widgets import ScrollablePage, SectionLabel, StyledEntry, StyledButton
from utils import styled_table, hash_pw
from dialogs import TeacherDialog
from database import db 

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
            
            if vals.get("username"):
                password = vals.get("password", hash_pw("password123"))
                cur.execute("""
                    INSERT INTO users (username, password, role, full_name, email, teacher_id, is_deleted)
                    VALUES (%s, %s, 'teacher', %s, %s, %s, FALSE)
                """, (vals["username"], password, vals["full_name"], vals["email"], teacher_db_id))
            
            db.commit()
            self.refresh()
            messagebox.showinfo("Success", "Teacher added successfully!")
        except Exception as e:
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
                        update_sql = "UPDATE users SET username=%s, full_name=%s, email=%s"
                        params = [new_username, new_vals["full_name"], new_vals["email"]]
                        if new_password:
                            update_sql += ", password=%s"
                            params.append(new_password)
                        update_sql += " WHERE teacher_id=%s"
                        params.append(self.selected_id)
                        cur.execute(update_sql, tuple(params))
                    else:
                        default_pw = new_password if new_password else hash_pw("password123")
                        cur.execute("""
                            INSERT INTO users (username, password, role, full_name, email, teacher_id, is_deleted)
                            VALUES (%s, %s, 'teacher', %s, %s, %s, FALSE)
                        """, (new_username, default_pw, new_vals["full_name"], new_vals["email"], self.selected_id))
                
                db.commit()
                self.refresh()
                messagebox.showinfo("Success", "Teacher updated successfully!", parent=dialog)
                dialog.destroy()
            except Exception as e:
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
            except Exception as e:
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
            except Exception as e:
                messagebox.showerror("Error", str(e))