from pydantic import BaseModel, Field
from typing import List, Optional

# --- Sub-Schema cho từng Từ vựng ---
class WordDetailResponse(BaseModel):
    id: str
    word: str                                               
    word_type: str                                          
    meaning: Optional[str] = None                           
    ipa: Optional[str] = None                               
    example_sentence: Optional[str] = None                  
    image_url: Optional[str] = None                         
    learning_status: Optional[str] = "LEARNING"             # "LEARNING", "MASTERED", "NEEDS_REVIEW"

# --- Schema Chính Trả Về Bộ Từ Vựng ---
class VocabularyCollectionResponse(BaseModel):
    id: str
    title: str                                              #
    description: Optional[str] = None                       
    topic: str                                              
    language: str                                           
    is_official: bool                                       
    total_learners: int                                     
    
    # Tiến độ cá nhân trong bộ từ này (nếu user đã học)
    accuracy_percentage: float = 0.0                        
    study_time_seconds: int = 0                             
    
    # Danh sách từ vựng chi tiết
    words_list: List[WordDetailResponse]                    #[cite: 13, 18]




# --- Request Cập nhật trạng thái từng từ ---
class UpdateWordStatusRequest(BaseModel):
    collection_id: str                                      
    word: str                                               
    status: str = Field(..., pattern="^(LEARNING|MASTERED|NEEDS_REVIEW)$") 

# --- Request Cập nhật Tiến độ chung bộ từ ---
class UpdateCollectionProgressRequest(BaseModel):
    collection_id: str                                      
    accuracy_percentage: float = Field(..., ge=0, le=100)   
    study_time_seconds: int = Field(..., ge=0)              

# --- Response Trả về ---
class VocabularyProgressResponse(BaseModel):
    message: str = "Progress updated successfully"
    user_id: str                                            
    collection_id: str                                      
    total_mastered: int
    total_learning: int
    accuracy_percentage: float                              