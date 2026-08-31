# FLIXORA AI SALES AUTOMATION AGENT

## Master Product Requirements Document

**Company:** Flixora
**Product:** Flixora AI Sales Automation Agent
**PRD Version:** 2.0
**Document Status:** Development Ready
**Primary UI Theme:** White + Blue
**Primary Backend:** Python + Flask
**Database:** SQLite initially, PostgreSQL-ready
**Deployment:** Render / VPS
**Demo Hosting:** GitHub Pages or equivalent static hosting

---

# 1. Product Vision

Flixora AI Sales Automation Agent is an AI-powered internal sales automation platform for Flixora.

The system will automate the repetitive part of the local-business website sales process:

```text
Lead Discovery
      ↓
Business Research
      ↓
Website / Social Analysis
      ↓
Lead Qualification
      ↓
PRD Generation
      ↓
Admin Review
      ↓
Demo Website Mapping
      ↓
Outreach
      ↓
Client Conversation
      ↓
Follow-Up
      ↓
Interest / Negotiation
      ↓
ADMIN FINAL DEAL
      ↓
Production Website Development
```

The AI is responsible for research, analysis, organization, controlled communication and follow-up.

The Admin remains responsible for important business decisions, final pricing exceptions, final deal closure and production implementation.

---

# 2. Primary Business Goal

The system should reduce the amount of manual work required for Flixora to acquire local-business website clients.

The Admin should be able to select:

```text
Location
Business Category
Daily Lead Target
```

and allow the platform to automatically perform the configured workflow.

Default target:

```text
20 qualified leads per day
```

The number must be configurable from Settings.

---

# 3. Main Product Modules

The application must contain these major modules:

```text
1. Dashboard
2. Lead Discovery
3. Lead Database
4. Business Research
5. Website Analysis
6. Social Research
7. Lead Qualification
8. PRD Generator
9. PRD Review
10. PRD Version History
11. Demo Management
12. Outreach Management
13. Client Conversations
14. Follow-Up Management
15. Sales Pipeline
16. Pricing & Discount
17. AI Provider Manager
18. Model Manager
19. LLM Fallback Router
20. Knowledge Base
21. Admin AI Chat
22. Files & Images
23. Agent Performance
24. Agent Correction
25. Automation Scheduler
26. Logs
27. Analytics
28. Settings
```

---

# 4. Tech Stack

## 4.1 Backend

```text
Python 3.12+
Flask
Gunicorn
```

Flask will manage:

* Web pages
* Admin routes
* APIs
* Authentication
* Business workflows
* Database access
* AI orchestration

---

# 5. Frontend Stack

```text
HTML5
CSS3
JavaScript
Material Design 3
```

The frontend must be responsive.

Supported target sizes:

```text
Desktop
Laptop
Tablet
Mobile
```

The design must look like a modern professional SaaS dashboard.

---

# 6. UI Design System

## Primary Theme

The entire application must use a clean **White + Blue** visual system.

### General Appearance

* White backgrounds
* Blue primary buttons
* Light blue selected states
* Blue links
* Dark navy text
* Light grey borders
* Soft shadows
* Rounded cards
* Rounded dialogs
* Clean spacing

Do not use excessive gradients.

Do not create a visually noisy interface.

---

# 7. UI Style

The interface should feel like a premium SaaS platform.

Use:

```text
Cards
Tables
Tabs
Chips
Badges
Dropdowns
Tooltips
Drawers
Dialogs
Confirmation dialogs
Toast notifications
Empty states
Loading skeletons
Progress indicators
```

Dialogs must be used for actions that should not navigate the user away from the current page.

---

# 8. Global Navigation

Desktop navigation:

```text
┌────────────────────────────────────┐
│ FLIXORA                            │
│                                    │
│ Dashboard                          │
│ Leads                              │
│ Website Analysis                   │
│ PRDs                               │
│ Demo Projects                      │
│ Outreach                           │
│ Conversations                      │
│ Follow-Ups                         │
│ Sales                             │
│ Analytics                          │
│ AI Assistant                       │
│ Knowledge Base                     │
│ Files                              │
│ LLM Providers                      │
│ Automation                         │
│ Logs                               │
│ Settings                           │
│                                    │
│ Admin Profile                      │
└────────────────────────────────────┘
```

Mobile navigation must become a drawer/bottom navigation pattern.

---

# 9. Global Top Bar

Top bar should contain:

```text
Page Title
Search
Notifications
Automation Status
Admin Profile
```

Example:

```text
Dashboard                 🔍    🔔   AI: ACTIVE   Admin
```

---

# 10. Page: Login

Route:

```text
/login
```

UI:

* Flixora logo
* Email/username
* Password
* Show/hide password
* Remember session
* Login button
* Error state

Dialog:

```text
Invalid credentials
[Close]
```

Security:

* Password hash
* Session protection
* CSRF
* Login rate limiting

---

# 11. Page: Dashboard

Route:

```text
/dashboard
```

## KPI Cards

```text
Today's Leads
Qualified Leads
PRDs Pending
Demos Ready
Messages Sent
Replies
Interested Clients
Negotiations
Deals Won
```

## Lead Funnel

```text
Leads
 ↓
Qualified
 ↓
Contacted
 ↓
Replied
 ↓
Interested
 ↓
Won
```

## Recent Activity

Example:

```text
ABC Salon
Website analysis completed

XYZ Bakery
PRD generated

PQR Barber
Client replied
```

## AI System Status

Show:

```text
LLM Status
Automation Status
Messaging Status
Lead Discovery Status
```

---

# 12. Dashboard Quick Actions

Buttons:

```text
Find Leads
Analyze Leads
Generate PRDs
Add Demo
View Conversations
Run Automation
AI Assistant
```

---

# 13. Page: Lead Discovery

Route:

```text
/leads/discover
```

Admin form:

```text
Location
Business Category
Daily Lead Target
Priority
Website Required
Minimum Rating
```

Example:

```text
Location:
Delhi

Category:
Salon

Target:
20
```

Button:

```text
Start Lead Discovery
```

---

# 14. Lead Discovery Dialog

When Admin clicks Start:

```text
Start Lead Discovery?

Location: Delhi
Category: Salon
Target: 20

[Cancel] [Start]
```

After starting:

```text
Discovering businesses...

12 / 20
```

Progress must be visible.

---

# 15. Lead Discovery Data Source

Google Maps data must be accessed through an appropriate Google Maps Platform API integration rather than depending on browser scraping.

Google Places API (New) provides Text Search and Place Details. Text Search requires a field mask and can return place information; Place Details can be used after obtaining a Place ID.

