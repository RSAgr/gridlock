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
        self._prepare_nodes()
        self._build_adjacency()

    def _prepare_nodes(self):
        # 1. Clean spacing tokens
        for col in ['zone', 'corridor', 'junction']:
            self.df[col] = self.df[col].astype(str).str.strip().str.replace(' ', '_')
            
        # 2. Extract valid coordinates and calculate median centers
        valid_coords = self.df[(self.df['latitude'] != 0) & (self.df['longitude'] != 0)].dropna(subset=['latitude', 'longitude'])
        self.unique_nodes = valid_coords.groupby(['zone', 'corridor', 'junction']).agg({
            'latitude': 'median',
            'longitude': 'median'
        }).reset_index()
        
        # 3. Create Unique Keys
        self.unique_nodes['node_id'] = self.unique_nodes['zone'] + "_" + self.unique_nodes['corridor'] + "_" + self.unique_nodes['junction']
        
        # Merge back to original df and setup temporal features
        self.df = pd.merge(self.df, self.unique_nodes[['zone', 'corridor', 'junction', 'node_id']], on=['zone', 'corridor', 'junction'], how='left')
        self.df['start_datetime'] = pd.to_datetime(self.df['start_datetime'], format='mixed', errors='coerce')
        self.df['hour'] = self.df['start_datetime'].dt.hour
        self.df['is_weekend'] = self.df['start_datetime'].dt.dayofweek >= 5

        # 4. Initialize Spatial Indexes for rapid math
        self.gdf_nodes = gpd.GeoDataFrame(self.unique_nodes, geometry=gpd.points_from_xy(self.unique_nodes.longitude, self.unique_nodes.latitude), crs="EPSG:4326")
        self.gdf_metric = self.gdf_nodes.to_crs(epsg=32643)

        # 5. Fast Lookup Dictionary
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
        """Calculates 500m-2km radius health scores for stationary isolated hazards."""
        node_data = self.unique_nodes[self.unique_nodes['node_id'] == node_id].iloc[0]
        event_point = gpd.GeoSeries([Point(node_data['longitude'], node_data['latitude'])], crs="EPSG:4326").to_crs(epsg=32643).iloc[0]
        
        self.gdf_metric['dist'] = self.gdf_metric.geometry.distance(event_point)
        cands = self.gdf_metric[(self.gdf_metric['dist'] <= 2000) & (self.gdf_metric['dist'] > 500)].copy()
        
        logical = cands[cands['corridor'] == node_data['corridor']].copy()
        if logical.empty: logical = cands.copy()
        
        hist = self.df[(self.df['hour'] == hr) & (self.df['is_weekend'] == is_wknd)]
        counts = hist['node_id'].value_counts().reset_index()
        counts.columns = ['node_id', 'count']
        
        logical = logical.drop_duplicates(subset=['junction'])
        res = pd.merge(logical, counts, on='node_id', how='left')
        res['count'] = res['count'].fillna(0)
        res['health'] = 1 / (1 + res['count'])
        return res.sort_values(by='health', ascending=False).reset_index(drop=True)

    def get_route_diversions(self, route_path, hr, is_wknd):
        """
        Uses Breadth-First Search (BFS) to find an alternate path from start to end,
        explicitly blocking all intermediate nodes of the planned event route.
        """
        from collections import deque

        if len(route_path) < 2:
            return {"status": "error"}

        start_node = route_path[0]
        end_node = route_path[-1]

        # Block all intermediate nodes so the algorithm is forced to bypass the event
        blocked_nodes = set(route_path[1:-1])

        # BFS Setup: Queue holds (current_node, path_history)
        queue = deque([(start_node, [start_node])])
        visited = set([start_node])
        alternate_path = None

        while queue:
            current, path = queue.popleft()

            # Target reached
            if current == end_node:
                # If the user only selected 2 nodes (A->B), we must avoid the direct A->B edge 
                # so we can find a true detour (A->C->B).
                if len(path) > 2 or (len(path) == 2 and len(route_path) > 2): 
                     alternate_path = path
                     break

            # Explore Valid Neighbors
            for neighbor in self.adj_graph.get(current, []):
                if neighbor not in visited and neighbor not in blocked_nodes:
                    # Skip the direct blocked edge if it's a 2-node event route
                    if current == start_node and neighbor == end_node and len(route_path) == 2:
                        continue 
                    
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        if alternate_path:
            # Build healthy score payload for the successful detour
            hist = self.df[(self.df['hour'] == hr) & (self.df['is_weekend'] == is_wknd)]
            counts = hist['node_id'].value_counts().to_dict()
            
            path_details = []
            total_incidents = 0
            for nid in alternate_path:
                c = counts.get(nid, 0)
                total_incidents += c
                path_details.append({
                    'junction': self.node_lookup[nid]['junction'].replace('_', ' '),
                    'corridor': self.node_lookup[nid]['corridor'].replace('_', ' '),
                    'health': 1 / (1 + c)
                })
            
            # Average Health of the new path
            avg_health = 1 / (1 + (total_incidents / len(alternate_path)))
            return {"status": "success", "path": path_details, "avg_health": avg_health}
        else:
            # Fallback if no continuous graph path exists (network is disconnected)
            fallback = self.get_single_point_diversions(start_node, hr, is_wknd).head(3)
            return {"status": "fallback", "nodes": fallback}