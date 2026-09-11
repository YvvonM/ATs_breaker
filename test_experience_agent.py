import asyncio
from agents.resume_rewriting.experience_agent import process_experience
from infrastructure.redis_service import redis_service

async def test_experience_agent():
    print("=" * 60)
    print("Testing Experience Agent")
    print("=" * 60)
    
    # Sample job description
    job_description = """
    Senior Software Engineer - Backend

    We are looking for a Senior Software Engineer to join our backend team.
    
    Responsibilities:
    - Design and implement high-performance REST APIs using FastAPI
    - Build scalable microservices architecture with Docker and Kubernetes
    - Optimize database queries and caching strategies with Redis and PostgreSQL
    - Lead technical decisions and mentor junior engineers
    
    Requirements (Must-Have):
    - 5+ years of Python development experience
    - Strong experience with FastAPI or similar frameworks
    - Experience with Redis and PostgreSQL
    - Docker and container orchestration (Kubernetes)
    
    Nice-to-Have:
    - Experience with AWS cloud services
    - GraphQL experience
    - Knowledge of event-driven architectures
    """
    
    # Sample user experience section
    experience_section = """
    ### Professional Experience
    
    **Senior Software Developer** | Tech Solutions Inc
    *2019 - Present | New York, NY*
    - Built web applications using Django and PostgreSQL
    - Designed REST APIs for internal and external use
    - Managed deployment pipelines with Docker
    - Mentored junior developers and led code reviews
    - Implemented caching with Redis to improve performance
    
    **Software Engineer** | Startup Co
    *2017 - 2019 | San Francisco, CA*
    - Developed features for a Python-based platform
    - Worked with MongoDB and Redis
    - Participated in Agile development process
    - Wrote unit tests and integration tests
    """
    
    # Extracted keywords (from keyword agent)
    keywords = [
        "Python", "FastAPI", "Redis", "PostgreSQL", 
        "Docker", "Kubernetes", "Microservices", "REST APIs",
        "AWS", "Mentoring", "Leadership"
    ]
    
    # Must-have requirements
    must_have = [
        "5+ years Python",
        "FastAPI experience",
        "Redis and PostgreSQL",
        "Docker and Kubernetes"
    ]
    
    nice_to_have = [
        "AWS",
        "GraphQL",
        "Event-driven architectures"
    ]
    
    # Generate run_id
    run_id = redis_service.get_run_id()
    print(f"Run ID: {run_id}")
    
    # Process experience section
    print("\n📝 Processing experience section...")
    result = process_experience(
        job_description=job_description,
        experience_section=experience_section,
        keywords=keywords,
        run_id=run_id,
        must_have=must_have,
        nice_to_have=nice_to_have,
    )
    
    # Print results
    print("\n" + "-" * 40)
    print("Results:")
    print("-" * 40)
    
    print(f"Status: {result.metadata.status}")
    print(f"Model: {result.metadata.model_used}")
    print(f"Execution Time: {result.metadata.execution_time:.2f}s")
    print(f"Error: {result.error or 'None'}")
    
    print("\n" + "-" * 40)
    print("Rewritten Experience Section:")
    print("-" * 40)
    print(result.content)
    
    print("\n" + "-" * 40)
    print("Structured Data:")
    print("-" * 40)
    print(f"Total Experiences: {result.structured.total_experiences}")
    print(f"Total Bullet Points: {result.structured.total_bullet_points}")
    print(f"Skills Used: {', '.join(result.structured.skills_used)}")
    print(f"Keywords Matched: {', '.join(result.structured.keywords_matched)}")
    print(f"Keywords Missing: {', '.join(result.structured.keywords_missing)}")
    print(f"Match Score: {result.structured.match_score}/100")
    
    print("\n" + "-" * 40)
    print("Experiences:")
    print("-" * 40)
    for exp in result.structured.experiences:
        print(f"\n  🏢 {exp.company}")
        print(f"  📋 {exp.title}")
        print(f"  📅 {exp.duration}")
        if exp.location:
            print(f"  📍 {exp.location}")
        print(f"  🔧 Skills: {', '.join(exp.skills_demonstrated)}")
        print("  📝 Bullet Points:")
        for bp in exp.bullet_points:
            print(f"    - {bp}")
    
    print("\n" + "=" * 60)
    print("✅ Experience Agent Test Complete!")
    print("=" * 60)
    
    return result

if __name__ == "__main__":
    asyncio.run(test_experience_agent())