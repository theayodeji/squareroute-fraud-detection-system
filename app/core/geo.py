import math

def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate the great circle distance in meters between two points 
    on the earth (specified in decimal degrees).
    """
    if None in (lat1, lng1, lat2, lng2):
        return 0.0

    # Convert decimal degrees to radians
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])

    # Haversine formula
    dlon = lng2 - lng1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371000 # Radius of earth in meters
    return c * r

def calculate_speed_kmh(distance_meters: float, time_seconds: float) -> float:
    """
    Calculate speed in km/h given distance in meters and time in seconds.
    """
    if time_seconds <= 0:
        return 0.0
    
    speed_mps = distance_meters / time_seconds
    speed_kmh = speed_mps * 3.6
    return speed_kmh
