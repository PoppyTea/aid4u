"""
Prompty dla zadania S01E02 - Findhim.

Trzymane osobno od logiki żeby łatwo iterować nad treścią
bez zagłębiania się w kod Pythona.

UWAGA!!!
wersja TYMCZASOWA z użyciem dataclass. Docelowo należy zaimplementować użycie ManagedPrompt.
Więcej na ten temat: (https://pydantic.dev/docs/ai/harness/managed-prompt/)[dokumentacja - ManagedPrompt]

"""
from dataclasses import dataclass


@dataclass
class GeoCity:
    granular_lvl = "city"
    good_examples = """\t\'Warszawa\'
        \t\'Piotrków Mazowiecki\'
        \t\'Kraków\'
        """
    bad_examples = """\t\'Europe\'
        \t\'Central Park\'
        \t\'Polska\'
        """
    template = f"""Name of geografic location which can be used to identify the location. Name shoud corelate with granularity level: {granular_lvl}
        GOOD EXAMPLES:
            {good_examples}
        BAD EXAMPLES:
            {bad_examples}
        """
    def prompt(self)->str:
        return self.template

# def geo_city_template() -> GeoPointCity:
#     return GeoPointCity(f"""
#     Name of geographic location which can be used to identify the location. Name shoud corelate with granularity level: {GeoPointCity.GRANULAR_LVL}
#     GOOD EXAMPLES:
#         {GeoPointCity.GOOD_EXAMPLES_CITY}
#     BAD EXAMPLES:
#         {GeoPointCity.BAD_EXAMPLES_CITY}
#     """)


SYSTEM_AGENT_FINDHIM = """\
Szukasz podejrzanego widzianego najbliżej jednej z elektrowni atomowych.

Dla KAŻDEJ osoby z podanej listy podejrzanych wywołaj find_nearest_plant_for_suspect,
żeby sprawdzić jej najmniejszy dystans do dowolnej elektrowni.

Po sprawdzeniu WSZYSTKICH osób, wywołaj get_access_level TYLKO dla tej z najmniejszym
dystansem ze wszystkich sprawdzonych.

Na koniec odpowiedz WYŁĄCZNIE obiektem JSON, bez dodatkowego tekstu ani markdown:
{"name": "...", "surname": "...", "accessLevel": <int>, "powerPlant": "<kod elektrowni>"}
"""

USER_AGENT_FINDHIM = """\
Lista podejrzanych do sprawdzenia:
{suspects_json}
"""
