# pages/subjects.py
import customtkinter as ctk
from tkinter import messagebox
from config import CARD, SUCCESS, WARNING, DANGER, PRIMARY
from widgets import ScrollablePage, SectionLabel, StyledEntry, StyledButton
from utils import styled_table
from dialogs import SubjectDialog
from database import db 

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
        
        self.show_deleted_var = ctk.BooleanVar(value=False)
        show_deleted_cb = ctk.CTkCheckBox(search_row, text="Show Deleted", 
                                          variable=self.show_deleted_var,
                                          command=self.refresh,
                                          fg_color=PRIMARY,
                                          text_color=PRIMARY)
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
        try:
            cur = db.cursor()
            cur.execute("SELECT COUNT(*) FROM scores WHERE subject_id = %s", (self.selected_id,))
            scores_count = cur.fetchone()[0]
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
        except Exception as e:
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
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _delete(self):
        if not self.selected_id:
            messagebox.showinfo("Select", "Select a subject first.")
            return
        data = self._get_selected_data()
        if data and data.get("is_deleted"):
            messagebox.showwarning("Already Deleted", "This subject is already deleted.")
            return
        
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
            except Exception as e:
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
            except Exception as e:
                messagebox.showerror("Error", str(e))