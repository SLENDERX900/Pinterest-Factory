"""

components/intake.py — Tab 1: Batch Intake

Dynamic form for entering 5–10 recipes. Saves to st.session_state on lock.

"""



import streamlit as st

from utils.web_scraper import scrape_recipes_from_website_with_memory, validate_url


def clear_batch_data():
    """Clear all batch data from session state."""
    st.session_state.recipe_data = []
    st.session_state.recipes = []
    st.session_state.batch_locked = False
    st.session_state.ai_generated = False
    st.session_state.hooks = {}
    st.session_state.descriptions = {}
    st.session_state.scraped_recipes = []
    st.session_state.show_scraper = True
    st.success("✅ Batch cleared! All data has been reset.")



BENEFITS = [

    "Quick Weeknight",

    "High Protein",

    "Budget Friendly",

    "No Oven",

    "One Pan",

    "Meal Prep",

    "Vegan",

    "Vegetarian",

    "Comfort Food",

    "Date Night",

    "Healthy",

    "Spicy",

    "Custom...",

]



# Web scraping will populate recipes dynamically





def render_intake():

    st.subheader("Batch Intake")

    st.caption("Add 5–10 recipes. Lock the batch when ready, then head to the AI Copy Engine.")



    # Initialize session state variables

    if "num_recipes" not in st.session_state:

        st.session_state.num_recipes = 5

    if "recipe_data" not in st.session_state:

        st.session_state.recipe_data = []

    if "show_scraper" not in st.session_state:

        st.session_state.show_scraper = True



    # Callback for Clear batch button

    def clear_batch():

        st.session_state.recipe_data = []

        st.session_state.recipes = []

        st.session_state.hooks = {}

        st.session_state.descriptions = {}

        st.session_state.ai_generated = False

        st.session_state.batch_locked = False

        st.session_state.num_recipes = 5



    # Callback for Load button - directly sets widget session state keys

    def load_selected(selections):

        # Clear all form widget keys up to max possible (10)

        for i in range(10):

            for key_suffix in ["name_", "url_", "time_", "ing_", "benefit_sel_", "benefit_custom_"]:

                key = f"{key_suffix}{i}"

                if key in st.session_state:

                    del st.session_state[key]



        # Directly set widget keys for each selected recipe

        for i, recipe in enumerate(selections):

            st.session_state[f"name_{i}"] = recipe["name"]

            st.session_state[f"url_{i}"] = recipe["url"]

            st.session_state[f"time_{i}"] = recipe["time"]

            st.session_state[f"ing_{i}"] = recipe["ingredients"]

            st.session_state[f"benefit_sel_{i}"] = recipe["benefit"]



        # Store selected recipes and update count

        st.session_state.recipe_data = selections.copy()

        st.session_state.num_recipes = len(selections)

        st.session_state.batch_locked = False

        st.session_state.ai_generated = False

        st.success(f"Loaded {len(selections)} recipe(s) into the form.")

        # Collapse scraper after loading

        st.session_state.show_scraper = False

        

        # Show nutrition facts for selected recipes

        if any('nutrition_facts' in r for r in selections):

            with st.expander("🥊 Nutrition Facts", expanded=False):

                st.caption("Nutrition information extracted from recipe pages.")

                

                for recipe in selections:

                    if 'nutrition_facts' in recipe and recipe['nutrition_facts']:

                        col1, col2, col3 = st.columns(3)

                        

                        with col1:

                            st.markdown(f"**{recipe['name']}**")

                        

                        with col2:

                            if recipe['nutrition_facts'].get('calories'):

                                st.metric("Calories", recipe['nutrition_facts']['calories'])

                            if recipe['nutrition_facts'].get('protein'):

                                st.metric("Protein (g)", recipe['nutrition_facts']['protein'])

                            if recipe['nutrition_facts'].get('carbs'):

                                st.metric("Carbs (g)", recipe['nutrition_facts']['carbs'])

                            if recipe['nutrition_facts'].get('fat'):

                                st.metric("Fat (g)", recipe['nutrition_facts']['fat'])

                        

                        with col3:

                            st.markdown("**Nutrition Highlights**")

                            highlights = []

                            

                            # Generate highlights based on nutrition data

                            if recipe['nutrition_facts'].get('calories'):

                                calories = int(recipe['nutrition_facts']['calories'])

                                if calories < 300:

                                    highlights.append("🥗 Low calorie (< 300 cal)")

                                elif calories < 500:

                                    highlights.append("⚖️ Moderate calorie (300-500 cal)")

                                else:

                                    highlights.append("🔥 High calorie (> 500 cal)")

                            

                            if recipe['nutrition_facts'].get('protein') and int(recipe['nutrition_facts']['protein']) > 20:

                                highlights.append("💪 High protein (> 20g)")

                            if recipe['nutrition_facts'].get('carbs') and int(recipe['nutrition_facts']['carbs']) < 15:

                                highlights.append("🌾 Low carb (< 15g)")

                            

                            for highlight in highlights:

                                st.markdown(f"• {highlight}")

                        

                        st.divider()



    # Web scraping interface - collapse after loading recipes

    scraper_expanded = st.session_state.get("show_scraper", True)

    with st.expander("🌐 Scrape Recipes from Website", expanded=scraper_expanded):

        st.caption("Enter your food blog URL to automatically extract recipe information.")

        

        # Website URL input

        website_url = st.text_input(

            "Website URL",

            placeholder="https://yourfoodblog.com",

            help="Enter the main URL of your food blog or recipe website"

        )

        

        # Smart scraping options
        from utils.sitemap_memory import get_processed_count, get_all_processed_urls
        
        # Show current memory status
        memory_count = get_processed_count()
        if memory_count > 0:
            st.info(f"📝 **Memory Status:** {memory_count} URLs already processed. Smart scraping will only update new or changed recipes.")
        
        # Scrape buttons
        col_smart, col_force, col_memory, col_clear = st.columns([2, 1, 1, 1])
        
        with col_smart:
            if st.button("🧠 Smart Scrape", disabled=not website_url, width='stretch', help="Only scrape new/updated recipes"):
                smart_scrape_website(website_url)
        
        with col_force:
            if st.button("🔄 Force Scrape", disabled=not website_url, width='stretch', help="Re-scrape all recipes"):
                force_scrape_website(website_url)
        
        with col_memory:
            if st.button("📋 Load Memory", width='stretch', help="Load recipes from current session"):
                load_from_memory()
        
        with col_clear:
            if st.button("🗑️ Clear Memory", help="Clear scraper memory to re-scrape all URLs", width='stretch'):
                from utils.sitemap_memory import clear_all_urls
                try:
                    clear_all_urls()
                    st.success("Scraper memory cleared! You can now re-scrape all URLs.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to clear memory: {str(e)}")


