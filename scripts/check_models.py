import os
import sys
from google import genai
from dotenv import load_dotenv

load_dotenv()

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def list_available_models():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Không tìm thấy GEMINI_API_KEY trong file .env!")
        return
    client = genai.Client(api_key=api_key)
    
    print("Đang tải danh sách models...\n")
    
    try:
        # Gọi API lấy danh sách model
        models = client.models.list()
        
        print("=== CÁC MODEL BẠN CÓ THỂ SỬ DỤNG ===")
        for model in models:
            # Chỉ in ra các model hỗ trợ generateContent (tạo văn bản)
            if "generateContent" in model.supported_actions:
                print(f"- Tên model: {model.name}")
                print(f"  Phiên bản: {model.version}")
                print(f"  Mô tả: {model.description}\n")
                
    except Exception as e:
        print(f"Lỗi khi lấy danh sách: {e}")

if __name__ == "__main__":
    list_available_models()