from models.Reading import (
    ReadingPassageModel,
    ReadingMultipleChoiceModel,
    ReadingHeadingMatchingModel,
    ReadingFillBlankModel,
    ReadingTrueFalseNotGivenModel
)

MOCK_READING_PASSAGES = [
    {
        "passage": {
            "topic": "Technology & Society",
            "title": "The Evolution of Remote Work in the Digital Era",
            "content": """
                <p><strong>Paragraph 1</strong><br/>
                In recent years, remote work has transitioned from a rare perk to a global standard. Advances in cloud computing, communication platforms, and asynchronous collaboration tools have enabled teams to operate effectively across diverse time zones.
                One major phenomenon arising from this shift is the concept of digital nomadism. Professionals are no longer bound to a physical office, allowing them to travel the world while maintaining full-time careers.
                However, this flexibility comes with challenges such as isolation, tax complexities, and blurring boundaries between work and personal life.</p>
                
                <p><strong>Paragraph 2</strong><br/>
                Technological infrastructure is the bedrock of this transition. Without reliable high-speed internet and secure remote access networks, corporations could not safely outsource critical tasks.
                Cybersecurity has thus become a primary focus, prompting companies to implement end-to-end encryption and multi-factor authentication protocols.
                Consequently, the remote workforce relies heavily on IT support teams to navigate daily technical hurdles.</p>
                
                <p><strong>Paragraph 3</strong><br/>
                Despite the clear benefits of convenience and cost savings, employers must also address psychological factors. Zoom fatigue and lack of casual face-to-face interaction can decrease overall team morale.
                To combat this, forward-thinking organizations are scheduling virtual team-building events and encouraging staff to set strict work-life boundaries.
                Managing a distributed workforce ultimately demands empathy and strong organizational communication.</p>
            """,
            "image_url": "https://images.unsplash.com/photo-1522202176988-66273c2fd55f",
            "time_limit_minutes": 15,
            "total_questions": 11,
            "learning_tip": "Hãy đọc lướt (Skimming) để nắm ý chính của từng đoạn văn trước khi trả lời câu hỏi."
        },
        "multiple_choices": [
            {
                "order": 1,
                "question_text": "What has driven the shift towards global remote work standards?",
                "options": [
                    "A. High real estate prices in big cities",
                    "B. Advances in cloud computing and collaboration tools",
                    "C. Direct mandates from international labor unions",
                    "D. Decreased global travel costs"
                ],
                "correct_answer": "B. Advances in cloud computing and collaboration tools",
                "excerpt": "Advances in cloud computing, communication platforms, and asynchronous collaboration tools have enabled teams to operate effectively across diverse time zones.",
                "explanation": "Đoạn văn chỉ rõ tiến bộ trong công nghệ điện toán đám mây và các công cụ cộng tác là yếu tố chính thúc đẩy sự chuyển dịch này."
            },
            {
                "order": 2,
                "question_text": "Which of the following is NOT mentioned as a challenge for digital nomads?",
                "options": [
                    "A. Feeling isolated",
                    "B. Navigating tax complexities",
                    "C. Lack of international flight options",
                    "D. Blurring work-life boundaries"
                ],
                "correct_answer": "C. Lack of international flight options",
                "excerpt": "However, this flexibility comes with challenges such as isolation, tax complexities, and blurring boundaries between work and personal life.",
                "explanation": "Đoạn văn đề cập đến sự cô đơn, thuế và ranh giới công việc, nhưng không nói gì về việc thiếu các chuyến bay quốc tế."
            }
        ],
        "heading_matchings": [
            {
                "order": 3,
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
                },
                "explanations": {
                    "paragraph_1": "Đoạn 1 thảo luận về xu hướng chuyển dịch của văn hóa làm việc linh hoạt toàn cầu.",
                    "paragraph_2": "Đoạn 2 tập trung vào hạ tầng công nghệ hỗ trợ làm việc từ xa.",
                    "paragraph_3": "Đoạn 3 bàn về các thách thức tâm lý và quản lý cần cân nhắc."
                },
                "excerpts": {
                    "paragraph_1": "In recent years, remote work has transitioned from a rare perk to a global standard.",
                    "paragraph_2": "Technological infrastructure is the bedrock of this transition.",
                    "paragraph_3": "Despite the clear benefits... employers must also address psychological factors."
                }
            }
        ],
        "fill_blanks": [
            {
                "order": 4,
                "passage_text": """
                    Remote work has evolved from a temporary solution to a [blank_1] business strategy. 
                    Companies are investing heavily in [blank_2] platforms to support distributed teams. 
                    However, managers must address [blank_3] concerns to maintain team cohesion.
                """,
                "blanks": [
                    {
                        "blank_id": "blank_1",
                        "correct_answer": "permanent",
                        "excerpt": "remote work has transitioned from a rare perk to a global standard",
                        "explanation": "Từ 'permanent' phù hợp với ý nghĩa chuyển đổi từ tạm thời sang lâu dài/chuẩn mực toàn cầu."
                    },
                    {
                        "blank_id": "blank_2",
                        "correct_answer": "collaboration",
                        "excerpt": "Advances in cloud computing, communication platforms, and asynchronous collaboration tools",
                        "explanation": "Đoạn văn đề cập đến các công cụ cộng tác (collaboration tools)."
                    },
                    {
                        "blank_id": "blank_3",
                        "correct_answer": "communication",
                        "excerpt": "Managing a distributed workforce ultimately demands empathy and strong organizational communication.",
                        "explanation": "Đoạn cuối nhấn mạnh tầm quan trọng của truyền thông tổ chức (communication)."
                    }
                ],
                "case_sensitive": False
            }
        ],
        "true_false_not_given": [
            {
                "order": 5,
                "statements": [
                    {
                        "statement": "Remote work was originally introduced as a permanent business model.",
                        "correct_answer": "FALSE",
                        "excerpt": "remote work has transitioned from a rare perk to a global standard",
                        "explanation": "Lúc đầu nó chỉ là một đặc quyền hiếm hoi (rare perk), không phải là mô hình lâu dài ngay từ đầu."
                    },
                    {
                        "statement": "Digital nomads are able to maintain their careers while traveling.",
                        "correct_answer": "TRUE",
                        "excerpt": "allowing them to travel the world while maintaining full-time careers.",
                        "explanation": "Đoạn văn xác nhận họ có thể đi du lịch vòng quanh thế giới mà vẫn duy trì công việc toàn thời gian."
                    },
                    {
                        "statement": "All companies have successfully implemented remote work policies.",
                        "correct_answer": "NOT GIVEN",
                        "excerpt": "",
                        "explanation": "Thông tin về việc 'tất cả' mọi công ty có triển khai thành công hay không không được đề cập trong bài."
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
                <p><strong>Paragraph 1</strong><br/>
                Metropolitan areas often experience the Urban Heat Island (UHI) effect, where concrete structures and asphalt absorb solar radiation, leading to significantly higher temperatures than surrounding rural areas.
                This temperature difference can escalate energy consumption due to air conditioning demands and threaten the health of vulnerable populations.</p>
                
                <p><strong>Paragraph 2</strong><br/>
                Urban greening—integrating vertical gardens, rooftop parks, and tree canopies—serves as a vital mitigation strategy. Plants absorb carbon dioxide and release water vapor through transpiration, providing natural cooling.
                Furthermore, root systems help manage stormwater runoff, preventing localized flash floods during heavy rainstorms.</p>
            """,
            "image_url": "https://images.unsplash.com/photo-1518531933037-91b2f5f229cc",
            "time_limit_minutes": 10,
            "total_questions": 9,
            "learning_tip": "Chú ý tới các thuật ngữ khoa học in đậm và đoạn giải thích ngay đằng sau nó."
        },
        "multiple_choices": [
            {
                "order": 1,
                "question_text": "What causes the Urban Heat Island (UHI) effect?",
                "options": [
                    "A. Overuse of air conditioning in high-rises",
                    "B. Concrete and asphalt absorbing solar radiation",
                    "C. Excessive water vapor in urban air",
                    "D. Lack of public transportation systems"
                ],
                "correct_answer": "B. Concrete and asphalt absorbing solar radiation",
                "excerpt": "...where concrete structures and asphalt absorb solar radiation, leading to significantly higher temperatures...",
                "explanation": "Lý do chính được bài viết nêu rõ là các cấu trúc bê tông và nhựa đường hấp thụ bức xạ mặt trời."
            }
        ],
        "heading_matchings": [
            {
                "order": 2,
                "headings": [
                    "A. Understanding Urban Heat Islands",
                    "B. Benefits of Green Infrastructure",
                    "C. Implementation Challenges"
                ],
                "correct_matches": {
                    "paragraph_1": "A. Understanding Urban Heat Islands",
                    "paragraph_2": "B. Benefits of Green Infrastructure"
                },
                "explanations": {
                    "paragraph_1": "Đoạn 1 định nghĩa và giải thích hiện tượng đảo nhiệt đô thị (UHI).",
                    "paragraph_2": "Đoạn 2 thảo luận về lợi ích làm mát và quản lý nước của hạ tầng xanh."
                },
                "excerpts": {
                    "paragraph_1": "Metropolitan areas often experience the Urban Heat Island (UHI) effect...",
                    "paragraph_2": "Urban greening—integrating vertical gardens... serves as a vital mitigation strategy."
                }
            }
        ],
        "fill_blanks": [
            {
                "order": 3,
                "passage_text": """
                    Urban greening initiatives include installing [blank_1] gardens on building facades 
                    and creating [blank_2] parks on rooftops. These strategies help reduce the 
                    [blank_3] effect in metropolitan areas.
                """,
                "blanks": [
                    {
                        "blank_id": "blank_1",
                        "correct_answer": "vertical",
                        "excerpt": "integrating vertical gardens, rooftop parks",
                        "explanation": "Đoạn văn nêu rõ tích hợp vườn thẳng đứng (vertical gardens)."
                    },
                    {
                        "blank_id": "blank_2",
                        "correct_answer": "rooftop",
                        "excerpt": "integrating vertical gardens, rooftop parks",
                        "explanation": "Rooftop parks là công viên trên mái nhà."
                    },
                    {
                        "blank_id": "blank_3",
                        "correct_answer": "urban heat island",
                        "excerpt": "Metropolitan areas often experience the Urban Heat Island (UHI) effect",
                        "explanation": "Thuật ngữ chính xác là hiệu ứng đảo nhiệt đô thị (Urban Heat Island effect)."
                    }
                ],
                "case_sensitive": False
            }
        ],
        "true_false_not_given": [
            {
                "order": 4,
                "statements": [
                    {
                        "statement": "Urban areas are typically cooler than rural areas.",
                        "correct_answer": "FALSE",
                        "excerpt": "...leading to significantly higher temperatures than surrounding rural areas.",
                        "explanation": "Bài viết nói đô thị có nhiệt độ cao hơn nhiều so với nông thôn, nên phát biểu đô thị mát hơn là SAI."
                    },
                    {
                        "statement": "Plants help cool urban areas through transpiration.",
                        "correct_answer": "TRUE",
                        "excerpt": "Plants absorb carbon dioxide and release water vapor through transpiration, providing natural cooling.",
                        "explanation": "Quá trình thoát hơi nước của thực vật giúp làm mát tự nhiên."
                    },
                    {
                        "statement": "Vertical gardens are more effective than rooftop parks.",
                        "correct_answer": "NOT GIVEN",
                        "excerpt": "",
                        "explanation": "Không có thông tin so sánh hiệu quả giữa vườn thẳng đứng và công viên sân thượng."
                    }
                ]
            }
        ]
    },
    {
        "passage": {
            "topic": "History & Culture",
            "title": "The History of Tea and Its Global Spread",
            "content": """
                <p><strong>Paragraph 1</strong><br/>
                Tea originated in ancient China, where it was initially utilized as a medicinal tonic. According to legend, Emperor Shennong discovered tea in 2737 BC when wild leaves drifted into his pot of boiling water, producing a pleasant aroma and refreshing taste.</p>
                
                <p><strong>Paragraph 2</strong><br/>
                During the Tang Dynasty, tea drinking became an art form and spread to Japan via Buddhist monks. In the 17th century, Portuguese traders introduced tea to European aristocrats, where it quickly became a symbol of high social status, particularly in Great Britain.</p>
            """,
            "image_url": "https://images.unsplash.com/photo-1576092768241-dec231879fc3",
            "time_limit_minutes": 10,
            "total_questions": 6,
            "learning_tip": "Hãy chú ý đến các mốc thời gian và địa danh để xác định tiến trình lịch sử trong bài."
        },
        "multiple_choices": [
            {
                "order": 1,
                "question_text": "According to legend, who discovered tea?",
                "options": [
                    "A. Portuguese merchants",
                    "B. Buddhist monks",
                    "C. Emperor Shennong",
                    "D. British aristocrats"
                ],
                "correct_answer": "C. Emperor Shennong",
                "excerpt": "According to legend, Emperor Shennong discovered tea in 2737 BC...",
                "explanation": "Truyền thuyết kể rằng Hoàng đế Thần Nông đã phát hiện ra trà."
            }
        ],
        "heading_matchings": [
            {
                "order": 2,
                "headings": [
                    "A. Origins and Legends",
                    "B. Integration into Global Trade",
                    "C. Tea Culture in the Tang Dynasty"
                ],
                "correct_matches": {
                    "paragraph_1": "A. Origins and Legends",
                    "paragraph_2": "B. Integration into Global Trade"
                },
                "explanations": {
                    "paragraph_1": "Đoạn 1 kể về nguồn gốc và truyền thuyết hoàng đế Thần Nông phát hiện ra trà.",
                    "paragraph_2": "Đoạn 2 nói về việc trà du nhập vào châu Âu và thương mại toàn cầu thông qua các nhà buôn Bồ Đào Nha."
                },
                "excerpts": {
                    "paragraph_1": "Tea originated in ancient China, where it was initially utilized...",
                    "paragraph_2": "Portuguese traders introduced tea to European aristocrats, where it quickly became..."
                }
            }
        ],
        "fill_blanks": [
            {
                "order": 3,
                "passage_text": """
                    Tea was first consumed in [blank_1] as a medicine. Later, Buddhist monks introduced 
                    this beverage to [blank_2]. By the 17th century, it reached European high society.
                """,
                "blanks": [
                    {
                        "blank_id": "blank_1",
                        "correct_answer": "China",
                        "excerpt": "Tea originated in ancient China, where it was initially utilized as a medicinal tonic.",
                        "explanation": "Trà có nguồn gốc từ Trung Quốc cổ đại và được dùng như thuốc bổ."
                    },
                    {
                        "blank_id": "blank_2",
                        "correct_answer": "Japan",
                        "excerpt": "...and spread to Japan via Buddhist monks.",
                        "explanation": "Các nhà sư Phật giáo đã truyền bá thói quen uống trà sang Nhật Bản."
                    }
                ],
                "case_sensitive": False
            }
        ],
        "true_false_not_given": [
            {
                "order": 4,
                "statements": [
                    {
                        "statement": "Tea was originally consumed purely for pleasure in ancient China.",
                        "correct_answer": "FALSE",
                        "excerpt": "...where it was initially utilized as a medicinal tonic.",
                        "explanation": "Trà ban đầu được dùng làm thuốc bổ cứu thương chứ không phải chỉ để thưởng thức giải trí."
                    }
                ]
            }
        ]
    },
    {
        "passage": {
            "topic": "Science & Tech",
            "title": "Renewable Energy and the Power Grid",
            "content": """
                <p><strong>Paragraph 1</strong><br/>
                The integration of renewable energy sources, such as wind and solar power, into national grids is crucial for reducing carbon emissions. However, their intermittent nature poses stability issues, requiring large-scale battery storage and smart grid technology.</p>
                
                <p><strong>Paragraph 2</strong><br/>
                Smart grids utilize digital communication technology to detect and react to local changes in usage. They automatically adjust electricity flow, minimizing blackouts and optimizing energy efficiency.</p>
            """,
            "image_url": "https://images.unsplash.com/photo-1509391366360-2e959784a276",
            "time_limit_minutes": 10,
            "total_questions": 6,
            "learning_tip": "Nắm vững mối quan hệ nhân quả giữa tính không ổn định của năng lượng tái tạo và giải pháp lưới điện thông minh."
        },
        "multiple_choices": [
            {
                "order": 1,
                "question_text": "What is the primary challenge of wind and solar power?",
                "options": [
                    "A. High carbon footprint",
                    "B. Intermittent nature",
                    "C. Lack of consumer demand",
                    "D. High transmission loss"
                ],
                "correct_answer": "B. Intermittent nature",
                "excerpt": "However, their intermittent nature poses stability issues...",
                "explanation": "Tính không liên tục (lúc có lúc không) là thách thức lớn nhất của điện gió và điện mặt trời."
            }
        ],
        "heading_matchings": [
            {
                "order": 2,
                "headings": [
                    "A. Challenges of Renewables",
                    "B. Smart Grid Capabilities",
                    "C. Government Subsidies"
                ],
                "correct_matches": {
                    "paragraph_1": "A. Challenges of Renewables",
                    "paragraph_2": "B. Smart Grid Capabilities"
                },
                "explanations": {
                    "paragraph_1": "Đoạn 1 nêu lên sự bất ổn của nguồn năng lượng sạch.",
                    "paragraph_2": "Đoạn 2 giải thích cơ chế lưới điện thông minh để điều phối dòng điện."
                },
                "excerpts": {
                    "paragraph_1": "...their intermittent nature poses stability issues...",
                    "paragraph_2": "Smart grids utilize digital communication technology to detect and react..."
                }
            }
        ],
        "fill_blanks": [
            {
                "order": 3,
                "passage_text": """
                    Wind and solar power are [blank_1] sources, meaning they do not produce energy constantly. 
                    To solve this, smart grids automatically adjust electricity [blank_2].
                """,
                "blanks": [
                    {
                        "blank_id": "blank_1",
                        "correct_answer": "intermittent",
                        "excerpt": "However, their intermittent nature poses stability issues...",
                        "explanation": "Bản chất ngắt quãng/không liên tục của năng lượng tái tạo."
                    },
                    {
                        "blank_id": "blank_2",
                        "correct_answer": "flow",
                        "excerpt": "They automatically adjust electricity flow...",
                        "explanation": "Hệ thống tự động điều chỉnh dòng chảy điện năng."
                    }
                ],
                "case_sensitive": False
            }
        ],
        "true_false_not_given": [
            {
                "order": 4,
                "statements": [
                    {
                        "statement": "Smart grids eliminate all risk of power outages.",
                        "correct_answer": "FALSE",
                        "excerpt": "...minimizing blackouts and optimizing energy efficiency.",
                        "explanation": "Hệ thống thông minh chỉ giúp giảm thiểu (minimizing), chứ không thể loại bỏ hoàn toàn (eliminate) mọi nguy cơ mất điện."
                    }
                ]
            }
        ]
    },
    {
        "passage": {
            "topic": "Psychology",
            "title": "The Psychology of Decision Making",
            "content": """
                <p><strong>Paragraph 1</strong><br/>
                Human decision-making is rarely purely logical. Psychologists have identified cognitive biases, such as loss aversion, where people feel the pain of losing something twice as intensely as the pleasure of gaining it. This bias leads to risk-averse choices in everyday situations.</p>
                
                <p><strong>Paragraph 2</strong><br/>
                Another common phenomenon is decision fatigue. As individuals make more choices throughout the day, the quality of their decisions deteriorates. Consequently, companies often place small, impulse-buy products near checkout counters to exploit this state.</p>
            """,
            "image_url": "https://images.unsplash.com/photo-1507537297725-24a1c029d3ca",
            "time_limit_minutes": 10,
            "total_questions": 6,
            "learning_tip": "Nhận biết các thuật ngữ tâm lý học hành vi và ví dụ thực tế đi kèm trong từng đoạn văn."
        },
        "multiple_choices": [
            {
                "order": 1,
                "question_text": "What does loss aversion describe?",
                "options": [
                    "A. A preference for risky financial ventures",
                    "B. Feeling the pain of loss more intensely than the pleasure of gain",
                    "C. Forgetting past losses quickly",
                    "D. A logical assessment of gains and losses"
                ],
                "correct_answer": "B. Feeling the pain of loss more intensely than the pleasure of gain",
                "excerpt": "...where people feel the pain of losing something twice as intensely as the pleasure of gaining it.",
                "explanation": "Hiệu ứng sợ mất mát mô tả việc con người cảm thấy nỗi đau mất mát mạnh hơn niềm vui có được thứ tương tự."
            }
        ],
        "heading_matchings": [
            {
                "order": 2,
                "headings": [
                    "A. Cognitive Biases and Loss Aversion",
                    "B. The Effect of Decision Fatigue",
                    "C. Methods for Better Choices"
                ],
                "correct_matches": {
                    "paragraph_1": "A. Cognitive Biases and Loss Aversion",
                    "paragraph_2": "B. The Effect of Decision Fatigue"
                },
                "explanations": {
                    "paragraph_1": "Đoạn 1 tập trung định nghĩa định kiến nhận thức và tâm lý sợ mất mát.",
                    "paragraph_2": "Đoạn 2 giải thích sự mệt mỏi khi đưa ra quyết định vào cuối ngày."
                },
                "excerpts": {
                    "paragraph_1": "Psychologists have identified cognitive biases, such as loss aversion...",
                    "paragraph_2": "Another common phenomenon is decision fatigue."
                }
            }
        ],
        "fill_blanks": [
            {
                "order": 3,
                "passage_text": """
                    Loss aversion makes people prefer [blank_1] decisions. 
                    Furthermore, decision [blank_2] explains why decision quality drops over time.
                """,
                "blanks": [
                    {
                        "blank_id": "blank_1",
                        "correct_answer": "risk-averse",
                        "excerpt": "This bias leads to risk-averse choices in everyday situations.",
                        "explanation": "Tâm lý sợ mất mát dẫn tới các quyết định né tránh rủi ro (risk-averse)."
                    },
                    {
                        "blank_id": "blank_2",
                        "correct_answer": "fatigue",
                        "excerpt": "Another common phenomenon is decision fatigue.",
                        "explanation": "Hiện tượng mệt mỏi khi ra quyết định (decision fatigue)."
                    }
                ],
                "case_sensitive": False
            }
        ],
        "true_false_not_given": [
            {
                "order": 4,
                "statements": [
                    {
                        "statement": "Decision fatigue causes people to make better decisions at the end of the day.",
                        "correct_answer": "FALSE",
                        "excerpt": "...the quality of their decisions deteriorates.",
                        "explanation": "Bài viết nói chất lượng quyết định bị giảm sút (deteriorates) chứ không phải tốt hơn."
                    }
                ]
            }
        ]
    }
]
