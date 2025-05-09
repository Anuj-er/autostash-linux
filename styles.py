import tkinter as tk
from tkinter import ttk


def setup_styles(app):
        """Configure the styles for the application"""
        style = ttk.Style(app)
        style.theme_use("clam")

        # Set app theme colors
        app.white = "#ffffff" 
        app.primary_color = "#1e3799"  # Dark blue
        app.secondary_color = "#4a69bd"  # Medium blue
        app.accent_color = "#38ada9"  # Teal
        app.black = "#2c3e50"  # Dark gray
        app.bg_color = "#f5f6fa"  # Light gray
        app.text_color = "#2f3640"  # Dark gray
        app.success_color = "#44bd32"  # Green
        app.warning_color = "#e1b12c"  # Yellow
        app.error_color = "#c23616"  # Red
    
        # Frame styles
        style.configure("Card.TFrame", background=app.bg_color, borderwidth=1, relief="solid")
    
        # LabelFrame styles
        style.configure("Card.TLabelframe", background="white", borderwidth=1, 
                        relief="solid", padding=10)
        style.configure("Card.TLabelframe.Label", font=("Helvetica", 12, "bold"), 
                    background="white", foreground=app.primary_color)
    
    # Label styles
        style.configure("TLabel", background="white", foreground=app.text_color)
        style.configure("Header.TLabel", font=("Helvetica", 14, "bold"), 
                        background=app.bg_color, foreground=app.primary_color)
        style.configure("Status.TLabel", font=("Helvetica", 10), 
                    background="white", padding=5)
    
        # Button styles
        style.configure("TButton", font=("Helvetica", 10), padding=8)
        style.configure("Primary.TButton", background=app.primary_color, 
                        foreground="white", borderwidth=0)
        style.map("Primary.TButton", 
                  background=[("active", app.secondary_color), ("disabled", "#cccccc")])
    
        # Checkbutton styles
        style.configure("TCheckbutton", background="white")
    
        # Combobox styles
        style.configure("TCombobox", fieldbackground="white", padding=5)
    
        # Progress bar styles
        style.configure("TProgressbar", thickness=18, troughcolor="#e0e0e0", 
                        background=app.accent_color, bordercolor="#bdc3c7", 
                        lightcolor=app.accent_color, darkcolor=app.primary_color)
    
        # Configure CPU, Memory, and Disk progress bars
        style.configure("CPU.Horizontal.TProgressbar", background="#3498db", troughcolor="#e0e0e0")
        style.configure("MEM.Horizontal.TProgressbar", background="#9b59b6", troughcolor="#e0e0e0")
        style.configure("DISK.Horizontal.TProgressbar", background="#2ecc71", troughcolor="#e0e0e0")

        # Browse Button Style (Primary Action)
        style.configure("Browse.TButton",
                        font=("Helvetica", 10, "bold"),
                        foreground="white",
                        background=app.primary_color,
                        padding=(10, 6),
                        borderwidth=0)
        style.map("Browse.TButton",
                  background=[("active", "#163d7a")],
                  foreground=[("active", "white")])

        # Remove Button Style (Destructive Action)
        style.configure("Remove.TButton",
                        font=("Helvetica", 10, "bold"),
                        foreground="white",
                        background=app.error_color,
                        padding=(10, 6),
                        borderwidth=0)
        style.map("Remove.TButton",
                  background=[("active", "#a93226")],
                  foreground=[("active", "white")])

        # === Style for "Run Backup Now" button ===
        style.configure("Run.TButton",
                        font=("Helvetica", 10, "bold"),
                        foreground="white",
                        background=app.success_color,  # Green (success)
                        padding=(12, 6),
                        relief="flat")
        style.map("Run.TButton",
                  background=[("active", "#28a745")],  # Active state green
                  foreground=[("active", "white")])
        
        # === Style for "Restore Backup" button ===
        style.configure("Restore.TButton",
                        font=("Helvetica", 10, "bold"),
                        foreground="white",
                        background=app.secondary_color,  # Blue (restore)
                        padding=(12, 6),
                        relief="flat")
        style.map("Restore.TButton",
                  background=[("active", app.primary_color)],  # Active state blue
                  foreground=[("active", "white")])
        
        # === Style for "Advanced Options" button ===
        style.configure("Options.TButton",
                        font=("Helvetica", 10, "bold"),
                        foreground="white",
                        background="#7f8c8d",  # Neutral gray (options)
                        padding=(12, 6),
                        relief="flat")
        style.map("Options.TButton",
                  background=[("active", "#95a5a6")],  # Active state light gray
                  foreground=[("active", "white")])

        # === GitHub Button Styles ===
        # Default GitHub button style
        style.configure("GitHub.TButton",
                        font=("Helvetica", 9),
                        background="#24292e",
                        foreground="white",
                        padding=(10, 4))
        
        # Connected state style
        style.configure("Connected.TButton",
                        font=("Helvetica", 9),
                        background="#28a745",
                        foreground="white",
                        padding=(10, 4))
        
        # Error state style
        style.configure("Error.TButton",
                        font=("Helvetica", 9),
                        background="#dc3545",
                        foreground="white",
                        padding=(10, 4))
