from typing import Optional, List
from pydantic import BaseModel, Field

class KeywordSentence(BaseModel):
    sentence: str = Field(..., description="The sentence from which keywords were extracted.")
    keywords: List[str] = Field(..., description="List of keywords extracted from the sentence.")

class KeywordExtractionResult(BaseModel):
    keyword_sentences: List[KeywordSentence] = Field(..., description="List of sentences with their extracted keywords.")
    extraction_notes: str = Field(..., description="Notes about the extraction process.")
    model_used: str = Field(..., description="The model used for keyword extraction.")