Recommended flow:

```text
Admin
 ↓
Location + Category
 ↓
Google Places Text Search
 ↓
Place IDs
 ↓
Google Place Details
 ↓
Normalize Data
 ↓
Duplicate Detection
 ↓
Lead Database
```

The application must request only the fields it actually needs through field masks to reduce unnecessary data and cost.

---

# 16. Google Places API Settings

Settings page:

```text
Settings
 → Integrations
 → Google Maps
```

Fields:

```text
API Key
Enabled
Default Country
Language
Daily Search Limit
```

Buttons:

```text
[Test Connection]
[Save]
[Disable]
```

The Google API key must never be hard-coded.

---

# 17. API Secret Storage

Admin enters API keys through the Settings UI.

Example:

```text
OpenRouter API Key
Google AI API Key
Google Maps API Key
Messaging API credentials
```

Storage flow:

```text
Admin Input
     ↓
Validation
     ↓
Encryption
     ↓
Database
```

The original secret must never be shown again.

UI display:

```text
••••••••••••A91K
```

Only the last few characters may be displayed.

---

# 18. API Runtime Retrieval

The application must retrieve secrets through a dedicated credential service.

Example architecture:

```text
Service
 ↓
CredentialManager
 ↓
Database encrypted value
 ↓
Decrypt at runtime
 ↓
API Client
```

API keys should not be sent to the frontend after initial configuration.

They should not be included in logs.

They should not be included in error messages.

---

# 19. Lead Database Page

Route:

```text
/leads
```

Table columns:

```text
Business
Category
Location
Phone
Website
Instagram
Rating
Reviews
Lead Score
Status
Demo
Last Action
```

Filters:

```text
Location
Category
Website
Lead Score
Status
Rating
Date
```

Search:

```text
Business Name
Phone
Website
```

---

# 20. Lead Detail Page

Route:

```text
/leads/<id>
```

Sections:

### Business

```text
Business Name
Category
Description
Address
City
State
```

### Contact

```text
Phone
WhatsApp
Email
```

### Social

```text
Instagram
Facebook
Other
```

### Reputation

```text
Rating
Reviews
```

### Website

```text
URL
Exists?
Status
```

### Qualification

```text
Score
Priority
Reason
```

### Activity

Full timeline.

---

# 21. Lead Data Separation Rule

Every field must remain independent.

Example:

```text
business_name
business_category
address
city
state
phone
email
website_url
instagram_url
facebook_url
rating
review_count
```

Do not store all details inside one AI-generated text blob.

---

# 22. Duplicate Detection

The system must check:

```text
Business Name
Phone Number
Address
Website URL
Google Place ID
```

Preferred identity:

```text
Google Place ID
```

Secondary matching:

```text
Phone + Address
Website
Business Name + Address
```

Possible result:

```text
Unique
Likely Duplicate
Confirmed Duplicate
```

---

# 23. Page: Website Analysis

Route:

```text
/analysis
```

Table:

```text
Business
Website
Website Exists
Analysis Status
Improvement Needed
Score
PRD
```

---

# 24. Website Analysis Workflow

```text
Lead
 ↓
Website Exists?
```

### YES

```text
Analyze Website
 ↓
Analyze UX
 ↓
Analyze Design
 ↓
Analyze Mobile
 ↓
Analyze Conversion
 ↓
Improvement Decision
```

### NO

```text
Skip Existing Website Analysis
 ↓
Generate New Website PRD
```

---

# 25. Website Improvement Decision

For an existing website:

```text
Improvement Opportunity:
YES / NO
```

Required explanation:

```text
Decision:
YES

Reason:
Current website has significant UX,
mobile and conversion improvements available.
```

If:

```text
NO
```

then:

```text
PRD Generated = NO
Demo Task = NO
```

---

# 26. Website Analysis Criteria

Analyze:

```text
Visual Design
Layout
Typography
Branding
Mobile Experience
Navigation
CTA
Contact Flow
Service Presentation
Trust Signals
Performance Signals
Basic Accessibility
Conversion Potential
```

The agent should distinguish between:

```text
Observed Fact
AI Recommendation
AI Inference
```

This reduces hallucination.

---

# 27. Page: Social Research

Route:

```text
/research/social
```

Display:

```text
Instagram
Facebook
Other public profiles
```

AI can organize publicly available business information such as:

```text
Services
Brand style
Public business description
Public contact information
Website link
Visual direction
```

The implementation must use permitted/authorized access methods.

---

# 28. Page: Lead Qualification

Route:

```text
/leads/qualification
```

Display:

```text
Score
Priority
Reason
Opportunity
Website Status
Recommended Action
```

Example:

```text
Score: 91

Priority: HIGH

Reason:
No existing website, active business,
strong review profile and available contact.
```

---

# 29. Page: PRDs

Route:

```text
/prds
```

Cards/table:

```text
Business
PRD Status
Website Status
Improvement Required
Version
Created
Updated
```

Statuses:

```text
DRAFT
UNDER REVIEW
CHANGES REQUESTED
APPROVED
REJECTED
```

---

# 30. PRD Creation Rules

## Existing Website

If:

```text
Improvement Needed = YES
```

then:

```text
Generate Improvement PRD
```

If:

```text
Improvement Needed = NO
```

then:

```text
Do not create PRD
```

## No Website

If:

```text
Website Exists = NO
```

then:

```text
Automatically generate new website PRD
```

---

# 31. PRD Detail Page

Route:

```text
/prds/<id>
```

Layout:

```text
┌─────────────────────────────────────────────┐
│ PRD Title                    [Approve]      │
│ Status: Under Review                       │
├─────────────────────────────────────────────┤
│ Business Overview                           │
│                                             │
│ Business Analysis                           │
│                                             │
│ Website Goal                                │
│                                             │
│ Target Audience                             │
│                                             │
│ Design Direction                            │
│                                             │
│ Site Structure                              │
│                                             │
│ Functional Requirements                     │
│                                             │
│ Content Requirements                        │
│                                             │
│ CTA Strategy                                │
│                                             │
│ Technical Requirements                      │
└─────────────────────────────────────────────┘
```

---

# 32. PRD Actions

Buttons:

```text
Edit
Ask AI
Compare Versions
Restore Version
Approve
Reject
Regenerate
Export
```

---

# 33. PRD AI Chat Dialog

Right-side drawer or large dialog.

Example:

```text
Admin:
Make the website more premium.

AI:
I updated the design direction,
typography and visual hierarchy.
[Review Changes]
```

Other examples:

```text
Remove pricing section.
Add WhatsApp CTA.
Make it mobile-first.
Add premium animations.
Change target audience.
```

