# modules/routing_engine.py
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import ast
from collections import defaultdict
import warnings
import os

warnings.filterwarnings('ignore')

class RoutingEngine:
    def __init__(self, data_path="datasets/givenData.csv"):
        if not os.path.exists(data_path):
            raise FileNotFoundError(f"Dataset not found at: {data_path}")
        
        self.df = pd.read_csv(data_path)
        
        # --- 1. NEW: Load Static Risk Dataframes ---
        self.j_scores_df = pd.read_csv("datasets/junction_scores.csv")
        self.e_scores_df = pd.read_csv("datasets/event_congestion_scores.csv")
        
        self._prepare_nodes()
        self._build_adjacency()

    def _prepare_nodes(self):
        # Clean spacing tokens
        for col in ['zone', 'corridor', 'junction']:
            self.df[col] = self.df[col].astype(str).str.strip().str.replace(' ', '_')
            
        # Extract valid coordinates and calculate median centers
        valid_coords = self.df[(self.df['latitude'] != 0) & (self.df['longitude'] != 0)].dropna(subset=['latitude', 'longitude'])
        self.unique_nodes = valid_coords.groupby(['zone', 'corridor', 'junction']).agg({
            'latitude': 'median',
            'longitude': 'median'
        }).reset_index()
        
        # Create Unique Keys
        self.unique_nodes['node_id'] = self.unique_nodes['zone'] + "_" + self.unique_nodes['corridor'] + "_" + self.unique_nodes['junction']
        
        # Merge back to original df and setup temporal features
        self.df = pd.merge(self.df, self.unique_nodes[['zone', 'corridor', 'junction', 'node_id']], on=['zone', 'corridor', 'junction'], how='left')
        self.df['start_datetime'] = pd.to_datetime(self.df['start_datetime'], format='mixed', errors='coerce')
        self.df['hour'] = self.df['start_datetime'].dt.hour
        self.df['is_weekend'] = self.df['start_datetime'].dt.dayofweek >= 5

        # Initialize Spatial Indexes for rapid math
        self.gdf_nodes = gpd.GeoDataFrame(self.unique_nodes, geometry=gpd.points_from_xy(self.unique_nodes.longitude, self.unique_nodes.latitude), crs="EPSG:4326")
        self.gdf_metric = self.gdf_nodes.to_crs(epsg=32643)

        # Fast Lookup Dictionary
        self.node_lookup = self.unique_nodes.set_index('node_id')[['junction', 'corridor', 'zone']].to_dict(orient='index')

    def _map_gps(self, lat, lon):
        try:
            raw_point = gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326").to_crs(epsg=32643).iloc[0]
            nearest_idx, distances = self.gdf_metric.sindex.nearest(raw_point, return_distance=True)
            if len(distances) > 0 and distances[0] <= 150: # 150m snapping threshold
                return self.gdf_metric.iloc[nearest_idx[1][0]]['node_id']
        except Exception:
            pass
        return None

    def _build_adjacency(self):
        self.adj_list = defaultdict(set)
        path_df = self.df[self.df['route_path'].notna() & (self.df['route_path'] != '')]
        
        for _, row in path_df.iterrows():
            try:
                coords = ast.literal_eval(str(row['route_path']).strip())
                if not isinstance(coords, list): continue
            except Exception: continue
            
            seq = []
            for coord in coords:
                if len(coord) == 2:
                    nid = self._map_gps(coord[0], coord[1])
                    if nid and (not seq or seq[-1] != nid):
                        seq.append(nid)
                        
            for i in range(len(seq)-1):
                node_a = seq[i]
                node_b = seq[i+1]
                
                # Add forward connection (i -> i+1)
                self.adj_list[node_a].add(node_b)
                
                # Add reverse connection (i+1 -> i)
                self.adj_list[node_b].add(node_a)
                
        self.adj_graph = {k: list(v) for k, v in self.adj_list.items()}

    # --- UI HELPER FUNCTIONS ---
    def get_all_nodes_dict(self):
        """Returns all 388 junctions dynamically formatted for Streamlit Selectboxes."""
        return {
            nid: f"{info['junction'].replace('_', ' ')}, {info['corridor'].replace('_', ' ')}, {info['zone'].replace('_', ' ')}"
            for nid, info in self.node_lookup.items()
        }

    def get_neighbors_dict(self, node_id):
        """Returns only strictly adjacent downstream junctions for dynamic route planning."""
        neighbors = self.adj_graph.get(node_id, [])
        return {
            nid: f"{self.node_lookup[nid]['junction'].replace('_', ' ')}, {self.node_lookup[nid]['corridor'].replace('_', ' ')}, {self.node_lookup[nid]['zone'].replace('_', ' ')}"
            for nid in neighbors if nid in self.node_lookup
        }
        
    def get_single_point_diversions(self, node_id, hr, is_wknd):
        """Calculates 500m-2km radius health scores blending live incidents and junction risk."""
        node_data = self.unique_nodes[self.unique_nodes['node_id'] == node_id].iloc[0]
        event_point = gpd.GeoSeries([Point(node_data['longitude'], node_data['latitude'])], crs="EPSG:4326").to_crs(epsg=32643).iloc[0]
        
        self.gdf_metric['dist'] = self.gdf_metric.geometry.distance(event_point)
        cands = self.gdf_metric[(self.gdf_metric['dist'] <= 2000) & (self.gdf_metric['dist'] > 500)].copy()
        
        logical = cands[cands['corridor'] == node_data['corridor']].copy()
        if logical.empty: logical = cands.copy()
        
        # Pull Live Incident Counts
        hist = self.df[(self.df['hour'] == hr) & (self.df['is_weekend'] == is_wknd)]
        counts = hist['node_id'].value_counts().reset_index()
        counts.columns = ['node_id', 'count']
        
        logical = logical.drop_duplicates(subset=['junction'])
        res = pd.merge(logical, counts, on='node_id', how='left')
        res['count'] = res['count'].fillna(0)
        
        # --- 2. NEW: Incorporate Junction Static Risk Scores ---
        res['clean_junc_key'] = res['junction'].str.replace('_', '')
        self.j_scores_df['clean_junc_key'] = self.j_scores_df['junction'].str.replace('_', '')
        
        res = pd.merge(res, self.j_scores_df[['clean_junc_key', 'risk_score']], on='clean_junc_key', how='left')
        res['risk_score'] = res['risk_score'].fillna(res['risk_score'].median()) # Safe fallback
        
        # Hybrid Predictive Health Score Formula
        # Penalty = (70% weight on active incidents) + (30% weight on base junction risk index)
        res['health'] = 1 / (1 + (res['count'] * 0.70) + ((res['risk_score'] / 100.0) * 0.30))
        
        return res.sort_values(by='health', ascending=False).reset_index(drop=True)

    # --- 3. NEW: Add active_event_type parameter for Multi-Point Routing ---
    def get_route_diversions(self, route_path, hr, is_wknd, active_event_type="others"):
        """
        Uses Breadth-First Search (BFS) to find an alternate path from start to end,
        explicitly blocking intermediate nodes, scoring edges by cumulative risk matrices.
        """
        from collections import deque

        if len(route_path) < 2:
            return {"status": "error"}

        start_node = route_path[0]
        end_node = route_path[-1]
        blocked_nodes = set(route_path[1:-1])

        # BFS Setup: Queue holds (current_node, path_history)
        queue = deque([(start_node, [start_node])])
        visited = set([start_node])
        alternate_path = None

        while queue:
            current, path = queue.popleft()

            if current == end_node:
                if len(path) > 2 or (len(path) == 2 and len(route_path) > 2): 
                     alternate_path = path
                     break

            for neighbor in self.adj_graph.get(current, []):
                if neighbor not in visited and neighbor not in blocked_nodes:
                    if current == start_node and neighbor == end_node and len(route_path) == 2:
                        continue 
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        if alternate_path:
            # Pull historical count tracking dictionaries
            hist = self.df[(self.df['hour'] == hr) & (self.df['is_weekend'] == is_wknd)]
            counts = hist['node_id'].value_counts().to_dict()
            
            # --- NEW: Match the current active event multiplier weight ---
            e_match = self.e_scores_df[self.e_scores_df["event_cause"].str.lower() == active_event_type.lower()]
            event_severity = e_match.iloc[0]["event_congestion_score"] if not e_match.empty else 50.0
            
            path_details = []
            total_penalty = 0
            
            # Clean up the local index structure for quick access
            j_risk_lookup = self.j_scores_df.set_index(self.j_scores_df['junction'].str.replace('_', '').str.lower())['risk_score'].to_dict()
            
            for nid in alternate_path:
                c_incidents = counts.get(nid, 0)
                
                # Fetch static junction structure metrics
                j_clean = self.node_lookup[nid]['junction'].replace('_', '').lower()
                base_junc_risk = j_risk_lookup.get(j_clean, 35.0) # default fallback median
                
                # Dynamic Edge Penalty Score Formula
                # Combines live constraints with base corridor vulnerability and global event intensity
                node_penalty = (c_incidents * 0.50) + ((base_junc_risk / 100.0) * 0.30) + ((event_severity / 100.0) * 0.20)
                total_penalty += node_penalty
                
                path_details.append({
                    'junction': self.node_lookup[nid]['junction'].replace('_', ' '),
                    'corridor': self.node_lookup[nid]['corridor'].replace('_', ' '),
                    'health': 1 / (1 + node_penalty)
                })
            
            # Average Health across the completed BFS graph route
            avg_health = 1 / (1 + (total_penalty / len(alternate_path)))
            return {
                "status": "success",
                "path": path_details,
                "node_ids": alternate_path,
                "avg_health": avg_health
            }
        else:
            fallback = self.get_single_point_diversions(start_node, hr, is_wknd).head(3)
            return {"status": "fallback", "nodes": fallback}
