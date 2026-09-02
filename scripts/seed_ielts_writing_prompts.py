import asyncio
import os
import sys
import logging
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath('src'))

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from models.Writing import WritingPromptModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IELTSWritingSeed")

load_dotenv()

async def seed_writing():
    mongo_uri = os.getenv("MONGO_URI", "mongodb+srv://omni_english_db:duy123@cluster0.0clx1qx.mongodb.net/?appName=Cluster0")
    client = AsyncIOMotorClient(mongo_uri)
    db = client.get_database("omni_english_db")
    await init_beanie(database=db, document_models=[WritingPromptModel])

    PROMPTS = [
    # =========================================================================
    # TASK 1: ACADEMIC TASK 1 (CHARTS, DIAGRAMS, MAPS, TABLES) - task_type="WITH_GRAPH"
    # =========================================================================
    WritingPromptModel(
        title="IELTS Task 1: Rainwater Collection Process for Drinking Water",
        task_type="WITH_GRAPH",
        task_description="The diagram shows how rainwater is collected, filtered, treated, and distributed for use as drinking water in an Australian town. Summarize the information by selecting and reporting the main features, and make comparisons where relevant.",
        reference_image_url="https://media.dolenglish.vn/PUBLIC/MEDIA/SAMPLE_WT1_2025Q1_17_169.png",
        ref_id="IELTS-T1-DOL-01",
        time_limit_minutes=20,
        word_count_target=200,
        suggested_structure=[
            {
                "section": "Introduction",
                "guide": "Paraphrase the prompt statement introducing the rainwater collection and purification system."
            },
            {
                "section": "Overview",
                "guide": "State the overall process from initial rooftop collection to domestic consumption, highlighting key filtration and chemical treatment phases."
            },
            {
                "section": "Body Paragraph 1",
                "guide": "Describe the initial collection stage: runoff from house roofs into gutters, piping into storage tanks, and primary sediment filtering."
            },
            {
                "section": "Body Paragraph 2",
                "guide": "Describe the secondary treatment stage: water treatment plant processing, chemical addition (chlorine), storage in clean tanks, and piped distribution."
            }
        ],
        advanced_vocabulary=["Collection mechanism", "Purification process", "Runoff", "Sediment filtration", "Piped distribution"]
    ),
    WritingPromptModel(
        title="IELTS Task 1: Industrial Recycling Process of Aluminium Cans",
        task_type="WITH_GRAPH",
        task_description="The diagram below shows the recycling process of aluminium beverage cans. Summarize the information by describing the main features, and make comparisons where relevant.",
        reference_image_url="https://media.dolenglish.vn/PUBLIC/MEDIA/SAMPLE_WT1_2025Q1_19_169.png",
        ref_id="IELTS-T1-DOL-02",
        time_limit_minutes=20,
        word_count_target=200,
        suggested_structure=[
            {
                "section": "Introduction",
                "guide": "Rephrase the prompt introducing the multi-stage recycling loop of aluminium drink cans."
            },
            {
                "section": "Overview",
                "guide": "Highlight that the process is a closed-loop system taking approximately 6 weeks from consumer disposal to new product shelf release."
            },
            {
                "section": "Body Paragraph 1",
                "guide": "Detail the collection and preparation stages: waste bin disposal, sorting, shredding, and paint coating removal."
            },
            {
                "section": "Body Paragraph 2",
                "guide": "Detail the manufacturing stages: thermal melting into ingots, rolling into thin sheets, and container fabrication."
            }
        ],
        advanced_vocabulary=["Closed-loop recycling", "Shredding into flakes", "Thermal melting", "Ingot fabrication", "Post-consumer waste"]
    ),
    WritingPromptModel(
        title="IELTS Task 1: Museum Floor Plan Redevelopment (1990 vs 2010)",
        task_type="WITH_GRAPH",
        task_description="The two maps illustrate the architectural layout and visitor facilities of a local museum in 1990 and following its redevelopment in 2010. Summarize the principal structural changes and additions.",
        reference_image_url="https://media.dolenglish.vn/PUBLIC/MEDIA/SAMPLE_R_WT1_2026_17.jpg",
        ref_id="IELTS-T1-DOL-03",
        time_limit_minutes=20,
        word_count_target=200,
        suggested_structure=[
            {
                "section": "Introduction",
                "guide": "State the museum location and the 20-year timeframe compared between 1990 and 2010."
            },
            {
                "section": "Overview",
                "guide": "Summarize major changes: expansion of exhibit space, introduction of an interactive media room, and commercial amenities."
            },
            {
                "section": "Body Paragraph 1",
                "guide": "Describe western and central layout changes: relocation of main entrance and conversion of storage rooms into gift shops."
            },
            {
                "section": "Body Paragraph 2",
                "guide": "Describe eastern section developments: addition of a cafe, elevator access, and modernized exhibition halls."
            }
        ],
        advanced_vocabulary=["Structural redevelopment", "Floor plan layout", "Converted into", "Amenities expansion", "Accessibility infrastructure"]
    ),
    WritingPromptModel(
        title="IELTS Task 1: Students' Favourite School Subjects (School A vs School B)",
        task_type="WITH_GRAPH",
        task_description="The chart below shows information about the favourite subjects of 60 students from two secondary schools, School A and School B. Summarize the information by selecting and reporting the main features, and make comparisons where relevant.",
        reference_image_url="https://media.dolenglish.vn/PUBLIC/MEDIA/SAMPLE_R_WT1_2026_07_Social.jpg",
        ref_id="IELTS-T1-DOL-04",
        time_limit_minutes=20,
        word_count_target=200,
        suggested_structure=[
            {
                "section": "Introduction",
                "guide": "Paraphrase the prompt specifying subject preferences among 60 students in two distinct schools."
            },
            {
                "section": "Overview",
                "guide": "Identify the most popular subjects overall (STEM vs Arts) and contrast the dominant choices between the two schools."
            },
            {
                "section": "Body Paragraph 1",
                "guide": "Analyze Science and Mathematics student preferences in School A compared to School B."
            },
            {
                "section": "Body Paragraph 2",
                "guide": "Compare preferences for Humanities, Art, and Physical Education across both cohorts."
            }
        ],
        advanced_vocabulary=["Preference breakdown", "Pronounced contrast", "Dominant preference", "Student cohort", "Disparity"]
    ),
    WritingPromptModel(
        title="IELTS Task 1: Retail Fuel Prices in Two US States (2005–2009)",
        task_type="WITH_GRAPH",
        task_description="The charts below show the average monthly price of retail fuel in two states of the USA (State X and State Y) between 2005 and 2009. Summarize the information by selecting and reporting the main features, and make comparisons where relevant.",
        reference_image_url="https://media.dolenglish.vn/PUBLIC/MEDIA/SAMPLE_R_WT1_2026_16.jpg",
        ref_id="IELTS-T1-DOL-05",
        time_limit_minutes=20,
        word_count_target=200,
        suggested_structure=[
            {
                "section": "Introduction",
                "guide": "Introduce the parameters: fuel price movements in two US states over a 4-year period."
            },
            {
                "section": "Overview",
                "guide": "Highlight common price volatility, a sharp price peak around mid-2008, followed by a dramatic slump."
            },
            {
                "section": "Body Paragraph 1",
                "guide": "Detail price fluctuations in State X from 2005 to the 2008 surge."
            },
            {
                "section": "Body Paragraph 2",
                "guide": "Detail price fluctuations in State Y and compare price differentials between both states."
            }
        ],
        advanced_vocabulary=["Price volatility", "Peak level", "Dramatic slump", "Fluctuated erratically", "Price differential"]
    ),

    # =========================================================================
    # TASK 2: ACADEMIC ESSAY TASK 2 (OPINION, DISCUSSION, CAUSES, SOLUTIONS) - task_type="WITHOUT_GRAPH"
    # =========================================================================
    WritingPromptModel(
        title="IELTS Task 2: Artificial Intelligence in Healthcare & Medical Diagnostics",
        task_type="WITHOUT_GRAPH",
        task_description="Some medical experts argue that artificial intelligence algorithms will eventually replace human doctors in diagnosing diseases and recommending treatments. To what extent do you agree or disagree with this view?",
        reference_image_url=None,
        ref_id="IELTS-T2-AI-01",
        time_limit_minutes=40,
        word_count_target=300,
        suggested_structure=[
            {
                "section": "Introduction",
                "guide": "Paraphrase the prompt statement and clearly state your thesis (e.g. AI will enhance diagnostics but cannot replace human doctors)."
            },
            {
                "section": "Body Paragraph 1",
                "guide": "Examine the benefits of AI diagnostics: immense data processing capacity, zero fatigue, and high accuracy in image recognition."
            },
            {
                "section": "Body Paragraph 2",
                "guide": "Discuss human doctor necessity: empathetic communication, nuanced clinical judgment, and moral/legal accountability."
            },
            {
                "section": "Conclusion",
                "guide": "Reiterate that AI will function as a powerful assistive tool rather than a complete substitute for physicians."
            }
        ],
        advanced_vocabulary=["Diagnostic accuracy", "Algorithmic precision", "Human touch", "Clinical judgement", "Ethical implications"]
    ),
    WritingPromptModel(
        title="IELTS Task 2: Government Budget: Space Exploration vs Domestic Poverty",
        task_type="WITHOUT_GRAPH",
        task_description="Governments in several nations allocate billions of dollars annually to space exploration programs. Some believe this funding is crucial for scientific progress, while others argue it should be redirected to solve urgent domestic issues such as healthcare and poverty. Discuss both views and give your opinion.",
        reference_image_url=None,
        ref_id="IELTS-T2-SPACE-02",
        time_limit_minutes=40,
        word_count_target=300,
        suggested_structure=[
            {
                "section": "Introduction",
                "guide": "Introduce the national budget priority debate and state your opinion clearly."
            },
            {
                "section": "Body Paragraph 1",
                "guide": "Discuss reasons supporting space investment: satellite technologies, climate tracking, and scientific breakthroughs."
            },
            {
                "section": "Body Paragraph 2",
                "guide": "Discuss reasons for prioritizing social welfare: immediate poverty relief, public healthcare funding, and education."
            },
            {
                "section": "Conclusion",
                "guide": "Summarize both perspectives and advocate for a balanced fiscal strategy."
            }
        ],
        advanced_vocabulary=["Fiscal allocation", "Scientific endeavor", "Socio-economic crisis", "Alleviation of hardship", "Technological spinoffs"]
    ),
    WritingPromptModel(
        title="IELTS Task 2: Rapid Urban Expansion, Traffic Gridlock & Air Pollution",
        task_type="WITHOUT_GRAPH",
        task_description="In many mega-cities today, rapid population growth has caused severe traffic congestion and deteriorating air quality. What are the primary causes of these urban problems, and what practical measures can be implemented by municipal authorities?",
        reference_image_url=None,
        ref_id="IELTS-T2-URBAN-03",
        time_limit_minutes=40,
        word_count_target=300,
        suggested_structure=[
            {
                "section": "Introduction",
                "guide": "State the background of urban migration and outline the intent to present causes and solutions."
            },
            {
                "section": "Body Paragraph 1",
                "guide": "Analyze main causes: outdated public transit networks, over-reliance on private vehicles, and unplanned suburban sprawl."
            },
            {
                "section": "Body Paragraph 2",
                "guide": "Propose practical solutions: expansion of high-speed metro lines, congestion pricing zones, and green vehicle subsidies."
            },
            {
                "section": "Conclusion",
                "guide": "Summarize key points and stress that sustainable urban planning is essential for city livability."
            }
        ],
        advanced_vocabulary=["Metropolitan congestion", "Gridlock", "Deteriorating air quality", "Eco-friendly transit", "Infrastructure overhaul"]
    ),
    WritingPromptModel(
        title="IELTS Task 2: Fast Fashion Boom and Consumer Culture",
        task_type="WITHOUT_GRAPH",
        task_description="Consumers today purchase significantly more cheap apparel than in previous decades due to the popularity of fast fashion brands. Why has fast fashion become so widespread, and is this a positive or negative development for society?",
        reference_image_url=None,
        ref_id="IELTS-T2-FASHION-04",
        time_limit_minutes=40,
        word_count_target=300,
        suggested_structure=[
            {
                "section": "Introduction",
                "guide": "Paraphrase the fast fashion trend and state your answers to both parts of the prompt."
            },
            {
                "section": "Body Paragraph 1",
                "guide": "Explain drivers of popularity: low pricing, rapid social media trend cycles, and disposable consumer behavior."
            },
            {
                "section": "Body Paragraph 2",
                "guide": "Evaluate impacts: argue it is a net negative development due to immense textile landfill waste, water pollution, and poor factory conditions."
            },
            {
                "section": "Conclusion",
                "guide": "Conclude that despite short-term consumer convenience, the environmental and labor toll makes fast fashion harmful."
            }
        ],
        advanced_vocabulary=["Consumerism", "Disposable apparel", "Environmental degradation", "Textile waste", "Exploitative labor"]
    ),
    WritingPromptModel(
        title="IELTS Task 2: Online Tertiary Education and Remote University Degrees",
        task_type="WITHOUT_GRAPH",
        task_description="An increasing number of top universities now offer complete degree programs online, enabling students to study from anywhere in the world. Do the advantages of remote tertiary education outweigh its disadvantages?",
        reference_image_url=None,
        ref_id="IELTS-T2-EDU-05",
        time_limit_minutes=40,
        word_count_target=300,
        suggested_structure=[
            {
                "section": "Introduction",
                "guide": "Introduce the rise of online degrees and state thesis that advantages outweigh disadvantages."
            },
            {
                "section": "Body Paragraph 1",
                "guide": "Acknowledge disadvantages: limited face-to-face networking, lack of campus life, and high self-discipline demands."
            },
            {
                "section": "Body Paragraph 2",
                "guide": "Elaborate on major advantages: democratization of top-tier education, elimination of housing/relocation costs, and schedule flexibility."
            },
            {
                "section": "Conclusion",
                "guide": "Reiterate that global accessibility and cost reduction make online degrees a highly beneficial evolution."
            }
        ],
        advanced_vocabulary=["Democratization of education", "Geographical flexibility", "Distance learning", "Tertiary institution", "Self-directed learning"]
    )
]

    # Delete existing prompts to refresh with clean IELTS Task 1 & Task 2 prompts
    deleted = await WritingPromptModel.find_all().delete()
    logger.info(f"Deleted {deleted.deleted_count} old writing prompts.")

    for p in PROMPTS:
        await p.insert()
    logger.info(f"Successfully seeded {len(PROMPTS)} authentic IELTS Writing prompts (5 Task 1, 5 Task 2).")

if __name__ == "__main__":
    asyncio.run(seed_writing())
