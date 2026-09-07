from app.services.query_planner import plan_query


def test_plan_part_revision():
    p = plan_query("Сравни деталь 8450012345 Rev D")
    assert p["part_number"] == "8450012345"
    assert p["revision"] == "D"
    assert p["intent"] == "revision_compare"

def test_quality_core_tools_intent_is_detected():
    assert plan_query("Покажи PFMEA и Control Plan по детали 8450012345")['intent'] == 'quality_core_tools'
    assert plan_query("Есть открытые 8D рекламации?")['intent'] == 'quality_core_tools'
