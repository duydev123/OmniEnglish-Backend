import pytest

@pytest.mark.asyncio
async def test_reading_flow_integration(client):
    # 1. Seed reading passages
    seed_res = await client.post("/api/v1/seed/seed-reading-passages")
    assert seed_res.status_code == 200
    seed_data = seed_res.json()
    assert len(seed_data["data"]) > 0
    passage_id = seed_data["data"][0]["passage_id"]

    # 2. Get list of passages
    list_res = await client.get("/api/v1/reading/passages")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert len(list_data["items"]) > 0


    # 3. Get passage details
    detail_res = await client.get(f"/api/v1/reading/passages/{passage_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["id"] == passage_id

    # 4. Start reading session
    start_res = await client.get(f"/api/v1/reading/passages/{passage_id}/start")
    assert start_res.status_code == 200
    start_data = start_res.json()
    assert "session_id" in start_data
    session_id = start_data["session_id"]

    # 5. Save draft
    draft_payload = {
        "time_remaining_seconds": 1200,
        "user_answers": {
            "q1": "A",
            "q2": "B"
        }
    }
    save_draft_res = await client.patch(f"/api/v1/reading/sessions/{session_id}/draft", json=draft_payload)
    assert save_draft_res.status_code == 200

    # 6. Get draft
    get_draft_res = await client.get(f"/api/v1/reading/sessions/{session_id}/draft")
    assert get_draft_res.status_code == 200
    get_draft_data = get_draft_res.json()
    assert get_draft_data["user_answers"]["q1"] == "A"

    # 7. Bookmark vocabulary
    vocab_payload = {
        "word": "ubiquitous",
        "definition": "present, appearing, or found everywhere.",
        "context_sentence": "Computers are ubiquitous in modern society."
    }
    vocab_res = await client.post(f"/api/v1/reading/sessions/{session_id}/vocabulary", json=vocab_payload)
    assert vocab_res.status_code == 200

    # 8. Submit answers
    submit_payload = {
        "time_remaining_seconds": 1100,
        "user_answers": {
            "q1": "A",
            "q2": "B"
        }
    }
    submit_res = await client.post(f"/api/v1/reading/sessions/{session_id}/submit", json=submit_payload)
    assert submit_res.status_code == 200

    # 9. Get session details
    session_res = await client.get(f"/api/v1/reading/sessions/{session_id}")
    assert session_res.status_code == 200

    # 10. Get review
    review_res = await client.get(f"/api/v1/reading/sessions/{session_id}/review")
    assert review_res.status_code == 200

    # 11. Get history for user
    history_res = await client.get("/api/v1/reading/users/test_user_001/history")
    assert history_res.status_code == 200

    # 12. Get stats
    stats_res = await client.get("/api/v1/reading/users/test_user_001/stats")
    assert stats_res.status_code == 200

    # 13. Delete session
    delete_res = await client.delete(f"/api/v1/reading/sessions/{session_id}")
    assert delete_res.status_code == 200
