# FINAL REQUIREMENT UPDATE
# MODIFY EXISTING AI WEBSITE SALES AUTOMATION AGENT — DO NOT REBUILD

You are working on the EXISTING AI Website Sales Automation Agent repository.

IMPORTANT:
This is NOT a new project.

DO NOT rebuild the application from scratch.
DO NOT replace the current architecture unnecessarily.
DO NOT remove working Phase 1–8 functionality.
DO NOT create duplicate services/routes/models when an existing implementation can be updated.
DO NOT change the existing UI/design system unless required for these features.

First inspect the COMPLETE repository and understand the current implementation.

The existing project already contains the Phase 1–8 implementation, tests, database models, authentication, AI providers, lead discovery, website analysis, PRD system, outreach, conversations and admin UI.

The task is to RECONCILE AND UPDATE the existing implementation according to the requirements below.

============================================================
1. FIRST: COMPLETE REPOSITORY AUDIT
============================================================

Before modifying code:

Inspect:

- app/
- app/models/
- app/routes/
- app/services/
- app/integrations/
- app/ai/
- app/templates/
- app/static/
- tests/
- Docs/
- database/migrations if present
- configuration files
- requirements.txt
- .env.example
- existing automation/worker code
- existing discovery code
- existing PRD code
- existing website analysis code
- existing outreach code
- existing WhatsApp code
- existing conversation code

Identify:

1. Existing lead discovery flow
2. Existing lead creation flow
3. Existing lead scoring
4. Existing website analysis
5. Existing PRD generation
6. Existing demo generation
7. Existing GitHub integration
8. Existing outreach implementation
9. Existing WhatsApp implementation
10. Existing TEST_MODE logic
11. Existing automation/worker logic
12. Existing admin navigation
13. Existing lead deletion support
14. Existing file export support
15. Existing conversation UI
16. Existing customer/business data fields

Create an internal dependency map before editing.

Then modify ONLY what is necessary.

============================================================
2. REMOVE WRONG RESPONSIBILITIES FROM THE AGENT
============================================================

The current implementation contains functionality related to:

- automatic GitHub deployment
- demo publishing
- simulated demo URLs
- TEST_MODE simulation
- fake/static demo routing

These are NOT required for the final agent workflow.

The AGENT must NOT:

- create GitHub repositories
- deploy to GitHub
- publish GitHub Pages
- generate fake GitHub URLs
- pretend that a demo is deployed
- automatically deploy websites

GitHub deployment is an ADMIN responsibility.

The agent only prepares:

- business research
- website analysis
- sales opportunity
- personalized PRD
- complete lead information
- outreach message
- WhatsApp conversation handling

If existing GitHub/demo code is not used anywhere else, remove it cleanly.

Before deleting code, verify all references and dependencies.

Do not leave broken imports/routes/templates.

============================================================
3. REMOVE TEST_MODE FROM THE FINAL OPERATIONAL WORKFLOW
============================================================

The final application must operate using REAL integrations.

Do not use fake customer replies.
Do not use fake WhatsApp sends.
Do not use simulated API success.
Do not generate fake URLs.
Do not fabricate business information.

The final production workflow must be real.

If an API is not configured:

show:

NOT CONFIGURED

or

BLOCKED

or

FAILED

with the real reason.

Never show:

SUCCESS

when the real external operation did not happen.

The application may retain unit-test mocks inside tests, but TEST_MODE must NOT control the real production business workflow.

============================================================
4. AUTOMATIC BUSINESS DISCOVERY
============================================================

Add/repair a real Automation system.

Admin navigation must contain:

AUTOMATION

with a dedicated automation control page.

Example:

/automation

The Automation page must show:

- Automation status
- ON/OFF toggle
- Daily lead limit
- Current leads discovered today
- Remaining daily capacity
- Discovery category
- Discovery location
- Last run
- Next run/status
- Errors
- API configuration status

============================================================
5. ONE-CLICK AUTOMATION
============================================================

When ADMIN turns:

AUTOMATION = ON

the system must automatically discover a maximum of:

20 NEW qualified leads per day.

Default:

daily_limit = 20

Do not continuously discover unlimited leads.

Example:

20/20 leads discovered today
→ STOP discovery.

The daily counter must reset according to the configured application timezone.

Do not exceed the configured daily limit.

If duplicates are found:

do NOT count duplicates as new leads.

