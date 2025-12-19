import re
import unicodedata
import random
import string
from dataclasses import dataclass


@dataclass
class NormalizationResult:
    tokens: list[str]
    normalized_text: str
    original_text: str
    leet_count: int = 0
    separator_count: int = 0


class TextNormalizer:
    def __init__(self):
        # 1. Leet Map: CHỈ GIỮ KÝ TỰ ĐẶC BIỆT (Tuyệt đối không map số ở đây)
        self.leet_map_chars = str.maketrans({
            # Đã xóa 0-9 và ( [ { để bảo vệ số liệu và cấu trúc
            '@': 'a', '$': 's', '+': 't', 
            'j': 'i', 'w': 'u', 'z': 'd' 
        })

        # 2. Leet word patterns (Regex Contextual)
        self.leet_word_patterns = [
            (r'\bko\b', 'không'),
            (r'\bf([aeiouàáảãạ])', r'ph\1'),
            (r'\bck\b', 'ch'),


            # --- NHÓM 1: XỬ LÝ 0 vs o (NÂNG CAO) ---
            
            # Case 1: "0k" đứng riêng lẻ -> "ok"
            # (An toàn vì tiền 0 đồng hiếm khi viết là 0k, mà là 'free'/'miễn phí')
            (r'\b0k\b', 'ok'), 

            # Case 2: 0 ở ĐẦU từ (vd: 0ng -> ong, 0la -> ola)
            # Logic: 0 + ít nhất 2 chữ cái (Tránh 0m, 0g, 0s)
            (r'\b0([a-zA-Z]{2,})\b', r'o\1'),

            # Case 3: 0 ở CUỐI từ (vd: c0 -> co, ck0 -> cho, k0 -> ko)
            # Logic: Chuỗi chữ cái + 0.
            # AN TOÀN TUYỆT ĐỐI VỚI Q10, V20, Note10:
            # Vì Q10 cấu trúc là Chữ+Số+0 -> Regex [a-zA-Z]+ sẽ dừng khi gặp số 1 -> Không khớp.
            (r'\b([a-zA-Z]+)0\b', r'\1o'),

            # --- NHÓM 2: XỬ LÝ SỐ KẸP GIỮA (Như cũ) ---
            (r'(?<=[a-zA-Z])0(?=[a-zA-Z])', 'o'), # h0tro -> hotro
            (r'(?<=[a-zA-Z])1(?=[a-zA-Z])', 'i'), 
            (r'(?<=[a-zA-Z])3(?=[a-zA-Z])', 'e'), 
            (r'(?<=[a-zA-Z])4(?=[a-zA-Z])', 'a'), 
            (r'(?<=[a-zA-Z])5(?=[a-zA-Z])', 's'), 
            (r'(?<=[a-zA-Z])8(?=[a-zA-Z])', 'b'), 

            # --- NHÓM 3: XỬ LÝ ! KẸP GIỮA CHỮ ---
            (r'(?<=[a-zA-Zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ])!(?=[a-zA-Zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ])', 'i'),
        ]

        # 3. Separator Pattern (không có underscore)
        self.separator_pattern = re.compile(r"['\-~:;,\.\"\*\^\{\}\[\]\(\)\/\|\\!]")

        # 4. Token Pattern
        self.token_pattern = re.compile(
            r'(<[A-Z_]+>)|'
            # Thêm 0-9 vào regex bên dưới
            r'([a-zA-Z0-9àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]+)', 
            re.IGNORECASE | re.UNICODE
        )
        
        # 5. Layer 1 Tag regex
        self.layer1_tag_regex = re.compile(r'<[A-Z_]+>')

        # 6. Placeholder prefix - CHỈ DÙNG UPPERCASE LETTERS (không bị translate)
        self._placeholder_prefix = ''.join(random.choices(string.ascii_uppercase, k=12))

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

    def _decode_leetspeak_safe(self, text: str) -> tuple[str, int]:
        """Decode leetspeak nhưng BẢO VỆ các Layer 1 Tags"""
        tags = []
        prefix = self._placeholder_prefix
        
        def store_tag(match):
            tags.append(match.group(0))
            # Dùng LETTER thay vì DIGIT cho index (A=0, B=1, C=2...)
            idx_letter = chr(ord('A') + len(tags) - 1)
            return f"LEETTAG{prefix}IDX{idx_letter}END"
        
        safe_text = self.layer1_tag_regex.sub(store_tag, text)
        
        # Đếm leet chars
        leet_count = 0
        leet_chars = set('0134567891!@$+([{')
        for char in safe_text:
            if char in leet_chars:
                leet_count += 1
        
        # Decode
        text_decoded = safe_text.translate(self.leet_map_chars)
        
        for pattern, replacement in self.leet_word_patterns:
            text_decoded = re.sub(pattern, replacement, text_decoded, flags=re.IGNORECASE)
        
        # Restore tags - dùng letter index
        def restore_tag(match):
            idx_letter = match.group(1)
            idx = ord(idx_letter.upper()) - ord('A')  # A→0, B→1, C→2...
            return tags[idx]
        
        final_text = re.sub(rf'LEETTAG{prefix}IDX([A-Z])END', restore_tag, text_decoded, flags=re.IGNORECASE)
        
        return final_text, leet_count

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
            return NormalizationResult([], "", "", 0, 0)

        original = text
        text = self._normalize_unicode(text)
        text, leet_count = self._decode_leetspeak_safe(text)
        text, sep_count = self._clean_separators_safe(text)
        tokens = self._tokenize(text)
        normalized_text = ' '.join(tokens)
        
        return NormalizationResult(
            tokens=tokens,
            normalized_text=normalized_text,
            original_text=original,
            leet_count=leet_count,
            separator_count=sep_count
        )


# --- TEST ---
if __name__ == "__main__":
    normalizer = TextNormalizer()
    samples = [
        "Truy cap <URL> ngay",
        "Lien he <PHONE> de duoc ho tro",
        "Th0ng ba0: Gửi qua <APP_LINK> hoặc <BAD_URL>",
        "kh0ng co d!eu k!en",
    ]
    
    print("LAYER 2 TEST")
    print("=" * 50)
    for s in samples:
        res = normalizer.normalize(s)
        print(f"Input:  {s}")
        print(f"Output: {res.normalized_text}")
        print(f"Tokens: {res.tokens}")
        print(f"Tags preserved: {[t for t in res.tokens if t.startswith('<')]}")
        print("-" * 30)