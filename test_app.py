import csv
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

import app as skillaby_app
from app import DEFAULT_PROFILE_ID, save_to_csv


@pytest.fixture
def client():
    skillaby_app.app.config["TESTING"] = True
    with skillaby_app.app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# save_to_csv
# ---------------------------------------------------------------------------

def test_save_to_csv_creates_file():
    skills = [{"name": "Python", "endorsement_count": 42}]
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        path = tmp.name
    try:
        save_to_csv(skills, path)
        assert os.path.exists(path)
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert rows == [{"name": "Python", "endorsement_count": "42"}]
    finally:
        os.unlink(path)


def test_save_to_csv_header():
    skills = []
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as tmp:
        path = tmp.name
    try:
        save_to_csv(skills, path)
        with open(path, newline="", encoding="utf-8") as f:
            header = f.readline().strip()
        assert header == "name,endorsement_count"
    finally:
        os.unlink(path)


def test_save_to_csv_multiple_rows():
    skills = [
        {"name": "Python", "endorsement_count": 10},
        {"name": "Java", "endorsement_count": 5},
    ]
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        path = tmp.name
    try:
        save_to_csv(skills, path)
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 2
        assert rows[0]["name"] == "Python"
        assert rows[1]["name"] == "Java"
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# /skills endpoint
# ---------------------------------------------------------------------------

def test_skills_missing_credentials(client):
    with patch.dict(os.environ, {}, clear=True):
        # Ensure credentials are absent
        os.environ.pop("LINKEDIN_USERNAME", None)
        os.environ.pop("LINKEDIN_PASSWORD", None)
        response = client.get("/skills")
    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data


def test_skills_default_profile(client):
    mock_skills = [
        {"name": "Leadership", "endorsementCount": 99},
        {"name": "Strategy", "endorsementCount": 50},
    ]
    with patch.dict(
        os.environ,
        {"LINKEDIN_USERNAME": "user@example.com", "LINKEDIN_PASSWORD": "secret"},
    ):
        with patch("app.Linkedin") as MockLinkedin:
            instance = MockLinkedin.return_value
            instance.get_profile_skills.return_value = mock_skills

            response = client.get("/skills")

    assert response.status_code == 200
    data = response.get_json()
    assert data["profile_id"] == DEFAULT_PROFILE_ID
    assert len(data["skills"]) == 2
    assert data["skills"][0]["name"] == "Leadership"
    assert data["skills"][0]["endorsement_count"] == 99


def test_skills_custom_profile(client):
    mock_skills = [{"name": "Python", "endorsementCount": 7}]
    with patch.dict(
        os.environ,
        {"LINKEDIN_USERNAME": "user@example.com", "LINKEDIN_PASSWORD": "secret"},
    ):
        with patch("app.Linkedin") as MockLinkedin:
            instance = MockLinkedin.return_value
            instance.get_profile_skills.return_value = mock_skills

            response = client.get("/skills?profile_id=satyanadella")

    assert response.status_code == 200
    data = response.get_json()
    assert data["profile_id"] == "satyanadella"
    instance.get_profile_skills.assert_called_once_with("satyanadella")


def test_skills_saves_csv(client, tmp_path):
    mock_skills = [{"name": "Go", "endorsementCount": 3}]
    csv_path = str(tmp_path / "current_skills.csv")

    with patch.dict(
        os.environ,
        {"LINKEDIN_USERNAME": "user@example.com", "LINKEDIN_PASSWORD": "secret"},
    ):
        with patch("app.Linkedin") as MockLinkedin:
            instance = MockLinkedin.return_value
            instance.get_profile_skills.return_value = mock_skills
            with patch("app.CSV_FILE", csv_path):
                with patch("app.save_to_csv") as mock_save:
                    response = client.get("/skills")
                    mock_save.assert_called_once()

    assert response.status_code == 200


def test_skills_linkedin_error(client):
    with patch.dict(
        os.environ,
        {"LINKEDIN_USERNAME": "user@example.com", "LINKEDIN_PASSWORD": "secret"},
    ):
        with patch("app.Linkedin") as MockLinkedin:
            MockLinkedin.side_effect = Exception("auth failed")
            response = client.get("/skills")

    assert response.status_code == 500
    data = response.get_json()
    assert "auth failed" in data["error"]