The system should continue discovery until:

20 NEW valid/qualified leads

are collected,

or the available search results are exhausted,
or an API/error condition prevents continuation.

============================================================
6. DISCOVERY SOURCES
============================================================

Primary discovery:

Google Places API (New)

Use the existing Google Places implementation if it already exists.

Normalize every result.

Collect all genuinely available data.

Do NOT fabricate missing data.

============================================================
7. LEAD DATA REQUIREMENTS
============================================================

Every discovered lead should attempt to collect:

BUSINESS INFORMATION

- business name
- category
- description
- address
- city
- state
- country
- phone
- email
- website
- Google Place ID
- Google rating
- review count
- business hours

SOCIAL INFORMATION

- Instagram
- Facebook
- other publicly available social links when legitimately obtainable

CONTACT INFORMATION

- owner name
- contact person
- phone
- email

SOURCE INFORMATION

- source
- source ID
- discovery query
- discovery location
- discovered timestamp

IMPORTANT:

Google Places does NOT guarantee owner name, email, Instagram or Facebook.

Never invent these fields.

If unavailable:

"Not Available"

or NULL according to the existing schema.

Do not display fake contact information.

============================================================
8. SOCIAL MEDIA ENRICHMENT
============================================================

If the existing architecture supports authorized/public social enrichment, use it.

Otherwise do not pretend that Google Places provides Instagram/owner information.

Use only legitimate accessible data sources and existing integrations.

If social information cannot be verified:

mark it unavailable.

Do not scrape protected/private accounts.

Do not bypass platform restrictions.

============================================================
9. SERVER-SIDE DEDUPLICATION
============================================================

Preserve the existing duplicate detection.

Deduplicate using the strongest available signals:

1. Google Place ID
2. normalized phone
3. normalized website/domain
4. email
5. business name + address similarity

Duplicates must not create separate leads.

============================================================
10. AUTOMATIC WEBSITE ANALYSIS
============================================================

Immediately after a valid lead is created:

trigger website analysis automatically.

If the business HAS a website:

perform a REAL website audit.

Analyze only measurable signals.

Include where applicable:

- HTTP availability
- HTTPS
- mobile responsiveness indicators
- viewport
- page structure
- title
- meta description
- headings
- SEO signals
- CTA presence
- contact visibility
- booking/contact functionality
- social links
- navigation
- performance indicators
- design/UX indicators
- conversion opportunities
- missing important sections
- obvious technical issues

Do not fabricate scores.

If something cannot be measured:

return:

NOT_MEASURABLE

instead of inventing a score.

If the website is unreachable:

WEBSITE_UNREACHABLE

with the real reason.

============================================================
11. LEADS WITHOUT WEBSITE
============================================================

If a business has no website:

do NOT run fake website metrics.

Instead create an opportunity analysis:

website_status = NO_WEBSITE

and explain:

- no official website detected
- potential digital presence gap
- recommended website structure
- conversion opportunities
- mobile-first requirements
- contact/booking CTA
- SEO foundation
- social integration
- business-specific sections

This information must flow into the PRD.

============================================================
12. AUTOMATIC PERSONALIZED PRD
============================================================

THIS IS CRITICAL.

Every lead must automatically receive its OWN personalized PRD.

Do NOT create one global:

PRD.md

for all businesses.

Each lead must have its own PRD record/file.

Example:

LEAD-000001
    PRD
    ↓
    personalized to Business A

LEAD-000002
    PRD
    ↓
    personalized to Business B

The PRD must contain actual lead-specific information.

Include:

1. Business overview
2. Business name
3. Category
4. Location
5. Existing website status
6. Existing website URL
7. Website audit findings
8. Website weaknesses
9. Sales opportunities
10. Recommended website improvements
11. Target audience assumptions based only on available data
12. Design direction
13. Brand direction
14. Recommended sections
15. Homepage structure
16. CTA strategy
17. Contact/booking strategy
18. Mobile requirements
19. SEO requirements
20. Social media integration
21. Trust/reviews section
22. Business-specific content recommendations
23. Conversion strategy
24. Technical requirements
25. Recommended website features
26. Missing features
27. Implementation notes

If an item is unknown:

say:

"Not available from current verified data."

Never fabricate.

============================================================
13. PRD MUST BE GENERATED AUTOMATICALLY
============================================================

The admin must NOT need to manually click:

Website Analysis

and then:

