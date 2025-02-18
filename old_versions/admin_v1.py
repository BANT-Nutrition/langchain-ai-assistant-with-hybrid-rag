#!/usr/bin/env python

"""
Web interface to:
1. crawl/scrape web pages
2. embed data
"""

import requests, json
from bs4 import BeautifulSoup
from modules.scrape_web_page_v1 import scrape_web_page
import streamlit as st

def scrape_commons_category(category):
    """
    METHOD 3: For Commons: Scrape the URLs from a Commons Category and save the results in a JSON file
    """
    
    FILE_PATH = "./files/commons-"

    #category = "Category:Prince_Philippe,_Count_of_Flanders_in_photographs"

    items = []
    href_old = ""

    # Step 1: Load the HTML content from a webpage
    url = f"https://commons.wikimedia.org/wiki/{category}"
    response = requests.get(url)
    html_content = response.text

    # Step 2: Parse the HTML content
    soup = BeautifulSoup(html_content, 'html.parser')

    # Step 3: Find all URLs in  tags
    urls = []
    for link in soup.find_all('a'):
        href = link.get('href')
        if href:
            #print(href)
            if href.startswith("/wiki/File:") and href != href_old: # This test because all links are in double!
                urls.append(f"https://commons.wikimedia.org{href}")
                href_old = href

    number_of_pages = len(urls)
    print(f"Number of pages to scrape: {number_of_pages}")

    i = 1
    items = []
    for url in urls:
        print(f"{i}/{number_of_pages}")
        url = url.replace("\ufeff", "")  # Remove BOM (Byte order mark at the start of a text stream)
        item = scrape_web_page(url, "hproduct commons-file-information-table")
        print(item)
        items.append(item)
        #time.sleep(1)
        i = i + 1

    # Save the Python list in a JSON file
    # json.dump is designed to take the Python objects, not the already-JSONified string. Read docs.python.org/3/library/json.html.
    with open(f"{FILE_PATH}{category}-swp.json", "w") as json_file:
        json.dump(items, json_file) # That step replaces the accentuated characters (ex: é) by its utf8 codes (ex: \u00e9)
    json_file.close()
    
def scrape_europeana_url(url):
    """
    METHOD 4: Scrape one URL (should be Europeana) and save the result in a JSON file
    """

    #url = "https://www.europeana.eu/en/item/0940429/_nhtSx4z"

    # Step 1: Load the HTML content from a webpage
    response = requests.get(url)
    html_content = response.text

    # Step 2: Parse the HTML content
    soup = BeautifulSoup(html_content, 'html.parser')

    url = url.replace("\ufeff", "")  # Remove BOM (Byte order mark at the start of a text stream)
    item = scrape_web_page(url, "card metadata-box-card mb-3")
    print(item)
    items = []
    items.append(item)   # Add in a list, even if only one item

    url2 = url.replace("https://","")
    url2 = url2.replace("http://","")
    url2 = url2.replace("/","-")
    # Save the Python list in a JSON file
    # json.dump is designed to take the Python objects, not the already-JSONified string. Read docs.python.org/3/library/json.html.
    with open(f"./files/{url2}-swp.json", "w") as json_file:
        json.dump(items, json_file) # That step replaces the accentuated characters (ex: é) by its utf8 codes (ex: \u00e9)
    json_file.close()

# Main program

st.title("BMAE Admin interface")
st.caption("💬 BMAE, A chatbot powered by Langchain and Streamlit")

#scrape_commons_category("Category_Portrait_paintings_of_Louise_of_Orléans")
#scrape_europeana_url("https://www.europeana.eu/en/item/2024903/photography_ProvidedCHO_KU_Leuven_9983808530101488")

options = ['Commons', 'Europeana']
choice = st.sidebar.radio("Scrape page(s) from:", options)
st.write(f'You selected: {choice}')

if choice == "Europeana":
    url = st.text_input("Europeana URL?")
    if url:
        st.write(f"Scraping the web page...")
        scrape_europeana_url(url)
        st.write(f"Web page scraped!")
