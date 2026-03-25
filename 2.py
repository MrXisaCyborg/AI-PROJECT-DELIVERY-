import tkinter as tk
from tkinter import messagebox, ttk
import tkintermapview
import math
import time
import threading
import requests # Required for Road-Routing API calls

# NOTE: pip install tkintermapview requests

class DeliveryRoutePlanner:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Logistics Pro - Real Road Route Optimizer")
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
        self.path_objects = [] # Stores road segments
        self.anim_marker = None
        self.is_animating = False
        
        self.setup_styles()
        self.setup_ui()

    def setup_styles(self):
        """Knowledge Representation: Standardizing UI Aesthetics."""
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background=self.colors["bg"])
        style.configure("Card.TLabelframe", background=self.colors["panel"], bordercolor=self.colors["border"])
        style.configure("Card.TLabelframe.Label", background=self.colors["panel"], foreground=self.colors["accent"], font=("Orbitron", 10, "bold"))
        style.configure("TLabel", background=self.colors["panel"], foreground=self.colors["text"], font=("Segoe UI", 10))
        style.configure("AI.Horizontal.TProgressbar", troughcolor=self.colors["bg"], bordercolor=self.colors["border"], background=self.colors["accent"])

    def setup_ui(self):
        """Pathology of UI: Building a high-performance logistics dashboard."""
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- LEFT PANEL: CONTROLS ---
        left_panel = ttk.Frame(main_frame, width=350)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15))

        # 1. Location Input
        search_card = ttk.LabelFrame(left_panel, text=" ROUTE INPUT ", style="Card.TLabelframe", padding=15)
        search_card.pack(fill=tk.X, pady=(0, 15))

        self.search_entry = tk.Entry(search_card, bg="#2d2d35", fg="white", insertbackground="white", 
                                     relief="flat", font=("Segoe UI", 11), highlightthickness=1, highlightbackground=self.colors["border"])
        self.search_entry.pack(fill=tk.X, pady=(0, 10), ipady=8)
        self.search_entry.bind("<Return>", lambda e: self.search_location())

        tk.Button(search_card, text="SEARCH & ADD DESTINATION", bg=self.colors["accent"], fg="white", 
                  font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2", command=self.search_location).pack(fill=tk.X, ipady=6)

        # 2. Advanced Analytics
        stats_card = ttk.LabelFrame(left_panel, text=" ROAD ANALYTICS ", style="Card.TLabelframe", padding=15)
        stats_card.pack(fill=tk.X, pady=(0, 15))

        self.stats_labels = {}
        metrics = [("Total Road Dist", "0.00 km"), ("Travel Time", "0 mins"), ("Fuel Cost", "₹0.00")]
        for label, val in metrics:
            f = ttk.Frame(stats_card)
            f.pack(fill=tk.X, pady=4)
            ttk.Label(f, text=label, foreground=self.colors["text_dim"]).pack(side=tk.LEFT)
            l = ttk.Label(f, text=val, foreground=self.colors["success"], font=("Segoe UI", 10, "bold"))
            l.pack(side=tk.RIGHT)
            self.stats_labels[label] = l

        # 3. Destination Manifest
        list_card = ttk.LabelFrame(left_panel, text=" DELIVERY MANIFEST ", style="Card.TLabelframe", padding=15)
        list_card.pack(fill=tk.BOTH, expand=True)

        self.loc_listbox = tk.Listbox(list_card, bg="#18181c", fg="#ccc", font=("Segoe UI", 10), 
                                      borderwidth=0, highlightthickness=0, selectbackground=self.colors["accent"])
        self.loc_listbox.pack(fill=tk.BOTH, expand=True)
        
        tk.Button(list_card, text="RESET LOGISTICS", bg="#3a3a42", fg="white", font=("Segoe UI", 9),
                  relief="flat", cursor="hand2", command=self.clear_data).pack(fill=tk.X, pady=(10, 0), ipady=4)

        # --- RIGHT PANEL: MAP & AI ---
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.map_widget = tkintermapview.TkinterMapView(right_panel, corner_radius=12, bg_color=self.colors["bg"])
        self.map_widget.pack(fill=tk.BOTH, expand=True)
        self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}&s=Ga")
        self.map_widget.set_position(self.warehouse_coords[0], self.warehouse_coords[1])
        self.map_widget.set_zoom(15)

        # AI Control Panel
        ai_frame = ttk.Frame(right_panel, padding=(0, 15, 0, 0))
        ai_frame.pack(fill=tk.X)

        self.progress = ttk.Progressbar(ai_frame, mode='determinate', style="AI.Horizontal.TProgressbar")
        self.progress.pack(fill=tk.X, pady=(0, 10))

        self.solve_btn = tk.Button(ai_frame, text="COMPUTE ROAD-NETWORK ROUTE (AI GREEDY)", 
                                   bg=self.colors["success"], fg="#000", font=("Segoe UI", 11, "bold"),
                                   relief="flat", cursor="hand2", command=self.start_ai_task)
        self.solve_btn.pack(fill=tk.X, ipady=12)

        self.warehouse_marker = self.map_widget.set_marker(self.warehouse_coords[0], self.warehouse_coords[1], 
                                                         text="SRM KTR WH", marker_color_circle="red")
        
        # Right-click bindings
        self.map_widget.add_right_click_menu_command(label="Set Warehouse", command=self.set_warehouse_from_map, pass_coords=True)
        self.map_widget.add_right_click_menu_command(label="Add Destination", command=self.add_point_from_map, pass_coords=True)

        self.update_listbox()

    # --- ROAD ROUTING AI LOGIC ---

    def get_road_path(self, start_coords, end_coords):
        """
        EXPERT FEATURE: Fetches actual road coordinates between two points using OSRM API.
        This ensures the route follows actual streets, not just straight lines.
        """
        try:
            url = f"http://router.project-osrm.org/route/v1/driving/{start_coords[1]},{start_coords[0]};{end_coords[1]},{end_coords[0]}?overview=full&geometries=geojson"
            response = requests.get(url, timeout=5)
            data = response.json()
            if data['code'] == 'Ok':
                # Convert [lng, lat] to [lat, lng] for tkintermapview
                raw_coords = data['routes'][0]['geometry']['coordinates']
                return [(c[1], c[0]) for c in raw_coords], data['routes'][0]['distance'] / 1000
        except Exception as e:
            print(f"Routing API Error: {e}")
        
        # Fallback to straight line if API fails
        return [start_coords, end_coords], self.haversine(start_coords[0], start_coords[1], end_coords[0], end_coords[1])

    def haversine(self, lat1, lon1, lat2, lon2):
        """Haversine Formula for crow-fly distance (used for greedy sorting)."""
        R = 6371
        dlat, dlon = math.radians(lat2-lat1), math.radians(lon2-lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    def solve_greedy_route(self):
        """
        Inference Engine: Performs Greedy Nearest Neighbor sorting
        to determine the order of visits.
        """
        unvisited = self.locations[1:]
        current = self.locations[0]
        stop_order = [current]
        
        while unvisited:
            nearest = min(unvisited, key=lambda n: self.haversine(current['lat'], current['lng'], n['lat'], n['lng']))
            stop_order.append(nearest)
            unvisited.remove(nearest)
            current = nearest
        stop_order.append(self.locations[0]) # Circuit back to WH
        
        return stop_order

    def start_ai_task(self):
        if len(self.locations) < 3:
            messagebox.showwarning("Incomplete", "Add at least 2 destinations.")
            return
        
        self.solve_btn.config(state=tk.DISABLED, text="AI TRACING ROADS...")
        self.progress['value'] = 0
        
        def run_ai():
            stops = self.solve_greedy_route()
            full_road_path = []
            total_km = 0
            
            # Fetch road coordinates for every segment
            for i in range(len(stops) - 1):
                p1 = (stops[i]['lat'], stops[i]['lng'])
                p2 = (stops[i+1]['lat'], stops[i+1]['lng'])
                segment, km = self.get_road_path(p1, p2)
                full_road_path.extend(segment)
                total_km += km
                self.progress['value'] = (i+1) / len(stops) * 100
            
            self.root.after(0, lambda: self.finalize_ui(full_road_path, total_km, stops))

        threading.Thread(target=run_ai, daemon=True).start()

    def finalize_ui(self, road_path, total_km, stops):
        """Updates the analytics and map with the road-following path."""
        # Update Analytics
        self.stats_labels["Total Road Dist"].config(text=f"{total_km:.2f} km")
        self.stats_labels["Travel Time"].config(text=f"{int(total_km * 3)} mins") # ~20km/h avg speed
        self.stats_labels["Fuel Cost"].config(text=f"₹{total_km * 9.2:.2f}")

        # Draw Road Path
        for p in self.path_objects: p.delete()
        self.path_objects = [self.map_widget.set_path(road_path, color=self.colors["success"], width=4)]
        
        # Start Animation along the road
        self.is_animating = True
        self.animate_path(road_path)
        
        self.solve_btn.config(state=tk.NORMAL, text="COMPUTE ROAD-NETWORK ROUTE (AI GREEDY)")

    def animate_path(self, coords, index=0):
        if not self.is_animating or index >= len(coords):
            if self.anim_marker: self.anim_marker.delete()
            return

        lat, lng = coords[index]
        if not self.anim_marker:
            self.anim_marker = self.map_widget.set_marker(lat, lng, text="🚚", marker_color_circle=self.colors["accent"])
        else:
            self.anim_marker.set_position(lat, lng)

        # Speed of animation: skip some points if road data is very dense
        skip = 2 if len(coords) > 200 else 1
        self.root.after(20, lambda: self.animate_path(coords, index + skip))

    # --- UI HELPERS ---

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
        self.locations[0] = {"name": "Central Depot (Custom)", "lat": coords[0], "lng": coords[1]}
        if self.warehouse_marker: self.warehouse_marker.delete()
        self.warehouse_marker = self.map_widget.set_marker(coords[0], coords[1], text="MAIN DEPOT", marker_color_circle="red")
        self.update_listbox()

    def add_point_from_map(self, coords):
        name = f"Customer {len(self.locations)}"
        self.locations.append({"name": name, "lat": coords[0], "lng": coords[1]})
        self.markers.append(self.map_widget.set_marker(coords[0], coords[1], text=name))
        self.update_listbox()

    def update_listbox(self):
        self.loc_listbox.delete(0, tk.END)
        for i, loc in enumerate(self.locations):
            icon = "🏢" if i==0 else "📍"
            self.loc_listbox.insert(tk.END, f" {icon} {loc['name']}")

    def clear_data(self):
        self.is_animating = False
        self.locations = [{"name": "Warehouse (SRM KTR)", "lat": 12.8231, "lng": 80.0442}]
        for m in self.markers: m.delete()
        for p in self.path_objects: p.delete()
        if self.anim_marker: self.anim_marker.delete()
        self.map_widget.set_position(12.8231, 80.0442)
        self.update_listbox()
        for l in self.stats_labels.values(): l.config(text="0.00")

if __name__ == "__main__":
    root = tk.Tk()
    app = DeliveryRoutePlanner(root)
    root.mainloop()
    root.mainloop()