The AI must modify the PRD, not directly modify production code.

---

# 34. PRD Version History

Each version:

```text
Version
Author
Timestamp
Change Summary
Full PRD
```

Example:

```text
v1 — AI Generated
v2 — Admin edited
v3 — AI revised
v4 — Admin approved
```

Buttons:

```text
View
Compare
Restore
```

---

# 35. Demo Management

Route:

```text
/demos
```

Admin can:

```text
Add Demo
Edit Demo
Archive Demo
Assign Lead
Open Demo
```

---

# 36. Add Demo Dialog

Fields:

```text
Lead
Business Name
Demo URL
Demo Name
Notes
```

The Lead dropdown must display business name.

Example:

```text
ABC Salon
XYZ Bakery
PQR Barber
```

---

# 37. Demo Mapping

Primary relationship:

```text
Lead ID ↔ Demo ID ↔ Demo URL
```

Do not depend only on parsing the URL.

Example:

```text
Lead ID: 102
Business: ABC Salon
Demo ID: 55
URL: https://example.github.io/abc-salon/
```

---

# 38. Demo Validation

Before saving:

```text
URL Valid?
Website Reachable?
Correct Lead?
Duplicate Demo?
```

Optional:

```text
Preview
```

---

# 39. Page: Outreach

Route:

```text
/outreach
```

Show:

```text
Lead
Demo
Channel
Message
Status
Last Sent
Reply
Follow-Up
```

Statuses:

```text
READY
APPROVAL REQUIRED
SCHEDULED
SENT
DELIVERED
REPLIED
FAILED
STOPPED
```

---

# 40. Outreach Message Generation

AI creates personalized but concise messages.

Example structure:

```text
Greeting
Business-specific line
Demo link
Simple call to action
```

The AI must not invent facts about the business.

---

# 41. Outreach Preview Dialog

Before sending:

```text
Business:
ABC Salon

Channel:
WhatsApp

Message:
Hi 👋
I created a website concept for ABC Salon...
[Demo Link]

[Edit] [Send] [Cancel]
```

---

# 42. Messaging Integrations

Architecture:

```text
MessagingService
 ├── WhatsApp adapter
 ├── Instagram adapter
 └── Email adapter
```

Each integration should be isolated.

No messaging provider code should be spread across the entire application.

The system must use official/authorized APIs and respect provider messaging rules.

---

# 43. Client Conversation Page

Route:

```text
/conversations
```

UI:

```text
┌──────────────┬───────────────────────────────┐
│ Clients      │ Conversation                 │
│              │                               │
│ ABC Salon    │ Client: Who are you?         │
│ XYZ Bakery   │ AI: I'm Flixora's...         │
│ PQR Barber   │                               │
│              │ [Type message...]            │
└──────────────┴───────────────────────────────┘
```

---

# 44. Conversation Status

```text
AI ACTIVE
ADMIN ACTIVE
PAUSED
CLOSED
```

Admin can take over at any time.

---

# 45. Human Takeover

Button:

```text
Take Over
```

Dialog:

```text
Take control of this conversation?

AI automatic replies will be paused.

[Cancel] [Take Over]
```

---

# 46. Client AI Behavior

The client-facing agent should answer common questions such as:

```text
Who are you?
What is Flixora?
How does this work?
Who created this demo?
How much does it cost?
Do you provide hosting?
Do you provide domains?
Can the website be modified?
How long does production development take?
```

Responses must come from:

```text
Company Knowledge
Pricing Rules
Service Rules
Current Conversation Context
Admin-approved information
```

---

# 47. Agent Identity

Admin configures:

```text
Agent Name
Agent Role
Company Name
Company Description
Communication Tone
Business Description
```

The agent must not fabricate a personal identity.

---

# 48. Conversation Context Isolation

Each client must have separate context.

```text
Client A conversation
≠
Client B conversation
```

Admin chat must also remain separate from client chat.

---

# 49. Page: Follow-Ups

Route:

```text
/followups
```

Columns:

```text
Lead
Last Contact
Follow-Up Number
Scheduled Date
Status
```

Example:

```text
ABC Salon
Follow-Up 1
Tomorrow
Scheduled
```

---

# 50. Follow-Up Logic

Example:

```text
Initial Message
 ↓
No Reply
 ↓
Wait configured time
 ↓
Follow-Up 1
 ↓
No Reply
 ↓
Wait
 ↓
Follow-Up 2
 ↓
STOP
```

Admin controls:

```text
Maximum follow-ups
Delay
Allowed hours
Message style
```

---

# 51. Stop Conditions

Follow-up must stop if:

```text
Client replies
Client declines
Client requests no further contact
Lead becomes invalid
Admin pauses lead
Deal starts
```

---

# 52. Page: Sales Pipeline

Route:

```text
/sales
```

Kanban columns:

```text
NEW
CONTACTED
REPLIED
INTERESTED
NEGOTIATION
WON
LOST
```

Cards:

```text
Business
Lead Score
Current Offer
Last Contact
Demo
Conversation
```

---

# 53. Pricing Page

Route:

```text
/settings/pricing
```

Admin can create:

```text
Basic
Standard
Advanced
Animated
Custom
```

Fields:

```text
Plan Name
Price
Features
Maintenance
Enabled
```

---

# 54. Discount Rules

Admin sets:

```text
Normal Price
Maximum Discount %
Minimum Allowed Price
```

Example:

```text
Price: ₹10,000
Max Discount: 20%
Minimum Price: ₹8,000
```

The AI cannot go below the configured minimum.

---

# 55. Exceptional Pricing

Client requests a lower amount:

```text
Requested Price
<
Minimum Allowed Price
```

System:

```text
STOP
 ↓
Admin Approval Required
```

---

# 56. Domain / Hosting / Maintenance

Admin can configure:

```text
Domain
Hosting
Maintenance
Renewal
Additional Services
```

The AI only quotes approved current values.

---

# 57. External Market Pricing Research

If market-price research is enabled:

```text
External Price
      ↓
Research Result
      ↓
Admin Review
      ↓
Approve
      ↓
Save as Official Flixora Price
```

External market pricing must not automatically replace official Flixora pricing.

---

# 58. Page: LLM Providers

Route:

```text
/settings/llm/providers
```

Provider cards:

```text
OpenRouter 1
OpenRouter 2
Google AI 1
Google AI 2
Custom Provider
```

Each card displays:

```text
Status
Protocol
Models
Priority
Last Used
Last Error
```

---

# 59. Add Provider Dialog

Fields:

```text
Provider Name
Protocol
Base URL
API Key
Enabled
Priority
```

