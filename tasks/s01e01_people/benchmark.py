import time
import random
from solution import (
    REFERENCE_YEAR,
    TARGET_GENDER,
    TARGET_CITY,
    MIN_AGE,
    MAX_AGE,
    _get_birth_year,
    _get_city,
)

# Generate a large dataset
random.seed(42)
genders = ["M", "F", "m", "f", "", "OTHER"]
cities = [
    "Grudziądz",
    "Warszawa",
    "Kraków",
    "Gdańsk",
    "Poznań",
    "Wrocław",
    " grudziądz ",
    "Warszawa ",
]
jobs = ["kierowca", "lekarz", "nauczyciel", "programista", "kierowca TIR-a"]

people = []
for i in range(500000):
    # birth year can be represented in different ways
    by_type = random.choice(["born", "year_of_birth", "birthDate"])
    year = random.randint(1950, 2020)

    person = {
        "name": f"Name{i}",
        "surname": f"Surname{i}",
        "gender": random.choice(genders),
        "job": random.choice(jobs),
    }

    if by_type == "born":
        person["born"] = str(year)
    elif by_type == "year_of_birth":
        person["year_of_birth"] = str(year)
    else:
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        person["birthDate"] = f"{year}-{month:02d}-{day:02d}"

    city_key = random.choice(["city", "birthPlace"])
    person[city_key] = random.choice(cities)
    people.append(person)

print(f"Generated {len(people)} dummy people.")


# Current implementation as defined in the task description (re-implemented here for comparison, or we just measure solution.py before and after)
def filter_candidates_baseline(people: list[dict]) -> list[dict]:
    result = []
    for person in people:
        try:
            born = _get_birth_year(person)
            age = REFERENCE_YEAR - born
            gender = person.get("gender", "").strip().upper()
            city = _get_city(person)
        except (ValueError, TypeError):
            continue

        if gender == TARGET_GENDER and city == TARGET_CITY and MIN_AGE <= age <= MAX_AGE:
            result.append(person)

    return result


def filter_candidates_optimized(people: list[dict]) -> list[dict]:
    result = []
    for person in people:
        try:
            born = _get_birth_year(person)
            age = REFERENCE_YEAR - born
            if not (MIN_AGE <= age <= MAX_AGE):
                continue

            # Cheaper checks next
            gender = person.get("gender", "")
            if not isinstance(gender, str):
                gender = str(gender)
            gender = gender.strip().upper()
            if gender != TARGET_GENDER:
                continue

            city = _get_city(person)
            if city != TARGET_CITY:
                continue

            result.append(person)
        except (ValueError, TypeError):
            continue

    return result


# Warm up
filter_candidates_baseline(people[:10000])
filter_candidates_optimized(people[:10000])

# Benchmark Baseline
start = time.perf_counter()
res_baseline = filter_candidates_baseline(people)
end = time.perf_counter()
time_baseline = end - start
print(f"Baseline: {time_baseline:.4f} seconds, found {len(res_baseline)} candidates.")

# Benchmark Optimized
start = time.perf_counter()
res_optimized = filter_candidates_optimized(people)
end = time.perf_counter()
time_optimized = end - start
print(f"Optimized: {time_optimized:.4f} seconds, found {len(res_optimized)} candidates.")

# Sanity check
assert len(res_baseline) == len(res_optimized), "Results count mismatch!"
print(f"Speedup: {((time_baseline / time_optimized) - 1) * 100:.2f}% faster!")
