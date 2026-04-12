import csv
from collections import Counter, defaultdict
import difflib
import re
from pathlib import Path

import yaml


LOW_CONFIDENCE_FALLBACK_THRESHOLD = 0.35
LOW_CONFIDENCE_STEP_VOTE_THRESHOLD = 0.67


BOOK_CODE_MAP = {
    # OT
    "GENESIS": "GEN", "GEN": "GEN",
    "EXODUS": "EXO", "EXO": "EXO",
    "LEVITICUS": "LEV", "LEV": "LEV",
    "NUMBERS": "NUM", "NUM": "NUM",
    "DEUTERONOMY": "DEU", "DEU": "DEU",
    "JOSHUA": "JOS", "JOS": "JOS",
    "JUDGES": "JDG", "JDG": "JDG",
    "RUTH": "RUT", "RUT": "RUT",
    "1SAMUEL": "1SA", "1 SA": "1SA", "1SA": "1SA",
    "2SAMUEL": "2SA", "2 SA": "2SA", "2SA": "2SA",
    "1KINGS": "1KI", "1 KI": "1KI", "1KI": "1KI",
    "2KINGS": "2KI", "2 KI": "2KI", "2KI": "2KI",
    "1CHRONICLES": "1CH", "1 CH": "1CH", "1CH": "1CH",
    "2CHRONICLES": "2CH", "2 CH": "2CH", "2CH": "2CH",
    "EZRA": "EZR", "EZR": "EZR",
    "NEHEMIAH": "NEH", "NEH": "NEH",
    "ESTHER": "EST", "EST": "EST",
    "JOB": "JOB",
    "PSALM": "PSA", "PSALMS": "PSA", "PSA": "PSA",
    "PROVERBS": "PRO", "PRO": "PRO",
    "ECCLESIASTES": "ECC", "ECC": "ECC",
    "SONGOFSOLOMON": "SNG", "SONG OF SOLOMON": "SNG", "SONGOFSONGS": "SNG", "SNG": "SNG",
    "ISAIAH": "ISA", "ISA": "ISA",
    "JEREMIAH": "JER", "JER": "JER",
    "LAMENTATIONS": "LAM", "LAM": "LAM",
    "EZEKIEL": "EZK", "EZK": "EZK",
    "DANIEL": "DAN", "DAN": "DAN",
    "HOSEA": "HOS", "HOS": "HOS",
    "JOEL": "JOL", "JOL": "JOL",
    "AMOS": "AMO", "AMO": "AMO",
    "OBADIAH": "OBA", "OBA": "OBA",
    "JONAH": "JON", "JON": "JON",
    "MICAH": "MIC", "MIC": "MIC",
    "NAHUM": "NAM", "NAH": "NAM", "NAM": "NAM",
    "HABAKKUK": "HAB", "HAB": "HAB",
    "ZEPHANIAH": "ZEP", "ZEP": "ZEP",
    "HAGGAI": "HAG", "HAG": "HAG",
    "ZECHARIAH": "ZEC", "ZEC": "ZEC",
    "MALACHI": "MAL", "MAL": "MAL",
    # NT
    "MATTHEW": "MAT", "MAT": "MAT",
    "MARK": "MRK", "MRK": "MRK",
    "LUKE": "LUK", "LUK": "LUK",
    "JOHN": "JHN", "JHN": "JHN",
    "ACTS": "ACT", "ACT": "ACT",
    "ROMANS": "ROM", "ROM": "ROM",
    "1CORINTHIANS": "1CO", "1 CORINTHIANS": "1CO", "1CO": "1CO",
    "2CORINTHIANS": "2CO", "2 CORINTHIANS": "2CO", "2CO": "2CO",
    "GALATIANS": "GAL", "GAL": "GAL",
    "EPHESIANS": "EPH", "EPH": "EPH",
    "PHILIPPIANS": "PHP", "PHI": "PHP", "PHP": "PHP",
    "COLOSSIANS": "COL", "COL": "COL",
    "1THESSALONIANS": "1TH", "1 THESSALONIANS": "1TH", "1TH": "1TH",
    "2THESSALONIANS": "2TH", "2 THESSALONIANS": "2TH", "2TH": "2TH",
    "1TIMOTHY": "1TI", "1 TIMOTHY": "1TI", "1TI": "1TI",
    "2TIMOTHY": "2TI", "2 TIMOTHY": "2TI", "2TI": "2TI",
    "TITUS": "TIT", "TIT": "TIT",
    "PHILEMON": "PHM", "PHM": "PHM",
    "HEBREWS": "HEB", "HEB": "HEB",
    "JAMES": "JAS", "JAS": "JAS",
    "1PETER": "1PE", "1 PETER": "1PE", "1PE": "1PE",
    "2PETER": "2PE", "2 PETER": "2PE", "2PE": "2PE",
    "1JOHN": "1JN", "1 JOHN": "1JN", "1JN": "1JN",
    "2JOHN": "2JN", "2 JOHN": "2JN", "2JN": "2JN",
    "3JOHN": "3JN", "3 JOHN": "3JN", "3JN": "3JN",
    "JUDE": "JUD", "JUD": "JUD",
    "REVELATION": "REV", "REV": "REV",
}


