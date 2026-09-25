"""
End-to-end verification script for SyllabusAI FastAPI backend.
Tests:
1. Health and root endpoints
2. Subject creation & retrieval
3. Teacher class creation & listing
4. Progress tracking and toggle
5. AI Chat error handling / response
"""
import sys
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import Subject, Unit, Topic, TeacherClass, TopicProgress

client = TestClient(app)

def test_full_flow():
    print("1. Testing root and health...")
    r = client.get("/")
    assert r.status_code == 200, f"Root failed: {r.text}"
    r = client.get("/health")
    assert r.status_code == 200, f"Health failed: {r.text}"
    print("   [PASS] Root and health OK")

    print("2. Seeding test subject...")
    db = SessionLocal()
    # Check if exists
    sub = db.query(Subject).filter(Subject.subject_code == "CS301").first()
    if not sub:
        sub = Subject(
            subject_code="CS301",
            subject_name="Data Structures and Algorithms",
            semester="III",
            credits=4,
            lecture_hours=3,
            tutorial_hours=1,
            practical_hours=0,
            course_type="Professional Core",
            department="Computer Science",
            course_objectives=["Understand basic data structures", "Analyze algorithm complexity"],
            course_outcomes=[{"code": "CO1", "description": "Implement linear data structures"}],
        )
        db.add(sub)
        db.flush()

        unit1 = Unit(subject_id=sub.id, unit_number=1, unit_title="Linear Data Structures", hours=9)
        db.add(unit1)
        db.flush()

        topic1 = Topic(unit_id=unit1.id, topic_order=1, topic_name="Arrays and Dynamic Arrays")
        topic2 = Topic(unit_id=unit1.id, topic_order=2, topic_name="Singly and Doubly Linked Lists")
        topic3 = Topic(unit_id=unit1.id, topic_order=3, topic_name="Stack and Queue Implementations")
        db.add_all([topic1, topic2, topic3])

        unit2 = Unit(subject_id=sub.id, unit_number=2, unit_title="Non-Linear Data Structures", hours=9)
        db.add(unit2)
        db.flush()

        topic4 = Topic(unit_id=unit2.id, topic_order=1, topic_name="Binary Trees and BST")
        topic5 = Topic(unit_id=unit2.id, topic_order=2, topic_name="Graph Representations and Traversals")
        db.add_all([topic4, topic5])

        db.commit()
        db.refresh(sub)
    db.close()
    print("   [PASS] Subject seeded successfully")

    print("3. Testing subject search and retrieval...")
    r = client.get("/api/subjects/search?q=Data Structures")
    assert r.status_code == 200, f"Search failed: {r.text}"
    results = r.json()["results"]
    assert len(results) > 0, "No results returned for search"
    subject_id = results[0]["id"]
    print(f"   [PASS] Search returned {len(results)} match(es), ID: {subject_id}")

    r = client.get(f"/api/subjects/{subject_id}")
    assert r.status_code == 200, f"Get subject failed: {r.text}"
    subj_data = r.json()
    assert len(subj_data["units"]) >= 2
    assert len(subj_data["units"][0]["topics"]) >= 3
    print(f"   [PASS] Full subject details verified ({len(subj_data['units'])} units)")

    print("4. Testing teacher class creation...")
    r = client.post("/api/classes", json={
        "subject_id": subject_id,
        "batch": "2025-2029",
        "department": "Computer Science & Engineering",
        "section": "A",
        "semester": "III"
    })
    assert r.status_code == 200, f"Create class failed: {r.text}"
    class_data = r.json()
    class_id = class_data["id"]
    print(f"   [PASS] Created Teacher Class ID: {class_id}")

    print("5. Testing progress listing...")
    r = client.get(f"/api/classes/{class_id}/progress")
    assert r.status_code == 200, f"Get progress failed: {r.text}"
    progress_list = r.json()
    assert len(progress_list) >= 5, f"Expected at least 5 topics, got {len(progress_list)}"
    target_topic = progress_list[0]
    print(f"   [PASS] Retrieved {len(progress_list)} topics for class tracker")

    print("6. Testing topic toggle...")
    r = client.patch(f"/api/classes/{class_id}/topics/{target_topic['topic_id']}/progress", json={
        "is_completed": True
    })
    assert r.status_code == 200, f"Toggle topic failed: {r.text}"
    assert r.json()["is_completed"] is True
    print(f"   [PASS] Marked topic '{target_topic['topic_name']}' as completed")

    # Verify class percentage updated
    r = client.get(f"/api/classes/{class_id}")
    assert r.status_code == 200
    updated_class = r.json()
    assert updated_class["completed_topics"] == 1
    assert updated_class["progress_percent"] > 0
    print(f"   [PASS] Class progress percentage updated to {updated_class['progress_percent']}%")

    print("7. Testing AI Assistant chat validation...")
    r = client.post("/api/ai/chat", json={
        "teacher_class_id": class_id,
        "topic_id": target_topic["topic_id"],
        "messages": [{"role": "user", "content": "How do I teach this topic?"}]
    })
    assert r.status_code == 200, f"AI chat failed: {r.text}"
    reply = r.json()["reply"]
    assert len(reply) > 0
    print(f"   [PASS] AI chat responded cleanly (length: {len(reply)})")

    print("\n=== ALL 7 TEST SUITES PASSED CLEANLY! ===")

if __name__ == "__main__":
    test_full_flow()
