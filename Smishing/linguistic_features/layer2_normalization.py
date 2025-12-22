import re
import unicodedata
import random
import string
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, Dict, Set

# Import từ dict module

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import tuyệt đối
from dicts.dict import load_both_dicts, remove_vietnamese_diacritics

@dataclass
class NormalizationResult:
    tokens: list[str]
    normalized_text: str
    original_text: str
    leet_count: int = 0
    separator_count: int = 0
    # Các feature mới theo phân tích
    teencode_count: int = 0  # ko, dc, hok, j
    visual_leet_count: int = 0  # 0->o, 3->e, 4->a (số thay chữ)
    symbol_leet_count: int = 0  # @->a, $->s, !->i (ký tự đặc biệt)
    validated_leet_count: int = 0  # Số leet đã validate bằng từ điển
    weighted_leet_score: float = 0.0  # Tổng điểm có trọng số


class TextNormalizer:
    def __init__(self, dict_path: str = None):
        """
        Khởi tạo TextNormalizer với dictionary validation
        
        Args:
            dict_path: Đường dẫn đến file từ điển (mặc định: sử dụng shadow_dict.py)
        """
        # 1. Leet Map: CHỈ GIỮ KÝ TỰ ĐẶC BIỆT (Symbol Leet)
        self.leet_map_chars = str.maketrans({
            '@': 'a', '$': 's', '+': 't', 
            'j': 'i',
        })
        
        # 2. Phân loại Leet Patterns với trọng số
        # TEENCODE (trọng số thấp - 0.3)
        self.teencode_patterns = [
            (r'\bko\b', 'không', 0.3),
            (r'\bck\b', 'ch', 0.3),
        ]
        
        # VISUAL LEET - Số thay chữ (trọng số cao - 1.0)
        self.visual_leet_patterns = [
            (r'\b0k\b', 'ok', 1.0),
            (r'\b0([a-zA-Z]{2,})\b', r'o\1', 1.0),
            (r'\b([a-zA-Z]+)0\b', r'\1o', 1.0),
            (r'(?<=[a-zA-Z])0(?=[a-zA-Z])', 'o', 1.0),  # h0tro -> hotro
            (r'(?<=[a-zA-Z])1(?=[a-zA-Z])', 'i', 1.0),
            (r'(?<=[a-zA-Z])3(?=[a-zA-Z])', 'e', 1.0),
            (r'(?<=[a-zA-Z])4(?=[a-zA-Z])', 'a', 1.0),
            (r'(?<=[a-zA-Z])5(?=[a-zA-Z])', 's', 1.0),
            (r'(?<=[a-zA-Z])8(?=[a-zA-Z])', 'b', 1.0),
        ]
        
        # SYMBOL LEET - Ký tự đặc biệt (trọng số rất cao - 1.2-1.5)
        self.symbol_leet_patterns = [
            (r'(?<=[a-zA-Zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ])!(?=[a-zA-Zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ])', 'i', 1.2),
        ]
        
        # Trọng số cho character-level leet (dùng trong translate)
        self.leet_char_weights = {
            '@': 1.5,  # @ -> a: rất nghi ngờ
            '$': 1.5,  # $ -> s: rất nghi ngờ
            '+': 1.2,  # + -> t: nghi ngờ
            'j': 0.3,  # j -> i: teencode
            'w': 0.3,  # w -> u: teencode
            'z': 0.3,  # z -> d: teencode
        }
        
        # Gộp tất cả patterns để decode (không có trọng số trong list này)
        self.leet_word_patterns = [
            (pattern, replacement) 
            for pattern, replacement, _ in self.teencode_patterns + self.visual_leet_patterns + self.symbol_leet_patterns
        ]

        # 3. Separator Pattern
        self.separator_pattern = re.compile(r"['\-~:;,\.\"\*\^\{\}\[\]\(\)\/\|\\!]")

        # 4. Token Pattern
        self.token_pattern = re.compile(
            r'(<[A-Z_]+>)|'
            r'([a-zA-Z0-9àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]+)', 
            re.IGNORECASE | re.UNICODE
        )
        
        # 5. Layer 1 Tag regex
        self.layer1_tag_regex = re.compile(r'<[A-Z_]+>')

        # 6. Placeholder prefix
        self._placeholder_prefix = ''.join(random.choices(string.ascii_uppercase, k=12))
        
        # 7. Load từ điển từ shadow_dict.py
        self.full_dict: Set[str] = set()  # Từ điển có dấu
        self.shadow_dict: Set[str] = set()  # Từ điển không dấu
        self._load_dictionary(dict_path)

    def _remove_vietnamese_accents(self, text: str) -> str:
        """
        Loại bỏ dấu tiếng Việt, giữ lại chữ cái Latin gốc
        "ngân hàng" → "ngan hang"
        "điều kiện" → "dieu kien"
        
        Note: Sử dụng remove_vietnamese_diacritics từ shadow_dict.py để đồng bộ
        """
        if not isinstance(text, str):
            return text
        return remove_vietnamese_diacritics(text)

    def _load_dictionary(self, dict_path: str = None):
        """
        Load từ điển từ shadow_dict.py hoặc từ file chỉ định
        
        Args:
            dict_path: Đường dẫn đến file từ điển. Nếu None, sử dụng load_both_dicts() từ shadow_dict.py
        """
        try:
            if dict_path is None:
                # Sử dụng load_both_dicts từ shadow_dict.py (tự động tìm words.txt)
                self.full_dict, self.shadow_dict = load_both_dicts()
            else:
                # Load từ file chỉ định
                dict_path = Path(dict_path)
                if not dict_path.exists():
                    print(f"⚠ Warning: Dictionary not found at {dict_path}. Dictionary validation will be disabled.")
                    return
                self.full_dict, self.shadow_dict = load_both_dicts(str(dict_path))
            
            print(f"✓ Dictionary loaded: {len(self.full_dict):,} words (full), {len(self.shadow_dict):,} words (shadow)")
        except (FileNotFoundError, RuntimeError) as e:
            print(f"⚠ Warning: Error loading dictionary: {e}. Dictionary validation will be disabled.")
            self.full_dict = set()
            self.shadow_dict = set()
        except Exception as e:
            print(f"⚠ Warning: Unexpected error loading dictionary: {e}. Dictionary validation will be disabled.")
            self.full_dict = set()
            self.shadow_dict = set()

    def _validate_word_in_dict(self, word: str) -> bool:
        """
        Validate từ có trong từ điển không (kiểm tra cả có dấu và không dấu)
        """
        if not self.full_dict:  # Dictionary chưa được load
            return False
        
        word_lower = word.lower().strip()
        
        # Check 1: Full dict (có dấu)
        if word_lower in self.full_dict:
            return True
        
        # Check 2: Shadow dict (không dấu)
        no_accent = remove_vietnamese_diacritics(word_lower)
        if no_accent in self.shadow_dict:
            return True
        
        return False

    def _normalize_unicode(self, text: str) -> str:
        return unicodedata.normalize('NFC', text)

    def _clean_separators_safe(self, text: str) -> tuple[str, int]:
        """Tách separator nhưng BẢO VỆ các token Layer 1"""
        tags = []
        prefix = self._placeholder_prefix
        
        def store_tag(match):
            tags.append(match.group(0))
            idx_letter = chr(ord('A') + len(tags) - 1)
            return f"SEPTAG{prefix}IDX{idx_letter}END"

        safe_text = self.layer1_tag_regex.sub(store_tag, text)
        cleaned_text = self.separator_pattern.sub(' ', safe_text)
        count = len(self.separator_pattern.findall(safe_text))
        
        def restore_tag(match):
            idx_letter = match.group(1)
            idx = ord(idx_letter.upper()) - ord('A')
            return tags[idx]
            
        final_text = re.sub(rf'SEPTAG{prefix}IDX([A-Z])END', restore_tag, cleaned_text, flags=re.IGNORECASE)
        final_text = re.sub(r'\s+', ' ', final_text).strip()
        
        return final_text, count

    def _decode_leetspeak_safe(self, text: str) -> Tuple[str, Dict[str, any]]:
        """
        Decode leetspeak với tracking chi tiết theo từng loại và validation
        
        Returns:
            (decoded_text, stats_dict) với stats_dict chứa:
            - leet_count: tổng số leet chars
            - teencode_count: số teencode patterns
            - visual_leet_count: số visual leet patterns
            - symbol_leet_count: số symbol leet patterns
            - validated_leet_count: số leet đã validate bằng từ điển
            - weighted_leet_score: tổng điểm có trọng số
        """
        tags = []
        prefix = self._placeholder_prefix
        
        def store_tag(match):
            tags.append(match.group(0))
            idx_letter = chr(ord('A') + len(tags) - 1)
            return f"LEETTAG{prefix}IDX{idx_letter}END"
        
        safe_text = self.layer1_tag_regex.sub(store_tag, text)
        
        # Khởi tạo stats
        stats = {
            'leet_count': 0,
            'teencode_count': 0,
            'visual_leet_count': 0,
            'symbol_leet_count': 0,
            'validated_leet_count': 0,
            'weighted_leet_score': 0.0,
            'leet_words': []  # Lưu các từ có leet để validate sau
        }
        
        # Đếm leet chars (character-level)
        leet_chars = set('013456789!@$')
        for char in safe_text:
            if char in leet_chars:
                stats['leet_count'] += 1
                # Áp dụng trọng số cho character-level leet
                if char in self.leet_char_weights:
                    stats['weighted_leet_score'] += self.leet_char_weights[char]
                    if char in ['@', '$', '+']:
                        stats['symbol_leet_count'] += 1
        
        # Decode character-level (symbol leet)
        text_decoded = safe_text.translate(self.leet_map_chars)
        
        # Track các từ trước và sau decode để validate
        original_words = set(re.findall(r'\b[a-zA-Zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]+\b', safe_text, re.IGNORECASE))
        
        # Apply patterns với tracking
        # Teencode patterns
        for pattern, replacement, weight in self.teencode_patterns:
            matches = re.findall(pattern, text_decoded, re.IGNORECASE)
            if matches:
                stats['teencode_count'] += len(matches) if isinstance(matches, list) else 1
                stats['weighted_leet_score'] += weight * (len(matches) if isinstance(matches, list) else 1)
            text_decoded = re.sub(pattern, replacement, text_decoded, flags=re.IGNORECASE)
        
        # Visual leet patterns
        for pattern, replacement, weight in self.visual_leet_patterns:
            matches = re.findall(pattern, text_decoded, re.IGNORECASE)
            if matches:
                count = len(matches) if isinstance(matches, list) else 1
                stats['visual_leet_count'] += count
                stats['weighted_leet_score'] += weight * count
            text_decoded = re.sub(pattern, replacement, text_decoded, flags=re.IGNORECASE)
        
        # Symbol leet patterns
        for pattern, replacement, weight in self.symbol_leet_patterns:
            matches = re.findall(pattern, text_decoded, re.IGNORECASE)
            if matches:
                count = len(matches) if isinstance(matches, list) else 1
                stats['symbol_leet_count'] += count
                stats['weighted_leet_score'] += weight * count
            text_decoded = re.sub(pattern, replacement, text_decoded, flags=re.IGNORECASE)
        
        # Restore tags
        def restore_tag(match):
            idx_letter = match.group(1)
            idx = ord(idx_letter.upper()) - ord('A')
            return tags[idx]
        
        final_text = re.sub(rf'LEETTAG{prefix}IDX([A-Z])END', restore_tag, text_decoded, flags=re.IGNORECASE)
        
        # Validate các từ sau khi decode bằng từ điển
        decoded_words = re.findall(r'\b[a-zA-Zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]+\b', final_text, re.IGNORECASE)
        for word in decoded_words:
            if self._validate_word_in_dict(word):
                # Tìm xem từ này có phải là kết quả của leet decode không
                # (so sánh với original_words để xác định)
                word_lower = word.lower()
                # Nếu từ này không có trong original (hoặc khác) → có thể là leet decode
                if word_lower not in [w.lower() for w in original_words]:
                    stats['validated_leet_count'] += 1
        
        return final_text, stats

    def _tokenize(self, text: str) -> list[str]:
        tokens = []
        for match in self.token_pattern.finditer(text):
            tag_group = match.group(1)
            word_group = match.group(2)
            
            if tag_group:
                tokens.append(tag_group)
            elif word_group:
                tokens.append(word_group.lower())
                
        return tokens

    def normalize(self, text: str) -> NormalizationResult:
        if not text:
            return NormalizationResult(
                tokens=[], 
                normalized_text="", 
                original_text="", 
                leet_count=0, 
                separator_count=0
            )

        original = text
        text = self._normalize_unicode(text)
        text, leet_stats = self._decode_leetspeak_safe(text)
        text, sep_count = self._clean_separators_safe(text)
        tokens = self._tokenize(text)
        normalized_text = ' '.join(tokens)
        
        return NormalizationResult(
            tokens=tokens,
            normalized_text=normalized_text,
            original_text=original,
            leet_count=leet_stats['leet_count'],
            separator_count=sep_count,
            teencode_count=leet_stats['teencode_count'],
            visual_leet_count=leet_stats['visual_leet_count'],
            symbol_leet_count=leet_stats['symbol_leet_count'],
            validated_leet_count=leet_stats['validated_leet_count'],
            weighted_leet_score=leet_stats['weighted_leet_score']
        )