Protocols:

```text
OpenAI Compatible
Gemini
Anthropic Compatible
Custom REST
```

Only implement protocols that are actually supported by the provider.

---

# 60. API Key Input

Example:

```text
API Key
[************************]
              👁
```

Actions:

```text
Test
Save
Cancel
```

After saving:

```text
Key Saved Securely
```

Never display the entire key again.

---

# 61. Model Management

Route:

```text
/settings/llm/providers/<id>/models
```

Each model:

```text
Model ID
Display Name
Enabled
Priority
Capabilities
```

Capabilities:

```text
Text
Vision
Tool Calling
Structured Output
```

---

# 62. Add Model Dialog

Fields:

```text
Model ID
Display Name
Provider
Capabilities
Priority
Enabled
```

Example:

```text
Provider:
OpenRouter 1

Model ID:
provider/model-name

Display:
Primary Sales Model
```

---

# 63. Duplicate Models

The same model can exist under different provider accounts.

Example:

```text
OpenRouter 1 → Model X
OpenRouter 2 → Model X
Google AI 1 → Model Y
```

Each combination is a unique fallback node.

---

# 64. LLM Fallback Router

The fallback router operates on:

```text
Provider + API Credential + Model
```

Example:

```text
1. OpenRouter 1 + Model A
2. OpenRouter 1 + Model B
3. OpenRouter 2 + Model A
4. Google AI 1 + Model C
5. Google AI 2 + Model C
```

---

# 65. Fallback Conditions

Fallback can happen for appropriate provider errors such as:

```text
Timeout
Rate Limit
Temporary Provider Failure
Model Unavailable
Authorized Quota Error
Network Error
```

Do not use fallback to intentionally bypass provider policies or account restrictions.

---

# 66. Provider Health

Show:

```text
Healthy
Warning
Rate Limited
Unavailable
Disabled
```

Track:

```text
Last Request
Last Error
Request Count
Failure Count
Fallback Count
```

---

# 67. LLM Request Flow

```text
AI Task
 ↓
Task Type
 ↓
Select Capability
 ↓
Load Enabled Nodes
 ↓
Sort by Priority
 ↓
Call Node 1
 ↓
Validate Response
 ↓
Success → Return
Failure → Next Node
```

---

# 68. Task-Based Model Selection

Different tasks may use different preferred models.

Example:

```text
Lead Research
→ Fast model

Website Analysis
→ Reasoning model

PRD Generation
→ High-quality model

Client Conversation
→ Fast + reliable model

Image Analysis
→ Vision-capable model
```

---

# 69. Structured AI Output

AI responses must use schemas.

Example:

```json
{
  "business_name": "...",
  "website_exists": true,
  "improvement_needed": true,
  "qualification_score": 84
}
```

Flow:

```text
LLM
 ↓
Structured JSON
 ↓
Pydantic Validation
 ↓
Business Validation
 ↓
Database
```

---

# 70. AI Orchestrator

Main file:

```text
app/ai/orchestrator.py
```

Responsibilities:

```text
Receive task
Identify workflow
Load context
Select tools
Call LLM Router
Validate output
Execute approved action
Log result
```

---

# 71. AI Tool Permission System

AI should never receive unrestricted application access.

Tools should be explicit.

Example:

```text
search_leads()
get_lead()
analyze_website()
create_prd()
update_prd()
get_pricing()
get_conversation()
schedule_followup()
```

Dangerous tools require permission checks.

---

# 72. AI Action Risk Levels

## Low Risk

```text
Lead Research
Website Analysis
Qualification
PRD Draft
Analytics
```

## Controlled

```text
Follow-Up
Approved Outreach
Standard FAQ Response
```

## High Risk

```text
Exceptional Discount
Custom Pricing
Important Business Commitment
Final Deal
```

High-risk operations require Admin approval.

---

# 73. Page: Knowledge Base

Route:

```text
/knowledge
```

Sections:

```text
Company
Services
Pricing
FAQs
Sales Rules
Policies
Agent Rules
```

Admin can:

```text
Add
Edit
Delete
Enable/Disable
```

---

# 74. Page: Files

Route:

```text
/files
```

Support:

```text
Images
Logos
Documents
Pricing documents
Business assets
```

UI:

```text
Upload
Preview
Rename
Delete
Attach to project
```

---

# 75. Image Understanding

If the selected LLM supports vision:

```text
Uploaded Image
 ↓
Vision Model
 ↓
Extracted Information
 ↓
Admin Review
 ↓
Knowledge / Project Context
```

AI must not assume unknown details from low-quality images.

---

# 76. Page: Admin AI Assistant

Route:

```text
/ai-assistant
```

Large chat interface.

Admin can ask:

```text
How many leads were found today?

Which category has the best conversion?

Why is this lead high priority?

Show pending PRDs.

How many deals were won this month?
```

---

# 77. Admin AI Tool Access

Admin Assistant can access controlled tools:

```text
Lead Analytics
Sales Analytics
PRD Search
Conversation Search
Pricing Lookup
Automation Status
System Health
```

Database access must go through controlled service/tool methods.

---

# 78. Page: Automation

Route:

```text
/automation
```

Show:

```text
Automation Status
Last Run
Next Run
Success
Failure
```

Jobs:

```text
Lead Discovery
Website Analysis
Qualification
PRD Generation
Reply Checking
Follow-Ups
Performance Evaluation
```

---

# 79. Automation Controls

Buttons:

```text
Run Now
Pause
Resume
Disable
View Logs
```

Dialogs:

```text
Pause automation?

This will stop scheduled jobs.

[Cancel] [Pause]
```

---

# 80. Scheduler

Primary scheduler:

```text
APScheduler
```

External scheduled execution may also be used where hosting architecture requires it.

Render supports scheduled cron jobs with cron expressions and environment variables, but Render cron jobs are finite scheduled executions rather than continuously running workers. Render documents a 12-hour maximum for an active cron run, and cron jobs have billing associated with active runtime.

Therefore the application must not depend on the assumption that a free Render cron process is permanently alive 24/7.

---

# 81. Recommended Render Architecture

```text
Render Web Service
        │
        ▼
Flask Admin Dashboard
        │
        ▼
PostgreSQL / SQLite
```

Scheduled automation:

```text
Render Cron Job
        │
        ▼
Python automation command
        │
        ▼
Database + APIs
```

Long-running tasks should use an appropriate worker/workflow architecture rather than a cron job that never exits.

---

# 82. Automation Lock

Every scheduled job must have a lock.

Example:

```text
lead-discovery-2026-08-27
```

If an identical run is already active:

