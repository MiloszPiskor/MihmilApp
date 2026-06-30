from typing import Dict, Tuple, Optional
import unicodedata

REPS_DATA: Dict[str, Tuple[str, str]] = {}
""" rep_data = {
    "jan kowalski": ("jankow", "jan.kowalski@zeppolska.pl"),
    "anna Nowak": ("annkow", "anna.nowak@zeppolska.pl"),
} """

POLISH_MAP = str.maketrans({
    'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l',
    'ń': 'n', 'ó': 'o', 'ś': 's', 'ż': 'z', 'ź': 'z',
    'Ą': 'A', 'Ć': 'C', 'Ę': 'E', 'Ł': 'L',
    'Ń': 'N', 'Ó': 'O', 'Ś': 'S', 'Ż': 'Z', 'Ź': 'Z',
})

class ZKMapper:
    def __init__(self, rep_data: Dict[str, Tuple[str, str]] | None = None):
        self.rep_data = rep_data if rep_data is not None else REPS_DATA


    def get_or_create_reference(self, rep_name: str) -> str:
        """Pobierz reference (fallback create)"""
        rep_name = self._normalize_name(rep_name)

        rep_info = self.get_rep_info(str(rep_name))
        if rep_info:
            return rep_info[0]  # Istniejący

        # Nowy → zapisz do REPS_DATA (bez DB!)
        ref = self._name_to_reference(rep_name)
        email = self._name_to_email(rep_name)
        self.rep_data[rep_name] = (ref, email)

        return ref

    def get_reference_and_email(self, rep_name: str) -> tuple[str, str]:
        normalized = self._normalize_name(rep_name)
        reference = self._name_to_reference(normalized)
        email = self._name_to_email(normalized)
        return reference, email

    def _normalize_polish(self, text: str) -> str:
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        return text.translate(POLISH_MAP)

    def _normalize_name(self, rep_name: str) -> str:
        rep_name = rep_name.lower().strip()
        rep_name = ' '.join(rep_name.split())  # normalize spaces
        return self._normalize_polish(rep_name)

    def get_rep_info(self, rep_name: str) -> Optional[Tuple[str, str]]:
        rep_name = self._normalize_name(rep_name)
        rep_info = self.rep_data.get(str(rep_name))
        return rep_info

    def _name_to_reference(self, rep_name: str) -> str:
        # clean_name = self.normalize_polish(rep_name) # REDUNDANT
        parts = rep_name.strip().split()
        if len(parts) < 2:
            raise ValueError("At least first and last name required")
        name_part = parts[0][:3].lower()
        surname_part = parts[-1][:3].lower()
        return name_part + surname_part

    # Version with colliding refs':
    # def _name_to_reference(self, rep_name: str) -> str:
    #     parts = rep_name.split()
    #     base = parts[0][:3] + parts[-1][:3]
    #
    #     ref = base
    #     counter = 1
    #
    #     while any(r == ref for r, _ in self.rep_data.values()):
    #         ref = f"{base}{counter}"
    #         counter += 1
    #
    #     return ref

    def _name_to_email(self, rep_name: str) -> str:
        # clean_name = self.normalize_polish(rep_name) # REDUNDANT
        parts = rep_name.strip().split()
        if len(parts) < 2:
            raise ValueError("At least first and last name required")
        full_name = parts[0]
        full_surname = parts[-1]
        return f"{full_name}.{full_surname}@zeppolska.pl"