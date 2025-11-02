import os
import re
import requests
from config import Config
from models import db, KnowledgeBaseEntry, AIResponseRating
from flask import current_app

class AIService:
    def __init__(self):
        self.config = Config()
        self.local_kb_path = self.config.KNOWLEDGE_BASE_PATH
        
    def search_local_knowledge_base(self, query):
        """
        Search the local knowledge base text file first.
        Returns answer if found, None otherwise.
        """
        if not os.path.exists(self.local_kb_path):
            return None
        
        try:
            with open(self.local_kb_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple keyword matching - can be enhanced
            query_lower = query.lower()
            
            # Remove common stop words for better matching
            stop_words = {'what', 'is', 'the', 'a', 'an', 'how', 'do', 'does', 'can', 'i', 'you', 'we', 'are', 'to', 'for', 'of', 'with', 'on', 'at', 'by', 'from', 'as', 'about'}
            query_words = [w for w in query_lower.split() if w not in stop_words and len(w) > 2]
            
            if not query_words:
                query_words = query_lower.split()
            
            # Try to find paragraphs that contain query keywords
            paragraphs = content.split('\n\n')
            best_matches = []
            
            for para in paragraphs:
                para_lower = para.lower()
                # Count how many query words appear in this paragraph
                matches = sum(1 for word in query_words if word in para_lower)
                if matches > 0:
                    best_matches.append((matches, para.strip()))
            
            if best_matches:
                # Return the best matching paragraph(s)
                best_matches.sort(reverse=True, key=lambda x: x[0])
                # Return top 1-2 paragraphs if they have good match scores
                top_match = best_matches[0]
                if top_match[0] >= len(query_words) * 0.5:  # At least 50% of keywords matched
                    if len(best_matches) > 1 and best_matches[1][0] >= len(query_words) * 0.3:
                        return f"{top_match[1]}\n\n{best_matches[1][1]}"
                    return top_match[1]
            
            # Fallback: search sentence by sentence
            sentences = re.split(r'[.!?]\s+', content)
            sentence_matches = []
            
            for sentence in sentences:
                sentence_lower = sentence.lower()
                matches = sum(1 for word in query_words if word in sentence_lower)
                if matches > 0:
                    sentence_matches.append((matches, sentence.strip()))
            
            if sentence_matches:
                sentence_matches.sort(reverse=True, key=lambda x: x[0])
                # Return top 2-3 sentences if good match
                if sentence_matches[0][0] >= 2:
                    result = '. '.join([s[1] for s in sentence_matches[:3]])
                    return result + '.' if not result.endswith('.') else result
                
        except Exception as e:
            print(f"Error reading knowledge base: {e}")
            return None
        
        return None
    
    def query_huggingface_api(self, query):
        """
        Query Hugging Face Inference API if local KB doesn't have answer.
        """
        if not self.config.HUGGINGFACE_API_KEY:
            return "I couldn't find information about that in our knowledge base. For advanced AI responses, please configure a Hugging Face API key in the settings. Alternatively, you can ask questions about our menu, ordering process, delivery times, or restaurant services."
        
        try:
            headers = {
                "Authorization": f"Bearer {self.config.HUGGINGFACE_API_KEY}"
            }
            
            # Prepare prompt
            prompt = f"Restaurant customer service question: {query}. Answer helpfully and concisely."
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_length": 200,
                    "temperature": 0.7
                }
            }
            
            response = requests.post(
                self.config.HUGGINGFACE_API_URL,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                # Handle different response formats
                if isinstance(result, list) and len(result) > 0:
                    if isinstance(result[0], dict) and 'generated_text' in result[0]:
                        return result[0]['generated_text']
                    elif isinstance(result[0], str):
                        return result[0]
                elif isinstance(result, dict):
                    if 'generated_text' in result:
                        return result['generated_text']
                    elif 'answer' in result:
                        return result['answer']
                
                return str(result)
            else:
                return f"I'm sorry, I encountered an error. Please try again later. (Error: {response.status_code})"
                
        except requests.exceptions.Timeout:
            return "I'm sorry, the service timed out. Please try again."
        except requests.exceptions.RequestException as e:
            return f"I'm sorry, I couldn't process your request. Please contact support."
        except Exception as e:
            return f"An error occurred: {str(e)}"
    
    def get_ai_response(self, query, user_id=None):
        """
        Main method to get AI response:
        1. Search local knowledge base first
        2. If no match, use Hugging Face API
        3. Store the interaction for rating
        """
        source = 'local'
        answer = self.search_local_knowledge_base(query)
        
        if not answer:
            # Try Hugging Face API if available
            if self.config.HUGGINGFACE_API_KEY:
                answer = self.query_huggingface_api(query)
                source = 'llm'
            else:
                # Better fallback message when no API key
                answer = f"I couldn't find specific information about '{query}' in our knowledge base. The local AI service (Hugging Face) is not configured. You can ask me about:\n\n- Our menu items and prices\n- How to place orders\n- Delivery information\n- VIP status and benefits\n- How to file complaints or compliments\n- Chef ratings\n\nOr contact our support team for more specific questions."
                source = 'local'  # Still mark as local since we're not using external API
        
        # Store the interaction for potential rating
        # Check if similar KB entry exists
        kb_entry = None
        if source == 'local':
            # Try to find or create KB entry
            kb_entry = KnowledgeBaseEntry.query.filter_by(question=query).first()
            if not kb_entry:
                kb_entry = KnowledgeBaseEntry(
                    question=query,
                    answer=answer,
                    rating=0.0,
                    rating_count=0
                )
                db.session.add(kb_entry)
                db.session.commit()
        
        # Create rating record
        rating_record = AIResponseRating(
            kb_entry_id=kb_entry.id if kb_entry else None,
            user_id=user_id,
            query=query,
            response=answer,
            rating=0,  # Unrated initially
            source=source
        )
        db.session.add(rating_record)
        db.session.commit()
        
        return {
            'answer': answer,
            'source': source,
            'rating_id': rating_record.id
        }
    
    def rate_ai_response(self, rating_id, rating_value):
        """
        Rate an AI response (0-5 stars).
        If 0 stars, flag the KB entry for manager review.
        """
        if rating_value < 0 or rating_value > 5:
            return False
        
        rating_record = db.session.get(AIResponseRating, rating_id)
        if not rating_record:
            return False
        
        rating_record.rating = rating_value
        db.session.commit()
        
        # If rating is 0 and there's a KB entry, flag it
        if rating_value == 0 and rating_record.kb_entry_id:
            kb_entry = db.session.get(KnowledgeBaseEntry, rating_record.kb_entry_id)
            if kb_entry:
                kb_entry.flagged = True
                
                # Update average rating
                all_ratings = AIResponseRating.query.filter(
                    AIResponseRating.kb_entry_id == kb_entry.id,
                    AIResponseRating.rating > 0  # Only count non-zero ratings for average
                ).all()
                
                if all_ratings:
                    kb_entry.rating = sum(r.rating for r in all_ratings) / len(all_ratings)
                    kb_entry.rating_count = len(all_ratings)
                
                db.session.commit()
        
        return True

def get_ai_service():
    """Factory function to get AI service instance."""
    return AIService()

