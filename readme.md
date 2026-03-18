# LeadsFlow

> B2B lead processing pipeline: email validation, AI-powered content generation, and automated SMTP sending — built with Streamlit.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.25+-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-412991?logo=openai&logoColor=white)](https://openai.com)

---

## What It Does

Process B2B sales leads through a **3-step modular workflow**, each step independent and cacheable:

1. **Validate** — Check email formats, verify DNS MX records, filter generic addresses, extract company names
2. **Generate** — Create personalized email content using OpenAI GPT with customizable templates in 6 languages
3. **Send** — Deliver emails via SMTP with rate limiting, batching, and delivery tracking

---

## Key Features

- **Email Validation** — Format check, DNS MX verification, generic address filtering (admin@, info@, etc.), duplicate detection
- **Company Extraction** — Automatic company name extraction from email domains
- **AI Content Generation** — OpenAI GPT-powered personalized emails with template variable system
- **6 Languages** — English, French, Spanish, German, Arabic, Chinese
- **4 Built-in Templates** — Introduction, Follow-up, Event Invitation, Case Study (+ custom templates)
- **Template Variables** — `{{firstName}}`, `{{company}}`, `{{jobTitle}}`, `{{product}}`, and more
- **SMTP Integration** — Gmail, Outlook, Yahoo, and custom SMTP servers
- **Rate Limiting** — Configurable delays (1-60s) between emails to avoid spam filters
- **Batch Processing** — Configurable batch sizes for memory-efficient processing of large datasets (100MB+)
- **Multi-Threading** — Up to 10 workers for validation, 5 for generation
- **Caching System** — Results saved as Excel files with metadata, supports resume from any step
- **Test Mode** — Save to drafts instead of sending

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| UI | Streamlit 1.25+ |
| AI | OpenAI GPT API |
| Email | SMTP (smtplib), rate-limited sending |
| Validation | dnspython (MX records), tldextract (domain parsing) |
| Data | pandas, openpyxl (Excel I/O) |
| Models | Pydantic 2.0+ (data validation) |

---

## Quick Start

### Installation

```bash
git clone https://github.com/Loryo80/leadsflow.git
cd leadsflow
pip install -r requirements.txt
```

### Configuration

```bash
# 1. OpenAI API key (create .streamlit/secrets.toml)
mkdir -p .streamlit
echo 'OPENAI_API_KEY = "sk-..."' > .streamlit/secrets.toml

# 2. SMTP credentials (create .env from example)
cp .env.example .env
# Edit .env with your email provider settings
```

**SMTP Examples:**

| Provider | Server | Port | SSL |
|----------|--------|------|-----|
| Gmail | smtp.gmail.com | 587 | No (STARTTLS) |
| Outlook | smtp.office365.com | 587 | No (STARTTLS) |
| Yahoo | smtp.mail.yahoo.com | 465 | Yes |

> Gmail requires an [App Password](https://support.google.com/accounts/answer/185833), not your regular password.

### Run

```bash
streamlit run app.py
```

---

## Workflow

### Step 1: Email Validation

Upload an Excel file with email addresses. The system validates format, checks DNS MX records, filters generic addresses, extracts company names, and removes duplicates.

**Output:** `cache/step1_TIMESTAMP.xlsx`

### Step 2: Email Content Generation

Loads validated data from Step 1. Select a template, choose target language (6 supported), fill sender info. OpenAI generates personalized subject + body for each lead.

**Output:** `cache/step2_TIMESTAMP.xlsx`

### Step 3: Email Sending

Loads generated content from Step 2. Sends via SMTP in configurable batches with random delays. Tracks delivery status. Supports test mode (drafts only).

**Output:** `cache/step3_TIMESTAMP.xlsx` with delivery status log.

---

## Project Structure

```
leadsflow/
├── app.py                    # Main Streamlit entry point
├── settings.py               # Settings UI page
├── app_settings.py           # Configuration defaults
├── src/leadsflow/
│   ├── core/
│   │   ├── config/           # SMTP config from .env
│   │   ├── email/            # SMTP sender, templates, placeholders
│   │   └── llm/              # OpenAI integration
│   ├── steps/
│   │   ├── validation.py     # Step 1
│   │   ├── generation.py     # Step 2
│   │   └── sending.py        # Step 3
│   └── utils.py
├── cache/                    # Auto-created, stores step results
└── tests/
```

---

## Input Format

Excel file (`.xlsx`) with at minimum an `email` column. Optional columns:

| Column | Required | Description |
|--------|----------|-------------|
| email | Yes | Email address |
| firstName | No | Contact first name |
| lastName | No | Contact last name |
| company | No | Company name (auto-extracted if missing) |
| jobTitle | No | Contact job title |

---

## License

MIT

## Author

**Yassine Senhaji** — AI Solution Architect
- [www.digitalsy.ma](https://www.digitalsy.ma/)
- [github.com/Loryo80](https://github.com/Loryo80)