def normalize_text(text):
    if not text:
        return ""
    text = text.lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def token_set(text):
    return set(normalize_text(text).split())


def sequence_score(a, b):
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


def overlap_score(a, b):
    sa = token_set(a)
    sb = token_set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def combined_score(step_title, law_title, law_commandment):
    title_seq = sequence_score(step_title, law_title)
    title_overlap = overlap_score(step_title, law_title)
    cmd_seq = sequence_score(step_title, law_commandment)

    # Weight title matching highest, with smaller support from commandment sentence.
    return (0.6 * title_seq) + (0.25 * title_overlap) + (0.15 * cmd_seq)


def canonical_book(book):
    if not book:
        return ""
    b = re.sub(r"\s+", " ", book.strip().upper())
    b_nospace = b.replace(" ", "")
    return BOOK_CODE_MAP.get(b, BOOK_CODE_MAP.get(b_nospace, b_nospace[:3]))


def parse_csv_ref(ref):
    # Example: MAT 4:17, 1JN 1:9
    match = re.match(r"^\s*([1-3]?[A-Z]{2,})\s+(\d+):(\d+)", ref or "")
    if not match:
        return None
    return f"{canonical_book(match.group(1))} {match.group(2)}:{match.group(3)}"


def extract_law_refs(item):
    refs = set()
    bible_refs = item.get("bible_references", {}) or {}
    for key in [
        "key_nt_scriptures",
        "key_ot_scriptures",
        "supportive_nt_scriptures",
        "supportive_ot_scriptures",
    ]:
        for ref in bible_refs.get(key, []) or []:
            text = str(ref)
            # Capture refs like "Matthew 5:20" or "1 Timothy 3:8"
            for m in re.finditer(r"([1-3]?\s?[A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(\d+):(\d+)", text):
                refs.add(f"{canonical_book(m.group(1))} {m.group(2)}:{m.group(3)}")
    return refs


def scripture_overlap_score(step_refs, law_refs):
    if not step_refs or not law_refs:
        return 0.0
    overlap = step_refs & law_refs
    if not overlap:
        return 0.0
    return len(overlap) / max(len(step_refs), 1)


def build_category_profiles(law_entries):
    profiles = {}
    for entry in law_entries:
        category = entry.get("category")
        if not category:
            continue
        profile = profiles.setdefault(
            category,
            {
                "tokens": Counter(),
                "refs": set(),
            },
        )

        for token in normalize_text(entry.get("title", "")).split():
            profile["tokens"][token] += 2
        for token in normalize_text(entry.get("commandment", "")).split():
            profile["tokens"][token] += 1

        profile["refs"].update(entry.get("refs", set()))

    return profiles


def category_text_score(step_title, token_profile):
    tokens = normalize_text(step_title).split()
    if not tokens or not token_profile:
        return 0.0
    weight = sum(token_profile.get(t, 0) for t in tokens)
    return weight / len(tokens)


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def load_law_entries(ot_path, nt_path):
    entries = []
    for item in load_yaml(ot_path) + load_yaml(nt_path):
        entries.append(
            {
                "id": item.get("id", ""),
                "title": item.get("title", ""),
                "commandment": item.get("commandment", ""),
                "category": item.get("category", ""),
            }
        )
    return entries


def build_step_category_votes(expanded_path):
    """
    Build category votes for STEP ids from expanded Law of Messiah data.
    Each commandment contributes one vote of its own category to every related STEP.
    """
    votes = defaultdict(Counter)
    if not expanded_path.exists():
        return votes

    for item in load_yaml(expanded_path):
        category = item.get("category")
        if not category:
            continue

        for related in item.get("related_steps", []) or []:
            if not isinstance(related, dict):
                continue
            step_id = str(related.get("id", "")).strip().upper()
            match = re.fullmatch(r"STEP(\d+)", step_id)
            if match:
                step_number = str(int(match.group(1)))
                votes[step_number][category] += 1

    return votes


