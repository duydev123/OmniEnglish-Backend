import logging
from models.WritingModel import WritingPromptModel

logger = logging.getLogger("WritingSeed")

async def seed_writing_prompts():
    existing_count = await WritingPromptModel.count()
    if existing_count > 0:
        logger.info(f"Writing prompts already seeded ({existing_count} prompts). Skipping seed.")
        return

    prompts = [
        WritingPromptModel(
            title="Urban Dynamics: Heritage Architecture vs Modern Skyscrapers",
            task_type="WITH_GRAPH",
            task_description='Analyze the provided image depicting urban development. Describe the contrast between heritage architecture and modern skyscrapers, focusing on the socio-economic implications of this transition.',
            reference_image_url="https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=800&auto=format&fit=crop&q=80",
            ref_id="ARCH-204-URB",
            time_limit_minutes=45,
            word_count_target=250,
            suggested_structure=[
                {
                    "section": "Introduction",
                    "guide": "Hook, background of the city, and your clear stance."
                },
                {
                    "section": "Body Paragraph 1",
                    "guide": "Visual analysis: Texture of stone vs. glass high-rises."
                },
                {
                    "section": "Body Paragraph 2",
                    "guide": "Socio-economic analysis: Economic growth vs gentrification."
                },
                {
                    "section": "Conclusion",
                    "guide": "Synthesize key points and state final recommendations."
                }
            ],
            advanced_vocabulary=["Juxtaposition", "Obsolescence", "Stratification", "Gentrifaction", "Equilibrium"]
        ),
        WritingPromptModel(
            title="The Impact of Artificial Intelligence on Higher Education",
            task_type="WITHOUT_GRAPH",
            task_description='Many experts argue that artificial intelligence tools like AI tutors and automated feedback systems will revolutionize education, while others fear they diminish human interaction. Discuss both views and give your own opinion.',
            reference_image_url=None,
            ref_id="EDU-501-AI",
            time_limit_minutes=40,
            word_count_target=250,
            suggested_structure=[
                {
                    "section": "Introduction",
                    "guide": "Introduce the debate surrounding AI in education and state your thesis."
                },
                {
                    "section": "Body Paragraph 1",
                    "guide": "Discuss the advantages of AI tools (personalized learning, instant feedback)."
                },
                {
                    "section": "Body Paragraph 2",
                    "guide": "Discuss concerns regarding loss of human empathy and critical thinking."
                },
                {
                    "section": "Conclusion",
                    "guide": "Summarize arguments and present a balanced verdict."
                }
            ],
            advanced_vocabulary=["Catalyst", "Personalization", "Paradigm Shift", "Pedagogical", "Technological Integration"]
        ),
        WritingPromptModel(
            title="Environmental Protection vs Economic Growth",
            task_type="WITHOUT_GRAPH",
            task_description='Developing countries face a hard choice between economic expansion and environmental sustainability. To what extent should economic progress take precedence over ecological preservation?',
            reference_image_url=None,
            ref_id="ENV-302-ECO",
            time_limit_minutes=40,
            word_count_target=250,
            suggested_structure=[
                {
                    "section": "Introduction",
                    "guide": "State the dilemma of developing nations and your opinion."
                },
                {
                    "section": "Body Paragraph 1",
                    "guide": "Explore the urgent need for industrial growth and poverty alleviation."
                },
                {
                    "section": "Body Paragraph 2",
                    "guide": "Analyze long-term consequences of environmental degradation."
                },
                {
                    "section": "Conclusion",
                    "guide": "Advocate for green economy and sustainable growth solutions."
                }
            ],
            advanced_vocabulary=["Sustainability", "Degradation", "Industrialization", "Mitigation", "Eco-friendly Infrastructure"]
        )
    ]

    for p in prompts:
        await p.insert()
    logger.info(f"Successfully seeded {len(prompts)} writing prompts.")
