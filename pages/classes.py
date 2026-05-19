# pages/classes.py
import customtkinter as ctk
from tkinter import messagebox
from config import CARD, SUCCESS, WARNING, DANGER, PRIMARY
from widgets import ScrollablePage, SectionLabel, StyledEntry, StyledButton
from utils import styled_table
from dialogs import ClassDialog
from database import db 

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
        
        self.show_deleted_var = ctk.BooleanVar(value=False)
        show_deleted_cb = ctk.CTkCheckBox(search_row, text="Show Deleted", 
                                          variable=self.show_deleted_var,
                                          command=self.refresh,
                                          fg_color=PRIMARY,
                                          text_color=PRIMARY)
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
        except Exception as e:
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
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _delete(self):
        if not self.selected_id:
            messagebox.showinfo("Select", "Select a class first.")
            return
        data = self._get_selected_data()
        if data and data.get("is_deleted"):
            messagebox.showwarning("Already Deleted", "This class is already deleted.")
            return
        
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
            except Exception as e:
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
            except Exception as e:
                messagebox.showerror("Error", str(e))