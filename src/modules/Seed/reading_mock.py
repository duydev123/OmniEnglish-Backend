from models.Reading import (
    ReadingPassageModel,
    ReadingMultipleChoiceModel,
    ReadingHeadingMatchingModel,
    ReadingFillBlankModel
)
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
            "total_questions": 14,  # ← Cập nhật tổng số câu hỏi (2 MC + 3 Vocab + 2 Sentence + 3 Heading + 4 TFNG)
            "learning_tip": "Hãy đọc lướt (Skimming) để nắm ý chính của từng đoạn văn trước khi trả lời câu hỏi."
        },
        
        # 3. MULTIPLE CHOICE
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
        ],
        
        # 4. HEADING MATCHING
        "heading_matchings": [
            {
                "order": 5,
                "headings": [
                    "A. The Rise of Flexible Work Culture",
                    "B. Technological Enablers",
                    "C. Challenges and Considerations",
                    "D. Future Outlook"
                ],
                "correct_matches": {
                    "paragraph_1": "A. The Rise of Flexible Work Culture",
                    "paragraph_2": "B. Technological Enablers",
                    "paragraph_3": "C. Challenges and Considerations"
                }
            }
        ],
        
        # 5. FILL-IN-THE-BLANK
        "fill_blanks": [
            {
                "order": 6,
                "passage_text": """
                    Remote work has evolved from a temporary solution to a [blank_1] business strategy. 
                    Companies are investing heavily in [blank_2] platforms to support distributed teams. 
                    However, managers must address [blank_3] concerns to maintain team cohesion.
                """,
                "blanks": [
                    {"blank_id": "blank_1", "correct_answer": "permanent"},
                    {"blank_id": "blank_2", "correct_answer": "collaboration"},
                    {"blank_id": "blank_3", "correct_answer": "communication"}
                ],
                "case_sensitive": False
            }
        ],
        
        # 6. TRUE/FALSE/NOT GIVEN
        "true_false_not_given": [
            {
                "order": 7,
                "statements": [
                    {
                        "statement": "Remote work was originally introduced as a permanent business model.",
                        "correct_answer": "FALSE"
                    },
                    {
                        "statement": "Digital nomads are able to maintain their careers while traveling.",
                        "correct_answer": "TRUE"
                    },
                    {
                        "statement": "All companies have successfully implemented remote work policies.",
                        "correct_answer": "NOT GIVEN"
                    },
                    {
                        "statement": "Tax complexities are one of the challenges faced by digital nomads.",
                        "correct_answer": "TRUE"
                    }
                ]
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
            "total_questions": 8,  # 1 MC + 2 Heading + 3 Fill + 3 TFNG = 9 (điều chỉnh)
            "learning_tip": "Chú ý tới các thuật ngữ khoa học in đậm và đoạn giải thích ngay đằng sau nó."
        },
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
        ],
        
        "heading_matchings": [
            {
                "order": 3,
                "headings": [
                    "A. Understanding Urban Heat Islands",
                    "B. Benefits of Green Infrastructure",
                    "C. Implementation Challenges"
                ],
                "correct_matches": {
                    "paragraph_1": "A. Understanding Urban Heat Islands",
                    "paragraph_2": "B. Benefits of Green Infrastructure"
                }
            }
        ],
        
        "fill_blanks": [
            {
                "order": 4,
                "passage_text": """
                    Urban greening initiatives include installing [blank_1] gardens on building facades 
                    and creating [blank_2] parks on rooftops. These strategies help reduce the 
                    [blank_3] effect in metropolitan areas.
                """,
                "blanks": [
                    {"blank_id": "blank_1", "correct_answer": "vertical"},
                    {"blank_id": "blank_2", "correct_answer": "rooftop"},
                    {"blank_id": "blank_3", "correct_answer": "urban heat island"}
                ],
                "case_sensitive": False
            }
        ],
        
        "true_false_not_given": [
            {
                "order": 5,
                "statements": [
                    {
                        "statement": "Urban areas are typically cooler than rural areas.",
                        "correct_answer": "FALSE"
                    },
                    {
                        "statement": "Plants help cool urban areas through transpiration.",
                        "correct_answer": "TRUE"
                    },
                    {
                        "statement": "Vertical gardens are more effective than rooftop parks.",
                        "correct_answer": "NOT GIVEN"
                    }
                ]
            }
        ]
    }
]

