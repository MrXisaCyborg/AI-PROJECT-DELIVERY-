import tkinter as tk
from tkinter import messagebox, ttk
import tkintermapview
import math
import time
import threading
import requests # Required for Road-Routing API (OSRM)

# TECHNICAL NOTE: 
# This application implements a Multi-Depot Vehicle Routing (MDVR) simulation.
# It uses the OSRM (Open Source Routing Machine) API for real-road navigation 
# and a Greedy Heuristic to determine the optimal sequence across multiple supply points.

class DeliveryRoutePlanner:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Logistics Pro - Multi-Depot Road Optimizer")
        self.root.geometry("1400x950")
        
        # Premium Dark Theme Palette
        self.colors = {
            "bg": "#0f0f12",
            "panel": "#1c1c21",
            "accent": "#00a8ff",    # Warehouse Blue
            "success": "#00d2ad",   # Route Green
            "customer": "#ff9f43",  # Customer Orange
            "text": "#e0e0e0",
            "text_dim": "#a0a0a0",
            "border": "#333338",
            "warehouse": "#ff5252"  # Warehouse Red
        }

        self.root.configure(bg=self.colors["bg"])
        
        # Logic & State Variables
        self.warehouse_coords = (12.8231, 80.0442) # SRM KTR Default
        # Locations now include a 'type' key: "Warehouse" or "Customer"
        self.locations = [{"name": "Primary Warehouse", "lat": self.warehouse_coords[0], "lng": self.warehouse_coords[1], "type": "Warehouse"}]
        self.markers = []
        self.path_objects = [] 
        self.anim_marker = None
        self.is_animating = False
        
        self.setup_styles()
        self.setup_ui()

    def setup_styles(self):
        """Standardizing UI Aesthetics for Professional Presentation."""
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background=self.colors["bg"])
        style.configure("Card.TLabelframe", background=self.colors["panel"], bordercolor=self.colors["border"])
        style.configure("Card.TLabelframe.Label", background=self.colors["panel"], foreground=self.colors["accent"], font=("Orbitron", 10, "bold"))
        style.configure("TLabel", background=self.colors["panel"], foreground=self.colors["text"], font=("Segoe UI", 10))
        style.configure("AI.Horizontal.TProgressbar", troughcolor=self.colors["bg"], bordercolor=self.colors["border"], background=self.colors["success"])

    def setup_ui(self):
        """Architectural Layout: Logistics Dashboard with Multi-Warehouse support."""
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- LEFT PANEL: LOGISTICS CONTROL ---
        left_panel = ttk.Frame(main_frame, width=380)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15))

        # 1. Location Entry & Type Selector
        search_card = ttk.LabelFrame(left_panel, text=" NODE MANAGEMENT ", style="Card.TLabelframe", padding=15)
        search_card.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(search_card, text="Search Location / Address:").pack(anchor="w")
        self.search_entry = tk.Entry(search_card, bg="#2d2d35", fg="white", insertbackground="white", 
                                     relief="flat", font=("Segoe UI", 11), highlightthickness=1, highlightbackground=self.colors["border"])
        self.search_entry.pack(fill=tk.X, pady=(5, 10), ipady=8)
        self.search_entry.bind("<Return>", lambda e: self.search_location())

        # Node Type Selection
        type_frame = ttk.Frame(search_card)
        type_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(type_frame, text="Add As:").pack(side=tk.LEFT)
        self.node_type_var = tk.StringVar(value="Customer")
        
        # Styled Radio alternatives
        tk.Radiobutton(type_frame, text="Customer", variable=self.node_type_var, value="Customer", 
                       bg=self.colors["panel"], fg=self.colors["customer"], selectcolor="#000", activebackground=self.colors["panel"]).pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(type_frame, text="Warehouse", variable=self.node_type_var, value="Warehouse", 
                       bg=self.colors["panel"], fg=self.colors["warehouse"], selectcolor="#000", activebackground=self.colors["panel"]).pack(side=tk.LEFT)

        tk.Button(search_card, text="SEARCH & ADD NODE", bg=self.colors["accent"], fg="white", 
                  font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2", command=self.search_location).pack(fill=tk.X, ipady=8, pady=(5,0))

        # 2. Analytics Dashboard
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
        list_card = ttk.LabelFrame(left_panel, text=" LOGISTICS MANIFEST ", style="Card.TLabelframe", padding=15)
        list_card.pack(fill=tk.BOTH, expand=True)

        self.loc_listbox = tk.Listbox(list_card, bg="#18181c", fg="#ccc", font=("Segoe UI", 10), 
                                      borderwidth=0, highlightthickness=0, selectbackground=self.colors["accent"])
        self.loc_listbox.pack(fill=tk.BOTH, expand=True)
        
        tk.Button(list_card, text="RESET ALL NODES", bg="#3a3a42", fg="white", font=("Segoe UI", 9),
                  relief="flat", cursor="hand2", command=self.clear_data).pack(fill=tk.X, pady=(10, 0), ipady=4)

        # --- RIGHT PANEL: MAP & AI INTERFACE ---
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Interactive Map
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

        self.solve_btn = tk.Button(ai_frame, text="RUN MULTI-WAREHOUSE ROUTE OPTIMIZER", 
                                   bg=self.colors["success"], fg="#000", font=("Segoe UI", 11, "bold"),
                                   relief="flat", cursor="hand2", command=self.start_ai_task)
        self.solve_btn.pack(fill=tk.X, ipady=14)

        # AI Log & Final Route Summary
        log_card = ttk.LabelFrame(right_panel, text=" AI LOGISTICS INTELLIGENCE ", style="Card.TLabelframe", padding=10)
        log_card.pack(fill=tk.X, pady=(15, 0))

        self.log_text = tk.Text(log_card, height=6, bg="#121214", fg=self.colors["success"], 
                                font=("Consolas", 10), relief="flat", padx=10, pady=10)
        self.log_text.pack(fill=tk.X)
        self.log_text.insert(tk.END, "> Multi-Depot System Initialized. Add warehouses and customers to compute.")

        # Markers
        self.warehouse_marker = self.map_widget.set_marker(self.warehouse_coords[0], self.warehouse_coords[1], 
                                                         text="WH: SRM KTR", marker_color_circle=self.colors["warehouse"])
        
        # Right-click bindings
        self.map_widget.add_right_click_menu_command(label="Add as Warehouse", command=lambda c: self.add_point_from_map(c, "Warehouse"), pass_coords=True)
        self.map_widget.add_right_click_menu_command(label="Add as Customer", command=lambda c: self.add_point_from_map(c, "Customer"), pass_coords=True)

        self.update_listbox()

    # --- AI INFERENCE & MULTI-WAREHOUSE LOGIC ---

    def haversine(self, lat1, lon1, lat2, lon2):
        """Standard AI Heuristic: Earth-curvature distance calculation."""
        R = 6371
        dlat, dlon = math.radians(lat2-lat1), math.radians(lon2-lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    def get_road_path(self, p1, p2):
        """OSRM API integration for actual road tracking."""
        try:
            url = f"http://router.project-osrm.org/route/v1/driving/{p1[1]},{p1[0]};{p2[1]},{p2[0]}?overview=full&geometries=geojson"
            response = requests.get(url, timeout=5)
            data = response.json()
            if data['code'] == 'Ok':
                raw_coords = data['routes'][0]['geometry']['coordinates']
                return [(c[1], c[0]) for c in raw_coords], data['routes'][0]['distance'] / 1000
        except:
            pass
        return [p1, p2], self.haversine(p1[0], p1[1], p2[0], p2[1])

    def solve_multi_depot_greedy(self):
        """
        AI Logic: Multi-Warehouse Greedy Search.
        Treats all locations as nodes in a unified TSP sequence.
        Starts at the first warehouse, visits all customers and additional warehouses, 
        then returns to the primary warehouse.
        """
        nodes_to_visit = self.locations[1:] # All nodes except primary WH
        current = self.locations[0]
        route = [current]
        
        while nodes_to_visit:
            # Greedy step: Find closest next node regardless of type
            nearest = min(nodes_to_visit, key=lambda n: self.haversine(current['lat'], current['lng'], n['lat'], n['lng']))
            route.append(nearest)
            nodes_to_visit.remove(nearest)
            current = nearest
        
        route.append(self.locations[0]) # Return to base
        return route

    def start_ai_task(self):
        if len(self.locations) < 3:
            messagebox.showwarning("Logic Error", "Add at least 2 nodes (e.g., 1 WH + 1 Customer) to optimize.")
            return
        
        self.solve_btn.config(state=tk.DISABLED, text="AI COMPUTING MULTI-DEPOT ROUTE...")
        self.is_animating = False
        self.log_text.delete(1.0, tk.END)
        self.log_text.insert(tk.END, "> Analyzing Multi-Warehouse Network Topology...\n")
        self.progress['value'] = 0
        
        def run():
            stops = self.solve_multi_depot_greedy()
            self.log_text.insert(tk.END, "> Sequence Optimized via Nearest Neighbor.\n")
            
            full_path = []
            total_km = 0
            
            for i in range(len(stops) - 1):
                c1 = (stops[i]['lat'], stops[i]['lng'])
                c2 = (stops[i+1]['lat'], stops[i+1]['lng'])
                seg, km = self.get_road_path(c1, c2)
                full_path.extend(seg)
                total_km += km
                self.progress['value'] = (i+1) / len(stops) * 100
                self.log_text.insert(tk.END, f"  - Segment {i+1}: {stops[i]['name']} -> {stops[i+1]['name']}\n")
                self.log_text.see(tk.END)
            
            self.root.after(0, lambda: self.finalize_ui(full_path, total_km, stops))

        threading.Thread(target=run, daemon=True).start()

    def finalize_ui(self, road_path, total_km, stops):
        self.stats_labels["Total Road Dist"].config(text=f"{total_km:.2f} km")
        self.stats_labels["Travel Time"].config(text=f"{int(total_km * 4)} mins") 
        self.stats_labels["Fuel Cost"].config(text=f"₹{total_km * 10.25:.2f}")

        for p in self.path_objects: p.delete()
        self.path_objects = [self.map_widget.set_path(road_path, color=self.colors["success"], width=4)]
        
        self.log_text.insert(tk.END, "\nOPTIMIZED MULTI-DEPOT MANIFEST:\n")
        route_str = " → ".join([s['name'] for s in stops])
        self.log_text.insert(tk.END, f"{route_str}\n")
        
        self.is_animating = True
        self.animate_path(road_path)
        self.solve_btn.config(state=tk.NORMAL, text="RUN MULTI-WAREHOUSE ROUTE OPTIMIZER")

    def animate_path(self, coords, index=0):
        if not self.is_animating or index >= len(coords):
            if self.anim_marker: self.anim_marker.delete()
            return
        lat, lng = coords[index]
        if not self.anim_marker:
            self.anim_marker = self.map_widget.set_marker(lat, lng, text="🚚", marker_color_circle=self.colors["accent"])
        else:
            self.anim_marker.set_position(lat, lng)
        step_skip = 2 if len(coords) > 250 else 1
        self.root.after(20, lambda: self.animate_path(coords, index + step_skip))

    # --- UI INTERACTION ---

    def search_location(self):
        address = self.search_entry.get().strip()
        node_type = self.node_type_var.get()
        if not address: return
        
        m = self.map_widget.set_address(address, marker=True)
        if m:
            marker_color = self.colors["warehouse"] if node_type == "Warehouse" else "#000"
            m.set_marker_color_circle(marker_color)
            m.set_text(f"{'WH' if node_type == 'Warehouse' else 'C'}: {address[:15]}")
            
            self.locations.append({"name": address, "lat": m.position[0], "lng": m.position[1], "type": node_type})
            self.markers.append(m)
            self.update_listbox()
            self.search_entry.delete(0, tk.END)
            self.map_widget.set_position(m.position[0], m.position[1])
        else:
            messagebox.showerror("Error", "Location not found.")

    def add_point_from_map(self, coords, node_type):
        name = f"{'WH' if node_type == 'Warehouse' else 'Node'} {len(self.locations)}"
        self.locations.append({"name": name, "lat": coords[0], "lng": coords[1], "type": node_type})
        
        m_color = self.colors["warehouse"] if node_type == "Warehouse" else "#000"
        m = self.map_widget.set_marker(coords[0], coords[1], text=name, marker_color_circle=m_color)
        self.markers.append(m)
        self.update_listbox()

    def update_listbox(self):
        self.loc_listbox.delete(0, tk.END)
        for i, loc in enumerate(self.locations):
            icon = "🏠" if loc['type'] == "Warehouse" else "📍"
            self.loc_listbox.insert(tk.END, f" {icon} {loc['name']}")

    def clear_data(self):
        self.is_animating = False
        self.locations = [{"name": "Warehouse (SRM KTR)", "lat": 12.8231, "lng": 80.0442, "type": "Warehouse"}]
        for m in self.markers: m.delete()
        for p in self.path_objects: p.delete()
        if self.anim_marker: self.anim_marker.delete()
        self.map_widget.set_position(12.8231, 80.0442)
        self.update_listbox()
        self.log_text.delete(1.0, tk.END)
        for l in self.stats_labels.values(): l.config(text="0.00")

if __name__ == "__main__":
    root = tk.Tk()
    app = DeliveryRoutePlanner(root)
    root.mainloop()
