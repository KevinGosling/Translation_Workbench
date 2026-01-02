import os
import json
import stanza
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime

# Version 1.11 - Store tokenized data in TMX as properties

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

    # V1.2: Build segment-to-file mapping
    segment_map = {}

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
        
        # V1.2: Map segment ID to source file
        if "source_file" in seg:
            segment_map[str(i)] = seg["source_file"]

    tree = ET.ElementTree(tmx)
    ET.indent(tree, space="  ", level=0)
    tree.write(output_file, encoding="utf-8", xml_declaration=True)
    
    # V1.2: Save segment-to-file mapping
    cache_dir = os.path.join(project_path, "cache")
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    mapping_file = os.path.join(cache_dir, "segment_files.json")
    with open(mapping_file, "w", encoding="utf-8") as f:
        json.dump(segment_map, f, ensure_ascii=False, indent=2)
    
    print(f"TMX exported to {output_file}")
    print(f"Segment mapping saved to {mapping_file}")


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
                segments.append({
                    "id": str(seg_id_counter),
                    "source": sentence.text.strip(),
                    "target": "",
                    "is_paragraph_end": i == len(doc.sentences) - 1,
                    "last_updated": datetime.utcnow().isoformat(),
                    "source_file": fname
                })
                seg_id_counter += 1

    return segments


