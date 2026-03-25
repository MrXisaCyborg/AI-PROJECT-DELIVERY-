import tkinter as tk
from tkinter import messagebox, ttk
import tkintermapview
import math
import time
import threading
import requests # Required for Road-Routing API (OSRM)

# TECHNICAL NOTE: 
# This application implements a Multi-Depot Vehicle Routing Problem (MDVRP) logic.
# Enhanced Feature: Dynamic Warehouse Status (Active/Closed).
# 1. Assignment: Customers are mapped to the nearest ACTIVE warehouse.
# 2. Routing: Independent Greedy Nearest Neighbor routes per active depot.
# 3. Pathfinding: OSRM API for real-world road navigation.

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
            "warehouse": "#ff5252", # Warehouse Red
            "closed": "#555555",    # Closed/Inactive Gray
            "route_alt": ["#00a8ff", "#9b59b6", "#f1c40f", "#e67e22", "#1abc9c"] 
        }

        self.root.configure(bg=self.colors["bg"])
        
        # Logic & State Variables
        self.warehouse_coords = (12.8231, 80.0442) # SRM KTR Default
        # Locations now include 'active' status for Warehouses
        self.locations = [{"name": "Primary Warehouse", "lat": self.warehouse_coords[0], "lng": self.warehouse_coords[1], "type": "Warehouse", "active": True}]
        self.markers = [] # We'll store marker objects here
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
        
        tk.Radiobutton(type_frame, text="Customer", variable=self.node_type_var, value="Customer", 
                       bg=self.colors["panel"], fg=self.colors["customer"], selectcolor="#000", activebackground=self.colors["panel"]).pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(type_frame, text="Warehouse", variable=self.node_type_var, value="Warehouse", 
                       bg=self.colors["panel"], fg=self.colors["warehouse"], selectcolor="#000", activebackground=self.colors["panel"]).pack(side=tk.LEFT)

        tk.Button(search_card, text="SEARCH & ADD NODE", bg=self.colors["accent"], fg="white", 
                  font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2", command=self.search_location).pack(fill=tk.X, ipady=8, pady=(5,0))

        # 2. Analytics Dashboard
        stats_card = ttk.LabelFrame(left_panel, text=" ROAD ANALYTICS (AGGREGATE) ", style="Card.TLabelframe", padding=15)
        stats_card.pack(fill=tk.X, pady=(0, 15))

        self.stats_labels = {}
        metrics = [("Total Distance", "0.00 km"), ("Avg. Trip Time", "0 mins"), ("Est. Fuel Cost", "₹0.00")]
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
        
        # Toggle Button for Warehouse Status
        self.toggle_btn = tk.Button(list_card, text="TOGGLE WAREHOUSE STATUS", bg=self.colors["accent"], fg="white", font=("Segoe UI", 9, "bold"),
                                   relief="flat", cursor="hand2", command=self.toggle_node_status)
        self.toggle_btn.pack(fill=tk.X, pady=(10, 5), ipady=4)

        tk.Button(list_card, text="RESET SYSTEM", bg="#3a3a42", fg="white", font=("Segoe UI", 9),
                  relief="flat", cursor="hand2", command=self.clear_data).pack(fill=tk.X, pady=(0, 0), ipady=4)

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

        self.solve_btn = tk.Button(ai_frame, text="RUN MULTI-DEPOT SERVICE ASSIGNMENT", 
                                   bg=self.colors["success"], fg="#000", font=("Segoe UI", 11, "bold"),
                                   relief="flat", cursor="hand2", command=self.start_ai_task)
        self.solve_btn.pack(fill=tk.X, ipady=14)

        # AI Log & Final Route Summary
        log_card = ttk.LabelFrame(right_panel, text=" AI LOGISTICS INTELLIGENCE ", style="Card.TLabelframe", padding=10)
        log_card.pack(fill=tk.X, pady=(15, 0))

        self.log_text = tk.Text(log_card, height=8, bg="#121214", fg=self.colors["success"], 
                                font=("Consolas", 10), relief="flat", padx=10, pady=10)
        self.log_text.pack(fill=tk.X)
        self.log_text.insert(tk.END, "> Multi-Depot System Active. Use the Manifest to activate/close warehouses.")

        # Markers
        wh_marker = self.map_widget.set_marker(self.warehouse_coords[0], self.warehouse_coords[1], 
                                               text="WH: SRM KTR", marker_color_circle=self.colors["warehouse"])
        self.markers.append(wh_marker)
        
        # Right-click bindings
        self.map_widget.add_right_click_menu_command(label="Add as Warehouse", command=lambda c: self.add_point_from_map(c, "Warehouse"), pass_coords=True)
        self.map_widget.add_right_click_menu_command(label="Add as Customer", command=lambda c: self.add_point_from_map(c, "Customer"), pass_coords=True)

        self.update_listbox()

    # --- LOGIC: STATUS MANAGEMENT ---

    def toggle_node_status(self):
        """Toggles the active state of a warehouse."""
        selection = self.loc_listbox.curselection()
        if not selection:
            messagebox.showinfo("Selection Required", "Select a warehouse from the manifest to toggle its status.")
            return
        
        idx = selection[0]
        node = self.locations[idx]
        
        if node['type'] != "Warehouse":
            messagebox.showinfo("Invalid Selection", "Only Warehouse nodes can be activated or closed.")
            return

        # Toggle state
        node['active'] = not node.get('active', True)
        
        # Update Marker Visuals
        marker = self.markers[idx]
        if node['active']:
            marker.set_marker_color_circle(self.colors["warehouse"])
            marker.set_text(f"WH: {node['name'][:10]}")
        else:
            marker.set_marker_color_circle(self.colors["closed"])
            marker.set_text(f"[CLOSED] {node['name'][:10]}")
            
        self.update_listbox()
        status_text = "ACTIVATED" if node['active'] else "CLOSED"
        self.log_text.insert(tk.END, f"\n> {node['name']} has been {status_text}.")
        self.log_text.see(tk.END)

    # --- AI INFERENCE: MULTI-DEPOT ASSIGNMENT & ROUTING ---

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

    def solve_multi_depot_assignment(self):
        """
        EXPERT LOGIC: Assignment-First, Route-Second.
        Filters for ACTIVE warehouses only.
        """
        active_warehouses = [loc for loc in self.locations if loc['type'] == "Warehouse" and loc.get('active', True)]
        customers = [loc for loc in self.locations if loc['type'] == "Customer"]
        
        if not active_warehouses:
            return None
        
        assignments = {i: [] for i in range(len(active_warehouses))}
        
        # Step 1: Assignment Heuristic (to nearest active warehouse)
        for cust in customers:
            nearest_idx = min(range(len(active_warehouses)), key=lambda i: self.haversine(
                cust['lat'], cust['lng'], active_warehouses[i]['lat'], active_warehouses[i]['lng']))
            assignments[nearest_idx].append(cust)
            
        # Step 2: Routing for each active warehouse
        final_routes = []
        for idx, assigned_customers in assignments.items():
            if not assigned_customers: continue
            
            wh = active_warehouses[idx]
            route = [wh]
            unvisited = assigned_customers[:]
            current = wh
            
            while unvisited:
                nearest = min(unvisited, key=lambda n: self.haversine(current['lat'], current['lng'], n['lat'], n['lng']))
                route.append(nearest)
                unvisited.remove(nearest)
                current = nearest
            
            route.append(wh) 
            final_routes.append({"warehouse": wh, "route": route})
            
        return final_routes

    def start_ai_task(self):
        active_warehouses = [loc for loc in self.locations if loc['type'] == "Warehouse" and loc.get('active', True)]
        customers = [loc for loc in self.locations if loc['type'] == "Customer"]
        
        if not active_warehouses:
            messagebox.showerror("No Active Warehouses", "Please activate at least one warehouse to process deliveries.")
            return
        if not customers:
            messagebox.showwarning("No Customers", "Add at least one customer node.")
            return
        
        self.solve_btn.config(state=tk.DISABLED, text="AI RE-ASSIGNING DEPOTS...")
        self.is_animating = False
        self.log_text.delete(1.0, tk.END)
        self.log_text.insert(tk.END, f"> Found {len(active_warehouses)} Active Depots.\n")
        self.progress['value'] = 0
        
        def run():
            depot_routes = self.solve_multi_depot_assignment()
            if not depot_routes:
                self.root.after(0, lambda: self.solve_btn.config(state=tk.NORMAL, text="RUN MULTI-DEPOT SERVICE ASSIGNMENT"))
                return

            all_road_paths = []
            aggregate_km = 0
            
            for d_idx, depot_data in enumerate(depot_routes):
                wh = depot_data['warehouse']
                stops = depot_data['route']
                route_path = []
                
                self.log_text.insert(tk.END, f"\n> {wh['name']} (ACTIVE) -> Serving {len(stops)-2} nodes:\n")
                
                for i in range(len(stops) - 1):
                    c1 = (stops[i]['lat'], stops[i]['lng'])
                    c2 = (stops[i+1]['lat'], stops[i+1]['lng'])
                    seg, km = self.get_road_path(c1, c2)
                    route_path.extend(seg)
                    aggregate_km += km
                    self.log_text.insert(tk.END, f"  - [{wh['name'][:5]}] Serving: {stops[i+1]['name']}\n")
                    self.log_text.see(tk.END)
                
                all_road_paths.append(route_path)
                self.progress['value'] = (d_idx + 1) / len(depot_routes) * 100
            
            self.root.after(0, lambda: self.finalize_ui(all_road_paths, aggregate_km, depot_routes))

        threading.Thread(target=run, daemon=True).start()

    def finalize_ui(self, all_road_paths, total_km, depot_routes):
        self.stats_labels["Total Distance"].config(text=f"{total_km:.2f} km")
        self.stats_labels["Avg. Trip Time"].config(text=f"{int(total_km * 4 / len(all_road_paths))} mins") 
        self.stats_labels["Est. Fuel Cost"].config(text=f"₹{total_km * 10.5:.2f}")

        for p in self.path_objects: p.delete()
        self.path_objects = []
        
        sequential_path = []
        for idx, path in enumerate(all_road_paths):
            color = self.colors["route_alt"][idx % len(self.colors["route_alt"])]
            p_obj = self.map_widget.set_path(path, color=color, width=4)
            self.path_objects.append(p_obj)
            sequential_path.extend(path)
        
        self.log_text.insert(tk.END, "\n> ROUTING COMPLETE BASED ON ACTIVE DEPOT CONSTRAINTS.\n")
        
        self.is_animating = True
        self.animate_path(sequential_path)
        self.solve_btn.config(state=tk.NORMAL, text="RUN MULTI-DEPOT SERVICE ASSIGNMENT")

    def animate_path(self, coords, index=0):
        if not self.is_animating or index >= len(coords):
            if self.anim_marker: self.anim_marker.delete()
            return
        lat, lng = coords[index]
        if not self.anim_marker:
            self.anim_marker = self.map_widget.set_marker(lat, lng, text="🚚", marker_color_circle=self.colors["success"])
        else:
            self.anim_marker.set_position(lat, lng)
        step_skip = 3 if len(coords) > 500 else 1
        self.root.after(15, lambda: self.animate_path(coords, index + step_skip))

    # --- UI INTERACTION ---

    def search_location(self):
        address = self.search_entry.get().strip()
        node_type = self.node_type_var.get()
        if not address: return
        
        m = self.map_widget.set_address(address, marker=True)
        if m:
            marker_color = self.colors["warehouse"] if node_type == "Warehouse" else self.colors["customer"]
            m.set_marker_color_circle(marker_color)
            m.set_text(f"{'WH' if node_type == 'Warehouse' else 'C'}: {address[:15]}")
            
            self.locations.append({"name": address, "lat": m.position[0], "lng": m.position[1], "type": node_type, "active": True})
            self.markers.append(m)
            self.update_listbox()
            self.search_entry.delete(0, tk.END)
            self.map_widget.set_position(m.position[0], m.position[1])
        else:
            messagebox.showerror("Error", "Location not found.")

    def add_point_from_map(self, coords, node_type):
        name = f"{'WH' if node_type == 'Warehouse' else 'Node'} {len(self.locations)}"
        self.locations.append({"name": name, "lat": coords[0], "lng": coords[1], "type": node_type, "active": True})
        
        m_color = self.colors["warehouse"] if node_type == "Warehouse" else self.colors["customer"]
        m = self.map_widget.set_marker(coords[0], coords[1], text=name, marker_color_circle=m_color)
        self.markers.append(m)
        self.update_listbox()

    def update_listbox(self):
        self.loc_listbox.delete(0, tk.END)
        for i, loc in enumerate(self.locations):
            icon = "🏠" if loc['type'] == "Warehouse" else "📍"
            status = ""
            if loc['type'] == "Warehouse":
                status = " [ACTIVE]" if loc.get('active', True) else " [CLOSED]"
            self.loc_listbox.insert(tk.END, f" {icon} {loc['name']}{status}")

    def clear_data(self):
        self.is_animating = False
        self.locations = [{"name": "Warehouse (SRM KTR)", "lat": 12.8231, "lng": 80.0442, "type": "Warehouse", "active": True}]
        for m in self.markers: m.delete()
        for p in self.path_objects: p.delete()
        if self.anim_marker: self.anim_marker.delete()
        self.markers = []
        # Re-add primary warehouse marker
        wh_marker = self.map_widget.set_marker(12.8231, 80.0442, text="WH: SRM KTR", marker_color_circle=self.colors["warehouse"])
        self.markers.append(wh_marker)
        self.map_widget.set_position(12.8231, 80.0442)
        self.update_listbox()
        self.log_text.delete(1.0, tk.END)
        for l in self.stats_labels.values(): l.config(text="0.00")

if __name__ == "__main__":
    root = tk.Tk()
    app = DeliveryRoutePlanner(root)
    root.mainloop()
