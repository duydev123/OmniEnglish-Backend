# src/modules/Seed/speaking_mock.py

MOCK_SPEAKING_DATA = [
    {
        "topic": {
            "title": "IELTS Full Test 1: Travel & Society",
            "description": "Bộ đề thi thử IELTS Speaking chuẩn, bao gồm 15 câu hỏi chia đều 3 phần. Chủ đề chính xoay quanh du lịch, phương tiện giao thông và các vấn đề xã hội.",
            "tags": ["Travel", "Transportation", "Society", "Full Test", "IELTS"],
            "is_full_test": True
        },
        "prompts": [
            # ==================================================
            # PART 1: Hobbies (3 câu)
            # ==================================================
            {
                "part": "PART_1",
                "sub_topic": "Hobbies",
                "question_text": "Do you have any hobbies or interests?",
                "useful_vocabulary": ["Pastime", "Immerse myself in", "Fascinated by", "Take up a hobby"],
                "ielts_tips": ["Mở rộng câu trả lời bằng cách nêu ví dụ cụ thể về sở thích của ông."],
                "examiner_tip": "Giám khảo đánh giá cao sự tự nhiên, đừng trả lời bằng một từ như 'Yes'.",
                "response_structure": [
                    {"section": "Direct Answer", "guide": "Yes, I'm quite passionate about..."},
                    {"section": "Details", "guide": "I usually spend my weekends..."}
                ]
            },
            {
                "part": "PART_1",
                "sub_topic": "Hobbies",
                "question_text": "How did you become interested in this hobby?",
                "useful_vocabulary": ["Stumbled upon", "Fell in love with", "A turning point", "Influenced by"],
                "ielts_tips": ["Sử dụng thì Quá khứ đơn (Past Simple) để kể lại thời điểm bắt đầu."],
                "examiner_tip": "Chú ý phát âm đuôi -ed khi dùng thì quá khứ.",
                "response_structure": [
                    {"section": "Origin", "guide": "It all started when I was..."},
                    {"section": "Development", "guide": "Since then, I've been..."}
                ]
            },
            {
                "part": "PART_1",
                "sub_topic": "Hobbies",
                "question_text": "Is there any hobby you would like to try in the future?",
                "useful_vocabulary": ["Give it a shot", "Step out of my comfort zone", "Broaden my horizons", "Bucket list"],
                "ielts_tips": ["Dùng 'would like to' hoặc 'am planning to' để nói về dự định tương lai."],
                "examiner_tip": "Từ vựng liên quan đến những điều mới mẻ sẽ ghi điểm (vd: step out of my comfort zone).",
                "response_structure": [
                    {"section": "Direct Answer", "guide": "I've always wanted to try..."},
                    {"section": "Reason", "guide": "The main reason is that..."}
                ]
            },

            # ==================================================
            # PART 1: Hometown (4 câu)
            # ==================================================
            {
                "part": "PART_1",
                "sub_topic": "Hometown",
                "question_text": "Where is your hometown located?",
                "useful_vocabulary": ["Metropolis", "Coastal city", "Situated in", "The heart of"],
                "ielts_tips": ["Sử dụng mệnh đề quan hệ để mô tả thêm (which is located in...)."],
                "examiner_tip": "Trả lời gãy gọn, đủ thông tin về vị trí địa lý.",
                "response_structure": [
                    {"section": "Direct Answer", "guide": "I was born and raised in [Name], which is a [Type of city] located in..."}
                ]
            },
            {
                "part": "PART_1",
                "sub_topic": "Hometown",
                "question_text": "What is your hometown famous for?",
                "useful_vocabulary": ["Renowned for", "Culinary delights", "Historical landmarks", "Tourist attraction"],
                "ielts_tips": ["Chuẩn bị sẵn 2 đặc điểm nổi bật nhất của quê hương để nói."],
                "examiner_tip": "Đừng ngập ngừng quá lâu ở những câu hỏi mang tính cá nhân thế này.",
                "response_structure": [
                    {"section": "Feature 1", "guide": "It is particularly well-known for..."},
                    {"section": "Feature 2", "guide": "Besides that, people also visit for..."}
                ]
            },
            {
                "part": "PART_1",
                "sub_topic": "Hometown",
                "question_text": "Has your hometown changed much since you were a child?",
                "useful_vocabulary": ["Undergone significant changes", "Urbanization", "Skyline", "Modernized"],
                "ielts_tips": ["Dùng thì Hiện tại hoàn thành (Present Perfect) để mô tả sự thay đổi (has changed, has become)."],
                "examiner_tip": "Sự tương phản giữa quá khứ và hiện tại là điểm mấu chốt để đánh giá Grammar.",
                "response_structure": [
                    {"section": "Direct Answer", "guide": "Yes, it has undergone massive transformations..."},
                    {"section": "Contrast", "guide": "When I was young, there were mostly... but now..."}
                ]
            },
            {
                "part": "PART_1",
                "sub_topic": "Hometown",
                "question_text": "Do you think your hometown is a good place for young people to live?",
                "useful_vocabulary": ["Job opportunities", "Vibrant nightlife", "Fast-paced lifestyle", "Career prospects"],
                "ielts_tips": ["Đưa ra quan điểm rõ ràng và giải thích bằng 1 lý do (cơ hội việc làm, giáo dục...)."],
                "examiner_tip": "Thể hiện khả năng đánh giá một vấn đề.",
                "response_structure": [
                    {"section": "Opinion", "guide": "Absolutely. I believe it's an ideal place because..."},
                    {"section": "Reason", "guide": "It offers plenty of..."}
                ]
            },

            # ==================================================
            # PART 2: Cue Card (1 câu - Có các bullet points)
            # ==================================================
            {
                "part": "PART_2",
                "sub_topic": "Travel",
                "question_text": "Describe a memorable journey you have made.\nYou should say:\n- Where you went\n- How you traveled\n- Why you went on the journey\n- And explain why it is memorable to you.",
                "useful_vocabulary": ["Embark on a journey", "Breathtaking scenery", "Unforgettable experience", "Broaden my horizons", "Get away from it all"],
                "ielts_tips": [
                    "Sử dụng kỹ thuật 'Mind-mapping' trong 1 phút chuẩn bị.",
                    "Sử dụng các thì Quá khứ đa dạng (Past Simple, Past Continuous, Past Perfect)."
                ],
                "examiner_tip": "Nói đủ 2 phút. Nếu hết ý, hãy mở rộng phần 'Giải thích tại sao nó đáng nhớ'.",
                "response_structure": [
                    {"section": "Introduction", "guide": "I'd like to tell you about a trip I took to..."},
                    {"section": "Body (Where & How)", "guide": "I traveled there by [Mode of transport] because..."},
                    {"section": "Body (Why)", "guide": "The main purpose of this journey was..."},
                    {"section": "Conclusion (Why memorable)", "guide": "What made this trip truly unforgettable was..."}
                ]
            },

            # ==================================================
            # PART 3: Transportation (4 câu)
            # ==================================================
            {
                "part": "PART_3",
                "sub_topic": "Transportation",
                "question_text": "Why do people need to travel every day?",
                "useful_vocabulary": ["Commute", "Daily basis", "Mundane tasks", "Socialize"],
                "ielts_tips": ["Nhìn vấn đề từ góc độ xã hội, đừng chỉ lấy ví dụ về bản thân."],
                "examiner_tip": "Part 3 yêu cầu thảo luận vĩ mô. Hãy dùng 'Most people', 'Society generally'.",
                "response_structure": [
                    {"section": "Main Reason", "guide": "The primary reason is commuting to work or school."},
                    {"section": "Additional Reason", "guide": "Furthermore, people travel for..."}
                ]
            },
            {
                "part": "PART_3",
                "sub_topic": "Transportation",
                "question_text": "What are the main problems with transportation in your country?",
                "useful_vocabulary": ["Traffic congestion", "Exhaust fumes", "Inadequate infrastructure", "Rush hour"],
                "ielts_tips": ["Nhóm các vấn đề lại (ví dụ: cơ sở hạ tầng, môi trường)."],
                "examiner_tip": "Sử dụng từ vựng nâng cao về giao thông để tăng điểm Lexical Resource.",
                "response_structure": [
                    {"section": "Problem 1", "guide": "One of the most pressing issues is..."},
                    {"section": "Problem 2", "guide": "Another significant challenge is..."}
                ]
            },
            {
                "part": "PART_3",
                "sub_topic": "Transportation",
                "question_text": "How can the government improve public transport?",
                "useful_vocabulary": ["Allocate budget", "Subsidize", "Upgrade facilities", "Encourage citizens"],
                "ielts_tips": ["Đưa ra các giải pháp thực tế và có logic (đầu tư tiền, tuyên truyền...)."],
                "examiner_tip": "Cấu trúc giả định (If the government..., then...) rất hữu ích ở đây.",
                "response_structure": [
                    {"section": "Solution 1", "guide": "Firstly, the authorities should allocate more funds to..."},
                    {"section": "Solution 2", "guide": "Moreover, offering subsidies could encourage..."}
                ]
            },
            {
                "part": "PART_3",
                "sub_topic": "Transportation",
                "question_text": "Do you think private cars will be completely replaced by public transport in the future?",
                "useful_vocabulary": ["Phase out", "Plausible", "Utmost convenience", "Shift towards"],
                "ielts_tips": ["Câu hỏi về tương lai -> Dùng Future tenses hoặc Modal verbs of probability (might, could, is likely to)."],
                "examiner_tip": "Trình bày cả 2 mặt của vấn đề trước khi chốt quan điểm cá nhân.",
                "response_structure": [
                    {"section": "Opinion", "guide": "I highly doubt it, although there will be a shift."},
                    {"section": "Explanation", "guide": "While public transport is eco-friendly, private cars offer..."}
                ]
            },

            # ==================================================
            # PART 3: Tourism (3 câu)
            # ==================================================
            {
                "part": "PART_3",
                "sub_topic": "Tourism",
                "question_text": "How does tourism affect the environment?",
                "useful_vocabulary": ["Take a toll on", "Ecological footprint", "Exploitation of resources", "Littering"],
                "ielts_tips": ["Phân tích hệ quả tiêu cực, dùng các cụm danh từ mạnh."],
                "examiner_tip": "Liên kết logic giữa hành động của du khách và hệ quả.",
                "response_structure": [
                    {"section": "Direct Impact", "guide": "Mass tourism often takes a heavy toll on local ecosystems."},
                    {"section": "Example", "guide": "For instance, excessive littering and..."}
                ]
            },
            {
                "part": "PART_3",
                "sub_topic": "Tourism",
                "question_text": "Do you think international travel will become more popular in the future?",
                "useful_vocabulary": ["Globalization", "Accessibility", "A surge in", "Aviation industry"],
                "ielts_tips": ["Đưa ra dự đoán và nguyên nhân (do máy bay rẻ hơn, toàn cầu hóa...)."],
                "examiner_tip": "Thể hiện vốn từ vựng về xu hướng (trend vocabulary).",
                "response_structure": [
                    {"section": "Prediction", "guide": "Yes, I strongly believe we will see a surge in international travel."},
                    {"section": "Reason", "guide": "Thanks to budget airlines and globalization, traveling abroad has become..."}
                ]
            },
            {
                "part": "PART_3",
                "sub_topic": "Tourism",
                "question_text": "What are the benefits of traveling to foreign countries?",
                "useful_vocabulary": ["Cultural immersion", "Broaden one's horizons", "Foster tolerance", "Eye-opening"],
                "ielts_tips": ["Phân loại lợi ích: lợi ích cá nhân (học hỏi) và lợi ích xã hội (giao lưu văn hóa)."],
                "examiner_tip": "Câu hỏi cuối thường khá rộng, hãy trả lời bao quát và tóm tắt lại ý.",
                "response_structure": [
                    {"section": "Benefit 1", "guide": "On a personal level, it broadens one's horizons and..."},
                    {"section": "Benefit 2", "guide": "Additionally, it fosters cultural tolerance by..."}
                ]
            }
        ]
    }
]