# -----------------------
# V1.11: Load segments with tokens from TMX
# -----------------------
def load_segments(project_path, include_tokens=True):
    """
    Returns list of segments with 'id', 'source', 'target', 'last_updated', 'is_paragraph_end'
    V1.11: Optionally includes 'tokens' if stored in TMX
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

        segment = {
            "id": f"{tuid}",
            "source": src_text,
            "target": tgt_text,
            "last_updated": last_updated,
            "is_paragraph_end": is_paragraph_end
        }

        # V1.11: Load tokens from TMX if requested and available
        if include_tokens:
            tokens_prop = tu.find("prop[@type='tokens']")
            if tokens_prop is not None and tokens_prop.text:
                try:
                    segment["tokens"] = json.loads(tokens_prop.text)
                except json.JSONDecodeError:
                    # If tokens are malformed, we'll need to re-tokenize
                    segment["tokens"] = None
            else:
                segment["tokens"] = None

        segments.append(segment)

    return segments


# -----------------------
# V1.11: Save tokens to TMX
# -----------------------
def save_tokens_to_tmx(project_path, segment_id, tokens):
    """
    Save tokenized data for a segment to TMX as a property
    """
    tmx_file = get_tmx_file(project_path)
    tree = ET.parse(tmx_file)
    root = tree.getroot()
    body = root.find("body")

    for tu in body.findall("tu"):
        tuid = tu.attrib.get("tuid")
        if segment_id == tuid:
            # Remove existing tokens prop if present
            existing_tokens = tu.find("prop[@type='tokens']")
            if existing_tokens is not None:
                tu.remove(existing_tokens)
            
            # Add new tokens prop
            tokens_prop = ET.SubElement(tu, "prop", {"type": "tokens"})
            tokens_prop.text = json.dumps(tokens, ensure_ascii=False)
            break

    tree.write(tmx_file, encoding="utf-8", xml_declaration=True, method="xml")


# -----------------------
# V1.11: Tokenize segment and save to TMX
# -----------------------
def tokenize_and_store_segment(project_path, segment_id, source_text):
    """
    Tokenize a source segment and store tokens in TMX.
    Returns the tokens.
    """
    tokens = []
    doc = nlp(source_text)
    for sent in doc.sentences:
        for token in sent.words:
            tokens.append({
                "text": token.text,
                "lemma": token.lemma.lower(),
                "pos": token.upos
            })
    
    # Save to TMX
    save_tokens_to_tmx(project_path, segment_id, tokens)
    
    return tokens


# -----------------------
# Cache file helpers
# -----------------------
def get_cache_file(project_path):
    cache_dir = os.path.join(project_path, "cache")
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    return os.path.join(cache_dir, "lemmas.json")


def get_master_cache_file(project_path):
    cache_dir = os.path.join(project_path, "cache")
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    return os.path.join(cache_dir, "lemmas_master.json")


# -----------------------
# V1.2: Segment-to-file mapping helper
# -----------------------
def get_segment_files_map(project_path):
    """Load the mapping of segment IDs to source files"""
    cache_dir = os.path.join(project_path, "cache")
    mapping_file = os.path.join(cache_dir, "segment_files.json")
    
    if not os.path.exists(mapping_file):
        return {}
    
    try:
        with open(mapping_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def get_source_files_list(project_path):
    """Get list of unique source files from the mapping"""
    mapping = get_segment_files_map(project_path)
    files = sorted(set(mapping.values()))
    return files


# -----------------------
# V1.8: Generator version for SSE streaming
# -----------------------
def extract_lemma_frequencies_generator(segments, project_path=None, progress_callback=None):
    """
    Generator version that yields SSE messages for frequency extraction.
    This is the version that should be used with SSE endpoints.
    V1.11: Also tokenizes and stores to TMX
    """
    master_cache_file = get_master_cache_file(project_path) if project_path else None
    
    # Check if master cache already exists
    if master_cache_file and os.path.exists(master_cache_file):
        try:
            with open(master_cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            # Send completion message
            if progress_callback:
                for msg in progress_callback(1, 1, "Using cached frequencies", None):
                    yield msg
            return
        except Exception:
            pass
    
    frequencies = defaultdict(lambda: {"wordforms": set(), "count": 0})
    
    # Group segments by source file for progress reporting
    if project_path and progress_callback:
        segment_files_map = get_segment_files_map(project_path)
        files_segments = defaultdict(list)
        for seg in segments:
            source_file = segment_files_map.get(seg["id"], "unknown")
            files_segments[source_file].append(seg)
        
        sorted_files = sorted(files_segments.keys())
        total_files = len(sorted_files)
        
        for file_idx, source_file in enumerate(sorted_files):
            # Yield progress update
            for msg in progress_callback(file_idx + 1, total_files, f"Processing source file: {source_file}", source_file):
                yield msg
            
            file_segments = files_segments[source_file]
            for seg in file_segments:
                # V1.11: Tokenize and save to TMX
                tokens = tokenize_and_store_segment(project_path, seg["id"], seg["source"])
                
                # Extract frequencies from tokens
                for token in tokens:
                    if not token["text"].isalpha():
                        continue
                    lemma = token["lemma"].strip().lower()
                    pos = token["pos"]
                    if not lemma:
                        continue
                    key = f"{lemma}|{pos}"
                    frequencies[key]["wordforms"].add(token["text"].lower())
                    frequencies[key]["count"] += 1
    else:
        # No progress reporting - process all at once
        for seg in segments:
            # V1.11: Tokenize and save to TMX
            tokens = tokenize_and_store_segment(project_path, seg["id"], seg["source"])
            
            # Extract frequencies from tokens
            for token in tokens:
                if not token["text"].isalpha():
                    continue
                lemma = token["lemma"].strip().lower()
                pos = token["pos"]
                if not lemma:
                    continue
                key = f"{lemma}|{pos}"
                frequencies[key]["wordforms"].add(token["text"].lower())
                frequencies[key]["count"] += 1

    # Save to lemmas_master.json (frequencies only)
    if master_cache_file:
        if progress_callback:
            for msg in progress_callback(total_files if project_path else 1, total_files if project_path else 1, "Saving frequency data...", None):
                yield msg
        
        to_save = {}
        for k, v in frequencies.items():
            to_save[k] = {
                "wordforms": list(v["wordforms"]),
                "count": v["count"]
            }
        with open(master_cache_file, "w", encoding="utf-8") as f:
            json.dump(to_save, f, ensure_ascii=False, indent=2)


# -----------------------
# V1.1: Extract lemma FREQUENCIES only (fast, no occurrences) - LEGACY VERSION
# -----------------------
def extract_lemma_frequencies(segments, project_path=None, progress_callback=None):
    """
    LEGACY: Extract lemma frequencies only - no occurrence data.
    This version doesn't support SSE properly. Use extract_lemma_frequencies_generator for SSE.
    V1.11: Also tokenizes and stores to TMX
    """
    master_cache_file = get_master_cache_file(project_path) if project_path else None
    
    # Check if master cache already exists
    if master_cache_file and os.path.exists(master_cache_file):
        try:
            with open(master_cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            # Convert wordforms back to sets for consistency
            for k, v in cached.items():
                v["wordforms"] = set(v["wordforms"])
            return cached
        except Exception:
            pass
    
    frequencies = defaultdict(lambda: {"wordforms": set(), "count": 0})
    
    # Group segments by source file for progress reporting
    if project_path and progress_callback:
        segment_files_map = get_segment_files_map(project_path)
        files_segments = defaultdict(list)
        for seg in segments:
            source_file = segment_files_map.get(seg["id"], "unknown")
            files_segments[source_file].append(seg)
        
        sorted_files = sorted(files_segments.keys())
        total_files = len(sorted_files)
        
        for file_idx, source_file in enumerate(sorted_files):
            if progress_callback:
                progress_callback(file_idx + 1, total_files, f"Processing source file: {source_file}", source_file)
            
            file_segments = files_segments[source_file]
            for seg in file_segments:
                # V1.11: Tokenize and save to TMX
                tokens = tokenize_and_store_segment(project_path, seg["id"], seg["source"])
                
                # Extract frequencies from tokens
                for token in tokens:
                    if not token["text"].isalpha():
                        continue
                    lemma = token["lemma"].strip().lower()
                    pos = token["upos"]
                    if not lemma:
                        continue
                    key = f"{lemma}|{pos}"
                    frequencies[key]["wordforms"].add(token["text"].lower())
                    frequencies[key]["count"] += 1
    else:
        # No progress reporting - process all at once
        for seg in segments:
            # V1.11: Tokenize and save to TMX
            tokens = tokenize_and_store_segment(project_path, seg["id"], seg["source"])
            
            # Extract frequencies from tokens
            for token in tokens:
                if not token["text"].isalpha():
                    continue
                lemma = token["lemma"].strip().lower()
                pos = token["pos"]
                if not lemma:
                    continue
                key = f"{lemma}|{pos}"
                frequencies[key]["wordforms"].add(token["text"].lower())
                frequencies[key]["count"] += 1

    # Save to lemmas_master.json (frequencies only)
    if master_cache_file:
        if progress_callback:
            progress_callback(total_files if project_path else 1, total_files if project_path else 1, "Saving frequency data...", None)
        
        to_save = {}
        for k, v in frequencies.items():
            to_save[k] = {
                "wordforms": list(v["wordforms"]),
                "count": v["count"]
            }
        with open(master_cache_file, "w", encoding="utf-8") as f:
            json.dump(to_save, f, ensure_ascii=False, indent=2)

    return frequencies


# -----------------------
# V1.8: Generator version for concordance building with SSE
# -----------------------
def build_working_concordances_generator(project_path, segments, suppressions, progress_callback=None):
    """
    Generator version that yields SSE messages for concordance building.
    This is the version that should be used with SSE endpoints.
    V1.11: Uses tokens from TMX if available
    """
    master_file = get_master_cache_file(project_path)
    
    # Load frequency data from master
    if not os.path.exists(master_file):
        # If master doesn't exist, create it first (but this shouldn't happen in normal flow)
        for msg in extract_lemma_frequencies_generator(segments, project_path, progress_callback):
            yield msg
    
    with open(master_file, "r", encoding="utf-8") as f:
        frequencies = json.load(f)
    
    # V1.11: Load segments with tokens from TMX
    segments_with_tokens = load_segments(project_path, include_tokens=True)
    
    # Build concordances only for non-suppressed lemmas
    lemmas = defaultdict(lambda: {"wordforms": set(), "occurrences": []})
    total_segments = len(segments_with_tokens)
    
    # Report progress every 10 segments to avoid overwhelming the connection
    report_interval = max(1, total_segments // 100)
    
    for idx, seg in enumerate(segments_with_tokens):
        if progress_callback and (idx % report_interval == 0 or idx == total_segments - 1):
            for msg in progress_callback(idx + 1, total_segments, f"Building concordances: segment {idx + 1}/{total_segments}", None):
                yield msg
        
        # V1.11: Use tokens from TMX if available, otherwise tokenize on-the-fly
        if seg.get("tokens"):
            tokens = seg["tokens"]
        else:
            # Fallback: tokenize if not in TMX yet
            tokens = tokenize_and_store_segment(project_path, seg["id"], seg["source"])
        
        # Process tokens to build concordances
        for token in tokens:
            if not token["text"].isalpha():
                continue
            lemma = token["lemma"].strip().lower()
            pos = token["pos"]
            if not lemma:
                continue
            key = f"{lemma}|{pos}"
            
            # Skip suppressed lemmas/POS
            if key in suppressions.get("lemmas", []) or pos in suppressions.get("pos", []):
                continue
            
            lemmas[key]["wordforms"].add(token["text"].lower())
            # Store just segment_id and source text (not tokens)
            if not any(occ["segment_id"] == seg["id"] for occ in lemmas[key]["occurrences"]):
                lemmas[key]["occurrences"].append({
                    "segment_id": seg["id"],
                    "source_segment": seg["source"]
                })
    
    if progress_callback:
        for msg in progress_callback(total_segments, total_segments, "Finalizing concordances...", None):
            yield msg
    
    # Merge with all lemmas from master (including suppressed, but with empty occurrences)
    working_lemmas = {}
    for key, freq_data in frequencies.items():
        if key in lemmas:
            # Non-suppressed: full concordance data
            working_lemmas[key] = {
                "wordforms": list(lemmas[key]["wordforms"]),
                "occurrences": lemmas[key]["occurrences"]
            }
        else:
            # Suppressed: keep lemma but no occurrences
            working_lemmas[key] = {
                "wordforms": freq_data["wordforms"],
                "occurrences": []
            }
    
    # Save working file
    working_file = get_cache_file(project_path)
    with open(working_file, "w", encoding="utf-8") as f:
        json.dump(working_lemmas, f, ensure_ascii=False, indent=2)


# -----------------------
# V1.1: Build full concordances for non-suppressed lemmas only - LEGACY VERSION
# -----------------------
def build_working_concordances(project_path, segments, suppressions, progress_callback=None):
    """
    LEGACY: Build full concordances only for non-suppressed lemmas.
    This version doesn't support SSE properly. Use build_working_concordances_generator for SSE.
    V1.11: Uses tokens from TMX if available
    """
    master_file = get_master_cache_file(project_path)
    
    # Load frequency data from master
    if not os.path.exists(master_file):
        extract_lemma_frequencies(segments, project_path, progress_callback)
    
    with open(master_file, "r", encoding="utf-8") as f:
        frequencies = json.load(f)
    
    # V1.11: Load segments with tokens from TMX
    segments_with_tokens = load_segments(project_path, include_tokens=True)
    
    # Build concordances only for non-suppressed lemmas
    lemmas = defaultdict(lambda: {"wordforms": set(), "occurrences": []})
    total_segments = len(segments_with_tokens)
    
    for idx, seg in enumerate(segments_with_tokens):
        if progress_callback:
            progress_callback(idx + 1, total_segments, f"Building concordances: segment {idx + 1}/{total_segments}", None)
        
        # V1.11: Use tokens from TMX if available, otherwise tokenize on-the-fly
        if seg.get("tokens"):
            tokens = seg["tokens"]
        else:
            # Fallback: tokenize if not in TMX yet
            tokens = tokenize_and_store_segment(project_path, seg["id"], seg["source"])
        
        # Process tokens to build concordances
        for token in tokens:
            if not token["text"].isalpha():
                continue
            lemma = token["lemma"].strip().lower()
            pos = token["pos"]
            if not lemma:
                continue
            key = f"{lemma}|{pos}"
            
            # Skip suppressed lemmas/POS
            if key in suppressions.get("lemmas", []) or pos in suppressions.get("pos", []):
                continue
            
            lemmas[key]["wordforms"].add(token["text"].lower())
            # Store just segment_id and source text (not tokens)
            if not any(occ["segment_id"] == seg["id"] for occ in lemmas[key]["occurrences"]):
                lemmas[key]["occurrences"].append({
                    "segment_id": seg["id"],
                    "source_segment": seg["source"]
                })
    
    if progress_callback:
        progress_callback(total_segments, total_segments, "Finalizing concordances...", None)
    
    # Merge with all lemmas from master (including suppressed, but with empty occurrences)
    working_lemmas = {}
    for key, freq_data in frequencies.items():
        if key in lemmas:
            # Non-suppressed: full concordance data
            working_lemmas[key] = {
                "wordforms": list(lemmas[key]["wordforms"]),
                "occurrences": lemmas[key]["occurrences"]
            }
        else:
            # Suppressed: keep lemma but no occurrences
            working_lemmas[key] = {
                "wordforms": freq_data["wordforms"],
                "occurrences": []
            }
    
    # Save working file
    working_file = get_cache_file(project_path)
    with open(working_file, "w", encoding="utf-8") as f:
        json.dump(working_lemmas, f, ensure_ascii=False, indent=2)


# -----------------------
# V1.1: Extract lemmas - now uses frequency-first approach
# -----------------------
def extract_lemmas(segments, project_path=None):
    """
    Extract lemmas using frequency-first approach.
    If lemmas.json exists, return it.
    Otherwise, return frequency data from lemmas_master.json.
    """
    cache_file = get_cache_file(project_path) if project_path else None
    
    # If working cache exists, use it
    if cache_file and os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            for k, v in cached.items():
                v["wordforms"] = set(v["wordforms"])
            return cached
        except Exception:
            pass
    
    # Otherwise, create frequency-only master cache
    frequencies = extract_lemma_frequencies(segments, project_path)
    
    # Convert to format expected by frontend (empty occurrences)
    result = {}
    for k, v in frequencies.items():
        result[k] = {
            "wordforms": v["wordforms"],
            "occurrences": []
        }
    
    return result


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