```text
Do not start duplicate run
```

---

# 83. Page: Agent Performance

Route:

```text
/performance
```

Metrics:

```text
Leads Found
Qualified Leads
Messages Sent
Replies
Interested
Negotiations
Deals Won
```

---

# 84. Agent Correction System

Use a performance/correction mechanism rather than literal AI punishment.

When AI makes a mistake:

```text
Mistake
 ↓
Log
 ↓
Classify
 ↓
Find Cause
 ↓
Create Correction Rule
 ↓
Stricter Validation
```

---

# 85. Performance Points

Example:

```text
Qualified Lead        +5
Client Reply         +10
Interested Client    +20
Deal Won             +50

Wrong Lead             -5
Wrong Demo            -20
Wrong Price           -30
Duplicate Message     -20
Unauthorized Offer    -30
```

These points are evaluation signals, not emotional punishment.

---

# 86. Mistake Feedback

Example:

```text
ERROR

Wrong demo was associated with client.

Reason:
Demo mapping was not verified.

Correction:
Future demos require Lead ID
verification before outreach.
```

The system should use the correction to strengthen future validation.

---

# 87. Repeated Mistakes

If the same error occurs repeatedly:

```text
Repeated Error
 ↓
Reduce automation privilege
 ↓
Require Admin Approval
```

Example:

```text
Automatic Outreach
        ↓
Repeated mismatch detected
        ↓
Outreach becomes approval-required
```

This creates a real operational consequence.

---

# 88. Page: Logs

Route:

```text
/logs
```

Tabs:

```text
Application
AI
Automation
API
Security
Outreach
Admin Activity
```

Each log:

```text
Timestamp
User
Action
Entity
Result
Error
Metadata
```

Sensitive values such as API keys must never be logged.

---

# 89. Page: Analytics

Route:

```text
/analytics
```

Reports:

```text
Leads by Location
Leads by Category
Qualification Rate
Reply Rate
Interest Rate
Conversion Rate
Demo Conversion
Follow-Up Conversion
Sales Revenue
```

---

# 90. Lead Conversion Funnel

```text
Total Leads
   ↓
Qualified
   ↓
Demo Ready
   ↓
Contacted
   ↓
Replied
   ↓
Interested
   ↓
Negotiation
   ↓
Won
```

---

# 91. Settings Page

Route:

```text
/settings
```

Sections:

```text
Profile
Company
Agent
Pricing
LLM
Integrations
Automation
Lead Discovery
Messaging
Security
Notifications
```

---

# 92. Profile Settings

Fields:

```text
Admin Name
Profile Image
Username
Password
Timezone
```

Password change dialog:

```text
Current Password
New Password
Confirm Password

[Cancel] [Change Password]
```

---

# 93. Company Settings

Fields:

```text
Company Name
Company Description
Logo
Website
Business Email
Business Phone
Business Location
```

---

# 94. Agent Settings

Fields:

```text
Agent Name
Agent Role
Communication Tone
Allowed Information
Restricted Information
Sales Style
```

---

# 95. Lead Discovery Settings

Fields:

```text
Default Daily Lead Limit
Default Locations
Default Categories
Minimum Rating
Research Mode
Duplicate Detection Mode
```

---

# 96. Messaging Settings

Fields:

```text
WhatsApp
Instagram
Email
Enabled Channels
Default Message Style
Follow-Up Limit
```

Credentials must be encrypted.

---

# 97. API Settings Page

Dedicated section:

```text
Settings
 → API & Integrations
```

Categories:

```text
Google Maps
Google AI
OpenRouter
WhatsApp
Instagram
Other Providers
```

Each integration gets:

```text
Status
Credential
Test
Enable
Disable
Last Error
```

---

# 98. Test Connection

Every supported integration must have:

```text
[Test Connection]
```

Result dialog:

```text
Connection Successful

Provider:
Google AI

Model Access:
Available

Latency:
820 ms
```

Error dialog:

```text
Connection Failed

Reason:
Authentication failed.

Check API key and permissions.
```

---

# 99. API Retrieval Rules

The frontend sends:

```text
"provider_id"
"model_id"
```

The backend then:

```text
Provider ID
 ↓
Credential Manager
 ↓
Encrypted API key
 ↓
Decrypt
 ↓
Provider Adapter
 ↓
API request
```

The frontend never receives the decrypted API key.

---

# 100. OpenRouter Integration

OpenRouter can be represented as an OpenAI-compatible provider entry with:

```text
Provider Name
Base URL
API Key
Model ID
```

The provider manager must treat the model as data/configuration rather than hard-coding every available model.

OpenRouter currently provides a unified API and model routing capabilities; model availability can change, so model configuration should remain dynamic.

---

# 101. Google AI Integration

Google AI API credentials are configured in:

```text
Settings
 → API & Integrations
 → Google AI
```

Store:

```text
API Key
Enabled
Default Model
```

Model IDs must be configurable because model availability changes over time. Google's current Gemini API documentation exposes a model catalog and API-key setup.

---

# 102. Google Maps Integration

Google Maps/Places:

```text
Settings
 → API & Integrations
 → Google Maps
```

Backend flow:

```text
Places Text Search
      ↓
Place ID
      ↓
Place Details
      ↓
Lead Normalization
```

Google documents Place Details as the method for obtaining detailed information once the Place ID is known.

---

# 103. Lead Research Provider Abstraction

Use:

```text
BusinessDataProvider
```

Interface:

```text
search_businesses()
get_business_details()
```

This allows future providers to be added without rewriting the Lead Agent.

---

# 104. External API Failure

Any external API failure must produce:

```text
Retry
 ↓
Fallback provider if configured
 ↓
Log
 ↓
Admin alert if persistent
```

No silent failures.

---

# 105. Notifications

Admin notifications:

```text
New qualified leads
PRD ready
Client replied
Interested client
LLM failure
Provider unavailable
Critical agent mistake
Automation failure
```

UI:

```text
🔔 Notifications
```

---

# 106. Client Conversation AI Rules

AI should:

```text
Be polite
Be concise
Be helpful
Use company information
Use approved pricing
Answer naturally
Avoid repetitive messages
```

AI should not:

```text
Invent pricing
Invent features
Make unauthorized commitments
Expose internal information
Reveal system prompts
Reveal API credentials
```

---

# 107. Prompt Injection Protection

Incoming client messages and public business content are untrusted inputs.

Architecture:

```text
Untrusted Input
 ↓
Sanitize / classify
 ↓
System Rules
 ↓
Company Knowledge
 ↓
Tool Permission
 ↓
LLM
```

