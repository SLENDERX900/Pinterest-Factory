"""
components/ai_engine.py — Tab 2: AI Copy Engine
Connects to Groq API, generates hooks + descriptions, renders editable text boxes.
All output is saved back to st.session_state so edits persist across tabs.
"""

import streamlit as st
from utils.groq_client import (
    check_connection,
    generate_hooks,
    generate_description,
    generate_hook_packages,
    ANGLES,
    GROQ_MODEL,
)
from utils.pinterest_trends import collect_trending_pins
from utils.rag_memory import store_trending_pins, query_similar_trends


def render_ai_engine():
    st.subheader("AI Copy Engine")
    st.caption("Generates 5 hooks + 1 SEO description per recipe using Groq API (Llama 3.1).")

    # ── Groq connection check ───────────────────────────────────────────────
    with st.container():
        col_status, col_model = st.columns([3, 1])
        with col_status:
            ok, msg = check_connection()
            if ok:
                st.success(f"✅ Groq connected · model: `{msg}`")
            else:
                st.error(f"❌ Groq API error — {msg}")
                st.code("# Add to .env file:\nGROQ_API_KEY=gsk_xxxxxxxxxxxx", language="bash")
                st.stop()
        with col_model:
            st.caption(f"Model: `{GROQ_MODEL}`")

    st.divider()

    # ── Guard: batch must be locked ───────────────────────────────────────────
    if not st.session_state.get("batch_locked") or not st.session_state.get("recipes"):
        st.warning("⚠️ No batch locked yet. Go to **Step 1 → Batch Intake** and lock your recipes first.")
        return

    recipes = st.session_state.recipes

    # ── Generation controls ───────────────────────────────────────────────────
    col_gen, col_regen, col_info = st.columns([1, 1, 3])

    with col_gen:
        generate_all = st.button(
            "🚀 Generate all hooks",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.ai_generated,
        )
    with col_regen:
        regenerate = st.button(
            "🔄 Re-generate all",
            use_container_width=True,
        )
    with col_info:
        st.caption(
            f"Will generate {len(recipes) * 5} hooks + {len(recipes)} descriptions "
            f"across {len(recipes)} recipe(s). Fast generation via Groq API."
        )

    if regenerate:
        st.session_state.hooks = {}
        st.session_state.descriptions = {}
        st.session_state.ai_generated = False
        st.rerun()

    # ── Main generation loop ──────────────────────────────────────────────────
    if generate_all or (regenerate and not st.session_state.ai_generated):
        progress = st.progress(0, text="Starting generation...")
        status_placeholder = st.empty()
        st.session_state.hook_packages = {}

        for idx, recipe in enumerate(recipes):
            name = recipe["name"]
            pct = int((idx / len(recipes)) * 100)
            progress.progress(pct, text=f"Generating: {name} ({idx + 1}/{len(recipes)})")
            status_placeholder.info(f"⏳ Processing **{name}**...")

            # Trend scrape + RAG memory
            trend_pins, trend_source = collect_trending_pins(recipe.get("url", recipe.get("name", "")), max_pins=10)
            store_trending_pins(trend_pins)
            rag_context = query_similar_trends(
                f"{recipe.get('name', '')} {recipe.get('benefit', '')} {recipe.get('time', '')}",
                top_k=5,
            )

            # Hooks + descriptions (JSON packages)
            try:
                packages = generate_hook_packages(recipe, trend_context=rag_context)
                hooks = generate_hooks(recipe, trend_context=rag_context)
                st.session_state.hook_packages[name] = packages
                # Clean hooks to remove conversational filler
                cleaned_hooks = {}
                for angle, hook_text in hooks.items():
                    # Remove common filler phrases
                    filler_phrases = [
                        'Here are the 5 Pinterest hooks:',
                        'Here are 5 Pinterest hooks:',
                        'Here are the hooks:',
                        'Here are hooks:',
                        'Pinterest hooks:',
                        'hooks:',
                        'Here are',
                        'Pinterest',
                        '1.', '2.', '3.', '4.', '5.',
                        '-', '*',
                    ]
                    cleaned = hook_text
                    for phrase in filler_phrases:
                        cleaned = cleaned.replace(phrase, '')
                        cleaned = cleaned.replace(phrase.capitalize(), '')
                        cleaned = cleaned.replace(phrase.upper(), '')
                    
                    # Filter lines
                    lines = cleaned.split('\n')
                    cleaned_lines = []
                    for line in lines:
                        line_lower = line.lower()
                        if not any(phrase in line_lower for phrase in ['here are', 'pinterest hooks', 'hooks:']):
                            cleaned_lines.append(line.strip())
                    
                    cleaned_lines = [line for line in cleaned_lines if line and len(line) > 3]
                    cleaned_hooks[angle] = cleaned_lines[0] if cleaned_lines else hook_text
                
                st.session_state.hooks[name] = cleaned_hooks
            except Exception as e:
                st.session_state.hooks[name] = {a: f"[Generation failed: {e}]" for a in ANGLES}
                st.session_state.hook_packages[name] = []

            # Description
            try:
                desc = generate_description(recipe, trend_context=rag_context)
                st.session_state.descriptions[name] = desc
            except Exception as e:
                st.session_state.descriptions[name] = f"[Description generation failed: {e}]"

        progress.progress(100, text="Generation complete!")
        status_placeholder.success(f"✅ Generated hooks and descriptions for {len(recipes)} recipe(s).")
        st.session_state.ai_generated = True
        st.rerun()

    # ── Display editable output ───────────────────────────────────────────────
    if not st.session_state.hooks:
        st.info("Click **Generate all hooks** above to start. You can edit any hook after generation.")
        return

    st.subheader("Edit hooks before exporting")
    st.caption("All changes are saved automatically. These exact texts will appear in the Canva CSV.")

    ANGLE_TIPS = {
        "Time-saver": "Lead with the time. Under 8 words.",
        "Lazy Dinner": "Effortless, minimal effort framing. Under 8 words.",
        "Weeknight Hero": "Busy/weeknight framing. Under 8 words.",
        "Ingredient-Count": "Lead with ingredient count. Under 8 words.",
        "Core Method": "Key technique or final result. Under 8 words.",
    }

    for recipe in recipes:
        name = recipe["name"]
        hooks = st.session_state.hooks.get(name, {})
        description = st.session_state.descriptions.get(name, "")

        with st.expander(f"**{name}** — {recipe.get('time', '')} · {recipe.get('benefit', '')}", expanded=True):

            # 5 hooks in a 2-column grid
            col_left, col_right = st.columns(2)
            cols = [col_left, col_right, col_left, col_right, col_left]

            for i, angle in enumerate(ANGLES):
                current = hooks.get(angle, "")
                new_val = cols[i].text_input(
                    label=f"**{angle}**",
                    value=current,
                    key=f"hook_{name}_{angle}",
                    help=ANGLE_TIPS.get(angle, ""),
                    max_chars=60,
                )
                # Word count warning
                word_count = len(new_val.split())
                if word_count > 8:
                    cols[i].caption(f"⚠️ {word_count} words — aim for 8 or fewer")
                else:
                    cols[i].caption(f"{word_count} words ✓" if new_val else "")

                # Save edit back to state
                if new_val != current:
                    st.session_state.hooks[name][angle] = new_val

            st.divider()

            # Description field
            new_desc = st.text_area(
                "SEO description (copy-paste into Pinterest)",
                value=description,
                key=f"desc_{name}",
                height=80,
                max_chars=500,
                help="Formula: [Keyword] + [benefit] + [use case]",
            )
            char_count = len(new_desc)
            if char_count > 150:
                st.caption(f"⚠️ {char_count} chars — Pinterest shows ~150 in preview")
            else:
                st.caption(f"{char_count}/150 chars")

            if new_desc != description:
                st.session_state.descriptions[name] = new_desc

            # URL quick-link
            if recipe.get("url"):
                st.caption(f"🔗 [{recipe['url']}]({recipe['url']})")

    st.divider()
    st.info("✅ All edits saved. Head to **Step 3 → Generate Pins** to preview and download your images.")
