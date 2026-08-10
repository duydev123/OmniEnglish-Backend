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
                for word_obj in pronunciation_result.words:
                    phonemes_list = []
                    # Lấy điểm từng âm tiết cấu tạo nên từ đó
                    if hasattr(word_obj, 'phonemes') and word_obj.phonemes:
                        for p in word_obj.phonemes:
                            phonemes_list.append({
                                "phoneme": p.phoneme,
                                "accuracy_score": p.accuracy_score
                            })
                    
                    words_detail_list.append({
                        "word": word_obj.word,
                        "accuracy_score": word_obj.accuracy_score,
                        "error_type": str(word_obj.error_type), # Mispronunciation, Omission, Insertion...
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
            feedback = ai_data.get("feedback", "")
            
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

    # ==========================================
    # 3. NHÓM THAO TÁC CƠ SỞ DỮ LIỆU (DATABASE & SESSION)
    # ==========================================

    @staticmethod
    async def get_valid_session(session_id: str, user_id: str):
        """
        Query và validate UserSpeakingTestSessionModel.
        Kiểm tra session có tồn tại, thuộc về user_id và đang có status == "IN_PROGRESS" hay không.
        Throw HTTPException(404/403) nếu không hợp lệ.
        """
        pass

    @staticmethod
    async def update_session_question_detail(
        session_id: str,
        prompt_id: str,
        question_text: str,
        user_transcript: str,
        user_audio_url: str
    ) -> bool:
        """
        Cập nhật hoặc thêm mới 1 phần tử QuestionDetailItem vào mảng `questions_detail`
        trong UserSpeakingTestSessionModel.
        """
        pass



    # {'_RecognitionResult__handle': <azure.cognitiveservices.speech.interop._Handle object at 0x000002447BA13E50>, '_offset': 16600000, '_duration': 130700000, '_channel': 0, '_result_id': 'c5b167f227fe45b5812a8b243f93dda6', '_reason': <ResultReason.RecognizedSpeech: 3>, '_text': 'Yes, I know I enjoy listening to music, watching movie and shevlin. I also like spending time with my friends in new things.', '_propbag': <azure.cognitiveservices.speech.PropertyCollection object at 0x000002447BA2D350>, '_json': '{"Id":"c5b167f227fe45b5812a8b243f93dda6","RecognitionStatus":"Success","Offset":16600000,"Duration":130700000,"Channel":0,"DisplayText":"Yes, I know I enjoy listening to music, watching movie and shevlin. I also like spending time with my friends in new things.","SNR":7.112994,"NBest":[{"Confidence":0.759454,"Lexical":"yes i know i enjoy listening to music watching movie and shevlin i also like spending time with my friends in new things","ITN":"yes i know i enjoy listening to music watching movie and shevlin i also like spending time with my friends in new things","MaskedITN":"yes i know i enjoy listening to music watching movie and shevlin i also like spending time with my friends in new things","Display":"Yes, I know I enjoy listening to music, watching movie and shevlin. I also like spending time with my friends in new things.","PronunciationAssessment":{"AccuracyScore":80.0,"FluencyScore":73.0,"CompletenessScore":100.0,"PronScore":75.8},"Words":[{"Word":"yes","Offset":16600000,"Duration":5700000,"PronunciationAssessment":{"AccuracyScore":97.0,"ErrorType":"None"},"Syllables":[{"Syllable":"yehs","Grapheme":"yes","PronunciationAssessment":{"AccuracyScore":75.0},"Offset":16600000,"Duration":5700000}],"Phonemes":[{"Phoneme":"y","PronunciationAssessment":{"AccuracyScore":71.0},"Offset":16600000,"Duration":2300000},{"Phoneme":"eh","PronunciationAssessment":{"AccuracyScore":94.0},"Offset":19000000,"Duration":900000},{"Phoneme":"s","PronunciationAssessment":{"AccuracyScore":72.0},"Offset":20000000,"Duration":2300000}]},{"Word":"i","Offset":22400000,"Duration":900000,"PronunciationAssessment":{"AccuracyScore":97.0,"ErrorType":"None"},"Syllables":[{"Syllable":"ay","Grapheme":"i","PronunciationAssessment":{"AccuracyScore":97.0},"Offset":22400000,"Duration":900000}],"Phonemes":[{"Phoneme":"ay","PronunciationAssessment":{"AccuracyScore":97.0},"Offset":22400000,"Duration":900000}]},{"Word":"know","Offset":23400000,"Duration":4700000,"PronunciationAssessment":{"AccuracyScore":91.0,"ErrorType":"None"},"Syllables":[{"Syllable":"now","Grapheme":"know","PronunciationAssessment":{"AccuracyScore":72.0},"Offset":23400000,"Duration":4700000}],"Phonemes":[{"Phoneme":"n","PronunciationAssessment":{"AccuracyScore":81.0},"Offset":23400000,"Duration":1700000},{"Phoneme":"ow","PronunciationAssessment":{"AccuracyScore":66.0},"Offset":25200000,"Duration":2900000}]},{"Word":"i","Offset":28200000,"Duration":1900000,"PronunciationAssessment":{"AccuracyScore":97.0,"ErrorType":"None"},"Syllables":[{"Syllable":"ay","Grapheme":"i","PronunciationAssessment":{"AccuracyScore":97.0},"Offset":28200000,"Duration":1900000}],"Phonemes":[{"Phoneme":"ay","PronunciationAssessment":{"AccuracyScore":97.0},"Offset":28200000,"Duration":1900000}]},{"Word":"enjoy","Offset":30200000,"Duration":4700000,"PronunciationAssessment":{"AccuracyScore":82.0,"ErrorType":"None"},"Syllables":[{"Syllable":"ihn","Grapheme":"en","PronunciationAssessment":{"AccuracyScore":72.0},"Offset":30200000,"Duration":2100000},{"Syllable":"jhoy","Grapheme":"joy","PronunciationAssessment":{"AccuracyScore":100.0},"Offset":32400000,"Duration":2500000}],"Phonemes":[{"Phoneme":"ih","PronunciationAssessment":{"AccuracyScore":54.0},"Offset":30200000,"Duration":700000},{"Phoneme":"n","PronunciationAssessment":{"AccuracyScore":82.0},"Offset":31000000,"Duration":1300000},{"Phoneme":"jh","PronunciationAssessment":{"AccuracyScore":100.0},"Offset":32400000,"Duration":1300000},{"Phoneme":"oy","PronunciationAssessment":{"AccuracyScore":100.0},"Offset":33800000,"Duration":1100000}]},{"Word":"listening","Offset":35000000,"Duration":7500000,"PronunciationAssessment":{"AccuracyScore":44.0,"ErrorType":"Mispronunciation"},"Syllables":[{"Syllable":"lihs","Grapheme":"lis","PronunciationAssessment":{"AccuracyScore":36.0},"Offset":35000000,"Duration":3500000},{"Syllable":"ax","Grapheme":"te","PronunciationAssessment":{"AccuracyScore":32.0},"Offset":38600000,"Duration":500000},{"Syllable":"nihng","Grapheme":"ning","PronunciationAssessment":{"AccuracyScore":59.0},"Offset":39200000,"Duration":3300000}],"Phonemes":[{"Phoneme":"l","PronunciationAssessment":{"AccuracyScore":32.0},"Offset":35000000,"Duration":900000},{"Phoneme":"ih","PronunciationAssessment":{"AccuracyScore":37.0},"Offset":36000000,"Duration":700000},{"Phoneme":"s","PronunciationAssessment":{"AccuracyScore":37.0},"Offset":36800000,"Duration":1700000},{"Phoneme":"ax","PronunciationAssessment":{"AccuracyScore":32.0},"Offset":38600000,"Duration":500000},{"Phoneme":"n","PronunciationAssessment":{"AccuracyScore":41.0},"Offset":39200000,"Duration":500000},{"Phoneme":"ih","PronunciationAssessment":{"AccuracyScore":100.0},"Offset":39800000,"Duration":900000},{"Phoneme":"ng","PronunciationAssessment":{"AccuracyScore":43.0},"Offset":40800000,"Duration":1700000}]},{"Word":"to","Offset":42600000,"Duration":2400000,"PronunciationAssessment":{"AccuracyScore":97.0,"ErrorType":"None"},"Syllables":[{"Syllable":"tow","Grapheme":"to","PronunciationAssessment":{"AccuracyScore":86.0},"Offset":42600000,"Duration":2400000}],"Phonemes":[{"Phoneme":"t","PronunciationAssessment":{"AccuracyScore":100.0},"Offset":42600000,"Duration":700000},{"Phoneme":"ow","PronunciationAssessment":{"AccuracyScore":80.0},"Offset":43400000,"Duration":1600000}]},{"Word":"music","Offset":45100000,"Duration":4700000,"PronunciationAssessment":{"AccuracyScore":47.0,"ErrorType":"Mispronunciation"},"Syllables":[{"Syllable":"myuw","Grapheme":"mu","PronunciationAssessment":{"AccuracyScore":44.0},"Offset":45100000,"Duration":1800000},{"Syllable":"zihk","Grapheme":"sic","PronunciationAssessment":{"AccuracyScore":54.0},"Offset":47000000,"Duration":2800000}],"Phonemes":[{"Phoneme":"m","PronunciationAssessment":{"AccuracyScore":44.0},"Offset":45100000,"Duration":900000},{"Phoneme":"y","PronunciationAssessment":{"AccuracyScore":37.0},"Offset":46100000,"Duration":300000},{"Phoneme":"uw","PronunciationAssessment":{"AccuracyScore":48.0},"Offset":46500000,"Duration":400000},{"Phoneme":"z","PronunciationAssessment":{"AccuracyScore":66.0},"Offset":47000000,"Duration":1300000},{"Phoneme":"ih","PronunciationAssessment":{"AccuracyScore":62.0},"Offset":48400000,"Duration":700000},{"Phoneme":"k","PronunciationAssessment":{"AccuracyScore":19.0},"Offset":49200000,"Duration":600000}]},{"Word":"watching","Offset":54400000,"Duration":5400000,"PronunciationAssessment":{"AccuracyScore":47.0,"ErrorType":"Mispronunciation"},"Syllables":[{"Syllable":"waach","Grapheme":"watch","PronunciationAssessment":{"AccuracyScore":45.0},"Offset":54400000,"Duration":3100000},{"Syllable":"ihng","Grapheme":"ing","PronunciationAssessment":{"AccuracyScore":51.0},"Offset":57600000,"Duration":2200000}],"Phonemes":[{"Phoneme":"w","PronunciationAssessment":{"AccuracyScore":28.0},"Offset":54400000,"Duration":900000},{"Phoneme":"aa","PronunciationAssessment":{"AccuracyScore":42.0},"Offset":55400000,"Duration":700000},{"Phoneme":"ch","PronunciationAssessment":{"AccuracyScore":58.0},"Offset":56200000,"Duration":1300000},{"Phoneme":"ih","PronunciationAssessment":{"AccuracyScore":61.0},"Offset":57600000,"Duration":700000},{"Phoneme":"ng","PronunciationAssessment":{"AccuracyScore":46.0},"Offset":58400000,"Duration":1400000}]},{"Word":"movie","Offset":59900000,"Duration":6000000,"PronunciationAssessment":{"AccuracyScore":50.0,"ErrorType":"Mispronunciation"},"Syllables":[{"Syllable":"muw","Grapheme":"mo","PronunciationAssessment":{"AccuracyScore":79.0},"Offset":59900000,"Duration":2000000},{"Syllable":"viy","Grapheme":"vie","PronunciationAssessment":{"AccuracyScore":37.0},"Offset":62000000,"Duration":3900000}],"Phonemes":[{"Phoneme":"m","PronunciationAssessment":{"AccuracyScore":51.0},"Offset":59900000,"Duration":800000},{"Phoneme":"uw","PronunciationAssessment":{"AccuracyScore":100.0},"Offset":60800000,"Duration":1100000},{"Phoneme":"v","PronunciationAssessment":{"AccuracyScore":36.0},"Offset":62000000,"Duration":1700000},{"Phoneme":"iy","PronunciationAssessment":{"AccuracyScore":38.0},"Offset":63800000,"Duration":2100000}]},{"Word":"and","Offset":66000000,"Duration":4300000,"PronunciationAssessment":{"AccuracyScore":97.0,"ErrorType":"None"},"Syllables":[{"Syllable":"aend","Grapheme":"and","PronunciationAssessment":{"AccuracyScore":52.0},"Offset":66000000,"Duration":4300000}],"Phonemes":[{"Phoneme":"ae","PronunciationAssessment":{"AccuracyScore":52.0},"Offset":66000000,"Duration":700000},{"Phoneme":"n","PronunciationAssessment":{"AccuracyScore":48.0},"Offset":66800000,"Duration":1600000},{"Phoneme":"d","PronunciationAssessment":{"AccuracyScore":55.0},"Offset":68500000,"Duration":1800000}]},{"Word":"shevlin","Offset":70400000,"Duration":7300000,"PronunciationAssessment":{"AccuracyScore":88.0,"ErrorType":"None"},"Syllables":[{"Syllable":"shehv","PronunciationAssessment":{"AccuracyScore":86.0},"Offset":70400000,"Duration":2700000},{"Syllable":"lihn","PronunciationAssessment":{"AccuracyScore":60.0},"Offset":73200000,"Duration":4500000}],"Phonemes":[{"Phoneme":"sh","PronunciationAssessment":{"AccuracyScore":78.0},"Offset":70400000,"Duration":900000},{"Phoneme":"eh","PronunciationAssessment":{"AccuracyScore":84.0},"Offset":71400000,"Duration":700000},{"Phoneme":"v","PronunciationAssessment":{"AccuracyScore":96.0},"Offset":72200000,"Duration":900000},{"Phoneme":"l","PronunciationAssessment":{"AccuracyScore":92.0},"Offset":73200000,"Duration":700000},{"Phoneme":"ih","PronunciationAssessment":{"AccuracyScore":79.0},"Offset":74000000,"Duration":700000},{"Phoneme":"n","PronunciationAssessment":{"AccuracyScore":46.0},"Offset":74800000,"Duration":2900000}]},{"Word":"i","Offset":81700000,"Duration":4100000,"PronunciationAssessment":{"AccuracyScore":97.0,"ErrorType":"None"},"Syllables":[{"Syllable":"ay","Grapheme":"i","PronunciationAssessment":{"AccuracyScore":97.0},"Offset":81700000,"Duration":4100000}],"Phonemes":[{"Phoneme":"ay","PronunciationAssessment":{"AccuracyScore":97.0},"Offset":81700000,"Duration":4100000}]},{"Word":"also","Offset":85900000,"Duration":5800000,"PronunciationAssessment":{"AccuracyScore":21.0,"ErrorType":"Mispronunciation"},"Syllables":[{"Syllable":"aol","Grapheme":"al","PronunciationAssessment":{"AccuracyScore":16.0},"Offset":85900000,"Duration":2000000},{"Syllable":"sow","Grapheme":"so","PronunciationAssessment":{"AccuracyScore":50.0},"Offset":88000000,"Duration":3700000}],"Phonemes":[{"Phoneme":"ao","PronunciationAssessment":{"AccuracyScore":18.0},"Offset":85900000,"Duration":700000},{"Phoneme":"l","PronunciationAssessment":{"AccuracyScore":15.0},"Offset":86700000,"Duration":1200000},{"Phoneme":"s","PronunciationAssessment":{"AccuracyScore":47.0},"Offset":88000000,"Duration":1900000},{"Phoneme":"ow","PronunciationAssessment":{"AccuracyScore":53.0},"Offset":90000000,"Duration":1700000}]},{"Word":"like","Offset":91800000,"Duration":3800000,"PronunciationAssessment":{"AccuracyScore":82.0,"ErrorType":"None"},"Syllables":[{"Syllable":"layk","Grapheme":"like","PronunciationAssessment":{"AccuracyScore":60.0},"Offset":91800000,"Duration":3800000}],"Phonemes":[{"Phoneme":"l","PronunciationAssessment":{"AccuracyScore":52.0},"Offset":91800000,"Duration":2100000},{"Phoneme":"ay","PronunciationAssessment":{"AccuracyScore":79.0},"Offset":94000000,"Duration":1100000},{"Phoneme":"k","PronunciationAssessment":{"AccuracyScore":47.0},"Offset":95200000,"Duration":400000}]},{"Word":"spending","Offset":95700000,"Duration":6000000,"PronunciationAssessment":{"AccuracyScore":94.0,"ErrorType":"None"},"Syllables":[{"Syllable":"spehn","Grapheme":"spen","PronunciationAssessment":{"AccuracyScore":79.0},"Offset":95700000,"Duration":3000000},{"Syllable":"dihng","Grapheme":"ding","PronunciationAssessment":{"AccuracyScore":84.0},"Offset":98800000,"Duration":2900000}],"Phonemes":[{"Phoneme":"s","PronunciationAssessment":{"AccuracyScore":56.0},"Offset":95700000,"Duration":600000},{"Phoneme":"p","PronunciationAssessment":{"AccuracyScore":80.0},"Offset":96400000,"Duration":700000},{"Phoneme":"eh","PronunciationAssessment":{"AccuracyScore":80.0},"Offset":97200000,"Duration":600000},{"Phoneme":"n","PronunciationAssessment":{"AccuracyScore":94.0},"Offset":97900000,"Duration":800000},{"Phoneme":"d","PronunciationAssessment":{"AccuracyScore":100.0},"Offset":98800000,"Duration":500000},{"Phoneme":"ih","PronunciationAssessment":{"AccuracyScore":100.0},"Offset":99400000,"Duration":900000},{"Phoneme":"ng","PronunciationAssessment":{"AccuracyScore":65.0},"Offset":100400000,"Duration":1300000}]},{"Word":"time","Offset":101800000,"Duration":3700000,"PronunciationAssessment":{"AccuracyScore":94.0,"ErrorType":"None"},"Syllables":[{"Syllable":"taym","Grapheme":"time","PronunciationAssessment":{"AccuracyScore":57.0},"Offset":101800000,"Duration":3700000}],"Phonemes":[{"Phoneme":"t","PronunciationAssessment":{"AccuracyScore":18.0},"Offset":101800000,"Duration":900000},{"Phoneme":"ay","PronunciationAssessment":{"AccuracyScore":96.0},"Offset":102800000,"Duration":1200000},{"Phoneme":"m","PronunciationAssessment":{"AccuracyScore":50.0},"Offset":104100000,"Duration":1400000}]},{"Word":"with","Offset":105600000,"Duration":3700000,"PronunciationAssessment":{"AccuracyScore":94.0,"ErrorType":"None"},"Syllables":[{"Syllable":"wihdh","Grapheme":"with","PronunciationAssessment":{"AccuracyScore":63.0},"Offset":105600000,"Duration":3700000}],"Phonemes":[{"Phoneme":"w","PronunciationAssessment":{"AccuracyScore":78.0},"Offset":105600000,"Duration":900000},{"Phoneme":"ih","PronunciationAssessment":{"AccuracyScore":77.0},"Offset":106600000,"Duration":500000},{"Phoneme":"dh","PronunciationAssessment":{"AccuracyScore":53.0},"Offset":107200000,"Duration":2100000}]},{"Word":"my","Offset":109400000,"Duration":4800000,"PronunciationAssessment":{"AccuracyScore":97.0,"ErrorType":"None"},"Syllables":[{"Syllable":"may","Grapheme":"my","PronunciationAssessment":{"AccuracyScore":72.0},"Offset":109400000,"Duration":4800000}],"Phonemes":[{"Phoneme":"m","PronunciationAssessment":{"AccuracyScore":99.0},"Offset":109400000,"Duration":1100000},{"Phoneme":"ay","PronunciationAssessment":{"AccuracyScore":63.0},"Offset":110600000,"Duration":3600000}]},{"Word":"friends","Offset":116400000,"Duration":5700000,"PronunciationAssessment":{"AccuracyScore":73.0,"ErrorType":"None"},"Syllables":[{"Syllable":"frehndz","Grapheme":"friends","PronunciationAssessment":{"AccuracyScore":58.0},"Offset":116400000,"Duration":5700000}],"Phonemes":[{"Phoneme":"f","PronunciationAssessment":{"AccuracyScore":26.0},"Offset":116400000,"Duration":500000},{"Phoneme":"r","PronunciationAssessment":{"AccuracyScore":55.0},"Offset":117000000,"Duration":500000},{"Phoneme":"eh","PronunciationAssessment":{"AccuracyScore":56.0},"Offset":117600000,"Duration":900000},{"Phoneme":"n","PronunciationAssessment":{"AccuracyScore":72.0},"Offset":118600000,"Duration":500000},{"Phoneme":"d","PronunciationAssessment":{"AccuracyScore":76.0},"Offset":119200000,"Duration":1100000},{"Phoneme":"z","PronunciationAssessment":{"AccuracyScore":53.0},"Offset":120400000,"Duration":1700000}]},{"Word":"in","Offset":134900000,"Duration":2700000,"PronunciationAssessment":{"AccuracyScore":97.0,"ErrorType":"None"},"Syllables":[{"Syllable":"ihn","Grapheme":"in","PronunciationAssessment":{"AccuracyScore":80.0},"Offset":134900000,"Duration":2700000}],"Phonemes":[{"Phoneme":"ih","PronunciationAssessment":{"AccuracyScore":80.0},"Offset":134900000,"Duration":1000000},{"Phoneme":"n","PronunciationAssessment":{"AccuracyScore":80.0},"Offset":136000000,"Duration":1600000}]},{"Word":"new","Offset":137700000,"Duration":2700000,"PronunciationAssessment":{"AccuracyScore":80.0,"ErrorType":"None"},"Syllables":[{"Syllable":"nuw","Grapheme":"new","PronunciationAssessment":{"AccuracyScore":80.0},"Offset":137700000,"Duration":2700000}],"Phonemes":[{"Phoneme":"n","PronunciationAssessment":{"AccuracyScore":80.0},"Offset":137700000,"Duration":1200000},{"Phoneme":"uw","PronunciationAssessment":{"AccuracyScore":80.0},"Offset":139000000,"Duration":1400000}]},{"Word":"things","Offset":140500000,"Duration":6800000,"PronunciationAssessment":{"AccuracyScore":70.0,"ErrorType":"None"},"Syllables":[{"Syllable":"thihngz","Grapheme":"things","PronunciationAssessment":{"AccuracyScore":57.0},"Offset":140500000,"Duration":6800000}],"Phonemes":[{"Phoneme":"th","PronunciationAssessment":{"AccuracyScore":54.0},"Offset":140500000,"Duration":1800000},{"Phoneme":"ih","PronunciationAssessment":{"AccuracyScore":61.0},"Offset":142400000,"Duration":900000},{"Phoneme":"ng","PronunciationAssessment":{"AccuracyScore":59.0},"Offset":143400000,"Duration":700000},{"Phoneme":"z","PronunciationAssessment":{"AccuracyScore":56.0},"Offset":144200000,"Duration":3100000}]}]}]}', '_error_json': '', '_properties': {<PropertyId.SpeechServiceResponse_JsonResult: 5000>: '{"Id":"c5b167f227fe45b5812a8b243f93dda6","RecognitionStatus":"Success","Offset":16600000,"Duration":130700000,"Channel":0,"DisplayText":"Yes, I know I enjoy listening to music, watching movie and shevlin. I also like spending time with my friends in new things.","SNR":7.112994,"NBest":[{"Confidence":0.759454,"Lexical":"yes i know i enjoy listening to music watching movie and shevlin i also like spending time with my friends in new things","ITN":"yes i know i enjoy listening to music watching movie and shevlin i also like spending time with my friends in new things","MaskedITN":"yes i know i enjoy listening to music watching movie and shevlin i also like spending time with my friends in new things","Display":"Yes, I know I enjoy listening to music, watching movie and shevlin. I also like spending time with my friends in new things.","PronunciationAssessment":{"AccuracyScore":80.0,"FluencyScore":73.0,"CompletenessScore":100.0,"PronScore":75.8},"Words":[{"Word":"yes","Offset":16600000,"Duration":5700000,"PronunciationAssessment":{"AccuracyScore":97.0,"ErrorType":"None"},"Syllables":[{"Syllable":"yehs","Grapheme":"yes","PronunciationAssessment":{"AccuracyScore":75.0},"Offset":16600000,"Duration":5700000}],"Phonemes":[{"Phoneme":"y","PronunciationAssessment":{"AccuracyScore":71.0},"Offset":16600000,"Duration":2300000},{"Phoneme":"eh","PronunciationAssessment":{"AccuracyScore":94.0},"Offset":19000000,"Duration":900000},{"Phoneme":"s","PronunciationAssessment":{"AccuracyScore":72.0},"Offset":20000000,"Duration":2300000}]},{"Word":"i","Offset":22400000,"Duration":900000,"PronunciationAssessment":{"AccuracyScore":97.0,"ErrorType":"None"},"Syllables":[{"Syllable":"ay","Grapheme":"i","PronunciationAssessment":{"AccuracyScore":97.0},"Offset":22400000,"Duration":900000}],"Phonemes":[{"Phoneme":"ay","PronunciationAssessment":{"AccuracyScore":97.0},"Offset":22400000,"Duration":900000}]},{"Word":"know","Offset":23400000,"Duration":4700000,"PronunciationAssessment":{"AccuracyScore":91.0,"ErrorType":"None"},"Syllables":[{"Syllable":"now","Grapheme":"know","PronunciationAssessment":{"AccuracyScore":72.0},"Offset":23400000,"Duration":4700000}],"Phonemes":[{"Phoneme":"n","PronunciationAssessment":{"AccuracyScore":81.0},"Offset":23400000,"Duration":1700000},{"Phoneme":"ow","PronunciationAssessment":{"AccuracyScore":66.0},"Offset":25200000,"Duration":2900000}]},{"Word":"i","Offset":28200000,"Duration":1900000,"PronunciationAssessment":{"AccuracyScore":97.0,"ErrorType":"None"},"Syllables":[{"Syllable":"ay","Grapheme":"i","PronunciationAssessment":{"AccuracyScore":97.0},"Offset":28200000,"Duration":1900000}],"Phonemes":[{"Phoneme":"ay","PronunciationAssessment":{"AccuracyScore":97.0},"Offset":28200000,"Duration":1900000}]},{"Word":"enjoy","Offset":30200000,"Duration":4700000,"PronunciationAssessment":{"AccuracyScore":82.0,"ErrorType":"None"},"Syllables":[{"Syllable":"ihn","Grapheme":"en","PronunciationAssessment":{"AccuracyScore":72.0},"Offset":30200000,"Duration":2100000},{"Syllable":"jhoy","Grapheme":"joy","PronunciationAssessment":{"AccuracyScore":100.0},"Offset":32400000,"Duration":2500000}],"Phonemes":[{"Phoneme":"ih","PronunciationAssessment":{"AccuracyScore":54.0},"Offset":30200000,"Duration":700000},{"Phoneme":"n","PronunciationAssessment":{"AccuracyScore":82.0},"Offset":31000000,"Duration":1300000},{"Phoneme":"jh","PronunciationAssessment":{"AccuracyScore":100.0},"Offset":32400000,"Duration":1300000},{"Phoneme":"oy","PronunciationAssessment":{"AccuracyScore":100.0},"Offset":33800000,"Duration":1100000}]},{"Word":"listening","Offset":35000000,"Duration":7500000,"PronunciationAssessment":{"AccuracyScore":44.0,"ErrorType":"Mispronunciation"},"Syllables":[{"Syllable":"lihs","Grapheme":"lis","PronunciationAssessment":{"AccuracyScore":36.0},"Offset":35000000,"Duration":3500000},{"Syllable":"ax","Grapheme":"te","PronunciationAssessment":{"AccuracyScore":32.0},"Offset":38600000,"Duration":500000},{"Syllable":"nihng","Grapheme":"ning","PronunciationAssessment":{"AccuracyScore":59.0},"Offset":39200000,"Duration":3300000}],"Phonemes":[{"Phoneme":"l","PronunciationAssessment":{"AccuracyScore":32.0},"Offset":35000000,"Duration":900000},{"Phoneme":"ih","PronunciationAssessment":{"AccuracyScore":37.0},"Offset":36000000,"Duration":700000},{"Phoneme":"s","PronunciationAssessment":{"AccuracyScore":37.0},"Offset":36800000,"Duration":1700000},{"Phoneme":"ax","PronunciationAssessment":{"AccuracyScore":32.0},"Offset":38600000,"Duration":500000},{"Phoneme":"n","PronunciationAssessment":{"AccuracyScore":41.0},"Offset":39200000,"Duration":500000},{"Phoneme":"ih","PronunciationAssessment":{"AccuracyScore":100.0},"Offset":39800000,"Duration":900000},{"Phoneme":"ng","PronunciationAssessment":{"AccuracyScore":43.0},"Offset":40800000,"Duration":1700000}]},{"Word":"to","Offset":42600000,"Duration":2400000,"PronunciationAssessment":{"AccuracyScore":97.0,"ErrorType":"None"},"Syllables":[{"Syllable":"tow","Grapheme":"to","PronunciationAssessment":{"AccuracyScore":86.0},"Offset":42600000,"Duration":2400000}],"Phonemes":[{"Phoneme":"t","PronunciationAssessment":{"AccuracyScore":100.0},"Offset":42600000,"Duration":700000},{"Phoneme":"ow","PronunciationAssessment":{"AccuracyScore":80.0},"Offset":43400000,"Duration":1600000}]},{"Word":"music","Offset":45100000,"Duration":4700000,"PronunciationAssessment":{"AccuracyScore":47.0,"ErrorType":"Mispronunciation"},"Syllables":[{"Syllable":"myuw","Grapheme":"mu","PronunciationAssessment":{"AccuracyScore":44.0},"Offset":45100000,"Duration":1800000},{"Syllable":"zihk","Grapheme":"sic","PronunciationAssessment":{"AccuracyScore":54.0},"Offset":47000000,"Duration":2800000}],"Phonemes":[{"Phoneme":"m","PronunciationAssessment":{"AccuracyScore":44.0},"Offset":45100000,"Duration":900000},{"Phoneme":"y","PronunciationAssessment":{"AccuracyScore":37.0},"Offset":46100000,"Duration":300000},{"Phoneme":"uw","PronunciationAssessment":{"AccuracyScore":48.0},"Offset":46500000,"Duration":400000},{"Phoneme":"z","PronunciationAssessment":{"AccuracyScore":66.0},"Offset":47000000,"Duration":1300000},{"Phoneme":"ih","PronunciationAssessment":{"AccuracyScore":62.0},"Offset":48400000,"Duration":700000},{"Phoneme":"k","PronunciationAssessment":{"AccuracyScore":19.0},"Offset":49200000,"Duration":600000}]},{"Word":"watching","Offset":54400000,"Duration":5400000,"PronunciationAssessment":{"AccuracyScore":47.0,"ErrorType":"Mispronunciation"},"Syllables":[{"Syllable":"waach","Grapheme":"watch","PronunciationAssessment":{"AccuracyScore":45.0},"Offset":54400000,"Duration":3100000},{"Syllable":"ihng","Grapheme":"ing","PronunciationAssessment":{"AccuracyScore":51.0},"Offset":57600000,"Duration":2200000}],"Phonemes":[{"Phoneme":"w","PronunciationAssessment":{"AccuracyScore":28.0},"Offset":54400000,"Duration":900000},{"Phoneme":"aa","PronunciationAssessment":{"AccuracyScore":42.0},"Offset":55400000,"Duration":700000},{"Phoneme":"ch","PronunciationAssessment":{"AccuracyScore":58.0},"Offset":56200000,"Duration":1300000},{"Phoneme":"ih","PronunciationAssessment":{"AccuracyScore":61.0},"Offset":57600000,"Duration":700000},{"Phoneme":"ng","PronunciationAssessment":{"AccuracyScore":46.0},"Offset":58400000,"Duration":1400000}]},{"Word":"movie","Offset":59900000,"Duration":6000000,"PronunciationAssessment":{"AccuracyScore":50.0,"ErrorType":"Mispronunciation"},"Syllables":[{"Syllable":"muw","Grapheme":"mo","PronunciationAssessment":{"AccuracyScore":79.0},"Offset":59900000,"Duration":2000000},{"Syllable":"viy","Grapheme":"vie","PronunciationAssessment":{"AccuracyScore":37.0},"Offset":62000000,"Duration":3900000}],"Phonemes":[{"Phoneme":"m","PronunciationAssessment":{"AccuracyScore":51.0},"Offset":59900000,"Duration":800000},{"Phoneme":"uw","PronunciationAssessment":{"AccuracyScore":100.0},"Offset":60800000,"Duration":1100000},{"Phoneme":"v","PronunciationAssessment":{"AccuracyScore":36.0},"Offset":62000000,"Duration":1700000},{"Phoneme":"iy","PronunciationAssessment":{"AccuracyScore":38.0},"Offset":63800000,"Duration":2100000}]},{"Word":"and","Offset":66000000,"Duration":4300000,"PronunciationAssessment":{"AccuracyScore":97.0,"ErrorType":"None"},"Syllables":[{"Syllable":"aend","Grapheme":"and","PronunciationAssessment":{"AccuracyScore":52.0},"Offset":66000000,"Duration":4300000}],"Phonemes":[{"Phoneme":"ae","PronunciationAssessment":{"AccuracyScore":52.0},"Offset":66000000,"Duration":700000},{"Phoneme":"n","PronunciationAssessment":{"AccuracyScore":48.0},"Offset":66800000,"Duration":1600000},{"Phoneme":"d","PronunciationAssessment":{"AccuracyScore":55.0},"Offset":68500000,"Duration":1800000}]},{"Word":"shevlin","Offset":70400000,"Duration":7300000,"PronunciationAssessment":{"AccuracyScore":88.0,"ErrorType":"None"},"Syllables":[{"Syllable":"shehv","PronunciationAssessment":{"AccuracyScore":86.0},"Offset":70400000,"Duration":2700000},{"Syllable":"lihn","PronunciationAssessment":{"AccuracyScore":60.0},"Offset":73200000,"Duration":4500000}],"Phonemes":[{"Phoneme":"sh","PronunciationAssessment":{"AccuracyScore":78.0},"Offset":70400000,"Duration":900000},{"Phoneme":"eh","PronunciationAssessment":{"AccuracyScore":84.0},"Offset":71400000,"Duration":700000},{"Phoneme":"v","PronunciationAssessment":{"AccuracyScore":96.0},"Offset":72200000,"Duration":900000},{"Phoneme":"l","PronunciationAssessment":{"AccuracyScore":92.0},"Offset":73200000,"Duration":700000},{"Phoneme":"ih","PronunciationAssessment":{"AccuracyScore":79.0},"Offset":74000000,"Duration":700000},{"Phoneme":"n","PronunciationAssessment":{"AccuracyScore":46.0},"Offset":74800000,"Duration":2900000}]},{"Word":"i","Offset":81700000,"Duration":4100000,"PronunciationAssessment":{"AccuracyScore":97.0,"ErrorType":"None"},"Syllables":[{"Syllable":"ay","Grapheme":"i","PronunciationAssessment":{"AccuracyScore":97.0},"Offset":81700000,"Duration":4100000}],"Phonemes":[{"Phoneme":"ay","PronunciationAssessment":{"AccuracyScore":97.0},"Offset":81700000,"Duration":4100000}]},{"Word":"also","Offset":85900000,"Duration":5800000,"PronunciationAssessment":{"AccuracyScore":21.0,"ErrorType":"Mispronunciation"},"Syllables":[{"Syllable":"aol","Grapheme":"al","PronunciationAssessment":{"AccuracyScore":16.0},"Offset":85900000,"Duration":2000000},{"Syllable":"sow","Grapheme":"so","PronunciationAssessment":{"AccuracyScore":50.0},"Offset":88000000,"Duration":3700000}],"Phonemes":[{"Phoneme":"ao","PronunciationAssessment":{"AccuracyScore":18.0},"Offset":85900000,"Duration":700000},{"Phoneme":"l","PronunciationAssessment":{"AccuracyScore":15.0},"Offset":86700000,"Duration":1200000},{"Phoneme":"s","PronunciationAssessment":{"AccuracyScore":47.0},"Offset":88000000,"Duration":1900000},{"Phoneme":"ow","PronunciationAssessment":{"AccuracyScore":53.0},"Offset":90000000,"Duration":1700000}]},{"Word":"like","Offset":91800000,"Duration":3800000,"PronunciationAssessment":{"AccuracyScore":82.0,"ErrorType":"None"},"Syllables":[{"Syllable":"layk","Grapheme":"like","PronunciationAssessment":{"AccuracyScore":60.0},"Offset":91800000,"Duration":3800000}],"Phonemes":[{"Phoneme":"l","PronunciationAssessment":{"AccuracyScore":52.0},"Offset":91800000,"Duration":2100000},{"Phoneme":"ay","PronunciationAssessment":{"AccuracyScore":79.0},"Offset":94000000,"Duration":1100000},{"Phoneme":"k","PronunciationAssessment":{"AccuracyScore":47.0},"Offset":95200000,"Duration":400000}]},{"Word":"spending","Offset":95700000,"Duration":6000000,"PronunciationAssessment":{"AccuracyScore":94.0,"ErrorType":"None"},"Syllables":[{"Syllable":"spehn","Grapheme":"spen","PronunciationAssessment":{"AccuracyScore":79.0},"Offset":95700000,"Duration":3000000},{"Syllable":"dihng","Grapheme":"ding","PronunciationAssessment":{"AccuracyScore":84.0},"Offset":98800000,"Duration":2900000}],"Phonemes":[{"Phoneme":"s","PronunciationAssessment":{"AccuracyScore":56.0},"Offset":95700000,"Duration":600000},{"Phoneme":"p","PronunciationAssessment":{"AccuracyScore":80.0},"Offset":96400000,"Duration":700000},{"Phoneme":"eh","PronunciationAssessment":{"AccuracyScore":80.0},"Offset":97200000,"Duration":600000},{"Phoneme":"n","PronunciationAssessment":{"AccuracyScore":94.0},"Offset":97900000,"Duration":800000},{"Phoneme":"d","PronunciationAssessment":{"AccuracyScore":100.0},"Offset":98800000,"Duration":500000},{"Phoneme":"ih","PronunciationAssessment":{"AccuracyScore":100.0},"Offset":99400000,"Duration":900000},{"Phoneme":"ng","PronunciationAssessment":{"AccuracyScore":65.0},"Offset":100400000,"Duration":1300000}]},{"Word":"time","Offset":101800000,"Duration":3700000,"PronunciationAssessment":{"AccuracyScore":94.0,"ErrorType":"None"},"Syllables":[{"Syllable":"taym","Grapheme":"time","PronunciationAssessment":{"AccuracyScore":57.0},"Offset":101800000,"Duration":3700000}],"Phonemes":[{"Phoneme":"t","PronunciationAssessment":{"AccuracyScore":18.0},"Offset":101800000,"Duration":900000},{"Phoneme":"ay","PronunciationAssessment":{"AccuracyScore":96.0},"Offset":102800000,"Duration":1200000},{"Phoneme":"m","PronunciationAssessment":{"AccuracyScore":50.0},"Offset":104100000,"Duration":1400000}]},{"Word":"with","Offset":105600000,"Duration":3700000,"PronunciationAssessment":{"AccuracyScore":94.0,"ErrorType":"None"},"Syllables":[{"Syllable":"wihdh","Grapheme":"with","PronunciationAssessment":{"AccuracyScore":63.0},"Offset":105600000,"Duration":3700000}],"Phonemes":[{"Phoneme":"w","PronunciationAssessment":{"AccuracyScore":78.0},"Offset":105600000,"Duration":900000},{"Phoneme":"ih","PronunciationAssessment":{"AccuracyScore":77.0},"Offset":106600000,"Duration":500000},{"Phoneme":"dh","PronunciationAssessment":{"AccuracyScore":53.0},"Offset":107200000,"Duration":2100000}]},{"Word":"my","Offset":109400000,"Duration":4800000,"PronunciationAssessment":{"AccuracyScore":97.0,"ErrorType":"None"},"Syllables":[{"Syllable":"may","Grapheme":"my","PronunciationAssessment":{"AccuracyScore":72.0},"Offset":109400000,"Duration":4800000}],"Phonemes":[{"Phoneme":"m","PronunciationAssessment":{"AccuracyScore":99.0},"Offset":109400000,"Duration":1100000},{"Phoneme":"ay","PronunciationAssessment":{"AccuracyScore":63.0},"Offset":110600000,"Duration":3600000}]},{"Word":"friends","Offset":116400000,"Duration":5700000,"PronunciationAssessment":{"AccuracyScore":73.0,"ErrorType":"None"},"Syllables":[{"Syllable":"frehndz","Grapheme":"friends","PronunciationAssessment":{"AccuracyScore":58.0},"Offset":116400000,"Duration":5700000}],"Phonemes":[{"Phoneme":"f","PronunciationAssessment":{"AccuracyScore":26.0},"Offset":116400000,"Duration":500000},{"Phoneme":"r","PronunciationAssessment":{"AccuracyScore":55.0},"Offset":117000000,"Duration":500000},{"Phoneme":"eh","PronunciationAssessment":{"AccuracyScore":56.0},"Offset":117600000,"Duration":900000},{"Phoneme":"n","PronunciationAssessment":{"AccuracyScore":72.0},"Offset":118600000,"Duration":500000},{"Phoneme":"d","PronunciationAssessment":{"AccuracyScore":76.0},"Offset":119200000,"Duration":1100000},{"Phoneme":"z","PronunciationAssessment":{"AccuracyScore":53.0},"Offset":120400000,"Duration":1700000}]},{"Word":"in","Offset":134900000,"Duration":2700000,"PronunciationAssessment":{"AccuracyScore":97.0,"ErrorType":"None"},"Syllables":[{"Syllable":"ihn","Grapheme":"in","PronunciationAssessment":{"AccuracyScore":80.0},"Offset":134900000,"Duration":2700000}],"Phonemes":[{"Phoneme":"ih","PronunciationAssessment":{"AccuracyScore":80.0},"Offset":134900000,"Duration":1000000},{"Phoneme":"n","PronunciationAssessment":{"AccuracyScore":80.0},"Offset":136000000,"Duration":1600000}]},{"Word":"new","Offset":137700000,"Duration":2700000,"PronunciationAssessment":{"AccuracyScore":80.0,"ErrorType":"None"},"Syllables":[{"Syllable":"nuw","Grapheme":"new","PronunciationAssessment":{"AccuracyScore":80.0},"Offset":137700000,"Duration":2700000}],"Phonemes":[{"Phoneme":"n","PronunciationAssessment":{"AccuracyScore":80.0},"Offset":137700000,"Duration":1200000},{"Phoneme":"uw","PronunciationAssessment":{"AccuracyScore":80.0},"Offset":139000000,"Duration":1400000}]},{"Word":"things","Offset":140500000,"Duration":6800000,"PronunciationAssessment":{"AccuracyScore":70.0,"ErrorType":"None"},"Syllables":[{"Syllable":"thihngz","Grapheme":"things","PronunciationAssessment":{"AccuracyScore":57.0},"Offset":140500000,"Duration":6800000}],"Phonemes":[{"Phoneme":"th","PronunciationAssessment":{"AccuracyScore":54.0},"Offset":140500000,"Duration":1800000},{"Phoneme":"ih","PronunciationAssessment":{"AccuracyScore":61.0},"Offset":142400000,"Duration":900000},{"Phoneme":"ng","PronunciationAssessment":{"AccuracyScore":59.0},"Offset":143400000,"Duration":700000},{"Phoneme":"z","PronunciationAssessment":{"AccuracyScore":56.0},"Offset":144200000,"Duration":3100000}]}]}]}', <PropertyId.SpeechServiceResponse_RecognitionLatencyMs: 5002>: '647', <PropertyId.SpeechServiceResponse_RecognitionBackend: 5003>: 'online', <PropertyId.SpeechServiceResponse_RequestId: 5004>: 'd0062cc1235144fa84407d4ee9ca8e73'}, '_cancellation_details': None, '_no_match_details': None}
