import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv
load_dotenv()

from modules.Writing.ai_service import AIService, AIConfig

async def test_eval():
    AIConfig.DEFAULT_MODEL = "gemini-2.5-flash"
    title = "Some people think that university education should be free for everyone."
    desc = "To what extent do you agree or disagree with this statement?"
    essay = """In recent years, higher education has become a subject of intense debate. Many individuals argue that university education ought to be completely free for all students, regardless of their financial background. I strongly agree with this perspective because tertiary education fosters equal opportunities and boosts national economic growth.

First and foremost, making university education tuition-free ensures equal opportunities for talented students from underprivileged backgrounds. Without financial barriers, low-income students can pursue higher degrees based solely on academic merit rather than wealth. Consequently, this reduces social inequality and creates a fairer society.

Furthermore, a highly educated workforce directly contributes to economic prosperity. When more citizens graduate from universities, industries benefit from skilled workers, researchers, and innovators. For instance, countries like Germany that offer tuition-free higher education consistently maintain strong economies and high standards of living.

In conclusion, free university education provides equal social opportunities and strengthens national economy. Therefore, governments should invest in public education for the future."""

    try:
        print(f"Calling AIService.evaluate_essay with model: {AIConfig.DEFAULT_MODEL}...")
        res = await AIService.evaluate_essay(title, desc, essay)
        print("RESULT:")
        import json
        print(json.dumps(res, indent=2, ensure_ascii=False))
    except Exception as e:
        print("ERROR:", type(e), e)

if __name__ == "__main__":
    asyncio.run(test_eval())
