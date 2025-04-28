# Lead Processing Workflow Application

This Streamlit application provides a comprehensive workflow for processing B2B sales leads through three independent, cacheable steps:

1. **Email Validation & Company Extraction** - Clean your data by validating emails and extracting company information
2. **Email Content Generation** - Create personalized email content using AI-driven templates
3. **Email Sending** - Send emails via SMTP in a controlled, batched manner

## Features

- **Modular Design** - Each step can be run independently with caching between steps
- **Efficient Processing** - Optimized for large datasets (up to 50,000 records) with multi-threading and batching
- **Resume Capability** - Pick up where you left off even with large datasets
- **Company Extraction** - Automatically extract company names from email domains
- **AI-Powered Content** - Generate personalized emails using templates and OpenAI GPT integration
- **Controlled Sending** - Send via SMTP with rate limiting and tracking
- **Multi-language Support** - Generate emails in multiple languages (English, French, Spanish, German, Arabic, Chinese)

## Installation

1. Clone this repository
2. Install required dependencies:

```bash
pip install -r requirements.txt
```

3. Set up your OpenAI API key (for email generation):
   - Create a `.streamlit/secrets.toml` file with:
   ```
   OPENAI_API_KEY = "your-api-key-here"
   ```
   - Or set it as an environment variable:
   ```
   export OPENAI_API_KEY="your-api-key-here"
   ```

4. For email sending, configure your SMTP settings in a `.env` file:
   ```
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=465
   SMTP_USERNAME=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   SMTP_FROM_EMAIL=your-email@gmail.com
   SMTP_USE_SSL=True
   ```

## Usage

1. Start the Streamlit application:

```bash
streamlit run app.py
```

2. Navigate through each step using the sidebar.

### Step 1: Email Validation

- Upload your Excel file containing contact information
- Select the email column
- Run validation to check email validity and extract company names
- Review results and proceed to step 2

### Step 2: Email Content Generation

- Select validated data from step 1
- Configure email template and sender information
- Choose your preferred language
- Generate personalized email content for each valid contact
- Review sample emails and proceed to step 3

### Step 3: Email Sending

- Select generated content from step 2
- Configure SMTP settings
- Choose sending options (batching, delays, daily limits)
- Select sending method (all, by company, or by batch)
- Send emails via SMTP
- Monitor sending progress and review results

## Architecture

The application is built with a modular architecture within the `src/leadsflow` package:

- `app.py` - Main application entry point (root level).
- `app_settings.py` - Configuration management and defaults (root level).
- `settings.py` - Streamlit UI for the settings page (root level).

- `src/leadsflow/`
  - `__init__.py`
  - `utils.py` - Utility functions for logging, file handling, etc.
  - `core/` - Core application logic.
    - `__init__.py`
    - `config/`
      - `__init__.py`
      - `env_loader.py` - Environment variables management.
    - `email/`
      - `__init__.py`
      - `placeholder_checker.py` - Checks and replaces template variables.
      - `smtp_sender.py` - SMTP email sending implementation.
      - `templates.py` - Email template loading, saving, rendering (and UI components).
    - `llm/`
      - `__init__.py`
      - `generator.py` - OpenAI integration for personalized content generation.
  - `steps/` - Modules for each workflow step.
    - `__init__.py`
    - `validation.py` - Step 1: Email validation and company extraction.
    - `generation.py` - Step 2: Email content generation using templates and LLM.
    - `sending.py` - Step 3: Email sending via SMTP.

- `tests/` - Contains test scripts (e.g., `test_email.py`).
- `cache/` - Stores cached data from workflow steps.
- `templates/` - Stores user-defined JSON email templates.

## Data Flow

The application maintains a cache of processed data at each step, making it efficient for large datasets:

1. Raw data → Validated data (step1_*.xlsx)
2. Validated data → Generated content (step2_*.xlsx)
3. Generated content → Sending results (step3_*.xlsx)

## Tips for Large Datasets

- **Batch Processing**: The app processes data in batches to manage memory usage
- **Resume Capability**: If a step is interrupted, you can resume from the last saved state
- **Separate Processing**: Run each step when convenient - validate all contacts first, then generate content later
- **Company Filtering**: In the sending step, you can choose to send emails company by company

## Input Format

The application accepts Excel files (.xlsx or .xls) with any column structure, as long as one column contains email addresses. The typical format might include:

- First Name
- Last Name
- Email Address
- Job Title
- Company
- etc.

## Requirements

- Python 3.7+
- Streamlit
- Pandas & OpenPyxl (for Excel handling)
- OpenAI Python SDK (for content generation)
- SMTP server access (for email sending)

## Notes

- The email validation performs format checks and DNS MX record verification
- Company extraction is based on domain analysis and may require manual review
- Email generation requires an OpenAI API key (GPT-3.5-turbo or GPT-4 family models)
- The application handles rate limiting for both API calls and email sending
- All data is processed locally, ensuring your lead data never leaves your system