# file: sa_cvrptw.py

import random
import math
import matplotlib.pyplot as plt
from typing import List, Dict, Tuple
import copy
from multiprocessing import Pool, cpu_count
from geopy.distance import geodesic
from shapely.geometry import MultiPoint
from shapely.geometry.polygon import Polygon


# ---- Global Seed ----
SEED = 42
random.seed(SEED)
DEBUG=True
# ---- Data Classes ----

class Location:
    def __init__(self, id: int, lat: float, lon: float):
        self.id = id
        self.lat = lat
        self.lon = lon


distance_matrix = {}  # global for reuse
def build_distance_matrix(locations: List[Location]) -> Dict[Tuple[int, int], float]:
      matrix = {}
      for i in range(len(locations)):
          for j in range(len(locations)):
              a, b = locations[i], locations[j]
              matrix[(a.id, b.id)] = geodesic((a.lat, a.lon), (b.lat, b.lon)).km
      return matrix

        

class Order:
    def __init__(self, id: int, pickup: Location, delivery: Location,
                 time_window: Tuple[float, float], demand: int):
        self.id = id
        self.pickup = pickup
        self.delivery = delivery
        self.time_window = time_window
        self.demand = demand

class Vehicle:
    def __init__(self, id: int, capacity: int, start: Location, end: Location,
                 location_limits: Tuple[float, float, float, float] = (-90, 90, -180, 180),
                 total_distance_limit: float = float('inf'),
                 travel_distance_limit: float = float('inf'),
                 total_time_limit: float = float('inf'),
                 travel_time_limit: float = float('inf')):
        self.id = id
        self.capacity = capacity
        self.start = start
        self.end = end
        self.location_limits = location_limits
        self.total_distance_limit = total_distance_limit
        self.travel_distance_limit = travel_distance_limit
        self.total_time_limit = total_time_limit
        self.travel_time_limit = travel_time_limit

# ---- Helper Functions ----

def compute_convex_hull(route: List[Location]) -> Polygon:
    points = [(p.lon, p.lat) for p in route]
    return MultiPoint(points).convex_hull

def hulls_intersect(hull1: Polygon, hull2: Polygon) -> bool:
    return hull1.intersects(hull2)



def total_distance(route: List[Location]) -> float:
    return sum(distance_matrix[(route[i].id, route[i+1].id)] for i in range(len(route) - 1))

def evaluate_candidate(args):
    solution, vehicles, overlap_weight, strict_overlap = args
    score = evaluate_solution(solution, vehicles,
                              overlap_weight=overlap_weight,
                              strict_overlap=strict_overlap)
    return (solution, score)

def create_initial_solution(orders: List[Order], vehicles: List[Vehicle]) -> Dict[int, List[Order]]:
    solution = {v.id: [] for v in vehicles}
    random.shuffle(orders)
    for i, order in enumerate(orders):
        solution[vehicles[i % len(vehicles)].id].append(order)
    return solution

def evaluate_solution(solution: Dict[int, List[Order]], vehicles: List[Vehicle],
                      unassigned_orders: List[Order] = [],
                      weights: Dict[str, float] = None,
                      leniency: Dict[str, float] = None,
                      overlap_weight: float = 0.000001, 
                      strict_overlap: bool = True) -> float:
  

    if weights is None:
        weights = {
            'distance': 1.0,
            'time_penalty': 100.0,
            'capacity_penalty': 100.0,
            'unassigned_penalty': 500.0
        }

    if leniency is None:
        leniency = {
            'total_distance': 0.0,
            'travel_distance': 0.0,
            'total_time': 0.0,
            'travel_time': 0.0
        }

    cost = 0
    penalty = 1e6

    for v in vehicles:
        if DEBUG:
          print(f"Evaluating vehicle {v.id} with {len(solution[v.id])} orders")
        route = [v.start]
        load = 0
        time_penalty = 0
        curr_time = 0
        total_travel_distance = 0
        min_lat, max_lat, min_lon, max_lon = v.location_limits
        hulls = []
        for o in solution[v.id]:
            for point in [o.pickup, o.delivery]:
                prev = route[-1]
                dist = distance_matrix[(prev.id, point.id)]
                total_travel_distance += dist
                curr_time += dist / 30.0

                if not (min_lat <= point.lat <= max_lat and min_lon <= point.lon <= max_lon):
                    return penalty

                tw_start, tw_end = o.time_window
                if curr_time < tw_start:
                    time_penalty += (tw_start - curr_time)
                    curr_time = tw_start
                elif curr_time > tw_end:
                    time_penalty += (curr_time - tw_end)

                route.append(point)
            load += o.demand

        route.append(v.end)
        total_dist = total_distance(route)

        if total_dist > v.total_distance_limit * (1 + leniency['total_distance']):
            return penalty
        if total_travel_distance > v.travel_distance_limit * (1 + leniency['travel_distance']):
            return penalty
        if curr_time > v.total_time_limit * (1 + leniency['total_time']):
            return penalty
        if curr_time > v.travel_time_limit * (1 + leniency['travel_time']):
            return penalty
        if overlap_weight > 0 or strict_overlap:
          for i in range(len(hulls)):
              for j in range(i + 1, len(hulls)):
                  if hulls_intersect(hulls[i], hulls[j]):
                      if strict_overlap:
                          return penalty
                      else:
                          cost += overlap_weight        

        hull = compute_convex_hull(route)
        hulls.append(hull)
        if overlap_weight > 0 or strict_overlap:
          for i in range(len(hulls)):
              for j in range(i + 1, len(hulls)):
                  if hulls_intersect(hulls[i], hulls[j]):
                      if strict_overlap:
                          return penalty
                      else:
                          cost += overlap_weight


        capacity_penalty = max(0, load - v.capacity)
        cost += (weights['distance'] * total_dist +
                 weights['time_penalty'] * time_penalty +
                 weights['capacity_penalty'] * capacity_penalty)

    cost += weights['unassigned_penalty'] * len(unassigned_orders)
    return cost

