# Pinterest Factory

A Streamlit-powered dashboard for batch production of Pinterest pins from recipe content. This tool automates the creation of compelling pin titles, descriptions, and visual content for nobscooking.com recipes.

## Features

- **Batch Intake**: Import 5-10 recipes with metadata (URL, cooking time, ingredients, benefits)
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
   - Select 5-10 recipes from the pre-populated nobscooking.com list
   - Add custom recipes if needed
   - Lock the batch to proceed

   **Step 2: AI Copy Engine**
   - Generate multiple hook angles for each recipe
   - Create compelling descriptions
   - Review and edit AI-generated content

   **Step 3: Pin Generation**
   - Generate visual pins using custom templates
   - Customize typography and layout
   - Export pin images

   **Step 4: Notion Sync**
   - Export all generated content to Notion
   - Track production status
   - Manage content calendar

## Features in Detail

### Recipe Management
- Pre-populated with 20+ nobscooking.com recipes
- Custom recipe entry with URL validation
- Benefit categorization (Quick Weeknight, High Protein, Budget Friendly, etc.)
- Batch locking to prevent accidental changes

### AI-Powered Copy Generation
- Multiple hook angles per recipe (5-7 variations)
- Compelling descriptions optimized for Pinterest
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

### Adding New Recipes
Edit `components/intake.py` to add new recipes to the `NOBSCOOKING_RECIPES` list:

```python
{"name": "Recipe Name", "url": "https://example.com/recipe-slug", "time": "XX mins", "ingredients": "X", "benefit": "Category"},
```

### Customizing Pin Templates
Replace `template.png` with your own design template. The system automatically overlays text based on the template dimensions.

### Extending AI Prompts
Modify the prompt templates in `components/ai_engine.py` to customize the generated content style and tone.

## Troubleshooting

### Ollama Connection Issues
- Ensure Ollama is running: `ollama serve`
- Check model availability: `ollama list`
- Verify host configuration in `.env`

### Notion Sync Problems
- Verify integration token is valid
- Ensure database is shared with the integration
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

## Support

For issues and questions:
- Create an issue on GitHub
- Contact the nobscooking.com team
- Check the troubleshooting section above

---

**Pinterest Factory** - Streamlining Pinterest content creation for food bloggers and content creators.
