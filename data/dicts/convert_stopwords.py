# convert_stopwords.py
def convert_stopwords_to_space():
    """Chuyển stopwords từ underscore sang space"""
    
    input_file = 'data/dicts/vietnamese-stopwords-dash.txt'
    output_file = 'data/dicts/vietnamese-stopwords.txt'
    
    with open(input_file, 'r', encoding='utf-8') as f:
        stopwords = f.readlines()
    
    # Chuyển _ thành space
    stopwords_converted = [word.strip().replace('_', ' ') for word in stopwords]
    
    # Loại bỏ duplicates và sort
    stopwords_converted = sorted(set(stopwords_converted))
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(stopwords_converted))
    
    print(f"Converted {len(stopwords_converted)} stopwords")
    print(f"Saved to: {output_file}")

if __name__ == '__main__':
    convert_stopwords_to_space()