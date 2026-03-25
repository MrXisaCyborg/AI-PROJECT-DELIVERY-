import tkinter as tk
from tkinter import messagebox, ttk
import tkintermapview # Library for interactive maps
import math

# NOTE: You will need to install the map library: pip install tkintermapview

class DeliveryRoutePlanner:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Delivery Route Planner - Pro Dark Edition")
        self.root.geometry("1300x850")
        
        # Color Palette - Modern Dark Theme
        self.bg_dark = "#1e1e1e"
        self.bg_panel = "#252526"
        self.accent_blue = "#007acc"
        self.accent_green = "#4ec9b0"
        self.accent_yellow = "#f1c40f" # New bright color for animation visibility
        self.text_color = "#d4d4d4"
        self.btn_hover = "#1a8ad4"

        self.root.configure(bg=self.bg_dark)
        
        # Data storage
        # SETTING WAREHOUSE TO SRM IST, KATTANKULATHUR (KTR)
        self.warehouse_coords = (12.8231, 80.0442)
        self.locations = [{"name": "Warehouse (SRM KTR)", "lat": self.warehouse_coords[0], "lng": self.warehouse_coords[1]}]
        self.markers = []
        self.warehouse_marker = None
        self.path = None
        self.anim_marker = None # Marker used for path animation
        self.is_animating = False
        
        self.setup_styles()
        self.setup_ui()

    def setup_styles(self):
        """Configures modern styles for the Dark Mode UI."""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Frame styles
        style.configure("TFrame", background=self.bg_dark)
        style.configure("Dark.TLabelframe", background=self.bg_panel, bordercolor="#333333", foreground=self.text_color)
        style.configure("Dark.TLabelframe.Label", background=self.bg_panel, foreground=self.accent_blue, font=("Segoe UI", 10, "bold"))
        
        # Label styles
        style.configure("TLabel", background=self.bg_panel, foreground=self.text_color, font=("Segoe UI", 10))
        
        # Entry styles
        style.configure("TEntry", fieldbackground="#3c3c3c", foreground="white", borderwidth=0)
        
        # Listbox Customization
        self.root.option_add("*Listbox.background", "#2d2d2d")
        self.root.option_add("*Listbox.foreground", self.text_color)
        self.root.option_add("*Listbox.selectBackground", self.accent_blue)
        self.root.option_add("*Listbox.borderwidth", 0)

    def setup_ui(self):
        """Creates the layout of the application."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Left Side: Input Controls
        input_frame = ttk.LabelFrame(main_frame, text=" LOGISTICS CONTROL ", style="Dark.TLabelframe", padding="20")
        input_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        # Search box
        ttk.Label(input_frame, text="Find Landmark / Destination:").pack(pady=(0,5), anchor="w")
        self.search_entry = tk.Entry(input_frame, bg="#3c3c3c", fg="white", insertbackground="white", 
                                     relief="flat", font=("Segoe UI", 11), highlightthickness=1, highlightbackground="#444")
        self.search_entry.pack(fill=tk.X, pady=(0, 10), ipady=5)
        self.search_entry.bind("<Return>", lambda e: self.search_location())
        
        search_btn = tk.Button(input_frame, text="SEARCH & ADD", bg=self.accent_blue, fg="white", 
                               font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2",
                               command=self.search_location, activebackground=self.btn_hover, activeforeground="white")
        search_btn.pack(fill=tk.X, pady=5, ipady=5)

        ttk.Separator(input_frame, orient='horizontal').pack(fill=tk.X, pady=20)

        # Listbox
        ttk.Label(input_frame, text="Active Route Sequence:").pack(pady=(0,5), anchor="w")
        self.loc_listbox = tk.Listbox(input_frame, height=18, font=("Segoe UI", 10), relief="flat", highlightthickness=1, highlightbackground="#444")
        self.loc_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        self.update_listbox()

        # Utility Buttons
        btn_grid = ttk.Frame(input_frame)
        btn_grid.pack(fill=tk.X, pady=10)

        reset_btn = tk.Button(btn_grid, text="RESET ALL", bg="#444444", fg="white", 
                              font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2",
                              command=self.clear_data)
        reset_btn.pack(fill=tk.X, ipady=5)

        # Right Side: Map and Results
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Map Widget
        self.map_widget = tkintermapview.TkinterMapView(right_frame, corner_radius=10, bg_color=self.bg_dark)
        self.map_widget.pack(fill=tk.BOTH, expand=True)
        
        self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}&s=Ga", max_zoom=22) 
        
        self.map_widget.set_position(self.warehouse_coords[0], self.warehouse_coords[1])
        self.map_widget.set_zoom(15)
        
        # Right-Click Menu
        self.map_widget.add_right_click_menu_command(label="Set as Warehouse", command=self.set_warehouse_from_map, pass_coords=True)
        self.map_widget.add_right_click_menu_command(label="Add Delivery Point", command=self.add_point_from_map, pass_coords=True)

        # Place Warehouse Marker
        self.warehouse_marker = self.map_widget.set_marker(self.warehouse_coords[0], self.warehouse_coords[1], 
                                                         text="SRM KTR WH", marker_color_circle="red", text_color="white")

        # Action Button
        solve_btn = tk.Button(right_frame, text="GENERATE AI OPTIMIZED ROUTE", 
                              bg=self.accent_green, fg="#121212", font=("Segoe UI", 11, "bold"),
                              command=self.generate_route, pady=12, relief="flat", cursor="hand2")
        solve_btn.pack(fill=tk.X, pady=(15, 0))

        # Results Display
        self.result_text = tk.Text(right_frame, height=4, font=("Consolas", 11), 
                                   bg="#1e1e1e", fg=self.accent_green, relief="flat", 
                                   padx=15, pady=10, highlightthickness=1, highlightbackground="#333")
        self.result_text.pack(fill=tk.X, pady=(10, 0))
        self.result_text.insert(tk.END, "> System Initialized: SRM KTR Node Active.")

    def set_warehouse_from_map(self, coords):
        lat, lng = coords
        self.warehouse_coords = (lat, lng)
        self.locations[0] = {"name": "Warehouse (Custom)", "lat": lat, "lng": lng}
        
        if self.warehouse_marker:
            self.warehouse_marker.delete()
        self.warehouse_marker = self.map_widget.set_marker(lat, lng, text="Warehouse", marker_color_circle="red")
        
        self.update_listbox()
        self.log_message(f"Warehouse moved to: {lat:.4f}, {lng:.4f}")

    def add_point_from_map(self, coords):
        lat, lng = coords
        name = f"Node {len(self.locations)}"
        self.locations.append({"name": name, "lat": lat, "lng": lng})
        marker = self.map_widget.set_marker(lat, lng, text=name, text_color="white")
        self.markers.append(marker)
        self.update_listbox()

    def search_location(self):
        address = self.search_entry.get().strip()
        if not address: return
        
        new_marker = self.map_widget.set_address(address, marker=True)
        if new_marker:
            new_marker.set_text(address)
            self.locations.append({
                "name": address, 
                "lat": new_marker.position[0], 
                "lng": new_marker.position[1]
            })
            self.markers.append(new_marker)
            self.update_listbox()
            self.search_entry.delete(0, tk.END)
            self.map_widget.set_position(new_marker.position[0], new_marker.position[1])
        else:
            messagebox.showwarning("Search Error", f"Location '{address}' not found.")

    def update_listbox(self):
        self.loc_listbox.delete(0, tk.END)
        for loc in self.locations:
            prefix = " 🏠 " if "Warehouse" in loc['name'] else " 📍 "
            self.loc_listbox.insert(tk.END, f"{prefix}{loc['name']}")

    def log_message(self, msg):
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, f"> {msg}")

    def clear_data(self):
        self.is_animating = False
        self.warehouse_coords = (12.8231, 80.0442)
        self.locations = [{"name": "Warehouse (SRM KTR)", "lat": self.warehouse_coords[0], "lng": self.warehouse_coords[1]}]
        for m in self.markers: m.delete()
        self.markers = []
        if self.warehouse_marker: self.warehouse_marker.delete()
        self.warehouse_marker = self.map_widget.set_marker(self.warehouse_coords[0], self.warehouse_coords[1], 
                                                         text="SRM KTR WH", marker_color_circle="red")
        if self.path: self.path.delete()
        self.path = None
        if self.anim_marker: self.anim_marker.delete()
        self.anim_marker = None
        
        self.update_listbox()
        self.log_message("System Reset. Warehouse restored to SRM KTR.")
        self.map_widget.set_position(self.warehouse_coords[0], self.warehouse_coords[1])
        self.map_widget.set_zoom(15)

    def calculate_distance(self, p1, p2):
        return math.sqrt((p1['lat'] - p2['lat'])**2 + (p1['lng'] - p2['lng'])**2)

    def animate_path(self, route_points, index=0, step=0):
        """Recursively animates a small arrow along the path."""
        if not self.is_animating or index >= len(route_points) - 1:
            if self.anim_marker: 
                self.anim_marker.delete()
                self.anim_marker = None
            return

        p1 = route_points[index]
        p2 = route_points[index + 1]
        
        # Number of interpolation steps for smoothness - increased for better visibility
        total_steps = 25 
        
        # Calculate interpolated position
        ratio = step / total_steps
        curr_lat = p1[0] + (p2[0] - p1[0]) * ratio
        curr_lng = p1[1] + (p2[1] - p1[1]) * ratio
        
        # Update or create the animation marker with high-contrast colors
        if not self.anim_marker:
            self.anim_marker = self.map_widget.set_marker(curr_lat, curr_lng, text="➤", 
                                                         marker_color_circle=self.accent_yellow,
                                                         marker_color_outside=self.accent_blue)
        else:
            self.anim_marker.set_position(curr_lat, curr_lng)
        
        # Logic for next step
        if step < total_steps:
            self.root.after(30, lambda: self.animate_path(route_points, index, step + 1))
        else:
            self.root.after(30, lambda: self.animate_path(route_points, index + 1, 0))

    def generate_route(self):
        if len(self.locations) < 3:
            messagebox.showinfo("Logistics", "Add at least 2 destinations to compute an optimized route.")
            return

        # Stop and clean up existing animation
        self.is_animating = False
        if self.anim_marker: 
            self.anim_marker.delete()
            self.anim_marker = None

        unvisited = self.locations[1:]
        current_node = self.locations[0]
        route = [current_node]
        total_distance = 0

        # Nearest Neighbor Heuristic
        while unvisited:
            nearest_node = min(unvisited, key=lambda node: self.calculate_distance(current_node, node))
            dist = self.calculate_distance(current_node, nearest_node)
            total_distance += dist
            route.append(nearest_node)
            unvisited.remove(nearest_node)
            current_node = nearest_node

        total_distance += self.calculate_distance(current_node, self.locations[0])
        route.append(self.locations[0])
        
        # UI Updates
        route_names = [l['name'] for l in route]
        self.log_message(f"OPTIMIZATION COMPLETE\nRoute: {' → '.join(route_names)}\nPath Weight: {total_distance:.6f}")

        if self.path: self.path.delete()
        path_coords = [(loc['lat'], loc['lng']) for loc in route]
        self.path = self.map_widget.set_path(path_coords, color=self.accent_green, width=3)
        
        # Trigger Animation after a brief delay to ensure path is drawn
        self.is_animating = True
        self.root.after(300, lambda: self.animate_path(path_coords))
        
        self.map_widget.set_zoom(14)

if __name__ == "__main__":
    root = tk.Tk()
    app = DeliveryRoutePlanner(root)
    root.mainloop()
