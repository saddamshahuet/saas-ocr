"""Multi-language support module for document processing

Provides language detection, multilingual prompts, and language-specific processing.
"""
from typing import Dict, Optional, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class LanguageConfig:
    """Configuration for language support"""
    code: str  # ISO 639-1 code (e.g., 'en', 'es', 'fr')
    name: str
    ocr_code: str  # PaddleOCR language code
    supported: bool = True
    llm_prompt_template: Optional[str] = None


class LanguageManager:
    """Manages language detection and multilingual processing"""

    # Supported languages with their configurations
    SUPPORTED_LANGUAGES = {
        'en': LanguageConfig('en', 'English', 'en'),
        'es': LanguageConfig('es', 'Spanish', 'es'),
        'fr': LanguageConfig('fr', 'French', 'fr'),
        'de': LanguageConfig('de', 'German', 'german'),
        'it': LanguageConfig('it', 'Italian', 'it'),
        'pt': LanguageConfig('pt', 'Portuguese', 'pt'),
        'ru': LanguageConfig('ru', 'Russian', 'ru'),
        'ja': LanguageConfig('ja', 'Japanese', 'japan'),
        'ko': LanguageConfig('ko', 'Korean', 'korean'),
        'zh': LanguageConfig('zh', 'Chinese', 'ch'),
        'ar': LanguageConfig('ar', 'Arabic', 'ar'),
        'hi': LanguageConfig('hi', 'Hindi', 'hi'),
        'nl': LanguageConfig('nl', 'Dutch', 'dutch'),
        'pl': LanguageConfig('pl', 'Polish', 'pl'),
        'tr': LanguageConfig('tr', 'Turkish', 'tr'),
        'vi': LanguageConfig('vi', 'Vietnamese', 'vi'),
        'th': LanguageConfig('th', 'Thai', 'th'),
        'sv': LanguageConfig('sv', 'Swedish', 'sv'),
        'da': LanguageConfig('da', 'Danish', 'da'),
        'fi': LanguageConfig('fi', 'Finnish', 'fi'),
        'no': LanguageConfig('no', 'Norwegian', 'no'),
        'cs': LanguageConfig('cs', 'Czech', 'cs'),
        'ro': LanguageConfig('ro', 'Romanian', 'ro'),
        'hu': LanguageConfig('hu', 'Hungarian', 'hu'),
        'el': LanguageConfig('el', 'Greek', 'el'),
        'he': LanguageConfig('he', 'Hebrew', 'he'),
        'uk': LanguageConfig('uk', 'Ukrainian', 'uk'),
    }

    def __init__(self):
        self.detector = None
        self._init_detector()

    def _init_detector(self):
        """Initialize language detector"""
        try:
            from langdetect import detect_langs, DetectorFactory
            # Set seed for consistent results
            DetectorFactory.seed = 0
            self.detector = detect_langs
            logger.info("Language detector initialized successfully")
        except ImportError:
            logger.warning(
                "langdetect not available. Install with: pip install langdetect. "
                "Language auto-detection will be disabled."
            )

    def detect_language(self, text: str, top_n: int = 3) -> List[Dict[str, float]]:
        """
        Detect language of given text

        Args:
            text: Text to analyze
            top_n: Number of top languages to return

        Returns:
            List of dictionaries with 'lang' and 'prob' keys
        """
        if not self.detector:
            logger.warning("Language detector not available, defaulting to English")
            return [{'lang': 'en', 'prob': 1.0}]

        if not text or len(text.strip()) < 10:
            logger.warning("Text too short for reliable language detection")
            return [{'lang': 'en', 'prob': 0.5}]

        try:
            # Detect languages
            results = self.detector(text)

            # Convert to list of dicts and limit to top_n
            detected = [
                {'lang': r.lang, 'prob': r.prob}
                for r in results[:top_n]
            ]

            logger.info(f"Detected languages: {detected}")
            return detected

        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return [{'lang': 'en', 'prob': 0.5}]

    def get_ocr_language_code(self, lang_code: str) -> str:
        """
        Get PaddleOCR language code for given ISO code

        Args:
            lang_code: ISO 639-1 language code

        Returns:
            PaddleOCR language code
        """
        config = self.SUPPORTED_LANGUAGES.get(lang_code)
        if config:
            return config.ocr_code
        else:
            logger.warning(f"Language {lang_code} not in supported list, using English")
            return 'en'

    def get_language_name(self, lang_code: str) -> str:
        """Get language name from code"""
        config = self.SUPPORTED_LANGUAGES.get(lang_code)
        return config.name if config else 'Unknown'

    def is_supported(self, lang_code: str) -> bool:
        """Check if language is supported"""
        return lang_code in self.SUPPORTED_LANGUAGES

    def get_all_supported_languages(self) -> Dict[str, LanguageConfig]:
        """Get all supported languages"""
        return self.SUPPORTED_LANGUAGES.copy()

    def get_multilingual_prompt(
        self,
        text: str,
        schema: Dict,
        detected_language: str = 'en',
        custom_template: Optional[str] = None
    ) -> str:
        """
        Build multilingual extraction prompt

        Args:
            text: Input text
            schema: Extraction schema
            detected_language: Detected language code
            custom_template: Optional custom template

        Returns:
            Formatted multilingual prompt
        """
        if custom_template:
            return custom_template.format(
                text=text,
                schema=schema,
                language=detected_language
            )

        # Language-specific instructions
        lang_instructions = {
            'en': "You are a medical document data extraction expert. Extract structured information from the following English document.",
            'es': "Eres un experto en extracción de datos de documentos médicos. Extrae información estructurada del siguiente documento en español.",
            'fr': "Vous êtes un expert en extraction de données de documents médicaux. Extrayez des informations structurées du document français suivant.",
            'de': "Sie sind ein Experte für die Extraktion von Daten aus medizinischen Dokumenten. Extrahieren Sie strukturierte Informationen aus dem folgenden deutschen Dokument.",
            'it': "Sei un esperto nell'estrazione di dati da documenti medici. Estrai informazioni strutturate dal seguente documento italiano.",
            'pt': "Você é um especialista em extração de dados de documentos médicos. Extraia informações estruturadas do seguinte documento em português.",
            'zh': "您是医疗文档数据提取专家。从以下中文文档中提取结构化信息。",
            'ja': "あなたは医療文書データ抽出の専門家です。次の日本語文書から構造化情報を抽出してください。",
            'ru': "Вы эксперт по извлечению данных из медицинских документов. Извлеките структурированную информацию из следующего русского документа.",
            'ar': "أنت خبير في استخراج البيانات من المستندات الطبية. استخرج معلومات منظمة من المستند العربي التالي.",
        }

        instruction = lang_instructions.get(
            detected_language,
            lang_instructions['en']
        )

        # Build schema description
        schema_desc = self._format_schema_description(schema)

        prompt = f"""{instruction}

Document Text:
{text}

Required Fields to Extract:
{schema_desc}

Instructions:
1. Extract only the information present in the document
2. Return results in JSON format matching the schema
3. Use null for missing fields
4. Provide confidence scores (0-1) for each field
5. Respect the document's language and terminology

Return your response as a valid JSON object."""

        return prompt

    def _format_schema_description(self, schema: Dict) -> str:
        """Format schema into description"""
        lines = []
        for field_name, field_info in schema.get("properties", {}).items():
            field_type = field_info.get("type", "string")
            description = field_info.get("description", "")
            required = field_name in schema.get("required", [])
            req_marker = " (required)" if required else " (optional)"
            lines.append(f"- {field_name} ({field_type}){req_marker}: {description}")
        return "\n".join(lines)

    def auto_detect_and_configure(self, text: str) -> Dict[str, any]:
        """
        Auto-detect language and return configuration

        Args:
            text: Document text

        Returns:
            Dictionary with detected language and configuration
        """
        detected = self.detect_language(text, top_n=1)

        if detected:
            lang_code = detected[0]['lang']
            confidence = detected[0]['prob']

            return {
                'detected_language': lang_code,
                'language_name': self.get_language_name(lang_code),
                'confidence': confidence,
                'ocr_language': self.get_ocr_language_code(lang_code),
                'supported': self.is_supported(lang_code)
            }
        else:
            return {
                'detected_language': 'en',
                'language_name': 'English',
                'confidence': 0.5,
                'ocr_language': 'en',
                'supported': True
            }


# Singleton instance
_language_manager = None


def get_language_manager() -> LanguageManager:
    """Get or create language manager singleton"""
    global _language_manager
    if _language_manager is None:
        _language_manager = LanguageManager()
    return _language_manager