# MOCK_HEADING_MATCHINGS = [
#     {
#         "passage_title": "The Evolution of Remote Work in the Digital Era",
#         "headings": [
#             "A. The Rise of Flexible Work Culture",
#             "B. Technological Enablers",
#             "C. Challenges and Considerations",
#             "D. Future Outlook"
#         ],
#         "correct_matches": {
#             "paragraph_1": "A. The Rise of Flexible Work Culture",
#             "paragraph_2": "B. Technological Enablers",
#             "paragraph_3": "C. Challenges and Considerations"
#         }
#     },
#     {
#         "passage_title": "Urban Greening and Microclimate Control",
#         "headings": [
#             "A. Understanding Urban Heat Islands",
#             "B. Benefits of Green Infrastructure",
#             "C. Implementation Challenges"
#         ],
#         "correct_matches": {
#             "paragraph_1": "A. Understanding Urban Heat Islands",
#             "paragraph_2": "B. Benefits of Green Infrastructure"
#         }
#     }
# ]
# MOCK_FILL_BLANKS = [
#     {
#         "passage_title": "The Evolution of Remote Work in the Digital Era",
#         "passage_text": """
#             Remote work has evolved from a temporary solution to a [blank_1] business strategy. 
#             Companies are investing heavily in [blank_2] platforms to support distributed teams. 
#             However, managers must address [blank_3] concerns to maintain team cohesion.
#         """,
#         "blanks": [
#             {"blank_id": "blank_1", "correct_answer": "permanent"},
#             {"blank_id": "blank_2", "correct_answer": "collaboration"},
#             {"blank_id": "blank_3", "correct_answer": "communication"}
#         ],
#         "case_sensitive": False
#     },
#     {
#         "passage_title": "Urban Greening and Microclimate Control",
#         "passage_text": """
#             Urban greening initiatives include installing [blank_1] gardens on building facades 
#             and creating [blank_2] parks on rooftops. These strategies help reduce the 
#             [blank_3] effect in metropolitan areas.
#         """,
#         "blanks": [
#             {"blank_id": "blank_1", "correct_answer": "vertical"},
#             {"blank_id": "blank_2", "correct_answer": "rooftop"},
#             {"blank_id": "blank_3", "correct_answer": "urban heat island"}
#         ],
#         "case_sensitive": False
#     }
# ]
# MOCK_TRUE_FALSE_NOT_GIVEN = [
#     {
#         "passage_title": "The Evolution of Remote Work in the Digital Era",
#         "statements": [
#             {
#                 "statement": "Remote work was originally introduced as a permanent business model.",
#                 "correct_answer": "FALSE"
#             },
#             {
#                 "statement": "Digital nomads are able to maintain their careers while traveling.",
#                 "correct_answer": "TRUE"
#             },
#             {
#                 "statement": "All companies have successfully implemented remote work policies.",
#                 "correct_answer": "NOT GIVEN"
#             },
#             {
#                 "statement": "Tax complexities are one of the challenges faced by digital nomads.",
#                 "correct_answer": "TRUE"
#             }
#         ]
#     },
#     {
#         "passage_title": "Urban Greening and Microclimate Control",
#         "statements": [
#             {
#                 "statement": "Urban areas are typically cooler than rural areas.",
#                 "correct_answer": "FALSE"
#             },
#             {
#                 "statement": "Plants help cool urban areas through transpiration.",
#                 "correct_answer": "TRUE"
#             },
#             {
#                 "statement": "Vertical gardens are more effective than rooftop parks.",
#                 "correct_answer": "NOT GIVEN"
#             }
#         ]
#     }
# ]