import json
import math
import random
import copy

# Set a random seed for reproducibility
random.seed(42)


# Haversine formula to calculate distance between two lat/lng points
def haversine_distance(lat1, lng1, lat2, lng2):
    R = 6371  # Radius of the Earth in kilometers
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lat2 - lng1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c  # Distance in kilometers


# Calculate the total distance for all vehicle routes
def total_distance(routes, depot_location, weight_distance, weight_time):
    total_dist = 0
    depot_lat, depot_lng = depot_location["lat"], depot_location["lng"]

    # For demonstration, let's assume we also have time calculations.
    total_time = (
        0  # Placeholder for total time (can be replaced with actual time calculation)
    )

    for route in routes:
        prev_lat, prev_lng = depot_lat, depot_lng
        for order in route:
            distance = haversine_distance(
                prev_lat, prev_lng, order["location"]["lat"], order["location"]["lng"]
            )
            total_dist += distance
            total_time += distance / 30  # Assuming an average speed of 30 km/h
            prev_lat, prev_lng = order["location"]["lat"], order["location"]["lng"]
        total_dist += haversine_distance(
            prev_lat, prev_lng, depot_lat, depot_lng
        )  # Return to depot

    # Combine distance and time into a weighted score
    score = (weight_distance * total_dist) + (weight_time * total_time)
    return score, total_dist, total_time


# Generate a random neighbor using different types of moves
def generate_neighbor(routes):
    move_type = random.choice(["swap", "relocate", "2-opt", "multiple_swap"])
    if move_type == "swap":
        return swap_move(routes)
    elif move_type == "relocate":
        return relocate_move(routes)
    elif move_type == "2-opt":
        return two_opt_move(routes)
    elif move_type == "multiple_swap":
        return multiple_swap_move(routes)


# Swap move: Swap two orders between two routes
def swap_move(routes):
    new_routes = copy.deepcopy(routes)
    route1, route2 = random.sample(range(len(new_routes)), 2)
    if len(new_routes[route1]) > 0 and len(new_routes[route2]) > 0:
        i, j = random.randint(0, len(new_routes[route1]) - 1), random.randint(
            0, len(new_routes[route2]) - 1
        )
        new_routes[route1][i], new_routes[route2][j] = (
            new_routes[route2][j],
            new_routes[route1][i],
        )
    return new_routes


# Multiple swaps: Swap multiple pairs of orders between routes
def multiple_swap_move(routes):
    new_routes = copy.deepcopy(routes)
    for _ in range(random.randint(2, 4)):  # Number of swaps can be configured
        route1, route2 = random.sample(range(len(new_routes)), 2)
        if len(new_routes[route1]) > 0 and len(new_routes[route2]) > 0:
            i, j = random.randint(0, len(new_routes[route1]) - 1), random.randint(
                0, len(new_routes[route2]) - 1
            )
            new_routes[route1][i], new_routes[route2][j] = (
                new_routes[route2][j],
                new_routes[route1][i],
            )
    return new_routes


# Relocate move: Move one order from one route to another
def relocate_move(routes):
    new_routes = copy.deepcopy(routes)
    route1, route2 = random.sample(range(len(new_routes)), 2)
    if len(new_routes[route1]) > 0:
        i = random.randint(0, len(new_routes[route1]) - 1)
        order = new_routes[route1].pop(i)
        insert_position = random.randint(0, len(new_routes[route2]))
        new_routes[route2].insert(insert_position, order)
    return new_routes


# 2-opt move: Reverse a segment of a route to reduce distance
def two_opt_move(routes):
    new_routes = copy.deepcopy(routes)
    route = random.choice(new_routes)
    if len(route) > 2:
        i, j = sorted(random.sample(range(len(route)), 2))
        route[i : j + 1] = reversed(route[i : j + 1])
    return new_routes


