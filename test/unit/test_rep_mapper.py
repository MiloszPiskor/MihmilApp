import pytest
from infrastructure import rep_mapper

def test_normalize_name_lowercase_and_strips():
    mapper = rep_mapper.ZKMapper()
    assert mapper._normalize_name("  JAN KOWALSKI  ") == "jan kowalski"
    assert mapper._normalize_name("Anna Nowak") == "anna nowak"

def test_normalize_name_removes_polish_diacritics():
    mapper = rep_mapper.ZKMapper()
    assert mapper._normalize_name("Tomasz Łukiewicz") == "tomasz lukiewicz"
    assert mapper._normalize_name("Marcin Więcek") == "marcin wiecek"
    assert mapper._normalize_name("Óczko") == "oczko"

def test_get_rep_info_returns_normalized_name_reference_and_email():
    mapper = rep_mapper.ZKMapper()

    name, reference, email = mapper.get_rep_data("JAN KOWALSKI")

    assert name == "jan kowalski"
    assert reference == "jankow"
    assert email == "jan.kowalski@zeppolska.pl"

def test_get_rep_data_handles_polish_characters():
    mapper = rep_mapper.ZKMapper()

    name, reference, email = mapper.get_rep_data("Piotr Zieliński")

    assert name == "piotr zielinski"
    assert reference == "piozie"
    assert email == "piotr.zielinski@zeppolska.pl"

def test_name_to_reference_format_is_three_plus_three():
    mapper = rep_mapper.ZKMapper()
    assert mapper._name_to_reference("Anna Nowak") == "annnow"
    assert mapper._name_to_reference("Jan Kowalski") == "jankow"
    assert mapper._name_to_reference("John Doe Smith") == "johsmi"

def test_name_to_reference_raises_when_only_one_name():
    mapper = rep_mapper.ZKMapper()
    with pytest.raises(ValueError, match="At least first and last name required"):
        mapper._name_to_reference("Tylko")

def test_name_to_email_format_is_first_dot_last_at_zeppolska():
    mapper = rep_mapper.ZKMapper()
    name_a, name_b = mapper._normalize_name("Anna Nowak"), mapper._normalize_name("John Doe Smith")
    assert mapper._name_to_email(name_a) == "anna.nowak@zeppolska.pl"
    assert mapper._name_to_email(name_b) == "john.smith@zeppolska.pl"

def test_name_to_email_raises_when_only_one_name():
    mapper = rep_mapper.ZKMapper()
    with pytest.raises(ValueError, match="At least first and last name required"):
        mapper._name_to_email("Tylko")

