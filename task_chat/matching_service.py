from rapidfuzz import fuzz, process
from .config import FUZZY_MATCH_THRESHOLD


def person_candidates(models, role_filter=None):
    candidates = []
    role_filter = (role_filter or "").lower().strip()

    Worker = models["workers"]
    Admin = models["admins"]

    if role_filter not in {"admin", "superadmin", "scrum"}:
        for obj in Worker.query.all():
            if role_filter in {"team_leader", "team leader", "tl"} and not getattr(obj, "is_tl", False):
                continue
            full = " ".join(x for x in [
                getattr(obj, "first_name", ""), getattr(obj, "last_name", "")
            ] if x).strip()
            if full:
                candidates.append({
                    "name": full, "id": obj.id, "role": "worker",
                    "source": "workers", "object": obj
                })

    if role_filter not in {"worker", "team_leader", "team leader", "tl"}:
        for obj in Admin.query.all():
            full = " ".join(x for x in [
                getattr(obj, "first_name", ""), getattr(obj, "last_name", "")
            ] if x).strip()
            if full:
                roles = []
                if getattr(obj, "is_superadmin", False): roles.append("superadmin")
                if getattr(obj, "is_admin", False): roles.append("admin")
                if getattr(obj, "is_scrum", False): roles.append("scrum")
                candidates.append({
                    "name": full, "id": obj.id, "role": roles[0] if roles else "admin",
                    "source": "admins", "object": obj
                })
    return candidates


def match_name(query, candidates, threshold=FUZZY_MATCH_THRESHOLD):
    if not query:
        return {"status": "not_requested", "match": None, "matches": []}
    if not candidates:
        return {"status": "not_found", "match": None, "matches": []}

    names = [item["name"] for item in candidates]
    ranked = process.extract(
        query, names, scorer=fuzz.WRatio, limit=5
    )
    results = []
    seen = set()
    for name, score, index in ranked:
        item = candidates[index]
        key = (item["source"], item["id"])
        if score >= threshold and key not in seen:
            seen.add(key)
            results.append({
                "name": item["name"], "id": item["id"],
                "role": item["role"], "source": item["source"],
                "score": round(float(score), 1)
            })

    if not results:
        return {"status": "not_found", "match": None, "matches": []}
    if len(results) > 1 and results[0]["score"] - results[1]["score"] < 5:
        return {"status": "ambiguous", "match": None, "matches": results}
    return {"status": "matched", "match": results[0], "matches": results}


def match_simple_name(query, objects, name_getter, threshold=FUZZY_MATCH_THRESHOLD):
    if not query:
        return {"status": "not_requested", "match": None, "matches": []}
    names = [name_getter(obj) for obj in objects]
    ranked = process.extract(query, names, scorer=fuzz.WRatio, limit=5)
    matches = []
    for name, score, index in ranked:
        if score >= threshold:
            obj = objects[index]
            matches.append({"name": name, "id": obj.id, "score": round(float(score), 1)})
    if not matches:
        return {"status": "not_found", "match": None, "matches": []}
    if len(matches) > 1 and matches[0]["score"] - matches[1]["score"] < 5:
        return {"status": "ambiguous", "match": None, "matches": matches}
    return {"status": "matched", "match": matches[0], "matches": matches}