# Check if a solution is valid (no vehicle exceeds its capacity)
def is_valid(routes, vehicles):
    for i, route in enumerate(routes):
        total_weight = sum(order["weight"] for order in route)
        total_volume = sum(order["volume"] for order in route)
        if (
            total_weight > vehicles[i]["capacity_weight"]
            or total_volume > vehicles[i]["capacity_volume"]
        ):
            return False
    return True


# Simulated Annealing algorithm with multiple moves
def simulated_annealing(
    vehicles,
    orders,
    depot_location,
    initial_temp,
    cooling_rate,
    max_iterations,
    weight_distance,
    weight_time,
):
    # Initial random solution
    routes = [[] for _ in vehicles]
    random.shuffle(orders)
    for i, order in enumerate(orders):
        routes[i % len(vehicles)].append(order)

    current_solution = routes
    current_score, current_distance, current_time = total_distance(
        current_solution, depot_location, weight_distance, weight_time
    )

    best_solution = copy.deepcopy(current_solution)
    best_score = current_score

    temperature = initial_temp

    for iteration in range(max_iterations):
        if temperature <= 0:
            break

        new_solution = generate_neighbor(current_solution)

        if not is_valid(new_solution, vehicles):
            continue

        new_score, new_distance, new_time = total_distance(
            new_solution, depot_location, weight_distance, weight_time
        )

        accepted = False
        # Accept new solution with a probability based on temperature
        if new_score < current_score or random.uniform(0, 1) < math.exp(
            (current_score - new_score) / temperature
        ):
            current_solution = new_solution
            current_score = new_score
            current_distance = new_distance
            current_time = new_time
            accepted = True

        # Update the best solution found
        if current_score < best_score:
            best_solution = copy.deepcopy(current_solution)
            best_score = current_score

        # Logging for debugging
        # print(f"Iteration {iteration + 1}, Temp: {temperature:.2f}, Current Score: {current_score:.2f}, "
        #       f"Best Score: {best_score:.2f}, Current Distance: {current_distance:.2f}, "
        #       f"Current Time: {current_time:.2f}, Accepted: {'Yes' if accepted else 'No'}")

        temperature *= cooling_rate

    return best_solution, best_score