PRD Generator

for every discovered lead.

Required:

Lead discovered
    ↓
Lead saved
    ↓
Analysis automatically triggered
    ↓
PRD automatically generated
    ↓
PRD status = READY

The existing:

/analysis

and

/prds

pages should remain available for:

- review
- editing
- regeneration
- version history
- manual processing

But they must NOT be required for the initial automatic pipeline.

============================================================
14. PRD DOWNLOAD
============================================================

For every lead, provide:

DOWNLOAD PRD

The download must return ONLY that specific lead's PRD.

Example:

Download PRD
→ LEAD-000001 website PRD

It must never download another lead's PRD.

============================================================
15. COMPLETE LEAD TXT EXPORT
============================================================

Add:

DOWNLOAD FULL LEAD TXT

This must generate one TXT file containing ALL available information for that specific lead.

Example:

LEAD-000001_FULL_DETAILS.txt

Include:

--------------------------------
BUSINESS INFORMATION
--------------------------------

Business Name:
Category:
Description:
Address:
City:
State:
Country:
Phone:
Email:
Website:

--------------------------------
OWNER / CONTACT
--------------------------------

Owner Name:
Contact Person:
Phone:
Email:

--------------------------------
SOCIAL MEDIA
--------------------------------

Instagram:
Facebook:
Other Social:

--------------------------------
GOOGLE / DISCOVERY
--------------------------------

Google Place ID:
Rating:
Review Count:
Business Hours:
Source:
Discovery Query:
Discovery Location:
Discovered At:

--------------------------------
LEAD SCORING
--------------------------------

Lead Score:
Lead Temperature:
Lead Status:

--------------------------------
WEBSITE ANALYSIS
--------------------------------

Website Status:
HTTPS:
Mobile:
SEO:
CTA:
Contact:
Booking:
Design:
Opportunity Score:

Then include the detailed analysis findings.

--------------------------------
PRD STATUS
--------------------------------

PRD Status:
PRD Version:
PRD Created At:

--------------------------------
OUTREACH
--------------------------------

WhatsApp status:
Last message:
Last response:
Conversation status:

--------------------------------
SYSTEM METADATA
--------------------------------

Lead ID:
Created:
Updated:

Only include real available data.

Do not fabricate missing information.

============================================================
16. LEAD DETAIL PAGE
============================================================

The Lead Details page must clearly show:

Business Profile

Contact Details

Owner Details

Website

Social Media

Google Information

Lead Score

Lead Temperature

Lead Status

Website Analysis

PRD

Outreach

Conversation

Activity

Downloads

Actions

Actions should include:

- Generate/Regenerate Analysis
- Generate/Regenerate PRD
- Download PRD
- Download Full TXT
- Add Demo URL
- Start Outreach
- Open WhatsApp Conversation
- Delete Lead

============================================================
17. DELETE LEAD
============================================================

Add a real:

DELETE LEAD

function.

It must:

- require admin authorization
- require confirmation
- delete the lead safely
- handle related records correctly
- not leave orphaned records
- not delete unrelated leads

Use proper foreign-key/cascade behavior where appropriate.

Never allow deleting another lead through manipulated IDs.

============================================================
18. ADMIN ADDS DEMO URL MANUALLY
============================================================

The agent does NOT build or deploy the demo.

Admin builds the website separately.

Admin deploys it manually to GitHub Pages.

Then admin opens the lead and enters:

DEMO URL

Example:

https://example.github.io/business-demo/

The system stores this URL against ONLY that lead.

Validate the URL.

Do not generate fake URLs.

============================================================
19. OUTREACH WORKFLOW
============================================================

After the admin provides a real demo URL:

the lead becomes eligible for outreach.

The agent should have access to:

- business information
- verified website analysis
- personalized PRD
- demo URL
- pricing/knowledge if configured
- conversation history

The outreach message must be personalized to the specific business.

Do NOT send generic spam-like messages.

============================================================
20. WHATSAPP REAL API
============================================================

Use the official WhatsApp Business Cloud API.

The WhatsApp API configuration page must support the credentials required by the existing integration, such as:

- Phone Number ID
- Access Token
- Business/WABA information where required
- webhook verification token if needed

Credentials must be encrypted using the existing credential encryption system.

The system must provide:

SAVE

TEST CONNECTION

REAL SEND

connection status

masked credentials

Do not expose access tokens.

