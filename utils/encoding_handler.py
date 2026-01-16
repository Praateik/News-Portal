"""
Encoding Handler for UTF-8 Safety
Preserves original encoding (Devanagari, etc.) while ensuring UTF-8 compatibility
"""

import chardet
import logging

logger = logging.getLogger(__name__)


class EncodingHandler:
    """
    Handles text encoding detection and conversion
    Ensures UTF-8 output while preserving original characters
    """

    @staticmethod
    def detect_encoding(data):
        """
        Detect encoding of byte data

        Args:
            data: Byte data

        Returns:
            str: Detected encoding name
        """
        try:
            result = chardet.detect(data)
            encoding = result.get('encoding', 'utf-8')
            confidence = result.get('confidence', 0.0)

            # If confidence is low, default to utf-8
            if confidence < 0.7:
                logger.warning(
                    f"Low encoding confidence ({confidence:.2f}), defaulting to utf-8")
                encoding = 'utf-8'

            # Normalize encoding names
            encoding_map = {
                'ISO-8859-1': 'latin1',
                'Windows-1252': 'latin1',
            }
            encoding = encoding_map.get(encoding, encoding)

            return encoding
        except Exception as e:
            logger.warning(
                f"Encoding detection failed: {e}, defaulting to utf-8")
            return 'utf-8'

    @staticmethod
    def to_utf8(text_or_bytes, encoding=None):
        """
        Convert text or bytes to UTF-8 string

        Args:
            text_or_bytes: Text string or byte data
            encoding: Known encoding (optional, will detect if not provided)

        Returns:
            str: UTF-8 encoded string
        """
        if isinstance(text_or_bytes, str):
            # Already a string, ensure it's valid UTF-8
            try:
                # Validate UTF-8
                text_or_bytes.encode('utf-8')
                return text_or_bytes
            except UnicodeEncodeError:
                # Invalid UTF-8, try to fix
                return text_or_bytes.encode('utf-8', errors='replace').decode('utf-8')

        elif isinstance(text_or_bytes, bytes):
            # Byte data, decode to string
            if encoding is None:
                encoding = EncodingHandler.detect_encoding(text_or_bytes)

            try:
                return text_or_bytes.decode(encoding, errors='replace')
            except (UnicodeDecodeError, LookupError) as e:
                logger.warning(
                    f"Failed to decode with {encoding}: {e}, trying utf-8")
                try:
                    return text_or_bytes.decode('utf-8', errors='replace')
                except Exception as e2:
                    logger.error(f"UTF-8 decode also failed: {e2}")
                    # Last resort: replace errors
                    return text_or_bytes.decode('utf-8', errors='replace')

        else:
            # Convert to string first
            return str(text_or_bytes)

    @staticmethod
    def clean_text(text):
        """
        Clean text while preserving Unicode characters (Devanagari, etc.)

        Args:
            text: Input text

        Returns:
            str: Cleaned UTF-8 text
        """
        text = EncodingHandler.to_utf8(text)

        # Remove null bytes
        text = text.replace('\x00', '')

        # Normalize whitespace (but preserve line breaks)
        import re
        text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces/tabs
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Multiple blank lines

        return text.strip()
