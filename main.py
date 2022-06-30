from os import link
from fastapi import FastAPI, Request, Response
from bs4 import BeautifulSoup
from fastapi.responses import HTMLResponse, FileResponse
import lxml
import aiofiles
import os
import requests
import json
import img2pdf
import re
from requests_html import HTMLSession
import requests

def Filter(text: str):
    K = text.split(" ")
    K.remove(K[0])
    result = " ".join(K)
    return result
       
def get_search_results(query):  
        try:
            mangalink = f"http://kissmanga.nl/search?q={query}"
            response = requests.get(mangalink)
            response_html = response.text
            soup = BeautifulSoup(response_html, 'lxml')
            source_url = soup.findAll("div", {"class": "media-body"})
            res_search_list = []
            for links in source_url:
                a = links.find('a')
                title = a.find('h4').text
                mangaId = a['href']
                mangaid = mangaId.split("/").pop()
                res_search_list.append({"title":f"{title}","mangaid":f"{mangaid}"})           
            return res_search_list
        except requests.exceptions.ConnectionError:
            return {"status":"404", "reason":"Check the host's network Connection"}

def get_manga_details(mangaid):  
        try:
            mangalink = f"http://kissmanga.nl/manga/{mangaid}"
            response = requests.get(mangalink)
            plainText = response.text
            soup = BeautifulSoup(plainText, "lxml")
            mangainfo = soup.find("div", {"class": "media-body"})
            manga = soup.find("p", {"class": "description-update"}).text
            image = soup.find("div", {"class": "media-left cover-detail"})
            imageurl = image.find('img')['src']
            description = soup.find("div", {"class": "manga-content"}).p.text.strip()
            title = mangainfo.h1.text
            manSplit = manga.split("\n")
            genres = []          
            status = []
            alternative = []
            view = []
            author = []
            status = []
            for i in manSplit:
                if "Alternative" in i:
                    alternative.append(Filter(i.strip()))
                if "View" in i:
                    view.append(Filter(i.strip()))
                if "Author(s)" in i:       
                    author.append(Filter(i.strip()[:-1]))
                if "Status" in i:               
                    status.append(Filter(i.strip()))
                if "\r" in i:
                    genres.append(i.strip()[:-1])
                genrek = ", ".join(genres)
                statusk = ", ".join(status)
                alternativek = ", ".join(alternative)
                viewk = ", ".join(view)
                authork = ", ".join(author)
                res_search_list = {"title":f"{title}","description":f"{description}","image":f"{imageurl}","status":f"{statusk}","view":f"{viewk}","author":f"{authork}","alternative":f"{alternativek}","genre":f"{genrek}"}          
            return res_search_list
        except AttributeError:
            return "Wrong Mangaid"
        except requests.exceptions.ConnectionError:
            return {"status":"404", "reason":"Check the host's network Connection"}


def get_manga_chapter(mangaid, chapNumber):  
        try:
            mangalink = f"http://kissmanga.nl/{mangaid}-chapter-{chapNumber}"
            response = requests.get(mangalink)
            response_html = response.text
            soup = BeautifulSoup(response_html, 'lxml')
            source_url = soup.find("p", id="arraydata")
            totalPages = source_url.text.split(",")
            res_search_list = {"totalPages":f"{totalPages}"}
            return res_search_list
        except AttributeError:
            return "Invalid Mangaid or chapter number"
        except requests.exceptions.ConnectionError:
            return {"status":"404", "reason":"Check the host's network Connection"}
       
def read_html(lol):  # returns list of image links of pages of full chapter [imglink1, imglink2, full chapter]
        try:
            url = f"{lol}"
            response = requests.get(url)
            response_html = response.text
            soup = BeautifulSoup(response_html, 'lxml')
            chapter_pages = soup.find("p", id="arraydata")
            pages = chapter_pages.text.split(",")
            return pages
        except AttributeError:
            return "Invalid Mangaid or chapter number"
        except requests.exceptions.ConnectionError:
            return "Check the host's network Connection"
       

from telegraph.aio import Telegraph


async def img2tph(name, link):
    lmeo = []
    for i in link:
        a_tag = f'<img src="{i}"/>'
        lmeo.append(a_tag)
    k = '\n'.join(lmeo)

    x = Telegraph()
    await x.create_account('MangaVoid')
    img = await x.create_page(name, author_name='MetaVoid', author_url='https://t.me/metavoidsupport', html_content=k)
    return img['url']

app = FastAPI()
@app.get('/')
def root(request: Request):
    return {"root": request.url.hostname}

@app.get('/search')
async def search(q):
    manga_search = get_search_results(query=q)
    return manga_search


@app.get('/details')
def manga_detail(manga):
    manga_details = get_manga_details(mangaid=manga)
    return manga_details


@app.get('/manga/read')
async def read(manga, chapter):
    chapurl = f"http://kissmanga.nl/{manga}-chapter-{chapter}"
    chap = read_html(chapurl)
    x = '''<div class="mangaapi" style="background-color:black">'''
    for i in chap:
        x = f'''{x}
    <div class="image">
      <img src="{i}" style="width:100%"><br>
      <br>
    </div>
        '''
    return HTMLResponse(content=x, status_code=200)


@app.get('/manga/telegraph')
async def read(manga, chapter):
    chapurl = f"http://kissmanga.nl/{manga}-chapter-{chapter}"
    chap = read_html(chapurl)
    name = f"{manga} {chapter}"
    url = await img2tph(name, chap)
    return {'link': url}
    
    

@app.get('/manga/pdf')
def episode_pdf(manga, chapter):
    chapurl = f"http://kissmanga.nl/{manga}-chapter-{chapter}"
    chap = read_html(chapurl)   
    i = 1
    Download = f"{manga}-Chapter-{chapter}"
    if os.path.exists(Download):
        return FileResponse(f"{Download}.pdf", media_type="application/pdf")
    else:
        os.mkdir(Download)
        for x in chap:
            res = requests.get(x).content
            with open(f"{Download}/{i}.jpg" , "wb") as f:
                f.write(res)
            i += 1
            file_paths = []
            for root, directories, files in os.walk(f"{Download}"):
                for filename in files:
                    filepath = os.path.join(root, filename)
                    file_paths.append(filepath)

            file_paths.sort(key=lambda f: int(re.sub('\D', '', f)))
            with open(f"{Download}.pdf" ,"wb") as f:
                f.write(img2pdf.convert(file_paths)) 
       
        return FileResponse(f"{Download}.pdf", media_type="application/pdf")
    

@app.get('/chapter')
def chapter_img(manga, chapter):
    manga_chapter = get_manga_chapter(mangaid=manga, chapNumber=chapter)    
    return manga_chapter
