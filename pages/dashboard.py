# pages/dashboard.py
import customtkinter as ctk
from tkinter import messagebox
from config import CARD, PRIMARY, SUCCESS, WARNING, SUBTEXT, TEXT
from widgets import ScrollablePage, SectionLabel
from utils import styled_table
from database import db 

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
                    total_students = sum(c['student_count'] or 0 for c in teacher_classes)
                    total_active = sum(c['active_count'] or 0 for c in teacher_classes)
                    class_count = len(teacher_classes)
                    
                    self.stat_cards["students"].configure(text=str(total_students))
                    self.stat_cards["active"].configure(text=str(total_active))
                    self.stat_cards["class"].configure(text=str(class_count))
                    
                    cur.execute("""
                        SELECT COUNT(DISTINCT s.id) as n
                        FROM subjects s
                        JOIN class_subjects cs ON s.id = cs.subject_id
                        JOIN classes c ON cs.class_id = c.id
                        WHERE c.teacher_id = %s AND c.is_deleted = FALSE 
                        AND s.is_deleted = FALSE AND s.status = 'Active'
                    """, (self.user_data['teacher_id'],))
                    self.stat_cards["subjects"].configure(text=cur.fetchone()["n"] or "0")
                    
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