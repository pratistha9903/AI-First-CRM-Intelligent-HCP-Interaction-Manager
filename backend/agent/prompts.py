INTENT_DETECTION_PROMPT = """You are an intent classifier for a Healthcare Professional (HCP) CRM assistant.
Classify the user's message into exactly ONE intent.

Intents:
- log_interaction: User is logging a new visit/meeting with a doctor (mentions meeting, visit, discussed products, etc.) — NOT when they only mention a future follow-up date
- edit_interaction: User wants to change/correct/update a field in the current interaction
- search_interaction: User wants to find or show past interactions with a doctor
- summarize_interaction: User wants a summary of the current or a specific interaction
- schedule_followup: User wants to schedule or set a follow-up date/reminder (e.g. "next meeting is tomorrow", "follow up next Monday")
- confirm: User is confirming a pending save (yes, save, confirm, go ahead, correct)
- cancel: User is canceling or rejecting a pending action (no, cancel, don't save)
- undo: User wants to undo the last change
- general: Greeting or unclear message

Return ONLY valid JSON:
{{"intent": "<intent_name>", "confidence": 0.0-1.0}}"""

LOG_INTERACTION_PROMPT = """Extract HCP interaction details from the user message for a pharmaceutical field rep CRM.

Today's date: {today}
Current time: {now_time}

Extract these fields:
- doctorName: HCP name (required)
- interactionType: Meeting, Call, Email, Conference (default Meeting)
- date: YYYY-MM-DD — use {today} if today or not mentioned
- time: HH:MM 24h — use {now_time} if not mentioned
- attendees: Other attendees present
- topicsDiscussed: Key discussion points (REQUIRED — put main conversation topics here)
- products: Products/drugs discussed
- sentiment: positive, negative, or neutral
- brochure: true if materials/brochures shared
- samples: true if samples given
- materialsShared: Description of materials shared
- samplesDistributed: Description of samples distributed
- outcomes: Key outcomes or agreements
- followUpActions: Next steps or tasks mentioned
- notes: Additional notes, advice, recommendations
- followUpDate: YYYY-MM-DD if follow-up/next meeting mentioned

Return ONLY valid JSON:
{{"doctorName":"","interactionType":"Meeting","date":"","time":"","attendees":"","topicsDiscussed":"","products":"","sentiment":"","brochure":false,"samples":false,"materialsShared":"","samplesDistributed":"","outcomes":"","followUpActions":"","notes":"","followUpDate":""}}"""

EDIT_INTERACTION_PROMPT = """The user wants to edit fields in the current HCP interaction.

Current interaction:
{current_interaction}

Valid fields: doctorName, interactionType, date, time, attendees, topicsDiscussed, products, sentiment, brochure, samples, materialsShared, samplesDistributed, outcomes, followUpActions, notes, followUpDate

Return ONLY valid JSON:
{{"fields": {{"fieldName": "newValue"}}, "explanation": "brief description of changes"}}"""

SEARCH_INTERACTION_PROMPT = """Extract search parameters from the user message for finding past HCP interactions.

Return ONLY valid JSON:
{{"doctorName": "", "limit": 1, "mostRecent": true}}

doctorName: Doctor name to search for (required)
limit: Number of results (default 1)
mostRecent: true if user asks for "last" or "most recent" meeting"""

SUMMARIZE_INTERACTION_PROMPT = """Summarize this HCP interaction in less than 100 words for a pharmaceutical field representative.

Interaction data:
{interaction_data}

Write a concise, professional summary covering: who was visited, what was discussed, sentiment, materials shared, and any follow-up needs.
Return ONLY the summary text, no JSON."""

SCHEDULE_FOLLOWUP_PROMPT = """Extract follow-up scheduling details from the user message.

Today's date for reference: {today}

Return ONLY valid JSON:
{{"followUpDate": "YYYY-MM-DD", "followUpStatus": "scheduled", "reminderNote": "brief reminder text"}}

Parse relative dates like "tomorrow", "next Monday", "next meeting is tomorrow", "in two weeks", etc. relative to today.

Examples:
- "next meeting is tomorrow" -> followUpDate = tomorrow's date
- "follow up next Monday" -> followUpDate = next Monday's date
- "schedule follow-up in 2 weeks" -> followUpDate = 14 days from today"""

MISSING_INFO_PROMPT = """The user tried to log an interaction but some required information is missing.

Extracted data so far:
{extracted}

Missing required fields: {missing_fields}

Generate a friendly, professional question asking for the missing information. Be specific and concise.
Return ONLY the question text."""

CONFIRMATION_PROMPT = """Generate a confirmation message before saving this HCP interaction.

Extracted data:
{extracted}

Format: List the key fields clearly and ask "Should I save this interaction?"
Return ONLY the confirmation message text."""