def load_step_titles_from_csv(csv_path):
    step_to_title = {}
    step_to_refs = defaultdict(set)
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            step = (row.get("step") or "").strip()
            title = (row.get("title_en") or "").strip()
            if step and title and step not in step_to_title:
                step_to_title[step] = title

            parsed_ref = parse_csv_ref((row.get("bible_ref") or "").strip())
            if step and parsed_ref:
                step_to_refs[step].add(parsed_ref)

    return step_to_title, step_to_refs


def build_category_mapping(step_to_title, step_to_refs, law_entries, step_category_votes, category_profiles):
    mapping = {}
    diagnostics = []
    all_categories = sorted(category_profiles.keys())

    for step, title in sorted(step_to_title.items(), key=lambda x: int(x[0])):
        # Preferred strategy: category voting via related STEP links.
        if step in step_category_votes and step_category_votes[step]:
            ranked_votes = sorted(
                step_category_votes[step].items(),
                key=lambda kv: (-kv[1], kv[0])
            )
            best_category, votes = ranked_votes[0]
            total_votes = sum(step_category_votes[step].values())
            confidence = votes / total_votes if total_votes else 0.0
            votes_for_category = dict(ranked_votes)
            alternatives = []
            for category in all_categories:
                count = votes_for_category.get(category, 0)
                alt = {"category": category}
                if count > 0 and total_votes:
                    alt["score"] = round(count / total_votes, 4)
                alternatives.append(alt)

            mapping[step] = {
                "category": best_category,
                "score": confidence,
                "matched_id": "STEP-VOTE",
                "matched_title": f"{votes}/{total_votes} votes",
                "source_step_title": title,
                "method": "step_vote",
                "alternatives": alternatives,
            }
            diagnostics.append(mapping[step])
            continue

        # Fallback strategy: title similarity against Law of Messiah titles.
        best_category = ""
        best_score = -1.0
        step_refs = step_to_refs.get(step, set())

        ranked_categories = []
        for category, profile in category_profiles.items():
            refs_score = scripture_overlap_score(step_refs, profile["refs"])
            text_score = category_text_score(title, profile["tokens"])
            score = (0.8 * refs_score) + (0.2 * text_score)
            ranked_categories.append((category, score, refs_score, text_score))
            if score > best_score:
                best_score = score
                best_category = category

        ranked_categories.sort(key=lambda item: (-item[1], item[0]))
        alternatives = [
            {
                "category": category,
                "score": round(score, 4),
            }
            for category, score, refs_score, text_score in ranked_categories
        ]

        mapping[step] = {
            "category": best_category,
            "score": best_score,
            "matched_id": "CATEGORY-PROFILE",
            "matched_title": best_category,
            "source_step_title": title,
            "method": "title_fallback",
            "alternatives": alternatives,
        }
        diagnostics.append(mapping[step])

    return mapping, diagnostics


def update_csv_categories(csv_path, mapping):
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        rows = list(reader)
        fieldnames = reader.fieldnames

    updated_rows = []
    updated_count = 0
    for row in rows:
        step = (row.get("step") or "").strip()
        if step in mapping:
            # Keep CSV compact: update rows that represent commandment metadata lines.
            if (row.get("title_en") or "").strip() or (row.get("category") or "").strip():
                new_category = mapping[step]["category"]
                if row.get("category") != new_category:
                    row["category"] = new_category
                    updated_count += 1
        updated_rows.append(row)

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(updated_rows)

    return updated_count


def update_yaml_categories(yaml_path, mapping):
    data = load_yaml(yaml_path)
    updated_count = 0

    for item in data:
        step = str(item.get("step", "")).strip()
        if step in mapping:
            new_category = mapping[step]["category"]
            if item.get("category") != new_category:
                item["category"] = new_category
                updated_count += 1

    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, width=1200)

    return updated_count