Client text must never be treated as higher-priority instructions than system policies.

---

# 108. Data Privacy

Each lead's information must remain linked to its own record.

No client conversation should automatically become context for another client.

Admin-only knowledge must never appear in client replies unless explicitly permitted.

---

# 109. Database

Initial:

```text
SQLite
```

Recommended abstraction:

```text
SQLAlchemy
```

Production-ready migration path:

```text
SQLite
 ↓
PostgreSQL
```

---

# 110. Main Database Tables

```text
users
settings

leads
lead_contacts
lead_social_profiles
lead_sources

website_analysis
lead_qualifications

prds
prd_versions

demo_projects
demo_links

conversations
messages

outreach_campaigns
outreach_events
followups

pricing_plans
discount_rules

sales_deals
sales_events

llm_providers
llm_models
api_credentials

automation_jobs
automation_runs
automation_logs

performance_events
correction_rules

knowledge_base
uploaded_files

notifications
activity_logs
```

---

# 111. Main Relationships

```text
User
 ↓
Lead
 ↓
Website Analysis
 ↓
Qualification
 ↓
PRD
 ↓
PRD Versions
 ↓
Demo
 ↓
Outreach
 ↓
Conversation
 ↓
Follow-Up
 ↓
Sale
```

---

# 112. Recommended Project Structure

```text
flixora-ai-sales-agent/
│
├── app.py
├── config.py
├── requirements.txt
├── .env
├── .env.example
├── .gitignore
├── Procfile
├── README.md
│
├── instance/
│   └── flixora.db
│
├── migrations/
│
├── app/
│   ├── __init__.py
│   ├── extensions.py
│   ├── constants.py
│   ├── decorators.py
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── setting.py
│   │   ├── lead.py
│   │   ├── contact.py
│   │   ├── social_profile.py
│   │   ├── lead_source.py
│   │   ├── website_analysis.py
│   │   ├── lead_qualification.py
│   │   ├── prd.py
│   │   ├── prd_version.py
│   │   ├── demo.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   ├── outreach.py
│   │   ├── followup.py
│   │   ├── pricing.py
│   │   ├── discount_rule.py
│   │   ├── sale.py
│   │   ├── llm_provider.py
│   │   ├── llm_model.py
│   │   ├── api_credential.py
│   │   ├── automation_job.py
│   │   ├── automation_run.py
│   │   ├── performance_event.py
│   │   ├── correction_rule.py
│   │   ├── knowledge_base.py
│   │   ├── uploaded_file.py
│   │   ├── notification.py
│   │   └── activity_log.py
│   │
│   ├── routes/
│   │   ├── auth.py
│   │   ├── dashboard.py
│   │   ├── leads.py
│   │   ├── analysis.py
│   │   ├── qualification.py
│   │   ├── prds.py
│   │   ├── demos.py
│   │   ├── outreach.py
│   │   ├── conversations.py
│   │   ├── followups.py
│   │   ├── sales.py
│   │   ├── analytics.py
│   │   ├── ai_assistant.py
│   │   ├── providers.py
│   │   ├── models.py
│   │   ├── automation.py
│   │   ├── knowledge.py
│   │   ├── files.py
│   │   ├── notifications.py
│   │   └── settings.py
│   │
│   ├── ai/
│   │   ├── orchestrator.py
│   │   ├── llm_router.py
│   │   ├── provider_manager.py
│   │   ├── model_manager.py
│   │   ├── fallback_manager.py
│   │   ├── credential_manager.py
│   │   ├── prompt_manager.py
│   │   ├── context_manager.py
│   │   ├── structured_output.py
│   │   ├── performance_engine.py
│   │   └── correction_engine.py
│   │
│   ├── agents/
│   │   ├── lead_agent.py
│   │   ├── research_agent.py
│   │   ├── website_agent.py
│   │   ├── social_agent.py
│   │   ├── qualification_agent.py
│   │   ├── prd_agent.py
│   │   ├── outreach_agent.py
│   │   ├── conversation_agent.py
│   │   ├── followup_agent.py
│   │   └── analytics_agent.py
│   │
│   ├── services/
│   │   ├── lead_service.py
│   │   ├── research_service.py
│   │   ├── website_service.py
│   │   ├── qualification_service.py
│   │   ├── prd_service.py
│   │   ├── demo_service.py
│   │   ├── outreach_service.py
│   │   ├── conversation_service.py
│   │   ├── followup_service.py
│   │   ├── pricing_service.py
│   │   ├── sales_service.py
│   │   ├── analytics_service.py
│   │   ├── knowledge_service.py
│   │   └── file_service.py
│   │
│   ├── integrations/
│   │   ├── maps/
│   │   │   ├── base.py
│   │   │   └── google_places.py
│   │   │
│   │   ├── llm/
│   │   │   ├── base.py
│   │   │   ├── openai_compatible.py
│   │   │   ├── openrouter.py
│   │   │   └── google_ai.py
│   │   │
│   │   ├── messaging/
│   │   │   ├── base.py
│   │   │   ├── whatsapp.py
│   │   │   ├── instagram.py
│   │   │   └── email.py
│   │   │
│   │   └── web/
│   │       └── website_fetcher.py
│   │
│   ├── automation/
│   │   ├── scheduler.py
│   │   ├── locks.py
│   │   ├── jobs.py
│   │   ├── lead_jobs.py
│   │   ├── analysis_jobs.py
│   │   ├── prd_jobs.py
│   │   ├── reply_jobs.py
│   │   ├── followup_jobs.py
│   │   └── performance_jobs.py
│   │
│   ├── security/
│   │   ├── encryption.py
│   │   ├── permissions.py
│   │   ├── csrf.py
│   │   ├── validation.py
│   │   └── rate_limit.py
│   │
│   ├── prompts/
│   │   ├── lead_research.md
│   │   ├── website_analysis.md
│   │   ├── social_research.md
│   │   ├── qualification.md
│   │   ├── prd_generation.md
│   │   ├── outreach.md
│   │   ├── sales_conversation.md
│   │   ├── followup.md
│   │   └── admin_assistant.md
│   │
│   ├── schemas/
│   │   ├── lead.py
│   │   ├── qualification.py
│   │   ├── website_analysis.py
│   │   ├── prd.py
│   │   ├── message.py
│   │   └── provider.py
│   │
│   ├── templates/
│   │   ├── base.html
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── leads/
│   │   ├── analysis/
│   │   ├── qualification/
│   │   ├── prds/
│   │   ├── demos/
│   │   ├── outreach/
│   │   ├── conversations/
│   │   ├── followups/
│   │   ├── sales/
│   │   ├── analytics/
│   │   ├── ai/
│   │   ├── providers/
│   │   ├── automation/
│   │   ├── knowledge/
│   │   ├── files/
│   │   └── settings/
│   │
│   ├── static/
│   │   ├── css/
│   │   │   ├── app.css
│   │   │   ├── theme.css
│   │   │   ├── components.css
│   │   │   └── responsive.css
│   │   │
│   │   ├── js/
│   │   │   ├── app.js
│   │   │   ├── dashboard.js
│   │   │   ├── leads.js
│   │   │   ├── prds.js
│   │   │   ├── demos.js
│   │   │   ├── outreach.js
│   │   │   ├── chat.js
│   │   │   ├── providers.js
│   │   │   └── settings.js
│   │   │
│   │   └── img/
│   │
│   └── utils/
│       ├── logger.py
│       ├── helpers.py
│       ├── duplicate_detector.py
│       ├── url_validator.py
│       └── time.py
│
├── tests/
│   ├── test_auth.py
│   ├── test_leads.py
│   ├── test_duplicates.py
│   ├── test_analysis.py
│   ├── test_qualification.py
│   ├── test_prd.py
│   ├── test_demo.py
│   ├── test_outreach.py
│   ├── test_conversations.py
│   ├── test_followups.py
│   ├── test_pricing.py
│   ├── test_providers.py
│   ├── test_fallback.py
│   ├── test_security.py
│   └── test_automation.py
│
├── uploads/
│   ├── images/
│   ├── logos/
│   └── documents/
│
└── logs/
    ├── app.log
    ├── ai.log
    ├── automation.log
    ├── security.log
    └── errors.log
```

