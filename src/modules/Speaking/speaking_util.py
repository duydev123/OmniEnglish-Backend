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

import os

import av  # Yêu cầu cài đặt thư viện: pip install av


cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)


def round_to_ielts_band(score: float) -> float:
    """
    Rounds a raw band score to the official IELTS half-band scale (0.0, 0.5, 1.0, 1.5, ..., 9.0).
    Official IELTS rounding rules:
    - fractional part < 0.25 -> .0
    - fractional part >= 0.25 and < 0.75 -> .5
    - fractional part >= 0.75 -> next integer
    """
    if score is None or score <= 0:
        return 0.0
    if score >= 9.0:
        return 9.0
    
    integer_part = int(score)
    fraction = score - integer_part
    if fraction < 0.25:
        return float(integer_part)
    elif fraction < 0.75:
        return float(integer_part) + 0.5
    else:
        return float(integer_part) + 1.0


class SpeakingUtil:
    round_to_ielts_band = staticmethod(round_to_ielts_band)

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
    async def evaluate_single_audio_segment(audio_url: str, prompt_text: str, part: str = "PART_1") -> dict:
        """
        Gọi Azure Speech (lấy Pronunciation, Fluency, Transcript) 
         + Gọi Gemini AI (lấy Grammar, Lexical, Overall, Feedback dựa trên giáo trình chuẩn IELTS Michael C. Thorp).
        """
        # Khởi tạo các biến để đảm bảo khối finally không bị lỗi UnboundLocalError
        tmp_file_path = ""
        speech_recognizer = None
        audio_config = None

        try:
            # ==========================================
            # 1. TẠO FILE TẠM VÀ TẢI AUDIO TỪ CLOUD VỀ
            # ==========================================
            # Dùng mkstemp tạo file an toàn và đóng ngay file descriptor của hệ thống
            fd, tmp_file_path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(audio_url)
                response.raise_for_status()
                with open(tmp_file_path, "wb") as tmp_file:
                    tmp_file.write(response.content)

            # ==========================================
            # 2. GỌI AZURE SPEECH SDK (PRONUNCIATION & FLUENCY)
            # ==========================================
            speech_key = os.getenv("AZURE_SPEECH_KEY")
            service_region = os.getenv("AZURE_SPEECH_REGION")
            
            if not speech_key or not service_region:
                raise HTTPException(
                    status_code=500, 
                    detail="Chưa cấu hình AZURE_SPEECH_KEY và AZURE_SPEECH_REGION"
                )

            speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
            audio_config = speechsdk.audio.AudioConfig(filename=tmp_file_path)

            pronunciation_config = speechsdk.PronunciationAssessmentConfig(
                reference_text="", # Để Azure tự nhận diện (Unscripted)
                grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
                granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
                enable_miscue=False
            )
            
            speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
            pronunciation_config.apply_to(speech_recognizer)

            # Chạy nhận diện
            result = speech_recognizer.recognize_once_async().get()

            transcript = ""
            pronunciation_score = 0.0
            fluency_score = 0.0
            words_detail_list = []

            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                transcript = result.text
                pronunciation_result = speechsdk.PronunciationAssessmentResult(result)
                pronunciation_score = round_to_ielts_band((pronunciation_result.pronunciation_score / 100.0) * 9.0)
                fluency_score = round_to_ielts_band((pronunciation_result.fluency_score / 100.0) * 9.0)
                
                # BẢNG MAP IPA
                AZURE_TO_IPA = {
                    "aa": "ɑ", "ae": "æ", "ah": "ʌ", "ao": "ɔ", "aw": "aʊ", "ax": "ə", "ay": "aɪ",
                    "b": "b", "ch": "tʃ", "d": "d", "dh": "ð", "eh": "ɛ", "er": "ɜr", "ey": "eɪ",
                    "f": "f", "g": "g", "hh": "h", "ih": "ɪ", "iy": "i", "jh": "dʒ", "k": "k",
                    "l": "l", "m": "m", "n": "n", "ng": "ŋ", "ow": "oʊ", "oy": "ɔɪ", "p": "p",
                    "r": "r", "s": "s", "sh": "ʃ", "t": "t", "th": "θ", "uh": "ʊ", "uw": "u",
                    "v": "v", "w": "w", "y": "j", "z": "z", "zh": "ʒ"
                }

                for word_obj in pronunciation_result.words:
                    phonemes_list = []
                    if hasattr(word_obj, 'phonemes') and word_obj.phonemes:
                        for p in word_obj.phonemes:
                            raw_phoneme = p.phoneme.lower()
                            ipa_phoneme = AZURE_TO_IPA.get(raw_phoneme, raw_phoneme)
                            phonemes_list.append({
                                "phoneme": ipa_phoneme,
                                "accuracy_score": p.accuracy_score
                            })
                    
                    err_type_str = word_obj.error_type.name if hasattr(word_obj.error_type, 'name') else str(word_obj.error_type)
                    words_detail_list.append({
                        "word": word_obj.word,
                        "accuracy_score": word_obj.accuracy_score,
                        "error_type": err_type_str,
                        "phonemes": phonemes_list
                    })
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Không thể nhận diện được giọng nói trong file audio."
                )

            # ==========================================
            # 3. GỌI GEMINI AI (CHẤM ĐIỂM CHUẨN KITE BOY / MICHAEL C. THORP)
            # ==========================================
            genai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            
            # Lọc ra tối đa 5 từ có điểm phát âm thấp nhất từ kết quả của Azure để đưa cho Gemini phân tích
            bad_pronunciation_words = [
                f"'{w['word']}' (Điểm: {w['accuracy_score']}/100, Lỗi: {w['error_type']})"
                for w in words_detail_list if w.get('accuracy_score', 100) < 80
            ][:5]
            bad_words_str = ", ".join(bad_pronunciation_words) if bad_pronunciation_words else "Thí sinh phát âm rất tốt, không có lỗi nghiêm trọng."
            
            part_upper = (part or "PART_1").upper()
            
            # Diễn giải tiêu chí riêng cho từng Part từ giáo trình Michael C. Thorp (Kite Boy IELTS Speaking Series)
            if "PART_2" in part_upper:
                part_rubric = """
[QUY TẮC BẮT BUỘC RIÊNG CHO PART 2 — INDIVIDUAL LONG TURN (BÀI NÓI DÀI 1.5–2 PHÚT)]
- Mục tiêu: Nói liên tục từ 1.5 đến 2 phút theo lối kể chuyện (Storytelling approach) có chiều sâu và diễn biến logic.
- Cấu trúc bài nói 3 phần chuẩn Michael C. Thorp:
  1. Setting (Giới thiệu bối cảnh): Đưa ra thời gian, địa điểm, nhân vật, mục tiêu ("When I started my second year...", "Around 2 years ago...").
  2. Main Events & Problem/Obstacle (Sự cố & Diễn biến chính): Phải nêu rõ vấn đề, thử thách hoặc sự cố gặp phải và cách giải quyết (Không có sự cố/vấn đề = bài nói bị khô khan, liệt kê điểm).
  3. Final Outcome & Feelings (Kết quả & Bài học/Cảm xúc): Kết quả cuối cùng và cảm xúc/bài học rút ra.
- QUY TẮC MỞ ĐẦU: KHÔNG đọc lại nguyên văn đề bài trên Cue Card (VD đề bảo "Describe a subject...", KHÔNG được bắt đầu "A subject I liked was..."). Phải mở đầu bằng một câu dẫn nhập cá nhân tự nhiên.
- CẢNH BÁO THỜI LƯỢNG / BÀI NÓI NGẮN: Nếu bài nói dưới 80 từ (hoặc nói dưới 1 phút), trừ nặng điểm Fluency & Coherence (tối đa Band 5.0–5.5).
- TỪ VỰNG & NGỮ PHÁP: Yêu cầu kết hợp thì quá khứ đơn chuẩn xác cho câu chuyện quá khứ và các cụm từ nối kể chuyện ("as far back as I can remember", "what I'll never forget was...", "it turned out that...").
"""
            elif "PART_3" in part_upper:
                part_rubric = """
[QUY TẮC BẮT BUỘC RIÊNG CHO PART 3 — TWO-WAY DISCUSSION (THẢO LUẬN KHÁI QUÁT XÃ HỘI)]
- Mục tiêu: Thảo luận sâu sắc về các chủ đề mang tính xã hội, toàn cầu, cộng đồng (KHÔNG NÓI VỀ CÁ NHÂN!).
- Cấu trúc chuẩn: General Opinion/Statement + Reason/Analysis + World Example/Implication.
- CẤU TRÚC KHÁI QUÁT HÓA (Generalizing phrases): Sử dụng "By and large", "Generally speaking", "On the whole", "As a rule", "Nine times out of ten".
- QUY TẮC VÀNG VỀ ĐỐI TƯỢNG (CRITICAL PART 3 RULE — NGUYÊN TẮC MICHAEL C. THORP):
  TUYỆT ĐỐI KHÔNG NÓI VỀ BẢN THÂN, GIA ĐÌNH HAY BẠN BÈ TRONG PART 3! Part 3 yêu cầu bàn luận góc nhìn xã hội ("people", "society", "governments", "younger/older generations"). Nếu thí sinh dùng ví dụ cá nhân ("When I was...", "My brother...", "My friend..."), đây là lỗi không thể tư duy khái quát -> TRỪ THẲNG 1.0 đến 1.5 điểm vào Fluency & Coherence và Lexical Resource (Giới hạn tối đa Band 5.0–5.5). Nêu rõ cảnh báo này trong "off_topic_warning".
- KỸ NĂNG TƯ DUY PHÂN TÍCH: Đánh giá cao việc so sánh (Quá khứ vs Hiện tại, Trẻ em vs Người lớn, Thành thị vs Nông thôn), phân tích Ưu/Nhược điểm, Nguyên nhân/Giải pháp, và Dự đoán tương lai.
"""
            else:
                part_rubric = """
[QUY TẮC BẮT BUỘC RIÊNG CHO PART 1 — EVERYDAY PERSONAL TOPICS (4-5 PHÚT, ~20s/CÂU)]
- Mục tiêu: Trả lời tự nhiên, ngắn gọn nhưng đầy đủ (2-3 câu, 20-30 giây mỗi câu).
- Cấu trúc chuẩn: Direct Answer + Reason/Explanation + Example/Detail (hoặc cấu trúc so sánh tình huống "if [situation 1] -> [result 1], whereas if [situation 2] -> [result 2]").
- QUY TẮC TRÁNH LẶP TỪ CÂU HỎI: KHÔNG lặp lại nguyên văn từ ngữ trong câu hỏi. Phải dùng đại từ (one, it, they) hoặc từ đồng nghĩa/paraphrase ngay ở câu mở đầu.
- CẢNH BÁO CÂU TRẢ LỜI QUÁ NGẮN: Nếu thí sinh chỉ trả lời 1 câu ngắn (dưới 15 từ) hoặc "Yes/No", trừ ngay điểm Fluency & Coherence xuống tối đa Band 5.0–5.5 (do thiếu khả năng phát triển ý).
- CẢNH BÁO CÂU MỞ ĐẦU SÁO RỖNG: Tránh các câu filler vô nghĩa ("That's an interesting question...").
- CẢNH BÁO LIỆT KÊ: Tránh trả lời liệt kê danh sách ("It has a park, a pool, and a mall") vì không thể hiện được cấu trúc ngữ pháp phức.
- THÀNH NGỮ TỰ NHIÊN: Đánh giá cao Phrasal Verbs và Collocations tự nhiên. Phê bình nếu chèn ép thành ngữ gượng gạo ("knee high to a grasshopper").
"""

            ai_prompt = f"""
            Bạn là một giám khảo IELTS Speaking chính thức, khắt khe và giàu kinh nghiệm (dựa theo bộ tiêu chuẩn chấm thi IELTS chuẩn quốc tế trong sách "IELTS Speaking: The Most Comprehensive Guide All in One" của Michael C. Thorp - Giám khảo IELTS trên 20 năm).

            Thí sinh vừa thực hiện phần thi IELTS Speaking ({part_upper}):
            - Câu hỏi / Đề bài: "{prompt_text}"
            - Transcript bài nói của thí sinh: "{transcript}"

            [DỮ LIỆU TỪ HỆ THỐNG PHÂN TÍCH ÂM THANH — AZURE SPEECH AI]
            - Điểm Phát âm ban đầu (Azure Pronunciation Score): {pronunciation_score}/9.0
            - Điểm Lưu loát ban đầu (Azure Fluency Score): {fluency_score}/9.0
            - Danh sách từ phát âm sai / điểm thấp nhất từ Azure: {bad_words_str}

            {part_rubric}

            [THANG ĐIỂM IELTS CHÍNH THỨC — BẮT BUỘC TUÂN THEO]
            Bạn PHẢI chấm điểm trên thang IELTS Band Score từ 0.0 đến 9.0, CHỈ sử dụng các mức half-band (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0).
            TUYỆT ĐỐI không dùng thang 10 hay số thập phân lẻ khác (như 6.2, 7.8, 2.1 là SAI).

            [4 TIÊU CHÍ CHẤM ĐIỂM IELTS CHÍNH THỨC BẮT BUỘC DIỄN GIẢI KỸ]

            1. PRONUNCIATION (Phát âm - P):
            - Lấy điểm Azure ({pronunciation_score}/9.0) làm cơ sở ban đầu.
            - Đánh giá dựa trên: Ngắt nhịp câu (Chunking), Trọng âm từ và câu (Stress), Giai điệu/Ngữ điệu (Intonation), và Độ chuẩn xác âm IPA.
            - Lọc danh sách {bad_words_str}: Nếu nhiều từ cơ bản phát âm sai nghiêm trọng (Error: Mispronunciation, điểm < 60), trừ thêm 0.5–1.0 band.
            - Band descriptors:
              • 8.5–9.0: Phát âm cực kỳ tự nhiên, ngữ điệu chuẩn native, âm tiết rõ ràng hoàn toàn.
              • 7.0–8.0: Phát âm rõ ràng, có ngắt nhịp và nhấn trọng âm tốt, lỗi nhỏ không đáng kể.
              • 5.5–6.5: Phát âm tương đối dễ hiểu, còn lỗi trọng âm hoặc âm cuối (ending sounds).
              • 4.0–5.0: Lỗi phát âm xuất hiện thường xuyên, ảnh hưởng trực tiếp đến người nghe.
              • Dưới 4.0: Lỗi phát âm nghiêm trọng, khó hiểu.

            2. FLUENCY & COHERENCE (Lưu loát & Mạch lạc - F&C):
            - Lấy điểm Azure ({fluency_score}/9.0) làm cơ sở ban đầu.
            - Đánh giá khả năng duy trì dòng nói, độ ngập ngừng (hesitation), tự sửa lỗi (self-correction), và tính liên kết logic.
            - ÁP DỤNG CÁC QUY TẮC ĐẶC THÙ THEO PART VÀ LẠC ĐỀ:
              • Quy tắc Lạc đề: IELTS không có tiêu chí Task Response riêng. Nếu trả lời LẠC ĐỀ hoặc sai trọng tâm câu hỏi "{prompt_text}", TRỪ TRỰC TIẾP 1.0 đến 3.0 điểm vào Fluency & Coherence.
              • Quy tắc Part 3: Nếu Part 3 mà thí sinh lấy ví dụ cá nhân ("I", "my family", "my friends") thay vì nói về xã hội/con người nói chung, trừ 1.0-1.5 điểm F&C.
              • Quy tắc Độ dài: Nếu câu trả lời quá ngắn (Part 1 < 15 từ, Part 2 < 80 từ), cap điểm F&C ở Band 5.0–5.5.
            - Band descriptors:
              • 8.0–9.0: Nói trôi chảy, tự nhiên, ý tưởng liên kết chặt chẽ, không ngập ngừng tìm từ.
              • 6.5–7.5: Duy trì tốt nhịp nói, sử dụng từ nối tự nhiên, đôi khi ngập ngừng nhẹ.
              • 5.0–6.0: Nói còn ngập ngừng, lặp từ hoặc phụ thuộc vào từ nối sáo rỗng.
              • Dưới 5.0: Nói đứt quãng, không nối được ý hoàn chỉnh.

            3. LEXICAL RESOURCE (Từ vựng - LR):
            - Đánh giá độ phong phú, độ chính xác của từ vựng, khả năng Paraphrase và sử dụng Collocations / Phrasal Verbs.
            - Quy tắc Paraphrase: Không lặp lại nguyên văn từ câu hỏi (khen ngợi nếu dùng đại từ hoặc từ đồng nghĩa phù hợp).
            - Quy tắc Idiom: Đánh giá cao Phrasal Verbs và Collocations tự nhiên. Phê bình nếu chèn ép thành ngữ gượng gạo ("knee high to a grasshopper").
            - Band descriptors:
              • 8.5–9.0: Từ vựng vô cùng phong phú, sử dụng idioms và collocations chính xác, tự nhiên.
              • 7.0–8.0: Từ vựng linh hoạt, sử dụng từ nâng cao và collocations tốt, ít lỗi nhỏ.
              • 5.5–6.5: Từ vựng đủ dùng cho chủ đề nhưng còn cơ bản, lặp từ, Paraphrase chưa mượt.
              • 4.0–5.0: Từ vựng hạn chế, dùng sai từ thường xuyên, không thể diễn đạt ý phức tạp.
              • Dưới 4.0: Từ vựng rất nghèo nàn.

            4. GRAMMATICAL RANGE & ACCURACY (Ngữ pháp - GRA):
            - Đánh giá sự kết hợp giữa câu đơn và CÂU PHỨC (Complex Sentences với subordinating conjunctions: because, since, although, while, if, given that, provided that, relative clauses).
            - Đánh giá độ chính xác: Thì của động từ (đặc biệt Past Simple trong kể chuyện), Hòa hợp chủ ngữ - động từ (Subject-verb agreement), Danh từ đếm được số nhiều.
            - Band descriptors:
              • 8.5–9.0: Cấu trúc câu đa dạng, phức tạp, hoàn toàn không có lỗi ngữ pháp.
              • 7.0–8.0: Sử dụng linh hoạt các câu phức, phần lớn câu không có lỗi (error-free structures).
              • 5.5–6.5: Có nỗ lực dùng câu phức nhưng còn mắc lỗi thì, s-v agreement, hoặc chủ yếu dùng câu đơn.
              • 4.0–5.0: Lỗi ngữ pháp cơ bản xuất hiện dày đặc, gây khó hiểu.
              • Dưới 4.0: Cấu trúc câu gãy vỡ.

            LƯU Ý QUAN TRỌNG VỀ MỨC ĐIỂM THỰC TẾ:
            Trình độ trung bình của học viên Việt Nam nằm ở mức Band 5.0 - 6.5. Band 7.0+ đòi hỏi sự chính xác và linh hoạt cao. Band 8.0+ rất hiếm. HÃY CHẤM THẬT NGHIÊM KHẮC, ĐÚNG CHUẨN GIÁM KHẢO IELTS, KHÔNG CHO ĐIỂM NÂNG ĐỠ.

            Trả về ĐÚNG cấu trúc JSON sau (KHÔNG dùng thẻ markdown ```json):
            {{
                "lexical_score": 5.5,
                "grammar_score": 5.0,
                "adjusted_fluency_score": 5.5,
                "ai_insights": "Tóm tắt 1-2 câu nhận xét tổng quan bám sát tiêu chí Michael C. Thorp. Nêu rõ điểm mạnh và điểm yếu nổi bật nhất...",
                "pronunciation_feedback": {{
                    "word": "Từ phát âm sai rõ nhất (trích từ danh sách Azure)",
                    "issue": "Mô tả lỗi âm tiết/trọng âm/âm cuối cụ thể",
                    "tip": "Mẹo cải thiện (VD: Đặt lưỡi, phát âm ending sound, Shadowing...)"
                }},
                "grammar_feedback": {{
                    "structure": "Cấu trúc ngữ pháp bị sai hoặc cần nâng cấp (VD: Thì quá khứ đơn, Cấu trúc 'although')",
                    "issue": "Mô tả lỗi sai trong transcript và đưa ra câu sửa chuẩn ngữ pháp"
                }},
                "fluency_feedback": {{
                    "is_off_topic": false,
                    "off_topic_warning": "Nếu lạc đề hoặc vi phạm quy tắc Part (như dùng ví dụ cá nhân ở Part 3): Nêu rõ cảnh báo bị trừ điểm F&C...",
                    "positive_point": "Nhận xét về tốc độ, ngắt nhịp (chunking) và sự phát triển ý",
                    "note": "Khuyên bảo cụ thể theo hướng dẫn Michael C. Thorp"
                }},
                "vocabulary_feedback": {{
                    "positive_point": "Điểm cộng từ vựng (VD: Dùng tốt phrasal verb/collocation...)",
                    "positive_detail": "Trích dẫn từ/cụm từ hay mà thí sinh đã dùng trong transcript",
                    "note": "Gợi ý 2-3 từ vựng/collocation nâng cao (Band 7.0+) thay thế cho từ cơ bản"
                }},
                "sample_response": "1 câu trả lời mẫu hoàn chỉnh Band 8.0+ bám sát cấu trúc khuyến nghị của Michael C. Thorp cho Part này (kèm giải nghĩa từ vựng nâng cao hoặc dịch tiếng Việt)."
            }}
            Viết bằng tiếng Việt tự nhiên, súc tích, chuyên nghiệp, thể hiện đẳng cấp của một giám khảo IELTS hàng đầu.
            """
            
            try:
                gemini_response = genai_client.models.generate_content(
                    model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"), 
                    contents=ai_prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.2
                    )
                )
                
                raw_output = gemini_response.text.strip()
                if raw_output.startswith("```"):
                    raw_output = raw_output.split("```")[1]
                    if raw_output.startswith("json"):
                        raw_output = raw_output[4:]
                
                ai_data = json.loads(raw_output.strip())
                lexical_score = SpeakingUtil.round_to_ielts_band(float(ai_data.get("lexical_score", 0.0)))
                grammar_score = SpeakingUtil.round_to_ielts_band(float(ai_data.get("grammar_score", 0.0)))
                
                adjusted_fluency = SpeakingUtil.round_to_ielts_band(float(ai_data.get("adjusted_fluency_score", fluency_score)))
                if adjusted_fluency > 0:
                    fluency_score = SpeakingUtil.round_to_ielts_band(min(fluency_score, adjusted_fluency))

                sample_resp = ai_data.get("sample_response", "")

                # Gom nhóm feedback lại và ép kiểu thành chuỗi JSON để lưu Database
                feedback_dict = {
                    "ai_insights": ai_data.get("ai_insights", ""),
                    "pronunciation_feedback": ai_data.get("pronunciation_feedback", {}),
                    "grammar_feedback": ai_data.get("grammar_feedback", {}),
                    "fluency_feedback": ai_data.get("fluency_feedback", {}),
                    "vocabulary_feedback": ai_data.get("vocabulary_feedback", {}),
                    "sample_response": sample_resp
                }
                
                # Biến dict thành string chuẩn JSON
                feedback = json.dumps(feedback_dict, ensure_ascii=False)
                
            except Exception as e:
                lexical_score = 0.0
                grammar_score = 0.0
                sample_resp = ""
                # Trả về JSON rỗng kèm thông báo lỗi để frontend không bị crash
                fallback_dict = {
                    "ai_insights": f"Hệ thống AI đang gặp sự cố: {str(e)}",
                    "pronunciation_feedback": {},
                    "grammar_feedback": {},
                    "fluency_feedback": {},
                    "vocabulary_feedback": {},
                    "sample_response": ""
                }
                feedback = json.dumps(fallback_dict, ensure_ascii=False)

            segment_score = SpeakingUtil.round_to_ielts_band((pronunciation_score + fluency_score + lexical_score + grammar_score) / 4.0)

            return {
                "transcript": transcript,
                "segment_score": segment_score,
                "pronunciation_score": pronunciation_score,
                "fluency_score": fluency_score,
                "lexical_score": lexical_score,
                "grammar_score": grammar_score,
                "feedback": feedback,
                "sample_response": sample_resp,
                "words_detail": words_detail_list
            }

        except HTTPException:
            # Nếu là lỗi do chính mình chủ động raise, cứ ném nó ra ngoài
            raise
        except Exception as e:
            # Lỗi ngẫu nhiên (chưa catch), đóng gói lại thành lỗi 500
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"Lỗi hệ thống khi chấm điểm: {str(e)}"
            )
            
        finally:
            # ==========================================
            # 5. DỌN RÁC (Luôn chạy bất chấp thành công hay lỗi)
            # ==========================================
            # Hủy Azure objects để nhả file lock (Rất quan trọng trên Windows/Linux)
            if speech_recognizer is not None:
                del speech_recognizer
            if audio_config is not None:
                del audio_config
                
            # Xóa file vật lý
            if tmp_file_path and os.path.exists(tmp_file_path):
                try:
                    os.remove(tmp_file_path)
                except Exception as del_err:
                    print(f"[Warning] Không thể dọn rác file tạm {tmp_file_path}: {del_err}")

    @staticmethod
    async def evaluate_shadowing_audio(audio_file: UploadFile, reference_text: str) -> dict:
        """
        Nhận trực tiếp UploadFile, convert sang .wav (16kHz, mono) cục bộ bằng thư viện `av` (PyAV)
        và gọi Azure Speech dành riêng cho Shadowing. 
        """

        tmp_in_path = ""
        tmp_wav_path = ""
        speech_recognizer = None
        audio_config = None

        try:
            # 1. TẠO FILE TẠM LƯU AUDIO ĐẦU VÀO (ví dụ .webm từ client)
            fd_in, tmp_in_path = tempfile.mkstemp()
            os.close(fd_in)
            
            with open(tmp_in_path, "wb") as f_in:
                f_in.write(await audio_file.read())

            # 2. CONVERT SANG WAV (16kHz, Mono) BẰNG THƯ VIỆN `av`
            fd_out, tmp_wav_path = tempfile.mkstemp(suffix=".wav")
            os.close(fd_out)
            
            try:
                # Mở file đầu vào
                in_container = av.open(tmp_in_path)
                in_stream = in_container.streams.audio[0]
                
                # Cấu hình file đầu ra (WAV, PCM 16-bit)
                out_container = av.open(tmp_wav_path, 'w', format='wav')
                out_stream = out_container.add_stream('pcm_s16le', rate=16000)
                out_stream.layout = 'mono'
                
                # Khởi tạo Resampler để ép frame rate 16kHz và channel mono
                resampler = av.AudioResampler(format='s16', layout='mono', rate=16000)
                
                # Đọc từng frame, resample và ghi vào file đích
                for frame in in_container.decode(in_stream):
                    frame.pts = None  # Xóa timestamp cũ để tránh lỗi đồng bộ khi đổi sample rate
                    resampled_frames = resampler.resample(frame)
                    for r_frame in resampled_frames:
                        for packet in out_stream.encode(r_frame):
                            out_container.mux(packet)
                            
                # Flush encoder (đẩy nốt các dữ liệu âm thanh còn sót lại trong buffer)
                for packet in out_stream.encode(None):
                    out_container.mux(packet)
                    
                # Đóng các file container để nhả lock
                out_container.close()
                in_container.close()
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Lỗi convert audio bằng thư viện av: {str(e)}")

            # 3. GỌI AZURE SPEECH
            speech_key = os.getenv("AZURE_SPEECH_KEY")
            service_region = os.getenv("AZURE_SPEECH_REGION")
            
            if not speech_key or not service_region:
                raise HTTPException(status_code=500, detail="Chưa cấu hình Azure Speech keys.")

            speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
            audio_config = speechsdk.audio.AudioConfig(filename=tmp_wav_path)
            
            pronunciation_config = speechsdk.PronunciationAssessmentConfig(
                reference_text=reference_text,
                grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
                granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
                enable_miscue=True
            )
            
            speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
            pronunciation_config.apply_to(speech_recognizer)
            
            result = speech_recognizer.recognize_once_async().get()

            # 4. TRÍCH XUẤT DỮ LIỆU & CHUẨN HÓA SANG IPA CHUẨN
            transcript = result.text if result.reason == speechsdk.ResultReason.RecognizedSpeech else ""
            accuracy_score = 0.0
            fluency_score = 0.0
            words_detail_list = []

            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                pronunciation_result = speechsdk.PronunciationAssessmentResult(result)
                accuracy_score = round(pronunciation_result.pronunciation_score, 1)
                fluency_score = round(pronunciation_result.fluency_score, 1)
                
                # Bảng Map chuẩn hóa từ định dạng ARPAbet của Azure sang IPA Quốc Tế
                AZURE_TO_IPA = {
                    "aa": "ɑ", "ae": "æ", "ah": "ʌ", "ao": "ɔ", "aw": "aʊ", "ax": "ə", "ay": "aɪ",
                    "b": "b", "ch": "tʃ", "d": "d", "dh": "ð", "eh": "ɛ", "er": "ɜr", "ey": "eɪ",
                    "f": "f", "g": "g", "hh": "h", "ih": "ɪ", "iy": "i", "jh": "dʒ", "k": "k",
                    "l": "l", "m": "m", "n": "n", "ng": "ŋ", "ow": "oʊ", "oy": "ɔɪ", "p": "p",
                    "r": "r", "s": "s", "sh": "ʃ", "t": "t", "th": "θ", "uh": "ʊ", "uw": "u",
                    "v": "v", "w": "w", "y": "j", "z": "z", "zh": "ʒ"
                }
                
                for word_obj in pronunciation_result.words:
                    err_type_str = word_obj.error_type.name if hasattr(word_obj.error_type, 'name') else str(word_obj.error_type)
                    
                    phonemes_list = []
                    if hasattr(word_obj, 'phonemes') and word_obj.phonemes:
                        for p in word_obj.phonemes:
                            raw_phoneme = p.phoneme.lower()
                            ipa_phoneme = AZURE_TO_IPA.get(raw_phoneme, raw_phoneme)
                            phonemes_list.append({
                                "phoneme": ipa_phoneme,
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

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Lỗi khi xử lý file âm thanh trực tiếp: {str(e)}"
            )
        finally:
            # 5. DỌN RÁC AN TOÀN TRÁNH LỖI FILE LOCK (QUAN TRỌNG)
            if speech_recognizer is not None:
                del speech_recognizer
            if audio_config is not None:
                del audio_config

            for temp_file in [tmp_in_path, tmp_wav_path]:
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception as del_err:
                        print(f"[Warning] Không thể dọn rác file tạm {temp_file}: {del_err}")
                        
                        
    @staticmethod
    async def get_gemini_shadowing_feedback(english_text: str, user_transcript: str, words_detail: list) -> str:
        """
        Lọc ra các từ có điểm số thấp và nhờ Gemini AI đưa ra hướng dẫn phát âm.
        """
        # Lọc các từ phát âm dưới 80 điểm (ông có thể tuỳ chỉnh con số này)
        bad_words = [w for w in words_detail if w.get("accuracy_score", 100) < 80]

        if not bad_words:
            return "Tuyệt vời! Bạn đã phát âm chuẩn xác hầu hết các từ trong câu. Hãy tiếp tục phát huy phong độ này nhé!"

        bad_words_info = "\n".join([f"- Từ: '{w.get('word')}' (Điểm: {w.get('accuracy_score')}/100)" for w in bad_words])

        genai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        ai_prompt = f"""
        Bạn là một chuyên gia ngữ âm học và giáo viên tiếng Anh chuyên nghiệp.
        Học viên đang luyện đọc câu sau theo phương pháp Shadowing:
        Văn bản gốc: "{english_text}"
        Học viên đã đọc thành: "{user_transcript}"

        Dưới đây là danh sách các từ học viên phát âm sai hoặc điểm thấp do hệ thống nhận diện được:
        {bad_words_info}

        Nhiệm vụ của bạn:
        1. Đưa ra một câu động viên ngắn gọn, tích cực.
        2. Hướng dẫn cực kỳ chi tiết cách cải thiện cho từng từ bị sai ở trên (chỉ rõ cách đặt khẩu hình miệng, vị trí đặt lưỡi, cách bật hơi hoặc độ rung của dây thanh quản).
        3. Nếu có hiện tượng nối âm hoặc nuốt âm trong câu khiến học viên đọc sai, hãy giải thích ngắn gọn.
        4. Trình bày rõ ràng bằng Markdown, ngôn ngữ tiếng Việt tự nhiên và dễ hiểu. Không sinh ra block json.
        """

        try:
            gemini_response = genai_client.models.generate_content(
                model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                contents=ai_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3
                )
            )
            return gemini_response.text.strip()
        except Exception as e:
            return f"Đã có lỗi khi hệ thống tạo phản hồi hướng dẫn: {str(e)}"
                        