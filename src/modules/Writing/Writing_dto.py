from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

# --- Prompt Schemas ---
class WritingPromptResponse(BaseModel):
    id: str
    title: str
    task_type: str                                 # "WITH_GRAPH" or "WITHOUT_GRAPH"
    task_description: str
    reference_image_url: Optional[str] = None
    ref_id: Optional[str] = None
    time_limit_minutes: int = 40
    word_count_target: int = 250
    suggested_structure: List[Dict[str, Any]] = Field(default_factory=list)
    advanced_vocabulary: List[str] = Field(default_factory=list)
    user_status: Optional[str] = None
    draft_content: Optional[str] = None
    time_spent_seconds: Optional[int] = None


# --- AI Assistance Requests & Responses (UC-09, UC-10, UC-11) ---
class AIAssistanceRequest(BaseModel):
    prompt_id: str
    action: str                                    # "OUTLINE", "COLLOCATIONS", "SAMPLE_ESSAY"
    user_notes: Optional[str] = None
    difficulty: Optional[str] = Field(default="medium")
    
class AIOutlineSection(BaseModel):
    title: str                                     # e.g., "Introduction"
    sub_points: List[str]                          # e.g., ["Hook: ...", "Thesis statement: ..."]

class AIOutlineResponse(BaseModel):
    status: str = "success"
    prompt_id: str
    outline: List[AIOutlineSection]

class AICollocationItem(BaseModel):
    word: str
    basic_equivalent: str = Field(default="", description="Simple word/phrase it replaces")
    meaning_en: str
    meaning_vi: str
    example: str

class AICollocationGroup(BaseModel):
    category: str
    items: List[AICollocationItem]

class AICollocationsResponse(BaseModel):
    status: str = "success"
    prompt_id: str
    suggestions: List[AICollocationGroup]
    difficulty: Optional[str] = Field(default="medium")

class AISampleEssayResponse(BaseModel):
    status: str = "success"
    prompt_id: str
    sample_title: str
    full_text: str
    structure_annotations: List[Dict[str, Any]]     
    good_practices: List[str]

# --- Draft Request & Response ---
class WritingDraftRequest(BaseModel):
    prompt_id: str
    essay_content: str = ""
    word_count: int = Field(default=0, ge=0)
    time_spent_seconds: int = Field(default=0, ge=0)

class WritingDraftResponse(BaseModel):
    session_id: str
    status: str = "DRAFT"
    message: str = "Draft saved successfully"

# --- Review Schemas (UC-13, UC-14) ---
class HighlightSpan(BaseModel):
    text: str
    type: str                                      # "GRAMMAR", "WORD_CHOICE", "COHERENCE"
    feedback_index: int

class DetailedFeedback(BaseModel):
    category: str                                  # "Grammar", "Vocabulary", "Coherence"
    original: str
    correction: str
    explanation: str
    rule: Optional[str] = None
    similar_examples: Optional[List[str]] = None

class ImprovementComparison(BaseModel):
    category: str                                  # "Grammar", "Vocabulary", "Structural Fix"
    original: str
    improved: str

class Milestone(BaseModel):
    date: str
    title: str

class WritingSubmitResponse(BaseModel):
    session_id: str
    status: str = "REVIEWED"                       # "DRAFT", "SUBMITTED", "REVIEWED"
    prompt_id: str
    topic_title: str
    essay_content: str
    word_count: int
    time_spent_seconds: int
    
    # 1. Band Scores (1.0 - 9.0)
    overall_score: float                           # e.g., 7.5
    potential_score: float                         # e.g., 8.0
    general_summary: str
    
    task_achievement_score: float                  # Task Response (25%)
    coherence_cohesion_score: float                # Coherence & Cohesion (25%)
    lexical_resource_score: float                  # Lexical Resource (25%)
    grammar_accuracy_score: float                  # Grammar Range & Accuracy (25%)

    # 2. Render Highlight markers on essay
    highlight_spans: List[HighlightSpan]

    # 3. Detailed feedback list
    detailed_feedbacks: List[DetailedFeedback]
    
    # 4. Side-by-side Key Improvements & Positive feedback & Next steps
    improvements_comparison: List[ImprovementComparison]
    positive_feedback: List[str]
    actionable_next_steps: List[str]
    achieved_milestones: List[Milestone]

# --- Improved Essay Sample Schema (UC-15) ---
class ImprovedEssaySampleResponse(BaseModel):
    status: str = "success"
    session_id: str
    original_essay: str
    improved_essay: str
    improvements_explanation: List[str]

class AnswerQuestionPayload(BaseModel):
    question: str