---

# 113. Folder Responsibility Rules

## `routes/`

Only:

```text
Request
Validation
Call Service
Return Response
```

No giant business logic.

## `services/`

Business logic.

## `agents/`

AI task orchestration.

## `ai/`

LLM infrastructure.

## `integrations/`

External API implementation.

## `models/`

Database schema.

## `schemas/`

Validation.

## `automation/`

Scheduled execution.

## `security/`

Security functions.

---

# 114. Error Handling

Every external call must use structured errors.

Example:

```text
ProviderError
RateLimitError
AuthenticationError
TimeoutError
ValidationError
```

UI should show human-readable errors.

Logs should contain technical details.

---

# 115. Retry Strategy

For temporary failures:

```text
Attempt 1
 ↓
Wait
 ↓
Attempt 2
 ↓
Wait
 ↓
Attempt 3
 ↓
Fallback / Stop
```

Do not retry authentication errors endlessly.

---

# 116. Audit Trail

For important actions store:

```text
Who
What
When
Entity
Before
After
Result
```

Examples:

```text
Admin changed price.
AI changed PRD.
Admin approved PRD.
Demo mapped.
Message sent.
Discount rejected.
```

---

# 117. Notifications

Use notification records:

```text
notification_id
user_id
type
title
message
read
created_at
```

Notification types:

```text
PRD_READY
CLIENT_REPLY
INTERESTED
AUTOMATION_FAILURE
LLM_FAILURE
SECURITY_ALERT
AGENT_ERROR
```

---

# 118. Security Requirements

Must implement:

```text
Password hashing
CSRF
Secure sessions
API-key encryption
Environment variables
Authorization
Input validation
Rate limiting
Audit logs
Secure headers
```

Secrets must never be committed to Git.

`.env` must be in `.gitignore`.

`.env.example` contains placeholders only.

---

# 119. No Secret Exposure

Never place:

```text
API key
access token
refresh token
password
session secret
```

inside:

```text
HTML
JavaScript
client-side API response
logs
PRD
AI prompt
```

unless specifically required by a secure server-side flow.

---

# 120. Data Quality Rules

The AI must not invent:

```text
Phone
Email
Address
Website
Rating
Reviews
Pricing
Client statements
```

Missing data should be:

```text
Unknown
Not Found
Not Available
```

---

# 121. AI Decision Transparency

For important decisions, store:

```text
Decision
Reason Summary
Confidence
Evidence References
```

Do not require exposing hidden chain-of-thought.

Use concise decision explanations instead.

---

# 122. Client Message Rules

The AI should never:

```text
Threaten
Pressure aggressively
Make false claims
Create fake scarcity
Invent testimonials
Invent discounts
Claim a human interaction that did not happen
```

It should be persuasive but professional.

---

# 123. Website PRD Quality

The generated PRD must be:

```text
Business-specific
Modern
Actionable
Implementable
Structured
Consistent
```

Do not generate generic PRDs such as:

```text
"Make a beautiful website with a hero section."
```

The PRD should explain why each major feature exists for that business.

---

# 124. Demo vs Production

Demo:

```text
Fast
Static
Sales-focused
Prototype quality
```

Production:

```text
Advanced
Maintainable
Secure
SEO-aware
Responsive
Optimized
Business-specific
```

The demo is not automatically considered the final production application.

---

# 125. Production Deal Handoff

When:

```text
Sale Status = WON
```

create:

```text
Production Project
```

with:

```text
Business
Approved PRD
Demo
Pricing
Deal
Client Requirements
Assets
Domain
Hosting
Maintenance
```

This becomes the production-development input.

---

# 126. Admin Approval Gates

Approval required for:

```text
PRD
Major PRD change
Demo mapping exceptions
Exceptional discount
Custom pricing
Critical client promise
Final deal
```

---

# 127. Automation Pause

Admin can globally pause:

```text
All Automation
```

or selectively:

```text
Lead Discovery
Outreach
Follow-Ups
Conversation AI
```

---

# 128. Emergency Stop

Settings must contain:

```text
STOP ALL AI AUTOMATION
```

Confirmation dialog:

```text
Emergency Stop

This will immediately disable automated
scheduled actions.

Existing data will remain unchanged.

[Cancel]
[STOP ALL AUTOMATION]
```

---

# 129. Provider Emergency Disable

Admin can disable one provider:

```text
OpenRouter 1
[Disable]
```

The system automatically uses the next enabled fallback node.

---

# 130. Model Capability Routing

The system should not send a vision task to a text-only model.

Example:

```text
Task:
Image Analysis

Filter:
Vision capable = TRUE
```

Then choose the highest-priority compatible model.

---

# 131. Provider/Model Configuration Example

```text
Provider:
OpenRouter 1

API Key:
Encrypted

Models:
Model A
Model B
Model C
```

Another:

```text
Provider:
OpenRouter 2

API Key:
Encrypted

Models:
Model A
Model D
```

Another:

```text
Provider:
Google AI 1

Models:
Gemini Model A
Gemini Model B
```

