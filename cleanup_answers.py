#!/usr/bin/env python3
"""
Cleanup script to remove duplicate answers from the database.
This script identifies and removes answers that are duplicates based on question_id, answer_text, and is_correct.
"""

from app import app, db
from models import Answer, Question, ParticipantAnswer

def cleanup_duplicate_answers():
    """Remove duplicate answers from the database"""
    
    with app.app_context():
        print("Starting cleanup of duplicate answers...")
        
        # Get all questions
        questions = Question.query.all()
        total_deleted = 0
        
        for question in questions:
            # Get all answers for this question
            answers = Answer.query.filter_by(question_id=question.question_id).all()
            
            if len(answers) <= 1:
                continue  # No duplicates possible
            
            # Group answers by text and correctness to find duplicates
            answer_groups = {}
            
            for answer in answers:
                key = (answer.answer_text, answer.is_correct)
                if key not in answer_groups:
                    answer_groups[key] = []
                answer_groups[key].append(answer)
            
            # For each group with duplicates, keep the first one and delete the rest
            for key, answer_list in answer_groups.items():
                if len(answer_list) > 1:
                    print(f"\nQuestion {question.question_id} ('{question.question_text[:50]}...'):")
                    print(f"  Found {len(answer_list)} duplicates for: '{key[0]}' (Correct: {key[1]})")
                    
                    # Keep the first answer, delete the rest
                    for answer_to_delete in answer_list[1:]:
                        try:
                            # Delete associated participant answers first
                            ParticipantAnswer.query.filter_by(answer_id=answer_to_delete.answer_id).delete()
                            print(f"    Deleted participant answers for answer_id {answer_to_delete.answer_id}")
                            
                            # Delete the answer
                            db.session.delete(answer_to_delete)
                            total_deleted += 1
                            print(f"    Deleted duplicate answer_id {answer_to_delete.answer_id}")
                        except Exception as e:
                            print(f"    ERROR deleting answer_id {answer_to_delete.answer_id}: {str(e)}")
                            db.session.rollback()
                            return False
        
        try:
            db.session.commit()
            print(f"\n✓ Successfully deleted {total_deleted} duplicate answers!")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"\n✗ Error committing changes: {str(e)}")
            return False

if __name__ == '__main__':
    success = cleanup_duplicate_answers()
    exit(0 if success else 1)
