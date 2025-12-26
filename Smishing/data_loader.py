"""
Smishing/data_loader.py
=======================
Module load dữ liệu đầu vào cho toàn bộ hệ thống Smishing Detection.
Xử lý các trường hợp CSV phức tạp có dấu nháy kép, dấu phẩy trong content.
"""

import pandas as pd
import io
from typing import Union, List
from pathlib import Path


class DataLoader:
    """
    Class load và tiền xử lý dữ liệu CSV cho hệ thống Smishing Detection.
    
    Example:
        >>> loader = DataLoader()
        >>> df = loader.load('data/dataset.csv')
        
        # Hoặc dùng static method
        >>> df = DataLoader.load_csv('data/dataset.csv')
    """
    
    # Các cột cố định ở cuối file CSV
    DEFAULT_TAIL_COLS = ['label', 'has_url', 'has_phone_number', 'sender_type']
    
    def __init__(self, encoding: str = 'utf-8'):
        self.encoding = encoding
    
    @staticmethod
    def load_csv(file_path: Union[str, Path], 
                 fixed_tail_cols: int = 4,
                 encoding: str = 'utf-8',
                 try_standard_first: bool = True) -> pd.DataFrame:
        """
        Load file CSV, tự động xử lý các trường hợp phức tạp.
        
        Args:
            file_path: Đường dẫn tới file CSV
            fixed_tail_cols: Số cột cố định ở cuối (default: 4)
            encoding: Encoding của file
            try_standard_first: Thử pd.read_csv() trước
            
        Returns:
            pd.DataFrame
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File không tồn tại: {file_path}")
        
        # Thử đọc bằng cách chuẩn trước
        if try_standard_first:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                print(f"✅ Loaded {len(df):,} rows from {file_path.name} (standard parser)")
                return df
            except Exception as e:
                print(f"⚠️ Standard parser failed: {e}")
                print("🔄 Switching to complex CSV parser...")
        
        # Fallback: Parser phức tạp
        return DataLoader._load_complex_csv(file_path, fixed_tail_cols, encoding)
    
    @staticmethod
    def _load_complex_csv(file_path: Union[str, Path],
                          fixed_tail_cols: int = 4,
                          encoding: str = 'utf-8') -> pd.DataFrame:
        """
        Parser cho CSV phức tạp có dấu nháy kép và dấu phẩy trong content.
        
        Chiến thuật: Cắt từ phải sang trái (rsplit) để tách content 
        khỏi các cột cố định ở cuối.
        """
        processed_lines = []
        error_lines = []
        
        with open(file_path, 'r', encoding=encoding) as f:
            # Header
            header = f.readline().strip()
            processed_lines.append(header)
            
            for line_num, line in enumerate(f, start=2):
                line = line.strip()
                if not line:
                    continue
                
                # Cắt từ phải sang trái
                parts = line.rsplit(',', fixed_tail_cols)
                
                if len(parts) < fixed_tail_cols + 1:
                    error_lines.append((line_num, line[:80]))
                    continue
                
                messy_content = parts[0]
                clean_tail = parts[1:]
                
                # Xử lý content
                if messy_content.startswith('"') and messy_content.endswith('"'):
                    messy_content = messy_content[1:-1]
                
                # Thay " bằng ' để tránh lỗi
                fixed_content = messy_content.replace('"', "'")
                
                # Đóng gói lại
                final_content = f'"{fixed_content}"'
                new_line = final_content + "," + ",".join(clean_tail)
                processed_lines.append(new_line)
        
        # Log lỗi
        if error_lines:
            print(f"⚠️ {len(error_lines)} dòng bị bỏ qua do lỗi format")
            for ln, content in error_lines[:3]:
                print(f"   Line {ln}: {content}...")
        
        # Tạo DataFrame
        virtual_file = io.StringIO("\n".join(processed_lines))
        df = pd.read_csv(virtual_file)
        
        print(f"✅ Loaded {len(df):,} rows from {Path(file_path).name} (complex parser)")
        return df
    
    @staticmethod
    def load_multiple(file_paths: List[Union[str, Path]], 
                      **kwargs) -> pd.DataFrame:
        """
        Load và gộp nhiều file CSV.
        
        Args:
            file_paths: Danh sách đường dẫn file
            **kwargs: Các tham số truyền cho load_csv()
            
        Returns:
            pd.DataFrame đã gộp
        """
        dfs = []
        for fp in file_paths:
            df = DataLoader.load_csv(fp, **kwargs)
            df['_source_file'] = Path(fp).name  # Đánh dấu nguồn
            dfs.append(df)
        
        merged = pd.concat(dfs, ignore_index=True)
        print(f"📊 Merged {len(merged):,} total rows from {len(file_paths)} files")
        return merged


# === LOAD DATASET FUNCTIONS ===

def load_dataset(file_path: Union[str, Path], **kwargs) -> pd.DataFrame:
    """Shortcut function để load dataset"""
    return DataLoader.load_csv(file_path, **kwargs)


def load_datasets(*file_paths, **kwargs) -> pd.DataFrame:
    """Shortcut function để load và merge nhiều datasets"""
    return DataLoader.load_multiple(list(file_paths), **kwargs)