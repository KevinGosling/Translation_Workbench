import os
import json
import stanza
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime

# Initialize Stanza pipeline for Norwegian Bokmål
nlp = stanza.Pipeline(lang="nb", processors="tokenize,pos,lemma", use_gpu=False)

# -----------------------
# TMX helpers
# -----------------------
def get_tmx_file(project_path):
    """
    Ensure TMX exists for the project; create it if missing.
    Returns path to project.tmx
    """
    tgt_dir = os.path.join(project_path, "target")
    if not os.path.exists(tgt_dir):
        os.makedirs(tgt_dir)
    tmx_file = os.path.join(tgt_dir, "project.tmx")
    if not os.path.exists(tmx_file):
        export_project_to_tmx(project_path, output_file=tmx_file)
    return tmx_file


def export_project_to_tmx(project_path, output_file=None):
    """
    Generate TMX from source files. Target initially empty.
    """
    segments = load_source_segments(project_path)
    if not output_file:
        tgt_dir = os.path.join(project_path, "target")
        if not os.path.exists(tgt_dir):
            os.makedirs(tgt_dir)
        output_file = os.path.join(tgt_dir, "project.tmx")

    tmx = ET.Element("tmx", version="1.4")
    ET.SubElement(tmx, "header", {
        "creationtool": "TranslationWorkbench",
        "creationtoolversion": "1.0",
        "datatype": "plaintext",
        "segtype": "sentence",
        "adminlang": "en-us",
        "srclang": "source",
        "o-tmf": "WorkbenchTMX"
    })
    body = ET.SubElement(tmx, "body")

    for i, seg in enumerate(segments, start=1):
        tu = ET.SubElement(body, "tu", {
            "tuid": str(i),
            "last_updated": seg["last_updated"]
        })
        if seg.get("is_paragraph_end"):
            ET.SubElement(tu, "prop", {"type": "paragraph-end"}).text = "yes"
        tuv_src = ET.SubElement(tu, "tuv", {"xml:lang": "source"})
        ET.SubElement(tuv_src, "seg").text = seg.get("source", "")
        tuv_tgt = ET.SubElement(tu, "tuv", {"xml:lang": "target"})
        ET.SubElement(tuv_tgt, "seg").text = seg.get("target", "")

    tree = ET.ElementTree(tmx)
    ET.indent(tree, space="  ", level=0)
    tree.write(output_file, encoding="utf-8", xml_declaration=True)
    print(f"TMX exported to {output_file}")


# -----------------------
# Load source segments (for TMX creation)
# -----------------------
def load_source_segments(project_path):
    """
    Reads all source text files and splits into sentence-level segments.
    Used only to create TMX initially.
    """
    src_dir = os.path.join(project_path, "source")
    if not os.path.exists(src_dir):
        return []

    segments = []
    seg_id_counter = 1

    for fname in sorted(os.listdir(src_dir)):
        if not fname.lower().endswith(".txt"):
            continue
        path = os.path.join(src_dir, fname)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        paragraphs = [p for p in text.split("\n\n") if p.strip()]
        for para in paragraphs:
            doc = nlp(para)
            for i, sentence in enumerate(doc.sentences):
                seg_id = f"{fname}_{seg_id_counter}"
                segments.append({
                    "id": seg_id,
                    "source": sentence.text.strip(),
                    "target": "",
                    "is_paragraph_end": i == len(doc.sentences) - 1,
                    "last_updated": datetime.utcnow().isoformat()
                })
                seg_id_counter += 1

    return segments


