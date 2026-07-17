from solution import haversine_distance

# Współrzędne:
#   latitude > 0 =>  North (N)
#   latitude < 0 => South (S)
#   longitude > 0 => East (E)
#   longitude < 0 => West (W)



def test_haversine_distance_same_location()->float | None:
    """ Test the haversine distance calculation. Edge case: same location """
    power_plant: tuple[float, float] = (21.00, 52.00)
    city: tuple[float, float] = (21.00, 52.00)
    distance = haversine_distance(power_plant, city)
    assert distance == 0.0
    return distance

def test_haversine_distance_calculation()->float | None:
    """ Test the haversine distance calculation. Standard case: Warszawa -> Kraków, ok. 251 km. """
    warszawa: tuple[float, float] = (21.0122, 52.2297)
    krakow: tuple[float, float] = (19.9450, 50.0647)
    distance = haversine_distance(warszawa, krakow)
    # Dystans podawany w km, tolerancja ±1% (linia prosta po powierzchni Ziemi)
    assert distance is not None
    assert 245 <= distance <= 257
    return distance

def test_haversine_distance_gt_zero()->float | None:
    """ Test if the haversine distance calculation returns a value greater than zero. """
    power_plant =(21.00, 52.00)
    city = (52.00, 21.00)
    distance = haversine_distance(power_plant, city)
    assert distance is not None
    assert distance > 0
    return distance
