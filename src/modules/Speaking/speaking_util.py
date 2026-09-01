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
                pronunciation_score = round((pronunciation_result.pronunciation_score / 100) * 9.0, 1)
                fluency_score = round((pronunciation_result.fluency_score / 100) * 9.0, 1)
                
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
            # 3. GỌI GEMINI AI (GRAMMAR, LEXICAL & FEEDBACK)
            # ==========================================
            genai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            
            # Lọc ra tối đa 5 từ có điểm phát âm thấp nhất từ kết quả của Azure để đưa cho Gemini phân tích
            bad_pronunciation_words = [
                f"'{w['word']}' (Điểm: {w['accuracy_score']}/100, Lỗi: {w['error_type']})"
                for w in words_detail_list if w.get('accuracy_score', 100) < 80
            ][:5]
            bad_words_str = ", ".join(bad_pronunciation_words) if bad_pronunciation_words else "Thí sinh phát âm rất tốt, không có lỗi nghiêm trọng."
            
            ai_prompt = f"""
            Bạn là một giám khảo IELTS chuyên nghiệp. Thí sinh vừa trả lời câu hỏi Speaking.
            - Câu hỏi được giao: "{prompt_text}"
            - Câu trả lời bóc băng của thí sinh (Transcript): "{transcript}"
            
            [DỮ LIỆU TỪ HỆ THỐNG PHÂN TÍCH ÂM THANH]
            - Điểm Phát âm ban đầu (Pronunciation): {pronunciation_score}/9.0
            - Điểm Lưu loát ban đầu (Fluency): {fluency_score}/9.0
            - Các từ phát âm sai/kém nhất: {bad_words_str}
            
            [QUY TẮC ĐÁNH GIÁ MẠCH LẠC & LẠC ĐỀ TRONG IELTS SPEAKING]
            Lưu ý quan trọng: IELTS Speaking không có tiêu chí Task Response đứng riêng biệt. Tuy nhiên, nếu trả lời LẠC ĐỀ, nói sai câu hỏi, nói tùm bậy hoặc không liên quan, giám khảo sẽ TRỪ THẲNG VÀO TIÊU CHÍ ĐỘ LƯU LOÁT VÀ MẠCH LẠC (Fluency & Coherence) do câu trả lời thiếu đi sự liên kết, logic (Coherence) đối với câu hỏi được đặt ra.
            
            Hãy kiểm tra kỹ xem câu trả lời của thí sinh có liên quan đến câu hỏi "{prompt_text}" hay không:
            1. Nếu thí sinh trả lời LẠC ĐỀ / NÓI TÀO LAO / KHÔNG LIÊN QUAN:
               - Hãy đặt "is_off_topic": true.
               - Đưa ra điểm "adjusted_fluency_score" bị trừ bớt từ 1.0 đến 3.0 điểm so với điểm ban đầu {fluency_score} (tối thiểu là 1.0).
               - Trong "ai_insights" và "fluency_feedback", nêu rõ lời cảnh báo LẠC ĐỀ và lý do bị trừ điểm Fluency & Coherence.
            2. Nếu thí sinh trả lời ĐÚNG TRỌNG TÂM:
               - Đặt "is_off_topic": false.
               - Đặt "adjusted_fluency_score" bằng hoặc gần bằng {fluency_score}.

            Hãy đánh giá và trả về ĐÚNG cấu trúc JSON sau để hệ thống hiển thị lên giao diện app (Không dùng thẻ markdown ```json):
            {{
                "lexical_score": 7.5,
                "grammar_score": 7.0,
                "adjusted_fluency_score": 6.0,
                "ai_insights": "Tóm tắt 1-2 câu về xu hướng phát âm, độ lưu loát, từ vựng và ngữ pháp. Nếu LẠC ĐỀ, nêu rõ cảnh báo thí sinh đã trả lời không đúng trọng tâm câu hỏi...",
                "pronunciation_feedback": {{
                    "word": "Từ thí sinh phát âm sai rõ nhất (lấy từ danh sách âm thanh ở trên)",
                    "issue": "Mô tả lỗi (VD: Âm cuối bị nuốt hoàn toàn...)",
                    "tip": "Mẹo cải thiện (VD: Luyện tập Shadowing...)"
                }},
                "grammar_feedback": {{
                    "structure": "Tên cấu trúc (VD: Cấu trúc 'how to')",
                    "issue": "Mô tả lỗi và cách sửa (VD: Bạn đã dùng 'how to applied'. Cấu trúc đúng: how to + V-inf)"
                }},
                "fluency_feedback": {{
                    "is_off_topic": true/false,
                    "off_topic_warning": "Nếu lạc đề: 'Cảnh báo: Trả lời không đúng trọng tâm câu hỏi. Trong IELTS Speaking, lỗi này trừ trực tiếp vào điểm Fluency & Coherence do thiếu tính liên kết logic.'",
                    "positive_point": "Nhận xét về tốc độ nói, độ ngập ngừng...",
                    "note": "Lưu ý để nói trôi chảy và mạch lạc hơn..."
                }},
                "vocabulary_feedback": {{
                    "positive_point": "Điểm cộng từ vựng (VD: Điểm cộng: Collocations)",
                    "positive_detail": "Trích dẫn từ hay (VD: Sử dụng tốt 'modern education system')",
                    "note": "Gợi ý từ vựng nâng cao thay thế cho từ cơ bản thí sinh đã dùng"
                }},
                "sample_response": "Đưa ra 1 câu trả lời mẫu hoàn chỉnh chuẩn Band 8.0+ cho câu hỏi này bằng tiếng Anh (kèm giải nghĩa từ vựng hay hoặc dịch nghĩa tiếng Việt)."
            }}
            Lưu ý: Viết bằng tiếng Việt tự nhiên, ngắn gọn và bám sát vào câu trả lời cũng như Dữ liệu âm thanh hệ thống cung cấp.
            """
            
            try:
                gemini_response = genai_client.models.generate_content(
                    model='gemini-3.6-flash', 
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
                lexical_score = float(ai_data.get("lexical_score", 0.0))
                grammar_score = float(ai_data.get("grammar_score", 0.0))
                
                adjusted_fluency = float(ai_data.get("adjusted_fluency_score", fluency_score))
                if adjusted_fluency > 0:
                    fluency_score = round(min(fluency_score, adjusted_fluency), 1)

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

            segment_score = round((pronunciation_score + fluency_score + lexical_score + grammar_score) / 4.0, 1)

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
                model='gemini-3.6-flash',
                contents=ai_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3
                )
            )
            return gemini_response.text.strip()
        except Exception as e:
            return f"Đã có lỗi khi hệ thống tạo phản hồi hướng dẫn: {str(e)}"
                        