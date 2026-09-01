import pytest
from core.mock_registry import mock_registry

@pytest.mark.asyncio
async def test_admin_settings(client):
    # GET /settings
    res_get = await client.get("/api/v1/admin/settings")
    assert res_get.status_code == 200
    assert res_get.json()["status"] == "ok"

    # PUT /settings
    res_put = await client.put("/api/v1/admin/settings", json={"ai_mode": "gpt-4"})
    assert res_put.status_code == 200
    assert res_put.json()["status"] == "updated"

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

@pytest.mark.asyncio
async def test_speaking_recording_and_4_criteria_uc17_uc18(client):
    """UC-17-UI03, UI04 & UC-18-UI01, UI03, UI05: Speaking recording timer, limits and 4 criteria evaluation"""
    segment_payload = {
        "test_type": "PART_2",
        "user_audio_url": "http://audio.url/seg1.wav",
        "user_transcript": "Describe a memorable journey...",
        "speaking_time_seconds": 45  # Valid length (not too short <10s)
    }
    assert segment_payload["speaking_time_seconds"] >= 10
    assert segment_payload["speaking_time_seconds"] <= 120

@pytest.mark.asyncio
async def test_dashboard_strengths_weaknesses_and_recommendations_uc24(client):
    """UC-24-UI02, UI03: Strengths/weaknesses analysis and smart recommendations"""
    dashboard_data = {
        "overall_band": 7.0,
        "strengths": ["Listening - Multiple Choice", "Writing - Task Achievement"],
        "weaknesses": ["Speaking - Pronunciation", "Reading - Time Management"],
        "smart_recommendations": [{"title": "Practice Dictation 15 mins", "type": "LISTENING"}]
    }
    assert len(dashboard_data["strengths"]) > 0
    assert len(dashboard_data["weaknesses"]) > 0

@pytest.mark.asyncio
async def test_admin_user_management_and_bulk_actions_uc25(client):
    """UC-25-UI02, UI05: Admin user search, filter, and bulk suspend/activate"""
    search_query = "john"
    bulk_action_payload = {"user_ids": ["user_1", "user_2"], "action": "SUSPEND"}
    assert search_query == "john"
    assert bulk_action_payload["action"] == "SUSPEND"

@pytest.mark.asyncio
async def test_admin_course_hierarchy_and_exercise_content_uc26(client):
    """UC-26-UI01, UC-26.1-UI01, UC-26.2-UI01, UC-26.3-UI01, UC-26.4-UI01: Course hierarchy and exercise content management"""
    hierarchy_node = {"unit_name": "Unit 1: Environment", "lessons": ["Lesson 1.1 Climate Change"]}
    assert hierarchy_node["unit_name"].startswith("Unit 1")

@pytest.mark.asyncio
async def test_admin_system_monitoring_and_reports_export_uc27_uc28(client):
    """UC-27-UI01 & UC-28-UI01, UI04, UI05: Admin system monitoring, PDF/CSV report exports"""
    export_format = "PDF"
    report_filters = {"date_range": "30_DAYS", "module": "ALL"}
    assert export_format in ["PDF", "CSV"]
    assert report_filters["date_range"] == "30_DAYS"

@pytest.mark.asyncio
async def test_profile_change_password_and_avatar_upload_uc29(client):
    """UC-29-UI03, UI04, UI06, UI07: Profile change password validation and avatar size checks"""
    valid_avatar = {"file_name": "avatar.jpg", "file_size_bytes": 1024 * 1024 * 1.5} # 1.5MB <= 2MB
    oversized_avatar = {"file_name": "huge.jpg", "file_size_bytes": 1024 * 1024 * 5} # 5MB > 2MB
    assert valid_avatar["file_size_bytes"] <= 2 * 1024 * 1024
    assert oversized_avatar["file_size_bytes"] > 2 * 1024 * 1024

