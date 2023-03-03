import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

from utils import *
import streamlit.components.v1 as components
md = st.markdown

st.set_page_config(
    page_title = "Git Scale",
    layout="wide",
    page_icon = "📊"
    )

st.title("Git Scale")

@st.cache_data
def cached_content(url):
    return get_repo_content(url)

@st.cache_data
def cached_analyze(path):
    return analyze(path)

with st.sidebar:
    st.header("Search")
    user_search = st.text_input("Search for a GitHub user", value = "ds-modules")
    result = find_user(user_search)
    if isinstance(result, list):
        if result == []:
            st.error("No results found, please try another search term")
        else:
            user = st.selectbox("Select a user", options = result)
            repos = get_user_repo_names(user)
            st.selectbox("Select a repository", options = repos)
    else:
        user = result
        repos = get_user_repo_names(user)
        st.selectbox("Select a repository", options = repos)
        
        
        
md("## A lightweight tool for visualizing the size of any public GitHub repository")
md("> ### Created by [Jonathan Ferrari](https://github.jonathanferrari.com)")

md("Enter a GitHub repository URL below to get started, or use the search function to find a repository")

url = st.text_input("Enter a GitHub repository URL:", placeholder="https://github.com/example-user/example-repo", value = "https://github.com/ds-modules/data-4ac")

def color_top_row(row):
    color = "transparent"
    if row.name == "Total":
        color = "#f0f0f0"
    return [f"background-color: {color}"] * len(row)

def index_color(column):
    color = "transparent"
    if column.name == "Total":
        color = "#f0f0f0"
    return [f"background-color: {color}"] * len(column)

if url:
    col1, col2 = st.columns(2)
    path = get_repo_path(url) 
    content = cached_content(url = url)
    with col2:
        files = [content['path'] for content in content if content['type'] == 'blob']
        size = convert_bytes(sum([content['size'] for content in content if content['type'] == 'blob']))
        md(f"## Repository Size: {size}")
        df = cached_analyze(path)
        st.dataframe(df[["Files", "Size"]].style.apply(color_top_row, axis=1).apply(index_color, axis=0), use_container_width=True, height=700)
    with col1:
        type_df = df.copy().drop(index="Total")
        fig = px.pie(type_df, values='Bytes', names=type_df.index, title=f'File Type Distribution of {path}', hover_data=["Size"],
                     template = "seaborn", height = 800)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig)
        
    md("## Repository Readme:")
    md("<hr style='line-height:0px;border: 3px solid #003262'/>", unsafe_allow_html=True)
    md("<hr style='line-height:0px;border: 3px solid #E2C258'/>", unsafe_allow_html=True)
    md(get_readme(path))
    
# bold the first row of the dataframe and highlight the index column with blue