def write_low_confidence_review(review_path, mapping):
    def sort_alternatives(alternatives):
        prepared = [alt for alt in alternatives if isinstance(alt, dict) and alt.get("category")]

        def sort_key(alt):
            has_score = "score" in alt
            score = alt.get("score", 0.0)
            if not isinstance(score, (int, float)):
                score = 0.0
            category = str(alt.get("category", ""))
            return (0 if has_score else 1, -float(score), category)

        return sorted(prepared, key=sort_key)

    existing_by_step = {}
    if review_path.exists():
        existing_items = load_yaml(review_path)
        if isinstance(existing_items, list):
            for existing in existing_items:
                if not isinstance(existing, dict):
                    continue
                step = str(existing.get("step", "")).strip()
                if step:
                    existing_by_step[step] = existing

    review_items = []
    for step, item in sorted(mapping.items(), key=lambda kv: int(kv[0])):
        method = item.get("method")
        score = item.get("score", 0.0)

        is_low_confidence = (
            (method == "title_fallback" and score < LOW_CONFIDENCE_FALLBACK_THRESHOLD)
            or (method == "step_vote" and score < LOW_CONFIDENCE_STEP_VOTE_THRESHOLD)
        )
        existing = existing_by_step.get(step, {})
        approved_category = str(existing.get("approved_category", "")).strip()

        review_items.append(
            {
                "step": step,
                "title_en": item.get("source_step_title", ""),
                "current_category": item.get("category", ""),
                "confidence_score": round(score, 4),
                "approved_category": approved_category,
                "proposed_alternatives": sort_alternatives(item.get("alternatives", [])),
            }
        )

    with open(review_path, "w", encoding="utf-8") as f:
        yaml.dump(review_items, f, allow_unicode=True, sort_keys=False, width=1200)

    return len(review_items)


def apply_review_overrides(review_path, mapping):
    """
    Apply manually approved categories from the low-confidence review file.
    Returns number of mapping entries overridden.
    """
    if not review_path.exists():
        return 0

    review_items = load_yaml(review_path)
    if not isinstance(review_items, list):
        return 0

    override_count = 0
    for item in review_items:
        if not isinstance(item, dict):
            continue

        step = str(item.get("step", "")).strip()
        approved = str(item.get("approved_category", "")).strip()
        if not step or not approved or step not in mapping:
            continue

        if mapping[step].get("category") != approved:
            mapping[step]["category"] = approved
            mapping[step]["method"] = "manual_review"
            mapping[step]["score"] = 1.0
            mapping[step]["matched_id"] = "REVIEW-OVERRIDE"
            mapping[step]["matched_title"] = approved
            override_count += 1

    return override_count


def main():
    base_dir = Path(__file__).resolve().parent
    law_dir = base_dir.parent / "lawofmessiah"

    csv_path = base_dir / "commandments.csv"
    yaml_path = base_dir / "commandments.yaml"
    review_path = base_dir / "commandments_category_review_low_confidence.yaml"
    ot_path = law_dir / "Law_of_Messiah_ot.yaml"
    nt_path = law_dir / "Law_of_Messiah_nt.yaml"
    expanded_path = law_dir / "filter_output" / "filtered_commandments_reviewed_unique_expanded.yaml"

    law_entries = load_law_entries(ot_path, nt_path)
    for entry in law_entries:
        entry["refs"] = extract_law_refs(entry)
    category_profiles = build_category_profiles(law_entries)

    step_to_title, step_to_refs = load_step_titles_from_csv(csv_path)
    step_category_votes = build_step_category_votes(expanded_path)
    mapping, diagnostics = build_category_mapping(
        step_to_title,
        step_to_refs,
        law_entries,
        step_category_votes,
        category_profiles,
    )

    manual_overrides = apply_review_overrides(review_path, mapping)

    csv_updates = update_csv_categories(csv_path, mapping)
    yaml_updates = update_yaml_categories(yaml_path, mapping)
    review_count = write_low_confidence_review(review_path, mapping)

    diagnostics.sort(key=lambda d: d["score"])
    vote_based = sum(1 for d in diagnostics if d["method"] == "step_vote")
    fallback_based = sum(1 for d in diagnostics if d["method"] == "title_fallback")

    print(f"Steps processed: {len(step_to_title)}")
    print(f"CSV rows updated: {csv_updates}")
    print(f"YAML commandments updated: {yaml_updates}")
    print(f"Manual review overrides applied: {manual_overrides}")
    print(f"Mapped by STEP votes: {vote_based}")
    print(f"Mapped by title fallback: {fallback_based}")
    print(f"Review items written: {review_count}")
    print(f"Review file: {review_path}")
    print("Lowest-confidence matches (top 15):")
    for item in diagnostics[:15]:
        print(
            f"- step title='{item['source_step_title']}' => {item['category']} "
            f"(score={item['score']:.3f}, method={item['method']}, "
            f"matched {item['matched_id']} '{item['matched_title']}')"
        )


if __name__ == "__main__":
    main()
