import streamlit as st
from src.models.grading import grade_answer
from src.models.content import summarize, diagram_prompt, qa_over_content, adaptation_suggestions
from src.models.recommend import recommend_modules
from src.models.analytics import compute_analytics
import altair as alt
import pandas as pd

# Simple translation dictionary
T = {
    'en': {
        'grading': "AI-Powered Grading System",
        'grading_desc': "Enter a question, reference answer, and your answer. Get instant grading and feedback.",
        'question': "Question",
        'reference': "Reference Answer",
        'your_answer': "Your Answer",
        'grade_btn': "Grade Answer",
        'score': "Score",
        'feedback': "Feedback",
        'content': "Intelligent Course Content Management",
        'content_desc': "Summarize, visualize, and adapt lesson content. Try with your own text!",
        'lesson_text': "Lesson Text",
        'summarize_btn': "Summarize Lesson",
        'summary': "Summary",
        'bullets': "Bullets",
        'diagram_btn': "Generate Diagram Prompt",
        'diagram': "Diagram Prompt",
        'qa': "Bilingual Q&A Assistant",
        'qa_input': "Ask a question about the course content:",
        'qa_btn': "Ask Q&A",
        'answer': "Answer",
        'source': "Source",
        'adapt': "Content Adaptation Suggestions (VARK)",
        'adapt_btn': "Suggest Adaptations",
        'recommend': "Personalized Recommendation System",
        'recommend_desc': "Get learning module recommendations based on region, patient tags, and level.",
        'tags': "Patient Tags (comma-separated)",
        'level': "Level",
        'recommend_btn': "Recommend Modules",
        'next_steps': "Adaptive Next Steps:",
        'analytics': "Analytics Dashboard & Data Visualization",
        'analytics_desc': "View CHW engagement, progress, and regional comparisons for region:",
        'compute_analytics': "Compute Analytics",
        'daily_active': "Daily Active CHWs",
        'regional_scores': "Regional Average Scores",
        'region_stats': "Region Stats:",
        'weekly_active': "Weekly Active CHWs:",
        'avg_session': "Average Session Length (min):",
        'quiz_attempts': "Quiz Attempts:",
        'avg_score': "Average Score:",
        'completion': "Completion Rate:",
        'flagged': "Flagged CHWs (need training):"
    },
    'ki': {
        'grading': "Sisitemu yo Gusuzuma yifashishije AI",
        'grading_desc': "Andika ikibazo, igisubizo cy'icyitegererezo, n'igisubizo cyawe. Sangira amanota n'inama ako kanya.",
        'question': "Ikibazo",
        'reference': "Igisubizo cy'Icyitegererezo",
        'your_answer': "Igisubizo cyawe",
        'grade_btn': "Suzuma Igisubizo",
        'score': "Amanota",
        'feedback': "Inama",
        'content': "Gucunga Ibisobanuro by'Isomo hifashishijwe AI",
        'content_desc': "Sobanura, shushanya, kandi uhindure isomo. Gerageza inyandiko yawe!",
        'lesson_text': "Inyandiko y'Isomo",
        'summarize_btn': "Sobanura Isomo",
        'summary': "Ibisobanuro",
        'bullets': "Ingingo z'ingenzi",
        'diagram_btn': "Tegura Ishusho y'Isano",
        'diagram': "Ishusho y'Isano",
        'qa': "Umufasha wa Q&A w'Indimi ebyiri",
        'qa_input': "Baza ikibazo ku isomo:",
        'qa_btn': "Baza Q&A",
        'answer': "Igisubizo",
        'source': "Aho byakuwe",
        'adapt': "Inama zo Guhindura Isomo (VARK)",
        'adapt_btn': "Saba Inama",
        'recommend': "Sisitemu yo Gutanga Inama z'Isomo",
        'recommend_desc': "Bona inama z'isomo zishingiye ku karere, ibimenyetso by'umurwayi, n'urwego.",
        'tags': "Ibimenyetso by'umurwayi (byandikwe bitandukanyijwe na koma)",
        'level': "Urwego",
        'recommend_btn': "Saba Inama z'Isomo",
        'next_steps': "Intambwe zikurikiraho:",
        'analytics': "Dashboard y'Ibisobanuro n'Ishusho",
        'analytics_desc': "Reba uko abajyanama bakora, intambwe, n'itandukaniro ry'uturere kuri:",
        'compute_analytics': "Bara Ibisobanuro",
        'daily_active': "Abajyanama bakora buri munsi",
        'regional_scores': "Amanota y'Akarere",
        'region_stats': "Ibisobanuro by'Akarere:",
        'weekly_active': "Abajyanama bakora mu cyumweru:",
        'avg_session': "Igihe cy'Inyigisho (min):",
        'quiz_attempts': "Ibizamini Byakozwe:",
        'avg_score': "Amanota (Average):",
        'completion': "Abasoje (%):",
        'flagged': "Abajyanama bakeneye kongererwa ubumenyi:"
    }
}

st.set_page_config(page_title="CHW E-Learning AI Demo", layout="wide")

# Sidebar
st.sidebar.title("Settings")
language = st.sidebar.selectbox("Language", ["English", "Kinyarwanda"], index=0, key="lang")
region = st.sidebar.selectbox("Region", ["North", "South", "East", "West", "Kigali"], index=0, key="region")
lang = "en" if language == "English" else "ki"
if st.sidebar.button("Reset Seed"):
    st.session_state.clear()

# Tabs
tabs = st.tabs([T[lang]['grading'], T[lang]['content'], T[lang]['recommend'], T[lang]['analytics']])

