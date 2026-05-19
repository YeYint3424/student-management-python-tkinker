# pages/reports.py
import customtkinter as ctk
from tkinter import messagebox, filedialog
from config import CARD, CARD2, SUBTEXT, PRIMARY, SUCCESS, WARNING
from widgets import ScrollablePage, SectionLabel, StyledButton
from utils import styled_table
from dialogs import ScoreDialog
from database import db 

class ReportsPage(ScrollablePage):
    def __init__(self, master, user_data):
        super().__init__(master)
        self.user_data = user_data
        self.students_data = {}
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
        except Exception as e:
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