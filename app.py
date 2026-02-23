import csv
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from linkedin_api import Linkedin

load_dotenv()

app = Flask(__name__)

DEFAULT_PROFILE_ID = os.getenv("DEFAULT_PROFILE_ID", "williamhgates")
CSV_FILE = "current_skills.csv"


def fetch_skills(profile_id: str) -> list[dict]:
    """Fetch skills and endorsement counts from a LinkedIn profile."""
    username = os.environ["LINKEDIN_USERNAME"]
    password = os.environ["LINKEDIN_PASSWORD"]

    api = Linkedin(username, password)
    profile = api.get_profile_skills(profile_id)

    skills = []
    for item in profile:
        skills.append(
            {
                "name": item.get("name", ""),
                "endorsement_count": item.get("endorsementCount", 0),
            }
        )
    return skills


def save_to_csv(skills: list[dict], filepath: str = CSV_FILE) -> None:
    """Save skills list to a CSV file."""
    with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["name", "endorsement_count"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(skills)


@app.route("/skills", methods=["GET"])
def get_skills():
    """Return skills and endorsements for a LinkedIn profile.

    Query parameters:
        profile_id (str): LinkedIn public profile ID (default: DEFAULT_PROFILE_ID).
    """
    profile_id = request.args.get("profile_id", DEFAULT_PROFILE_ID)

    if not os.getenv("LINKEDIN_USERNAME") or not os.getenv("LINKEDIN_PASSWORD"):
        return jsonify({"error": "LinkedIn credentials not configured"}), 500

    try:
        skills = fetch_skills(profile_id)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    save_to_csv(skills)

    return jsonify({"profile_id": profile_id, "skills": skills})


if __name__ == "__main__":
    app.run(debug=False)
