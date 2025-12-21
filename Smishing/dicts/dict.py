import unicodedata
import json
from pathlib import Path
from typing import Set, Optional, Tuple

def remove_vietnamese_diacritics(text):
    """
    Chuyển text tiếng Việt có dấu về không dấu.
    Giữ nguyên chữ cái tiếng Anh, số, ký tự đặc biệt.
    """
    if not isinstance(text, str):
        return text
    text = unicodedata.normalize('NFD', text)
    text = ''.join([c for c in text if unicodedata.category(c) != 'Mn'])
    return text

def load_full_dict(word_file: Optional[str] = None) -> Set[str]:
    """
    Đọc file words.txt (định dạng JSON lines), trả về set chứa các từ có dấu (lowercase).
    
    Args:
        word_file: Đường dẫn đến file words.txt. Nếu None, tự động tìm trong thư mục dicts.
    
    Returns:
        Set[str]: Set chứa các từ có dấu (full dict)
    """
    # Tự động tìm file words.txt trong cùng thư mục dicts nếu không chỉ định
    if word_file is None:
        current_dir = Path(__file__).parent
        word_file = current_dir / 'words.txt'
    else:
        word_file = Path(word_file)
    
    vocab = set()
    
    if not word_file.exists():
        raise FileNotFoundError(f"Dictionary file not found: {word_file}")
    
    try:
        with open(word_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    # Parse JSON format: {"text": "từ", "source": [...]}
                    data = json.loads(line)
                    word = data.get('text', '').strip()
                    
                    if word:
                        # Chỉ chuyển về lowercase, giữ nguyên dấu
                        word_lower = word.lower()
                        vocab.add(word_lower)
                        
                except json.JSONDecodeError:
                    # Nếu không phải JSON, thử đọc như plain text
                    word = line.strip()
                    if word:
                        vocab.add(word.lower())
                    continue
        
        print(f"✓ Full dict loaded: {len(vocab):,} words from {word_file}")
        return vocab
        
    except Exception as e:
        raise RuntimeError(f"Error loading full dict from {word_file}: {e}")

def load_shadow_dict(word_file: Optional[str] = None) -> Set[str]:
    """
    Đọc file words.txt (định dạng JSON lines), trả về set chứa các từ đã chuẩn hóa không dấu.
    
    Args:
        word_file: Đường dẫn đến file words.txt. Nếu None, tự động tìm trong thư mục dicts.
    
    Returns:
        Set[str]: Set chứa các từ không dấu (shadow dict)
    """
    # Tự động tìm file words.txt trong cùng thư mục dicts nếu không chỉ định
    if word_file is None:
        current_dir = Path(__file__).parent
        word_file = current_dir / 'words.txt'
    else:
        word_file = Path(word_file)
    
    vocab = set()
    
    if not word_file.exists():
        raise FileNotFoundError(f"Dictionary file not found: {word_file}")
    
    try:
        with open(word_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    # Parse JSON format: {"text": "từ", "source": [...]}
                    data = json.loads(line)
                    word = data.get('text', '').strip()
                    
                    if word:
                        # Chuyển về lowercase và loại bỏ dấu
                        word_lower = word.lower()
                        shadow = remove_vietnamese_diacritics(word_lower)
                        vocab.add(shadow)
                        
                except json.JSONDecodeError:
                    # Nếu không phải JSON, thử đọc như plain text
                    word = line.strip()
                    if word:
                        shadow = remove_vietnamese_diacritics(word).lower()
                        vocab.add(shadow)
                    continue
        
        print(f"✓ Shadow dict loaded: {len(vocab):,} words from {word_file}")
        return vocab
        
    except Exception as e:
        raise RuntimeError(f"Error loading shadow dict from {word_file}: {e}")

def load_both_dicts(word_file: Optional[str] = None) -> Tuple[Set[str], Set[str]]:
    """
    Load cả full_dict và shadow_dict cùng lúc từ words.txt (tối ưu hơn).
    
    Args:
        word_file: Đường dẫn đến file words.txt. Nếu None, tự động tìm trong thư mục dicts.
    
    Returns:
        Tuple[Set[str], Set[str]]: (full_dict, shadow_dict)
    """
    # Tự động tìm file words.txt trong cùng thư mục dicts nếu không chỉ định
    if word_file is None:
        current_dir = Path(__file__).parent
        word_file = current_dir / 'words.txt'
    else:
        word_file = Path(word_file)
    
    full_vocab = set()
    shadow_vocab = set()
    
    if not word_file.exists():
        raise FileNotFoundError(f"Dictionary file not found: {word_file}")
    
    try:
        with open(word_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    # Parse JSON format: {"text": "từ", "source": [...]}
                    data = json.loads(line)
                    word = data.get('text', '').strip()
                    
                    if word:
                        # Chuyển về lowercase
                        word_lower = word.lower()
                        # Thêm vào full_dict (có dấu)
                        full_vocab.add(word_lower)
                        # Thêm vào shadow_dict (không dấu)
                        shadow = remove_vietnamese_diacritics(word_lower)
                        shadow_vocab.add(shadow)
                        
                except json.JSONDecodeError:
                    # Nếu không phải JSON, thử đọc như plain text
                    word = line.strip()
                    if word:
                        word_lower = word.lower()
                        full_vocab.add(word_lower)
                        shadow = remove_vietnamese_diacritics(word_lower)
                        shadow_vocab.add(shadow)
                    continue
        
        print(f"✓ Both dicts loaded: {len(full_vocab):,} words (full), {len(shadow_vocab):,} words (shadow) from {word_file}")
        return full_vocab, shadow_vocab
        
    except Exception as e:
        raise RuntimeError(f"Error loading dicts from {word_file}: {e}")

def export_full_dict(output_file: str = "full_dict.txt", word_file: Optional[str] = None):
    """
    Load từ 'words.txt', giữ nguyên dấu (lowercase), lưu ra file mới (full_dict.txt).
    Mỗi từ một dòng, đã sắp xếp.
    
    Args:
        output_file: Tên file output (mặc định: full_dict.txt trong cùng thư mục)
        word_file: Đường dẫn đến file words.txt (mặc định: tự động tìm)
    """
    vocab = load_full_dict(word_file)
    
    # Nếu output_file là tên file đơn giản, lưu vào cùng thư mục với shadow_dict.py
    output_path = Path(output_file)
    if not output_path.is_absolute() and output_path.parent == Path('.'):
        output_path = Path(__file__).parent / output_file
    
    with open(output_path, "w", encoding="utf-8") as f:
        for word in sorted(vocab):
            f.write(word + "\n")
    
    print(f"✓ Full dict exported: {len(vocab):,} words to {output_path}")

def export_shadow_dict(output_file: str = "shadow_dict.txt", word_file: Optional[str] = None):
    """
    Load từ 'words.txt', chuẩn hóa về không dấu, lưu ra file mới (shadow_dict.txt).
    Mỗi từ một dòng, đã sắp xếp.
    
    Args:
        output_file: Tên file output (mặc định: shadow_dict.txt trong cùng thư mục)
        word_file: Đường dẫn đến file words.txt (mặc định: tự động tìm)
    """
    vocab = load_shadow_dict(word_file)
    
    # Nếu output_file là tên file đơn giản, lưu vào cùng thư mục với shadow_dict.py
    output_path = Path(output_file)
    if not output_path.is_absolute() and output_path.parent == Path('.'):
        output_path = Path(__file__).parent / output_file
    
    with open(output_path, "w", encoding="utf-8") as f:
        for word in sorted(vocab):
            f.write(word + "\n")
    
    print(f"✓ Shadow dict exported: {len(vocab):,} words to {output_path}")

# Load sẵn cả full_dict và shadow_dict để các layer có thể import và sử dụng
# Có thể comment dòng này nếu muốn lazy loading
try:
    full_dict, shadow_dict = load_both_dicts()
except (FileNotFoundError, RuntimeError) as e:
    print(f"⚠ Warning: Could not load dicts: {e}")
    full_dict = set()  # Fallback: empty set
    shadow_dict = set()  # Fallback: empty set

if __name__ == "__main__":
    # Export cả hai dict khi chạy trực tiếp
    export_full_dict()
    export_shadow_dict()