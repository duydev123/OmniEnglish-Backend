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
    title: str                                              
    description: Optional[str] = None                       
    topic: str                                              
    language: str                                           
    is_official: bool                                       
    total_learners: int                                     
    total_words: int = 0
    
    # Tiến độ cá nhân trong bộ từ này (nếu user đã học)
    accuracy_percentage: float = 0.0                        
    study_time_seconds: int = 0                             
    
    # Danh sách từ vựng chi tiết
    words_list: Optional[List[WordDetailResponse]] = Field(default_factory=list)                    

# --- Request Cập nhật trạng thái từng từ ---
class UpdateWordStatusRequest(BaseModel):
    collection_id: str                                      
    word_id: Optional[str] = None
    word: Optional[str] = None
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

class CreateCollectionRequest(BaseModel):
    title: str = Field(..., min_length=1)
    language: str = Field(default="Anh-Mỹ")
    description: Optional[str] = None

class UpdateCollectionRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = None

# --- DTO: Thêm 1 từ vựng vào bộ (Dựa theo chi tiết thẻ Flashcard) ---
class AddWordRequest(BaseModel):
    word: str
    word_type: Optional[str] = None
    ipa: Optional[str] = None       
    meaning: str                    
    example_sentence: Optional[str] = None
    image_url: Optional[str] = None

# --- DTO: Cập nhật 1 từ vựng ---
class UpdateWordRequest(BaseModel):
    word: Optional[str] = None
    word_type: Optional[str] = None
    ipa: Optional[str] = None       
    meaning: Optional[str] = None                    
    example_sentence: Optional[str] = None
    image_url: Optional[str] = None

# --- DTO: Cập nhật một từ trong danh sách Bulk Update ---
class BulkUpdateWordItem(BaseModel):
    id: str
    word: Optional[str] = None
    word_type: Optional[str] = None
    ipa: Optional[str] = None
    meaning: Optional[str] = None
    example_sentence: Optional[str] = None
    image_url: Optional[str] = None

# --- DTO: Cập nhật hàng loạt từ vựng (Bulk Edit Words) ---
class BulkUpdateWordsRequest(BaseModel):
    words: List[BulkUpdateWordItem]

# --- DTO: Thêm hàng loạt từ vựng (Bulk Add) ---
class BulkAddWordsRequest(BaseModel):
    words: List[AddWordRequest]

class PasteTextRequest(BaseModel):
    raw_text: str = Field(..., min_length=1)