import re
import os
import sys
from dataclasses import dataclass, field
from typing import Set, List, Optional
import logging

# Import từ dict module
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import tuyệt đối
from dicts.dict import load_both_dicts, remove_vietnamese_diacritics
try:
    from ..dicts.dict import load_both_dicts, remove_vietnamese_diacritics
except ImportError:
    # Fallback cho môi trường test đơn lẻ
    pass

logger = logging.getLogger(__name__)

@dataclass
class MisspellResult:
    oov_count: int = 0
    oov_density: float = 0.0
    broken_telex_count: int = 0
    longest_oov_length: int = 0
    # --- NEW FEATURES ---
    gibberish_count: int = 0        # Từ vô nghĩa (không nguyên âm, consonant cluster)
    repeated_char_count: int = 0    # Lặp ký tự > 2 (HOTTT)
    run_on_word_count: int = 0      # Dính từ (vuilong)
    # --------------------
    oov_tokens: List[str] = field(default_factory=list)

class MisspellExtractor:
    def __init__(self, full_dict: Optional[Set[str]] = None, shadow_dict: Optional[Set[str]] = None, dict_path: Optional[str] = None):
        # ... (Phần Init giữ nguyên như code của bạn) ...
        # (Để gọn code tôi xin phép lược bớt phần Init này vì bạn đã làm tốt)
        if full_dict is None or shadow_dict is None:
             # ... (Logic load dict giữ nguyên) ...
             self.full_dict = set() # Placeholder
             self.shadow_dict = set() # Placeholder
        else:
            self.full_dict = full_dict
            self.shadow_dict = shadow_dict

        # Regex Broken Telex (Giữ nguyên)
        self.broken_telex_pattern = re.compile(
            r'(?i)\b[a-z]*('
            r'aa|ee|dd|oo|ow|uw|ww|aw|'
            r'af|as|ar|ax|aj|aq'
            r')[a-z]*\b'
        )
        
        # --- NEW REGEX PATTERNS ---
        # 1. Repeated Chars: Ký tự lặp lại 3 lần trở lên (vd: aaa, hhh)
        self.repeated_char_pattern = re.compile(r'(.)\1{2,}')
        
        # 2. Consonant Cluster: 4 phụ âm liên tiếp trở lên (Khó phát âm trong tiếng Việt)
        # Loại trừ 'ngh' (3 char), 'ng' (2 char). 
        # Tiếng Việt hiếm khi có 4 phụ âm dính liền trừ từ vay mượn.
        self.consonant_cluster_pattern = re.compile(r'[bcdfghjklmnpqrstvwxyz]{4,}', re.IGNORECASE)
        
        # 3. No Vowel: Không có nguyên âm nào (trừ số đã filter)
        self.has_vowel_pattern = re.compile(r'[aeiouyàáảãạ...]', re.IGNORECASE) # (Rút gọn cho demo, thực tế cần list đủ nguyên âm)
        
        # 4. Data Capacity Units: Whitelist các đơn vị dung lượng (3gb, 2mb, 15gb...)
        # Pattern: số + đơn vị (gb, mb, tb, kb) hoặc tốc độ (gbps, mbps, kbps)
        self.data_capacity_pattern = re.compile(
            r'^\d+(gb|mb|tb|kb|gbps|mbps|kbps)$',
            re.IGNORECASE
        )

    def _remove_accents(self, text: str) -> str:
        # (Giữ nguyên)
        if not isinstance(text, str): return text
        # Fallback nếu không import được
        try:
            return remove_vietnamese_diacritics(text)
        except NameError:
            return text

    def _check_run_on_word(self, token: str) -> bool:
        """Kiểm tra lỗi dính từ (vd: 'vuilong')"""
        if len(token) < 4: return False # Quá ngắn không check
        
        # Thử cắt đôi token tại mọi vị trí
        # vd: v-uilong, vu-ilong, vui-long...
        for i in range(2, len(token) - 1):
            left = token[:i]
            right = token[i:]
            
            # Check xem cả 2 phần có nghĩa không (dùng shadow dict cho nhanh)
            # Lưu ý: Logic này đơn giản hóa, có thể check full_dict nếu muốn chính xác hơn
            if left in self.shadow_dict and right in self.shadow_dict:
                return True
        return False

    def _is_gibberish(self, token: str) -> bool:
        """Kiểm tra xem token có phải là rác vô nghĩa không"""
        # Rule 1: Không có nguyên âm (vd: 'xkqv')
        # (Cần danh sách nguyên âm đầy đủ, ở đây dùng simple check a,e,i,o,u,y)
        if not re.search(r'[aeiouy]', token, re.IGNORECASE):
            return True
            
        # Rule 2: Cụm phụ âm quá dài (vd: 'xkqvz')
        if self.consonant_cluster_pattern.search(token):
            return True
            
        return False

    def extract(self, tokens: List[str]) -> MisspellResult:
        if not tokens or not isinstance(tokens, list):
            return MisspellResult()

        oov_tokens = []
        broken_telex_count = 0
        max_len = 0
        checked_token_count = 0
        
        # New counters
        gibberish_count = 0
        repeated_char_count = 0
        run_on_word_count = 0

        for token in tokens:
            if not isinstance(token, str): continue
            token = token.strip()
            if not token or token.isdigit() or len(token) < 2:
                continue
            
            # Whitelist: Bỏ qua các đơn vị dung lượng (3gb, 2mb, 15gb...)
            if self.data_capacity_pattern.match(token):
                continue
            
            checked_token_count += 1
            token_lower = token.lower()

            # --- DUAL LOOKUP CHECK ---
            if token_lower in self.full_dict:
                continue
            
            token_no_accent = self._remove_accents(token_lower)
            if token_no_accent in self.shadow_dict:
                continue
            
            # === TOKEN IS OOV ===
            oov_tokens.append(token)
            if len(token) > max_len: max_len = len(token)

            # 1. Check Gibberish (Ưu tiên check rác trước)
            if self._is_gibberish(token_no_accent):
                gibberish_count += 1
                # Nếu đã là rác, có thể không cần check các lỗi khác để tiết kiệm, 
                # hoặc check tiếp tùy nhu cầu. Ở đây ta check tiếp.

            # 2. Check Repeated Chars (Lỗi lặp > 2)
            if self.repeated_char_pattern.search(token_lower):
                repeated_char_count += 1
                
            # 3. Check Broken Telex (Chỉ check nếu KHÔNG phải repeated char quá nhiều)
            elif self.broken_telex_pattern.search(token_lower):
                broken_telex_count += 1
                
            # 4. Check Run-on Words (Dính từ)
            # Chỉ check nếu token không chứa ký tự lạ và không phải gibberish
            if not gibberish_count and token.isalpha():
                if self._check_run_on_word(token_no_accent):
                    run_on_word_count += 1

        oov_count = len(oov_tokens)
        density = oov_count / checked_token_count if checked_token_count > 0 else 0.0

        return MisspellResult(
            oov_count=oov_count,
            oov_density=density,
            broken_telex_count=broken_telex_count,
            longest_oov_length=max_len,
            # New Metrics
            gibberish_count=gibberish_count,
            repeated_char_count=repeated_char_count,
            run_on_word_count=run_on_word_count,
            # List
            oov_tokens=oov_tokens
        )