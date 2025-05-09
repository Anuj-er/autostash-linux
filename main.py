from core.imports import *


def check_and_request_permissions():
    """Check and request necessary permissions for the application"""
    try:
        # Check if running with sudo
        if os.geteuid() == 0:
            return True

        # Check if we can write to required directories
        required_paths = [
            os.path.expanduser("~/.autostash"),
            "/var/log/autostash"
        ]

        for path in required_paths:
            if not os.path.exists(path):
                try:
                    os.makedirs(path, exist_ok=True)
                except PermissionError:
                    # Request sudo access
                    result = subprocess.run(
                        ["sudo", "mkdir", "-p", path],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode != 0:
                        raise Exception(f"Failed to create directory: {path}")

        # Check if we can write to log directory
        log_path = "/var/log/autostash"
        if not os.access(log_path, os.W_OK):
            # Request sudo access to change permissions
            result = subprocess.run(
                ["sudo", "chown", f"{os.getenv('USER')}:", log_path],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise Exception(f"Failed to set permissions for: {log_path}")

        # Check if we can access system directories for backup
        system_paths = ["/etc"]
        for path in system_paths:
            if not os.access(path, os.R_OK):
                # Request sudo access
                result = subprocess.run(
                    ["sudo", "chmod", "a+r", path],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    raise Exception(f"Failed to set read permissions for: {path}")

        return True

    except Exception as e:
        messagebox.showerror(
            "Permission Error",
            f"Failed to set up required permissions:\n{str(e)}\n\n"
            "Please run the application with sudo or contact your system administrator."
        )
        return False

class AutoStashGUI(tk.Tk):

    def __init__(self):
        super().__init__()
        
        # Check permissions before initializing
        if not check_and_request_permissions():
            self.destroy()
            sys.exit(1)
            
        self.title("AutoStash - Advanced Linux Backup System")
        self.geometry("700x1000")  # Adjusted width but kept original height
        setup_styles(self)
        self.minsize(700, 1000)  # Adjusted minimum width but kept original height
    
        # Initialize schedule timer
        self.schedule_timer = None
        self.next_backup_time = None
    
        # Configure the window
        self.configure(bg=self.black)
        self.option_add("*Font", "Helvetica 11")  # Restored original font size
    
        # Initialize resource monitor
        self.resource_monitor = ResourceMonitor()
        self.resource_monitor.register_callback(self.update_resource_display)
        self.resource_monitor.start_monitoring(interval=2.0)

    
        # Initialize managers
        self.config = ConfigManager()
        self.github = GitHubManager()
        self.backup = BackupManager()

        # Create data directory
        os.makedirs(os.path.expanduser("~/.autostash"), exist_ok=True)

        # Create main container frame with some padding
        self.main_container = tk.Frame(self, bg=self.bg_color, padx=15, pady=15)
        self.main_container.pack(fill="both", expand=True)

        # Create and initialize header
        self._create_header()
    
        # Create widgets
        self.create_widgets()
    
        # Load saved settings
        self.load_saved_settings()
        self.load_backup_timeline()
        self.check_backup_status()

    def _create_header(self):
        """Create app header with logo and description"""
        header_frame = tk.Frame(self.main_container, bg=self.bg_color)
        header_frame.pack(fill="x", pady=(0, 15))
    
        # Logo and title in the same row, centered
        logo_title_frame = tk.Frame(header_frame, bg=self.bg_color)
        logo_title_frame.pack(fill="x")
    
        # Center container for logo and title
        center_container = tk.Frame(logo_title_frame, bg=self.bg_color)
        center_container.pack(expand=True)
    
        # Simulated logo (can be replaced with an actual image)
        logo_canvas = tk.Canvas(center_container, width=50, height=50, 
                               bg=self.bg_color, highlightthickness=0)
        logo_canvas.pack(side="left")
    
        # Draw a backup icon
        logo_canvas.create_oval(10, 10, 40, 40, fill=self.primary_color, outline="")
        logo_canvas.create_rectangle(20, 5, 30, 15, fill=self.primary_color, outline="")
        logo_canvas.create_arc(15, 15, 35, 35, start=0, extent=300, 
                              style="arc", outline="white", width=2)
        logo_canvas.create_line(25, 15, 25, 25, fill="white", width=2)
        logo_canvas.create_line(25, 25, 30, 20, fill="white", width=2)
    
        # Title and subtitle
        title_frame = tk.Frame(center_container, bg=self.bg_color)
        title_frame.pack(side="left", padx=10)

        title_label = tk.Label(title_frame, text="AutoStash", 
                              font=("Helvetica", 24, "bold"), 
                              bg=self.bg_color, fg=self.primary_color)
        title_label.pack(anchor="w")

        subtitle_label = tk.Label(title_frame, 
                                 text="Smart Linux Backup System", 
                                 font=("Helvetica", 12), 
                                 bg=self.bg_color, fg=self.secondary_color)
        subtitle_label.pack(anchor="w")
    
        # Divider
        divider = ttk.Separator(header_frame, orient="horizontal")
        divider.pack(fill="x", pady=(10, 0))

    def create_widgets(self):
        # Create a notebook for tab-based organization
        self.notebook = ttk.Notebook(self.main_container)
        self.notebook.pack(fill="both", expand=True, pady=(0, 15))

        # Create tabs
        self.backup_tab = ttk.Frame(self.notebook, style="Card.TFrame")
        self.monitor_tab = ttk.Frame(self.notebook, style="Card.TFrame")
        self.history_tab = ttk.Frame(self.notebook, style="Card.TFrame")

        self.notebook.add(self.backup_tab, text="Backup Configuration")
        self.notebook.add(self.monitor_tab, text="System Monitor")
        self.notebook.add(self.history_tab, text="Backup History")

        # Set up the backup tab content
        self._create_backup_tab()

        # Set up the monitor tab content
        self._create_monitor_tab()

        # Set up the history tab content
        self._create_history_tab()

        # Create action buttons below the tabs
        self._create_action_buttons()

        # Create status bar at the bottom
        self._create_status_bar()

    def _create_backup_tab(self):
        # === Folders Frame ===
        self.folder_frame = ttk.LabelFrame(self.backup_tab, text="Backup Sources", style="Card.TLabelframe")
        self.folder_frame.pack(fill="x", pady=(5, 5), padx=8)

        folder_inner = tk.Frame(self.folder_frame, bg="white")
        folder_inner.pack(fill="x", pady=2)

        # Modern folder selection with icon
        folder_header = tk.Frame(folder_inner, bg="white")
        folder_header.pack(fill="x", pady=(0, 4))
        
        folder_icon = tk.Label(folder_header, text="📁", font=("Helvetica", 12), bg="white")
        folder_icon.pack(side="left", padx=(0, 4))
        
        folder_title = tk.Label(folder_header, text="Select Folders to Backup", 
                              font=("Helvetica", 11, "bold"), bg="white", fg="#2c3e50")
        folder_title.pack(side="left")

        # Path selection with modern styling
        path_frame = tk.Frame(folder_inner, bg="white")
        path_frame.pack(fill="x", pady=2)

        path_label = ttk.Label(path_frame, text="Path:", width=6)
        path_label.pack(side="left", padx=(0, 4))

        self.folder_entry = ttk.Entry(path_frame, width=35, font=("Helvetica", 10))
        self.folder_entry.pack(side="left", padx=(0, 4), pady=2, fill="x", expand=True)

        browse_btn = ttk.Button(path_frame, text="Browse", command=self.add_folder, 
                              style="Browse.TButton", width=8)
        browse_btn.pack(side="left", padx=(0, 4))

        remove_btn = ttk.Button(path_frame, text="Remove", command=self.remove_folder, 
                              style="Remove.TButton", width=8)
        remove_btn.pack(side="left")

        # Selected folders list with modern styling
        folder_list_frame = tk.Frame(self.folder_frame, bg="white")
        folder_list_frame.pack(fill="x", pady=2)

        folder_list_label = tk.Label(folder_list_frame, text="Selected Folders:", 
                                   font=("Helvetica", 10, "bold"), bg="white", fg="#2c3e50")
        folder_list_label.pack(anchor="w", pady=(0, 2))

        folder_listbox_frame = tk.Frame(folder_list_frame, bg="white", relief="solid", bd=1)
        folder_listbox_frame.pack(fill="both", expand=True)

        folder_scrollbar = tk.Scrollbar(folder_listbox_frame)
        folder_scrollbar.pack(side="right", fill="y")

        self.folder_list = tk.Listbox(folder_listbox_frame, width=35, height=3, 
                                    font=("Helvetica", 10), bd=0,
                                    selectbackground="#3498db", selectforeground="white",
                                    yscrollcommand=folder_scrollbar.set)
        self.folder_list.pack(side="left", fill="both", expand=True)
        folder_scrollbar.config(command=self.folder_list.yview)

        # === GitHub Repository Frame ===
        self.repo_frame = ttk.LabelFrame(self.backup_tab, text="GitHub Repository", style="Card.TLabelframe")
        self.repo_frame.pack(fill="x", pady=(5, 5), padx=8)

        repo_inner = tk.Frame(self.repo_frame, bg="white")
        repo_inner.pack(fill="x", pady=2)

        # GitHub header with icon
        github_header = tk.Frame(repo_inner, bg="white")
        github_header.pack(fill="x", pady=(0, 4))
        
        github_icon = tk.Label(github_header, text="🐙", font=("Helvetica", 12), bg="white")
        github_icon.pack(side="left", padx=(0, 4))
        
        github_title = tk.Label(github_header, text="GitHub Repository", 
                              font=("Helvetica", 11, "bold"), bg="white", fg="#2c3e50")
        github_title.pack(side="left")

        # Repository selection with modern styling
        repo_select_frame = tk.Frame(repo_inner, bg="white")
        repo_select_frame.pack(fill="x", pady=2)

        repo_label = ttk.Label(repo_select_frame, text="Repository:", width=8)
        repo_label.pack(side="left", padx=(0, 4))

        self.repo_combobox = ttk.Combobox(repo_select_frame, width=25, state="readonly",
                                        font=("Helvetica", 10))
        self.repo_combobox.pack(side="left", padx=(0, 4), pady=2, fill="x", expand=True)

        self.connect_btn = ttk.Button(repo_select_frame, text="Connect GitHub", 
                                    command=self.connect_github, style="GitHub.TButton",
                                    width=12)
        self.connect_btn.pack(side="left")

        # === Backup Options Frame ===
        self.options_frame = ttk.LabelFrame(self.backup_tab, text="Backup Options", style="Card.TLabelframe")
        self.options_frame.pack(fill="x", pady=(5, 5), padx=8)

        options_inner = tk.Frame(self.options_frame, bg="white")
        options_inner.pack(fill="x", pady=2)

        # Options header with icon
        options_header = tk.Frame(options_inner, bg="white")
        options_header.pack(fill="x", pady=(0, 4))
        
        options_icon = tk.Label(options_header, text="⚙️", font=("Helvetica", 12), bg="white")
        options_icon.pack(side="left", padx=(0, 4))
        
        options_title = tk.Label(options_header, text="Backup Configuration", 
                               font=("Helvetica", 11, "bold"), bg="white", fg="#2c3e50")
        options_title.pack(side="left")

        # Options grid with modern styling
        options_grid = tk.Frame(options_inner, bg="white")
        options_grid.pack(fill="x", pady=2)

        # Create option cards
        def create_option_card(parent, icon, text, var, row, col):
            card = tk.Frame(parent, bg="white", relief="solid", bd=1)
            card.grid(row=row, column=col, sticky="nsew", padx=4, pady=2)
            
            icon_label = tk.Label(card, text=icon, font=("Helvetica", 11), bg="white")
            icon_label.pack(side="left", padx=(4, 2))
            
            check = ttk.Checkbutton(card, text=text, variable=var, style="Option.TCheckbutton")
            check.pack(side="left", padx=(0, 4), pady=2)
            
            return card

        self.system_files_var = tk.BooleanVar(value=False)
        self.encrypt_var = tk.BooleanVar(value=False)
        self.compression_var = tk.BooleanVar(value=False)
        self.incremental_var = tk.BooleanVar(value=False)

        create_option_card(options_grid, "🔒", "Backup system files (/etc)", 
                         self.system_files_var, 0, 0)
        create_option_card(options_grid, "🔐", "Encrypt backup with GPG", 
                         self.encrypt_var, 0, 1)
        create_option_card(options_grid, "🗜️", "Use compression", 
                         self.compression_var, 1, 0)
        create_option_card(options_grid, "📈", "Use incremental backup", 
                         self.incremental_var, 1, 1)

        # === Schedule Frame ===
        self.schedule_frame = ttk.LabelFrame(self.backup_tab, text="Backup Schedule", style="Card.TLabelframe")
        self.schedule_frame.pack(fill="x", pady=(5, 5), padx=8)

        schedule_inner = tk.Frame(self.schedule_frame, bg="white")
        schedule_inner.pack(fill="x", pady=2)

        # Schedule header with icon
        schedule_header = tk.Frame(schedule_inner, bg="white")
        schedule_header.pack(fill="x", pady=(0, 4))
        
        schedule_icon = tk.Label(schedule_header, text="🕒", font=("Helvetica", 12), bg="white")
        schedule_icon.pack(side="left", padx=(0, 4))
        
        schedule_title = tk.Label(schedule_header, text="Automated Backup Schedule", 
                                font=("Helvetica", 11, "bold"), bg="white", fg="#2c3e50")
        schedule_title.pack(side="left")

        # Schedule controls with modern styling
        schedule_controls = tk.Frame(schedule_inner, bg="white")
        schedule_controls.pack(fill="x", pady=2)

        freq_label = ttk.Label(schedule_controls, text="Frequency:", width=8)
        freq_label.pack(side="left", padx=(0, 4))

        self.schedule_combobox = ttk.Combobox(schedule_controls, 
                                            values=["Daily", "Weekly", "Monthly", "Custom"], 
                                            width=10, state="readonly", font=("Helvetica", 10))
        self.schedule_combobox.current(0)
        self.schedule_combobox.pack(side="left", padx=(0, 4))

        time_label = ttk.Label(schedule_controls, text="Time:", font=("Helvetica", 10))
        time_label.pack(side="left", padx=(4, 4))

        self.hour_var = tk.StringVar(value="02")
        self.minute_var = tk.StringVar(value="00")

        hour_spinbox = ttk.Spinbox(schedule_controls, from_=0, to=23, width=3, 
                                 textvariable=self.hour_var, format="%02.0f",
                                 font=("Helvetica", 10))
        hour_spinbox.pack(side="left")

        ttk.Label(schedule_controls, text=":", font=("Helvetica", 10)).pack(side="left")

        minute_spinbox = ttk.Spinbox(schedule_controls, from_=0, to=59, width=3, 
                                   textvariable=self.minute_var, format="%02.0f",
                                   font=("Helvetica", 10))
        minute_spinbox.pack(side="left")

        set_schedule_btn = ttk.Button(schedule_controls, text="Set Schedule", 
                                    command=self.set_schedule, style="Schedule.TButton",
                                    width=10)
        set_schedule_btn.pack(side="left", padx=(8, 0))

        # === Backup Status Frame ===
        self.status_frame = ttk.LabelFrame(self.backup_tab, text="Backup Status", style="Card.TLabelframe")
        self.status_frame.pack(fill="x", pady=(5, 5), padx=8)

        status_inner = tk.Frame(self.status_frame, bg="white")
        status_inner.pack(fill="x", pady=2)

        # Status header with icon and title in a single row
        status_header = tk.Frame(status_inner, bg="white")
        status_header.pack(fill="x", pady=(0, 2))
        
        # Left side: Icon and title
        left_header = tk.Frame(status_header, bg="white")
        left_header.pack(side="left")
        
        status_icon = tk.Label(left_header, text="📊", font=("Helvetica", 12), bg="white")
        status_icon.pack(side="left", padx=(0, 4))
        
        status_title = tk.Label(left_header, text="Backup Status", 
                              font=("Helvetica", 11, "bold"), bg="white", fg="#2c3e50")
        status_title.pack(side="left")

        # Right side: Last backup info
        right_header = tk.Frame(status_header, bg="white")
        right_header.pack(side="right", padx=(0, 4))

        status_icon_label = tk.Label(right_header, text="⚠️", font=("Helvetica", 12), 
                                   bg="white", fg=self.warning_color)
        status_icon_label.pack(side="left", padx=(0, 4))

        self.last_backup_label = tk.Label(right_header, 
                                        text="No previous backups found", 
                                        fg=self.error_color, bg="white", 
                                        font=("Helvetica", 10))
        self.last_backup_label.pack(side="left")

        # Progress section with modern styling
        progress_frame = tk.Frame(status_inner, bg="white", relief="solid", bd=1)
        progress_frame.pack(fill="x", pady=2, padx=4)

        # Progress header with label and percentage
        progress_header = tk.Frame(progress_frame, bg="white")
        progress_header.pack(fill="x", pady=(4, 2), padx=4)

        progress_label = tk.Label(progress_header, text="Backup Progress", 
                                font=("Helvetica", 10, "bold"), bg="white", fg="#2c3e50")
        progress_label.pack(side="left")

        self.progress_text = tk.Label(progress_header, text="Ready", bg="white",
                                    font=("Helvetica", 10), fg="#7f8c8d")
        self.progress_text.pack(side="right")

        # Progress bar with custom styling
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                          maximum=100, style="TProgressbar", length=480)
        self.progress_bar.pack(fill="x", pady=(0, 4), padx=4)

        # Status indicators
        indicators_frame = tk.Frame(status_inner, bg="white")
        indicators_frame.pack(fill="x", pady=(0, 2), padx=4)

        def create_status_indicator(parent, icon, text, color):
            frame = tk.Frame(parent, bg="white")
            frame.pack(side="left", padx=(0, 8))
            
            icon_label = tk.Label(frame, text=icon, font=("Helvetica", 10), 
                                bg="white", fg=color)
            icon_label.pack(side="left", padx=(0, 2))
            
            text_label = tk.Label(frame, text=text, font=("Helvetica", 9),
                                bg="white", fg="#7f8c8d")
            text_label.pack(side="left")
            
            return text_label

        self.status_indicators = {
            'files': create_status_indicator(indicators_frame, "📁", "Files: 0", "#3498db"),
            'size': create_status_indicator(indicators_frame, "💾", "Size: 0 MB", "#2ecc71"),
            'time': create_status_indicator(indicators_frame, "⏱️", "Time: 0s", "#e74c3c")
        }

    def _create_monitor_tab(self):
        # === Resource Monitor Frame ===
        self.resource_frame = ttk.LabelFrame(self.monitor_tab, text="System Resources", style="Card.TLabelframe")
        self.resource_frame.pack(fill="x", pady=5, padx=10)

        resource_inner = tk.Frame(self.resource_frame, bg="white")
        resource_inner.pack(fill="x", pady=2)

        # Title with modern styling
        title_frame = tk.Frame(resource_inner, bg="white")
        title_frame.pack(fill="x", pady=(0, 8))

        monitor_icon = tk.Label(title_frame, text="📊", font=("Helvetica", 14), bg="white")
        monitor_icon.pack(side="left", padx=(0, 8))

        monitor_title = tk.Label(title_frame, text="System Resource Monitor", 
                               font=("Helvetica", 12, "bold"), bg="white", fg="#2c3e50")
        monitor_title.pack(side="left")

        # Create custom styles for progress bars
        style = ttk.Style()
        style.configure("CPU.Horizontal.TProgressbar", troughcolor='#f0f0f0', background='#3498db')
        style.configure("MEM.Horizontal.TProgressbar", troughcolor='#f0f0f0', background='#2ecc71')
        style.configure("DISK.Horizontal.TProgressbar", troughcolor='#f0f0f0', background='#e74c3c')

        # Create a modern card-style container for each resource
        def create_resource_card(parent, icon, title, color):
            card = tk.Frame(parent, bg="white", relief="solid", bd=1)
            card.pack(fill="x", pady=4, padx=5)
            
            # Header with icon and title
            header = tk.Frame(card, bg="white")
            header.pack(fill="x", pady=(6, 2), padx=8)
            
            # Icon with background
            icon_frame = tk.Frame(header, bg=color, width=24, height=24)
            icon_frame.pack(side="left", padx=(0, 8))
            icon_frame.pack_propagate(False)
            
            icon_label = tk.Label(icon_frame, text=icon, font=("Helvetica", 12), 
                                bg=color, fg="white")
            icon_label.pack(expand=True)
            
            # Title and value in same row
            title_frame = tk.Frame(header, bg="white")
            title_frame.pack(side="left", fill="x", expand=True)
            
            title_label = tk.Label(title_frame, text=title, font=("Helvetica", 11, "bold"), 
                                 bg="white", fg="#2c3e50")
            title_label.pack(side="left")
            
            value_label = tk.Label(title_frame, text="0%", font=("Helvetica", 11, "bold"),
                                 bg="white", fg=color)
            value_label.pack(side="right")
            
            # Progress bar container
            progress_frame = tk.Frame(card, bg="white")
            progress_frame.pack(fill="x", pady=(0, 6), padx=8)
            
            # Progress bar with custom style
            progress_var = tk.DoubleVar()
            progress = ttk.Progressbar(progress_frame, variable=progress_var,
                                     length=300, maximum=100,
                                     style=f"{title}.Horizontal.TProgressbar")
            progress.pack(fill="x", expand=True)
            
            # Add percentage indicator above progress bar
            def update_progress(value):
                progress_var.set(value)
                value_label.config(text=f"{value:.1f}%")
                
                # Update colors based on value
                if value < 50:
                    # Green for low usage
                    value_label.config(fg="#27ae60")
                    style.configure(f"{title}.Horizontal.TProgressbar", 
                                  background='#27ae60', troughcolor='#f0f0f0')
                elif value < 80:
                    # Orange for medium usage
                    value_label.config(fg="#f39c12")
                    style.configure(f"{title}.Horizontal.TProgressbar", 
                                  background='#f39c12', troughcolor='#f0f0f0')
                else:
                    # Red for high usage
                    value_label.config(fg="#e74c3c")
                    style.configure(f"{title}.Horizontal.TProgressbar", 
                                  background='#e74c3c', troughcolor='#f0f0f0')
                
                # Update progress bar color
                progress.configure(style=f"{title}.Horizontal.TProgressbar")
            
            progress_var.trace_add("write", lambda *args: update_progress(progress_var.get()))
            
            return card, value_label, progress_var

        # Create resource cards with custom colors
        self.cpu_card, self.cpu_label, self.cpu_progress_var = create_resource_card(
            resource_inner, "⚡", "CPU", "#3498db")
        
        self.memory_card, self.memory_label, self.memory_progress_var = create_resource_card(
            resource_inner, "🧠", "MEM", "#2ecc71")
        
        self.disk_card, self.disk_label, self.disk_progress_var = create_resource_card(
            resource_inner, "💾", "DISK", "#e74c3c")

        # Resource warning message with modern styling
        warning_frame = tk.Frame(resource_inner, bg="white")
        warning_frame.pack(fill="x", pady=(8, 2))

        warning_icon = tk.Label(warning_frame, text="⚠️", font=("Helvetica", 14), 
                              bg="white", fg=self.warning_color)
        warning_icon.pack(side="left", padx=(0, 4))

        self.resource_warning = tk.Label(warning_frame, text="", fg=self.error_color, 
                                       bg="white", font=("Helvetica", 9))
        self.resource_warning.pack(side="left", fill="x")

        # === System Information Frame ===
        self.sysinfo_frame = ttk.LabelFrame(self.monitor_tab, text="System Information", style="Card.TLabelframe")
        self.sysinfo_frame.pack(fill="x", pady=(8, 10), padx=10)

        sysinfo_inner = tk.Frame(self.sysinfo_frame, bg="white")
        sysinfo_inner.pack(fill="x", pady=2)

        # Title with icon
        sysinfo_title_frame = tk.Frame(sysinfo_inner, bg="white")
        sysinfo_title_frame.pack(fill="x", pady=(0, 8))

        sysinfo_icon = tk.Label(sysinfo_title_frame, text="ℹ️", font=("Helvetica", 14), bg="white")
        sysinfo_icon.pack(side="left", padx=(0, 8))

        sysinfo_title = tk.Label(sysinfo_title_frame, text="System Details", 
                               font=("Helvetica", 12, "bold"), bg="white", fg="#2c3e50")
        sysinfo_title.pack(side="left")

        # System info in a modern grid layout
        info_grid = tk.Frame(sysinfo_inner, bg="white")
        info_grid.pack(fill="x", pady=2)

        # Create info rows with icons
        def create_info_row(parent, icon, label, value, row, color):
            frame = tk.Frame(parent, bg="white")
            frame.grid(row=row, column=0, sticky="w", padx=8, pady=4)
            
            # Icon with background
            icon_frame = tk.Frame(frame, bg=color, width=24, height=24)
            icon_frame.pack(side="left", padx=(0, 8))
            icon_frame.pack_propagate(False)
            
            icon_label = tk.Label(icon_frame, text=icon, font=("Helvetica", 12), 
                                bg=color, fg="white")
            icon_label.pack(expand=True)
            
            label_frame = tk.Frame(frame, bg="white")
            label_frame.pack(side="left")
            
            label_text = tk.Label(label_frame, text=label, font=("Helvetica", 9, "bold"),
                                bg="white", fg="#7f8c8d")
            label_text.pack(anchor="w")
            
            value_label = tk.Label(label_frame, text=value, font=("Helvetica", 9),
                                 bg="white", fg="#2c3e50")
            value_label.pack(anchor="w")
            
            return value_label

        # Create system info rows with custom colors
        self.os_info = create_info_row(info_grid, "💻", "Operating System", get_os_info(), 0, "#3498db")
        self.cpu_info = create_info_row(info_grid, "⚡", "CPU", get_cpu_info(), 1, "#2ecc71")
        self.memory_info = create_info_row(info_grid, "🧠", "Memory", get_memory_info(), 2, "#e74c3c")
        self.disk_info = create_info_row(info_grid, "💾", "Disk Space", get_disk_info(), 3, "#f39c12")

    def _create_history_tab(self):
        # === Backup Timeline Frame ===
        self.timeline_frame = ttk.LabelFrame(self.history_tab, text="Backup History", style="Card.TLabelframe")
        self.timeline_frame.pack(fill="both", expand=True, pady=10, padx=10)

        timeline_inner = tk.Frame(self.timeline_frame, bg="white")
        timeline_inner.pack(fill="both", expand=True, pady=5)

        # Header with icon and title
        header_frame = tk.Frame(timeline_inner, bg="white")
        header_frame.pack(fill="x", pady=(0, 10))

        history_icon = tk.Label(header_frame, text="📅", font=("Helvetica", 16), bg="white")
        history_icon.pack(side="left", padx=(0, 10))

        title_frame = tk.Frame(header_frame, bg="white")
        title_frame.pack(side="left")

        title_label = tk.Label(title_frame, text="Backup Timeline", 
                             font=("Helvetica", 14, "bold"), bg="white", fg="#2c3e50")
        title_label.pack(anchor="w")

        subtitle_label = tk.Label(title_frame, text="Latest backups first", 
                                font=("Helvetica", 10), bg="white", fg="#7f8c8d")
        subtitle_label.pack(anchor="w")

        # Search and filter frame
        filter_frame = tk.Frame(timeline_inner, bg="white")
        filter_frame.pack(fill="x", pady=(0, 10))

        search_frame = tk.Frame(filter_frame, bg="white", relief="solid", bd=1)
        search_frame.pack(side="left", padx=(0, 10))

        search_icon = tk.Label(search_frame, text="🔍", font=("Helvetica", 12), bg="white")
        search_icon.pack(side="left", padx=5)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._filter_backups)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side="left", padx=(0, 5), pady=2)

        # Timeline with scrollbar
        timeline_container = tk.Frame(timeline_inner, bg="white")
        timeline_container.pack(fill="both", expand=True)

        self.timeline_scrollbar = tk.Scrollbar(timeline_container)
        self.timeline_scrollbar.pack(side="right", fill="y")

        # Configure listbox colors
        self.timeline_list = tk.Listbox(timeline_container, 
                                      font=("Helvetica", 10),
                                      bg="white",
                                      fg="#2c3e50",  # Dark text color
                                      selectbackground="#3498db",
                                      selectforeground="white",
                                      activestyle="none",
                                      bd=0,
                                      highlightthickness=0,
                                      yscrollcommand=self.timeline_scrollbar.set)
        self.timeline_list.pack(side="left", fill="both", expand=True)
        self.timeline_scrollbar.config(command=self.timeline_list.yview)

        # Add right-click menu for timeline entries
        self.timeline_menu = tk.Menu(self.timeline_list, tearoff=0)
        self.timeline_menu.add_command(label="View Details", command=self._view_backup_details)
        self.timeline_menu.add_command(label="Restore This Backup", command=self._restore_selected_backup)
        self.timeline_menu.add_separator()
        self.timeline_menu.add_command(label="Delete", command=self._delete_selected_backup)

        self.timeline_list.bind("<Button-3>", self._show_timeline_menu)
        self.timeline_list.bind("<Double-1>", self._view_backup_details)

        # Status bar for timeline
        status_frame = tk.Frame(timeline_inner, bg="white")
        status_frame.pack(fill="x", pady=(10, 0))

        self.timeline_status = tk.Label(status_frame, text="", 
                                      font=("Helvetica", 9),
                                      bg="white", fg="#7f8c8d")
        self.timeline_status.pack(side="left")

    def _filter_backups(self, *args):
        """Filter backup entries based on search text"""
        search_text = self.search_var.get().lower()
        self.timeline_list.delete(0, tk.END)
        
        history_path = os.path.expanduser("~/.autostash/backup_history")
        if os.path.exists(history_path):
            with open(history_path, "r") as f:
                lines = [line.strip() for line in f if line.strip()]
            
            # Filter and show matching entries
            filtered_entries = [line for line in reversed(lines) 
                              if search_text in line.lower()]
            
            for line in filtered_entries:
                self.timeline_list.insert(tk.END, line)
            
            # Update status
            self.timeline_status.config(
                text=f"Showing {len(filtered_entries)} of {len(lines)} backups"
            )
        else:
            self.timeline_status.config(text="No backup history found")

    def load_backup_timeline(self):
        """Load backup history into the timeline"""
        try:
            # Sync with repository history first
            self.backup.sync_backup_history()
            
            # Verify and repair history file if needed
            self.backup.verify_and_repair_history()
            
            self.timeline_list.delete(0, tk.END)
            history_path = os.path.expanduser("~/.autostash/backup_history")
            if os.path.exists(history_path):
                with open(history_path, "r") as f:
                    lines = [line.strip() for line in f if line.strip()]
                
                # Show latest entries at the top
                for line in reversed(lines):
                    try:
                        backup_data = json.loads(line)
                        # Format timestamp for display
                        display_time = datetime.datetime.strptime(
                            backup_data['timestamp'], "%Y%m%d_%H%M"
                        ).strftime("%Y-%m-%d %H:%M")
                        
                        # Create a formatted display string
                        display_text = (
                            f"Backup: {display_time} | "
                            f"Type: {backup_data['type']} | "
                            f"Files: {backup_data['total_files']} | "
                            f"Size: {backup_data['total_size']}"
                        )
                        
                        # Store the full backup data as a tuple with the display text
                        self.timeline_list.insert(tk.END, (display_text, line))
                    except json.JSONDecodeError:
                        # Handle old format entries
                        self.timeline_list.insert(tk.END, (line, line))
                
                # Update status
                self.timeline_status.config(
                    text=f"Showing {len(lines)} backups"
                )
            else:
                self.timeline_status.config(text="No backup history found")
                
        except Exception as e:
            self.timeline_status.config(text=f"Error loading backup history: {str(e)}")
            messagebox.showerror("Error", f"Failed to load backup history: {str(e)}")

    def add_folder(self):
        folder = filedialog.askdirectory()
        if folder and folder not in self.folder_list.get(0, tk.END):
            self.folder_list.insert(tk.END, folder)
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder)
            self.config.save_folders(self.folder_list.get(0, tk.END))

    def remove_folder(self):
        sel = self.folder_list.curselection()
        if sel:
            self.folder_list.delete(sel)
            self.config.save_folders(self.folder_list.get(0, tk.END))
            self.folder_entry.delete(0, tk.END)

    def connect_github(self):
        token = keyring.get_password("autostash", "github_token")
        if not token:
            from tkinter.simpledialog import askstring
            token = askstring("GitHub Token", "Enter your GitHub Personal Access Token:", show='*')
            if not token:
                self.status_var.set("GitHub connection cancelled.")
                return
            keyring.set_password("autostash", "github_token", token)
        try:
            self.github.authenticate(token)
            repos = self.github.get_repos()
            self.repo_combobox['values'] = repos
            if repos:
                self.repo_combobox.current(0)
            # Update button appearance for connected state
            self.connect_btn.configure(text="Connected ✓", style="Connected.TButton")
            self.status_var.set("GitHub connected. Select a repository.")
        except Exception as e:
            # Update button appearance for error state
            self.connect_btn.configure(text="Connection Failed", style="Error.TButton")
            self.status_var.set(f"GitHub error: {e}")

    def create_new_repo(self):
        """Create a new GitHub repository for backup"""
        from tkinter.simpledialog import askstring
        repo_name = askstring("New Repository", 
                            "Enter a name for your backup repository:",
                            initialvalue="autostash-backup")
        if not repo_name:
            return
        
        try:
            # Create the repository
            repo = self.github.create_repository(repo_name)
            
            # Update the repository list
            repos = self.github.get_repos()
            self.repo_combobox['values'] = repos
            self.repo_combobox.set(repo)
            
            messagebox.showinfo("Success", 
                              f"Repository '{repo}' created successfully!\n"
                              "You can now use it for backups.")
            
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def run_backup(self):
        folders = self.folder_list.get(0, tk.END)
        repo = self.repo_combobox.get()
        if not folders:
            messagebox.showerror("Missing Info", "Please select at least one folder to backup.")
            return
        
        if not repo:
            if messagebox.askyesno("No Repository", 
                                 "No repository selected. Would you like to create a new one?"):
                self.create_new_repo()
                repo = self.repo_combobox.get()
                if not repo:
                    return
            else:
                return

        self.status_var.set("Running backup...")
        self.update_idletasks()
        self.progress_var.set(0)
        self.progress_bar.update()
        self.is_backup_running = True  # Flag for resource monitoring

        # Clear previous resource warnings
        self.resource_warning.config(text="")

        def progress_callback(percent, message=None):
            self.progress_var.set(percent)
            if message:
                self.progress_text.config(text=message)

            # Get current resource usage during backup
            resources = self.resource_monitor.get_current_usage()

            # Show warning if resources are critically high during backup
            warnings = []
            if resources['cpu'] > 90:
                warnings.append(f"CPU usage critical: {resources['cpu']:.1f}%")
            if resources['memory'] > 90:
                warnings.append(f"Memory usage critical: {resources['memory']:.1f}%")
            if resources['disk'] > 95:
                warnings.append(f"Disk usage critical: {resources['disk']:.1f}%")

            if warnings:
                warning_text = " | ".join(warnings)
                self.resource_warning.config(text=f"⚠️ {warning_text} - Backup may be affected")
                # Optionally slow down the backup process when resources are critical
                time.sleep(0.5)  # Brief pause to ease system load

            self.update_idletasks()

        try:
            # Get all backup options
            backup_system = self.system_files_var.get()
            encrypt = self.encrypt_var.get()
            compress = self.compression_var.get()
            incremental = self.incremental_var.get()

            # Run backup with all options
            self.backup.run(
                folders, repo,
                backup_system=backup_system,
                encrypt=encrypt,
                compress=compress,
                incremental=incremental,
                progress_callback=progress_callback
            )
            self.status_var.set("Backup completed successfully!")
            self.progress_text.config(text="Backup complete ✓", fg="#27ae60")
            messagebox.showinfo("Backup", "Backup completed successfully!")
            self.check_backup_status()
            self.load_backup_timeline()
        except Exception as e:
            self.status_var.set(f"Backup failed: {e}")
            self.progress_text.config(text="Backup failed ⚠️", fg="#c0392b")
            messagebox.showerror("Backup Failed", str(e))
        finally:
            self.is_backup_running = False  # Reset backup flag
            self.resource_warning.config(text="")  # Clear any resource warnings

    def restore_backup(self):
        repo = self.repo_combobox.get()
        if not repo:
            messagebox.showerror("Missing Repo", "Please select a GitHub repository first.")
            return

        # Create backup selection window
        backup_window = tk.Toplevel(self)
        backup_window.title("Select Backup to Restore")
        backup_window.geometry("1000x700")
        backup_window.transient(self)
        backup_window.grab_set()

        # Header
        header_frame = tk.Frame(backup_window, bg="white")
        header_frame.pack(fill="x", pady=10, padx=15)

        icon_label = tk.Label(header_frame, text="📦", font=("Helvetica", 16), bg="white")
        icon_label.pack(side="left", padx=(0, 10))

        title_label = tk.Label(header_frame, text="Select Backup to Restore", 
                             font=("Helvetica", 14, "bold"), bg="white", fg="#2c3e50")
        title_label.pack(side="left")

        # Create a frame for the backup list and details
        content_frame = tk.Frame(backup_window, bg="white")
        content_frame.pack(fill="both", expand=True, padx=15, pady=10)

        # Left side: Backup list
        list_frame = tk.Frame(content_frame, bg="white")
        list_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        list_header = tk.Label(list_frame, text="Available Backups", 
                             font=("Helvetica", 11, "bold"), bg="white", fg="#2c3e50")
        list_header.pack(anchor="w", pady=(0, 5))

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        backup_list = tk.Listbox(list_frame, 
                               font=("Helvetica", 10),
                               bg="white",
                               fg="#2c3e50",
                               selectbackground="#3498db",
                               selectforeground="white",
                               activestyle="none",
                               bd=0,
                               highlightthickness=0,
                               yscrollcommand=scrollbar.set)
        backup_list.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=backup_list.yview)

        # Right side: Backup details
        details_frame = tk.Frame(content_frame, bg="white")
        details_frame.pack(side="right", fill="both", expand=True)

        details_header = tk.Label(details_frame, text="Backup Details", 
                                font=("Helvetica", 11, "bold"), bg="white", fg="#2c3e50")
        details_header.pack(anchor="w", pady=(0, 5))

        # Create a text widget with scrollbar for details
        details_scrollbar = tk.Scrollbar(details_frame)
        details_scrollbar.pack(side="right", fill="y")

        details_text = tk.Text(details_frame, 
                             font=("Helvetica", 10),
                             bg="white",
                             fg="#2c3e50",
                             wrap=tk.WORD,
                             height=25,
                             width=60,
                             yscrollcommand=details_scrollbar.set)
        details_text.pack(fill="both", expand=True)
        details_scrollbar.config(command=details_text.yview)

        # Load backup history into list
        history_path = os.path.expanduser("~/.autostash/backup_history")
        if os.path.exists(history_path):
            with open(history_path, "r") as f:
                lines = [line.strip() for line in f if line.strip()]
            
            # Show latest entries at the top
            for line in reversed(lines):
                try:
                    backup_data = json.loads(line)
                    # Format timestamp for display
                    display_time = datetime.datetime.strptime(
                        backup_data['timestamp'], "%Y%m%d_%H%M"
                    ).strftime("%Y-%m-%d %H:%M")
                    
                    # Create a formatted display string
                    display_text = (
                        f"Backup: {display_time} | "
                        f"Type: {backup_data['type']} | "
                        f"Files: {backup_data['total_files']}"
                    )
                    
                    # Store the full backup data as a tuple with the display text
                    backup_list.insert(tk.END, (display_text, line))
                except json.JSONDecodeError:
                    backup_list.insert(tk.END, (line, line))

        def show_backup_details(event):
            selection = backup_list.curselection()
            if selection:
                backup_entry = backup_list.get(selection)[1]
                try:
                    backup_data = json.loads(backup_entry)
                    # Format timestamp for display
                    display_time = datetime.datetime.strptime(
                        backup_data['timestamp'], "%Y%m%d_%H%M"
                    ).strftime("%Y-%m-%d %H:%M")
                    
                    # Create detailed information
                    details = (
                        f"Backup Details\n"
                        f"==============\n\n"
                        f"Timestamp: {display_time}\n"
                        f"Type: {backup_data['type']}\n"
                        f"Total Files: {backup_data['total_files']}\n"
                        f"Changed Files: {backup_data['changed_files']}\n"
                        f"Total Size: {backup_data['total_size']}\n"
                        f"Backup Name: {backup_data.get('backup_name', 'N/A')}\n\n"
                        f"Backed up folders:\n"
                        f"-----------------\n"
                    )
                    for folder_name, original_path in backup_data['folders'].items():
                        details += f"• {folder_name}: {original_path}\n"
                    
                    details_text.delete("1.0", tk.END)
                    details_text.insert("1.0", details)
                except json.JSONDecodeError:
                    details_text.delete("1.0", tk.END)
                    details_text.insert("1.0", "Invalid backup entry format")

        backup_list.bind("<<ListboxSelect>>", show_backup_details)

        # Status label
        status_label = tk.Label(backup_window, text="", bg="white", fg="#7f8c8d")
        status_label.pack(pady=5)

        # Button frame
        button_frame = tk.Frame(backup_window, bg="white")
        button_frame.pack(fill="x", pady=15, padx=15)

        def on_restore():
            selection = backup_list.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a backup to restore.")
                return

            backup_entry = backup_list.get(selection)[1]
            try:
                backup_data = json.loads(backup_entry)
                
                # Ask for confirmation
                confirm_msg = (
                    f"Are you sure you want to restore this backup?\n\n"
                    f"Timestamp: {datetime.datetime.strptime(backup_data['timestamp'], '%Y%m%d_%H%M').strftime('%Y-%m-%d %H:%M')}\n"
                    f"Type: {backup_data['type']}\n"
                    f"Total Files: {backup_data['total_files']}\n\n"
                    f"This will restore files to their original locations:\n"
                )
                for folder_name, original_path in backup_data['folders'].items():
                    confirm_msg += f"- {original_path}\n"
                
                if not messagebox.askyesno("Confirm Restore", confirm_msg):
                    return

                self.status_var.set("Restoring backup...")
                status_label.config(text="Restoring backup...", fg="#3498db")
                backup_window.update_idletasks()

                try:
                    # Get the backup folder name from metadata
                    backup_folder = backup_data.get('backup_name')
                    if not backup_folder:
                        raise Exception("Backup folder name not found in metadata")

                    # Call restore with the specific backup folder
                    result = self.backup.restore(repo, backup_folder)
                    
                    self.status_var.set("Restore completed successfully!")
                    status_label.config(text="Restore completed successfully!", fg="#27ae60")
                    
                    # Show success message with details
                    success_msg = (
                        f"Backup has been restored successfully!\n\n"
                        f"Files restored: {result['files_restored']}\n"
                        f"Total size: {result['total_size']} bytes\n"
                        f"Restore path: {result['path']}\n\n"
                        f"Would you like to open the restore location?"
                    )
                    
                    if messagebox.askyesno("Restore Complete", success_msg):
                        # Open the restore location in Finder
                        subprocess.run(["open", result['path']])
                    
                    # Close the backup selection window
                    backup_window.destroy()
                    
                except Exception as e:
                    self.status_var.set(f"Restore failed: {e}")
                    status_label.config(text=f"Restore failed: {e}", fg="#e74c3c")
                    messagebox.showerror("Restore Failed", str(e))
                
            except Exception as e:
                self.status_var.set(f"Restore failed: {e}")
                status_label.config(text=f"Restore failed: {e}", fg="#e74c3c")
                messagebox.showerror("Restore Failed", str(e))

        def on_cancel():
            backup_window.destroy()

        # Add buttons
        restore_btn = ttk.Button(button_frame, text="Restore Selected", 
                               command=on_restore, style="Restore.TButton")
        restore_btn.pack(side="left", padx=5)

        cancel_btn = ttk.Button(button_frame, text="Cancel", 
                              command=on_cancel)
        cancel_btn.pack(side="right", padx=5)

        # Add double-click handler
        def on_double_click(event):
            on_restore()

        backup_list.bind("<Double-1>", on_double_click)

        # Center the window
        backup_window.update_idletasks()
        width = backup_window.winfo_width()
        height = backup_window.winfo_height()
        x = (backup_window.winfo_screenwidth() // 2) - (width // 2)
        y = (backup_window.winfo_screenheight() // 2) - (height // 2)
        backup_window.geometry(f'{width}x{height}+{x}+{y}')

    def set_schedule(self):
        """Set up automated backup schedule"""
        try:
            # Create schedule configuration dictionary
            schedule_config = {
                "frequency": self.schedule_combobox.get(),
                "hour": self.hour_var.get(),
                "minute": self.minute_var.get()
            }
            
            # Set up the schedule
            setup_schedule(schedule_config, os.path.abspath(__file__))
            
            # Calculate next backup time
            self._calculate_next_backup_time(schedule_config)
            
            # Start the schedule timer
            self._start_schedule_timer()
            
            # Update status
            self.status_var.set(f"Scheduled backups: {schedule_config['frequency'].lower()}.")
            messagebox.showinfo("Schedule", 
                              f"Backups scheduled: {schedule_config['frequency']}\n"
                              f"Time: {schedule_config['hour']}:{schedule_config['minute']}")
            
            # Save schedule to config
            self.config.save_settings({"schedule": schedule_config})
            
        except Exception as e:
            self.status_var.set(f"Schedule failed: {e}")
            messagebox.showerror("Schedule Failed", str(e))

    def _calculate_next_backup_time(self, schedule_config):
        """Calculate the next scheduled backup time"""
        now = datetime.datetime.now()
        hour = int(schedule_config['hour'])
        minute = int(schedule_config['minute'])
        
        # Create the next backup time
        next_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # If the time has already passed today, schedule for next occurrence
        if next_time <= now:
            if schedule_config['frequency'] == 'Daily':
                next_time += datetime.timedelta(days=1)
            elif schedule_config['frequency'] == 'Weekly':
                days_until_sunday = (6 - now.weekday()) % 7
                next_time += datetime.timedelta(days=days_until_sunday)
            elif schedule_config['frequency'] == 'Monthly':
                # Move to first day of next month
                if now.month == 12:
                    next_time = next_time.replace(year=now.year + 1, month=1)
                else:
                    next_time = next_time.replace(month=now.month + 1)
        
        self.next_backup_time = next_time

    def _start_schedule_timer(self):
        """Start the timer to update the next backup time display"""
        if self.schedule_timer:
            self.after_cancel(self.schedule_timer)
        
        def update_timer():
            if self.next_backup_time:
                now = datetime.datetime.now()
                time_left = self.next_backup_time - now
                
                if time_left.total_seconds() <= 0:
                    # Recalculate next backup time
                    schedule_config = self.config.get_settings().get('schedule', {})
                    self._calculate_next_backup_time(schedule_config)
                    time_left = self.next_backup_time - now
                
                # Format the time remaining
                days = time_left.days
                hours = time_left.seconds // 3600
                minutes = (time_left.seconds % 3600) // 60
                
                if days > 0:
                    time_str = f"{days}d {hours}h {minutes}m"
                elif hours > 0:
                    time_str = f"{hours}h {minutes}m"
                else:
                    time_str = f"{minutes}m"
                
                # Update the status label
                self.status_var.set(f"Next backup in: {time_str}")
            
            # Schedule next update
            self.schedule_timer = self.after(60000, update_timer)  # Update every minute
        
        # Start the timer
        update_timer()

    def load_saved_settings(self):
        """Load saved settings and initialize schedule timer"""
        folders = self.config.get_folders()
        for folder in folders:
            self.folder_list.insert(tk.END, folder)
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder)
        
        # Load schedule settings
        settings = self.config.get_settings()
        schedule_config = settings.get('schedule', {})
        if schedule_config:
            self.schedule_combobox.set(schedule_config.get('frequency', 'Daily'))
            self.hour_var.set(schedule_config.get('hour', '02'))
            self.minute_var.set(schedule_config.get('minute', '00'))
            
            # Calculate and start schedule timer
            self._calculate_next_backup_time(schedule_config)
            self._start_schedule_timer()

    def update_resource_display(self, cpu, memory, disk):
        """Update the resource monitor display with current values"""
        try:
            # Check if the window is still valid
            if not self.winfo_exists():
                return

            # Update labels with current usage
            if hasattr(self, 'cpu_label') and self.cpu_label.winfo_exists():
                self.cpu_label.config(text=f"{cpu:.1f}%")
            if hasattr(self, 'memory_label') and self.memory_label.winfo_exists():
                self.memory_label.config(text=f"{memory:.1f}%")
            if hasattr(self, 'disk_label') and self.disk_label.winfo_exists():
                self.disk_label.config(text=f"{disk:.1f}%")

            # Update progress bars
            if hasattr(self, 'cpu_progress_var'):
                self.cpu_progress_var.set(cpu)
            if hasattr(self, 'memory_progress_var'):
                self.memory_progress_var.set(memory)
            if hasattr(self, 'disk_progress_var'):
                self.disk_progress_var.set(disk)

            # Set colors based on thresholds
            if hasattr(self, 'cpu_label') and self.cpu_label.winfo_exists():
                self._set_resource_color(self.cpu_label, cpu, 50, 80)
            if hasattr(self, 'memory_label') and self.memory_label.winfo_exists():
                self._set_resource_color(self.memory_label, memory, 60, 80)
            if hasattr(self, 'disk_label') and self.disk_label.winfo_exists():
                self._set_resource_color(self.disk_label, disk, 70, 90)

            # Display warning if threshold exceeded during backup
            if hasattr(self, 'is_backup_running') and self.is_backup_running:
                warnings = []
                if cpu > 85:
                    warnings.append(f"CPU usage critical: {cpu:.1f}%")
                if memory > 85:
                    warnings.append(f"Memory usage critical: {memory:.1f}%")
                if disk > 90:
                    warnings.append(f"Disk usage critical: {disk:.1f}%")

                if warnings and hasattr(self, 'resource_warning') and self.resource_warning.winfo_exists():
                    self.resource_warning.config(text=f"⚠️ {' | '.join(warnings)}")
                elif hasattr(self, 'resource_warning') and self.resource_warning.winfo_exists():
                    self.resource_warning.config(text="")

        except Exception as e:
            print(f"Error updating resource display: {str(e)}")

    def _set_resource_color(self, label, value, warning_threshold, critical_threshold):
        """Set the color of a resource label based on the value"""
        try:
            if not label.winfo_exists():
                return
                
            if value < warning_threshold:
                label.config(fg="#27ae60")  # Green
            elif value < critical_threshold:
                label.config(fg="#f39c12")  # Orange/Yellow
            else:
                label.config(fg="#e74c3c")  # Red
        except Exception as e:
            print(f"Error setting resource color: {str(e)}")

    def destroy(self):
        """Override destroy to stop resource monitoring thread"""
        try:
            if hasattr(self, 'resource_monitor'):
                self.resource_monitor.stop_monitoring()
            super().destroy()
        except Exception as e:
            print(f"Error during window destruction: {str(e)}")
            super().destroy()

    def _show_timeline_menu(self, event):
        """Show the context menu for timeline entries"""
        try:
            self.timeline_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.timeline_menu.grab_release()
        
    def _view_backup_details(self, event=None):
        """Show details for the selected backup"""
        sel = self.timeline_list.curselection()
        if sel:
            backup_entry = self.timeline_list.get(sel)[1]  # Get the full backup data
            try:
                # Parse the JSON backup entry
                backup_data = json.loads(backup_entry)
                
                # Create a details window
                details_window = tk.Toplevel(self)
                details_window.title("Backup Details")
                details_window.geometry("600x500")
                details_window.transient(self)
                details_window.grab_set()

                # Add details content
                header_frame = tk.Frame(details_window, bg="white")
                header_frame.pack(fill="x", pady=10, padx=15)

                icon_label = tk.Label(header_frame, text="📋", font=("Helvetica", 16), bg="white")
                icon_label.pack(side="left", padx=(0, 10))

                title_label = tk.Label(header_frame, text="Backup Details", 
                                     font=("Helvetica", 14, "bold"), bg="white", fg="#2c3e50")
                title_label.pack(side="left")

                # Details content
                content_frame = tk.Frame(details_window, bg="white")
                content_frame.pack(fill="both", expand=True, padx=15, pady=10)

                # Create detail rows with icons
                def create_detail_row(parent, icon, label, value, row):
                    frame = tk.Frame(parent, bg="white")
                    frame.pack(fill="x", pady=5)
                    
                    icon_label = tk.Label(frame, text=icon, font=("Helvetica", 12), bg="white")
                    icon_label.pack(side="left", padx=(0, 8))
                    
                    label_text = tk.Label(frame, text=label, font=("Helvetica", 10, "bold"),
                                        bg="white", fg="#7f8c8d", width=15, anchor="w")
                    label_text.pack(side="left", padx=(0, 10))
                    
                    value_text = tk.Label(frame, text=value, font=("Helvetica", 10),
                                        bg="white", fg="#2c3e50")
                    value_text.pack(side="left")

                # Format timestamp for display
                display_time = datetime.datetime.strptime(
                    backup_data['timestamp'], "%Y%m%d_%H%M"
                ).strftime("%Y-%m-%d %H:%M")

                # Add all backup details
                create_detail_row(content_frame, "🕒", "Date:", display_time, 0)
                create_detail_row(content_frame, "📁", "Total Files:", str(backup_data['total_files']), 1)
                create_detail_row(content_frame, "📝", "Changed Files:", str(backup_data['changed_files']), 2)
                create_detail_row(content_frame, "💾", "Total Size:", backup_data['total_size'], 3)
                create_detail_row(content_frame, "🔄", "Backup Type:", backup_data['type'], 4)
                create_detail_row(content_frame, "📂", "Backup Name:", backup_data.get('backup_name', 'N/A'), 5)

                # Add backed up folders section
                folders_frame = tk.Frame(content_frame, bg="white")
                folders_frame.pack(fill="x", pady=10)

                folders_label = tk.Label(folders_frame, text="Backed Up Folders:", 
                                       font=("Helvetica", 10, "bold"), bg="white", fg="#7f8c8d")
                folders_label.pack(anchor="w", pady=(0, 5))

                # Create a frame for the folders list with scrollbar
                folders_list_frame = tk.Frame(folders_frame, bg="white", relief="solid", bd=1)
                folders_list_frame.pack(fill="both", expand=True)

                folders_scrollbar = tk.Scrollbar(folders_list_frame)
                folders_scrollbar.pack(side="right", fill="y")

                folders_list = tk.Listbox(folders_list_frame, 
                                        font=("Helvetica", 10),
                                        bg="white",
                                        fg="#2c3e50",
                                        yscrollcommand=folders_scrollbar.set,
                                        height=6)
                folders_list.pack(side="left", fill="both", expand=True)
                folders_scrollbar.config(command=folders_list.yview)

                # Add folders to the list
                for folder_name, original_path in backup_data['folders'].items():
                    folders_list.insert(tk.END, f"{folder_name}: {original_path}")

                # Add restore button
                def on_restore():
                    if messagebox.askyesno("Confirm Restore", 
                                         "Are you sure you want to restore this backup?"):
                        details_window.destroy()
                        self.restore_backup()  # This will use the selected backup

                restore_btn = ttk.Button(details_window, text="Restore This Backup", 
                                       command=on_restore, style="Restore.TButton")
                restore_btn.pack(pady=15)

                # Close button
                close_btn = ttk.Button(details_window, text="Close", 
                                     command=details_window.destroy)
                close_btn.pack(pady=(0, 15))

                # Center the window
                details_window.update_idletasks()
                width = details_window.winfo_width()
                height = details_window.winfo_height()
                x = (details_window.winfo_screenwidth() // 2) - (width // 2)
                y = (details_window.winfo_screenheight() // 2) - (height // 2)
                details_window.geometry(f'{width}x{height}+{x}+{y}')
                
            except json.JSONDecodeError:
                messagebox.showerror("Error", "Invalid backup entry format")
            except Exception as e:
                messagebox.showerror("Error", f"Error displaying backup details: {str(e)}")

    def _restore_selected_backup(self):
        """Restore the selected backup"""
        sel = self.timeline_list.curselection()
        if sel:
            backup_entry = self.timeline_list.get(sel)
            if messagebox.askyesno("Confirm Restore", 
                                 f"Are you sure you want to restore:\n{backup_entry}?"):
                self.status_var.set(f"Attempting to restore: {backup_entry}")
                # Call your restore logic here
            
    def _delete_selected_backup(self):
        """Delete the selected backup"""
        sel = self.timeline_list.curselection()
        if sel:
            backup_entry = self.timeline_list.get(sel)
            if messagebox.askyesno("Confirm Delete", 
                                 f"Are you sure you want to delete:\n{backup_entry}?"):
                self.status_var.set(f"Deleting backup: {backup_entry}")
                # Call your delete logic here
                self.timeline_list.delete(sel)
                self.load_backup_timeline()  # Refresh the list

    def _create_action_buttons(self):
        """Create action buttons for the main interface"""
        action_frame = tk.Frame(self.main_container, bg=self.bg_color)
        action_frame.pack(fill="x", pady=10)

        button_container = tk.Frame(action_frame, bg=self.white)
        button_container.pack()

        # Use grid for better alignment
        run_btn = ttk.Button(button_container, text="Run Backup Now",
                           command=self.run_backup, style="Run.TButton")
        run_btn.grid(row=0, column=0, padx=5, pady=5)

        restore_btn = ttk.Button(button_container, text="Restore Backup",
                               command=self.restore_backup, style="Restore.TButton")
        restore_btn.grid(row=0, column=1, padx=5, pady=5)

        options_btn = ttk.Button(button_container, text="Advanced Options",
                               command=self._show_advanced_options, style="Options.TButton")
        options_btn.grid(row=0, column=2, padx=5, pady=5)

    def _create_status_bar(self):
        """Create the status bar at the bottom of the window"""
        self.status_var = tk.StringVar()
        self.status_var.set("Ready. AutoStash initialized successfully.")
        self.status_bar = tk.Label(self, textvariable=self.status_var, 
                                 bg="#ecf0f1", fg="#34495e", 
                                 anchor="w", font=("Helvetica", 10),
                                 relief="sunken", bd=1, pady=5, padx=10)
        self.status_bar.pack(side="bottom", fill="x")

    def _show_advanced_options(self):
        """Show the advanced options window"""
        options_window = tk.Toplevel(self)
        options_window.title("Advanced Options")
        options_window.geometry("600x500")
        options_window.resizable(False, False)
        options_window.transient(self)
        options_window.grab_set()

        # Main container with padding
        main_frame = tk.Frame(options_window, bg="white", padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)

        # Header
        header_frame = tk.Frame(main_frame, bg="white")
        header_frame.pack(fill="x", pady=(0, 20))

        icon_label = tk.Label(header_frame, text="⚙️", font=("Helvetica", 16), bg="white")
        icon_label.pack(side="left", padx=(0, 10))

        title_label = tk.Label(header_frame, text="Advanced Options", 
                             font=("Helvetica", 14, "bold"), bg="white", fg="#2c3e50")
        title_label.pack(side="left")

        # Create notebook for tabbed interface
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True)

        # Configuration Tab
        config_frame = ttk.Frame(notebook)
        notebook.add(config_frame, text="Configuration")

        # Export/Import Section
        config_section = ttk.LabelFrame(config_frame, text="Backup Configuration")
        config_section.pack(fill="x", padx=10, pady=5)

        def export_config():
            file_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
                title="Export Configuration"
            )
            if file_path:
                try:
                    config_data = {
                        "folders": self.folder_list.get(0, tk.END),
                        "repository": self.repo_combobox.get(),
                        "options": {
                            "backup_system": self.system_files_var.get(),
                            "encrypt": self.encrypt_var.get(),
                            "compress": self.compression_var.get(),
                            "incremental": self.incremental_var.get()
                        },
                        "schedule": {
                            "frequency": self.schedule_combobox.get(),
                            "hour": self.hour_var.get(),
                            "minute": self.minute_var.get()
                        }
                    }
                    with open(file_path, 'w') as f:
                        json.dump(config_data, f, indent=4)
                    messagebox.showinfo("Success", "Configuration exported successfully!")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to export configuration: {str(e)}")

        def import_config():
            file_path = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json")],
                title="Import Configuration"
            )
            if file_path:
                try:
                    with open(file_path, 'r') as f:
                        config_data = json.load(f)
                    
                    # Update folders
                    self.folder_list.delete(0, tk.END)
                    for folder in config_data.get("folders", []):
                        self.folder_list.insert(tk.END, folder)
                    
                    # Update repository
                    if config_data.get("repository"):
                        self.repo_combobox.set(config_data["repository"])
                    
                    # Update options
                    options = config_data.get("options", {})
                    self.system_files_var.set(options.get("backup_system", False))
                    self.encrypt_var.set(options.get("encrypt", False))
                    self.compression_var.set(options.get("compress", False))
                    self.incremental_var.set(options.get("incremental", False))
                    
                    # Update schedule
                    schedule = config_data.get("schedule", {})
                    self.schedule_combobox.set(schedule.get("frequency", "Daily"))
                    self.hour_var.set(schedule.get("hour", "02"))
                    self.minute_var.set(schedule.get("minute", "00"))
                    
                    messagebox.showinfo("Success", "Configuration imported successfully!")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to import configuration: {str(e)}")

        ttk.Button(config_section, text="Export Configuration", 
                  command=export_config).pack(pady=5, anchor="w", padx=10)
        ttk.Button(config_section, text="Import Configuration", 
                  command=import_config).pack(pady=5, anchor="w", padx=10)

        # Maintenance Tab
        maintenance_frame = ttk.Frame(notebook)
        notebook.add(maintenance_frame, text="Maintenance")

        # Backup Verification Section
        verify_section = ttk.LabelFrame(maintenance_frame, text="Backup Verification")
        verify_section.pack(fill="x", padx=10, pady=5)

        def verify_backups():
            try:
                self.status_var.set("Verifying backups...")
                result = self.backup.verify_backups()
                if result["status"] == "success":
                    messagebox.showinfo("Verification Complete", 
                                      f"All backups verified successfully!\n\n"
                                      f"Total backups checked: {result['total']}\n"
                                      f"Verified: {result['verified']}\n"
                                      f"Failed: {result['failed']}")
                else:
                    messagebox.showwarning("Verification Issues", 
                                         f"Some backups failed verification:\n\n"
                                         f"Total backups checked: {result['total']}\n"
                                         f"Verified: {result['verified']}\n"
                                         f"Failed: {result['failed']}\n\n"
                                         f"Failed backups: {', '.join(result['failed_backups'])}")
            except Exception as e:
                messagebox.showerror("Error", f"Verification failed: {str(e)}")
            finally:
                self.status_var.set("Ready")

        def cleanup_old_backups():
            try:
                # Ask for retention period
                retention = tk.simpledialog.askinteger(
                    "Cleanup Old Backups",
                    "Enter number of days to retain backups:",
                    minvalue=1,
                    maxvalue=365,
                    initialvalue=30
                )
                if retention:
                    self.status_var.set("Cleaning up old backups...")
                    result = self.backup.cleanup_old_backups(retention)
                    messagebox.showinfo("Cleanup Complete", 
                                      f"Cleanup completed successfully!\n\n"
                                      f"Backups removed: {result['removed']}\n"
                                      f"Space freed: {result['space_freed']}")
            except Exception as e:
                messagebox.showerror("Error", f"Cleanup failed: {str(e)}")
            finally:
                self.status_var.set("Ready")

        def cleanup_all_backups():
            if messagebox.askyesno("Confirm Cleanup", 
                                 "Are you sure you want to delete ALL backups?\nThis action cannot be undone!"):
                try:
                    self.status_var.set("Cleaning up all backups...")
                    result = self.backup.cleanup_all_backups()
                    messagebox.showinfo("Cleanup Complete", 
                                      f"All backups have been removed successfully!\n\n"
                                      f"Space freed: {result['space_freed']} bytes")
                    # Refresh the backup timeline
                    self.load_backup_timeline()
                except Exception as e:
                    messagebox.showerror("Error", f"Cleanup failed: {str(e)}")
                finally:
                    self.status_var.set("Ready")

        ttk.Button(verify_section, text="Verify All Backups", 
                  command=verify_backups).pack(pady=5, anchor="w", padx=10)
        ttk.Button(verify_section, text="Cleanup Old Backups", 
                  command=cleanup_old_backups).pack(pady=5, anchor="w", padx=10)
        ttk.Button(verify_section, text="Cleanup ALL Backups", 
                  command=cleanup_all_backups).pack(pady=5, anchor="w", padx=10)

        # Security Tab
        security_frame = ttk.Frame(notebook)
        notebook.add(security_frame, text="Security")

        # Encryption Settings Section
        security_section = ttk.LabelFrame(security_frame, text="Encryption Settings")
        security_section.pack(fill="x", padx=10, pady=5)

        def manage_gpg_keys():
            key_window = tk.Toplevel(options_window)
            key_window.title("GPG Key Management")
            key_window.geometry("400x300")
            key_window.transient(options_window)
            key_window.grab_set()

            # Add key management interface here
            ttk.Label(key_window, text="GPG Key Management").pack(pady=10)
            ttk.Button(key_window, text="Import Key").pack(pady=5)
            ttk.Button(key_window, text="Export Key").pack(pady=5)
            ttk.Button(key_window, text="Generate New Key").pack(pady=5)

        ttk.Button(security_section, text="Manage GPG Keys", 
                  command=manage_gpg_keys).pack(pady=5, anchor="w", padx=10)

        # Close button
        close_btn = ttk.Button(main_frame, text="Close", 
                             command=options_window.destroy)
        close_btn.pack(pady=(20, 0))

        # Center the window
        options_window.update_idletasks()
        width = options_window.winfo_width()
        height = options_window.winfo_height()
        x = (options_window.winfo_screenwidth() // 2) - (width // 2)
        y = (options_window.winfo_screenheight() // 2) - (height // 2)
        options_window.geometry(f'{width}x{height}+{x}+{y}')

    def check_backup_status(self):
        """Check and update the backup status"""
        last_backup = self.backup.get_last_backup_time()
        if last_backup:
            try:
                backup_time = datetime.datetime.strptime(last_backup, "%Y-%m-%d %H:%M:%S")
                now = datetime.datetime.now()
                self.last_backup_label.config(
                    text=f"Last backup: {backup_time.strftime('%Y-%m-%d %H:%M')}", 
                    fg="#c0392b"
                )
                if (now - backup_time).total_seconds() > 24 * 60 * 60:
                    self.last_backup_label.config(fg="#c0392b")
                    try:
                        days = (now - backup_time).days
                        subprocess.run([
                            "notify-send",
                            "AutoStash Backup Overdue",
                            f"Last backup was {days} days ago"
                        ])
                    except:
                        pass
                else:
                    self.last_backup_label.config(fg="#27ae60")
            except Exception as e:
                self.last_backup_label.config(
                    text=f"Error reading backup time: {str(e)}", 
                    fg="#c0392b"
                )
        else:
            self.last_backup_label.config(text="No previous backups found", fg="#c0392b")
        self.after(3600000, self.check_backup_status)

    def show_error(self, message, title="Error"):
        """Show error message with detailed information"""
        error_dialog = tk.Toplevel(self)
        error_dialog.title(title)
        error_dialog.geometry("400x200")
        error_dialog.transient(self)
        error_dialog.grab_set()

        error_label = tk.Label(error_dialog, text=message, fg="red")
        error_label.pack(padx=10, pady=10)

        close_btn = tk.Button(error_dialog, text="Close", command=error_dialog.destroy)
        close_btn.pack(pady=10)

    def show_success(self, message, title="Success"):
        """Show success message"""
        messagebox.showinfo(title, message)

    def update_status(self, message, timeout=0):
        """Update status bar with message and optional timeout"""
        self.status_bar.config(text=message)
        if timeout > 0:
            self.after(timeout, lambda: self.status_bar.config(text=""))

    def start_backup(self):
        """Start the backup process with enhanced status updates"""
        if not self.validate_inputs():
            return

        # Get backup options
        backup_system = self.system_var.get()
        encrypt = self.encrypt_var.get()
        compress = self.compress_var.get()
        incremental = self.incremental_var.get()

        # Get folders to backup
        folders = [folder.strip() for folder in self.folder_entry.get().split(',') if folder.strip()]

        # Get repository name
        repo = self.repo_entry.get().strip()

        # Update status
        self.status_label.config(text="Starting backup...")
        self.progress_var.set(0)
        self.root.update()

        # Start backup in a separate thread
        def backup_thread():
            try:
                # Initialize backup manager
                backup_manager = BackupManager()
                
                # Create progress callback
                def update_progress(progress, status):
                    self.progress_var.set(progress)
                    self.status_label.config(text=status)
                    self.root.update()

                # Start backup with progress updates
                result = backup_manager.run(
                    folders=folders,
                    repo_name=repo,
                    backup_system=backup_system,
                    encrypt=encrypt,
                    compress=compress,
                    incremental=incremental,
                    progress_callback=update_progress
                )

                # Update final status
                if result['status'] == 'success':
                    self.status_label.config(text=f"Backup completed successfully!")
                    # Update backup info
                    self.update_backup_info(result)
                else:
                    self.status_label.config(text=f"Backup failed: {result.get('error', 'Unknown error')}")

            except Exception as e:
                self.status_label.config(text=f"Backup failed: {str(e)}")
                messagebox.showerror("Backup Error", str(e))

        # Start backup thread
        threading.Thread(target=backup_thread, daemon=True).start()

    def update_backup_info(self, result):
        """Update backup information display with dynamic data"""
        try:
            # Update file count
            self.file_count_label.config(text=f"Files: {result.get('total_files', 0)}")
            
            # Update total size
            total_size = result.get('total_size', '0 B')
            self.size_label.config(text=f"Size: {total_size}")
            
            # Update last backup time
            timestamp = result.get('timestamp', '')
            if timestamp:
                self.last_backup_label.config(text=f"Last Backup: {timestamp}")
            
            # Update backup name
            backup_name = result.get('backup_name', '')
            if backup_name:
                self.backup_name_label.config(text=f"Backup: {backup_name}")
            
            # Update status
            self.status_label.config(text="Backup completed successfully!")
            
            # Update progress
            self.progress_var.set(100)
            
            # Force GUI update
            self.root.update()
            
        except Exception as e:
            self.logger.error(f"Error updating backup info: {str(e)}")

    def create_backup_frame(self):
        """Create the backup configuration frame with dynamic status updates"""
        backup_frame = ttk.LabelFrame(self.root, text="Backup Configuration", padding="10")
        backup_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")

        # Repository entry
        ttk.Label(backup_frame, text="Repository (username/repo):").grid(row=0, column=0, sticky="w")
        self.repo_entry = ttk.Entry(backup_frame, width=40)
        self.repo_entry.grid(row=0, column=1, padx=5, pady=5)

        # Folder entry
        ttk.Label(backup_frame, text="Folders to backup (comma-separated):").grid(row=1, column=0, sticky="w")
        self.folder_entry = ttk.Entry(backup_frame, width=40)
        self.folder_entry.grid(row=1, column=1, padx=5, pady=5)

        # Options frame
        options_frame = ttk.Frame(backup_frame)
        options_frame.grid(row=2, column=0, columnspan=2, pady=5)

        # Backup options
        self.system_var = tk.BooleanVar()
        self.encrypt_var = tk.BooleanVar()
        self.compress_var = tk.BooleanVar()
        self.incremental_var = tk.BooleanVar(value=True)

        ttk.Checkbutton(options_frame, text="Backup System Files", variable=self.system_var).grid(row=0, column=0, padx=5)
        ttk.Checkbutton(options_frame, text="Encrypt Backup", variable=self.encrypt_var).grid(row=0, column=1, padx=5)
        ttk.Checkbutton(options_frame, text="Compress Backup", variable=self.compress_var).grid(row=0, column=2, padx=5)
        ttk.Checkbutton(options_frame, text="Incremental Backup", variable=self.incremental_var).grid(row=0, column=3, padx=5)

        # Status frame
        status_frame = ttk.LabelFrame(backup_frame, text="Backup Status", padding="5")
        status_frame.grid(row=3, column=0, columnspan=2, pady=5, sticky="ew")

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        # Status label
        self.status_label = ttk.Label(status_frame, text="Ready")
        self.status_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=5)

        # Backup info frame
        info_frame = ttk.Frame(status_frame)
        info_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        # File count
        self.file_count_label = ttk.Label(info_frame, text="Files: 0")
        self.file_count_label.grid(row=0, column=0, sticky="w", padx=5)

        # Total size
        self.size_label = ttk.Label(info_frame, text="Size: 0 B")
        self.size_label.grid(row=0, column=1, sticky="w", padx=5)

        # Last backup time
        self.last_backup_label = ttk.Label(info_frame, text="Last Backup: Never")
        self.last_backup_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=5)

        # Backup name
        self.backup_name_label = ttk.Label(info_frame, text="Backup: None")
        self.backup_name_label.grid(row=2, column=0, columnspan=2, sticky="w", padx=5)

        # Start backup button
        ttk.Button(backup_frame, text="Start Backup", command=self.start_backup).grid(row=4, column=0, columnspan=2, pady=10)


if __name__ == "__main__":
    app = AutoStashGUI()
    app.mainloop()
