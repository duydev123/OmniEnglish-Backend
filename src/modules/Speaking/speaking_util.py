# src/modules/Speaking/speaking_util.py
from fastapi import UploadFile, HTTPException, status
from typing import Optional, Dict, Any
import os
import cloudinary
import cloudinary.uploader

import json
import httpx
import tempfile
import azure.cognitiveservices.speech as speechsdk
from google import genai
from google.genai import types

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)


class SpeakingUtil:
    # ==========================================
    # 1. NHÓM XỬ LÝ FILE ÂM THANH & LƯU TRỮ (AUDIO & CLOUD)
    # ==========================================
    
    @staticmethod
    async def validate_audio_file(audio_file: UploadFile) -> bool:
        allowed_extensions = [".webm", ".wav", ".m4a", ".mp3", ".ogg"]
        filename = audio_file.filename.lower() if audio_file.filename else ""
        
        if not any(filename.endswith(ext) for ext in allowed_extensions):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Định dạng file âm thanh không hợp lệ! (Chấp nhận .webm, .wav, .m4a, .mp3, .ogg)"
            )
        return True

    @staticmethod
    async def upload_audio_to_cloud(audio_file: UploadFile, folder: str = "speaking_audios") -> str:
        """
        Upload file âm thanh lên Cloudinary.
        Trả về URL trực tiếp của file âm thanh.
        """
        try:
            # Đọc bytes từ file upload
            contents = await audio_file.read()
            
            # Gọi API Cloudinary để upload.
            # resource_type="video" được dùng chung cho cả video và audio trên Cloudinary.
            result = cloudinary.uploader.upload(
                contents,
                folder=f"omni_english/{folder}",
                resource_type="video",
                format="wav"
            )
            
            # Trả về URL bảo mật (HTTPS) của file vừa upload
            return result.get("secure_url")
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi khi upload âm thanh lên Cloudinary: {str(e)}"
            )

    # ==========================================
    # 2. NHÓM TRÍ TUỆ NHÂN TẠO (SPEECH-TO-TEXT)
    # ==========================================

    @staticmethod
    async def evaluate_single_audio_segment(audio_url: str, prompt_text: str) -> dict:
        """
        Gọi Azure Speech (lấy Pronunciation, Fluency, Transcript) 
        + Gọi Gemini AI (lấy Grammar, Lexical, Overall, Feedback).
        """
        # ==========================================
        # 1. TẢI AUDIO TỪ CLOUD VỀ FILE TẠM
        # ==========================================
        # Azure SDK yêu cầu đọc từ file local hoặc stream. Ta tải file từ audio_url về.
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(audio_url)
                    response.raise_for_status()
                    tmp_file.write(response.content)
                    tmp_file_path = tmp_file.name
                    tmp_file.close() 
                    print("tai len roi \n")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi khi tải file âm thanh từ Cloud để phân tích: {str(e)}"
            )

        # ==========================================
        # 2. GỌI AZURE SPEECH SDK (PRONUNCIATION & FLUENCY)
        # ==========================================
        speech_key = os.getenv("AZURE_SPEECH_KEY")
        service_region = os.getenv("AZURE_SPEECH_REGION")
        
        if not speech_key or not service_region:
            raise HTTPException(status_code=500, detail="Chưa cấu hình AZURE_SPEECH_KEY và AZURE_SPEECH_REGION")

        speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
        audio_config = speechsdk.audio.AudioConfig(filename=tmp_file_path)

        # Cấu hình Pronunciation Assessment (Chấm điểm Unscripted - Không cần đoạn text chuẩn)
        pronunciation_config = speechsdk.PronunciationAssessmentConfig(
            reference_text="", # Để trống để Azure tự nhận diện (Unscripted)
            grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
            granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
            enable_miscue=False
        )
        
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
        pronunciation_config.apply_to(speech_recognizer)

        # Chạy nhận diện (Lưu ý: recognize_once_async phù hợp cho câu ngắn < 15s. Nếu đoạn dài hơn, cần dùng continuous recognition)
        result = speech_recognizer.recognize_once_async().get()
        print("châm điểm xong", result.text)
        print("\n")
        print(vars(result))

        print("\n")


        if tmp_file_path and os.path.exists(tmp_file_path):
                try:
                    os.remove(tmp_file_path)
                except Exception as del_err:
                    print(f"[Warning] Không thể xóa file tạm {tmp_file_path}: {del_err}")
        # Xóa file tạm sau khi xử lý xong
        # os.remove(tmp_file_path)

        transcript = ""
        pronunciation_score = 0.0
        fluency_score = 0.0
        words_detail_list = []

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                transcript = result.text
                pronunciation_result = speechsdk.PronunciationAssessmentResult(result)
                pronunciation_score = round((pronunciation_result.pronunciation_score / 100) * 9.0, 1)
                fluency_score = round((pronunciation_result.fluency_score / 100) * 9.0, 1)

                # BÓC TÁCH CHI TIẾT TỪNG TỪ VÀ ÂM TIẾT
                # 1. Bảng map từ ARPAbet/SAPI (Azure default) sang IPA chuẩn quốc tế
                AZURE_TO_IPA = {
                    "aa": "ɑ", "ae": "æ", "ah": "ʌ", "ao": "ɔ", "aw": "aʊ", "ax": "ə", "ay": "aɪ",
                    "b": "b", "ch": "tʃ", "d": "d", "dh": "ð", "eh": "ɛ", "er": "ər", "ey": "eɪ",
                    "f": "f", "g": "g", "hh": "h", "ih": "ɪ", "iy": "i", "jh": "dʒ", "k": "k",
                    "l": "l", "m": "m", "n": "n", "ng": "ŋ", "ow": "oʊ", "oy": "ɔɪ", "p": "p",
                    "r": "r", "s": "s", "sh": "ʃ", "t": "t", "th": "θ", "uh": "ʊ", "uw": "u",
                    "v": "v", "w": "w", "y": "j", "z": "z", "zh": "ʒ"
                }

                # 2. Bóc tách và quy đổi
                for word_obj in pronunciation_result.words:
                    phonemes_list = []
                    
                    # Lấy điểm từng âm tiết cấu tạo nên từ đó
                    if hasattr(word_obj, 'phonemes') and word_obj.phonemes:
                        for p in word_obj.phonemes:
                            raw_phoneme = p.phoneme.lower()
                            
                            # Áp dụng bảng quy đổi sang IPA (Nếu có ký tự lạ không lường trước thì giữ nguyên gốc)
                            ipa_phoneme = AZURE_TO_IPA.get(raw_phoneme, raw_phoneme)
                            
                            phonemes_list.append({
                                "phoneme": ipa_phoneme,
                                "accuracy_score": p.accuracy_score
                            })
                    err_type_str = word_obj.error_type.name if hasattr(word_obj.error_type, 'name') else str(word_obj.error_type)
                    words_detail_list.append({
                        "word": word_obj.word,
                        "accuracy_score": word_obj.accuracy_score,
                        "error_type": err_type_str, # Mispronunciation, Omission, Insertion...
                        "phonemes": phonemes_list
                    })
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể nhận diện được giọng nói trong file audio."
            )

        # ==========================================
        # 3. GỌI GEMINI AI (GRAMMAR, LEXICAL & FEEDBACK)
        # ==========================================
        genai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
        ai_prompt = f"""
        Bạn là một giám khảo IELTS. Thí sinh vừa trả lời một câu hỏi Speaking.
        - Câu hỏi: "{prompt_text}"
        - Câu trả lời của thí sinh (Transcript do AI nhận diện): "{transcript}"
        
        Hãy thực hiện:
        1. Chấm điểm tiêu chí Từ vựng (Lexical Resource) theo thang điểm 0-9.0.
        2. Chấm điểm tiêu chí Ngữ pháp (Grammar Accuracy) theo thang điểm 0-9.0.
        3. Viết nhận xét chi tiết bằng Tiếng Việt (chỉ ra lỗi sai ngữ pháp, cách dùng từ chưa hay và đưa ra câu gợi ý tốt hơn).
        
        TRẢ VỀ DUY NHẤT ĐỊNH DẠNG JSON (Không dùng markdown block):
        {{
            "lexical_score": 6.5,
            "grammar_score": 6.0,
            "feedback": "Nhận xét của bạn ở đây..."
        }}
        """

        try:
            gemini_response = genai_client.models.generate_content(
                model='gemini-3.6-flash', # Model cấu hình trong project
                contents=ai_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2
                )
            )
            print("goi gemini xong ")
            
            # Parse JSON từ Gemini
            raw_output = gemini_response.text.strip()
            if raw_output.startswith("```"):
                raw_output = raw_output.split("```")[1]
                if raw_output.startswith("json"):
                    raw_output = raw_output[4:]
            
            ai_data = json.loads(raw_output.strip())
            lexical_score = float(ai_data.get("lexical_score", 0.0))
            grammar_score = float(ai_data.get("grammar_score", 0.0))
            raw_feedback = ai_data.get("feedback", "")
            feedback = raw_feedback.replace('\\n', '\n').replace('\\"', '"').replace('\"', '"')
            
        except Exception as e:
            # Fallback nếu Gemini lỗi
            lexical_score = 0.0
            grammar_score = 0.0
            feedback = f"Hệ thống AI nhận xét đang gặp lỗi: {str(e)}"

        # ==========================================
        # 4. TÍNH OVERALL VÀ TRẢ VỀ DỮ LIỆU
        # ==========================================
        # Công thức tính trung bình cộng 4 kỹ năng, làm tròn đến 0.5 (IELTS format)
        raw_overall = (pronunciation_score + fluency_score + lexical_score + grammar_score) / 4
        overall_score = round(raw_overall * 2) / 2
        
        return {
            "transcript": transcript,
            "pronunciation_score": pronunciation_score,
            "fluency_score": fluency_score,
            "lexical_score": lexical_score,
            "grammar_score": grammar_score,
            "segment_score": overall_score,
            "feedback": feedback,
            "words_detail": words_detail_list # Trả thêm list này
        }

    @staticmethod
    async def evaluate_shadowing_audio(audio_url: str, reference_text: str) -> dict:
        """
        Hàm gọi Azure Speech dành riêng cho Shadowing. 
        Tải file WAV chuẩn từ Cloudinary và chấm điểm dựa trên reference_text.
        """
        import os
        import tempfile
        import httpx
        from fastapi import HTTPException
        import azure.cognitiveservices.speech as speechsdk

        # 1. Tải file WAV (đã được convert) từ Cloudinary về lưu tạm
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(audio_url)
                    response.raise_for_status()
                    tmp_file.write(response.content)
                    tmp_file_path = tmp_file.name
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Lỗi tải file âm thanh chuẩn từ Cloud: {str(e)}"
            )

        # 2. Gọi Azure Speech
        speech_key = os.getenv("AZURE_SPEECH_KEY")
        service_region = os.getenv("AZURE_SPEECH_REGION")
        
        speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
        audio_config = speechsdk.audio.AudioConfig(filename=tmp_file_path)
        
        # BẬT reference_text ĐỂ CHẤM SHADOWING CHUẨN XÁC
        pronunciation_config = speechsdk.PronunciationAssessmentConfig(
            reference_text=reference_text,
            grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
            granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
            enable_miscue=True
        )
        
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
        pronunciation_config.apply_to(speech_recognizer)
        
        result = speech_recognizer.recognize_once_async().get()
        
        # Xóa file tạm sau khi chấm xong
        # if os.path.exists(tmp_file_path):
        #     os.remove(tmp_file_path)

        # 3. Trích xuất dữ liệu trả về
        transcript = result.text if result.reason == speechsdk.ResultReason.RecognizedSpeech else ""
        accuracy_score = 0.0
        fluency_score = 0.0
        words_detail_list = []

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            pronunciation_result = speechsdk.PronunciationAssessmentResult(result)
            accuracy_score = round(pronunciation_result.pronunciation_score, 1)
            fluency_score = round(pronunciation_result.fluency_score, 1)
            
            for word_obj in pronunciation_result.words:
                err_type_str = word_obj.error_type.name if hasattr(word_obj.error_type, 'name') else str(word_obj.error_type)
                
                phonemes_list = []
                if hasattr(word_obj, 'phonemes') and word_obj.phonemes:
                    for p in word_obj.phonemes:
                        phonemes_list.append({
                            "phoneme": p.phoneme.lower(),
                            "accuracy_score": p.accuracy_score
                        })
                
                words_detail_list.append({
                    "word": word_obj.word,
                    "accuracy_score": word_obj.accuracy_score,
                    "error_type": err_type_str,
                    "phonemes": phonemes_list
                })
        else:
            raise HTTPException(status_code=400, detail="Không thể nhận diện giọng nói, vui lòng thử lại.")

        return {
            "accuracy_score": accuracy_score,
            "fluency_score": fluency_score,
            "transcript": transcript,
            "words_detail": words_detail_list
        }