with tabs[0]:
    st.header(T[lang]['grading'])
    st.write(T[lang]['grading_desc'])
    q = st.text_area(T[lang]['question'], key="grade_q")
    ref = st.text_area(T[lang]['reference'], key="grade_ref")
    user = st.text_area(T[lang]['your_answer'], key="grade_user")
    if st.button(T[lang]['grade_btn']):
        try:
            result = grade_answer(q, ref, user, lang)
            # Handle 0-5 scoring
            score = result['score_0_to_5']
            if score == 0:
                st.error(f"{T[lang]['score']}: {score} - Completely off-topic or no understanding")
            elif score <= 2:
                st.warning(f"{T[lang]['score']}: {score}")
            elif score <= 4:
                st.info(f"{T[lang]['score']}: {score}")
            else:
                st.success(f"{T[lang]['score']}: {score}")
            
            st.write(f"**{T[lang]['feedback']}:**")
            for s in result['suggestions']:
                st.write(f"- {s}")
        except Exception as e:
            st.error(f"Error grading answer: {e}")

with tabs[1]:
    st.header(T[lang]['content'])
    st.write(T[lang]['content_desc'])
    lesson = st.text_area(T[lang]['lesson_text'], key="lesson_text")
    if st.button(T[lang]['summarize_btn']):
        try:
            summ = summarize(lesson, lang)
            st.write(f"**{T[lang]['summary']}:**", summ['summary'])
            st.write(f"**{T[lang]['bullets']}:**", summ['bullets'])
        except Exception as e:
            st.error(f"Error summarizing: {e}")
    if st.button(T[lang]['diagram_btn']):
        try:
            diag = diagram_prompt(lesson, lang)
            st.write(f"**{T[lang]['diagram']}:**", diag['prompt'])
        except Exception as e:
            st.error(f"Error generating diagram prompt: {e}")
    st.write("---")
    st.subheader(T[lang]['qa'])
    q = st.text_input(T[lang]['qa_input'], key="qa_q")
    if st.button(T[lang]['qa_btn']):
        try:
            ans = qa_over_content(q, lang)
            st.write(f"**{T[lang]['answer']}:**", ans['answer'])
            if ans.get('source_title'):
                st.caption(f"**{T[lang]['source']}:** {ans['source_title']}")
                if ans.get('focus_area'):
                    st.caption(f"**Focus Area:** {ans['focus_area']}")
                if ans.get('confidence'):
                    st.caption(f"**Confidence:** {ans['confidence']}")
        except Exception as e:
            st.error(f"Error in Q&A: {e}")
    st.write("---")
    st.subheader(T[lang]['adapt'])
    if st.button(T[lang]['adapt_btn']):
        try:
            tips = adaptation_suggestions(lesson, lang)
            for style, tip in tips['suggestions'].items():
                st.write(f"**{style.title()}:** {tip[0]}")
        except Exception as e:
            st.error(f"Error suggesting adaptations: {e}")

with tabs[2]:
    st.header(T[lang]['recommend'])
    st.write(T[lang]['recommend_desc'])
    tags = st.text_input(T[lang]['tags'], key="rec_tags")
    level = st.selectbox(T[lang]['level'], ["basic", "advanced"], index=0, key="rec_level")
    if st.button(T[lang]['recommend_btn']):
        try:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
            rec = recommend_modules(region, tag_list, level)
            for m in rec['modules']:
                st.write(f"**{m['module']}** (Score: {m['score']})")
                for r in m['rationales']:
                    st.caption(f"- {r}")
            st.write(f"**{T[lang]['next_steps']}**", rec['next_steps'])
        except Exception as e:
            st.error(f"Error in recommendations: {e}")

with tabs[3]:
    st.header(T[lang]['analytics'])
    st.write(f"{T[lang]['analytics_desc']} {region}.")
    if st.button(T[lang]['compute_analytics']):
        try:
            data = compute_analytics()
            # Daily active chart
            daily_df = pd.DataFrame(list(data['daily_active'].items()), columns=['date', 'active_chws'])
            daily_df['date'] = pd.to_datetime(daily_df['date'])
            st.subheader(T[lang]['daily_active'])
            chart = alt.Chart(daily_df).mark_line(point=True).encode(
                x='date:T', y='active_chws:Q'
            ).properties(height=250)
            st.altair_chart(chart, use_container_width=True)
            # Regional comparison chart
            reg_df = pd.DataFrame(data['regional_comparison'])
            st.subheader(T[lang]['regional_scores'])
            bar = alt.Chart(reg_df).mark_bar().encode(
                x='region:N', y='avg_score:Q', color='region:N', tooltip=['region', 'avg_score']
            ).properties(height=250)
            st.altair_chart(bar, use_container_width=True)
            # Filtered region stats
            reg_row = reg_df[reg_df['region'] == region]
            if not reg_row.empty:
                st.write(f"**{region} {T[lang]['region_stats']}**")
                st.write(reg_row.T)
            st.write(f"**{T[lang]['weekly_active']} {data['weekly_active']}")
            st.write(f"**{T[lang]['avg_session']} {data['avg_session_length']}")
            st.write(f"**{T[lang]['quiz_attempts']} {data['quiz_attempts']}")
            st.write(f"**{T[lang]['avg_score']} {data['avg_score']}")
            st.write(f"**{T[lang]['completion']} {data['completion_rate']}")
            st.write(f"**{T[lang]['flagged']} {data['flagged_chws']}")
        except Exception as e:
            st.error(f"Error computing analytics: {e}")
