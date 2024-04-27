import requests
from bs4 import BeautifulSoup

### Insert Ur Api key to get Started here USe Link shortner urlshortx ###
url_list = {}
api_key = "ede4b7e2c0392f545a2681dfe67134fde4379618"


def search_movies(query):
    movies_list = []
    website = BeautifulSoup(requests.get(f"https://mkvcinemas.nexus/?s={query.replace(' ', '+')}").text, "html.parser")
    movies = website.find_all("a", {'class': 'ml-mask jt'})
    for movie in movies:
        if movie:
            movies_details = {}  # Create a new dictionary for each movie
            movies_details["id"] = f"link{movies.index(movie)}"
            movies_details["title"] = movie.find("span", {'class': 'mli-info'}).text
            url_list[movies_details["id"]] = movie['href']
            movies_list.append(movies_details)  # Append the newly created dictionary
    return movies_list

def get_movie(query):
    movie_details = {}
    movie_page_link = BeautifulSoup(requests.get(f"{url_list[query]}").text, "html.parser")
    if movie_page_link:
        title = movie_page_link.find("div", {'class': 'mvic-desc'}).h3.text
        movie_details["title"] = title
        img = movie_page_link.find("div", {'class': 'mvic-thumb'})['data-bg']
        movie_details["img"] = img
        links = movie_page_link.find_all("a", {'rel': 'noopener', 'data-wpel-link': 'internal'})
        final_links = {}
        for i in links:
            url = f"https://urlshortx.com/api?api={api_key}&url={i['href']}"
            response = requests.get(url)
            link = response.json()
            final_links[f"{i.text}"] = link['shortenedUrl']
        movie_details["links"] = final_links
    return movie_details
