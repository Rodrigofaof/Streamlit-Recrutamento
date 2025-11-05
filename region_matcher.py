import pandas as pd
import re
from rapidfuzz import process, fuzz
from utils.normalization import normalize_text

NACIONAL_KEYWORDS = [
    "nacional", "national", "todas", "all", "por pais", "by country",
    "todas as regioes", "all regions", "todas as areas", "all areas",
    "todo o pais", "toda la region", "todo el pais"
]

def is_nacional(text):
    t = normalize_text(text)
    return any(word in t for word in NACIONAL_KEYWORDS)

def build_country_groups(df_ref):
    # Normaliza colunas de referência
    for col in ["city", "state", "region", "region_alt", "region_alt_2", "region_alt_atlantia", "am"]:
        if col in df_ref.columns:
            df_ref[col + "_norm"] = df_ref[col].astype(str).fillna("").apply(normalize_text)
        else:
            df_ref[col + "_norm"] = ""

    # Cria lookup
    lookup_rows = []
    for idx, r in df_ref.iterrows():
        country = str(r.get("Country", "")).strip()

        if not pd.notna(r.get("region")) or str(r.get("region")).strip() == "":
            continue

        # Campos que podem apontar para a região canônica
        source_fields = []
        for c in ["city", "state", "region", "region_alt", "region_alt_2", "region_alt_atlantia", "am"]:
            val = r.get(c)
            if pd.notna(val) and str(val).strip() != "":
                source_fields.append(str(val))

        for c in ["city_norm", "state_norm", "region_norm", "region_alt_norm",
                  "region_alt_2_norm", "region_alt_atlantia_norm", "am_norm"]:
            val = r.get(c)
            if pd.notna(val) and str(val).strip() != "":
                source_fields.append(str(val))

        for key in set([s for s in source_fields if str(s).strip() != ""]):
            lookup_rows.append({
                "Country": country,
                "key_norm": normalize_text(key),
                "canonical_region": str(r.get("region")).strip(),
                "ref_index": idx
            })

    lookup_df = pd.DataFrame(lookup_rows)
    country_groups = {
        country: list(g[["key_norm", "canonical_region", "ref_index"]].itertuples(index=False, name=None))
        for country, g in lookup_df.groupby("Country")
    }
    return country_groups, df_ref

def match_region(text, country_groups, country_code=None, top_n=3):
    txt_norm = normalize_text(text)
    best = {"score": 0, "match": None, "country": None, "method": None, "ref_index": None}

    if not country_code or country_code not in country_groups:
        return best

    choices = country_groups[country_code]
    keys = [c[0] for c in choices]
    if not keys:
        return best

    results = process.extract(txt_norm, keys, scorer=fuzz.token_sort_ratio, limit=top_n)
    for key_candidate, score, pos in results:
        canonical, ref_idx = choices[pos][1], choices[pos][2]
        score2 = fuzz.partial_ratio(txt_norm, key_candidate)
        comb = max(score, score2)
        if comb > best["score"]:
            best.update({
                "score": comb,
                "match": key_candidate,
                "country": country_code,
                "method": "fuzzy_in_country",
                "ref_index": ref_idx
            })

    return best

def generate_rapidfuzzRecruitments(Recruitments, df_ref, country_groups):
    ACCEPT_THRESHOLD = 85
    LOW_CONF_THRESHOLD = 70
    matched = []

    for _, row in Recruitments.iterrows():
        raw = row.get("Region", "")
        country_code = str(row.get("Code", "")).strip() if "Code" in Recruitments.columns else None
        norm = normalize_text(raw)

        if is_nacional(norm):
            matched.append({
                "matched_region": "Nacional",
                "match_score": 100,
                "match_country": country_code,
                "match_method": "rule_based"
            })
            continue

        parts = re.split(r"[,;/|&\-]|\/| e | and | y ", norm)
        parts = [p.strip() for p in parts if p.strip() != ""]

        region_matches, scores = [], []

        for p in parts:
            found = match_region(p, country_groups=country_groups, country_code=country_code)
            if found and found["match"] and found["score"] >= LOW_CONF_THRESHOLD:
                ref_idx = found["ref_index"]
                canonical_region = None
                if "region" in df_ref.columns and pd.notna(df_ref.at[ref_idx, "region"]):
                    canonical_region = str(df_ref.at[ref_idx, "region"]).strip()
                else:
                    continue

                if canonical_region and canonical_region not in region_matches:
                    region_matches.append(canonical_region)
                    scores.append(found["score"])

        if len(region_matches) == 0:
            matched.append({
                "matched_region": None,
                "match_score": None,
                "match_country": country_code,
                "match_method": "no_match"
            })
        else:
            final_region = ", ".join(region_matches)
            avg_score = sum(scores) / len(scores)
            matched.append({
                "matched_region": final_region,
                "match_score": avg_score,
                "match_country": country_code,
                "match_method": "multi_fuzzy"
            })

    matched_df = pd.DataFrame(matched)
    rapidfuzzRecruitments = pd.concat([Recruitments.reset_index(drop=True), matched_df], axis=1)
    if "Project_ID" not in rapidfuzzRecruitments.columns and "Project_ID" in Recruitments.columns:
        rapidfuzzRecruitments["Project_ID"] = Recruitments["Project_ID"].values
    rapidfuzzRecruitments["regions_count"] = rapidfuzzRecruitments["matched_region"].apply(
        lambda x: len(str(x).split(",")) if pd.notna(x) else 0
    )
    return rapidfuzzRecruitments

