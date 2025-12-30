import flet as ft


class SidebarButton(ft.Container):
    def __init__(self, icon, text, selected=False, on_click=None):
        super().__init__(
            content=ft.Row(
                # ft.colors is deprecated/moved in newer versions, use ft.Colors or string literals
                [
                    ft.Icon(icon, color=ft.Colors.WHITE if selected else ft.Colors.WHITE54),
                    ft.Text(text, color=ft.Colors.WHITE if selected else ft.Colors.WHITE54, weight="bold" if selected else "normal"),
                ],
                spacing=10,
            ),
            padding=ft.Padding.all(10),
            border_radius=5,
            bgcolor=ft.Colors.WHITE10 if selected else None,
            ink=True,
            on_click=on_click,
        )

class StatCard(ft.Container):
    def __init__(self, title, value, icon, color):
        super().__init__(
            content=ft.Column(
                [
                    ft.Icon(icon, color=color, size=30),
                    ft.Text(value, size=24, weight="bold"),
                    ft.Text(title, size=12, color=ft.Colors.WHITE54),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=150,
            height=100,
            bgcolor="#2b2b2b", # Replaced ft.Colors.SURFACE_VARIANT because it triggers a bug in Flet 0.80 deprecated_enum shim
            border_radius=10,
            padding=10,
        )

class DuplicateGroup(ft.Container):
    def __init__(self, size: int, files: list, on_selection_change):
        """
        files: list of dicts {'path': str, 'mtime': float, 'selected': bool}
        on_selection_change: callback(path, is_selected)
        """
        super().__init__()
        self.files = files
        self.on_selection_change = on_selection_change
        
        # Header
        size_str = f"{size/1024/1024:.2f} MB" if size > 1024*1024 else f"{size/1024:.2f} KB"
        header = ft.Row([
            ft.Icon(ft.Icons.COPY, color=ft.Colors.RED_400),
            ft.Text(f"{len(files)} Copies", weight="bold"),
            ft.Text(f"Size: {size_str}", color="white54"),
        ])
        
        # File Rows
        self.file_rows = ft.Column(spacing=2)
        for f in files:
            self.file_rows.controls.append(self._create_file_row(f))
            
        self.content = ft.Column([
            ft.Container(content=header, bgcolor="#2b2b2b", padding=10, border_radius=5),
            ft.Container(            content=self.file_rows,
            padding=ft.Padding.only(left=20)
        )], spacing=5)
        
        self.border_radius = 5
        self.bgcolor = ft.Colors.BLACK54
        self.padding = 5
        self.margin = ft.Margin(bottom=10, top=0, left=0, right=0) # Space between groups

    def _create_file_row(self, file_data):
        import datetime
        mtime_str = datetime.datetime.fromtimestamp(file_data['mtime']).strftime('%Y-%m-%d %H:%M')
        
        is_protected = file_data.get('protected', False)
        
        icon = None
        if is_protected:
            icon = ft.Icon(ft.Icons.SHIELD, size=16, color=ft.Colors.BLUE_400, tooltip="Protected Reference Copy")
            
        return ft.Row([
            ft.Checkbox(
                value=False if is_protected else file_data.get('selected', False),
                disabled=is_protected,
                on_change=lambda e: self.on_selection_change(file_data['path'], e.control.value)
            ),
            icon if icon else ft.Container(),
            ft.Column([
                ft.Text(file_data['path'], size=12, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS, 
                        color=ft.Colors.BLUE_200 if is_protected else None),
                ft.Text(f"Modified: {mtime_str}", size=10, color="white30")
            ], spacing=0, expand=True)
        ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER)


def get_app_theme():
    return ft.Theme(
        color_scheme_seed=ft.Colors.INDIGO,
        visual_density=ft.VisualDensity.COMFORTABLE,
        page_transitions=ft.PageTransitionsTheme(
            windows=ft.PageTransitionTheme.CUPERTINO
        )
    )
