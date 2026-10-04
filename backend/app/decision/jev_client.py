# In jev_client.py — update build_routing_question()

def build_routing_question(
    question_id: str,
    question_text: str,
    choices: list[str],
) -> dict[str, Any]:
    """
    OpenJev/Jev API uses 'criteria' (dict with null values), not 'choices' (list).
    This matches the /v1/systemone format for both hosted Jev and OpenJev.
    """
    return {
        "type": "choice",
        "instructions": question_text,
        "criteria": {choice: None for choice in choices},  # ← correct format
    }

# And the top-level request wraps questions in a dict keyed by question_id:
# { "model": "openjev", "state": "...", "questions": { "model_route": {...} } }