def smart_scrape_website(website_url: str):
    """Smart scraping that only processes new or changed recipes."""
    if not validate_url(website_url):
        st.error("Please enter a valid URL.")
        return
    
    with st.spinner("Smart scraping recipes..."):
        try:
            # Get existing recipes from session state
            existing_recipes = {r.get('url'): r for r in st.session_state.get('recipes', [])}
            
            # Get all URLs that would be scraped
            from utils.web_scraper import get_all_recipe_urls
            all_urls = get_all_recipe_urls(website_url, max_urls=30)
            
            # Find new URLs (not in memory) and existing URLs to re-check
            from utils.sitemap_memory import has_url
            new_urls = [url for url in all_urls if not has_url(url)]
            existing_urls = [url for url in all_urls if has_url(url)]
            
            st.info(f"🔍 Found {len(new_urls)} new recipes + {len(existing_urls)} existing recipes")
            
            # Scrape new recipes
            new_recipes = []
            if new_urls:
                st.info(f"📥 Processing {len(new_urls)} new recipes...")
                from utils.web_scraper import scrape_recipes_from_urls
                new_recipes = scrape_recipes_from_urls(new_urls)
            
            # Show existing recipes from memory for selection
            if existing_urls:
                st.info(f"📋 Found {len(existing_urls)} recipes in memory. Select which ones to load:")
                
                # Get recipes that are already in session state (previously scraped)
                current_recipes = {r.get('url'): r for r in st.session_state.get('recipes', [])}
                
                # Show recipes already available in session
                available_recipes = []
                for url in existing_urls:
                    if url in current_recipes:
                        available_recipes.append(current_recipes[url])
                
                if available_recipes:
                    st.subheader("📋 Select Recipes to Load from Memory")
                    
                    # Show available recipes with selection checkboxes
                    selected_existing = []
                    for i, recipe in enumerate(available_recipes):
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            # Create a unique key for each checkbox
                            checkbox_key = f"select_memory_{i}_{hash(recipe.get('url', '')) % 10000}"
                            selected = st.checkbox(
                                f"**{recipe.get('name', 'Unknown Recipe')}** - {recipe.get('time', 'No time')}",
                                key=checkbox_key,
                                help=f"URL: {recipe.get('url', 'No URL')}"
                            )
                            if selected:
                                selected_existing.append(recipe)
                        with col2:
                            st.write(f"📌 {recipe.get('benefit', 'No benefit')}")
                    
                    # Load selected recipes into scraped_recipes for normal selection flow
                    if selected_existing:
                        if st.button(f"📥 Load {len(selected_existing)} Selected Recipes", type="primary"):
                            st.session_state.scraped_recipes = selected_existing
                            st.session_state.show_scraper = True
                            st.success(f"✅ Ready to load {len(selected_existing)} recipes into batch!")
                            st.rerun()
                else:
                    st.warning("No recipes found in current session. Try scraping first or use Force Scrape.")
                
                # Combine with any new recipes found
                all_recipes = new_recipes + available_recipes
            else:
                all_recipes = new_recipes
                
            if all_recipes:
                st.success(f"✅ Total recipes available: {len(all_recipes)}")
            
            if all_recipes:
                # Add to scraped_recipes for the normal selection interface
                st.session_state.scraped_recipes = all_recipes
                st.session_state.show_scraper = True
                
                current_batch = st.session_state.get('recipes', [])
                if current_batch:
                    st.info(f"✅ Found {len(all_recipes)} recipes! You can select which ones to add to your current batch of {len(current_batch)} recipes.")
                else:
                    st.info(f"✅ Found {len(all_recipes)} recipes! Select which ones to add to your batch.")
                
                st.rerun()
            else:
                st.warning("No recipes found in memory. Try scraping first or use Force Scrape.")
                
        except Exception as e:
            st.error(f"Smart scraping failed: {str(e)}")
            with st.expander("Debug details"):
                st.code(traceback.format_exc())


