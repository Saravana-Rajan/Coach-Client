import os
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)


def generate_transition_brief(reassignment_data):
    """
    Call Gemini to generate a transition brief from real data.
    Raises on failure — caller handles the exception.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

    prompt = f"""You are an executive coaching assistant. Generate a transition brief for a coach
who is being assigned a new client. Use ONLY the data provided below — do not invent any facts.

CLIENT INFORMATION:
- Name: {reassignment_data['contact_name']}
- Title: {reassignment_data['contact_title']}
- Email: {reassignment_data['contact_email']}

ACCOUNT INFORMATION:
- Company: {reassignment_data['account_name']}
- Industry: {reassignment_data['account_industry']}
- Coaching relationship started: {reassignment_data['account_start_date']}

ASSIGNMENT CHANGE:
- Previous Coach: {reassignment_data['previous_coach']}
- New Coach (you are writing for): {reassignment_data['new_coach']}

Write a brief that includes:
1. Client & Account Summary
2. Coaching History (based on timeline)
3. Key Insights (what the new coach should know)
4. Recommended Next Steps (3-5 actionable items)

Keep it concise and actionable. Format with clear headers."""

    response = model.generate_content(prompt)
    return response.text
