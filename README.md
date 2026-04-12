# Pinterest Factory

A Streamlit-powered dashboard for batch production of Pinterest pins from recipe content. This tool automates the creation of compelling pin titles, descriptions, and visual content for food blogs and recipe websites.

## Features

- **Batch Intake**: Automatically scrape recipes from your food blog website or manually enter recipe data

**Live Demo**: https://pinterest-factory-example.streamlit.app/

> **Customization**: Replace `https://example.com/recipes/` URLs in the example recipes with your own website URLs to match your content.
> 
> **Note**: The live demo shows the complete UI functionality, but to use the full dashboard you'll need to run Ollama locally for AI features and configure your own Notion API for content synchronization.

- **AI Copy Engine**: Generate multiple hook angles and compelling descriptions using local Ollama models

- **Pin Generation**: Create visually appealing pins with custom typography and layout

- **Notion Sync**: Export generated content to Notion database for content management

## Tech Stack

- **Frontend**: Streamlit (web interface)
- **AI**: Ollama (local LLM integration)
- **Image Processing**: Pillow (PIL)
- **Data**: Pandas
- **API**: Requests, BeautifulSoup4
- **Environment**: python-dotenv

## Project Structure

```
Pinterest-Factory/
|
app.py                    # Main Streamlit application router
components/               # Tab components
  |-- intake.py          # Step 1: Batch recipe intake
  |-- ai_engine.py       # Step 2: AI copy generation
  |-- pin_generator.py   # Step 3: Visual pin creation
  |-- notion_sync.py     # Step 4: Notion database sync
  |-- export.py          # Export utilities
utils/                   # Helper utilities
  |-- ollama_client.py   # Ollama API client
requirements.txt         # Python dependencies
.env.example            # Environment variables template
template.png            # Pin design template
Montserrat/             # Font files for pin design
```

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/Pinterest-Factory.git
   cd Pinterest-Factory
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

5. **Install Ollama** (for AI features)
   ```bash
   # Follow instructions at https://ollama.ai
   # Pull required model:
   ollama pull llama3:8b-instruct-q4_K_M
   ```

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```env
# Notion Integration (required for Tab 4)
NOTION_TOKEN=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Ollama Configuration (optional - defaults work for local install)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3:8b-instruct-q4_K_M
OLLAMA_TIMEOUT=180
```

### Notion Setup

1. Create a Notion integration at https://www.notion.so/my-integrations
2. Share your recipe database with the integration
3. Copy the integration token and database ID to your `.env` file

## Usage

1. **Start the application**
   ```bash
   streamlit run app.py
   ```

2. **Navigate through the 4-step workflow:**

   **Step 1: Batch Intake**
   - Enter your food blog URL to automatically scrape recipe information
   - Filter and select recipes for your batch
   - Add custom recipes manually if needed
   - Lock the batch to proceed

   **Step 2: AI Copy Engine**
   - Generate multiple hook angles for each recipe
   - Create compelling descriptions
   - Review and edit AI-generated content

   **Step 3: Pin Generation**
   - Generate visual pins using custom templates
   - Customise typography and layout
   - Export pin images

   **Step 4: Notion Sync**
   - Export all generated content to Notion
   - Track production status
   - Manage content calendar

## Features in Detail

### Recipe Management
- Automatic web scraping from food blog websites
- Intelligent recipe extraction (name, time, ingredients, benefits)
- Custom recipe entry with URL validation
- Benefit categorization (Quick Weeknight, High Protein, Budget Friendly, etc.)
- Batch locking to prevent accidental changes

### AI-Powered Copy Generation
- Multiple hook angles per recipe (5-7 variations)
- Compelling descriptions optimised for Pinterest
- Local Ollama integration for privacy and cost control
- Customizable prompts and parameters

### Visual Pin Design
- Custom template system
- Montserrat font family for professional typography
- Responsive layout generation
- Batch export capabilities

### Content Management
- Notion database synchronization
- Production status tracking
- Export to CSV format
- Content calendar integration

## Development

### Web Scraping Features
The app automatically extracts recipe information from food blog websites:
- **Recipe Detection**: Finds recipe links using common URL patterns
- **Data Extraction**: Extracts recipe names, cooking times, ingredient counts, and benefits
- **Smart Categorization**: Automatically categorizes recipes based on content analysis
- **Respectful Scraping**: Includes rate limiting to avoid overwhelming servers

### Manual Recipe Entry
You can still add recipes manually if web scraping doesn't find all your content:

```python
# Manual entry format (for reference)
{"name": "Recipe Name", "url": "https://yourwebsite.com/recipe-slug", "time": "XX mins", "ingredients": "X", "benefit": "Category"},
```

### Customising Pin Templates
Replace `template.png` with your own design template. The system automatically overlays text based on the template dimensions.

### Extending AI Prompts
Modify the prompt templates in `components/ai_engine.py` to customise the generated content style and tone.

## Troubleshooting

### Ollama Connection Issues
- Ensure Ollama is running: `ollama serve`
- Check model availability: `ollama list`
- Verify host configuration in `.env`

### Notion Sync Problems
- Verify integration token is valid
- Ensure databases is shared with the integration
- Check database ID matches the correct database

### Font Rendering Issues
- Ensure Montserrat font files are in the `/Montserrat` directory
- Verify font permissions and file integrity

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Deployment

### Streamlit Cloud (Recommended)
1. Push your code to GitHub
2. Connect your repository to Streamlit Cloud
3. Configure environment variables in Streamlit Cloud dashboard
4. Deploy - your app will be live at `https://yourapp.streamlit.app`

### Other Platforms
- **Heroku**: Use the Streamlit Heroku template
- **Render**: Deploy as a web service
- **DigitalOcean**: Use App Platform
- **Self-hosting**: Run on any server with `streamlit run app.py`

## Support

For issues and questions:
- Create an issue on GitHub
- Check the troubleshooting section above
- Review Streamlit documentation for deployment guidance

---

**Pinterest Factory** - Streamlining Pinterest content creation for food bloggers and content creators.