============================================================
21. WHATSAPP OUTREACH TRIGGER
============================================================

The required workflow:

Lead discovered
    ↓
Analysis
    ↓
Personalized PRD
    ↓
STOP

No outreach yet.

Admin manually creates/deploys website demo.

Admin enters:

DEMO URL

Then:

START OUTREACH

or the configured automation rule may initiate the first real WhatsApp message if explicitly enabled.

Do not send WhatsApp messages before a valid demo URL exists.

============================================================
22. WHATSAPP MESSAGE
============================================================

The agent must generate the message using actual lead information.

Example conceptual structure:

Hello [Business Name],

I checked your current online presence and noticed [specific verified opportunity].

I prepared a website concept specifically for [Business Name].

You can preview it here:

[REAL DEMO URL]

If you'd like, I can explain what can be improved and how we can build it.

Do NOT copy this exact message for every business.

The AI should personalize it using verified lead data.

============================================================
23. CUSTOMER REPLIES
============================================================

When a customer replies through WhatsApp:

receive the real webhook/event.

Store:

- external message ID
- timestamp
- lead ID
- conversation ID
- sender
- message
- channel
- detected intent
- confidence
- sales stage

The AI should respond using:

Lead details
+
Current conversation
+
Approved knowledge
+
Approved pricing
+
PRD
+
Website analysis
+
Demo URL

Strict lead isolation is mandatory.

============================================================
24. ADMIN MUST SEE WHAT AGENT REPLIED
============================================================

In:

Conversations

show:

Customer message
Agent reply
Timestamp
Intent
Sales stage
Channel
Delivery status

Example:

CUSTOMER
"How much will this website cost?"

AGENT
actual AI-generated response

ADMIN must be able to see the complete conversation.

============================================================
25. HUMAN TAKEOVER
============================================================

Keep:

TAKE OVER

and

RETURN TO AI

functionality.

When ADMIN takes over:

AI must stop replying automatically for that conversation.

When admin returns control:

AI can resume according to the configured rules.

============================================================
26. MANUAL AUTOMATION
============================================================

Add a manual automation control.

Admin should be able to choose:

AUTOMATION OFF

AUTOMATION ON

and manually trigger:

RUN DISCOVERY NOW

The manual run must still respect:

daily_limit = 20

unless an explicit admin override feature already exists and is intentionally configured.

Also provide:

PAUSE

RESUME

============================================================
27. AUTOMATION DASHBOARD
============================================================

Create/update:

/automation

Show:

--------------------------------
AUTOMATION
--------------------------------

Status:
ON/OFF

Mode:
REAL

Daily Limit:
20

Discovered Today:
X/20

Remaining:
20-X

Last Run:
timestamp

Last Result:
success/partial/failed

Discovery Category:
...

Location:
...

--------------------------------
PIPELINE
--------------------------------

Discovered
Analysis
PRD
Waiting for Demo
Outreach
Conversation
Hot Leads

--------------------------------
ERRORS
--------------------------------

Show real API/system errors.

============================================================
28. ADMIN NAVIGATION
============================================================

Update navigation to include:

Dashboard
Leads
Automation
Website Analysis
PRDs
Conversations
Outreach
Follow-Ups
Sales
Analytics
Integrations
AI Providers
Settings

Do not create duplicate navigation items.

Use the existing design system.

============================================================
29. PROVIDER / AI ROUTER
============================================================

Preserve the existing multi-provider AI architecture.

The AI router must remain provider-agnostic.

Use configured providers such as:

OpenRouter
Gemini
Grok/xAI
other existing configured providers

Do not hardcode one provider.

If the primary provider fails:

use the existing fallback system.

Never fabricate an AI response when all configured providers fail.

============================================================
30. PRICING
============================================================

The AI must NEVER invent pricing.

If pricing is discussed:

retrieve pricing from the existing admin-controlled pricing system.

Use the correct active pricing version.

Never calculate arbitrary prices in the prompt.

============================================================
31. STRICT LEAD ISOLATION
============================================================

This is mandatory.

For every operation:

lead_id must be explicitly resolved.

AI context must contain ONLY:

current lead
current conversation
approved global knowledge
approved pricing

Never mix:

Lead A
with
Lead B.

Test cross-lead isolation.

============================================================
32. ERROR HANDLING
============================================================

Every automated operation must have real states.

Examples:

