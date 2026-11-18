"""A patient can have several specialties; doctors see the patient through any of them."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from medicg.doctor_scope import scope, patient_specialties, filter_data  # noqa: E402


def main():
    data = {
        "medicos": [{"id": 1, "nombre": "Dra. Pediatra", "esp": "Pediatría"}, {"id": 2, "nombre": "Dr. Neuro", "esp": "Neurología"},
                    {"id": 3, "nombre": "Psicóloga", "esp": "Psicologia"}],
        "pacientes": [{"id": 1, "nombres": "Ana", "esp": "Pediatría", "esps": ["Pediatría", "Terapia de Lenguaje", "Psicologia"]},
                      {"id": 2, "nombres": "Luis", "esp": "Neurología"},
                      {"id": 3, "nombres": "Old", "esp": "Pediatría", "esps": None}],
        "citas": [], "notas": {"1": [{"id": 9}], "2": [{"id": 8}]},
    }
    assert patient_specialties(data["pacientes"][0]) == ["Pediatría", "Terapia de Lenguaje", "Psicologia"]
    assert patient_specialties(data["pacientes"][2]) == ["Pediatría"]  # records saved before this change
    assert scope(data, {"medicoId": 1})[0] == {"1", "3"}
    assert scope(data, {"medicoId": 3})[0] == {"1"}, "additional specialty gives access"
    assert scope(data, {"medicoId": 2})[0] == {"2"}
    visible = filter_data(data, {"medicoId": 3})
    assert [p["id"] for p in visible["pacientes"]] == [1] and list(visible["notas"]) == ["1"]
    print("PASS patient specialties: several per patient, doctors see patients of any of their specialties, old records still work")


if __name__ == "__main__":
    main()
