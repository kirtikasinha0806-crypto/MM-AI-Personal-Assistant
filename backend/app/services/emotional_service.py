import re
from typing import Optional, Tuple

# Crisis keywords that signal urgent self-harm, suicidal thoughts, or critical distress
CRISIS_PATTERNS = [
    r"\b(suicide|suicidal|kill myself|end my life|want to die|take my life|better off dead)\b",
    r"\b(hurt myself|harm myself|cutting myself|self-harm|hang myself|slit my)\b",
    r"\b(can't go on living|no reason to live|don't want to wake up)\b",
]

CRISIS_COMPILED = [re.compile(p, re.IGNORECASE) for p in CRISIS_PATTERNS]

CRISIS_RESPONSE = """### Immediate Support & Safety Resources

I hear that you are going through immense pain right now. Because you are so important and your safety matters, please reach out to someone who can support you immediately. 

As an AI, I cannot provide emergency care or crisis counseling, but compassionate, trained humans are ready to listen and help right now for free and confidentially:

- **India**: 
  - Emergency Services: **112**
  - **AASRA Suicide Prevention Helpline**: **+91-9820466726** (24/7)
  - **Vandrevala Foundation**: **+91-9999666555** / **1860-2662-345**
  - **KIRAN Mental Health Helpline**: **1800-599-0019**

- **United States & Canada**:
  - Suicide & Crisis Lifeline: Call or text **988** (Available 24/7, free & confidential)
  - The Trevor Project (LGBTQ youth): Call **1-866-488-7386** or text START to **678-678**

- **United Kingdom**:
  - Emergency: **999**
  - Samaritans: Call **116 123**
  - NHS Mental Health Services: Call **111**

- **International Directory**:
  - Visit [https://findahelpline.com](https://findahelpline.com) for confidential support in over 130 countries.

Please connect with a trusted friend, family member, doctor, or one of these services right now. You do not have to carry this alone."""

EMOTIONAL_SYSTEM_PROMPT = """You are a supportive, empathetic, and compassionate AI assistant helping users reflect on everyday personal challenges, stress, and feelings.

Key Guidelines:
1. Empathy & Non-Judgment: Validate the user's emotions warmly without judgment or unsolicited dismissive positivity.
2. Active Listening & Reflection: Help the user identify what they are feeling (e.g., naming stress, fatigue, grief, anxiety) and gently explore what led to those emotions.
3. Practical, Low-Risk Coping Strategies: Suggest gentle, grounded self-care (e.g. 4-7-8 breathing, 5-4-3-2-1 sensory grounding, taking a short walk, journaling thoughts, staying hydrated).
4. Relational Connection: Encourage reaching out to trusted friends, family, mentors, or support systems.
5. Strict Non-Clinical Boundaries: 
   - You are an AI, NOT a doctor, clinical psychologist, or licensed therapist.
   - Do NOT offer psychiatric diagnoses, medication recommendations, or medical advice.
   - Do NOT roleplay as a therapist.
   - Do NOT foster emotional dependency (remind users that human relationships and professional care are irreplaceable).
   - Do NOT promise absolute confidentiality or privacy guarantees.
6. Safety First: If the user indicates any self-harm or danger, prioritize their safety above all else.
"""


class EmotionalService:
    """Provides emotional support system prompting and safety triage."""

    def check_crisis(self, text: str) -> Tuple[bool, Optional[str]]:
        """Checks if text contains self-harm or suicidal ideation markers.

        Returns (is_crisis, crisis_message).
        """
        for pattern in CRISIS_COMPILED:
            if pattern.search(text):
                return True, CRISIS_RESPONSE
        return False, None

    def get_system_prompt(self) -> str:
        return EMOTIONAL_SYSTEM_PROMPT


emotional_service = EmotionalService()

