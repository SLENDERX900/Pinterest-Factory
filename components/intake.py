"""
components/intake.py — Tab 1: Batch Intake
Dynamic form for entering 5–10 recipes. Saves to st.session_state on lock.
"""

import streamlit as st

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

EXAMPLE_RECIPES = [
    {"name": "Beef Chili", "url": "https://example.com/recipes/beef-chili", "time": "1 hr", "ingredients": "10", "benefit": "High Protein"},
    {"name": "Stovetop Mac and Cheese", "url": "https://example.com/recipes/mac-and-cheese", "time": "20 mins", "ingredients": "6", "benefit": "Quick Weeknight"},
    {"name": "Thai Basil Chicken", "url": "https://example.com/recipes/thai-basil-chicken", "time": "15 mins", "ingredients": "8", "benefit": "Quick Weeknight"},
    {"name": "French Onion Soup", "url": "https://example.com/recipes/french-onion-soup", "time": "1 hr 25 mins", "ingredients": "7", "benefit": "Date Night"},
    {"name": "Korean Cucumber Kimchi", "url": "https://example.com/recipes/korean-cucumber-kimchi", "time": "10 mins", "ingredients": "5", "benefit": "Vegan"},
    {"name": "Black Bean Tacos", "url": "https://example.com/recipes/black-bean-tacos", "time": "15 mins", "ingredients": "7", "benefit": "Budget Friendly"},
    {"name": "Garlic Butter Pasta", "url": "https://example.com/recipes/garlic-butter-pasta", "time": "15 mins", "ingredients": "5", "benefit": "Quick Weeknight"},
    {"name": "Overnight Oats", "url": "https://example.com/recipes/overnight-oats", "time": "5 mins", "ingredients": "4", "benefit": "Meal Prep"},
    {"name": "Butter Chicken", "url": "https://example.com/recipes/butter-chicken", "time": "40 mins", "ingredients": "12", "benefit": "Comfort Food"},
    {"name": "Roasted Tomato Soup", "url": "https://example.com/recipes/roasted-tomato-soup", "time": "50 mins", "ingredients": "7", "benefit": "Vegetarian"},
    {"name": "Crispy Chicken Thighs", "url": "https://example.com/recipes/crispy-chicken-thighs", "time": "40 mins", "ingredients": "5", "benefit": "High Protein"},
    {"name": "Greek Salad", "url": "https://example.com/recipes/greek-salad", "time": "10 mins", "ingredients": "7", "benefit": "Healthy"},
    {"name": "Banana Bread", "url": "https://example.com/recipes/banana-bread", "time": "1 hr 5 mins", "ingredients": "8", "benefit": "Comfort Food"},
    {"name": "Pad Thai", "url": "https://example.com/recipes/pad-thai", "time": "25 mins", "ingredients": "10", "benefit": "Quick Weeknight"},
    {"name": "Chicken Tortilla Soup", "url": "https://example.com/recipes/chicken-tortilla-soup", "time": "35 mins", "ingredients": "11", "benefit": "Comfort Food"},
    {"name": "Honey Garlic Shrimp", "url": "https://example.com/recipes/honey-garlic-shrimp", "time": "12 mins", "ingredients": "6", "benefit": "Quick Weeknight"},
    {"name": "Cucumber Salad", "url": "https://example.com/recipes/cucumber-salad", "time": "10 mins", "ingredients": "5", "benefit": "Vegan"},
    {"name": "Peanut Noodles", "url": "https://example.com/recipes/peanut-noodles", "time": "18 mins", "ingredients": "8", "benefit": "Vegan"},
    {"name": "Shakshuka", "url": "https://example.com/recipes/shakshuka", "time": "25 mins", "ingredients": "8", "benefit": "One Pan"},
    {"name": "Miso Salmon", "url": "https://example.com/recipes/miso-salmon", "time": "17 mins", "ingredients": "5", "benefit": "High Protein"},
    {"name": "Sesame Edamame", "url": "https://example.com/recipes/sesame-edamame", "time": "7 mins", "ingredients": "4", "benefit": "Healthy"},
    {"name": "Chocolate Mug Cake", "url": "https://example.com/recipes/chocolate-mug-cake", "time": "3 mins", "ingredients": "6", "benefit": "Quick Weeknight"},
]


def render_intake():
    st.subheader("Batch Intake")
    st.caption("Add 5–10 recipes. Lock the batch when ready, then head to the AI Copy Engine.")

    # Initialize session state variables
    if "num_recipes" not in st.session_state:
        st.session_state.num_recipes = 5
    if "recipe_data" not in st.session_state:
        st.session_state.recipe_data = []

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

    # Quick-load from example recipes
    with st.expander("⚡ Quick-load from example recipes (22 recipes)", expanded=False):
        st.caption("Select recipes to pre-fill the form instantly.")

        # Filter by benefit
        benefits_available = sorted(set(r["benefit"] for r in EXAMPLE_RECIPES))
        selected_filter = st.multiselect(
            "Filter by tag",
            options=benefits_available,
            default=[],
            key="quick_filter",
        )

        filtered = (
            [r for r in EXAMPLE_RECIPES if r["benefit"] in selected_filter]
            if selected_filter else EXAMPLE_RECIPES
        )

        cols = st.columns(3)
        quick_selections = []
        for i, r in enumerate(filtered):
            col = cols[i % 3]
            if col.checkbox(f"{r['name']} · {r['time']}", key=f"ql_{r['name']}"):
                quick_selections.append(r)

        st.button("Load selected into batch", disabled=len(quick_selections) == 0, on_click=load_selected, args=(quick_selections,))

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