# JSON input for vehicles and orders
data = """
{
    "vehicles": [
        {"id": 1, "capacity_weight": 10000, "capacity_volume": 20000},
        {"id": 2, "capacity_weight": 10000, "capacity_volume": 20000}
    ],
    "orders": [
        {
            "id": 1,
            "weight": 20.73938417905054,
            "volume": 84.87458258706378,
            "location": {
                "lat": 10.447042118520102,
                "lng": 93.64875252870615
            }
        },
        {
            "id": 2,
            "weight": 6.142835085124508,
            "volume": 24.588470656828395,
            "location": {
                "lat": 18.867962678748306,
                "lng": 83.02193878023306
            }
        },
        {
            "id": 3,
            "weight": 8.475416306910688,
            "volume": 56.22456076405092,
            "location": {
                "lat": 9.57660529610817,
                "lng": 73.44336082327405
            }
        },
        {
            "id": 4,
            "weight": 38.164317515512295,
            "volume": 89.59239851137805,
            "location": {
                "lat": 9.458337951922683,
                "lng": 91.74984723605762
            }
        },
        {
            "id": 5,
            "weight": 18.57700001567364,
            "volume": 87.27339403855277,
            "location": {
                "lat": 16.410758044942718,
                "lng": 77.5357838744415
            }
        },
        {
            "id": 6,
            "weight": 38.257114593141644,
            "volume": 47.553828954867,
            "location": {
                "lat": 21.141940558011964,
                "lng": 74.32151267457309
            }
        },
        {
            "id": 7,
            "weight": 38.59982248458614,
            "volume": 63.48793551290433,
            "location": {
                "lat": 10.041052858989511,
                "lng": 89.94011730267134
            }
        },
        {
            "id": 8,
            "weight": 49.72577766996663,
            "volume": 78.24761807241124,
            "location": {
                "lat": 9.327731859708964,
                "lng": 83.918508944758
            }
        },
        {
            "id": 9,
            "weight": 49.89285355817644,
            "volume": 44.48895129256209,
            "location": {
                "lat": 14.988419969420319,
                "lng": 89.19426116435189
            }
        },
        {
            "id": 10,
            "weight": 18.102459133010974,
            "volume": 88.92249994915714,
            "location": {
                "lat": 16.660910261426334,
                "lng": 90.954526746835
            }
        },
        {
            "id": 11,
            "weight": 18.440317614373434,
            "volume": 48.29519310800534,
            "location": {
                "lat": 11.444290422284336,
                "lng": 94.84331552055124
            }
        },
        {
            "id": 12,
            "weight": 17.483332409077285,
            "volume": 90.92786175343146,
            "location": {
                "lat": 18.301891875138452,
                "lng": 74.2861461005201
            }
        },
        {
            "id": 13,
            "weight": 44.50417587559284,
            "volume": 37.27130593918963,
            "location": {
                "lat": 11.91655768678709,
                "lng": 78.15280599041515
            }
        },
        {
            "id": 14,
            "weight": 13.45097426681456,
            "volume": 19.32167994183122,
            "location": {
                "lat": 14.80941808276926,
                "lng": 90.53022637412435
            }
        },
        {
            "id": 15,
            "weight": 6.320539433192794,
            "volume": 66.29320412505244,
            "location": {
                "lat": 9.394851070061524,
                "lng": 84.23871185440808
            }
        },
        {
            "id": 16,
            "weight": 33.73329616294217,
            "volume": 87.58623885093766,
            "location": {
                "lat": 21.314090604020027,
                "lng": 73.44261502293335
            }
        },
        {
            "id": 17,
            "weight": 26.056673210780115,
            "volume": 67.69889770199428,
            "location": {
                "lat": 10.165896962744895,
                "lng": 89.45583550070288
            }
        },
        {
            "id": 18,
            "weight": 40.92738279683582,
            "volume": 30.17767071965818,
            "location": {
                "lat": 18.048656557039095,
                "lng": 72.91174728177106
            }
        },
        {
            "id": 19,
            "weight": 40.25310784066673,
            "volume": 66.69515265994892,
            "location": {
                "lat": 8.393014975446238,
                "lng": 89.38909617973388
            }
        },
        {
            "id": 20,
            "weight": 18.624167994475158,
            "volume": 68.57347889795048,
            "location": {
                "lat": 11.246679694682108,
                "lng": 82.60526864979433
            }
        },
        {
            "id": 21,
            "weight": 34.79621360650755,
            "volume": 70.31845991566527,
            "location": {
                "lat": 10.80128830904747,
                "lng": 76.22270504237508
            }
        },
        {
            "id": 22,
            "weight": 25.238077956267336,
            "volume": 19.11545672815287,
            "location": {
                "lat": 14.460353830125065,
                "lng": 96.85292739343944
            }
        },
        {
            "id": 23,
            "weight": 43.730957106024945,
            "volume": 64.33430409890384,
            "location": {
                "lat": 9.949046684078697,
                "lng": 85.2832396348771
            }
        },
        {
            "id": 24,
            "weight": 33.14472021497984,
            "volume": 94.89274320705313,
            "location": {
                "lat": 17.51738381025215,
                "lng": 70.04797539929102
            }
        },
        {
            "id": 25,
            "weight": 21.407177854652783,
            "volume": 11.864792326397943,
            "location": {
                "lat": 11.599674028986762,
                "lng": 69.49118173862756
            }
        },
        {
            "id": 26,
            "weight": 46.25607192901187,
            "volume": 94.6582003777504,
            "location": {
                "lat": 12.021171729774515,
                "lng": 72.40802995890286
            }
        },
        {
            "id": 27,
            "weight": 17.76692132574544,
            "volume": 85.22346724076907,
            "location": {
                "lat": 14.331042818562567,
                "lng": 77.03617559806811
            }
        },
        {
            "id": 28,
            "weight": 17.922930775550185,
            "volume": 71.69616913919837,
            "location": {
                "lat": 11.051359923189036,
                "lng": 68.97268944895737
            }
        },
        {
            "id": 29,
            "weight": 37.852751100542555,
            "volume": 60.04804687594995,
            "location": {
                "lat": 14.522995078743955,
                "lng": 91.24320550452438
            }
        },
        {
            "id": 30,
            "weight": 8.726645702068712,
            "volume": 26.794804223799144,
            "location": {
                "lat": 18.852737157921048,
                "lng": 75.74082554201874
            }
        },
        {
            "id": 31,
            "weight": 11.591401230566579,
            "volume": 83.31052176046629,
            "location": {
                "lat": 21.728459865663275,
                "lng": 69.11463875086288
            }
        },
        {
            "id": 32,
            "weight": 16.045892098672667,
            "volume": 20.345817764277548,
            "location": {
                "lat": 9.738472079619996,
                "lng": 89.30572949448744
            }
        },
        {
            "id": 33,
            "weight": 19.891195499668477,
            "volume": 33.4666012968832,
            "location": {
                "lat": 18.19214568702179,
                "lng": 70.81101888655654
            }
        },
        {
            "id": 34,
            "weight": 5.71985141570169,
            "volume": 36.73534877740143,
            "location": {
                "lat": 15.765385306083855,
                "lng": 78.28319396977044
            }
        },
        {
            "id": 35,
            "weight": 7.471852658979408,
            "volume": 40.380777692660615,
            "location": {
                "lat": 21.50696625322729,
                "lng": 83.1948976988287
            }
        },
        {
            "id": 36,
            "weight": 30.321830135532437,
            "volume": 68.62765037336712,
            "location": {
                "lat": 16.482925659077452,
                "lng": 89.58173053293305
            }
        },
        {
            "id": 37,
            "weight": 12.154054662752579,
            "volume": 18.32500428639789,
            "location": {
                "lat": 9.468838707372614,
                "lng": 90.60845127662607
            }
        },
        {
            "id": 38,
            "weight": 36.9486923557182,
            "volume": 36.618489773762064,
            "location": {
                "lat": 20.054605262179685,
                "lng": 94.96251304352847
            }
        },
        {
            "id": 39,
            "weight": 49.42517134855786,
            "volume": 45.246565090245824,
            "location": {
                "lat": 14.200335240628249,
                "lng": 92.41932407048995
            }
        },
        {
            "id": 40,
            "weight": 12.506811565505178,
            "volume": 69.92888421249086,
            "location": {
                "lat": 14.620278331243338,
                "lng": 91.77484344292884
            }
        },
        {
            "id": 41,
            "weight": 41.56736584717082,
            "volume": 87.35192952439697,
            "location": {
                "lat": 15.387912411205653,
                "lng": 92.15838031134189
            }
        },
        {
            "id": 42,
            "weight": 31.7145384286308,
            "volume": 86.24786622282241,
            "location": {
                "lat": 13.94465530149839,
                "lng": 88.3916074127467
            }
        },
        {
            "id": 43,
            "weight": 12.546245774524483,
            "volume": 61.822671100629556,
            "location": {
                "lat": 18.314132407770458,
                "lng": 96.54783202251927
            }
        },
        {
            "id": 44,
            "weight": 22.095734813214005,
            "volume": 85.3094056334951,
            "location": {
                "lat": 11.86259621499251,
                "lng": 72.17256296169873
            }
        },
        {
            "id": 45,
            "weight": 34.78582192633645,
            "volume": 75.31127945313403,
            "location": {
                "lat": 16.813603157000394,
                "lng": 91.43201522772364
            }
        },
        {
            "id": 46,
            "weight": 15.011189628301803,
            "volume": 41.698840620480496,
            "location": {
                "lat": 9.749710708908275,
                "lng": 91.40421621437008
            }
        },
        {
            "id": 47,
            "weight": 7.774614226103542,
            "volume": 16.339456708702937,
            "location": {
                "lat": 11.463609852659351,
                "lng": 75.30710415661088
            }
        },
        {
            "id": 48,
            "weight": 44.29759069417374,
            "volume": 53.06943538879376,
            "location": {
                "lat": 11.312039941741716,
                "lng": 91.59115032827609
            }
        },
        {
            "id": 49,
            "weight": 6.115670336418264,
            "volume": 17.018006284924603,
            "location": {
                "lat": 10.487117105718912,
                "lng": 69.61943164738894
            }
        },
        {
            "id": 50,
            "weight": 10.31664144210107,
            "volume": 80.52817834249629,
            "location": {
                "lat": 20.376421387381956,
                "lng": 94.78919005068197
            }
        },
        {
            "id": 51,
            "weight": 36.2173960796671,
            "volume": 51.92742713017032,
            "location": {
                "lat": 12.031411014479037,
                "lng": 72.57659644028976
            }
        },
        {
            "id": 52,
            "weight": 26.492160484401108,
            "volume": 78.34054923297076,
            "location": {
                "lat": 19.39264306855928,
                "lng": 87.46369572072621
            }
        },
        {
            "id": 53,
            "weight": 44.46235433888916,
            "volume": 25.390659393264656,
            "location": {
                "lat": 13.555434174455552,
                "lng": 75.30487621539729
            }
        },
        {
            "id": 54,
            "weight": 21.86236996035619,
            "volume": 34.51375887990133,
            "location": {
                "lat": 19.672193337775344,
                "lng": 81.94656730813873
            }
        },
        {
            "id": 55,
            "weight": 25.278322397152298,
            "volume": 90.7526600142256,
            "location": {
                "lat": 10.050472398877934,
                "lng": 86.54090251226613
            }
        },
        {
            "id": 56,
            "weight": 38.587571806554124,
            "volume": 67.95529690330648,
            "location": {
                "lat": 21.310756113123844,
                "lng": 87.84623336294456
            }
        },
        {
            "id": 57,
            "weight": 45.791338597678376,
            "volume": 18.36675107609279,
            "location": {
                "lat": 13.421811299062224,
                "lng": 71.58599537295233
            }
        },
        {
            "id": 58,
            "weight": 43.85043067327145,
            "volume": 64.33824038932649,
            "location": {
                "lat": 18.47319100130612,
                "lng": 93.81452093596852
            }
        },
        {
            "id": 59,
            "weight": 6.164864881601823,
            "volume": 54.76289465927066,
            "location": {
                "lat": 8.655004891607568,
                "lng": 85.06269351672778
            }
        },
        {
            "id": 60,
            "weight": 21.854707337363212,
            "volume": 64.42695365030565,
            "location": {
                "lat": 8.137293085669008,
                "lng": 73.82267947655826
            }
        },
        {
            "id": 61,
            "weight": 7.69309757557027,
            "volume": 83.34097285968046,
            "location": {
                "lat": 20.050365761381762,
                "lng": 87.41017978626871
            }
        },
        {
            "id": 62,
            "weight": 20.630512465757466,
            "volume": 73.12211651095382,
            "location": {
                "lat": 10.015083303269321,
                "lng": 86.27529826767872
            }
        },
        {
            "id": 63,
            "weight": 49.07393613413487,
            "volume": 26.55439858460085,
            "location": {
                "lat": 21.218081512647746,
                "lng": 73.55205341986075
            }
        },
        {
            "id": 64,
            "weight": 30.35558973577522,
            "volume": 41.9111821409728,
            "location": {
                "lat": 15.4431391372935,
                "lng": 84.96508137013389
            }
        },
        {
            "id": 65,
            "weight": 49.148146092756015,
            "volume": 51.17734944664295,
            "location": {
                "lat": 20.466450948097865,
                "lng": 90.37663755852734
            }
        },
        {
            "id": 66,
            "weight": 34.13626552844701,
            "volume": 16.48926150187361,
            "location": {
                "lat": 18.575649887579313,
                "lng": 86.48506194204342
            }
        },
        {
            "id": 67,
            "weight": 46.92964503015372,
            "volume": 99.97990273417113,
            "location": {
                "lat": 20.181564534184012,
                "lng": 73.16408184616675
            }
        },
        {
            "id": 68,
            "weight": 35.09252091718219,
            "volume": 49.76610189500036,
            "location": {
                "lat": 15.15776863684027,
                "lng": 76.50154650376268
            }
        },
        {
            "id": 69,
            "weight": 12.835308017211123,
            "volume": 98.23843637145632,
            "location": {
                "lat": 20.714885076380124,
                "lng": 69.5773109498052
            }
        },
        {
            "id": 70,
            "weight": 18.46352603120105,
            "volume": 78.90202777085193,
            "location": {
                "lat": 15.50407828801741,
                "lng": 73.19874287382429
            }
        },
        {
            "id": 71,
            "weight": 14.935570989728587,
            "volume": 46.435039832723916,
            "location": {
                "lat": 19.9472738453722,
                "lng": 79.86951365542537
            }
        },
        {
            "id": 72,
            "weight": 33.99362194956747,
            "volume": 76.88706152236679,
            "location": {
                "lat": 15.302854934062049,
                "lng": 73.67755944096317
            }
        },
        {
            "id": 73,
            "weight": 32.94367340963035,
            "volume": 30.50208602140743,
            "location": {
                "lat": 13.038553265403252,
                "lng": 96.31365479217347
            }
        },
        {
            "id": 74,
            "weight": 14.091828315766762,
            "volume": 38.23990476543296,
            "location": {
                "lat": 16.408339348712055,
                "lng": 71.18587938990821
            }
        },
        {
            "id": 75,
            "weight": 23.498612281204437,
            "volume": 64.50768259543241,
            "location": {
                "lat": 16.699356350917732,
                "lng": 84.10151357888313
            }
        },
        {
            "id": 76,
            "weight": 11.125495939512021,
            "volume": 65.7154990598026,
            "location": {
                "lat": 17.812570276971062,
                "lng": 93.58156873284031
            }
        },
        {
            "id": 77,
            "weight": 48.52141076650716,
            "volume": 96.6720768036044,
            "location": {
                "lat": 19.46355316244928,
                "lng": 87.39522464287434
            }
        },
        {
            "id": 78,
            "weight": 30.15831152578766,
            "volume": 73.64054894647953,
            "location": {
                "lat": 15.351559835056658,
                "lng": 90.3202323599809
            }
        },
        {
            "id": 79,
            "weight": 24.950666368598913,
            "volume": 87.55624207877733,
            "location": {
                "lat": 13.567238350894762,
                "lng": 76.89773938273044
            }
        },
        {
            "id": 80,
            "weight": 32.005326298763435,
            "volume": 67.82882151330922,
            "location": {
                "lat": 10.547735569446576,
                "lng": 68.2165995645344
            }
        },
        {
            "id": 81,
            "weight": 21.069315022663147,
            "volume": 42.825697266043875,
            "location": {
                "lat": 19.109625508798572,
                "lng": 68.78976007107218
            }
        },
        {
            "id": 82,
            "weight": 34.32710922417785,
            "volume": 93.77414994453493,
            "location": {
                "lat": 18.4595162501901,
                "lng": 86.74963041645404
            }
        },
        {
            "id": 83,
            "weight": 22.987082056920496,
            "volume": 77.94042559722124,
            "location": {
                "lat": 12.51234917848998,
                "lng": 73.54464280265292
            }
        },
        {
            "id": 84,
            "weight": 21.498334238673387,
            "volume": 38.50005954996208,
            "location": {
                "lat": 12.875495667435931,
                "lng": 87.65779120910213
            }
        },
        {
            "id": 85,
            "weight": 41.42172312498415,
            "volume": 70.68022618015502,
            "location": {
                "lat": 9.894478288456975,
                "lng": 70.45808581578702
            }
        },
        {
            "id": 86,
            "weight": 34.29123721692863,
            "volume": 72.16858739875548,
            "location": {
                "lat": 21.131215092122574,
                "lng": 79.89279242090788
            }
        },
        {
            "id": 87,
            "weight": 18.290083094479368,
            "volume": 25.244693930812797,
            "location": {
                "lat": 9.959744649005005,
                "lng": 81.0638689236266
            }
        },
        {
            "id": 88,
            "weight": 32.549016833524476,
            "volume": 24.455117202030333,
            "location": {
                "lat": 18.451652182666713,
                "lng": 80.76812021082078
            }
        },
        {
            "id": 89,
            "weight": 23.32608268355414,
            "volume": 48.48124160445959,
            "location": {
                "lat": 17.23965898857198,
                "lng": 71.35349873420675
            }
        },
        {
            "id": 90,
            "weight": 10.918635815739858,
            "volume": 17.350054414367072,
            "location": {
                "lat": 21.12304435583316,
                "lng": 92.97870892893424
            }
        },
        {
            "id": 91,
            "weight": 47.84152037033997,
            "volume": 53.99501445034519,
            "location": {
                "lat": 15.552219047678971,
                "lng": 96.67331015679054
            }
        },
        {
            "id": 92,
            "weight": 41.55690377334896,
            "volume": 29.309239541671957,
            "location": {
                "lat": 14.900770962729759,
                "lng": 90.93015260925577
            }
        },
        {
            "id": 93,
            "weight": 21.14849211721862,
            "volume": 63.436015090004624,
            "location": {
                "lat": 8.830627470839536,
                "lng": 76.04864991272902
            }
        },
        {
            "id": 94,
            "weight": 24.855481589448203,
            "volume": 73.21520024593454,
            "location": {
                "lat": 13.898051335511425,
                "lng": 87.64875698797238
            }
        },
        {
            "id": 95,
            "weight": 15.976617473642365,
            "volume": 54.59335391111676,
            "location": {
                "lat": 8.07917256176613,
                "lng": 93.86154149197293
            }
        },
        {
            "id": 96,
            "weight": 17.098538528439587,
            "volume": 68.18398285710654,
            "location": {
                "lat": 16.030202499214848,
                "lng": 83.84883143693307
            }
        },
        {
            "id": 97,
            "weight": 15.929599668420675,
            "volume": 68.12537922469,
            "location": {
                "lat": 9.771284883036136,
                "lng": 94.78041579913824
            }
        },
        {
            "id": 98,
            "weight": 5.513442441891588,
            "volume": 69.43670491850555,
            "location": {
                "lat": 14.498977591771322,
                "lng": 69.59154692784719
            }
        },
        {
            "id": 99,
            "weight": 47.03460207679615,
            "volume": 38.66733617790114,
            "location": {
                "lat": 11.51090513360148,
                "lng": 69.36794505471678
            }
        },
        {
            "id": 100,
            "weight": 11.465234251902428,
            "volume": 26.51909575610689,
            "location": {
                "lat": 11.133001594894088,
                "lng": 92.27721592918265
            }
        }
    ],
     "depot_location": {"lat": 12.9716, "lng": 77.5946}
}
"""

# Load the data
data = json.loads(data)
vehicles = data["vehicles"]
orders = data["orders"]
depot_location = data["depot_location"]

# Parameters for simulated annealing
initial_temp = 10000
cooling_rate = 0.995
max_iterations = 10000
weight_distance = 0.5  # Weight for distance constraint
weight_time = 0.5  # Weight for time constraint

best_solution, best_score = simulated_annealing(
    vehicles,
    orders,
    depot_location,
    initial_temp,
    cooling_rate,
    max_iterations,
    weight_distance,
    weight_time,
)

print("Best solution found:", best_solution)
print("Best score:", best_score)
