from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from beanie import Document, Indexed
from pydantic import Field, BaseModel

class StructureItem(BaseModel):
    section: str            # "Introduction", "Body Paragraph 1", etc.
    guide: str              # "Hook, background of the city, and your clear stance."
    details: Optional[List[str]] = None

class SpecificError(BaseModel):
    category: str           # "Grammar", "Vocabulary", "Coherence"
    original: str           # Original text snippet
    correction: str         # Corrected text snippet
    rule: str               # Explanation/rule name
    similar: Optional[List[str]] = None

class HighlightSpanModel(BaseModel):
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    text: str               # Text snippet
    type: str               # "GRAMMAR", "WORD_CHOICE", "COHERENCE"
    feedback_index: int     # Pointer to error detail

class ImprovementComparisonModel(BaseModel):
    category: str           # "Grammar", "Vocabulary", "Structural Fix"
    original: str           # Original text snippet
    improved: str           # Improved text snippet

class MilestoneModel(BaseModel):
    date: str
    title: str

class WritingPromptModel(Document):
    title: Indexed(str)
    task_type: str = "WITHOUT_GRAPH"   # "WITH_GRAPH" or "WITHOUT_GRAPH"
    task_description: str
    reference_image_url: Optional[str] = None
    ref_id: Optional[str] = None
    time_limit_minutes: int = 40
    word_count_target: int = 250
    suggested_structure: List[Dict[str, Any]] = Field(default_factory=list)
    advanced_vocabulary: List[str] = Field(default_factory=list)
    collocation_suggestions: Optional[Dict[str, List[str]]] = None
    sample_essay: Optional[Dict[str, Any]] = None
    essay_outline: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "writing_prompts"

class WritingSubmissionModel(Document):
    user_id: Indexed(str)
    prompt_id: str
    prompt_title: str
    essay_content: str = ""
    word_count: int = 0
    time_spent_seconds: int = 0
    status: str = "DRAFT"              # "DRAFT", "SUBMITTED", "REVIEWED"
    
    # 4 IELTS Criteria & Overall Scores
    overall_score: float = 0.0         # 1.0 - 9.0
    potential_score: float = 0.0       # 1.0 - 9.0
    general_summary: str = ""
    
    task_achievement_score: float = 0.0     # 25%
    coherence_cohesion_score: float = 0.0   # 25%
    lexical_resource_score: float = 0.0     # 25%
    grammar_accuracy_score: float = 0.0     # 25%
    
    highlight_spans: List[HighlightSpanModel] = Field(default_factory=list)
    specific_errors: List[SpecificError] = Field(default_factory=list)
    improvements_comparison: List[ImprovementComparisonModel] = Field(default_factory=list)
    positive_feedback: List[str] = Field(default_factory=list)
    actionable_next_steps: List[str] = Field(default_factory=list)
    improved_essay_sample: Optional[str] = None
    achieved_milestones: List[MilestoneModel] = Field(default_factory=list)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "writing_submissions"
