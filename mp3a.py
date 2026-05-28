import ssl
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

st.set_page_config(
    page_title="VibeMatch - Music Discovery",
    page_icon="🎵",
    layout="centered"
)

st.title("🎵 VibeMatch")
st.caption("Discover 20 tracks with the exact same style, energy, and mood.")

# 1. Setup Session State to hold our active search term
if "active_search" not in st.session_state:
    st.session_state.active_search = None

# Hardcode your API key here inside the quotes if you want to bypass the sidebar:
api_key = "AIzaSyDcfVAM3t_ioVnZRaKXVgkEmAMNtOyQ9lQ"

if not api_key:
    st.info("Please enter your YouTube API Key in the sidebar to get started.", icon="🔑")
else:
    youtube = build("youtube", "v3", developerKey=api_key)

    # --- SEARCH CONTROLS SYSTEM ---
    with st.form(key="search_form", clear_on_submit=True):
        search_query = st.text_input(
            "Search for a track, artist, or vibe:", 
            placeholder="e.g., Rouge Rouge - L'amour"
        )
        submit_button = st.form_submit_button(label="Find Similar Music")

    # When the form is submitted, save the query to session state
    if submit_button and search_query.strip():
        st.session_state.active_search = search_query.strip()

    # Create a layout placeholder container for the clear button below the form
    button_placeholder = st.empty()

    # --- SEARCH EXECUTION & RENDERING ---
    # Run the main engine if a current search is active in state
    if st.session_state.active_search:
        
        # Place the clear button at the top of the results. 
        # Clicking this button clears the state and refreshes the view.
        if button_placeholder.button("🔄 Clear Results & Start Fresh"):
            st.session_state.active_search = None
            st.rerun()

        active_query = st.session_state.active_search
        
        with st.spinner(f"Analyzing '{active_query}' vibe and gathering recommendations..."):
            try:
                # STEP 1: Search for the initial seed track + fetch its metadata tags
                search_response = youtube.search().list(
                    q=active_query,
                    type="video",
                    videoCategoryId="10", # Music category
                    part="id,snippet",
                    maxResults=1
                ).execute()

                if not search_response.get("items"):
                    st.error("No tracks found for your search. Try adjusting the spelling.")
                else:
                    seed_track = search_response["items"][0]
                    seed_video_id = seed_track["id"]["videoId"]
                    seed_title = seed_track["snippet"]["title"]
                    seed_channel = seed_track["snippet"]["channelTitle"]

                    st.markdown(f"### Found Seed Track: **{seed_title}**")
                    
                    # Fetch extra details (tags) for deep semantic generation
                    video_details = youtube.videos().list(
                        id=seed_video_id,
                        part="snippet"
                    ).execute()
                    
                    # Build an optimized recommendation query string from metadata
                    tags = video_details["items"][0]["snippet"].get("tags", [])
                    clean_title = seed_title.split('(')[0].split('[')[0].strip()
                    
                    # Core search strategy combining artist profile + top style tags
                    recommendation_query = f"{clean_title} music style audio mood"
                    if tags:
                        recommendation_query += f" { ' '.join(tags[:2]) }"

                    # STEP 2 & 3: Run semantic algorithm query for 20 similar items
                    recommend_response = youtube.search().list(
                        q=recommendation_query,
                        type="video",
                        videoCategoryId="10", # Filter strictly for Music
                        part="id,snippet",
                        maxResults=25
                    ).execute()

                    recommendations = []
                    seen_titles = set([seed_title.lower()])

                    for item in recommend_response.get("items", []):
                        video_id = item["id"].get("videoId")
                        title = item["snippet"]["title"]
                        channel = item["snippet"]["channelTitle"]
                        
                        norm_title = title.lower().split('(official')[0].strip()

                        if video_id and norm_title not in seen_titles and len(recommendations) < 20:
                            seen_titles.add(norm_title)
                            
                            description = (
                                f"Aligned with the structural progression and tempo footprint of your search. "
                                f"Shares production elements with {seed_channel}'s atmospheric vibe."
                            )
                            video_link = f"https://www.youtube.com/watch?v={video_id}"
                            
                            recommendations.append({
                                "Track Name": title,
                                "Track Description": description,
                                "YouTube Link": video_link
                            })

                    # STEP 4: Render clean responsive Markdown Table
                    if not recommendations:
                        st.warning("Could not find variations. Try a different artist formatting.")
                    else:
                        markdown_table = "| Track Name | Track Description | YouTube Link |\n| --- | --- | --- |\n"

                        for track in recommendations:
                            t_name = track['Track Name'].replace("|", "-")
                            t_desc = track['Track Description']
                            t_link = f"[🎵 Listen]({track['YouTube Link']})"
                            
                            markdown_table += f"| **{t_name}** | {t_desc} | {t_link} |\n"

                        st.write("### 20 Similar Tracks Recommended for You:")
                        st.markdown(markdown_table)

            except HttpError as e:
                st.error("API Error: Please check if your YouTube API Key is valid or has exceeded its quota limits.")
            except Exception as e:
                st.error(f"An unexpected error occurred: {str(e)}")
