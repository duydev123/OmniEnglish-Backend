import os
import sys
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

print("=" * 80)
print("🔍 BÁO CÁO PHÂN TÍCH CẤU TRÚC DỮ LIỆU THỰC TẾ TRONG THƯ MỤC 'data/'")
print("=" * 80)

# 1. Oxford 3000 (package.txt)
pkg_path = os.path.join(DATA_DIR, "package.txt")
if os.path.exists(pkg_path):
    print(f"\n1. 📘 File: 'data/package.txt' (Size: {os.path.getsize(pkg_path):,} bytes)")
    with open(pkg_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        data = json.loads(content)
        print(f"   - Loại dữ liệu: {type(data).__name__}")
        if isinstance(data, dict):
            print(f"   - Danh sách Keys (Cấp độ CEFR): {list(data.keys())}")
            for k in data.keys():
                items = data[k]
                sample = items[:3] if isinstance(items, list) else items
                cnt = len(items) if isinstance(items, list) else 0
                print(f"     * Level '{k}': {cnt} từ | Mẫu: {sample}")
        elif isinstance(data, list):
            print(f"   - Tổng số phần tử: {len(data)}")
            print(f"   - Mẫu phần tử đầu tiên: {data[0]}")

# 2. TOEFL / TOEIC Essential Vocabulary (toefl_essential_vocabulary.json)
toefl_path = os.path.join(DATA_DIR, "toefl_essential_vocabulary.json")
if os.path.exists(toefl_path):
    print(f"\n2. 💼 File: 'data/toefl_essential_vocabulary.json' (Size: {os.path.getsize(toefl_path):,} bytes)")
    with open(toefl_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        print(f"   - Loại dữ liệu: {type(data).__name__}")
        if isinstance(data, list):
            print(f"   - Tổng số từ vựng: {len(data)}")
            print(f"   - Cấu trúc mẫu phần tử đầu tiên:")
            print(json.dumps(data[0], indent=4, ensure_ascii=False))
        elif isinstance(data, dict):
            keys = list(data.keys())[:5]
            print(f"   - Số lượng từ: {len(data)} | Keys mẫu: {keys}")
            first_key = list(data.keys())[0]
            print(f"   - Cấu trúc phần tử '{first_key}':")
            print(json.dumps(data[first_key], indent=4, ensure_ascii=False))

# 3. MIDAS / EN Idioms (EN_Idioms.json)
idioms_path = os.path.join(DATA_DIR, "EN_Idioms.json")
if os.path.exists(idioms_path):
    print(f"\n3. 🗣️ File: 'data/EN_Idioms.json' (Size: {os.path.getsize(idioms_path):,} bytes)")
    with open(idioms_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        print(f"   - Loại dữ liệu: {type(data).__name__}")
        if isinstance(data, list):
            print(f"   - Tổng số thành ngữ: {len(data)}")
            print(f"   - Cấu trúc mẫu phần tử đầu tiên:")
            print(json.dumps(data[0], indent=4, ensure_ascii=False))
        elif isinstance(data, dict):
            print(f"   - Số lượng phần tử: {len(data)} | Keys mẫu: {list(data.keys())[:5]}")
            first_key = list(data.keys())[0]
            print(f"   - Cấu trúc phần tử '{first_key}':")
            print(json.dumps(data[first_key], indent=4, ensure_ascii=False))

print("\n" + "=" * 80)
