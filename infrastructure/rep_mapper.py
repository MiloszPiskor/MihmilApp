from typing import Optional, Tuple
import unicodedata

POLISH_MAP = str.maketrans({
    'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l',
    'ń': 'n', 'ó': 'o', 'ś': 's', 'ż': 'z', 'ź': 'z',
    'Ą': 'A', 'Ć': 'C', 'Ę': 'E', 'Ł': 'L',
    'Ń': 'N', 'Ó': 'O', 'Ś': 'S', 'Ż': 'Z', 'Ź': 'Z',
})

class ZKMapper:
    def _normalize_name(self, rep_name: str) -> str:
        rep_name = rep_name.lower().strip()
        rep_name = ' '.join(rep_name.split())
        return self._normalize_polish(rep_name)

    def get_rep_data(self, rep_name: str) -> Tuple[str, str, str]:
        normalized_name = self._normalize_name(rep_name)
        reference = self._name_to_reference(normalized_name)
        email = self._name_to_email(normalized_name)
        return normalized_name, reference, email

    def _normalize_polish(self, text: str) -> str:
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        return text.translate(POLISH_MAP)

    def _name_to_reference(self, rep_name: str) -> str:
        parts = rep_name.split()
        if len(parts) < 2:
            raise ValueError("At least first and last name required")
        return parts[0][:3].lower() + parts[-1][:3].lower()

    def _name_to_email(self, rep_name: str) -> str:
        parts = rep_name.split()
        if len(parts) < 2:
            raise ValueError("At least first and last name required")
        return f"{parts[0]}.{parts[-1]}@zeppolska.pl"

