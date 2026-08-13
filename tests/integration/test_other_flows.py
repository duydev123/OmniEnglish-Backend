import pytest
from core.mock_registry import mock_registry

@pytest.mark.asyncio
async def test_admin_settings(client):
    # GET /settings
    res_get = await client.get("/api/v1/admin/settings")
    assert res_get.status_code == 200
    assert res_get.json() is None

    # PUT /settings
    res_put = await client.put("/api/v1/admin/settings", json={"ai_mode": "gpt-4"})
    assert res_put.status_code == 200
    assert res_put.json() is None

@pytest.mark.asyncio
async def test_grammar_flow(client):
    mock_registry["start_grammar_session"] = lambda topic_id: {
        "session_id": "session_g123",
        "topic_id": topic_id,
        "title": "Tenses",
        "level": "Intermediate B2",
        "guide": {
            "rule_title": "Active vs Passive",
            "rule_description": "Explanation of active and passive voice",
            "formula": "S + V + O",
            "quick_reference": []
        },
        "completed_tasks": 0,
        "total_tasks": 10,
        "questions": []
    }
    mock_registry["save_grammar_draft"] = lambda session_id, payload: {
        "session_id": session_id,
        "status": "DRAFT",
        "message": "Draft saved"
    }
    mock_registry["submit_grammar_answers"] = lambda session_id, payload: {
        "session_id": session_id,
        "status": "COMPLETED",
        "score": 4,
        "total_tasks": 5,
        "accuracy_rate": 80.0,
        "xp_earned": 10,
        "practice_time_seconds": 120,
        "detailed_results": {}
    }

    # Start
    res = await client.get("/api/v1/grammar/topics/grammar_1/start")
    assert res.status_code == 200
    assert res.json()["topic_id"] == "grammar_1"

    # Save draft
    res_save = await client.patch("/api/v1/grammar/sessions/session_123/draft", json={"user_answers": {}})
    assert res_save.status_code == 200

    # Submit
    res_sub = await client.post("/api/v1/grammar/sessions/session_123/submit", json={"user_answers": {}})
    assert res_sub.status_code == 200

    mock_registry.clear()

@pytest.mark.asyncio
async def test_writing_flow(client):
    mock_registry["get_writing_prompt"] = lambda prompt_id: {
        "id": prompt_id,
        "title": "AI Impact",
        "task_type": "TASK_2",
        "task_description": "Discuss the impact of AI...",
        "time_limit_minutes": 40,
        "word_count_target": 250,
        "suggested_structure": [],
        "advanced_vocabulary": []
    }
    mock_registry["save_writing_draft"] = lambda session_id, payload: {
        "session_id": session_id,
        "status": "DRAFT",
        "message": "Draft saved"
    }
    mock_registry["submit_writing_essay"] = lambda session_id, payload: {
        "session_id": session_id,
        "status": "REVIEWED",
        "topic_title": "AI Impact",
        "essay_content": "AI is changing the world...",
        "word_count": 260,
        "time_spent_seconds": 1800,
        "overall_score": 75,
        "task_achievement_score": 8.0,
        "lexical_resource_score": 7.5,
        "grammar_accuracy_score": 7.0,
        "coherence_cohesion_score": 7.5,
        "highlight_spans": [],
        "detailed_feedbacks": [],
        "improvements_comparison": [],
        "achieved_milestones": []
    }

    # Get prompt
    res = await client.get("/api/v1/writing/prompts/write_1")
    assert res.status_code == 200
    assert res.json()["title"] == "AI Impact"

    # Save draft
    res_save = await client.patch("/api/v1/writing/sessions/session_w1/draft", json={
        "essay_content": "draft essay",
        "word_count": 2,
        "time_spent_seconds": 10
    })
    assert res_save.status_code == 200

    # Submit
    res_sub = await client.post("/api/v1/writing/sessions/session_w1/submit", json={
        "essay_content": "submitted essay",
        "word_count": 2,
        "time_spent_seconds": 10
    })
    assert res_sub.status_code == 200

    mock_registry.clear()

@pytest.mark.asyncio
async def test_speaking_flow(client):
    mock_registry["get_speaking_prompt"] = lambda prompt_id: {
        "id": prompt_id,
        "part": "PART_1",
        "topic": "Hometown",
        "question_text": "Talk about your hometown",
        "candidate_card_bullet_points": [],
        "useful_vocabulary": [],
        "ielts_tips": [],
        "response_structure": []
    }
    mock_registry["submit_speaking_segment"] = lambda session_id, payload: {
        "session_id": session_id,
        "status": "IN_PROGRESS",
        "segment_score": 7.0,
        "realtime_feedback": "Good job"
    }
    mock_registry["complete_speaking_test"] = lambda session_id: {
        "session_id": session_id,
        "test_type": "PART_1",
        "title": "Speaking Part 1 Result",
        "duration_str": "02:00",
        "status": "COMPLETED",
        "overall_band_score": 7.0,
        "band_score_delta": 0.0,
        "percentile_rank": "Top 20%",
        "pronunciation_score": 7.0,
        "fluency_score": 7.0,
        "lexical_score": 7.0,
        "grammar_score": 7.0,
        "key_strengths": [],
        "areas_for_growth": [],
        "questions_detail": [],
        "ai_insights_summary": "Overall good",
        "detailed_criteria_feedback": [],
        "next_milestone": {},
        "recommended_resources": []
    }

    # Get prompt
    res = await client.get("/api/v1/speaking/prompts/speak_1")
    assert res.status_code == 200

    # Submit segment
    res_seg = await client.post("/api/v1/speaking/sessions/session_s1/submit-segment", json={
        "test_type": "PART_1",
        "question_text": "Talk about your hometown",
        "user_audio_url": "http://audio.url",
        "user_transcript": "My hometown is Hanoi",
        "speaking_time_seconds": 15
    })
    assert res_seg.status_code == 200

    # Complete
    res_comp = await client.post("/api/v1/speaking/sessions/session_s1/complete")
    assert res_comp.status_code == 200

    mock_registry.clear()

@pytest.mark.asyncio
async def test_vocabulary_flow(client):
    mock_registry["get_vocabulary_collection"] = lambda collection_id: {
        "id": collection_id,
        "title": "IELTS Words",
        "description": "Vocabulary for IELTS",
        "topic": "Academic",
        "language": "English",
        "is_official": True,
        "total_learners": 100,
        "accuracy_percentage": 0.0,
        "study_time_seconds": 0,
        "words_list": []
    }
    mock_registry["update_word_status"] = lambda payload: {
        "message": "Word status updated",
        "user_id": "user123",
        "collection_id": payload.collection_id,
        "total_mastered": 5,
        "total_learning": 10,
        "accuracy_percentage": 50.0
    }
    mock_registry["update_collection_progress"] = lambda payload: {
        "message": "Collection progress updated",
        "user_id": "user123",
        "collection_id": payload.collection_id,
        "total_mastered": 6,
        "total_learning": 9,
        "accuracy_percentage": 60.0
    }

    # Get collection
    res = await client.get("/api/v1/vocabulary/collections/vocab_1")
    assert res.status_code == 200

    # Update word status
    res_word = await client.post("/api/v1/vocabulary/word-status/update", json={
        "collection_id": "vocab_1",
        "word": "ubiquitous",
        "status": "MASTERED"
    })
    assert res_word.status_code == 200

    # Update collection progress
    res_col = await client.post("/api/v1/vocabulary/collection-progress/update", json={
        "collection_id": "vocab_1",
        "accuracy_percentage": 60.0,
        "study_time_seconds": 120
    })
    assert res_col.status_code == 200

    mock_registry.clear()
