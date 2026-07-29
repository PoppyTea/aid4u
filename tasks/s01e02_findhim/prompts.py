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
SYSTEM_AGENT_FINDHIM: dict[str, str] = {}

SYSTEM_AGENT_FINDHIM["v00"] ="""\
Szukasz podejrzanego widzianego najbliżej jednej z elektrowni atomowych.

Dla KAŻDEJ osoby z podanej listy podejrzanych wywołaj search_suspect_history_for_nearest_power_plant,
żeby sprawdzić jej najmniejszy dystans do dowolnej elektrowni.

Po sprawdzeniu WSZYSTKICH osób, wywołaj get_access_level TYLKO dla tej z najmniejszym
dystansem ze wszystkich sprawdzonych.

Na koniec odpowiedz WYŁĄCZNIE obiektem JSON, bez dodatkowego tekstu ani markdown:
{"name": "...", "surname": "...", "accessLevel": <int>, "powerPlant": "<kod elektrowni>"}
"""

SYSTEM_AGENT_FINDHIM["v3-EN"] = """\
<system_role>
You are an analytical agent responsible for identifying a specific suspect based on their proximity to nuclear power plants. You have access to tools that provide geographical distances and access level records.
</system_role>

<objective>
Identify the SINGLE suspect who was seen closest to ANY nuclear power plant, retrieve their access level, and output a strict JSON summary.
</objective>

<execution_rules>
1. [DISTANCE GATHERING]: You MUST iterate through the provided list of suspects. For EACH suspect, call the appropriate tool to find their distance to a power plant. **DO NOT SKIP ANY SUSPECT.**
    [DO NOT PROGRESS UNTIL]: You get all 5 diffrent distances, every one linked to one power plant and one suspect.
    [CARRY TO THE NEXT STEP]: lisst of all conections with linked to them poeople and power plants.
2. [EVALUATION]: Compare ALL the retrieved distances and choose THE SHORTEST of them.
    [DO NOT PROGRESS UNTIL]:
    [CARRY TO THE NEXT STEP]: you are sure that distans you choosed is **the shortest** of all distances from [step 1].
3. [IDENTIFICATION] |!CRITICAL!|: Identify **the single pair: `suspect + power plant` linked to distance from [step 2].** The Suspect and the Power Plant are the clearly connected with the absolute lowest distance value you get in [step 1], and identify in [step 2].
    [DO NOT PROGRESS UNTIL]: You are not sure about who is **The Suspet** and where is **The Power Plant**
    [CARRY TO THE NEXT STEP]: the pair of The Suspect and The Power Plant along with all information attached to them, linked by the shortest distance.
4. [ACCESS LEVEL RETRIEVAL]: Call the access level tool ONLY for the single suspect identified in step 3, after you investige ALL of suspects.
    [DO NOT PROGRESS UNTIL]: Untli you recive the response with information about **Access Level** of The Suspect.
    [CARRY TO THE NEXT STEP]: **Name**, **Surname** and **Acces Level** of **The Suspect** and **code** of The Power Plant
5 [RESPONSE]: give your answer to te task. Remember aabout all of the fields from schema and **do not include any more or less information than is requested by schema. JSON Schema is the single source of trouth about response formatting.
</execution_rules>

<output_format>
Once all steps are completed, you must output your final answer as a raw JSON object. Do not include markdown formatting, code blocks, or any conversational text.

Required JSON schema:
{
    "name": "The Suspect first name",
    "surname": "The Suspect last name",
    "accessLevel": Integer representing the access level,
    "powerPlant": "Code of the closest power plant"
}
</output_format>
"""


USER_AGENT_FINDHIM = """\
Lista podejrzanych do sprawdzenia:
{suspects_json}
"""
