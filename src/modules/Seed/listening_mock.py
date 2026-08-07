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
        "audio_segments": [
            {
                "key": "segment_1",
                "start_time_ms": 3000,
                "end_time_ms": 8000,
                "transcript": "Today is November 26th.",
                "transcript_json": [
                    {"word": "Today", "start_ms": 3000, "end_ms": 3500},
                    {"word": "is", "start_ms": 3500, "end_ms": 3800},
                    {"word": "November", "start_ms": 3800, "end_ms": 4500},
                    {"word": "26th", "start_ms": 4500, "end_ms": 5200}
                ]
            },
            {
                "key": "segment_2",
                "start_time_ms": 9000,
                "end_time_ms": 15000,
                "transcript": "It snowed all day yesterday.",
                "transcript_json": [
                    {"word": "It", "start_ms": 9000, "end_ms": 9300},
                    {"word": "snowed", "start_ms": 9300, "end_ms": 10000},
                    {"word": "all", "start_ms": 10000, "end_ms": 10500},
                    {"word": "day", "start_ms": 10500, "end_ms": 11000},
                    {"word": "yesterday", "start_ms": 11000, "end_ms": 12000}
                ]
            },
            {
                "key": "segment_3",
                "start_time_ms": 23000,
                "end_time_ms": 28000,
                "transcript": "I need to wear a warm coat and gloves.",
                "transcript_json": [
                    {"word": "I", "start_ms": 23000, "end_ms": 23300},
                    {"word": "need", "start_ms": 23300, "end_ms": 23800},
                    {"word": "to", "start_ms": 23800, "end_ms": 24000},
                    {"word": "wear", "start_ms": 24000, "end_ms": 24300},
                    {"word": "a", "start_ms": 24300, "end_ms": 24500},
                    {"word": "warm", "start_ms": 24500, "end_ms": 25000},
                    {"word": "coat", "start_ms": 25000, "end_ms": 25500},
                    {"word": "and", "start_ms": 25500, "end_ms": 25800},
                    {"word": "gloves", "start_ms": 25800, "end_ms": 26500}
                ]
            }
        ],
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
                "audio_segment_key": "segment_1",
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
                "audio_segment_key": "segment_2",
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
                "audio_segment_key": "segment_3",
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
        "audio_segments": [
            {
                "key": "negotiation_seg_1",
                "start_time_ms": 5000,
                "end_time_ms": 12000,
                "transcript": "Good morning, everyone. Thank you for coming to this meeting."
            },
            {
                "key": "negotiation_seg_2",
                "start_time_ms": 13000,
                "end_time_ms": 20000,
                "transcript": "Today we are going to discuss the new project timeline."
            },
            {
                "key": "negotiation_seg_3",
                "start_time_ms": 21000,
                "end_time_ms": 28000,
                "transcript": "We need to deliver the first phase by next month."
            }
        ],
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
                "audio_segment_key": "negotiation_seg_2",
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
                "audio_segment_key": "negotiation_seg_3",
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
                "audio_segment_key": "negotiation_seg_2",
                "case_sensitive": False
            }
        ]
    }
]