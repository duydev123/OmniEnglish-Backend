import os
from google import genai

def list_available_models():
    # Khởi tạo client (Đảm bảo bạn đã set GEMINI_API_KEY trong biến môi trường)
    # Hoặc thay trực tiếp api_key="AIzaSy..." vào đây để test nhanh
    client = genai.Client(api_key="GEMINI_API_KEY")
    
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