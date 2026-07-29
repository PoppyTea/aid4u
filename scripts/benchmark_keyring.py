import timeit

KEYRING_KEYS_LIST = [
    "APIKEY",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "GEMINI_API_KEY_PREMIUM",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    "LOGFIRE_TOKEN",
    "VPS_HOST",
]

KEYRING_KEYS_SET = set(KEYRING_KEYS_LIST)

# We will test lookups of present and missing keys
test_keys = [
    "APIKEY",  # present, start of list
    "VPS_HOST",  # present, end of list
    "LOGFIRE_TOKEN",  # present, middle
    "SOME_MISSING_KEY_1",  # missing
    "SOME_MISSING_KEY_2",  # missing
]


def run_benchmark():
    iterations = 1_000_000

    print("--- KEYRING_KEYS List vs Set Benchmark ---")
    print(f"Iterations: {iterations:,}\n")

    # List benchmark
    list_time = timeit.timeit(
        stmt="for k in test_keys: _ = k not in KEYRING_KEYS_LIST",
        globals=globals(),
        number=iterations,
    )
    print(f"List membership check: {list_time:.4f} seconds")

    # Set benchmark
    set_time = timeit.timeit(
        stmt="for k in test_keys: _ = k not in KEYRING_KEYS_SET",
        globals=globals(),
        number=iterations,
    )
    print(f"Set membership check:  {set_time:.4f} seconds")

    speedup = (list_time - set_time) / list_time * 100
    ratio = list_time / set_time if set_time > 0 else float("inf")
    print(f"\nSpeedup: {speedup:.2f}% (Set is {ratio:.2f}x faster)")


if __name__ == "__main__":
    run_benchmark()
