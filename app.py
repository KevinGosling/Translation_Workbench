import os
import json
from flask import Flask, render_template, jsonify, request
from lib import tmx_processing

app = Flask(__name__)
PROJECTS_DIR = os.path.join(os.getcwd(), "Projects")


def list_projects():
    if not os.path.exists(PROJECTS_DIR):
        os.makedirs(PROJECTS_DIR)
    return [
        d for d in os.listdir(PROJECTS_DIR)
        if os.path.isdir(os.path.join(PROJECTS_DIR, d))
    ]


@app.route("/")
def index():
    projects = list_projects()
    return render_template("index.html", projects=projects)


@app.route("/workbench/<project_name>")
def workbench(project_name):
    projects = list_projects()
    if project_name not in projects:
        return jsonify({"error": "Project not found"}), 404
    return render_template("workbench.html", project=project_name, projects=projects)


# -------------------------------------------------
# NAOB overrides helpers (NEW, AGREED)
# -------------------------------------------------
def get_naob_overrides(project_path):
    cache_dir = os.path.join(project_path, "cache")
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    overrides_file = os.path.join(cache_dir, "naob_overrides.json")
    if not os.path.exists(overrides_file):
        return {}

    try:
        with open(overrides_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_naob_override(project_path, lemma_key, url):
    cache_dir = os.path.join(project_path, "cache")
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    overrides_file = os.path.join(cache_dir, "naob_overrides.json")

    overrides = {}
    if os.path.exists(overrides_file):
        try:
            with open(overrides_file, "r", encoding="utf-8") as f:
                overrides = json.load(f)
        except Exception:
            overrides = {}

    # ✅ ONLY CHANGE: normalize URL to absolute https://
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    overrides[lemma_key] = url

    with open(overrides_file, "w", encoding="utf-8") as f:
        json.dump(overrides, f, ensure_ascii=False, indent=2)


# -------------------------------------------------
# Meanings helpers (NEW, AGREED)
# -------------------------------------------------
def get_meanings(project_path):
    cache_dir = os.path.join(project_path, "cache")
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    meanings_file = os.path.join(cache_dir, "meanings.json")
    if not os.path.exists(meanings_file):
        return {}

    try:
        with open(meanings_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_meaning(project_path, lemma_key, meaning):
    cache_dir = os.path.join(project_path, "cache")
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    meanings_file = os.path.join(cache_dir, "meanings.json")

    meanings = {}
    if os.path.exists(meanings_file):
        try:
            with open(meanings_file, "r", encoding="utf-8") as f:
                meanings = json.load(f)
        except Exception:
            meanings = {}

    meanings[lemma_key] = meaning

    with open(meanings_file, "w", encoding="utf-8") as f:
        json.dump(meanings, f, ensure_ascii=False, indent=2)


@app.route("/project/<project_name>")
def load_project(project_name):
    project_path = os.path.join(PROJECTS_DIR, project_name)
    if not os.path.exists(project_path):
        return jsonify({"error": "Project not found"}), 404

    segments = tmx_processing.load_segments(project_path)
    lemmas = tmx_processing.extract_lemmas(segments, project_path=project_path)
    naob_overrides = get_naob_overrides(project_path)
    meanings = get_meanings(project_path)

    seg_list = []
    for s in segments:
        tokens = []
        doc = tmx_processing.nlp(s["source"])
        for sent in doc.sentences:
            for token in sent.words:
                tokens.append({
                    "text": token.text,
                    "lemma": token.lemma.lower(),
                    "pos": token.upos
                })
        seg_list.append({
            "id": s["id"],
            "source": s["source"],
            "target": s["target"],
            "tokens": tokens
        })

    lemma_dict = {}
    for key, data in lemmas.items():
        lemma_dict[key] = {
            "lemma": key.split("|")[0],
            "pos": key.split("|")[1],
            "wordforms": list(data["wordforms"]),
            "occurrences": [
                {
                    "source": occ["source_segment"],
                    "target": next(
                        (s["target"] for s in segments if s["id"] == occ["segment_id"]),
                        ""
                    ),
                    "lemma_wordforms": list(data["wordforms"])
                } for occ in data["occurrences"]
            ]
        }

    return jsonify({
        "segments": seg_list,
        "lemmas": lemma_dict,
        "naob_overrides": naob_overrides,
        "meanings": meanings
    })


@app.route("/project/<project_name>/set_naob_override", methods=["POST"])
def set_naob_override(project_name):
    project_path = os.path.join(PROJECTS_DIR, project_name)
    if not os.path.exists(project_path):
        return jsonify({"error": "Project not found"}), 404

    data = request.get_json() or {}
    lemma_key = data.get("lemma_key")
    url = data.get("url")

    if not lemma_key or not url:
        return jsonify({"error": "Invalid payload"}), 400

    save_naob_override(project_path, lemma_key, url)
    return jsonify({"status": "ok"})


@app.route("/project/<project_name>/set_meaning", methods=["POST"])
def set_meaning(project_name):
    project_path = os.path.join(PROJECTS_DIR, project_name)
    if not os.path.exists(project_path):
        return jsonify({"error": "Project not found"}), 404

    data = request.get_json() or {}
    lemma_key = data.get("lemma_key")
    meaning = data.get("meaning")

    if not lemma_key or not meaning:
        return jsonify({"error": "Invalid payload"}), 400

    save_meaning(project_path, lemma_key, meaning)
    return jsonify({"status": "ok"})


@app.route("/project/<project_name>/update_segment", methods=["POST"])
def update_segment(project_name):
    project_path = os.path.join(PROJECTS_DIR, project_name)
    data = request.get_json()
    seg_id = data.get("segment_id")
    target_text = data.get("target_text", "")
    tmx_processing.update_target_segment(project_path, seg_id, target_text)
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True)