def load_from_memory():
    """Load recipes from current session state for selection."""
    current_recipes = st.session_state.get('recipes', [])
    
    if not current_recipes:
        st.warning("No recipes found in current session. Try scraping some recipes first.")
        return
    
    st.info(f"📋 Found {len(current_recipes)} recipes in current session. Select which ones to load:")
    
    # Show recipes with selection checkboxes
    selected_recipes = []
    for i, recipe in enumerate(current_recipes):
        col1, col2 = st.columns([4, 1])
        with col1:
            checkbox_key = f"load_memory_{i}_{hash(recipe.get('url', '')) % 10000}"
            selected = st.checkbox(
                f"**{recipe.get('name', 'Unknown Recipe')}** - {recipe.get('time', 'No time')}",
                key=checkbox_key,
                help=f"URL: {recipe.get('url', 'No URL')}"
            )
            if selected:
                selected_recipes.append(recipe)
        with col2:
            st.write(f"📌 {recipe.get('benefit', 'No benefit')}")
    
    # Load selected recipes
    if selected_recipes:
        if st.button(f"📥 Load {len(selected_recipes)} Selected Recipes", type="primary"):
            st.session_state.scraped_recipes = selected_recipes
            st.session_state.show_scraper = True
            st.success(f"✅ Ready to load {len(selected_recipes)} recipes into batch!")
            st.rerun()