# --- TEST ---
if __name__ == "__main__":
    normalizer = TextNormalizer()
    samples = [
        "Truy cap <URL> ngay",
        "Lien he <PHONE> de duoc ho tro",
        "Th0ng ba0: Gửi qua <APP_LINK> hoặc <BAD_URL>",
        "kh0ng co d!eu k!en",
        "Nhan tien @ngay de duoc ho tro",
        "ko can d!eu k!en",
    ]
    
    print("LAYER 2 TEST - Enhanced with Dictionary Validation & Leet Classification")
    print("=" * 70)
    for s in samples:
        res = normalizer.normalize(s)
        print(f"\nInput:  {s}")
        print(f"Output: {res.normalized_text}")
        print(f"Tokens: {res.tokens}")
        print(f"Leet Stats:")
        print(f"  - Total leet chars: {res.leet_count}")
        print(f"  - Teencode count: {res.teencode_count} (weight: 0.3)")
        print(f"  - Visual leet count: {res.visual_leet_count} (weight: 1.0)")
        print(f"  - Symbol leet count: {res.symbol_leet_count} (weight: 1.2-1.5)")
        print(f"  - Validated leet count: {res.validated_leet_count}")
        print(f"  - Weighted leet score: {res.weighted_leet_score:.2f}")
        print("-" * 70)