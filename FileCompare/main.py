
import flet as ft
from ui_components import SidebarButton, StatCard, get_app_theme, DuplicateGroup
from database import DatabaseManager
from database import DatabaseManager
from scanner_engine import FileScanner, HashStrategy, XXHashStrategy, Blake3Strategy, Shake128Strategy, SHA256Strategy
from profiler import Profiler, DriveDetector
from config_manager import ConfigManager
import threading
import queue
import time
import asyncio
import os

class ScanItem(ft.Container):
    def __init__(self, path: str, drive_type: str, on_delete, on_type_change):
        initial_value = drive_type if drive_type != "Unknown" else "HDD"
        
        # Color coding
        def get_icon(dtype):
            if dtype == "SSD": return ft.Icons.MEMORY
            return ft.Icons.STORAGE

        def get_color(dtype):
            if dtype == "SSD": return ft.Colors.GREEN
            return ft.Colors.ORANGE

        self.icon = ft.Icon(get_icon(initial_value), color=get_color(initial_value))

        self.dropdown = ft.Dropdown(
            options=[
                ft.dropdown.Option("SSD"), 
                ft.dropdown.Option("HDD"),
                ft.dropdown.Option("Network")
            ],
            value=initial_value,
            text_size=11,
            height=30,
            width=100,
            content_padding=5,
            filled=True,
            bgcolor=ft.Colors.BLACK12,
            border_color=ft.Colors.TRANSPARENT
        )
        self.dropdown.on_change = lambda e: self._on_change(e.control.value, path, on_type_change)

        super().__init__(
            content=ft.Row([
                self.icon,
                ft.Column([
                    ft.Text(path, weight="bold", size=12, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                    self.dropdown
                ], expand=True),
                ft.IconButton(ft.Icons.DELETE, on_click=lambda _: on_delete(path))
            ]),
            bgcolor="#333333",
            padding=10,
            border_radius=10,
            # visual hint that it's interactive
            border=ft.Border.all(1, ft.Colors.WHITE10)
        )

    def _on_change(self, new_val, path, callback):
        # Update Icon
        if new_val == "SSD":
            self.icon.name = ft.Icons.MEMORY
            self.icon.color = ft.Colors.GREEN
        else:
            self.icon.name = ft.Icons.STORAGE
            self.icon.color = ft.Colors.ORANGE
        self.icon.update()
        callback(path, new_val)


class DedupeApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Titan File Deduplicator"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.theme = get_app_theme()
        self.page.padding = 0
        
        # Core
        self.config = ConfigManager()
        # Enforce "Reset to Recommended" logic on startup as requested
        self.config.set("hash_algo", "auto")
        
        # Benchmark (Run Once Logic)
        saved_scores = self.config.get("benchmark_scores")
        if saved_scores:
             print("Loading cached benchmark scores...")
             self.system_profile = Profiler().hydrate_profile(saved_scores, self.config.get("recommended_algo"))
        else:
             print("First run: Executing benchmark...")
             self.system_profile = Profiler().run_benchmark(enabled=True)
             # Save results
             self.config.set("benchmark_scores", self.system_profile.scores)
             self.config.set("recommended_algo", self.system_profile.recommended_algo)
        
        self.db = DatabaseManager()
        # Ensure fresh start
        self.db.clear_db()
        
        self.scanner = FileScanner(
            self.db, 
            num_workers=self.system_profile.recommended_workers,
            on_progress=self.on_scan_progress
        )
        self.duplicates_state = {} # Init for safety
        
        # State
        self.scan_paths = [] # List of {'path': str, 'type': str}
        self.duplicates_state = {}
        self.is_scanning = False
        self.has_scanned = False
        self.progress_data = None
        
        # UI Components
        self.path_list_view = ft.ListView(expand=True, spacing=5)
        self.path_input = ft.TextField(
            label="Add Folder Path", 
            value="C:\\", 
            text_size=14, 
            expand=True,
            border_color=ft.Colors.WHITE24,
            on_submit=self.add_path_manual
        )
        self.scan_progress = ft.ProgressBar(width=400, color="amber", bgcolor="#222222", value=0)
        self.status_text = ft.Text("Ready to Scan", color="white54")
        self.files_scanned_text = ft.Text("0", size=40, weight="bold")
        self.start_btn = ft.FilledButton(
            "Start Scan", 
            icon=ft.Icons.PLAY_ARROW, 
            style=ft.ButtonStyle(bgcolor=ft.Colors.INDIGO, color=ft.Colors.WHITE),
            on_click=self.start_scan,
            disabled=True
        )
        
        # Build UI
        self.init_ui()

    def init_ui(self):
        # Sidebar Buttons
        self.sidebar_buttons = {
            "dashboard": SidebarButton(ft.Icons.DASHBOARD, "Dashboard", selected=True, on_click=lambda _: self.navigate_to("dashboard")),
            "results": SidebarButton(ft.Icons.LIST, "Results", on_click=lambda _: self.navigate_to("results")),
            "settings": SidebarButton(ft.Icons.SETTINGS, "Settings", on_click=lambda _: self.navigate_to("settings")),
        }

        # Sidebar
        sidebar = ft.Container(
            content=ft.Column([
                ft.Text("TITAN", size=30, weight="bold", color=ft.Colors.INDIGO_400),
                ft.Divider(color=ft.Colors.WHITE24),
                self.sidebar_buttons["dashboard"],
                self.sidebar_buttons["results"],
                self.sidebar_buttons["settings"],
            ]),
            width=250,
            bgcolor="#1a1a1a",
            padding=20,
        )

        # Main Content Area
        self.main_content_area = ft.Column(expand=True) # Container for views
        # Main Layout
        self.page.add(
            ft.Row([
                sidebar,
                ft.VerticalDivider(width=1, color=ft.Colors.WHITE12),
                self.main_content_area
            ], expand=True)
        )
        
        self.navigate_to("dashboard")

    def navigate_to(self, view_name):
        # Prevent navigation while scanning (unless it's the auto-switch to results)
        if self.is_scanning and view_name != "results":
             # If we are scanning, we usually block. 
             # BUT: The auto-switch at the end calls navigate_to("results") AFTER setting is_scanning=False.
             # So if is_scanning is True, it MUST be a manual click.
             # Wait, what if the user wants to go back to Dashboard during a scan? (They are already there).
             # Efficiently, just block all changes if is_scanning is True.
             # Note: ui_loop sets is_scanning=False BEFORE calling navigate_to("results").
             # So this check effectively blocks ALL manual clicks during scan.
             self.page.show_snack_bar(ft.SnackBar(content=ft.Text("Please wait for the scan to complete."), duration=2000))
             return

        self.current_view = view_name
        
        # Update sidebar
        for name, btn in self.sidebar_buttons.items():
            # Hack: Update internal container properties of SidebarButton
            # We should probably expose a set_selected method on SidebarButton, 
            # but modifying the control works if we understand the structure.
            # Wrapper logic: Re-instantiating might be cleaner or just updating visual props.
            # Given SidebarButton inherits Container, we can update bgcolor.
            is_selected = (name == view_name)
            btn.bgcolor = ft.Colors.WHITE10 if is_selected else None
            
            # Content is Row -> [Icon, Text]
            icon = btn.content.controls[0]
            text = btn.content.controls[1]
            icon.color = ft.Colors.WHITE if is_selected else ft.Colors.WHITE54
            text.color = ft.Colors.WHITE if is_selected else ft.Colors.WHITE54
            text.weight = "bold" if is_selected else "normal"
            btn.update()

        # Build view
        self.main_content_area.controls.clear()
        
        if view_name == "dashboard":
            self.main_content_area.controls.append(self.build_dashboard_view())
        elif view_name == "results":
             # Always attempt to show results (scanner determines if empty)
             self.show_results(None) 
        elif view_name == "settings":
            self.main_content_area.controls.append(self.build_settings_view())
            
        self.page.update()

    def build_dashboard_view(self):
        return ft.Column(
            [
                ft.Text("Scan Dashboard", size=24, weight="bold"),
                ft.Container(height=20),
                
                # Hardware Info
                ft.Row([
                    ft.Icon(ft.Icons.MEMORY, color=ft.Colors.GREEN),
                    ft.Text(f"System Optimized: Using {self.system_profile.recommended_workers} threads ({self.system_profile.recommended_algo})")
                ]),
                
                ft.Container(height=20),
                
                # Path Selection Area
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.IconButton(ft.Icons.FOLDER_OPEN, tooltip="Browse Folder", on_click=self.browse_folder, icon_color=ft.Colors.INDIGO_400),
                            self.path_input,
                            ft.IconButton(ft.Icons.ADD, tooltip="Add to List", on_click=self.add_path_manual)
                        ]),
                        ft.Container(height=10),
                        ft.Text("Selected Locations:", size=16),
                        ft.Container(
                            content=self.path_list_view,
                            height=150,
                            bgcolor="#262626",
                            border_radius=5,
                            padding=5
                        )
                    ]),
                    bgcolor="#262626",
                    padding=20,
                    border_radius=10,
                ),
                
                ft.Container(height=20),
                
                # Scan Controls
                ft.Container(
                    content=ft.Column([
                        ft.Row([self.start_btn]),
                        ft.Container(height=10),
                        self.files_scanned_text,
                        self.scan_progress,
                        self.status_text
                    ]),
                    bgcolor="#262626",
                    padding=20,
                    border_radius=10,
                ),
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO
        )

    def safe_show_snackbar(self, message: str):
        """Robust snackbar display that handles different Flet API versions."""
        sb = ft.SnackBar(content=ft.Text(message))
        try:
            # Modern Flet (0.21+)
            if hasattr(self.page, "open"):
                self.page.open(sb)
            # Older Flet
            elif hasattr(self.page, "show_snack_bar"):
                self.page.show_snack_bar(sb)
            # Legacy Flet
            elif hasattr(self.page, "snack_bar"):
                self.page.snack_bar = sb
                sb.open = True
                self.page.update()
            else:
                # Fallback - Silent failure in production to avoid console clutter
                pass
        except Exception:
            # Silent catch
            pass

    def build_settings_view(self):
        # Determine options with "Recommended" tag
        options = []
        rec_algo = self.system_profile.recommended_algo
        
        for algo in ["xxhash", "sha256", "shake_128", "blake3"]:
            text = algo
            if algo == rec_algo:
                text += " (Recommended)"
            options.append(ft.dropdown.Option(key=algo, text=text))

        # Current selection (use config if set, else auto)
        current_algo = self.config.get("hash_algo")
        
        # Bit Length Config
        current_len = self.config.get("hash_length", 256)
        
        # Determine Bit Length Options based on Algo
        bit_len_options = []
        is_fixed = False
        
        # Resolve effective algo (handle 'auto')
        effective_algo = current_algo
        if effective_algo == "auto": effective_algo = rec_algo
        
        if effective_algo == "xxhash":
             current_len = 64
             bit_len_options = [ft.dropdown.Option("64")]
             is_fixed = True
        elif effective_algo == "sha256":
             current_len = 256
             bit_len_options = [ft.dropdown.Option("256")]
             is_fixed = True
        else:
             # Variable length algos
             bit_len_options = [
                ft.dropdown.Option("128"),
                ft.dropdown.Option("256"),
                ft.dropdown.Option("512"),
             ]
             is_fixed = False
        
        # Validation: Ensure current_len is in options
        # If we switched from xxHash (64) to BLAKE3, 64 is invalid.
        valid_keys = [opt.key for opt in bit_len_options]
        # Flet Option key defaults to text if key is None, but here we used init with positional text? 
        # Actually my options above are ft.dropdown.Option("128"). key="128" text="128".
        
        if str(current_len) not in valid_keys:
            # Fallback
            if is_fixed:
                 current_len = int(valid_keys[0])
            else:
                 current_len = 256 # Default for variable
        
        self.bit_length_dropdown = ft.Dropdown(
            label="Hash Output Size (Bits)",
            value=str(current_len),
            options=bit_len_options,
            width=200,
            disabled=is_fixed, 
        )
        # Force bind for reliability
        self.bit_length_dropdown.on_change = self.on_length_change
        self.bit_length_dropdown.on_select = self.on_length_change
        
        target_algo = current_algo
        if current_algo == "auto":
            target_algo = rec_algo
            
        current_algo = target_algo

        self.algo_dropdown = ft.Dropdown(
            label="Hashing Algorithm",
            value=current_algo,
            options=options,
        )
        # Attempting binding based on inspection results
        if hasattr(self.algo_dropdown, "on_change"):
             self.algo_dropdown.on_change = self.on_algo_change
        
        # Fallback bindings for this version
        setattr(self.algo_dropdown, "on_change", self.on_algo_change) # Force it anyway?
        if hasattr(self.algo_dropdown, "on_select"):
             self.algo_dropdown.on_select = self.on_algo_change
        if hasattr(self.algo_dropdown, "on_click"):
             self.algo_dropdown.on_click = self.on_algo_change
        
        
        
        rerun_bench_btn = ft.FilledButton(
            "Rerun Hardware Benchmark",
            icon=ft.Icons.SPEED,
            on_click=self.rerun_benchmark,
            tooltip="Re-evaluate system performance."
        )
        # benchmark_toggle.on_change = self.on_benchmark_toggle # Removed
        
        benchmark_explainer = ft.Text(
             "Measures CPU performance to determine optimal thread count and algorithm.",
             size=12,
             color=ft.Colors.WHITE54
        )
        
        
        # Populate text based on current config/profile
        active_algo = self.algo_dropdown.value
        
        # Helper to update context
        def update_context():
             algo = self.algo_dropdown.value
             bit_len = int(self.bit_length_dropdown.value)
             
             # Try specific key first (e.g. blake3_512), fallback to base
             score_key = f"{algo}_{bit_len}"
             score = self.system_profile.scores.get(score_key)
             if score is None:
                 score = self.system_profile.scores.get(algo, 0)
                 
             ctx = self.system_profile.get_context(algo, score, bit_length=bit_len)
             text1.value = ctx["prefix"]
             text2.value = ctx["suitability"]
             text3.value = ctx["probability"]
             text4.value = ctx["suffix"]
             text3_container.tooltip = ctx["tooltip"]
             explanation_row.update()
        
        # Store for access
        self.update_context_fn = update_context

        if True: # Always show context now
             score = self.system_profile.scores.get(active_algo, 0)
             ctx = self.system_profile.get_context(active_algo, score, bit_length=int(current_len))
        else:
             score = self.system_profile.scores.get(active_algo, 0)
             ctx = self.system_profile.get_context(active_algo, score, bit_length=int(current_len))
        
        text1 = ft.Text(ctx["prefix"], size=14, italic=True, color=ft.Colors.GREY_400)
        
        text2 = ft.Text(
             ctx["suitability"],
             size=14,
             italic=True,
             color=ft.Colors.GREY_400 
        )
        
        text3 = ft.Text(
            ctx["probability"], 
            size=14, 
            italic=True, 
            weight="bold", 
            color=ft.Colors.GREEN_400 
        )
        
        text4 = ft.Text(
             ctx["suffix"],
             size=14,
             italic=True,
             color=ft.Colors.GREY_400 
        )
        
        # Interactive part wrapper
        text3_container = ft.Container(
            content=text3,
            tooltip=ctx["tooltip"],
            padding=ft.Padding.only(bottom=1), 
            border=ft.Border.only(bottom=ft.border.BorderSide(1, ft.Colors.WHITE24))
        )
        
        # Combined Row
        explanation_row = ft.Row(
            controls=[text1, text2, text3_container, text4],
            wrap=True,
            spacing=0, # Tight spacing for sentence flow
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.START
        )
             

        
        
        # Initialize Controls
        self.ignore_ext_input = ft.TextField(label=".ext", width=100, on_submit=self.add_ignore_ext_manual)
        
        # Min Size Logic
        ms_bytes = self.config.get("min_file_size", 0)
        ms_val = ms_bytes
        ms_unit = "KB"
        if ms_bytes > 0:
            if ms_bytes % (1024**4) == 0: ms_val, ms_unit = ms_bytes // (1024**4), "TB"
            elif ms_bytes % (1024**3) == 0: ms_val, ms_unit = ms_bytes // (1024**3), "GB"
            elif ms_bytes % (1024**2) == 0: ms_val, ms_unit = ms_bytes // (1024**2), "MB"
            # Default to KB (even if perfectly divisible by 1024, or if smaller)
            else: 
                ms_val, ms_unit = round(ms_bytes / 1024, 1), "KB"
                if ms_val == int(ms_val): ms_val = int(ms_val) # Clean up .0
        else:
             ms_val, ms_unit = 0, "KB"
            
        self.min_size_input = ft.TextField(
            label="Min Size", 
            value=str(ms_val), 
            width=100, 
            on_change=self.update_min_size_combined,
            input_filter=ft.InputFilter(regex_string=r"^\d*\.?\d{0,1}$")
        )
        self.min_size_unit = ft.Dropdown(
            options=[ft.dropdown.Option(u) for u in ["KB", "MB", "GB", "TB"]],
            value=ms_unit,
            width=100
        )
        self.min_size_unit.on_change = self.update_min_size_combined

        return ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, controls=[
            ft.Text("Settings", size=24, weight="bold"),
            ft.Container(height=20),
            
            # Benchmark Section
            ft.Text("Performance Tuning", size=18, weight="bold"),
            rerun_bench_btn,
            benchmark_explainer,
            ft.Container(height=10),
            
            ft.Container(height=20),
            
            # Hashing Section
            ft.Text("Scanning Strategy", size=18, weight="bold"),
            ft.Text("1TB is equal to roughly 250 million 4KB files.", size=12, italic=True, color=ft.Colors.WHITE54),
            ft.Row([self.algo_dropdown, self.bit_length_dropdown]),
            explanation_row,
            
            ft.Container(height=20),
            
            # Global Configuration
            ft.Text("Global Configuration", size=18, weight="bold"),
            ft.Row([
                (theme_d := ft.Dropdown(
                    label="Theme",
                    value=self.config.get("theme_mode", "system"),
                    options=[
                        ft.dropdown.Option("system", "System Default"),
                        ft.dropdown.Option("dark", "Dark Mode"),
                        ft.dropdown.Option("light", "Light Mode"),
                    ],
                    width=200
                )),
                (threads_d := ft.Dropdown(
                    label="Threads",
                    value=str(self.config.get("thread_count", "auto")),
                    options=[ft.dropdown.Option("auto", "Auto")] + [ft.dropdown.Option(str(i), str(i)) for i in [1, 2, 4, 8, 16]],
                    width=120
                )),
                self.min_size_input,
                self.min_size_unit,
            ]),
            
            # Post-init bindings
            (setattr(theme_d, "on_change", lambda e: self.update_global_setting("theme_mode", e.control.value)) or ft.Container()),
            (setattr(threads_d, "on_change", lambda e: self.update_global_setting("thread_count", e.control.value)) or ft.Container()),

            ft.Row([
                ft.OutlinedButton("Reset Defaults", on_click=self.reset_defaults, icon=ft.Icons.RESTORE),
                ft.OutlinedButton("Clear Cache", on_click=self.clear_cache, icon=ft.Icons.DELETE_SWEEP),
            ]),
            
            ft.Container(height=20),

            # Ignore List
            ft.Text("Exclusions (Ignore List)", size=18, weight="bold"),
            ft.Text("Folders", weight="bold"),
            ft.OutlinedButton("Add Folder to Ignore", icon=ft.Icons.CREATE_NEW_FOLDER, on_click=self.browse_ignore_folder),
            ft.Container(
                content=ft.Column([
                    ft.ListTile(
                        title=ft.Text(p), 
                        trailing=ft.IconButton(ft.Icons.DELETE, on_click=lambda _, x=p: self.remove_list_item("ignore_folders", x))
                    ) for p in self.config.get("ignore_folders", [])
                ], spacing=0),
                border=ft.Border.all(1, ft.Colors.WHITE12),
                border_radius=5,
                padding=5
            ),
            
            ft.Text("Extensions", weight="bold"),

            ft.Row([
                self.ignore_ext_input,
                ft.IconButton(ft.Icons.ADD, on_click=self.add_ignore_ext_manual)
            ]),
            ft.Row([
                ft.Chip(
                    label=ft.Text(e), 
                    on_delete=lambda _, x=e: self.remove_list_item("ignore_extensions", x)
                ) for e in self.config.get("ignore_extensions", [])
            ], wrap=True),

            ft.Container(height=20),
            
            # Protected Files
            ft.Text("Protected Files (Reference Copies)", size=18, weight="bold"),
            ft.Text("Scanned but strictly read-only. Useful for master copies.", size=12, italic=True, color=ft.Colors.WHITE54),
            ft.OutlinedButton("Add Protected File", icon=ft.Icons.UPLOAD_FILE, on_click=self.browse_protected_file),
             ft.Container(
                content=ft.Column([
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.SHIELD, color=ft.Colors.BLUE_400),
                        title=ft.Text(p, size=12), 
                        trailing=ft.IconButton(ft.Icons.DELETE, on_click=lambda _, x=p: self.remove_list_item("protected_files", x))
                    ) for p in self.config.get("protected_files", [])
                ], spacing=0),
                border=ft.Border.all(1, ft.Colors.WHITE12),
                border_radius=5,
                padding=5
            ),
        ])

    def update_min_size_combined(self, e):
        try:
            val = float(self.min_size_input.value) if self.min_size_input.value else 0
            unit = self.min_size_unit.value
            mult = {"Bytes": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}.get(unit, 1)
            new_bytes = int(val * mult)
            self.update_global_setting("min_file_size", new_bytes)
        except ValueError:
            pass 

    def rerun_benchmark(self, e):
        e.control.disabled = True
        self.safe_show_snackbar("Running benchmark... This may take a moment.")
        self.page.update()
        
        def run_task():
            # Run benchmark
            self.system_profile = Profiler().run_benchmark(enabled=True)
            # Save
            self.config.set("benchmark_scores", self.system_profile.scores)
            self.config.set("recommended_algo", self.system_profile.recommended_algo)
            
            # Update UI on main thread
            self.update_context_fn()
            e.control.disabled = False
            self.safe_show_snackbar("Benchmark updated successfully.")
            self.page.update()
            
        # Run in thread to avoid freezing UI
        threading.Thread(target=run_task, daemon=True).start()

    def on_algo_change(self, e):
        # Read directly from control
        val = self.algo_dropdown.value
        
        # Dynamic Bit Length Logic
        if val == "xxhash":
            self.config.set("hash_length", 64)
        elif val == "sha256":
            self.config.set("hash_length", 256)
        # elif val == "blake3" or "shake_128": 
        # For variable ones, we keep the user's last selected length (or default)
            
        self.config.set("hash_algo", val)
        self.safe_show_snackbar("Hash strategy updated.")
        self.navigate_to("settings") # Refresh current view
    
    def on_length_change(self, e):
        val = int(self.bit_length_dropdown.value)
        self.config.set("hash_length", val)
        self.safe_show_snackbar(f"Hash length set to {val} bits.")
        
        # Live update text
        if hasattr(self, "update_context_fn"):
             self.update_context_fn()

    
    
    # --- Settings Helpers (v0.6) ---
    def update_global_setting(self, key, val):
        self.config.set(key, val)
        self.safe_show_snackbar(f"{key.replace('_', ' ').title()} updated.")
        
    def add_list_item(self, key, item):
        if not item: return
        current = self.config.get(key, [])
        if item not in current:
            current.append(item)
            self.config.set(key, current)
            self.navigate_to("settings") # Refresh
            
    def remove_list_item(self, key, item):
        current = self.config.get(key, [])
        if item in current:
            current.remove(item)
            self.config.set(key, current)
            self.navigate_to("settings")

    def reset_defaults(self, e):
        try:
            if os.path.exists("config.json"):
                os.remove("config.json")
            # Clear in-memory
            self.config.__init__() 
            self.safe_show_snackbar("Configuration reset. Please restart app.")
        except Exception as ex:
            self.safe_show_snackbar(f"Error resetting: {ex}")

    def clear_cache(self, e):
        self.config.set("benchmark_scores", None)
        self.config.set("recommended_algo", None)
        self.safe_show_snackbar("Cache cleared. Please restart to re-benchmark.")
        
    def browse_ignore_folder(self, _):
        import tkinter as tk
        from tkinter import filedialog
        try:
            root = tk.Tk()
            root.withdraw() 
            root.attributes('-topmost', True) 
            path = filedialog.askdirectory(title="Select Folder to Ignore")
            root.destroy()
            if path:
                self.add_list_item("ignore_folders", path.replace("/", "\\"))
        except: pass

    def browse_protected_file(self, _):
        import tkinter as tk
        from tkinter import filedialog
        try:
            root = tk.Tk()
            root.withdraw() 
            root.attributes('-topmost', True) 
            path = filedialog.askopenfilename(title="Select File to Protect")
            root.destroy()
            if path:
                self.add_list_item("protected_files", path.replace("/", "\\"))
        except: pass
        
    def add_ignore_ext_manual(self, e):
        if self.ignore_ext_input.value:
            ext = self.ignore_ext_input.value.strip().lower()
            if not ext.startswith("."): ext = "." + ext
            self.add_list_item("ignore_extensions", ext)
            self.ignore_ext_input.value = ""

    # -------------------------------

    def browse_folder(self, _):
        import tkinter as tk
        from tkinter import filedialog
        
        try:
            root = tk.Tk()
            root.withdraw() # Hide the main window
            root.attributes('-topmost', True) # Bring dialog to front
            
            path = filedialog.askdirectory(initialdir=self.path_input.value or r"C:\\", title="Select Scan Directory")
            root.destroy()
            
            if path:
                # Show busy status immediately
                self.status_text.value = f"Analyzing drive type for: {path}..."
                self.scan_progress.value = None # Indeterminate animation
                self.page.update()
                
                # Run drive checking in background to not freeze UI
                threading.Thread(target=self._add_path_worker, args=(path,), daemon=True).start()
                
        except Exception as e:
            print(f"Dialog error: {e}")

    def add_path_manual(self, _):
        path = self.path_input.value
        if not path or not os.path.exists(path):
            self.status_text.value = "Invalid path!"
            self.page.update()
            return
            
        # Check if already added
        if any(p['path'] == path for p in self.scan_paths):
            self.path_input.value = ""
            self.page.update()
            return

        # Show busy status immediately
        self.status_text.value = f"Analyzing drive type for: {path}..."
        self.path_input.disabled = True # Prevent double add
        self.scan_progress.value = None # Indeterminate animation
        self.page.update()

        # Run in background
        threading.Thread(target=self._add_path_worker, args=(path,), daemon=True).start()

    def _add_path_worker(self, path):
        try:
            dtype = DriveDetector.get_drive_type(path)
            # Default Unknown to HDD as requested
            if dtype == "Unknown": dtype = "HDD"
            
            # Update State (Thread-safe enough for append?)
            # Python lists are thread-safe for append, but let's be careful if we iterate elsewhere.
            # We only iterate in start_scan which is triggered by button, so user can't click it yet.
            self.scan_paths.append({'path': path, 'type': dtype})
            
            # Update UI
            self.path_list_view.controls.append(
                ScanItem(path, dtype, self.remove_path, self.update_path_type)
            )
            self.path_list_view.update()
            self.path_input.value = ""
            self.start_btn.disabled = False
            self.status_text.value = "Ready to scan"
        except Exception as e:
            self.status_text.value = f"Error adding path: {e}"
        
        # Cleanup (always run)
        self.path_input.disabled = False
        self.scan_progress.value = 0 
        self.page.update()

    def update_path_type(self, path, new_type):
        for p in self.scan_paths:
            if p['path'] == path:
                p['type'] = new_type
                break

    def remove_path(self, path):
        self.scan_paths = [p for p in self.scan_paths if p['path'] != path]
        # Rebuild list UI
        self.path_list_view.controls.clear()
        for p in self.scan_paths:
            self.path_list_view.controls.append(
                ScanItem(p['path'], p['type'], self.remove_path, self.update_path_type)
            )
        
        if not self.scan_paths:
            self.start_btn.disabled = True
            
        self.page.update()

    def start_scan(self, _):
        if not self.scan_paths:
            self.status_text.value = "No paths selected!"
            self.page.update()
            return
            
        has_spinning = any(p['type'] in ["HDD", "Network"] for p in self.scan_paths)
        
        # Reset UI
        self.files_scanned_text.value = "0"
        self.status_text.value = "Starting..."
        self.scan_progress.value = None
        self.page.update()
        
        self.is_scanning = True
        self.progress_data = None
        
        # Extract paths
        root_paths = [p['path'] for p in self.scan_paths]

        # proper thread start
        threading.Thread(target=self._run_scan, args=(root_paths, has_spinning), daemon=True).start()

    def on_scan_progress(self, stage, data):
        # Just update state, no UI calls here!
        self.progress_data = (stage, data)

    async def ui_loop(self):
        import asyncio
        last_data = None
        while True:
            if self.is_scanning:
                if self.progress_data and self.progress_data != last_data:
                    stage, data = self.progress_data
                    last_data = self.progress_data
                    
                    if stage == "scanned":
                        count = data
                        self.files_scanned_text.value = f"{count}"
                        self.files_scanned_text.update()
                        self.status_text.value = f"Scanning... {count} files found"
                        self.status_text.update()
                        if self.scan_progress.value != None:
                            self.scan_progress.value = None
                            self.scan_progress.update()
                        
                    elif stage == "hashing_partial":
                        current, total = data
                        self.status_text.value = f"Stage 2/3: Partial Check ({current}/{total})"
                        self.status_text.update()
                        val = current / total if total > 0 else 0
                        self.scan_progress.value = val
                        self.scan_progress.update()
                        
                    elif stage == "hashing_full":
                        current, total = data
                        self.status_text.value = f"Stage 3/3: Deep Scan ({current}/{total})"
                        self.status_text.update()
                        val = current / total if total > 0 else 0
                        self.scan_progress.value = val
                        self.scan_progress.update()
                
                if self.progress_data and self.progress_data[0] == "complete":
                    self.is_scanning = False
                    self.has_scanned = True
                    self.navigate_to("results")

            await asyncio.sleep(0.1)



    def show_results(self, _):
        # Retrieve results from scanner (which calls DB)
        raw_dupes = self.scanner.get_duplicates()
        
        # Group duplicates
        self.duplicates_state = {}
        for full_hash, size, path, mtime in raw_dupes:
            if full_hash not in self.duplicates_state:
                 self.duplicates_state[full_hash] = {'size': size, 'files': []}
            
            is_protected = path in self.config.get("protected_files", [])
            self.duplicates_state[full_hash]['files'].append({
                'path': path, 
                'mtime': mtime, 
                'selected': False,
                'protected': is_protected
            })

        # Calculate stats
        total_dupes = len(raw_dupes) - len(self.duplicates_state)
        wasted_space = sum(g['size'] * (len(g['files']) - 1) for g in self.duplicates_state.values())
        
        # Build Scan Results List
        self.results_column = ft.ListView(expand=True, spacing=10)
        
        for h, g in self.duplicates_state.items():
            if len(g['files']) > 1:
                self.results_column.controls.append(
                    DuplicateGroup(g['size'], g['files'], self.on_file_selected)
                )

        # Action Bar
        if self.duplicates_state:
            # Action Bar
            action_bar = ft.Container(
                content=ft.Row([
                    ft.Text(f"Wasted: {wasted_space/1024/1024:.2f} MB", weight="bold", size=16),
                    ft.Container(expand=True),
                    ft.PopupMenuButton(
                        icon=ft.Icons.SELECT_ALL,
                        tooltip="Smart Selection",
                        items=[
                            ft.PopupMenuItem(content=ft.Text("Select All"), on_click=lambda _: self.smart_select("all")),
                            ft.PopupMenuItem(content=ft.Text("Select None"), on_click=lambda _: self.smart_select("none")),
                            ft.PopupMenuItem(content=ft.Text("Keep Newest (Mark Older)"), on_click=lambda _: self.smart_select("keep_newest")),
                            ft.PopupMenuItem(content=ft.Text("Keep Oldest (Mark Newer)"), on_click=lambda _: self.smart_select("keep_oldest")),
                        ]
                    ),
                    ft.FilledButton("Delete Selected", icon=ft.Icons.DELETE_FOREVER, style=ft.ButtonStyle(bgcolor=ft.Colors.RED, color="white"), on_click=self.delete_selected),
                ]),
                bgcolor="#222222",
                padding=10,
                border_radius=5
            )

            results_view = ft.Column(
                [
                    ft.Text("Scan Results", size=24, weight="bold"),
                    action_bar,
                    ft.Divider(),
                    self.results_column
                ],
                expand=True
            )
        elif self.has_scanned:
            # Empty State (Scan run, but no duplicates)
            results_view = ft.Column(
                [
                    ft.Text("Scan Results", size=24, weight="bold"),
                    ft.Divider(),
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=64, color=ft.Colors.GREEN),
                            ft.Text("No duplicates found.", size=20, color=ft.Colors.WHITE54)
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        alignment=ft.Alignment(0, 0),
                        expand=True,
                        padding=50
                    )
                ],
                expand=True
            )
        else:
            # No Scan Run Yet
            results_view = ft.Column(
                [
                    ft.Text("Scan Results", size=24, weight="bold"),
                    ft.Divider(),
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Icon(ft.Icons.SEARCH_OFF, color=ft.Colors.WHITE24, size=64),
                                ft.Text("No Results Yet", size=20, weight="bold", color=ft.Colors.WHITE54),
                                ft.Text("Run a scan from the Dashboard to see results here.", color=ft.Colors.WHITE24),
                                ft.Container(height=20),
                                ft.FilledButton("Go to Dashboard", on_click=lambda _: self.navigate_to("dashboard"))
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER
                        ),
                        alignment=ft.Alignment(0, 0),
                        expand=True,
                        padding=50
                    )
                ],
                expand=True
            )
        
        self.main_content_area.controls = [results_view]
        self.page.update()

    def on_file_selected(self, path, is_selected):
        # Update state
        for g in self.duplicates_state.values():
            for f in g['files']:
                if f['path'] == path:
                    f['selected'] = is_selected
                    return

    def smart_select(self, criteria):
        for h, g in self.duplicates_state.items():
            files = g['files']
            if not files: continue
            
            if criteria == "all":
                for f in files: 
                    if not f.get('protected'):
                        f['selected'] = True
            elif criteria == "none":
                for f in files: f['selected'] = False
            elif criteria == "keep_newest":
                # Sort by mtime desc (newest first)
                sorted_files = sorted(files, key=lambda x: x['mtime'], reverse=True)
                # Keep first (newest), select rest
                for i, f in enumerate(sorted_files):
                    if not f.get('protected'):
                        f['selected'] = (i > 0)
            elif criteria == "keep_oldest":
                # Sort by mtime asc (oldest first)
                sorted_files = sorted(files, key=lambda x: x['mtime'])
                # Keep first (oldest), select rest
                for i, f in enumerate(sorted_files):
                    if not f.get('protected'):
                        f['selected'] = (i > 0)
        
        # Re-render UI to reflect changes
        self.results_column.controls.clear()
        for h, g in self.duplicates_state.items():
            if len(g['files']) > 1:
                self.results_column.controls.append(
                    DuplicateGroup(g['size'], g['files'], self.on_file_selected)
                )
        self.page.update()

    def delete_selected(self, _):
        # Collect files to delete
        to_delete = []
        for g in self.duplicates_state.values():
            for f in g['files']:
                if f['selected']:
                    to_delete.append(f['path'])
        
        if not to_delete:
            self.page.open(ft.AlertDialog(title=ft.Text("No files selected")))
            return

        def confirm_delete(e):
            self.page.close_dialog()
            success_count = 0
            for p in to_delete:
                try:
                    os.remove(p)
                    success_count += 1
                except Exception as err:
                    print(f"Failed to delete {p}: {err}")
            
            self.page.show_snack_bar(ft.SnackBar(ft.Text(f"Deleted {success_count} files")))
            self._remove_deleted_from_view(to_delete)
        
        self.page.open(ft.AlertDialog(
            title=ft.Text("Confirm Deletion"),
            content=ft.Text(f"Permanently delete {len(to_delete)} files?"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.page.close_dialog()),
                ft.TextButton("Delete", on_click=confirm_delete, style=ft.ButtonStyle(color=ft.Colors.RED)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        ))

    def _remove_deleted_from_view(self, deleted_paths):
        # Update state
        for h in list(self.duplicates_state.keys()): # Copy keys
            g = self.duplicates_state[h]
            g['files'] = [f for f in g['files'] if f['path'] not in deleted_paths]
            if len(g['files']) <= 1:
                # No longer duplicate
                del self.duplicates_state[h]
        
        # Re-render UI
        self.results_column.controls.clear()
        for h, g in self.duplicates_state.items():
            if len(g['files']) > 1:
                self.results_column.controls.append(
                    DuplicateGroup(g['size'], g['files'], self.on_file_selected)
                )
        self.page.update()

    def _run_scan(self, paths, is_spinning):
        # This runs in a thread
        # Configure Strategy
        algo = self.config.get("hash_algo")
        if algo == "auto": algo = self.system_profile.recommended_algo
        
        # Determine bit length (bytes)
        # Default 256 bits (32 bytes)
        bit_len = int(self.config.get("hash_length", 256))
        byte_len = bit_len // 8
        
        strategy = XXHashStrategy() # Default
        
        if algo == "blake3":
            strategy = Blake3Strategy(digest_size=byte_len)
        elif algo == "sha256":
            strategy = SHA256Strategy(digest_size=byte_len) # Fixed, but pass anyway
        elif algo == "shake_128":
            strategy = Shake128Strategy(digest_size=byte_len)
        elif algo == "xxhash":
            strategy = XXHashStrategy(digest_size=byte_len)
            
        print(f"Using Strategy: {strategy.get_name()} ({bit_len}-bit)")
        self.scanner.hasher.set_strategy(strategy)
        
        # Configure Filters (New v0.6)
        ignore_folders = self.config.get("ignore_folders", [])
        ignore_extensions = self.config.get("ignore_extensions", [])
        min_size = self.config.get("min_file_size", 0)
        self.scanner.configure_filters(ignore_folders, ignore_extensions, min_size)
        
        # Setup run
        self.scanner.scanned_count = 0
        try:
            # 0. Clear previous results
            self.db.clear_db()
            
            # 1. Scan
            self.scanner.scan_roots(paths, is_spinning_disk=is_spinning)
            # 2. Process
            self.scanner.process_duplicates(force_single_thread=is_spinning)
            
            # Wait briefly to ensure UI catches the final "100%" progress update
            time.sleep(0.5)
            
            # Signal Done (via state, picked up by async loop)
            self.progress_data = ("complete", None)
            
        except Exception as e:
            print(f"Scan failed: {e}")
            self.progress_data = ("error", str(e))

async def main(page: ft.Page):
    app = DedupeApp(page)
    # detailed initialization is in app.__init__
    
    # Start the async UI loop
    page.run_task(app.ui_loop)

if __name__ == "__main__":
    ft.run(main)
