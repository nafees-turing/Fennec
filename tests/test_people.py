from app.detect import classify
from app.people.enrich import available_actions, seed_value
from app.people.keep import is_relevant
from app.people.suggest import attached_profile, candidates


def test_ip_is_not_a_phone():
    result = classify("202.83.232.198")
    modules = [item["module"] for item in result["matches"]]
    assert result["detected"] == "ip"
    assert "phone" not in modules


def test_swiss_number_is_phone():
    assert classify("+41446681800")["detected"] == "phone"


def test_rate_limit_is_not_relevant():
    assert is_relevant("rate_limit", "reddit") is False


def test_email_is_relevant():
    assert is_relevant("email", "a@b.com") is True


def test_candidates_match_similar_username():
    profile = {"id": "p1", "title": "Test", "usernames": ["test"]}
    found = candidates("testing", [profile])
    assert any(item["id"] == profile["id"] for item in found)


def test_attached_profile_without_overlap():
    profile = {"id": "p1", "title": "Other", "usernames": ["unrelated"]}
    assert attached_profile("testing", [profile]) is None


def test_seed_value_username():
    assert seed_value({"usernames": ["ada"]}, "username") == "ada"


def test_available_actions_social_without_phone():
    actions = available_actions({"usernames": ["ada"], "phones": []})
    ids = [item["id"] for item in actions]
    assert "social" in ids
    assert "phone" not in ids
