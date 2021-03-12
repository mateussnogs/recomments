import scrapy
from scrapy_splash import SplashRequest
from scrapy.http import FormRequest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import hashlib
import pandas as pd

# models 
class ArtigoItem(scrapy.Item):    
    autor = scrapy.Field()
    titulo = scrapy.Field()
    conteudo = scrapy.Field()
    data = scrapy.Field()
    nLikes = scrapy.Field()
    isComment = scrapy.Field()
    idColuna = scrapy.Field()
    idArtigo = scrapy.Field()
    idComment = scrapy.Field()
    url = scrapy.Field()


# class CommentItem(scrapy.Item):
#     autor = scrapy.Field()
#     conteudo = scrapy.Field()
#     nLikes = scrapy.Field()

# ------------------------------------------------------------------------------------

try:
    dfIds = pd.read_csv("knownIds.csv")
except:
    dfIds = pd.DataFrame(columns=['hash', 'url', 'artigoId'])
    dfIds = dfIds.set_index('hash')

def get_expand_button(driver):
    try:
        driver.implicitly_wait(10)
        expandBtn = driver.find_element_by_class_name("c-button.c-button--expand")
        return expandBtn
    except:
        return None


class TestSpider(scrapy.Spider):
    name='fsp'

    # start_urls = ["https://login.folha.com.br/login", "http://www.folha.uol.com.br/colunaseblogs/#colunas-e-blogs"]
    start_urls = ["http://www.folha.uol.com.br/colunaseblogs/#colunas-e-blogs"]
    def __init__(self):
        # selenium to constinously expand the texts of a column
        options = webdriver.ChromeOptions()
        options.add_argument("headless")
        options.add_argument("--silent")
        desired_capabilities = options.to_capabilities()
        self.driver = webdriver.Chrome(desired_capabilities=desired_capabilities)
        # self.driver.set_network_conditions(
        #     offline=False,
        #     latency=5,  # additional latency (ms)
        #     download_throughput= 1000 / 2 * 1024,  # maximal throughput
        #     upload_throughput= 1000 / 2 * 1024  # maximal throughput
        # )
    def start_requests(self):
        i = 0
        for url in self.start_urls:
            # if (i == 0):
                # yield FormRequest(url, formdata={'email':'', 'password':''})
                # i+=1
            # else:
            splash_args = {
                'wait': 1.5,
                'headers': {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:84.0) Gecko/20100101 Firefox/84.0'}
            }
            yield SplashRequest(url, self.parse_colunas, args=splash_args)

    def parse_colunas(self, response):
        colunistas_urls = response.css("h3.c-author__kicker.c-author__kicker--medium a::attr(href)").getall()
        # for url in colunistas_urls:
        for i in range(len(colunistas_urls)):
            url = colunistas_urls[i]
            splash_args = {
                'wait': 1.5,
            }
            yield SplashRequest(url, self.parse_coluna, args=splash_args, cb_kwargs={'idColuna': i})
 
    def parse_coluna(self, response, idColuna):        
        self.driver.get(response.url)
        expandBtn = get_expand_button(self.driver)
        i = 0
        # expand until is no longer possible
        while(expandBtn):
            self.driver.execute_script("arguments[0].click();", expandBtn)
            expandBtn = get_expand_button(self.driver)
            print(i)
            i += 1
        try:
            textos_urls = [e.get_attribute('href') for e in self.driver.find_elements_by_css_selector("div.c-headline__content a")]
            # textos_urls = response.css("div.c-headline__content a::attr(href)").getall()
            
            for i in range(len(textos_urls)):
                url = textos_urls[i]
                idArtigo = i
                if (not url in dfIds.index):
                    hash = hashlib.md5(str(url).encode('utf-8')).hexdigest()
                    dfIds.loc[hash] = [url, idArtigo]
                    splash_args = {
                        'wait': 0.5,
                    }
                    yield SplashRequest(url, self.parse_texto, args=splash_args, cb_kwargs={'idColuna': idColuna, 'idArtigo': idArtigo})
        except:
            print("Exception requesting url")
            pass
        
    def parse_texto(self, response, idColuna, idArtigo):
        artigo = ArtigoItem()
        # artigo['conteudo'] = response.css("div.c-news__content p")
        artigo['idColuna'] = idColuna
        artigo['idArtigo'] = idArtigo
        # artigo['titulo'] = response.xpath("//h1[contains(@class, 'title')]").get()
        artigo['titulo'] = response.xpath("//h1").getall()[-1]
        artigo['conteudo'] = response.xpath("//div[contains(@class, 'content')]//p").getall()
        artigo['autor'] = response.css("h4.c-top-columnist__name a::text").get()
        artigo['data'] = response.css("time[itemprop='datePublished']::text").get()
        artigo['isComment'] = False
        artigo['url'] = response.url
        yield artigo
        dfIds.to_csv("knownIds.csv")
        all_coments_link = response.css("a.more.c-button::attr(href)").get()
        if (all_coments_link is not None):
            splash_args = {
                'wait': 1.5,
            }
            yield SplashRequest(all_coments_link, self.parse_coments, 
                args=splash_args, cb_kwargs={'idArtigo': artigo['idArtigo'], 'idColuna': artigo['idColuna'], 
                'urlArtigo': artigo['url'], 'lastCommentId': 0})


    def parse_coments(self, response, idArtigo, idColuna, urlArtigo, lastCommentId):
        # global ID_COMMENT
        conteudos = response.css("p.c-list-comments__comment").getall()
        autores = response.css("strong.c-list-comments__user").getall()
        likes = response.xpath("//button[contains(@class, 'rating')]/span").getall()
        coments = zip(autores, conteudos, likes)
        for c in coments:            
            coment = ArtigoItem()
            coment['conteudo'] = c[0]
            coment['autor'] = c[1]
            coment['nLikes'] = c[2]
            coment['isComment'] = True
            coment['idArtigo'] = idArtigo
            coment['idColuna'] = idColuna
            coment['url'] = urlArtigo
            coment['idComment'] = lastCommentId
            lastCommentId += 1
            yield coment
        temProx = response.css("li.c-pagination__arrow a svg.icon.icon--chevron-right").get()
        if (temProx is not None):
            # getall[-1] para pegar o link da última seta - a direita.
            prox_pag = response.css("li.c-pagination__arrow a::attr(href)").getall()[-1]
            splash_args = {
                'wait': 1.5,
            }
            yield SplashRequest(prox_pag, self.parse_coments, 
                args=splash_args, cb_kwargs={'idArtigo': idArtigo, 'lastCommentId': lastCommentId})

        # from scrapy.shell import inspect_response
        # inspect_response(response, self)
