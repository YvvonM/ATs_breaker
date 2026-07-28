# test_groq_model.py (updated)
import os
import asyncio
import json
import re
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

async def test_model():
    llm = ChatGroq(
        model="qwen/qwen3.6-27b",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.0,
        max_tokens=1024,
        reasoning_format="hidden",  # Try to hide reasoning
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You extract structured data. Return only JSON."),
        ("human", 'Extract company and role from: "Notion is hiring ML Engineers. Remote. Apply at jobs@notion.so"')
    ])
    
    chain = prompt | llm
    
    print("Testing model...")
    result = await chain.ainvoke({})
    
    print(f"Result type: {type(result)}")
    print(f"Result: {repr(str(result)[:500])}")
    
    # Extract content from AIMessage
    if hasattr(result, 'content'):
        content = result.content
        print(f"\nContent type: {type(content)}")
        print(f"Content: {repr(content[:500])}")
        
        # Strip <think> tags
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
        content = content.strip()
        print(f"\nAfter stripping think tags: {repr(content[:500])}")

if __name__ == "__main__":
    asyncio.run(test_model())