PENDING
RUNNING
READY
FAILED
BLOCKED
NOT_CONFIGURED

Never:

fake success
fake API response
fake PRD data
fake contact data
fake website audit
fake demo URL
fake WhatsApp delivery

============================================================
33. CLEANUP OF UNUSED CODE
============================================================

After implementation:

identify obsolete functionality created by previous phases that is no longer required.

Examples may include:

- simulated GitHub publishing
- fake demo URLs
- TEST_MODE production branches
- duplicate PRD generation routes
- duplicate automation implementations
- obsolete mock production services

ONLY remove code after verifying it is unused.

Do not delete working shared components.

No dead imports.
No broken references.
No orphaned templates.
No duplicate services.

============================================================
34. DATABASE
============================================================

Update the existing database schema only where necessary.

Do NOT create duplicate lead tables.

Do NOT destroy existing data.

Preserve existing relationships.

Add fields/tables only if genuinely required for:

- automation
- discovery metadata
- owner/contact enrichment
- PRD per lead
- demo URL
- outreach state
- WhatsApp conversation
- TXT export metadata

Use migrations if the project already has migration support.

============================================================
35. TESTS
============================================================

Do not remove existing tests.

Run the complete existing test suite.

Then add/update tests for:

1. Automation ON
2. Maximum 20 new leads/day
3. Duplicate leads do not count toward new-lead limit
4. Automatic analysis after lead creation
5. Automatic PRD generation
6. Individual PRD per lead
7. PRD download isolation
8. Full TXT export
9. Missing owner/contact handling
10. Missing social data handling
11. No fake data
12. Website analysis
13. No-website handling
14. Admin demo URL entry
15. No outreach before demo URL
16. WhatsApp configuration
17. Real WhatsApp adapter
18. Conversation storage
19. AI response visibility to admin
20. Human takeover
21. Lead deletion
22. Cross-lead isolation
23. Provider fallback

Run:

venv\Scripts\pytest

Do not claim success unless the tests actually pass.

============================================================
36. REAL END-TO-END VERIFICATION
============================================================

Verify this exact workflow:

ADMIN
 ↓
Automation ON
 ↓
Google Places
 ↓
20 maximum NEW qualified leads/day
 ↓
Lead normalization
 ↓
Deduplication
 ↓
Lead score
 ↓
Business/contact/social enrichment
 ↓
Website analysis
 ↓
Personalized PRD
 ↓
PRD READY
 ↓
WAITING FOR ADMIN
 ↓
ADMIN builds website separately
 ↓
ADMIN deploys website manually
 ↓
ADMIN enters REAL demo URL
 ↓
START OUTREACH
 ↓
REAL WhatsApp API
 ↓
Customer replies
 ↓
Webhook
 ↓
Conversation stored
 ↓
AI generates response
 ↓
Customer receives response
 ↓
ADMIN sees customer + AI messages
 ↓
Purchase intent
 ↓
HOT LEAD
 ↓
ADMIN takeover/closing

============================================================
37. VERY IMPORTANT FINAL RULE
============================================================

Do not interpret this request as permission to redesign the entire project.

The existing application is the source of truth.

MODIFY.

REPAIR.

CONNECT.

REMOVE ONLY OBSOLETE CODE.

KEEP ALL WORKING FEATURES.

Do not create duplicate implementations.

Do not silently change database semantics.

Do not fabricate unavailable data.

Do not claim a feature is complete merely because code exists.

Actually test the workflow.

============================================================
FINAL REPORT REQUIRED
============================================================

After implementation, provide:

1. Files modified
2. Files created
3. Files deleted
4. Why each deleted file/code was obsolete
5. Existing features preserved
6. New automation workflow
7. Automatic discovery behavior
8. Daily 20-lead enforcement
9. Lead data enrichment behavior
10. Website analysis behavior
11. Automatic PRD behavior
12. PRD download behavior
13. Full TXT export behavior
14. Demo URL admin workflow
15. WhatsApp configuration
16. WhatsApp send workflow
17. Conversation workflow
18. Admin visibility
19. Human takeover
20. Lead deletion
21. Database changes
22. API requirements
23. Exact environment variables
24. Test results
25. Any remaining blockers

MOST IMPORTANT:

Do not say "implemented" until you have actually tested:

Lead → Analysis → PRD

and:

Demo URL → WhatsApp → Customer Reply → AI Reply → Admin Conversation View.