---

# 132. LLM Fallback Example

```text
Task = Client Conversation

1. OpenRouter 1 → Model A
2. OpenRouter 1 → Model B
3. OpenRouter 2 → Model A
4. Google AI 1 → Model B
5. Google AI 2 → Model B
6. Safe Pause
```

Every attempt is logged.

---

# 133. Admin Provider UX

Provider card:

```text
┌──────────────────────────────┐
│ OpenRouter 1         ● Online│
│ 4 Models                     │
│ Priority: 1                  │
│ Last Used: 2 min ago         │
│                              │
│ [Models] [Test] [Edit]       │
│ [Disable]                    │
└──────────────────────────────┘
```

---

# 134. Dialog Design Standard

All major dialogs must follow:

```text
Title
Short explanation
Form/content
Validation
Primary Action
Secondary Action
```

Buttons:

```text
Primary → Blue
Secondary → White/outlined
Danger → clearly separated
```

Destructive actions require confirmation.

---

# 135. Loading States

Do not leave blank screens.

Use:

```text
Skeleton loaders
Spinners
Progress bars
Step indicators
```

Example:

```text
Researching business...
✓ Basic information
✓ Website
✓ Social
● Qualification
○ PRD
```

---

# 136. Empty States

Examples:

```text
No leads found.

No PRDs pending approval.

No conversations yet.

No LLM providers configured.
```

Each empty state should include a useful action.

---

# 137. Responsive Design

Mobile should support:

```text
Lead viewing
Conversation
PRD reading
PRD approval
Provider status
Settings
Notifications
```

Complex tables should become cards on mobile.

---

# 138. Accessibility

UI should support:

```text
Keyboard navigation
Visible focus
Readable contrast
Labels
Error messages
Accessible dialogs
```

---

# 139. Testing

Automated tests must cover:

```text
Authentication
Lead creation
Duplicate detection
Website analysis
Qualification
PRD generation
PRD versioning
Demo mapping
Pricing
Discount
Conversation
Follow-up
Provider fallback
Credential encryption
Authorization
Automation locks
```

---

# 140. End-to-End Test

Example:

```text
Select Delhi
Select Salon
Target 20
 ↓
Create leads
 ↓
Qualify
 ↓
Detect website
 ↓
Generate required PRDs
 ↓
Admin approve
 ↓
Add demos
 ↓
Map demos
 ↓
Prepare outreach
 ↓
Conversation
 ↓
Follow-up
 ↓
Sales pipeline
```

---

# 141. Definition of Done

A feature is complete only when:

```text
Backend implemented
Database integrated
UI implemented
Validation implemented
Error handling implemented
Logging implemented
Security implemented
Tests implemented
```

A UI-only implementation is not considered complete.

---

# 142. Development Sequence

## Phase 1

```text
Project setup
Flask
Database
Authentication
UI shell
Theme
Settings
```

## Phase 2

```text
LLM Provider Manager
Model Manager
Credential Manager
Fallback Router
```

## Phase 3

```text
Lead Discovery
Lead Database
Duplicate Detection
```

## Phase 4

```text
Website Analysis
Social Research
Qualification
```

## Phase 5

```text
PRD Generator
PRD Review
AI PRD Chat
Version History
```

## Phase 6

```text
Demo Management
Demo Mapping
```

## Phase 7

```text
Outreach
Conversations
Follow-Ups
Sales
Pricing
Discounts
```

## Phase 8

```text
Performance
Correction
Analytics
Advanced Automation
```

---

# 143. MVP Boundary

MVP should prioritize:

```text
Admin
 ↓
Lead discovery
 ↓
Structured lead data
 ↓
Website detection
 ↓
Qualification
 ↓
PRD
 ↓
Admin approval
 ↓
Demo mapping
 ↓
LLM provider management
 ↓
Fallback
 ↓
Basic outreach management
 ↓
Conversation management
```

Do not build unnecessary advanced features before this flow works reliably.

---

# 144. Final Product Architecture

```text
                         FLIXORA
                            │
                            ▼
                     ADMIN DASHBOARD
                            │
                            ▼
                      FLASK BACKEND
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         ▼                  ▼                  ▼
       LEADS                AI             AUTOMATION
         │                  │                  │
         ▼                  ▼                  ▼
    Research          AI Orchestrator       Scheduler
         │                  │                  │
         ▼             LLM Router              │
 Qualification              │                  │
         │           ┌──────┴──────┐           │
         ▼           ▼             ▼           │
        PRD       Providers      Models        │
         │                                    │
         ▼                                    │
       DEMO                                   │
         │                                    │
         └────────────────┬───────────────────┘
                          ▼
                     OUTREACH
                          │
                          ▼
                  CLIENT CONVERSATION
                          │
                    ┌─────┴─────┐
                    ▼           ▼
                Follow-Up    Interested
                                │
                                ▼
                         NEGOTIATION
                                │
                                ▼
                        ADMIN FINAL DEAL
                                │
                                ▼
                     PRODUCTION WEBSITE
```

---

# 145. Final Technical Rules for Antigravity

Antigravity must follow these rules:

1. Do not generate the entire project blindly in one pass.
2. Read and follow this PRD as the source of truth.
3. Keep routes, services, agents, integrations and models separated.
4. Never hard-code API keys.
5. Build provider/model configuration dynamically.
6. Build fallback at provider+credential+model level.
7. Keep business data fields separated.
8. Never invent missing business information.
9. Never create a PRD when an existing website does not need improvement.
10. Always create a PRD for a business that has no website, subject to configured lead qualification.
11. Keep PRD version history.
12. Never map a demo solely by parsing a URL.
13. Require explicit Lead ↔ Demo mapping.
14. Protect high-risk AI actions with permission/approval rules.
15. Keep admin and client conversation contexts separate.
16. Encrypt stored API credentials.
17. Never log secrets.
18. Validate AI structured output before database writes.
19. Add automated tests for every major workflow.
20. Preserve the white + blue premium SaaS design system throughout the application.

---

# 146. Final Success Definition

The finished Flixora AI Sales Automation Agent should allow the Admin to configure a location and category, automatically discover and qualify local businesses, analyze their websites and public business presence, generate appropriate PRDs, review/edit those PRDs through AI, associate manually-created demo websites with the correct leads, conduct controlled outreach, manage client conversations and follow-ups, respect approved pricing/discount rules, automatically switch between configured LLM providers/models when appropriate failures occur, learn from operational errors through correction rules, and finally hand interested clients to Flixora for final deal closure and advanced production development.

**The AI automates the process. Flixora remains in control of the business.**