# -----------------------
# Load segments for workbench (TMX + lemma caching)
# -----------------------
def load_segments(project_path):
    """
    Returns list of segments with 'id', 'source', 'target', 'last_updated', 'is_paragraph_end'
    """
    segments = []

    tmx_file = get_tmx_file(project_path)

    tree = ET.parse(tmx_file)
    root = tree.getroot()
    body = root.find("body")

    # Namespace mapping for xml:lang
    namespaces = {"xml": "http://www.w3.org/XML/1998/namespace"}

    for tu in body.findall("tu"):
        tuid = tu.attrib.get("tuid")
        last_updated = tu.attrib.get("last_updated")
        is_paragraph_end = False
        prop = tu.find("prop[@type='paragraph-end']")
        if prop is not None and prop.text == "yes":
            is_paragraph_end = True

        # Source text
        src_seg = tu.find("./tuv[@xml:lang='source']", namespaces=namespaces)
        src_text = ""
        if src_seg is not None:
            seg_elem = src_seg.find("seg")
            if seg_elem is not None and seg_elem.text:
                src_text = seg_elem.text.strip()

        # Target text
        tgt_seg = tu.find("./tuv[@xml:lang='target']", namespaces=namespaces)
        tgt_text = ""
        if tgt_seg is not None:
            seg_elem = tgt_seg.find("seg")
            if seg_elem is not None and seg_elem.text:
                tgt_text = seg_elem.text.strip()

        segments.append({
            "id": f"{tuid}",  # Only TMX ID
            "source": src_text,
            "target": tgt_text,
            "last_updated": last_updated,
            "is_paragraph_end": is_paragraph_end
        })

    return segments


# -----------------------
# Cache file helper
# -----------------------
def get_cache_file(project_path):
    cache_dir = os.path.join(project_path, "cache")
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    return os.path.join(cache_dir, "lemmas.json")


# -----------------------
# Extract lemmas and wordforms
# -----------------------
def extract_lemmas(segments, project_path=None):
    """
    Extract lemmas using TMX-only segment IDs (tuid).
    Target segments are not stored in the cache.
    """
    cache_file = get_cache_file(project_path) if project_path else None
    if cache_file and os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            for k, v in cached.items():
                v["wordforms"] = set(v["wordforms"])
            return cached
        except Exception:
            pass

    lemmas = defaultdict(lambda: {"wordforms": set(), "occurrences": []})

    for seg in segments:
        tuid = seg["id"]  # TMX-only ID
        doc = nlp(seg["source"])
        for sentence in doc.sentences:
            for token in sentence.words:
                if not token.text.isalpha():
                    continue
                lemma = token.lemma.strip().lower()
                pos = token.upos
                if not lemma:
                    continue
                key = f"{lemma}|{pos}"
                data = lemmas[key]
                data["wordforms"].add(token.text.lower())
                data["occurrences"].append({
                    "segment_id": tuid,
                    "source_segment": sentence.text
                })

    if cache_file:
        to_save = {}
        for k, v in lemmas.items():
            to_save[k] = {
                "wordforms": list(v["wordforms"]),
                "occurrences": v["occurrences"]
            }
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(to_save, f, ensure_ascii=False, indent=2)

    return lemmas


# -----------------------
# Update target segment in TMX
# -----------------------
def update_target_segment(project_path, segment_id, new_text):
    tmx_file = get_tmx_file(project_path)
    tree = ET.parse(tmx_file)
    root = tree.getroot()
    body = root.find("body")

    # Namespace mapping for xml:lang
    namespaces = {"xml": "http://www.w3.org/XML/1998/namespace"}

    for tu in body.findall("tu"):
        tuid = tu.attrib.get("tuid")
        if segment_id == tuid:
            tuv_tgt = tu.find("./tuv[@xml:lang='target']", namespaces=namespaces)
            if tuv_tgt is None:
                tuv_tgt = ET.SubElement(tu, "tuv", {"xml:lang": "target"})
            seg_elem = tuv_tgt.find("seg")
            if seg_elem is None:
                seg_elem = ET.SubElement(tuv_tgt, "seg")
            seg_elem.text = new_text
            tu.attrib["last_updated"] = datetime.utcnow().isoformat()
            break

    tree.write(tmx_file, encoding="utf-8", xml_declaration=True, method="xml")
