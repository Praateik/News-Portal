"""
Language Detection Utility
Detects language with confidence scoring and preserves original encoding
"""

from langdetect import detect, detect_langs, LangDetectException
import logging
import re

logger = logging.getLogger(__name__)


class LanguageDetector:
    """
    Language detection with confidence scoring
    Supports 55+ languages including Devanagari scripts
    """
    
    # Language mappings for common cases
    LANGUAGE_MAP = {
        'ne': 'Nepali',  # Nepali (Devanagari)
        'hi': 'Hindi',   # Hindi (Devanagari)
        'en': 'English',
        'zh': 'Chinese',
        'ja': 'Japanese',
        'ko': 'Korean',
        'ar': 'Arabic',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
    }
    
    def __init__(self, min_confidence=0.5):
        """
        Initialize language detector
        
        Args:
            min_confidence: Minimum confidence threshold (0.0-1.0)
        """
        self.min_confidence = min_confidence
    
    def detect_language(self, text, default='en'):
        """
        Detect language from text
        
        Args:
            text: Text to analyze (UTF-8 encoded)
            default: Default language if detection fails
            
        Returns:
            dict: {
                'language': str (ISO 639-1 code),
                'confidence': float (0.0-1.0),
                'language_name': str
            }
        """
        if not text or len(text.strip()) < 10:
            logger.warning("Text too short for language detection")
            return {
                'language': default,
                'confidence': 0.0,
                'language_name': self.LANGUAGE_MAP.get(default, default)
            }
        
        try:
            # Clean text (remove URLs, special chars)
            cleaned_text = self._clean_text(text)
            
            if len(cleaned_text) < 10:
                return {
                    'language': default,
                    'confidence': 0.0,
                    'language_name': self.LANGUAGE_MAP.get(default, default)
                }
            
            # Detect language
            detected_lang = detect(cleaned_text)
            
            # Get confidence scores
            lang_probs = detect_langs(cleaned_text)
            confidence = lang_probs[0].prob if lang_probs else 0.5
            
            # Validate confidence
            if confidence < self.min_confidence:
                logger.warning(f"Low confidence ({confidence:.2f}) for language detection")
                detected_lang = default
                confidence = 0.5
            
            language_name = self.LANGUAGE_MAP.get(detected_lang, detected_lang)
            
            return {
                'language': detected_lang,
                'confidence': round(confidence, 2),
                'language_name': language_name
            }
            
        except LangDetectException as e:
            logger.warning(f"Language detection failed: {e}")
            return {
                'language': default,
                'confidence': 0.0,
                'language_name': self.LANGUAGE_MAP.get(default, default)
            }
        except Exception as e:
            logger.error(f"Error in language detection: {e}")
            return {
                'language': default,
                'confidence': 0.0,
                'language_name': self.LANGUAGE_MAP.get(default, default)
            }
    
    def _clean_text(self, text):
        """
        Clean text for better language detection
        
        Args:
            text: Raw text
            
        Returns:
            str: Cleaned text
        """
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep Unicode characters (Devanagari, etc.)
        # This preserves non-Latin scripts
        text = text.strip()
        
        return text
    
    def detect_multiple(self, texts, default='en'):
        """
        Detect language from multiple text samples
        Uses majority voting for better accuracy
        
        Args:
            texts: List of text samples
            default: Default language
            
        Returns:
            dict: Detection result with majority language
        """
        if not texts:
            return self.detect_language('', default)
        
        # Detect language for each text
        detections = []
        for text in texts:
            if text:
                det = self.detect_language(text, default)
                detections.append(det)
        
        if not detections:
            return self.detect_language('', default)
        
        # Find most common language
        from collections import Counter
        languages = [d['language'] for d in detections]
        lang_counts = Counter(languages)
        majority_lang = lang_counts.most_common(1)[0][0]
        
        # Calculate average confidence for majority language
        majority_detections = [d for d in detections if d['language'] == majority_lang]
        avg_confidence = sum(d['confidence'] for d in majority_detections) / len(majority_detections)
        
        return {
            'language': majority_lang,
            'confidence': round(avg_confidence, 2),
            'language_name': self.LANGUAGE_MAP.get(majority_lang, majority_lang),
            'sample_count': len(detections)
        }






