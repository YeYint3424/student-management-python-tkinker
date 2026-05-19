# pages/students.py
import customtkinter as ctk
from tkinter import messagebox
from config import CARD, SUCCESS, WARNING, DANGER, PRIMARY, BG_DARK, SUBTEXT, TEXT
from widgets import ScrollablePage, SectionLabel, StyledEntry, StyledButton
from utils import styled_table
from dialogs import StudentDialog, ScoreDialog
from database import db 

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
            
            if "password" in vals and vals.get("username"):
                cur.execute("""
                    INSERT INTO users (username, password, role, full_name, email, student_id, is_deleted)
                    VALUES (%s, %s, 'student', %s, %s, %s, FALSE)
                """, (vals["username"], vals["password"], vals["full_name"], 
                    vals["email"], vals["student_id"]))
            
            db.commit()
            self.refresh()
            messagebox.showinfo("Success", "Student added successfully!")
        except Exception as e:
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
        except Exception as e:
            messagebox.showerror("Error", str(e))
            
    def _can_delete_student(self):
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
            except Exception as e:
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
            except Exception as e:
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
        except Exception as e:
            messagebox.showerror("Error", str(e))