# ---- Remaining Functions Unchanged ----

# ---- Neighborhood Operators ----

def apply_2opt(orders: List[Order]) -> List[Order]:
    if len(orders) < 2: return orders[:]
    i, j = sorted(random.sample(range(len(orders)), 2))
    return orders[:i] + list(reversed(orders[i:j+1])) + orders[j+1:]

def apply_3opt(orders: List[Order]) -> List[Order]:
    if len(orders) < 3: return orders[:]
    i, j, k = sorted(random.sample(range(len(orders)), 3))
    return orders[:i] + list(reversed(orders[i:j])) + list(reversed(orders[j:k])) + orders[k:]

def tour_swap(solution: Dict[int, List[Order]]) -> Dict[int, List[Order]]:
    s = copy.deepcopy(solution)
    v1, v2 = random.sample(list(s.keys()), 2)
    s[v1], s[v2] = s[v2], s[v1]
    return s

def tour_merge(solution: Dict[int, List[Order]]) -> Dict[int, List[Order]]:
    s = copy.deepcopy(solution)
    v1, v2 = random.sample(list(s.keys()), 2)
    merged = s[v1] + s[v2]
    random.shuffle(merged)
    s[v1], s[v2] = merged[:len(merged)//2], merged[len(merged)//2:]
    return s

def split_insert(solution: Dict[int, List[Order]]) -> Dict[int, List[Order]]:
    s = copy.deepcopy(solution)
    all_orders = [o for lst in s.values() for o in lst]
    if not all_orders: return s
    sel = random.choice(all_orders)
    for v in s:
        if sel in s[v]:
            s[v].remove(sel)
            break
    tgt = random.choice(list(s.keys()))
    pos = random.randint(0, len(s[tgt]))
    s[tgt].insert(pos, sel)
    return s

def destroy_and_repair(solution: Dict[int, List[Order]]) -> Dict[int, List[Order]]:
    s = copy.deepcopy(solution)
    all_orders = [o for lst in s.values() for o in lst]
    if len(all_orders) < 2: return s
    removed = random.sample(all_orders, max(1, len(all_orders) // 4))
    for v in s: s[v] = [o for o in s[v] if o not in removed]
    for o in removed:
        random.choice(list(s.values())).append(o)
    return s

def generate_neighbor(solution: Dict[int, List[Order]],
                      vehicles: List[Vehicle],
                      overlap_weight: float = 0.0,
                      strict_overlap: bool = True) -> Dict[int, List[Order]]:

    candidates = []
    for vid in solution:
        for op in [apply_2opt, apply_3opt]:
            new_sol = copy.deepcopy(solution)
            new_sol[vid] = op(new_sol[vid])
            candidates.append(new_sol)

    for op in [tour_swap, tour_merge, split_insert, destroy_and_repair]:
        candidates.append(op(solution))

    args = [(c, vehicles, overlap_weight, strict_overlap) for c in candidates]

    with Pool(processes=min(cpu_count(), len(candidates))) as pool:
        scored = pool.map(evaluate_candidate, args)

    return min(scored, key=lambda x: x[1])[0]



# ---- Simulated Annealing ----

def simulated_annealing(orders: List[Order], vehicles: List[Vehicle], T=1000, alpha=0.95, T_min=0.01, iters=1000):
    current = create_initial_solution(orders, vehicles)
    cost = evaluate_solution(current, vehicles)
    best = current
    best_cost = cost
    T_current = T
    history, temps = [cost], [T_current]
    no_improve_iters = 0  # <-- NEW
    print("Start simulated annealing")

    for _ in range(iters):
        if DEBUG:
            print(f"Iteration {_}, Temp: {T_current:.4f}, Cost: {cost:.2f}, Best: {best_cost:.2f}")
        neighbor = generate_neighbor(current, vehicles, overlap_weight=500.0,strict_overlap=False)
        new_cost = evaluate_solution(neighbor, vehicles)
        delta = new_cost - cost
        if delta < 0 or random.random() < math.exp(-delta / T_current):
            current = neighbor
            cost = new_cost
            if cost < best_cost:
                best = current
                best_cost = cost
                no_improve_iters = 0  # <-- RESET
            else:
                no_improve_iters += 1
        else:
            no_improve_iters += 1

        T_current *= alpha
        history.append(cost)
        temps.append(T_current)

        if T_current < T_min or no_improve_iters >= 1000:  # <-- EARLY EXIT
            break

    plt.figure(figsize=(10, 4))
    plt.subplot(1, 2, 1)
    plt.plot(history)
    plt.title('Cost')
    plt.subplot(1, 2, 2)
    plt.plot(temps)
    plt.title('Temperature')
    plt.show()

    return best


def plot_routes(solution: Dict[int, List[Order]], vehicles: List[Vehicle], show_labels: bool = True):
    plt.figure(figsize=(10, 8))
    cmap = plt.cm.get_cmap('tab10')
    jitter_amt = 0.05
    hulls = []

    for v in vehicles:
        route = [v.start] + [pt for o in solution[v.id] for pt in [o.pickup, o.delivery]] + [v.end]
        lat = [pt.lat + random.uniform(-jitter_amt, jitter_amt) for pt in route]
        lon = [pt.lon + random.uniform(-jitter_amt, jitter_amt) for pt in route]
        color = cmap(v.id % 10)

        plt.plot(lon, lat, marker='o', label=f'Vehicle {v.id}', alpha=0.7, color=color)

        if show_labels:
            for i, pt in enumerate(route):
                plt.text(lon[i], lat[i], str(pt.id), fontsize=7, alpha=0.9)

        hull = compute_convex_hull(route)
        hulls.append((hull, color))

    # Plot convex hulls
    for hull, color in hulls:
        if hasattr(hull, 'exterior'):
            x, y = hull.exterior.xy
            plt.fill(x, y, alpha=0.1, color=color, edgecolor='black')

    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.grid(True)
    plt.legend()
    plt.title('Vehicle Routes with Convex Hulls & Overlap Visualization')
    plt.show()



# ---- Example Run ----

if __name__ == '__main__':
    city_coords = {
        "Indore": (22.7196, 75.8577),
        "Chennai": (13.0827, 80.2707),
        "Hyderabad": (17.3850, 78.4867),
        "Mysore": (12.2958, 76.6394),
        "Bangalore": (12.9716, 77.5946),
        "Asansol": (23.6739, 86.9524),
        "Lucknow": (26.8467, 80.9462),
        "Mumbai": (19.0760, 72.8777),
        "Mangalore": (12.9141, 74.8560),
        "Coimbatore": (11.0168, 76.9558),
    }

    city_locations = {name: Location(i, lat, lon) for i, (name, (lat, lon)) in enumerate(city_coords.items())}
    city_list = list(city_locations.values())

    depot = city_locations["Indore"]
    orders = []

    for i in range(500):
        pickup, delivery = random.sample(city_list, 2)
        orders.append(Order(i, pickup, delivery, time_window=(0, 100), demand=1))

    vehicles = [Vehicle(i, 10, depot, depot) for i in range(5)]

    # Register locations for ID consistency
    location_map = {}
    counter = 0

    def register(loc: Location):
        global counter
        key = (loc.lat, loc.lon)
        if key not in location_map:
            loc.id = counter
            location_map[key] = loc
            counter += 1
        else:
            loc.id = location_map[key].id
        return loc

    for order in orders:
        order.pickup = register(order.pickup)
        order.delivery = register(order.delivery)
    for v in vehicles:
        v.start = register(v.start)
        v.end = register(v.end)

    distance_matrix = build_distance_matrix(list(location_map.values()))

    solution = simulated_annealing(orders, vehicles)
    for vid, ords in solution.items():
        print(f"Vehicle {vid}: {[o.id for o in ords]}")
    plot_routes(solution, vehicles)

    
# if __name__ == '__main__':
#     depot = Location(0, 28.6139, 77.2090)  # Delhi as depot
#     orders = [
#         Order(i,
#               Location(i, random.uniform(8.0, 37.0), random.uniform(68.0, 97.0)),
#               Location(i+100, random.uniform(8.0, 37.0), random.uniform(68.0, 97.0)),
#               (0, 100), 1)
#         for i in range(100)
#     ]
#     vehicles = [Vehicle(i, 5, depot, depot) for i in range(3)]
#     # 
#     location_map = {}
#     counter = 0

#     def register(loc: Location):
#         global counter
#         key = (loc.lat, loc.lon)
#         if key not in location_map:
#             loc.id = counter
#             location_map[key] = loc
#             counter += 1
#         else:
#             loc.id = location_map[key].id
#         return loc

#     for order in orders:
#         order.pickup = register(order.pickup)
#         order.delivery = register(order.delivery)
#     for v in vehicles:
#         v.start = register(v.start)
#         v.end = register(v.end)

#     distance_matrix = build_distance_matrix(list(location_map.values()))
#     # 
#     solution = simulated_annealing(orders, vehicles)
#     for vid, ords in solution.items():
#         print(f"Vehicle {vid}: {[o.id for o in ords]}")
#     plot_routes(solution, vehicles)
