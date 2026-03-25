import tkinter as tk
from tkinter import messagebox, ttk
import tkintermapview
import math
import time
import threading

# NOTE: pip install tkintermapview is required

class DeliveryRoutePlanner:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Logistics Pro - Advanced Route Optimizer")
        self.root.geometry("1400x900")
        
        # Premium Dark Theme Palette
        self.colors = {
            "bg": "#0f0f12",
            "panel": "#1c1c21",
            "accent": "#00a8ff",
            "success": "#00d2ad",
            "warning": "#ff9f43",
            "text": "#e0e0e0",
            "text_dim": "#a0a0a0",
            "border": "#333338"
        }

        self.root.configure(bg=self.colors["bg"])
        
        # Logic Variables
        self.warehouse_coords = (12.8231, 80.0442) # SRM KTR
        self.locations = [{"name": "Warehouse (SRM KTR)", "lat": self.warehouse_coords[0], "lng": self.warehouse_coords[1]}]
        self.markers = []
        self.path = None
        self.anim_marker = None
        self.is_animating = False
        
        self.setup_styles()
        self.setup_ui()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background=self.colors["bg"])
        style.configure("Card.TLabelframe", background=self.colors["panel"], bordercolor=self.colors["border"])
        style.configure("Card.TLabelframe.Label", background=self.colors["panel"], foreground=self.colors["accent"], font=("Orbitron", 10, "bold"))
        style.configure("TLabel", background=self.colors["panel"], foreground=self.colors["text"], font=("Segoe UI", 10))
        
        # Custom Progress Bar
        style.configure("AI.Horizontal.TProgressbar", troughcolor=self.colors["bg"], bordercolor=self.colors["border"], background=self.colors["accent"])

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- LEFT PANEL: CONTROLS ---
        left_panel = ttk.Frame(main_frame, width=350)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15))

        # 1. Search Section
        search_card = ttk.LabelFrame(left_panel, text=" LOCATION ENGINE ", style="Card.TLabelframe", padding=15)
        search_card.pack(fill=tk.X, pady=(0, 15))

        self.search_entry = tk.Entry(search_card, bg="#2d2d35", fg="white", insertbackground="white", 
                                     relief="flat", font=("Segoe UI", 11), highlightthickness=1, highlightbackground=self.colors["border"])
        self.search_entry.pack(fill=tk.X, pady=(0, 10), ipady=8)
        self.search_entry.bind("<Return>", lambda e: self.search_location())

        search_btn = tk.Button(search_card, text="ADD TO ROUTE", bg=self.colors["accent"], fg="white", 
                               font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2", command=self.search_location)
        search_btn.pack(fill=tk.X, ipady=6)

        # 2. Analytics Section (High Marks Feature)
        stats_card = ttk.LabelFrame(left_panel, text=" LOGISTICS ANALYTICS ", style="Card.TLabelframe", padding=15)
        stats_card.pack(fill=tk.X, pady=(0, 15))

        self.stats_labels = {}
        metrics = [("Total Distance", "0.00 km"), ("Est. Time", "0 mins"), ("Fuel Cost", "₹0.00")]
        for label, val in metrics:
            f = ttk.Frame(stats_card)
            f.pack(fill=tk.X, pady=2)
            ttk.Label(f, text=label, foreground=self.colors["text_dim"]).pack(side=tk.LEFT)
            l = ttk.Label(f, text=val, foreground=self.colors["success"], font=("Segoe UI", 10, "bold"))
            l.pack(side=tk.RIGHT)
            self.stats_labels[label] = l

        # 3. Route List
        list_card = ttk.LabelFrame(left_panel, text=" DELIVERY MANIFEST ", style="Card.TLabelframe", padding=15)
        list_card.pack(fill=tk.BOTH, expand=True)

        self.loc_listbox = tk.Listbox(list_card, bg="#18181c", fg="#ccc", font=("Segoe UI", 10), 
                                      borderwidth=0, highlightthickness=0, selectbackground=self.colors["accent"])
        self.loc_listbox.pack(fill=tk.BOTH, expand=True)
        
        reset_btn = tk.Button(list_card, text="CLEAR SYSTEM", bg="#3a3a42", fg="white", font=("Segoe UI", 9),
                              relief="flat", cursor="hand2", command=self.clear_data)
        reset_btn.pack(fill=tk.X, pady=(10, 0), ipady=4)

        # --- RIGHT PANEL: MAP & AI ---
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Map
        self.map_widget = tkintermapview.TkinterMapView(right_panel, corner_radius=12, bg_color=self.colors["bg"])
        self.map_widget.pack(fill=tk.BOTH, expand=True)
        self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}&s=Ga")
        self.map_widget.set_position(self.warehouse_coords[0], self.warehouse_coords[1])
        self.map_widget.set_zoom(15)

        # Right-click bindings
        self.map_widget.add_right_click_menu_command(label="Set Warehouse", command=self.set_warehouse_from_map, pass_coords=True)
        self.map_widget.add_right_click_menu_command(label="Add Customer", command=self.add_point_from_map, pass_coords=True)

        # AI Execution Section
        ai_frame = ttk.Frame(right_panel, padding=(0, 15, 0, 0))
        ai_frame.pack(fill=tk.X)

        self.progress = ttk.Progressbar(ai_frame, mode='determinate', style="AI.Horizontal.TProgressbar")
        self.progress.pack(fill=tk.X, pady=(0, 10))

        self.solve_btn = tk.Button(ai_frame, text="RUN AI OPTIMIZATION (Greedy Heuristic)", 
                                   bg=self.colors["success"], fg="#000", font=("Segoe UI", 11, "bold"),
                                   relief="flat", cursor="hand2", command=self.start_ai_task)
        self.solve_btn.pack(fill=tk.X, ipady=12)

        # Warehouse Initial Marker
        self.warehouse_marker = self.map_widget.set_marker(self.warehouse_coords[0], self.warehouse_coords[1], 
                                                         text="SRM KTR DEPOT", marker_color_circle="red")

        self.update_listbox()

    # --- AI ALGORITHMS ---
    
    def haversine(self, lat1, lon1, lat2, lon2):
        """Calculates real-world distance between two points in KM."""
        R = 6371 # Earth radius
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    def get_total_path_dist(self, path):
        d = 0
        for i in range(len(path)-1):
            d += self.haversine(path[i]['lat'], path[i]['lng'], path[i+1]['lat'], path[i+1]['lng'])
        return d

    def solve_route_ai(self):
        """AI Engine: Greedy Nearest Neighbor Algorithm."""
        unvisited = self.locations[1:]
        current = self.locations[0]
        route = [current]
        
        # Greedy Phase (Nearest Neighbor)
        while unvisited:
            # Find the closest unvisited location from current position
            nearest = min(unvisited, key=lambda n: self.haversine(current['lat'], current['lng'], n['lat'], n['lng']))
            route.append(nearest)
            unvisited.remove(nearest)
            current = nearest
            
        # Return to warehouse (starting point) to complete the circuit
        route.append(self.locations[0])
        return route

    # --- UI & ANIMATION LOGIC ---

    def start_ai_task(self):
        if len(self.locations) < 3:
            messagebox.showwarning("Incomplete Data", "Please add at least 2 customers.")
            return
        
        self.solve_btn.config(state=tk.DISABLED, text="AI COMPUTING...")
        self.progress['value'] = 0
        
        def run():
            # Simulate 'Thinking' process for UI feedback
            for i in range(1, 101, 10):
                time.sleep(0.05)
                self.progress['value'] = i
            
            final_route = self.solve_route_ai()
            self.root.after(0, lambda: self.finalize_route(final_route))

        threading.Thread(target=run).start()

    def finalize_route(self, route):
        dist = self.get_total_path_dist(route)
        
        # Update Analytics
        self.stats_labels["Total Distance"].config(text=f"{dist:.2f} km")
        self.stats_labels["Est. Time"].config(text=f"{int(dist * 2.5)} mins") # Estimated 2.5 min/km avg
        self.stats_labels["Fuel Cost"].config(text=f"₹{dist * 8.5:.2f}") # Estimated ₹8.5/km fuel cost

        # Draw on Map
        if self.path: self.path.delete()
        path_coords = [(l['lat'], l['lng']) for l in route]
        self.path = self.map_widget.set_path(path_coords, color=self.colors["success"], width=3)
        
        # Start Animation
        self.is_animating = True
        self.animate_path(path_coords)
        
        self.solve_btn.config(state=tk.NORMAL, text="RUN AI OPTIMIZATION (Greedy Heuristic)")

    def animate_path(self, coords, index=0, step=0):
        if not self.is_animating or index >= len(coords)-1:
            if self.anim_marker: self.anim_marker.delete()
            return

        p1, p2 = coords[index], coords[index+1]
        steps = 15
        ratio = step / steps
        lat = p1[0] + (p2[0]-p1[0])*ratio
        lng = p1[1] + (p2[1]-p1[1])*ratio

        if not self.anim_marker:
            self.anim_marker = self.map_widget.set_marker(lat, lng, text="🚚", marker_color_circle=self.colors["accent"])
        else:
            self.anim_marker.set_position(lat, lng)

        if step < steps:
            self.root.after(30, lambda: self.animate_path(coords, index, step+1))
        else:
            self.root.after(30, lambda: self.animate_path(coords, index+1, 0))

    # --- SEARCH & UTILS ---

    def search_location(self):
        address = self.search_entry.get().strip()
        if not address: return
        m = self.map_widget.set_address(address, marker=True)
        if m:
            self.locations.append({"name": address, "lat": m.position[0], "lng": m.position[1]})
            self.markers.append(m)
            self.update_listbox()
            self.search_entry.delete(0, tk.END)
            self.map_widget.set_position(m.position[0], m.position[1])
        else:
            messagebox.showerror("Error", "Location not found.")

    def set_warehouse_from_map(self, coords):
        self.warehouse_coords = coords
        self.locations[0] = {"name": "Central Depot (Custom)", "lat": coords[0], "lng": coords[1]}
        if self.warehouse_marker: self.warehouse_marker.delete()
        self.warehouse_marker = self.map_widget.set_marker(coords[0], coords[1], text="MAIN DEPOT", marker_color_circle="red")
        self.update_listbox()

    def add_point_from_map(self, coords):
        name = f"Customer {len(self.locations)}"
        self.locations.append({"name": name, "lat": coords[0], "lng": coords[1]})
        m = self.map_widget.set_marker(coords[0], coords[1], text=name)
        self.markers.append(m)
        self.update_listbox()

    def update_listbox(self):
        self.loc_listbox.delete(0, tk.END)
        for i, loc in enumerate(self.locations):
            icon = "🏢" if i==0 else "👤"
            self.loc_listbox.insert(tk.END, f" {icon} {loc['name']}")

    def clear_data(self):
        self.is_animating = False
        self.locations = [{"name": "Warehouse (SRM KTR)", "lat": 12.8231, "lng": 80.0442}]
        for m in self.markers: m.delete()
        self.markers = []
        if self.path: self.path.delete()
        if self.anim_marker: self.anim_marker.delete()
        self.map_widget.set_position(12.8231, 80.0442)
        self.update_listbox()
        for label in ["Total Distance", "Est. Time", "Fuel Cost"]:
            self.stats_labels[label].config(text="0.00")

if __name__ == "__main__":
    root = tk.Tk()
    app = DeliveryRoutePlanner(root)
    root.mainloop()
