"""
SCOPE: Plik zawiera globalne prompty dla LLM, wykorzystywane w wielu ZADANIACH jednocześnie.

CEL: Likwidacja zbędnych duplikacji instrukcji pomiędzy zadaniami, większa konsystencja odpowiedzi modelu, unikanie powtórzeń logiki promptowania.

OUT OF SCOPE: W pliku NIE zamieszczamy promptów, które:
  - wychodzą swoim zasięgiem poza folder aid4u/tasks/
  - są używane tylko w jednym zadaniu

WARUNKI UMIESZCZENIA W TYM PLIKU: Definiowane tu prompty muszą być używane w więcej niż jednym zadaniu z folderu /aid4u/tasks/
"""
