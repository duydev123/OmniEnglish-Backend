
MOCK_LISTENING_PASSAGES = [
    {
        "passage": {
            "title": "FIRST SNOWFALL",
            "unit_code": "UNIT04",
            "audio_url": "https://example.com/audio/first_snowfall.mp3",
            "time_limit_minutes": 15,
            "total_questions": 5,
            "interactive_transcript": [
                {
                    "start_time": "0:03",
                    "end_time": "0:08",
                    "en": "Today is November 26th.",
                    "vi": "Hôm nay là ngày 26 tháng 11."
                },
                {
                    "start_time": "0:09",
                    "end_time": "0:15",
                    "en": "It snowed all day yesterday.",
                    "vi": "Hôm qua trời tuyết rơi cả ngày."
                },
                {
                    "start_time": "0:16",
                    "end_time": "0:22",
                    "en": "The snow is beautiful, but it's very cold.",
                    "vi": "Tuyết đẹp nhưng rất lạnh."
                },
                {
                    "start_time": "0:23",
                    "end_time": "0:28",
                    "en": "I need to wear a warm coat and gloves.",
                    "vi": "Tôi cần mặc áo khoác ấm và đeo găng tay."
                }
            ],
            "key_vocabulary": [
                {"word": "Snowfall", "meaning": "The amount of snow that falls in a particular area"},
                {"word": "Coat", "meaning": "An outer garment worn outdoors"}
            ]
        },
        "multiple_choices": [
            {
                "order": 1,
                "question_text": "What is the date in the audio?",
                "options": [
                    "A. November 26th",
                    "B. November 27th",
                    "C. December 26th",
                    "D. December 27th"
                ],
                "correct_answer": "A. November 26th",
                "timestamp_clip": "0:03",
                "competency_type": "Specific Information Retrieval",
                "learning_hint": "Listen carefully to the date mentioned at the beginning."
            },
            {
                "order": 2,
                "question_text": "What did the speaker say about yesterday?",
                "options": [
                    "A. It was sunny",
                    "B. It snowed all day",
                    "C. It rained heavily",
                    "D. It was warm"
                ],
                "correct_answer": "B. It snowed all day",
                "timestamp_clip": "0:09",
                "competency_type": "Specific Information Retrieval",
                "learning_hint": "Focus on what happened yesterday."
            }
        ],
        "completions": [
            {
                "order": 3,
                "template_text": "The speaker needs to wear a warm [gap_1] and [gap_2].",
                "correct_answers": {
                    "gap_1": "coat",
                    "gap_2": "gloves"
                },
                "case_sensitive": False
            }
        ]
    },
    {
        "passage": {
            "title": "Business Negotiation",
            "unit_code": "UNIT08",
            "audio_url": "https://example.com/audio/business_negotiation.mp3",
            "time_limit_minutes": 20,
            "total_questions": 6,
            "interactive_transcript": [
                {
                    "start_time": "0:05",
                    "end_time": "0:12",
                    "en": "Good morning, everyone. Thank you for coming to this meeting.",
                    "vi": "Chào buổi sáng mọi người. Cảm ơn các bạn đã đến cuộc họp này."
                },
                {
                    "start_time": "0:13",
                    "end_time": "0:20",
                    "en": "Today we are going to discuss the new project timeline.",
                    "vi": "Hôm nay chúng ta sẽ thảo luận về tiến độ dự án mới."
                },
                {
                    "start_time": "0:21",
                    "end_time": "0:28",
                    "en": "We need to deliver the first phase by next month.",
                    "vi": "Chúng ta cần bàn giao giai đoạn đầu vào tháng tới."
                }
            ],
            "key_vocabulary": [
                {"word": "Negotiation", "meaning": "Discussion aimed at reaching an agreement"},
                {"word": "Timeline", "meaning": "A schedule of events or deadlines"}
            ]
        },
        "multiple_choices": [
            {
                "order": 1,
                "question_text": "What is the main topic of the meeting?",
                "options": [
                    "A. New project timeline",
                    "B. Company budget",
                    "C. Employee benefits",
                    "D. Marketing strategy"
                ],
                "correct_answer": "A. New project timeline",
                "timestamp_clip": "0:13",
                "competency_type": "Global Understanding",
                "learning_hint": "Listen for the main topic announced at the start."
            },
            {
                "order": 2,
                "question_text": "When does the first phase need to be delivered?",
                "options": [
                    "A. This week",
                    "B. Next week",
                    "C. Next month",
                    "D. Next year"
                ],
                "correct_answer": "C. Next month",
                "timestamp_clip": "0:21",
                "competency_type": "Specific Information Retrieval",
                "learning_hint": "Pay attention to the deadline mentioned."
            }
        ],
        "completions": [
            {
                "order": 3,
                "template_text": "The meeting is about discussing the new [gap_1].",
                "correct_answers": {
                    "gap_1": "project timeline"
                },
                "case_sensitive": False
            }
        ]
    }
]