# src/modules/Seed/reading_mock.py

MOCK_READING_PASSAGES = [
    {
        "passage": {
            "topic": "Technology & Society",
            "title": "The Evolution of Remote Work in the Digital Era",
            "content": """
            
                The Changing Paradigm of Work
                In recent years, remote work has transitioned from a rare perk to a global standard. Advances in cloud computing, communication platforms, and asynchronous collaboration tools have enabled teams to operate effectively across diverse time zones.
                One major phenomenon arising from this shift is the concept of digital nomadism. Professionals are no longer bound to a physical office, allowing them to travel the world while maintaining full-time careers.
                However, this flexibility comes with challenges such as isolation, tax complexities, and blurring boundaries between work and personal life.
            
            """,
            "image_url": "https://images.unsplash.com/photo-1522202176988-66273c2fd55f",
            "time_limit_minutes": 15,
            "total_questions": 5,
            "learning_tip": "Hãy đọc lướt (Skimming) để nắm ý chính của từng đoạn văn trước khi trả lời câu hỏi."
        },
        "vocab_matchings": [
            {
                "order": 1,
                "pairs": [
                    {"term": "Asynchronous", "definition": "Not existing or happening at the same time"},
                    {"term": "Digital Nomad", "definition": "A person who earns a living working online while traveling"},
                    {"term": "Paradigm", "definition": "A typical example or pattern of something"}
                ]
            }
        ],
        "sentence_completions": [
            {
                "order": 2,
                "template_text": "Remote work has shifted from a rare perk to a [gap_1] standard. Professionals who travel while working online are known as [gap_2].",
                "correct_answers": {
                    "gap_1": "global",
                    "gap_2": "digital nomads"
                },
                "case_sensitive": False
            }
        ],
        "multiple_choices": [
            {
                "order": 3,
                "question_text": "What has driven the shift towards global remote work standards?",
                "options": [
                    "A. High real estate prices in big cities",
                    "B. Advances in cloud computing and collaboration tools",
                    "C. Direct mandates from international labor unions",
                    "D. Decreased global travel costs"
                ],
                "correct_answer": "B. Advances in cloud computing and collaboration tools"
            },
            {
                "order": 4,
                "question_text": "Which of the following is NOT mentioned as a challenge for digital nomads?",
                "options": [
                    "A. Feeling isolated",
                    "B. Navigating tax complexities",
                    "C. Lack of international flight options",
                    "D. Blurring work-life boundaries"
                ],
                "correct_answer": "C. Lack of international flight options"
            }
        ]
    },
    {
        "passage": {
            "topic": "Environment & Science",
            "title": "Urban Greening and Microclimate Control",
            "content": """
            
                Cooling Down Concrete Jungles
                Metropolitan areas often experience the Urban Heat Island (UHI) effect, where concrete structures and asphalt absorb solar radiation, leading to significantly higher temperatures than surrounding rural areas.
                Urban greening—integrating vertical gardens, rooftop parks, and tree canopies—serves as a vital mitigation strategy. Plants absorb carbon dioxide and release water vapor through transpiration, providing natural cooling.
            
            """,
            "image_url": "https://images.unsplash.com/photo-1518531933037-91b2f5f229cc",
            "time_limit_minutes": 10,
            "total_questions": 3,
            "learning_tip": "Chú ý tới các thuật ngữ khoa học in đậm và đoạn giải thích ngay đằng sau nó."
        },
        "vocab_matchings": [
            {
                "order": 1,
                "pairs": [
                    {"term": "Mitigation", "definition": "The action of reducing the severity or seriousness of something"},
                    {"term": "Transpiration", "definition": "Process where plants absorb water through roots and give off vapor through pores"}
                ]
            }
        ],
        "sentence_completions": [],
        "multiple_choices": [
            {
                "order": 2,
                "question_text": "What causes the Urban Heat Island (UHI) effect?",
                "options": [
                    "A. Overuse of air conditioning in high-rises",
                    "B. Concrete and asphalt absorbing solar radiation",
                    "C. Excessive water vapor in urban air",
                    "D. Lack of public transportation systems"
                ],
                "correct_answer": "B. Concrete and asphalt absorbing solar radiation"
            }
        ]
    }
]