def force_scrape_website(website_url: str):
    """Force scraping of all recipes (clears memory first)."""
    if not validate_url(website_url):
        st.error("Please enter a valid URL.")
        return
    
    with st.spinner("Force scraping all recipes..."):
        try:
            # Clear memory for this site
            from utils.sitemap_memory import get_all_processed_urls, clear_url
            from utils.web_scraper import get_all_recipe_urls
            
            all_urls = get_all_recipe_urls(website_url, max_urls=30)
            cleared_count = 0
            for url in all_urls:
                if clear_url(url):
                    cleared_count += 1
            
            st.info(f"🗑️ Cleared {cleared_count} URLs from memory")
            
            # Now scrape all URLs
            scraped_recipes = scrape_recipes_from_website_with_memory(website_url, max_recipes=30)
            
            if scraped_recipes:
                st.success(f"✅ Force scraped {len(scraped_recipes)} recipes!")
                st.session_state.scraped_recipes = scraped_recipes
                st.session_state.show_scraper = True
                st.rerun()
            else:
                st.error("No recipes found. Please check the URL and try again.")
                
        except Exception as e:
            st.error(f"Force scraping failed: {str(e)}")
            with st.expander("Debug details"):
                st.code(traceback.format_exc())

        # Display scraped recipes OUTSIDE the button block - persists across reruns

        if "scraped_recipes" in st.session_state and st.session_state.scraped_recipes:

            scraped_recipes = st.session_state.scraped_recipes

            

            st.subheader("Scraped Recipes")

            

            # Create selection options from all scraped recipes

            recipe_options = {}

            for r in scraped_recipes:

                time_display = r.get('time', '')

                if r.get('prep_time') and r.get('cook_time'):

                    time_display = f"Prep: {r['prep_time']}, Cook: {r['cook_time']}"

                elif r.get('total_time'):

                    time_display = r['total_time']

                label = f"{r['name']} · {time_display}"

                recipe_options[label] = r

            

            # Multiselect for recipe selection

            selected_labels = st.multiselect(

                "Select recipes to load",

                options=list(recipe_options.keys()),

                key="recipe_multiselect"

            )

            

            quick_selections = [recipe_options[label] for label in selected_labels]

            selected_count = len(quick_selections)

            

            st.write(f"**{selected_count} recipes selected**")

            

            if st.button(

                "Load selected into batch",

                disabled=selected_count == 0,

                key="load_scraped_btn"

            ):

                load_selected(quick_selections)

                # Clear scraped recipes to hide this section

                st.session_state.scraped_recipes = []

                st.session_state.show_scraper = False

                st.rerun()

    

    st.divider()



    # How many recipe slots - slider tied to session state

    col_a, col_b = st.columns([2, 1])

    with col_a:

        st.slider(

            "Number of recipes in this batch",

            min_value=1,

            max_value=10,

            step=1,

            key="num_recipes",

        )



    with col_b:

        if st.button("🗑 Clear batch", width='stretch'):
            clear_batch_data()



    st.divider()



    # Recipe entry forms

    form_data = []

    for i in range(st.session_state.num_recipes):

        with st.container():

            st.markdown(f"**Recipe {i + 1}**")

            c1, c2 = st.columns([2, 2])

            c3, c4, c5 = st.columns([1, 1, 2])



            name = c1.text_input(

                "Recipe name",

                key=f"name_{i}",

                placeholder="e.g. Garlic Butter Pasta",

            )

            url = c2.text_input(

                "URL (optional)",

                key=f"url_{i}",

                placeholder="https://nobscooking.com/recipes/...",

            )

            time = c3.text_input(

                "Cook time",

                key=f"time_{i}",

                placeholder="15 mins",

            )

            ingredients = c4.text_input(

                "Ingredient count",

                key=f"ing_{i}",

                placeholder="5",

            )



            # Benefit selector — handle custom

            benefit_opts = BENEFITS

            benefit_sel = c5.selectbox(

                "Key benefit / tag",

                options=benefit_opts,

                index=0,

                key=f"benefit_sel_{i}",

            )

            if benefit_sel == "Custom...":

                benefit = c5.text_input(

                    "Enter custom tag",

                    key=f"benefit_custom_{i}",

                )

            else:

                benefit = benefit_sel



            form_data.append({

                "name": name.strip(),

                "url": url.strip(),

                "time": time.strip(),

                "ingredients": ingredients.strip(),

                "benefit": benefit.strip(),

            })



            if i < st.session_state.num_recipes - 1:

                st.divider()



    # Lock batch button

    st.divider()

    col_lock, col_status = st.columns([1, 3])



    with col_lock:

        lock_clicked = st.button(

            "🔒 Lock Batch",

            type="primary",

            width='stretch',

        )



    if lock_clicked:

        valid = [r for r in form_data if r["name"]]

        if len(valid) < 1:

            st.error("Add at least 1 recipe name before locking.")

        else:

            st.session_state.recipes = valid

            st.session_state.recipe_data = form_data

            st.session_state.batch_locked = True

            st.session_state.ai_generated = False

            st.session_state.hooks = {}

            st.session_state.descriptions = {}

            with col_status:

                st.success(f"✅ Batch locked — {len(valid)} recipe(s) ready for AI generation.")



    if st.session_state.batch_locked and st.session_state.recipes:

        with col_status:

            st.info(

                f"Batch locked with **{len(st.session_state.recipes)}** recipes. "

                "Head to **Step 2 → AI Copy Engine** to generate hooks."

            )



        st.subheader("Locked batch preview")

        import pandas as pd

        preview_df = pd.DataFrame(st.session_state.recipes)[

            ["name", "time", "ingredients", "benefit", "url"]

        ]

        preview_df.columns = ["Recipe", "Cook Time", "Ingredients", "Benefit", "URL"]

        st.dataframe(preview_df, width='stretch', hide_index=True)

