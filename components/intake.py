"""

components/intake.py — Tab 1: Batch Intake

Dynamic form for entering 5–10 recipes. Saves to st.session_state on lock.

"""



import streamlit as st

from utils.web_scraper import scrape_recipes_from_website_with_memory, validate_url



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

        

        # Scrape button

        if st.button("🔍 Scrape Recipes", disabled=not website_url):

            if validate_url(website_url):

                with st.spinner("Scraping recipes from website..."):

                    scraped_recipes = scrape_recipes_from_website_with_memory(website_url, max_recipes=30)

                    

                    if scraped_recipes:

                        st.success(f"Found {len(scraped_recipes)} recipes!")

                        # Keep scraper open to show results

                        st.session_state.show_scraper = True

                        

                        # Store scraped recipes in session state

                        st.session_state.scraped_recipes = scraped_recipes

                        st.rerun()  # Rerun to display results outside the button block

                    else:

                        st.error("No recipes found. Please check the URL and try again.")

            else:

                st.error("Please enter a valid URL.")

        

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

        st.button("🗑 Clear batch", use_container_width=True, on_click=clear_batch)



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

            use_container_width=True,

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

        st.dataframe(preview_df, use_container_width=True, hide_index=True)

