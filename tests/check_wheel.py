from pathlib import Path
from zipfile import ZipFile

wheel, = Path("dist").glob("*.whl")
with ZipFile(wheel) as archive:
    names = archive.namelist()
    assert "pwp_api/apps.py" in names
    assert "pwp_api/migrations/0001_initial.py" in names
    assert not any(n.startswith(("api_fhir_r4/", "tests/")) for n in names)
    metadata, = [n for n in names if n.endswith(".dist-info/METADATA")]
    text = archive.read(metadata).decode()
    assert "Name: openimis-be-pwp" in text
    assert "Version: 0.1.0" in text
    for dependency in ("insuree", "claim", "policy", "policyholder", "fhir.resources"):
        assert not any(dependency in line for line in text.splitlines() if line.startswith("Requires-Dist:"))
print("PWP wheel identity and namespace verified")
